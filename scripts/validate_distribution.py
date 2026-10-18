"""Validate one prebuilt wheel in an isolated installation; never build or publish.

The external walkthrough fixtures come from this checkout. Every product import
and CLI invocation comes from the installed wheel, using the selected Python.
Dependencies are installed normally; --no-index/--find-links can use a wheelhouse.
Build provenance is unconfirmed unless an explicit build manifest binds the
wheel filename, SHA-256 and version to a source commit. See docs/distribution.md.
"""

from __future__ import annotations

import argparse
import email.parser
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import venv
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__:
    from . import gen_quickstart
else:
    import gen_quickstart  # type: ignore[import-not-found, no-redef]

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "core",
    "inference",
    "evaluation",
    "llm_judge",
    "finetuning",
    "safety",
    "privacy",
    "judge_only",
}
SCHEMAS = {
    "manifest",
    "lock",
    "run_record",
    "profile",
    "project_rules",
    "rule_archive",
    "config",
    "audit_report",
    "diff_report",
    "discover_candidates",
}


class ValidationFailure(ValueError):
    """A fixed diagnostic identifier, safe to include in a portable summary."""


def _require(condition: bool, name: str) -> None:
    if not condition:
        raise ValidationFailure(name)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_wheel(wheel: Path) -> dict[str, str]:
    _require(wheel.name.endswith(".whl"), "wheel_filename")
    with zipfile.ZipFile(wheel) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        _require(len(names) == 1, "wheel_metadata_count")
        metadata = email.parser.BytesParser().parsebytes(archive.read(names[0]))
    _require(metadata.get_all("Name") == ["reprollm"], "wheel_distribution_name")
    versions = metadata.get_all("Version") or []
    _require(
        len(versions) == 1 and re.fullmatch(r"[A-Za-z0-9.!+_-]+", versions[0]) is not None,
        "wheel_metadata_version",
    )
    _require(
        re.fullmatch(r"reprollm-[A-Za-z0-9.!+_-]+\.whl", wheel.name) is not None, "wheel_filename"
    )
    return {"filename": wheel.name, "version": versions[0], "sha256": _sha(wheel.read_bytes())}


def source_provenance(identity: dict[str, str], manifest: Path | None) -> dict[str, Any]:
    if manifest is None:
        return {"status": "UNCONFIRMED", "source_commit": None}
    raw = manifest.read_bytes()
    data = json.loads(raw)
    _require(isinstance(data, dict), "build_manifest_document")
    _require(
        type(data.get("schema_version")) is int and data["schema_version"] == 1,
        "build_manifest_schema",
    )
    commit = data.get("source_commit")
    _require(
        isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
        "build_manifest_commit",
    )
    _require(data.get("version") == identity["version"], "build_manifest_version")
    artifacts = data.get("artifacts")
    _require(isinstance(artifacts, list), "build_manifest_artifacts")
    matches = [
        item
        for item in artifacts
        if isinstance(item, dict) and item.get("filename") == identity["filename"]
    ]
    _require(
        len(matches) == 1 and matches[0].get("sha256") == identity["sha256"], "build_manifest_wheel"
    )
    return {
        "status": "BUILD_MANIFEST_ASSOCIATED",
        "source_commit": commit,
        "manifest_sha256": _sha(raw),
    }


def command_evidence(step: gen_quickstart.Step) -> dict[str, Any]:
    return {
        "command": step.command,
        "executable": "<venv-python>",
        "exit_code": step.exit_code,
        "elapsed_seconds": round(step.elapsed_seconds, 6),
        "stdout_sha256": _sha(
            (step.raw_stdout if step.raw_stdout is not None else step.stdout).encode("utf-8")
        ),
        "stderr_sha256": _sha(
            (step.raw_stderr if step.raw_stderr is not None else step.stderr).encode("utf-8")
        ),
    }


def _export_has_cap(document: str, expected: int) -> bool:
    _, heading, generation = document.partition("### Generation parameters\n")
    section = generation.split("\n### ", 1)[0]
    return bool(heading) and f"- `max_tokens`: {expected}" in section.splitlines()


