from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.core.hashing import sha256_file
from reprollm.rules.consistency import FileHashesRule, LockFreshRule
from reprollm.schemas.finding import Severity
from reprollm.schemas.lock import FileEntry, Lock, PromptLock, ResolutionMode


def _lock(
    *,
    manifest_sha256: str = "sha256:manifest",
    project_rules_sha256: str | None = None,
    prompts: dict[str, PromptLock] | None = None,
    files: list[FileEntry] | None = None,
) -> Lock:
    return Lock(
        reprollm_version="0.1.1",
        generated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        manifest_sha256=manifest_sha256,
        project_rules_sha256=project_rules_sha256,
        resolution=ResolutionMode(mode="offline"),
        prompts=prompts or {},
        files=files or [],
    )


def test_lock_fresh_passes_when_both_hashes_match(tmp_path: Path) -> None:
    manifest = tmp_path / "reprollm.yaml"
    manifest.write_text("manifest\n", encoding="utf-8")
    rules = tmp_path / ".reprollm/project-rules.yaml"
    rules.parent.mkdir()
    rules.write_text("rules\n", encoding="utf-8")
    lock = _lock(
        manifest_sha256=sha256_file(manifest),
        project_rules_sha256=sha256_file(rules),
    )

    assert LockFreshRule().check(AuditContext(tmp_path, level=2, lock=lock)) == []


def test_lock_fresh_emits_one_finding_per_changed_source(tmp_path: Path) -> None:
    manifest = tmp_path / "reprollm.yaml"
    manifest.write_text("current manifest\n", encoding="utf-8")
    rules = tmp_path / ".reprollm/project-rules.yaml"
    rules.parent.mkdir()
    rules.write_text("current rules\n", encoding="utf-8")
    ctx = AuditContext(
        tmp_path,
        level=2,
        lock=_lock(manifest_sha256="sha256:old", project_rules_sha256="sha256:old"),
    )

    findings = LockFreshRule().check(ctx)

    assert len(findings) == 2
    assert {finding.message for finding in findings} == {
        "reprollm.yaml changed after reprollm.lock was generated",
        ".reprollm/project-rules.yaml changed after reprollm.lock was generated",
    }
    assert all(finding.severity == Severity.WARNING for finding in findings)
    assert {finding.evidence[0].field for finding in findings} == {
        "manifest_sha256",
        "project_rules_sha256",
    }


def test_file_hashes_pass_for_unchanged_prompt_and_declared_file(tmp_path: Path) -> None:
    prompt = tmp_path / "prompts/system.txt"
    config = tmp_path / "configs/eval.yaml"
    prompt.parent.mkdir()
    config.parent.mkdir()
    prompt.write_text("prompt\n", encoding="utf-8")
    config.write_text("temperature: 0\n", encoding="utf-8")
    lock = _lock(
        prompts={
            "system": PromptLock(
                path="prompts/system.txt",
                sha256=sha256_file(prompt),
                size_bytes=prompt.stat().st_size,
            )
        },
        files=[
            FileEntry(
                path="configs/eval.yaml",
                sha256=sha256_file(config),
                size_bytes=config.stat().st_size,
            )
        ],
    )

    assert FileHashesRule().check(AuditContext(tmp_path, level=2, lock=lock)) == []


def test_file_hashes_reports_changed_file_with_lock_and_current_values(tmp_path: Path) -> None:
    prompt = tmp_path / "prompts/system.txt"
    prompt.parent.mkdir()
    prompt.write_text("before\n", encoding="utf-8")
    locked_hash = sha256_file(prompt)
    lock = _lock(
        prompts={
            "system": PromptLock(
                path="prompts/system.txt",
                sha256=locked_hash,
                size_bytes=prompt.stat().st_size,
            )
        }
    )
    prompt.write_text("after\n", encoding="utf-8")

    findings = FileHashesRule().check(AuditContext(tmp_path, level=2, lock=lock))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.message == "prompts/system.txt content differs from reprollm.lock"
    assert finding.evidence[0].path == "prompts/system.txt"
    assert finding.evidence[0].expected == locked_hash
    assert finding.evidence[0].value == sha256_file(prompt)


def test_file_hashes_reports_missing_file_separately(tmp_path: Path) -> None:
    lock = _lock(
        files=[
            FileEntry(
                path="configs/missing.yaml",
                sha256="sha256:locked",
                size_bytes=10,
            )
        ]
    )

    findings = FileHashesRule().check(AuditContext(tmp_path, level=2, lock=lock))

    assert len(findings) == 1
    assert findings[0].message == "configs/missing.yaml is missing from the working tree"
    assert findings[0].evidence[0].expected == "sha256:locked"
    assert findings[0].evidence[0].value is None


def test_file_hashes_refuses_escaping_lock_path(tmp_path: Path) -> None:
    lock = _lock(files=[FileEntry(path="../outside.txt", sha256="sha256:locked", size_bytes=1)])

    findings = FileHashesRule().check(AuditContext(tmp_path, level=2, lock=lock))

    assert len(findings) == 1
    assert "invalid path" in findings[0].message
    assert findings[0].evidence[0].path is None
    assert findings[0].evidence[0].field == "files[0].path"
