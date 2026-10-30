"""SK15 native I/O and guarded publication preserve original artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from tests.unit.skills import test_skill_local_lifecycle as draft

from reprollm.core import rule_lifecycle
from reprollm.lock import writer
from reprollm.schemas.rule_archive import RuleArchive

call = draft.call
checked = draft.checked
read_rules = draft.read_rules
writes = __import__("skill_writes")


@pytest.fixture(autouse=True)
def no_external_effects(monkeypatch):
    draft.no_external_effects.__wrapped__(monkeypatch)


@pytest.fixture
def project(tmp_path):
    return draft.project.__wrapped__(tmp_path)


def add(root, state):
    checked(
        call(
            root, state, "rules.add", field="custom.alpha", severity="WARNING", reason="Keep alpha."
        )
    )


def archives(root):
    return sorted((root / ".reprollm/rule-archives").glob("*.json"))


@pytest.mark.parametrize("change", ["manifest", "rules", "weight_membership", "metadata"])
def test_lock_source_change_after_native_render_rejects_publication(
    project, tmp_path, monkeypatch, change
):
    root = project
    model = root / "model"
    model.mkdir()
    (model / "a.bin").write_bytes(b"abc")
    (model / "config.json").write_text("{}", encoding="utf-8")
    path = root / "reprollm.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["models"] = {"primary": {"provider": "local", "id": "model"}}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    target = root / "reprollm.lock"
    old = b"old lock retained on failure\n"
    target.write_bytes(old)
    original = writer.write_lock

    def write_then_edit(staged_target, lock):
        original(staged_target, lock)
        if change == "manifest":
            path.write_bytes(path.read_bytes() + b"\n# intervening edit\n")
        elif change == "rules":
            (root / ".reprollm/project-rules.yaml").write_text(
                "schema_version: 1\nrules: []\n", encoding="utf-8"
            )
        elif change == "weight_membership":
            (model / "b.bin").write_bytes(b"new weight shard")
        else:
            (model / "config.json").write_text('{"hidden_size":2}', encoding="utf-8")

    monkeypatch.setattr(writer, "write_lock", write_then_edit)
    result = call(root, tmp_path / "state", "lock", offline=True)
    assert result.invocation in {"blocked", "user_error"}
    assert "action_unavailable" not in json.dumps(result.as_dict())
    assert target.read_bytes() == old


def test_lock_target_changed_at_publication_preserves_human_bytes(project, tmp_path, monkeypatch):
    target = project / "reprollm.lock"
    target.write_bytes(b"initial lock\n")
    original = writes.publish_artifact

    def edit_before_publish(artifact, published):
        if artifact.target == target:
            target.write_bytes(b"human edit wins\n")
        return original(artifact, published)

    monkeypatch.setattr(writes, "publish_artifact", edit_before_publish)
    result = call(project, tmp_path / "state", "lock", offline=True)
    assert result.invocation in {"blocked", "user_error"}
    assert "action_unavailable" not in json.dumps(result.as_dict())
    assert target.read_bytes() == b"human edit wins\n"


def test_nested_local_model_link_cannot_read_unapproved_external_weight(
    project, tmp_path, monkeypatch
):
    model = project / "model"
    model.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"synthetic private model bytes must not be opened")
    try:
        (model / "a.bin").symlink_to(outside)
    except OSError:
        pytest.skip("File symlinks unavailable")
    manifest = project / "reprollm.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["models"] = {"primary": {"provider": "local", "id": "model"}}
    manifest.write_text(yaml.safe_dump(data), encoding="utf-8")
    original = Path.open
    opened = []

    def guarded_open(path, *a, **kw):
        if path.resolve() == outside.resolve():
            opened.append(path)
            raise AssertionError("native external weight opened before scope decision")
        return original(path, *a, **kw)

    monkeypatch.setattr(Path, "open", guarded_open)
    result = call(project, tmp_path / "state", "lock", offline=True)
    assert result.invocation in {"blocked", "user_error"}
    assert "action_unavailable" not in json.dumps(result.as_dict())
    assert opened == [] and not (project / "reprollm.lock").exists()


def test_remove_after_archive_active_publish_failure_keeps_recovery_and_active(
    project, tmp_path, monkeypatch
):
    state = tmp_path / "state"
    add(project, state)
    active = project / ".reprollm/project-rules.yaml"
    original_bytes = active.read_bytes()
    original = writes.publish_artifact

    def fail_active(artifact, published):
        if artifact.target == active:
            raise OSError("synthetic active publication failure")
        return original(artifact, published)

    monkeypatch.setattr(writes, "publish_artifact", fail_active)
    result = call(
        project, state, "rules.remove", rule_id="project.alpha", reason="Retired experiment."
    )
    assert result.invocation != "handled_result"
    assert active.read_bytes() == original_bytes
    assert len(archives(project)) == 1
    archive = RuleArchive.model_validate_json(archives(project)[0].read_bytes())
    assert archive.rule == read_rules(project).rules[0]
    assert archive.archive_id == archive.content_id()
    assert archive.archive_id in json.dumps(result.as_dict())


def test_remove_archive_publish_failure_never_deactivates(project, tmp_path, monkeypatch):
    state = tmp_path / "state"
    add(project, state)
    active = project / ".reprollm/project-rules.yaml"
    before = active.read_bytes()
    original = writes.publish_artifact

    def fail_archive(artifact, published):
        if artifact.target.parent.name == "rule-archives":
            raise OSError("synthetic archive publication failure")
        return original(artifact, published)

    monkeypatch.setattr(writes, "publish_artifact", fail_archive)
    result = call(
        project, state, "rules.remove", rule_id="project.alpha", reason="Retired experiment."
    )
    assert result.invocation != "handled_result"
    assert active.read_bytes() == before and archives(project) == []


def test_restore_publication_failure_never_changes_archive(project, tmp_path, monkeypatch):
    state = tmp_path / "state"
    add(project, state)
    checked(
        call(project, state, "rules.remove", rule_id="project.alpha", reason="Retired experiment.")
    )
    recovery = archives(project)[0]
    raw = recovery.read_bytes()
    active = project / ".reprollm/project-rules.yaml"
    before = active.read_bytes()
    original = writes.publish_artifact

    def fail_active(artifact, published):
        if artifact.target == active:
            raise OSError("synthetic restore publication failure")
        return original(artifact, published)

    monkeypatch.setattr(writes, "publish_artifact", fail_active)
    result = call(project, state, "rules.restore", archive_id=recovery.stem)
    assert result.invocation != "handled_result"
    assert recovery.read_bytes() == raw and active.read_bytes() == before


@pytest.mark.parametrize("conflicting_bytes", [False, True])
def test_existing_archive_identical_reuse_or_conflict_preserves_bytes(
    project, tmp_path, monkeypatch, conflicting_bytes
):
    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(rule_lifecycle, "datetime", FrozenClock)
    state = tmp_path / "state"
    add(project, state)
    checked(
        call(project, state, "rules.remove", rule_id="project.alpha", reason="Retired experiment.")
    )
    recovery = archives(project)[0]
    checked(call(project, state, "rules.restore", archive_id=recovery.stem))
    active = project / ".reprollm/project-rules.yaml"
    before = active.read_bytes()
    if conflicting_bytes:
        data = json.loads(recovery.read_bytes())
        data["reason"] = "Changed archive reason without changing ID"
        recovery.write_text(json.dumps(data), encoding="utf-8")
    raw = recovery.read_bytes()
    result = call(
        project, state, "rules.remove", rule_id="project.alpha", reason="Retired experiment."
    )
    if conflicting_bytes:
        assert result.invocation != "handled_result" and active.read_bytes() == before
    else:
        checked(result)
        assert read_rules(project).rules == []
    assert len(archives(project)) == 1 and recovery.read_bytes() == raw