def verify_walkthrough(records: list[gen_quickstart.Step], work: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool) -> None:
        _require(passed, name)
        checks.append({"id": name, "passed": True})

    check(
        "twelve_step_workflow",
        [step.command[0] for step in records]
        == [
            "audit",
            "init",
            "audit",
            "audit",
            "lock",
            "lock",
            "run",
            "lock",
            "run",
            "audit",
            "diff",
            "export",
        ],
    )
    check(
        "command_exit_codes",
        [step.exit_code for step in records]
        == [
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            0,
        ],
    )
    reports = [json.loads(step.report_json) for step in records if step.command[0] == "audit"]
    check("audit_levels", [report["level"] for report in reports] == [0, 1, 1, 2])
    check(
        "offline_locks",
        all(
            "--offline" in step.command or "--check" in step.command
            for step in records
            if step.command[0] == "lock"
        ),
    )
    runs = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(work.glob(".reprollm/runs/*/run.json"))
    ]
    check(
        "capture_values",
        len(runs) == 2
        and all(
            run["status"] == "completed"
            and run["exit_code"] == 0
            and run["bindings_observed"]["generation.max_tokens"][0]["value"] == cap
            and run["input_capture"]["baseline_phase"] == "pre_child"
            and run["input_capture"]["consumption"] == "unverified"
            for run, cap in zip(runs, (32, 48), strict=True)
        ),
    )
    delta = json.loads(next(step.report_json for step in records if step.command[0] == "diff"))
    caps = [item for item in delta["changes"] if item["path"] == "generation.max_tokens"]
    check(
        "semantic_cap_drift",
        len(caps) == 1
        and caps[0]["a"] == 32
        and caps[0]["b"] == 48
        and caps[0]["severity"] == "HIGH",
    )
    document = (work / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    check(
        "export_selected_run",
        runs[1]["run_id"] in document
        and _export_has_cap(document, 48)
        and "unverified" in document,
    )
    return checks


def _install(
    python: Path,
    wheel: Path,
    cwd: Path,
    *,
    no_index: bool,
    find_links: list[Path],
    raw_output_dir: Path | None = None,
) -> dict[str, Any]:
    command = [
        str(python),
        "-I",
        "-X",
        "utf8",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
    ]
    if no_index:
        command.append("--no-index")
    for link in find_links:
        command.extend(["--find-links", str(link)])
    command.append(str(wheel))
    env = gen_quickstart._env(python)
    # Only the installation phase may contact a package source. Never forward
    # model/provider credentials to the offline product commands.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"):
        if name in os.environ:
            env[name] = os.environ[name]
    started = time.monotonic()
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, encoding="utf-8")
    if raw_output_dir:
        (raw_output_dir / "installation.stdout.txt").write_text(
            result.stdout, encoding="utf-8", newline="\n"
        )
        (raw_output_dir / "installation.stderr.txt").write_text(
            result.stderr, encoding="utf-8", newline="\n"
        )
    evidence = {
        "exit_code": result.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "dependency_mode": "declared-runtime-dependencies",
        "no_index": no_index,
        "find_links_count": len(find_links),
        "stdout_sha256": _sha(result.stdout.encode()),
        "stderr_sha256": _sha(result.stderr.encode()),
    }
    return evidence


