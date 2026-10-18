"""Offline D03 decisions: bind release notes, validation and distributions to one commit.

This tool never builds, contacts a provider, creates a tag or publishes a package.
The workflow supplies authenticated validation artifacts and the quality-job result.
"""

from __future__ import annotations

import argparse
import ast
import email.parser
import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Any

if __package__:
    from . import validate_distribution
else:
    import validate_distribution  # type: ignore[import-not-found, no-redef]

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (
    "lm-evaluation-harness",
    "FastChat",
    "LlamaFactory",
    "HarmBench",
    "llm-dp-finetune",
)
REQUIRED_GATES = tuple(
    f"{group}:{project}"
    for group in ("gate_a", "m4_metadata", "runtime_pair", "export", "discover_collection")
    for project in PROJECTS
) + ("api_judge", "discover_live", "hf_gated")
DISTRIBUTION_CHECKS = (
    "twelve_step_workflow",
    "command_exit_codes",
    "audit_levels",
    "offline_locks",
    "capture_values",
    "semantic_cap_drift",
    "export_selected_run",
    "all_builtin_profiles",
    "all_schema_exports",
    "template_default",
    "template_neurips",
    "template_acl",
    "template_acm",
)


class GateFailure(ValueError):
    """Only fixed identifiers enter portable failure reports."""


def require(condition: bool, identifier: str) -> None:
    if not condition:
        raise GateFailure(identifier)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return _stream_hash(stream)


def _stream_hash(stream: Any) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def document(path: Path) -> dict[str, Any]:
    require(path.stat().st_size <= 8 * 1024 * 1024, "evidence_size")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    require(isinstance(value, dict), "evidence_document")
    require(
        type(value.get("schema_version")) is int and value["schema_version"] == 1, "evidence_schema"
    )
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def target(root: Path, commit: str, tag: str) -> str:
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "source_commit")
    module = ast.parse((root / "src/reprollm/__init__.py").read_text(encoding="utf-8"))
    values = [
        node.value.value
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(name, ast.Name) and name.id == "__version__" for name in node.targets)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]
    require(len(values) == 1, "source_version")
    version = values[0]
    require(re.fullmatch(r"[0-9][A-Za-z0-9.!+_-]*", version) is not None, "source_version")
    require(tag == f"v{version}", "tag_version")
    return version


def release_notes(root: Path, version: str) -> str:
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = list(re.finditer(r"^## \[([^\]\r\n]+)\][^\r\n]*$", text, re.MULTILINE))
    matches = [index for index, item in enumerate(headings) if item.group(1) == version]
    require(len(matches) == 1, "release_notes_section")
    index = matches[0]
    end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
    body = text[headings[index].end() : end]
    body = re.sub(r"(?m)^\[[^\]]+\]:[^\n]*$", "", body).strip()
    require(bool(re.sub(r"(?m)^\s*#+[^\n]*$", "", body).strip()), "release_notes_empty")
    return body + "\n"


def referenced_file(base: Path, reference: Any) -> Path:
    require(isinstance(reference, dict), "evidence_reference")
    name, digest = reference.get("path"), reference.get("sha256")
    require(
        isinstance(name, str) and bool(name) and "\\" not in name and ":" not in name,
        "evidence_path",
    )
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts, "evidence_path")
    resolved = (base / path).resolve()
    require(resolved.is_relative_to(base.resolve()) and resolved.is_file(), "evidence_path")
    require(
        isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
        "evidence_hash",
    )
    require(sha256(resolved) == digest, "evidence_hash")
    return resolved


def validation_evidence(base: Path, commit: str) -> dict[str, Any]:
    summary = document(base / "validation.json")
    require(summary.get("source_commit") == commit, "validation_commit")
    gates = summary.get("gates")
    require(isinstance(gates, list), "validation_matrix")
    require(len(gates) == len(REQUIRED_GATES), "validation_matrix")
    identifiers = [item.get("id") if isinstance(item, dict) else None for item in gates]
    require(all(isinstance(item, str) for item in identifiers), "validation_matrix")
    require(set(identifiers) == set(REQUIRED_GATES), "validation_matrix")
    for gate in gates:
        require(gate.get("status") == "PASS", "validation_status")
        require(gate.get("source_commit") == commit, "validation_commit")
        inputs = gate.get("inputs")
        require(isinstance(inputs, list) and bool(inputs), "validation_inputs")
        for reference in inputs:
            referenced_file(base, reference)
        report = document(referenced_file(base, gate.get("report")))
        require(report.get("source_commit") == commit, "report_commit")
        require(
            report.get("gate_id") == gate["id"] and report.get("status") == "PASS", "report_status"
        )
    return {"sha256": sha256(base / "validation.json"), "gate_count": len(gates)}


