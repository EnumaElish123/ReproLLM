"""D03: exercise the actual release decisions without publishing anything."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest
from scripts import release_gate

COMMIT = "a" * 40
TAG = "v0.7.0"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def reference(base: Path, name: str, content: bytes) -> dict[str, str]:
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {"path": name, "sha256": hashlib.sha256(content).hexdigest()}


@pytest.fixture
def candidate(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    version = root / "src/reprollm/__init__.py"
    version.parent.mkdir(parents=True)
    version.write_text('__version__ = "0.7.0"\n', encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\nPending.\n\n"
        "## [0.7.0] - 2026-10-18\n\n### Fixed\n\nPreserve inputs.\n\n"
        "## [0.6.1]\n\nOld notes.\n",
        encoding="utf-8",
    )
    validation = root / "validation"
    gates = []
    for gate_id in release_gate.REQUIRED_GATES:
        label = gate_id.replace(":", "-")
        report = {
            "schema_version": 1,
            "source_commit": COMMIT,
            "gate_id": gate_id,
            "status": "PASS",
        }
        gates.append(
            {
                "id": gate_id,
                "source_commit": COMMIT,
                "status": "PASS",
                "inputs": [reference(validation, f"inputs/{label}.txt", b"reviewed input\n")],
                "report": reference(
                    validation, f"reports/{label}.json", json.dumps(report).encode()
                ),
            }
        )
    write_json(
        validation / "validation.json",
        {
            "schema_version": 1,
            "source_commit": COMMIT,
            "gates": gates,
        },
    )
    dist = root / "dist"
    dist.mkdir()
    metadata = b"Metadata-Version: 2.1\nName: reprollm\nVersion: 0.7.0\n"
    with zipfile.ZipFile(dist / "reprollm-0.7.0-py3-none-any.whl", "w") as wheel:
        wheel.writestr("reprollm-0.7.0.dist-info/METADATA", metadata)
    with tarfile.open(dist / "reprollm-0.7.0.tar.gz", "w:gz") as archive:
        info = tarfile.TarInfo("reprollm-0.7.0/PKG-INFO")
        info.size = len(metadata)
        archive.addfile(info, io.BytesIO(metadata))
    return root


def prepare(root: Path) -> None:
    release_gate.preflight(root, COMMIT, TAG, root / "validation", root / "evidence")
    manifest = release_gate.build_manifest(root, COMMIT, TAG, root / "dist")
    write_json(root / "evidence/build-manifest.json", manifest)
    wheel = next((root / "dist").glob("*.whl"))
    identity = release_gate.validate_distribution.inspect_wheel(wheel)
    write_json(
        root / "evidence/distribution.json",
        {
            "schema_version": 1,
            "status": "PASS",
            "wheel": identity,
            "provenance": release_gate.validate_distribution.source_provenance(
                identity, root / "evidence/build-manifest.json"
            ),
            "installation": {"exit_code": 0},
            "imports": {
                "isolated": True,
                "archive_sha256": identity["sha256"],
                "distribution_version": "0.7.0",
                "code_version": "0.7.0",
                "editable": False,
                "user_site_enabled": False,
            },
            "commands": [
                {
                    "command": [name],
                    "exit_code": code,
                    "executable": "<venv-python>",
                    "stdout_sha256": "a" * 64,
                    "stderr_sha256": "b" * 64,
                }
                for name, code in zip(
                    [
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
                    ],
                    [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0] + [0] * 14,
                    strict=True,
                )
            ],
            "checks": [{"id": name, "passed": True} for name in release_gate.DISTRIBUTION_CHECKS],
        },
    )


def authorize(root: Path, quality: str = "success") -> dict:
    return release_gate.authorize(
        root,
        COMMIT,
        TAG,
        quality,
        root / "dist",
        root / "validation",
        root / "evidence",
        root / "evidence/distribution.json",
    )


def test_all_gates_bind_one_commit_one_build_and_preflight_notes(candidate: Path) -> None:
    prepare(candidate)
    result = authorize(candidate)
    assert result["status"] == "PASS"
    assert result["source_commit"] == COMMIT
    assert result["version"] == "0.7.0"
    assert len(result["artifacts"]) == 2
    assert (
        result["notes_sha256"]
        == hashlib.sha256((candidate / "evidence/release-notes.md").read_bytes()).hexdigest()
    )
    assert result["validation_gate_count"] == 28


@pytest.mark.parametrize("content", [b"*", b"*\n", b"*\r\n"])
def test_uv_dist_marker_keeps_exact_package_manifest_and_download_authorization(
    candidate: Path, content: bytes
) -> None:
    expected = release_gate.build_manifest(candidate, COMMIT, TAG, candidate / "dist")
    marker = candidate / "dist/.gitignore"
    marker.write_bytes(content)
    prepare(candidate)
    manifest = json.loads((candidate / "evidence/build-manifest.json").read_text())
    assert manifest == expected
    assert len(manifest["artifacts"]) == 2
    assert {row["filename"] for row in manifest["artifacts"]} == {
        "reprollm-0.7.0-py3-none-any.whl",
        "reprollm-0.7.0.tar.gz",
    }
    for artifact in manifest["artifacts"]:
        package = candidate / "dist" / artifact["filename"]
        assert artifact["sha256"] == hashlib.sha256(package.read_bytes()).hexdigest()
    result = authorize(candidate)
    assert result["status"] == "PASS"
    marker.unlink()
    assert authorize(candidate) == result


@pytest.mark.parametrize("content", [b"", b"!\n", b"**", b"*\n\n", b"*\nextra"])
def test_dist_rejects_unexpected_marker_contents(candidate: Path, content: bytes) -> None:
    (candidate / "dist/.gitignore").write_bytes(content)
    with pytest.raises(release_gate.GateFailure):
        release_gate.build_manifest(candidate, COMMIT, TAG, candidate / "dist")


def test_dist_rejects_marker_directory(candidate: Path) -> None:
    (candidate / "dist/.gitignore").mkdir()
    with pytest.raises(release_gate.GateFailure):
        release_gate.build_manifest(candidate, COMMIT, TAG, candidate / "dist")


@pytest.mark.parametrize("name", [".gitkeep", ".env"])
def test_dist_does_not_ignore_other_hidden_files(candidate: Path, name: str) -> None:
    (candidate / "dist" / name).write_bytes(b"*")
    with pytest.raises(release_gate.GateFailure, match="distribution_files"):
        release_gate.build_manifest(candidate, COMMIT, TAG, candidate / "dist")


@pytest.mark.parametrize("kind", ["missing", "blank", "duplicate", "wrong-version"])
def test_bad_changelog_or_tag_fails_before_build(candidate: Path, kind: str) -> None:
    path = candidate / "CHANGELOG.md"
    if kind == "missing":
        path.write_text("## [Unreleased]\nNo version.\n", encoding="utf-8")
    elif kind == "blank":
        path.write_text("## [0.7.0]\n \n## [0.6.1]\nOld.\n", encoding="utf-8")
    elif kind == "duplicate":
        path.write_text("## [0.7.0]\nFirst.\n## [0.7.0]\nOther.\n", encoding="utf-8")
    with pytest.raises(release_gate.GateFailure):
        release_gate.preflight(
            candidate,
            COMMIT,
            "v0.6.1" if kind == "wrong-version" else TAG,
            candidate / "validation",
            candidate / "evidence",
        )
    assert not (candidate / "evidence/preflight.json").exists()


@pytest.mark.parametrize(
    "kind",
    [
        "blocked",
        "missing-gate",
        "duplicate-gate",
        "old-sha",
        "old-report-sha",
        "missing-report",
        "changed-report",
        "changed-input",
        "no-inputs",
        "escaping-input",
        "bool-schema",
        "empty-matrix",
    ],
)
def test_resource_evidence_cannot_silently_skip_or_reuse_old_results(
    candidate: Path, kind: str
) -> None:
    base = candidate / "validation"
    path = base / "validation.json"
    data = json.loads(path.read_text())
    first = data["gates"][0]
    if kind == "blocked":
        first["status"] = "BLOCKED"
    elif kind == "missing-gate":
        data["gates"].pop()
    elif kind == "duplicate-gate":
        data["gates"].append(first)
    elif kind == "old-sha":
        first["source_commit"] = "b" * 40
    elif kind == "old-report-sha":
        report = json.loads((base / first["report"]["path"]).read_text())
        report["source_commit"] = "b" * 40
        first["report"] = reference(base, first["report"]["path"], json.dumps(report).encode())
    elif kind == "missing-report":
        (base / first["report"]["path"]).unlink()
    elif kind == "changed-report":
        (base / first["report"]["path"]).write_bytes(b"changed")
    elif kind == "changed-input":
        (base / first["inputs"][0]["path"]).write_bytes(b"changed")
    elif kind == "no-inputs":
        first["inputs"] = []
    elif kind == "escaping-input":
        first["inputs"][0]["path"] = "../outside.txt"
    elif kind == "bool-schema":
        data["schema_version"] = True
    else:
        data["gates"] = []
    write_json(path, data)
    with pytest.raises(release_gate.GateFailure):
        release_gate.preflight(candidate, COMMIT, TAG, base, candidate / "evidence")


@pytest.mark.parametrize("quality", ["failure", "cancelled", "skipped", "", "pending"])
def test_failed_cancelled_or_missing_quality_never_authorizes_publish(
    candidate: Path, quality: str
) -> None:
    prepare(candidate)
    with pytest.raises(release_gate.GateFailure, match="quality"):
        authorize(candidate, quality)


@pytest.mark.parametrize(
    "kind",
    [
        "wheel",
        "sdist",
        "extra-dist",
        "notes",
        "manifest-sha",
        "distribution-fail",
        "distribution-sha",
        "distribution-source",
        "distribution-check",
        "resources",
    ],
)
def test_final_boundary_revalidates_artifacts_and_all_prior_results(
    candidate: Path, kind: str
) -> None:
    prepare(candidate)
    evidence = candidate / "evidence"
    summary_path = evidence / "distribution.json"
    summary = json.loads(summary_path.read_text())
    if kind in {"wheel", "sdist"}:
        artifact = next((candidate / "dist").glob("*.whl" if kind == "wheel" else "*.tar.gz"))
        artifact.write_bytes(artifact.read_bytes() + b"tamper")
    elif kind == "extra-dist":
        (candidate / "dist/unvalidated.json").write_text("{}")
    elif kind == "notes":
        (evidence / "release-notes.md").write_text("Different notes.")
    elif kind == "manifest-sha":
        manifest = json.loads((evidence / "build-manifest.json").read_text())
        manifest["source_commit"] = "b" * 40
        write_json(evidence / "build-manifest.json", manifest)
    elif kind == "distribution-fail":
        summary["status"] = "FAIL"
    elif kind == "distribution-sha":
        summary["wheel"]["sha256"] = "b" * 64
    elif kind == "distribution-source":
        summary["provenance"]["source_commit"] = "b" * 40
    elif kind == "distribution-check":
        summary["checks"].pop()
    else:
        validation = json.loads((candidate / "validation/validation.json").read_text())
        validation["gates"][-1]["status"] = "BLOCKED"
        write_json(candidate / "validation/validation.json", validation)
    write_json(summary_path, summary)
    with pytest.raises(release_gate.GateFailure):
        authorize(candidate)


def test_cli_rejects_wrong_source_sha_with_portable_json(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/release_gate.py"),
            "preflight",
            "--commit",
            COMMIT,
            "--tag",
            TAG,
            "--validation-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
    )
    assert result.returncode == 1
    document = json.loads(result.stdout)
    assert document["status"] == "FAIL"
    assert document["failure"] == "checkout_commit"
    assert str(tmp_path) not in result.stdout + result.stderr


@pytest.mark.parametrize("change", ["null", "exit", "command", "executable", "hash"])
def test_distribution_command_receipts_cannot_be_replaced_by_length_only(
    candidate: Path, change: str
) -> None:
    prepare(candidate)
    path = candidate / "evidence/distribution.json"
    summary = json.loads(path.read_text())
    if change == "null":
        summary["commands"][0] = None
    elif change == "exit":
        summary["commands"][0]["exit_code"] = 99
    elif change == "command":
        summary["commands"][0]["command"] = ["--help"]
    elif change == "executable":
        summary["commands"][0]["executable"] = "<source-python>"
    else:
        summary["commands"][0]["stdout_sha256"] = "missing"
    write_json(path, summary)
    with pytest.raises(release_gate.GateFailure, match="distribution_commands"):
        authorize(candidate)


@pytest.mark.parametrize("field", ["repository", "head_repository"])
def test_validation_run_null_repository_is_rejected_safely(tmp_path: Path, field: str) -> None:
    path = tmp_path / "run.json"
    payload = {
        "id": 1,
        "head_sha": COMMIT,
        "status": "completed",
        "conclusion": "success",
        "repository": {"full_name": "owner/reprollm"},
        "head_repository": {"full_name": "owner/reprollm"},
    }
    payload[field] = None
    write_json(path, payload)
    with pytest.raises(release_gate.GateFailure):
        release_gate.validation_run(path, COMMIT, "owner/reprollm")