def _import_evidence(
    python: Path,
    environment: Path,
    cwd: Path,
    identity: dict[str, str],
    raw_output_dir: Path | None = None,
) -> dict[str, Any]:
    code = """
import importlib.metadata, json, site, sys
from pathlib import Path
import reprollm
import reprollm.cli.main
d = importlib.metadata.distribution('reprollm')
print(json.dumps({'module': str(Path(reprollm.__file__).resolve()),
    'cli_module': str(Path(reprollm.cli.main.__file__).resolve()),
    'distribution_root': str(Path(d.locate_file('')).resolve()),
    'version': d.version, 'code_version': reprollm.__version__,
    'prefix': sys.prefix, 'user_site_enabled': site.ENABLE_USER_SITE,
    'sys_path': sys.path, 'direct_url': d.read_text('direct_url.json'),
    'installed_distributions': sorted(
        ({'name': item.metadata['Name'], 'version': item.version}
         for item in importlib.metadata.distributions()), key=lambda item: item['name'])}))
"""
    result = subprocess.run(
        [str(python), "-I", "-X", "utf8", "-c", code],
        cwd=cwd,
        env=gen_quickstart._env(python),
        capture_output=True,
        encoding="utf-8",
    )
    _require(result.returncode == 0, "installed_import")
    probe_sha256 = _sha(result.stdout.encode("utf-8"))
    info = json.loads(result.stdout)
    if raw_output_dir:
        (raw_output_dir / "import-probe.json").write_text(
            result.stdout, encoding="utf-8", newline="\n"
        )
    prefix = environment.resolve()
    _require(Path(info["prefix"]).resolve() == prefix, "isolated_prefix")
    _require(not info["user_site_enabled"], "isolated_user_site")
    _require(info["version"] == identity["version"] == info["code_version"], "installed_version")
    for name in ("module", "cli_module", "distribution_root"):
        _require(Path(info[name]).is_relative_to(prefix), "installed_import_location")
    _require(
        all(not Path(path).resolve().is_relative_to(ROOT.resolve()) for path in info["sys_path"]),
        "isolated_source_path",
    )
    direct_url = json.loads(info["direct_url"]) if info["direct_url"] else {}
    _require(not direct_url.get("dir_info", {}).get("editable"), "isolated_non_editable")
    _require(
        direct_url.get("archive_info", {}).get("hashes", {}).get("sha256") == identity["sha256"],
        "installed_wheel_hash",
    )
    cli = python.parent / ("reprollm.exe" if os.name == "nt" else "reprollm")
    result = subprocess.run(
        [str(cli), "--version"],
        cwd=cwd,
        env=gen_quickstart._env(python),
        capture_output=True,
        encoding="utf-8",
    )
    _require(
        result.returncode == 0 and result.stdout.strip() == f"reprollm {identity['version']}",
        "installed_console_entrypoint",
    )
    return {
        "python": "<venv-python>",
        "module": Path(info["module"]).relative_to(prefix).as_posix(),
        "cli_module": Path(info["cli_module"]).relative_to(prefix).as_posix(),
        "distribution_version": info["version"],
        "code_version": info["code_version"],
        "isolated": True,
        "user_site_enabled": False,
        "editable": False,
        "archive_sha256": identity["sha256"],
        "console_entrypoint": "<venv-cli>",
        "console_entrypoint_exit_code": result.returncode,
        "installed_distributions": info["installed_distributions"],
        "probe_sha256": probe_sha256,
    }


def _package_data(
    python: Path, work: Path, on_step: Callable[[gen_quickstart.Step], None]
) -> list[dict[str, Any]]:
    checks = []

    def run(args: list[str]) -> gen_quickstart.Step:
        step = gen_quickstart._run(args, work, python=python, on_step=on_step)
        _require(step.exit_code == 0, "package_data_command")
        return step

    rows = json.loads(run(["profiles", "list", "--json"]).stdout)
    _require(
        {row["name"] for row in rows} == PROFILES
        and all(row["source"] == "built-in" for row in rows),
        "installed_profiles",
    )
    for name in sorted(PROFILES):
        step = run(["profiles", "show", name])
        _require(
            f"profile: {name}" in step.stdout and "rules (" in step.stdout,
            "installed_profile_rules",
        )
    checks.append({"id": "all_builtin_profiles", "passed": True})
    run(["schema", "export", "--out", "schema-output"])
    actual = {path.name: path.read_bytes() for path in (work / "schema-output").glob("*.json")}
    expected = {
        f"{name}.schema.json": (ROOT / "schemas" / f"{name}.schema.json").read_bytes()
        for name in SCHEMAS
    }
    _require(actual == expected, "installed_schema_exports")
    checks.append({"id": "all_schema_exports", "passed": True})
    run_id = sorted(work.glob(".reprollm/runs/*/run.json"))[-1].parent.name
    for template in ("default", "neurips", "acl", "acm"):
        target = f"REPRODUCIBILITY.{template}.md"
        run(["export", ".", "--run", run_id, "--template", template, "--output", target])
        content = (work / target).read_text(encoding="utf-8")
        _require(run_id in content and _export_has_cap(content, 48), "installed_export_template")
        checks.append({"id": f"template_{template}", "passed": True})
    return checks


def _fixture_hashes() -> dict[str, str]:
    paths = [
        ROOT / "scripts/gen_quickstart.py",
        ROOT / "scripts/capture_probe.py",
        ROOT / "tests/fixtures/repos/hf_vllm_eval/manifests/complete.yaml",
    ]
    paths.extend(
        path
        for path in (ROOT / "examples/hf_vllm_eval").rglob("*")
        if path.is_file()
        and ".reprollm" not in path.parts
        and path.name not in ("reprollm.yaml", "reprollm.lock")
        and not path.name.startswith("REPRODUCIBILITY")
    )
    paths.extend((ROOT / "schemas").glob("*.json"))
    return {path.relative_to(ROOT).as_posix(): _sha(path.read_bytes()) for path in sorted(paths)}