def validation_run(path: Path, commit: str, repository: str | None) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    require(isinstance(data, dict), "validation_run")
    require(data.get("head_sha") == commit, "validation_run_commit")
    require(
        data.get("status") == "completed" and data.get("conclusion") == "success",
        "validation_run_status",
    )
    require(isinstance(repository, str) and bool(repository), "validation_run_repository")
    require(
        isinstance(data.get("repository"), dict)
        and isinstance(data.get("head_repository"), dict)
        and data["repository"].get("full_name") == repository
        and data.get("head_repository", {}).get("full_name") == repository,
        "validation_run_repository",
    )
    require(type(data.get("id")) is int and data["id"] > 0, "validation_run_id")
    return {"run_id": data["id"], "source_commit": commit, "status": "PASS"}


def preflight(
    root: Path,
    commit: str,
    tag: str,
    validation_dir: Path,
    output_dir: Path,
    *,
    run: Path | None = None,
    repository: str | None = None,
) -> dict[str, Any]:
    version = target(root, commit, tag)
    notes = release_notes(root, version)
    validation = validation_evidence(validation_dir, commit)
    result = {
        "schema_version": 1,
        "status": "PASS",
        "source_commit": commit,
        "version": version,
        "tag": tag,
        "validation": validation,
        "notes_sha256": hashlib.sha256(notes.encode("utf-8")).hexdigest(),
    }
    if run is not None:
        result["validation_run"] = validation_run(run, commit, repository)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "release-notes.md").write_text(notes, encoding="utf-8", newline="\n")
    write_json(output_dir / "preflight.json", result)
    return result


def artifacts(dist: Path, version: str) -> list[dict[str, Any]]:
    files = sorted(dist.iterdir())
    require(
        len(files) == 2 and all(path.is_file() and not path.is_symlink() for path in files),
        "distribution_files",
    )
    wheels = [path for path in files if path.name.endswith(".whl")]
    sources = [path for path in files if path.name == f"reprollm-{version}.tar.gz"]
    require(len(wheels) == 1 and len(sources) == 1, "distribution_files")
    identity = validate_distribution.inspect_wheel(wheels[0])
    require(identity["version"] == version, "distribution_version")
    with tarfile.open(sources[0], "r:gz") as archive:
        names = [
            member
            for member in archive.getmembers()
            if member.name == f"reprollm-{version}/PKG-INFO" and member.isfile()
        ]
        require(len(names) == 1 and names[0].size <= 1024 * 1024, "sdist_metadata")
        stream = archive.extractfile(names[0])
        require(stream is not None, "sdist_metadata")
        metadata = email.parser.BytesParser().parsebytes(stream.read())
    require(
        metadata.get_all("Name") == ["reprollm"] and metadata.get_all("Version") == [version],
        "sdist_metadata",
    )
    return [
        {"filename": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size}
        for path in files
    ]


def build_manifest(root: Path, commit: str, tag: str, dist: Path) -> dict[str, Any]:
    version = target(root, commit, tag)
    return {
        "schema_version": 1,
        "source_commit": commit,
        "version": version,
        "tag": tag,
        "artifacts": artifacts(dist, version),
    }


