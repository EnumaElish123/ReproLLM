from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from reprollm.core.errors import UserError
from reprollm.lock.writer import check_lock, write_lock
from reprollm.schemas.lock import Lock, ResolutionMode


def _lock() -> Lock:
    return Lock(
        reprollm_version="0.1.1",
        generated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        manifest_sha256="sha256:manifest",
        resolution=ResolutionMode(mode="offline"),
    )


def test_atomic_write_preserves_existing_lock_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "reprollm.lock"
    target.write_text("old lock\n", encoding="utf-8")
    monkeypatch.setattr(
        "reprollm.lock.writer.os.replace", lambda *_: (_ for _ in ()).throw(OSError("boom"))
    )

    with pytest.raises(UserError, match="cannot write reprollm.lock"):
        write_lock(target, _lock())

    assert target.read_text(encoding="utf-8") == "old lock\n"
    assert list(tmp_path.glob(".reprollm.lock.*.tmp")) == []


def test_check_lock_compares_both_source_hashes(tmp_path: Path) -> None:
    manifest = tmp_path / "reprollm.yaml"
    manifest.write_text("manifest\n", encoding="utf-8")
    rules = tmp_path / ".reprollm/project-rules.yaml"
    rules.parent.mkdir()
    rules.write_text("rules\n", encoding="utf-8")
    lock = _lock().model_copy(
        update={"manifest_sha256": "wrong", "project_rules_sha256": "also-wrong"}
    )
    write_lock(tmp_path / "reprollm.lock", lock)

    reasons = check_lock(tmp_path)

    assert reasons == ["reprollm.yaml changed", ".reprollm/project-rules.yaml changed"]