def validate(
    wheel: Path,
    *,
    build_manifest: Path | None = None,
    expected_version: str | None = None,
    expected_tag: str | None = None,
    no_index: bool = False,
    find_links: list[Path] | None = None,
    raw_output_dir: Path | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {"schema_version": 1, "status": "FAIL", "commands": [], "checks": []}
    started = time.monotonic()

    def on_step(step: gen_quickstart.Step) -> None:
        evidence = command_evidence(step)
        if raw_output_dir:
            stem = f"command-{len(summary['commands']) + 1:02d}"
            for stream in ("stdout", "stderr"):
                filename = f"{stem}.{stream}.txt"
                raw = getattr(step, f"raw_{stream}")
                value = raw if raw is not None else getattr(step, stream)
                (raw_output_dir / filename).write_text(value, encoding="utf-8", newline="\n")
                evidence[f"{stream}_artifact"] = filename
        summary["commands"].append(evidence)

    try:
        wheel = wheel.absolute()
        identity = inspect_wheel(wheel)
        summary["wheel"] = identity
        _require(
            (expected_version is None or expected_version == identity["version"])
            and (expected_tag is None or expected_tag == f"v{identity['version']}"),
            "wheel_target_version",
        )
        summary["provenance"] = source_provenance(identity, build_manifest)
        summary["fixture_sha256"] = _fixture_hashes()
        if raw_output_dir:
            raw_output_dir = raw_output_dir.absolute()
            _require(
                not raw_output_dir.resolve().is_relative_to(ROOT.resolve()),
                "private_output_outside_checkout",
            )
            _require(
                not raw_output_dir.exists() or not any(raw_output_dir.iterdir()),
                "private_output_empty",
            )
            raw_output_dir.mkdir(parents=True, exist_ok=True)
        summary["private_raw_evidence_retained"] = raw_output_dir is not None
        with tempfile.TemporaryDirectory(prefix="reprollm-wheel-") as temporary:
            base = Path(temporary)
            _require(not base.resolve().is_relative_to(ROOT.resolve()), "external_environment")
            environment = base / "venv"
            candidate = base / wheel.name
            shutil.copyfile(wheel, candidate)
            _require(_sha(candidate.read_bytes()) == identity["sha256"], "wheel_copy_hash")
            venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            summary["installation"] = _install(
                python,
                candidate,
                base,
                no_index=no_index,
                find_links=find_links or [],
                raw_output_dir=raw_output_dir,
            )
            _require(summary["installation"]["exit_code"] == 0, "wheel_install")
            summary["imports"] = _import_evidence(
                python, environment, base, identity, raw_output_dir
            )
            work = base / "tour"
            try:
                records = gen_quickstart.run_workflow(work, python=python, on_step=on_step)
                summary["checks"].extend(verify_walkthrough(records, work))
                summary["checks"].extend(_package_data(python, work, on_step))
            finally:
                if raw_output_dir and work.exists():
                    shutil.copytree(
                        work, raw_output_dir / "walkthrough", ignore=shutil.ignore_patterns(".git")
                    )
        _require(_sha(wheel.read_bytes()) == identity["sha256"], "wheel_changed_during_validation")
        summary["status"] = "PASS"
    except gen_quickstart.CommandError as exc:
        if not summary["commands"]:
            on_step(exc.step)
        summary["failure"] = "installed_command"
    except ValidationFailure as exc:
        summary["failure"] = str(exc)
    except (
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        summary["failure"] = "invalid_input_or_execution"
        summary["error_type"] = type(exc).__name__
    summary["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--build-manifest", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-tag")
    parser.add_argument("--no-index", action="store_true")
    parser.add_argument("--find-links", type=Path, action="append", default=[])
    parser.add_argument(
        "--raw-output-dir",
        type=Path,
        help=(
            "Empty private directory outside this checkout; raw logs contain local paths. "
            "Do not publish unsanitized."
        ),
    )
    parser.add_argument(
        "--output", type=Path, help="Write the same portable JSON emitted on stdout."
    )
    args = parser.parse_args(argv)
    result = validate(
        args.wheel,
        build_manifest=args.build_manifest,
        expected_version=args.expected_version,
        expected_tag=args.expected_tag,
        no_index=args.no_index,
        find_links=[path.absolute() for path in args.find_links],
        raw_output_dir=args.raw_output_dir,
    )
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
