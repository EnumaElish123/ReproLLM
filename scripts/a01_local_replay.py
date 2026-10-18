"""Replay the existing recipe's stdlib layer twice against one prebuilt wheel.

This A01-B tool never builds, resolves remote models, runs lm-eval or publishes.
It reuses D02's installation/isolation helpers and D01's independent child probe.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
import traceback
import venv
from pathlib import Path
from typing import Any

import yaml

if __package__:
    from . import check_no_leaks, gen_quickstart, validate_distribution
else:
    import check_no_leaks  # type: ignore[import-not-found, no-redef]
    import gen_quickstart  # type: ignore[import-not-found, no-redef]
    import validate_distribution  # type: ignore[import-not-found, no-redef]

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "examples/lm_eval_replay"
CHILD = ["python", "-I", "-X", "utf8", "probe.py", "--config", "validation/eval.yaml"]


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def local_snapshot(directory: Path, reference: str) -> Path:
    path = Path(reference)
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in reference
        and ":" not in reference,
        "snapshot_path",
    )
    resolved = (directory / path).resolve()
    require(resolved.is_relative_to(directory.resolve()), "snapshot_path")
    return resolved


def verify_capture(
    record: dict[str, Any],
    directory: Path,
    receipt: dict[str, Any],
    recipe: Path,
    cap: int,
    *,
    rewrite: bool = False,
) -> dict[str, Any]:
    sources = {
        "validation/eval.yaml": recipe
        / ("validation/eval.yaml" if cap == 32 else "variants/eval-b.yaml"),
        "validation/tasks/gsm8k_validation.yaml": recipe / "validation/tasks/gsm8k_validation.yaml",
        "lm_eval/tasks/gsm8k/gsm8k.yaml": recipe / "upstream/gsm8k.yaml",
        "probe.py": recipe / "probe.py",
    }
    config = sources["validation/eval.yaml"].read_bytes()
    require(record["status"] == "completed" and record["exit_code"] == 0, "child_completion")
    require(receipt["schema_version"] == 1, "receipt_schema")
    require(receipt["input_sha256"] == digest(config), "consumed_input_hash")
    require(receipt["configuration"] == yaml.safe_load(config), "consumed_configuration")
    require(receipt["configuration"]["gen_kwargs"]["max_gen_toks"] == cap, "consumed_cap")
    require(record["bindings_observed"]["generation.max_tokens"][0]["value"] == cap, "captured_cap")
    capture = record["input_capture"]
    require(
        capture["baseline_phase"] == "pre_child" and capture["consumption"] == "unverified",
        "capture_scope",
    )
    references = {item["path"]: item for item in record["files"]}
    checks = {item["path"]: item for item in capture["checks"]}
    for name, source in sources.items():
        data = source.read_bytes()
        reference = references[name]
        require(reference["sha256"] == "sha256:" + digest(data), "input_hash")
        require(reference["size_bytes"] == len(data), "input_size")
        require(reference["snapshot"] is not None and not reference["redacted"], "input_snapshot")
        require(
            local_snapshot(directory, reference["snapshot"]).read_bytes() == data,
            "input_snapshot_bytes",
        )
        expected_change = "changed" if rewrite and name == "validation/eval.yaml" else "unchanged"
        require(checks[name]["change"] == expected_change, "input_change")
        require(checks[name]["before"]["sha256"] == reference["sha256"], "input_baseline")
    if rewrite:
        changed = directory.parents[2] / "validation/eval.yaml"
        require(
            yaml.safe_load(changed.read_bytes())["gen_kwargs"]["max_gen_toks"] == 96,
            "rewritten_cap",
        )
        require(
            checks["validation/eval.yaml"]["after"]["sha256"]
            == "sha256:" + digest(changed.read_bytes()),
            "post_input_hash",
        )
    return {
        "consumed_cap": cap,
        "input_snapshot_files_checked": len(sources),
        "recorder_consumption": "unverified",
        "input_change": "changed" if rewrite else "unchanged",
    }


def assert_portable(directory: Path, private_values: list[str]) -> None:
    require(not check_no_leaks.scan(directory), "known_machine_or_secret_in_evidence")
    spec = importlib.util.spec_from_file_location(
        "a01_secret_policy", ROOT / "src/reprollm/core/redaction.py"
    )
    require(spec is not None and spec.loader is not None, "secret_policy_available")
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)

    def check_text(text: str) -> None:
        require(
            re.search(
                r"(?<![\w:])(?:[A-Za-z]:[/\\]|\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_$.-]+|/(?:Users|home|root|tmp|mnt|opt|var|workspace|data|etc|private|usr|srv)/)",
                text,
            )
            is None,
            "absolute_path_in_evidence",
        )
        require(policy.redact_text(text)[1] == 0, "credential_pattern_in_evidence")

    def check_value(value: Any) -> None:
        if isinstance(value, str):
            check_text(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                if str(key).upper() in policy.KNOWN_SECRET_NAMES:
                    require(
                        item == {"present": True} or item is None or item == "",
                        "keyed_secret_in_evidence",
                    )
                if isinstance(item, str):
                    require(
                        policy.redact_text(f"{key}=\n{item}")[1] == 0, "keyed_secret_in_evidence"
                    )
                check_value(item)
        elif isinstance(value, list):
            for item in value:
                check_value(item)

    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8")
        for private in private_values:
            if private:
                require(private not in text, "private_material_in_evidence")
        check_text(text)
        if path.suffix == ".json":
            data = json.loads(text)
            require(
                isinstance(data, dict) and type(data.get("schema_version")) is int,
                "persisted_json_schema",
            )
            check_value(data)
        elif path.suffix in (".yaml", ".yml"):
            check_value(yaml.safe_load(text))


def verify_delta(delta: dict[str, Any]) -> list[str]:
    paths = [item["path"] for item in delta["changes"]]
    require(len(paths) == len(set(paths)), "duplicate_drift_path")
    changes = {item["path"]: item for item in delta["changes"] if item["severity"] != "NONE"}
    require(
        set(changes)
        == {"generation.max_tokens", "files.validation/eval.yaml.sha256", "code.commit"},
        "complete_drift_set",
    )
    require(
        changes["generation.max_tokens"]["a"] == 32
        and changes["generation.max_tokens"]["b"] == 48
        and changes["generation.max_tokens"]["severity"] == "HIGH",
        "target_drift",
    )
    require(
        changes["files.validation/eval.yaml.sha256"]["severity"] == "HIGH"
        and changes["code.commit"]["severity"] == "MEDIUM",
        "context_drift",
    )
    return sorted(changes)


def prepare_seed(seed: Path, recipe: Path) -> dict[str, Any]:
    expected = json.loads((recipe / "expected.json").read_text(encoding="utf-8"))
    for name, checksum in expected["sha256"].items():
        require(digest((recipe / name).read_bytes()) == checksum, "recipe_input_hash")
    shutil.copytree(recipe, seed)
    task = seed / "lm_eval/tasks/gsm8k/gsm8k.yaml"
    task.parent.mkdir(parents=True)
    shutil.copyfile(seed / "upstream/gsm8k.yaml", task)
    (seed / ".gitignore").write_text(
        ".reprollm/\noutputs/\nREPRODUCIBILITY.md\n", encoding="utf-8", newline="\n"
    )
    gen_quickstart._git(seed, "init", "-q", "-b", "a01-stdlib")
    gen_quickstart._git(seed, "config", "core.autocrlf", "false")
    gen_quickstart._git(seed, "add", "-A")
    gen_quickstart._git(seed, "commit", "-qm", "Prepare public stdlib replay inputs")
    return expected


def variant(case: Path, cap: int, recipe: Path, *, rewrite: bool) -> None:
    manifest = yaml.safe_load(
        (recipe / ("reprollm.yaml" if cap == 32 else "variants/reprollm-b.yaml")).read_bytes()
    )
    manifest["project"]["name"] = "a01-stdlib-replay"
    manifest["execution"]["command"] = " ".join(
        [*CHILD, *(["--rewrite-cap", "96"] if rewrite else [])]
    )
    (case / "reprollm.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, width=100), encoding="utf-8", newline="\n"
    )
    shutil.copyfile(
        recipe / ("validation/eval.yaml" if cap == 32 else "variants/eval-b.yaml"),
        case / "validation/eval.yaml",
    )


def clone_seed(seed: Path, case: Path) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "clone",
            "--no-hardlinks",
            "--quiet",
            str(seed),
            str(case),
        ],
        check=True,
        capture_output=True,
        env=gen_quickstart._env(),
    )


def replay(
    label: str,
    home: Path,
    seed: Path,
    wheel: Path,
    identity: dict[str, str],
    output: Path,
    recipe: Path,
    *,
    no_index: bool,
    find_links: list[Path],
) -> dict[str, Any]:
    home.mkdir(parents=True)
    private = home / "private"
    private.mkdir()
    case = home / "case"
    clone_seed(seed, case)
    gen_quickstart._git(case, "remote", "remove", "origin")
    gen_quickstart._git(case, "config", "core.autocrlf", "false")
    environment = home / "venv"
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    install = validate_distribution._install(
        python, wheel, home, no_index=no_index, find_links=find_links, raw_output_dir=private
    )
    require(install["exit_code"] == 0, "wheel_install")
    imports = validate_distribution._import_evidence(python, environment, home, identity, private)
    output.mkdir(parents=True)
    commands = []

    def on_step(step: gen_quickstart.Step) -> None:
        index = len(commands) + 1
        commands.append(validate_distribution.command_evidence(step))
        for stream in ("stdout", "stderr"):
            (private / f"{index:02d}.{stream}.txt").write_text(
                getattr(step, f"raw_{stream}") or "", encoding="utf-8", newline="\n"
            )

    def run(args: list[str], expected: int = 0) -> gen_quickstart.Step:
        step = gen_quickstart._run(args, case, python=python, on_step=on_step)
        require(step.exit_code == expected, "command_exit")
        return step

    rows = []
    for name, cap, rewrite in (
        ("a", 32, False),
        ("b", 48, False),
        ("consume-then-mutate", 32, True),
    ):
        variant(case, cap, recipe, rewrite=rewrite)
        manifest_bytes = (case / "reprollm.yaml").read_bytes()
        before = run(["audit", ".", "--format", "json", "--fail-on", "never"])
        run(["lock", ".", "--offline"])
        run(["lock", ".", "--check"])
        lock_bytes = (case / "reprollm.lock").read_bytes()
        lock = yaml.safe_load(lock_bytes)
        require(lock["manifest_sha256"] == "sha256:" + digest(manifest_bytes), "lock_manifest_hash")
        config_bytes = (case / "validation/eval.yaml").read_bytes()
        locked = {item["path"]: item for item in lock["files"]}
        require(
            locked["validation/eval.yaml"]["sha256"] == "sha256:" + digest(config_bytes),
            "lock_input_hash",
        )
        gen_quickstart._git(case, "add", "-A")
        gen_quickstart._git(case, "commit", "-qm", f"Declare stdlib {name}")
        before_runs = set(case.glob(".reprollm/runs/*/run.json"))
        child = [*CHILD, *(["--rewrite-cap", "96"] if rewrite else [])]
        run(["run", "--name", f"a01-{name}", "--capture-output", "--", *child])
        created = set(case.glob(".reprollm/runs/*/run.json")) - before_runs
        require(len(created) == 1, "unique_capture")
        path = created.pop()
        record = json.loads(path.read_bytes())
        require(record["code"]["dirty"] is rewrite, "expected_worktree_change")
        receipt_bytes = (case / "outputs/current/consumed.json").read_bytes()
        receipt = json.loads(receipt_bytes)
        checks = verify_capture(record, path.parent, receipt, recipe, cap, rewrite=rewrite)
        for key, original in (("manifest", manifest_bytes), ("lock", lock_bytes)):
            reference = record[key]
            require(reference["sha256"] == "sha256:" + digest(original), "document_hash")
            require(
                local_snapshot(path.parent, reference["snapshot"]).read_bytes() == original,
                "document_snapshot_bytes",
            )
        artifact = next(
            item for item in record["artifacts"] if item["path"] == "outputs/current/consumed.json"
        )
        require(
            artifact["sha256"] == "sha256:" + digest(receipt_bytes)
            and artifact["size_bytes"] == len(receipt_bytes),
            "output_hash",
        )
        after = run(["audit", ".", "--format", "json", "--fail-on", "never"])
        run(["export", ".", "--run", record["run_id"]])
        document = (case / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
        require(
            validate_distribution._export_has_cap(document, cap)
            and "Input consumption by the child is unverified." in document,
            "selected_export",
        )
        target = output / name
        shutil.copytree(path.parent, target / "run")
        (target / "consumed.json").write_bytes(receipt_bytes)
        (target / "lock.yaml").write_bytes(lock_bytes)
        (target / "REPRODUCIBILITY.md").write_bytes((case / "REPRODUCIBILITY.md").read_bytes())
        (target / "audit-before.json").write_text(
            before.report_json, encoding="utf-8", newline="\n"
        )
        (target / "audit-after.json").write_text(after.report_json, encoding="utf-8", newline="\n")
        self_diff = run(["diff", record["run_id"], record["run_id"], "--format", "json"])
        require(json.loads(self_diff.report_json)["changes"] == [], "self_diff")
        (target / "self-diff.json").write_text(
            self_diff.report_json, encoding="utf-8", newline="\n"
        )
        rows.append(
            {
                "name": name,
                "run_id": record["run_id"],
                "cap": cap,
                "checks": checks,
                "manifest_sha256": digest(manifest_bytes),
                "lock_sha256": digest(lock_bytes),
                "config_sha256": digest(config_bytes),
                "receipt_sha256": digest(receipt_bytes),
            }
        )
    pair = run(
        ["diff", rows[0]["run_id"], rows[1]["run_id"], "--format", "json", "--fail-on", "HIGH"], 1
    )
    delta = json.loads(pair.report_json)
    changes = verify_delta(delta)
    (output / "pair-diff.json").write_text(pair.report_json, encoding="utf-8", newline="\n")
    result = {
        "schema_version": 1,
        "status": "PASS",
        "case_id": "a01-stdlib-replay",
        "replay": label,
        "layer": "L2 stdlib only",
        "native_framework": "NOT_RUN",
        "installation": install,
        "imports": imports,
        "captures": rows,
        "commands": commands,
        "non_none_drift_paths": changes,
    }
    write_json(output / "results.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--build-manifest", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--no-index", action="store_true")
    parser.add_argument("--find-links", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    started = time.monotonic()
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "FAIL",
        "layer": "L2 stdlib only",
        "native_framework": "NOT_RUN",
    }
    try:
        work = args.work_root.absolute()
        destination = args.output_dir.absolute()
        require(
            not work.resolve().is_relative_to(ROOT.resolve()) and not work.exists(),
            "new_external_work_root",
        )
        require(
            not destination.exists() or not any(destination.iterdir()), "empty_output_directory"
        )
        identity = validate_distribution.inspect_wheel(args.wheel)
        provenance = validate_distribution.source_provenance(identity, args.build_manifest)
        work.mkdir(parents=True)
        output = work / "shareable"
        output.mkdir()
        shutil.copyfile(args.build_manifest, output / "build-manifest.json")
        expected = json.loads((RECIPE / "expected.json").read_text(encoding="utf-8"))
        packet = output / "recipe"
        for name in ["expected.json", *sorted(expected["sha256"])]:
            target = packet / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(RECIPE / name, target)
        (packet / "README.md").write_text(
            "# Public stdlib replay inputs\n\n"
            "These are the unchanged D01 inputs and independent hash registry. "
            "The A01 runner adapts only the disposable manifest's name and command. "
            "Follow [the replay guide](../../replay-guide.md); "
            "no model or GPU execution is claimed.\n",
            encoding="utf-8",
            newline="\n",
        )
        independent = work / "shared-package-copy"
        shutil.copytree(packet, independent)
        rows = []
        for label, recipe in (("first", packet), ("second", independent)):
            recovered = prepare_seed(work / f"seed-{label}", recipe)
            require(recovered == expected, "independent_input_identity")
            rows.append(
                replay(
                    label,
                    work / label,
                    work / f"seed-{label}",
                    args.wheel.absolute(),
                    identity,
                    output / label,
                    recipe,
                    no_index=args.no_index,
                    find_links=args.find_links,
                )
            )
        require(
            rows[0]["non_none_drift_paths"] == rows[1]["non_none_drift_paths"],
            "independent_replay_drift",
        )
        identities = [os.environ.get(name, "") for name in ("USERNAME", "COMPUTERNAME")]
        assert_portable(output, [str(work), str(ROOT), *identities])
        result.update(
            {
                "status": "PASS",
                "wheel": identity,
                "build_provenance": provenance,
                "recipe_framework": expected["framework"],
                "input_sha256": expected["sha256"],
                "independent_replays": 2,
                "second_input_source": "independent copy of the public replay/recipe package",
                "tool_sha256": {
                    name: digest((ROOT / name).read_bytes())
                    for name in (
                        "scripts/a01_local_replay.py",
                        "scripts/gen_quickstart.py",
                        "scripts/validate_distribution.py",
                        "scripts/check_no_leaks.py",
                        "src/reprollm/core/redaction.py",
                    )
                },
                "elapsed_seconds": round(time.monotonic() - started, 6),
            }
        )
        write_json(output / "summary.json", result)
        sums = [
            f"{digest(path.read_bytes())}  {path.relative_to(output).as_posix()}"
            for path in sorted(output.rglob("*"))
            if path.is_file()
        ]
        (output / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
        assert_portable(output, [str(work), str(ROOT), *identities])
        shutil.copytree(output, destination, dirs_exist_ok=True)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result["status"] = "FAIL"
        result["error_type"] = type(exc).__name__
        if args.work_root.exists():
            (args.work_root / "failure.private.txt").write_text(
                traceback.format_exc(), encoding="utf-8", newline="\n"
            )
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