def authorize(
    root: Path,
    commit: str,
    tag: str,
    quality_result: str,
    dist: Path,
    validation_dir: Path,
    evidence_dir: Path,
    distribution: Path,
) -> dict[str, Any]:
    require(quality_result == "success", "quality_result")
    version = target(root, commit, tag)
    before = document(evidence_dir / "preflight.json")
    require(
        before.get("status") == "PASS"
        and before.get("source_commit") == commit
        and before.get("tag") == tag
        and before.get("version") == version,
        "preflight_binding",
    )
    notes_path = evidence_dir / "release-notes.md"
    notes = release_notes(root, version)
    require(
        notes_path.read_bytes() == notes.encode("utf-8")
        and sha256(notes_path) == before.get("notes_sha256"),
        "release_notes_hash",
    )
    validation = validation_evidence(validation_dir, commit)
    require(validation == before.get("validation"), "validation_changed")
    manifest_path = evidence_dir / "build-manifest.json"
    manifest = document(manifest_path)
    actual = build_manifest(root, commit, tag, dist)
    require(manifest == actual, "build_manifest_binding")
    summary = document(distribution)
    require(summary.get("status") == "PASS", "distribution_status")
    wheel = next(path for path in dist.iterdir() if path.name.endswith(".whl"))
    identity = validate_distribution.inspect_wheel(wheel)
    require(summary.get("wheel") == identity, "distribution_wheel")
    provenance = validate_distribution.source_provenance(identity, manifest_path)
    require(
        summary.get("provenance") == provenance and provenance["source_commit"] == commit,
        "distribution_provenance",
    )
    imports = summary.get("imports", {})
    require(
        isinstance(imports, dict)
        and imports.get("isolated") is True
        and imports.get("archive_sha256") == identity["sha256"]
        and imports.get("distribution_version") == version
        and imports.get("code_version") == version
        and imports.get("user_site_enabled") is False
        and imports.get("editable") is False,
        "distribution_isolation",
    )
    installation = summary.get("installation")
    require(
        isinstance(installation, dict)
        and type(installation.get("exit_code")) is int
        and installation["exit_code"] == 0,
        "distribution_installation",
    )
    commands = summary.get("commands")
    require(isinstance(commands, list) and len(commands) == 26, "distribution_commands")
    command_names = [
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
        *(["profiles"] * 9),
        "schema",
        *(["export"] * 4),
    ]
    command_exits = [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0] + [0] * 14
    for receipt, name, code in zip(commands, command_names, command_exits, strict=True):
        require(isinstance(receipt, dict), "distribution_commands")
        command = receipt.get("command")
        require(
            isinstance(command, list)
            and bool(command)
            and command[0] == name
            and all(isinstance(part, str) for part in command)
            and type(receipt.get("exit_code")) is int
            and receipt["exit_code"] == code
            and receipt.get("executable") == "<venv-python>"
            and all(
                isinstance(receipt.get(f"{stream}_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", receipt[f"{stream}_sha256"]) is not None
                for stream in ("stdout", "stderr")
            ),
            "distribution_commands",
        )
    checks = summary.get("checks")
    require(
        isinstance(checks, list) and len(checks) == len(DISTRIBUTION_CHECKS), "distribution_checks"
    )
    require(
        all(isinstance(check, dict) and check.get("passed") is True for check in checks),
        "distribution_checks",
    )
    require(
        {check.get("id") for check in checks} == set(DISTRIBUTION_CHECKS), "distribution_checks"
    )
    return {
        "schema_version": 1,
        "status": "PASS",
        "source_commit": commit,
        "version": version,
        "tag": tag,
        "quality_result": quality_result,
        "artifacts": actual["artifacts"],
        "notes_sha256": sha256(notes_path),
        "preflight_sha256": sha256(evidence_dir / "preflight.json"),
        "build_manifest_sha256": sha256(manifest_path),
        "distribution_sha256": sha256(distribution),
        "validation_sha256": validation["sha256"],
        "validation_gate_count": validation["gate_count"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="stage", required=True)
    pre = subparsers.add_parser("preflight")
    pre.add_argument("--validation-dir", type=Path, required=True)
    pre.add_argument("--validation-run", type=Path)
    pre.add_argument("--repository")
    pre.add_argument("--output-dir", type=Path, required=True)
    build = subparsers.add_parser("build-manifest")
    build.add_argument("--dist", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    auth = subparsers.add_parser("authorize")
    auth.add_argument("--quality-result", required=True)
    auth.add_argument("--dist", type=Path, required=True)
    auth.add_argument("--validation-dir", type=Path, required=True)
    auth.add_argument("--evidence-dir", type=Path, required=True)
    auth.add_argument("--distribution", type=Path, required=True)
    for command in (pre, build, auth):
        command.add_argument("--commit", required=True)
        command.add_argument("--tag", required=True)
    args = parser.parse_args(argv)
    try:
        checkout = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
        require(checkout == args.commit, "checkout_commit")
        if args.stage == "preflight":
            result = preflight(
                ROOT,
                args.commit,
                args.tag,
                args.validation_dir,
                args.output_dir,
                run=args.validation_run,
                repository=args.repository,
            )
        elif args.stage == "build-manifest":
            result = build_manifest(ROOT, args.commit, args.tag, args.dist)
            write_json(args.output, result)
        else:
            result = authorize(
                ROOT,
                args.commit,
                args.tag,
                args.quality_result,
                args.dist,
                args.validation_dir,
                args.evidence_dir,
                args.distribution,
            )
            write_json(args.evidence_dir / "publish-authorization.json", result)
    except GateFailure as exc:
        result = {"schema_version": 1, "status": "FAIL", "failure": str(exc)}
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        SyntaxError,
        tarfile.TarError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        result = {
            "schema_version": 1,
            "status": "FAIL",
            "failure": "invalid_release_input",
            "error_type": type(exc).__name__,
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return (
        0
        if result.get("status") == "PASS"
        or args.stage == "build-manifest"
        and ("artifacts" in result and "failure" not in result)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
