"""SK15 read closure, preview lifetime and cooperative publication boundaries."""

from __future__ import annotations

import pytest
import yaml
from tests.unit.skills import test_skill_local_lifecycle as contract

call = contract.call
local = contract.local
checked = contract.checked


@pytest.fixture(autouse=True)
def no_external_effects(monkeypatch):
    contract.no_external_effects.__wrapped__(monkeypatch)


@pytest.fixture
def project(tmp_path):
    return contract.project.__wrapped__(tmp_path)


def local_model(root, value="model"):
    path = root / "reprollm.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["models"] = {"primary": {"provider": "local", "id": value}}
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")


def test_local_model_root_alias_retarget_after_render_is_stale(project, tmp_path, monkeypatch):
    from reprollm.lock import writer

    first, second = project / "first", project / "second"
    first.mkdir()
    second.mkdir()
    (first / "a.bin").write_bytes(b"first")
    (second / "a.bin").write_bytes(b"second")
    alias = project / "model"
    try:
        alias.symlink_to(first, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks unavailable")
    local_model(project)
    target = project / "reprollm.lock"
    target.write_bytes(b"original lock\n")
    original = writer.write_lock

    def changed(path, document):
        original(path, document)
        alias.unlink()
        alias.symlink_to(second, target_is_directory=True)

    monkeypatch.setattr(writer, "write_lock", changed)
    reply = call(project, tmp_path / "state", "lock", offline=True)
    assert reply.invocation == "blocked" and target.read_bytes() == b"original lock\n"


@pytest.mark.parametrize(
    "action", ["lock", "rules.add", "rules.remove", "rules.accept", "rules.ignore", "rules.restore"]
)
def test_preview_apply_remains_valid_across_native_generation_times(
    project, tmp_path, monkeypatch, action
):
    import time

    state = tmp_path / "state"
    options = (
        {"offline": True}
        if action == "lock"
        else {"field": "custom.alpha", "severity": "WARNING", "reason": "Public rule"}
    )
    if action == "rules.remove":
        checked(call(project, state, "rules.add", **options))
        options = {"rule_id": "project.alpha", "reason": "Public retired rule"}
    if action == "lock":
        options["operation_id"] = "a" * 32
    grants = contract.Grants(write=True)
    if action in {"rules.accept", "rules.ignore"}:
        source = contract.discovery(project)
        options = {"candidate_id": "c-000001"}
        grants = contract.reviewed(project, source)
    if action == "rules.restore":
        checked(call(project, state, "rules.add", **options))
        removed = call(project, state, "rules.remove", rule_id="project.alpha", reason="Retired")
        checked(removed)
        options = {"archive_id": removed.data["archive_id"]}
    preview = call(project, state, action, preview=True, grants=grants, **options)
    checked(preview)
    assert preview.data["phase"] == "prepared" and preview.data["artifacts_written"] == []
    time.sleep(1.1)
    if action == "lock":
        options["operation_id"] = "b" * 32
    applied = call(
        project,
        state,
        action,
        grants=contract.Grants(
            write=True, expected_hashes=grants.expected_hashes, plan_hash=preview.data["plan_hash"]
        ),
        **options,
    )
    checked(applied)
    assert (
        applied.data["phase"] == "applied"
        and applied.data["plan_hash"] == preview.data["plan_hash"]
    )
    if action == "rules.remove":
        from reprollm.schemas.rule_archive import RuleArchive

        path = next((project / ".reprollm/rule-archives").glob("*.json"))
        archive = RuleArchive.model_validate_json(path.read_bytes())
        assert archive.archive_id == path.stem == archive.content_id()


def test_cancel_checkpoint_prevents_publication_without_restarting(project, tmp_path, monkeypatch):
    from reprollm.lock import writer

    class Cancelled(RuntimeError):
        pass

    class Cancellation:
        cancelled = False

        def check_cancel(self):
            if self.cancelled:
                raise Cancelled

        def publication(self):
            pytest.fail("Cancelled work entered publication")

    cancellation = Cancellation()
    original = writer.write_lock

    def staged(path, document):
        original(path, document)
        cancellation.cancelled = True

    monkeypatch.setattr(writer, "write_lock", staged)
    with pytest.raises(Cancelled):
        local.execute_lock(
            contract.Request("lock", str(project), {"offline": True}, contract.Grants(write=True)),
            root=project,
            state_home=tmp_path / "state",
            identity="fixed",
            cancellation=cancellation,
        )
    assert not (project / "reprollm.lock").exists()


@pytest.mark.parametrize(
    "damage", ["expired", "request", "prepared_at", "symlink", "owner", "oversized"]
)
def test_plan_state_damage_refuses_before_resolving(project, tmp_path, monkeypatch, damage):
    import json

    from reprollm.lock import writer

    state = tmp_path / "state"
    preview = call(project, state, "lock", offline=True, preview=True)
    checked(preview)
    token = preview.data["plan_hash"]
    path = state / "writes/plans" / (token + ".json")
    record = json.loads(path.read_bytes())
    if damage == "expired":
        monkeypatch.setattr(
            local.time, "time", lambda: record["created_at"] + local.PLAN_TTL_SECONDS + 1
        )
    elif damage == "request":
        record["request_sha256"] = "0" * 64
        path.write_text(json.dumps(record), encoding="utf-8")
    elif damage == "prepared_at":
        record["prepared_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(record), encoding="utf-8")
    elif damage == "owner":
        (path.parent / "owner.json").write_text(
            '{"schema_version":1,"owner":"foreign"}', encoding="utf-8"
        )
    elif damage == "oversized":
        path.write_bytes(b"x" * (local.MAX_PLAN_BYTES + 1))
    else:
        original = tmp_path / "foreign-plan"
        original.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(original)
        except OSError:
            pytest.skip("File symlinks unavailable")
    monkeypatch.setattr(
        writer, "build_lock", lambda *a, **k: pytest.fail("Invalid plan started resolution")
    )
    result = call(
        project, state, "lock", offline=True, grants=contract.Grants(write=True, plan_hash=token)
    )
    assert result.invocation == "blocked" and not (project / "reprollm.lock").exists()
    if damage == "expired":
        assert result.diagnostics == [{"code": "local_plan_expired"}]


def test_candidate_inspection_supplies_content_and_membership_identity(project, tmp_path):
    import hashlib
    import json

    source = contract.discovery(project)
    result = call(
        project, tmp_path / "state", "rules.candidates", grants=contract.Grants(), json=True
    )
    checked(result)
    assert isinstance(result.data, list) and result.data[0]["candidate"]["id"] == "c-000001"
    metadata = next(item for item in result.diagnostics if item.get("source"))
    assert metadata["source"] == source.relative_to(project).as_posix()
    assert metadata["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert metadata["active_sha256"] is None
    assert (
        metadata["membership_sha256"]
        == hashlib.sha256(
            json.dumps(
                [source.name], ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )


def test_large_granted_nested_weight_is_hashed_once_by_native_resolver(
    project, tmp_path, monkeypatch
):
    from pathlib import Path

    from reprollm.core.yaml_io import load_lock
    from reprollm.lock.local_resolver import _aggregate_hash

    model = project / "model"
    model.mkdir()
    external = tmp_path / "large-weight.bin"
    with external.open("wb") as stream:
        stream.truncate(101 * 1024 * 1024)
    alias = model / "weight.bin"
    try:
        alias.symlink_to(external)
    except OSError:
        pytest.skip("File symlinks unavailable")
    expected = _aggregate_hash([alias], model)
    local_model(project)
    original = Path.open
    opens = []

    def opened(path, *a, **k):
        if path.resolve() == external and (not a or "r" in str(a[0])):
            opens.append(path)
        return original(path, *a, **k)

    monkeypatch.setattr(Path, "open", opened)
    result = call(
        project,
        tmp_path / "state",
        "lock",
        offline=True,
        hash_large_files=True,
        grants=contract.Grants(write=True, external_paths=(str(external),)),
    )
    checked(result)
    assert len(opens) == 1
    locked = load_lock(project / "reprollm.lock").models["primary"].local.weights
    assert (
        locked.hashed and locked.total_size_bytes == 101 * 1024 * 1024 and locked.sha256 == expected
    )


def test_native_single_model_file_does_not_require_a_weight_extension(project, tmp_path):
    from reprollm.core.yaml_io import load_lock
    from reprollm.lock.local_resolver import _aggregate_hash

    target = project / "research-weights.data"
    target.write_bytes(b"public native model bytes")
    local_model(project, target.name)
    expected = _aggregate_hash([target], project)
    checked(call(project, tmp_path / "state", "lock", offline=True))
    assert load_lock(project / "reprollm.lock").models["primary"].local.weights.sha256 == expected


def test_one_file_can_have_multiple_native_read_roles(project, tmp_path):
    path = project / "reprollm.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["execution"] = {"config_files": ["reprollm.yaml"]}
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    checked(call(project, tmp_path / "state", "lock", offline=True))


def test_appearing_immutable_archive_cannot_be_adopted_as_replaceable(
    project, tmp_path, monkeypatch
):
    checked(
        call(
            project,
            tmp_path / "state",
            "rules.add",
            field="custom.alpha",
            severity="WARNING",
            reason="Public",
        )
    )
    active = project / ".reprollm/project-rules.yaml"
    before = active.read_bytes()
    original = local._artifact
    appeared = []

    def foreign(request, root, relative, content):
        if relative.startswith(".reprollm/rule-archives/"):
            target = root / relative
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(b"foreign immutable archive\n")
            appeared.append(target)
        return original(request, root, relative, content)

    monkeypatch.setattr(local, "_artifact", foreign)
    reply = call(
        project, tmp_path / "state", "rules.remove", rule_id="project.alpha", reason="Retired"
    )
    assert reply.invocation != "handled_result" and active.read_bytes() == before
    assert appeared and appeared[0].read_bytes() == b"foreign immutable archive\n"


def test_private_remove_failure_does_not_claim_project_recovery_copy(
    project, tmp_path, monkeypatch
):
    from reprollm.core import rule_lifecycle
    from reprollm.core.errors import UserError

    checked(
        call(
            project,
            tmp_path / "state",
            "rules.add",
            field="custom.alpha",
            severity="WARNING",
            reason="Public",
        )
    )
    active = project / ".reprollm/project-rules.yaml"
    before = active.read_bytes()
    monkeypatch.setattr(
        rule_lifecycle,
        "write_rules",
        lambda *a, **k: (_ for _ in ()).throw(UserError("synthetic private active failure")),
    )
    result = call(
        project, tmp_path / "state", "rules.remove", rule_id="project.alpha", reason="Retired"
    )
    assert result.invocation == "user_error" and result.cli_exit_code == 2
    assert result.data == {"phase": "preparation_failed", "artifacts_written": []}
    assert "saved" not in str(result.diagnostics)
    assert not list((project / ".reprollm/rule-archives").glob("*.json"))
    assert active.read_bytes() == before


def test_preview_state_failed_publication_is_atomic_and_recoverable(project, tmp_path, monkeypatch):
    original = local.os.link

    def failed(source, target):
        if len(str(target.stem)) == 64 and target.suffix == ".json":
            raise OSError("synthetic plan publication failure")
        return original(source, target)

    monkeypatch.setattr(local.os, "link", failed)
    state = tmp_path / "state"
    result = call(project, state, "lock", offline=True, preview=True)
    assert result.invocation == "blocked" and not (project / "reprollm.lock").exists()
    directory = state / "writes/plans"
    assert not list(directory.glob(".plan-*.tmp"))
    assert not [path for path in directory.glob("*.json") if path.name != "owner.json"]
    monkeypatch.setattr(local.os, "link", original)
    checked(call(project, state, "lock", offline=True, preview=True))


@pytest.mark.parametrize("action", ["lock", "rules.add"])
def test_unsafe_generated_content_never_publishes_or_remains_in_helper_state(
    project, tmp_path, action
):
    canary = "PublicSyntheticPrivateFixture23456"
    state = tmp_path / "state"
    if action == "lock":
        path = project / "reprollm.yaml"
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document["training"] = {"params": {"api_key": canary}}
        path.write_text(yaml.safe_dump(document), encoding="utf-8")
        result = call(project, state, action, offline=True)
    else:
        result = call(
            project,
            state,
            action,
            field="custom.alpha",
            severity="WARNING",
            reason="password=" + canary,
        )
    assert result.invocation == "user_error" and result.cli_exit_code == 2
    assert (
        not (project / "reprollm.lock").exists()
        and not (project / ".reprollm/project-rules.yaml").exists()
    )
    assert canary not in str(result.as_dict())
    assert all(
        canary.encode() not in path.read_bytes() for path in state.rglob("*") if path.is_file()
    )
