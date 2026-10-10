from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from reprollm.core.errors import UserError
from reprollm.core.yaml_io import dump_yaml, load_lock
from reprollm.lock.writer import check_lock, write_lock
from reprollm.schemas.lock import InferenceLock, Lock, Provenance, ResolutionMode
from reprollm.schemas.manifest import AttackSpec, MechanismSpec, Privacy, Training


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


def _inference(params: dict[str, Any], *, note: str | None = None) -> InferenceLock:
    return InferenceLock(
        backend="other",
        version=Provenance(
            value=None, source="unsupported_backend", confidence="unresolved", note=note
        ),
        params=params,
    )


def test_plain_keyed_secret_is_rejected_before_temporary_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "reprollm.lock"
    target.write_bytes(b"old lock\n")
    canary = "syntheticPlainCanaryABC"
    document = _lock().model_copy(update={"inference": _inference({"api_key": canary})})
    monkeypatch.setattr(
        "reprollm.lock.writer.tempfile.mkstemp",
        lambda **_: pytest.fail("unsafe lock reached temporary creation"),
    )
    with pytest.raises(UserError) as error:
        write_lock(target, document)
    assert canary not in str(error.value)
    assert "reprollm.yaml" in str(error.value)
    assert target.read_bytes() == b"old lock\n"
    assert not list(tmp_path.glob(".reprollm.lock.*.tmp"))


@pytest.mark.parametrize(
    "params",
    [
        {"outer": [{"api_key": "syntheticPlainCanaryABC"}]},
        {"access-token": ["syntheticPlainCanaryABC", "secondPlainCanaryABC"]},
        {"password": {"nested": "syntheticPlainCanaryABC"}},
        {"ordinary": "sk-abcdefghijklmnopQRST"},
        {"ordinary": "eyJabcdefghi.abcdefghijk.lmnopqrstuv=="},
        {"sk-abcdefghijklmnopQRST": "ordinary"},
        {"cache": "/external-private/cache"},
        {"cache": "C:\\private-machine\\cache"},
        {"cache": "\\\\private-machine\\share"},
        {"machine": "synthetic-machine"},
        {"author": "synthetic-user"},
    ],
)
def test_persisted_mapping_keys_nested_values_and_identity_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, params: dict[str, Any]
) -> None:
    monkeypatch.setattr("reprollm.lock.writer.socket.gethostname", lambda: "synthetic-machine")
    monkeypatch.setattr("reprollm.lock.writer.getpass.getuser", lambda: "synthetic-user")
    monkeypatch.setattr(
        "reprollm.lock.writer.tempfile.mkstemp",
        lambda **_: pytest.fail("unsafe lock reached temporary creation"),
    )
    target = tmp_path / "reprollm.lock"
    target.write_bytes(b"previous exact bytes\n")
    with pytest.raises(UserError, match="remove secrets"):
        write_lock(target, _lock().model_copy(update={"inference": _inference(params)}))
    assert target.read_bytes() == b"previous exact bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["reprollm.lock"]


@pytest.mark.parametrize("section", ["training", "privacy.mechanism", "privacy.attack"])
def test_free_parameters_are_checked_in_every_copied_section(tmp_path: Path, section: str) -> None:
    params = {"api_key": "syntheticPlainCanaryABC"}
    if section == "training":
        update = {"training": Training(params=params)}
    elif section == "privacy.mechanism":
        update = {"privacy": Privacy(mechanism=MechanismSpec(name="other", params=params))}
    else:
        update = {"privacy": Privacy(attack=AttackSpec(params=params))}
    with pytest.raises(UserError, match="reprollm.yaml"):
        write_lock(tmp_path / "reprollm.lock", _lock().model_copy(update=update))
    assert list(tmp_path.iterdir()) == []


def test_provenance_notes_and_final_serialized_text_are_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(UserError):
        write_lock(
            tmp_path / "reprollm.lock",
            _lock().model_copy(
                update={"inference": _inference({}, note="password=plainCanaryABC")}
            ),
        )
    monkeypatch.setattr(
        "reprollm.lock.writer.dump_yaml",
        lambda _: dump_yaml(_lock()) + "# password=plainCanaryABC\n",
    )
    monkeypatch.setattr(
        "reprollm.lock.writer.tempfile.mkstemp",
        lambda **_: pytest.fail("unsafe serialized lock reached temporary creation"),
    )
    with pytest.raises(UserError):
        write_lock(tmp_path / "reprollm.lock", _lock())
    assert list(tmp_path.iterdir()) == []


def test_safe_identifiers_and_scalar_types_keep_exact_serialization(tmp_path: Path) -> None:
    params = {
        "model": "Qwen/Qwen3-32B",
        "endpoint": "https://example.org/v1/models",
        "cache": "cache/models",
        "glob": "configs/**/*.json",
        "stop": ["</s>", "</think>"],
        "max_tokens": 2048,
        "TOKENIZERS_PARALLELISM": False,
        "api_key": "short",
        "nested": [{"enabled": True, "nothing": None}],
    }
    document = _lock().model_copy(update={"inference": _inference(params)})
    target = tmp_path / "reprollm.lock"
    write_lock(target, document)
    assert target.read_text(encoding="utf-8") == dump_yaml(document)
    assert load_lock(target).inference.params == params


def test_safe_short_leaves_under_secret_container_keep_yaml_bytes(tmp_path: Path) -> None:
    document = _lock().model_copy(
        update={"inference": _inference({"password": {"max_tokens": 2048, "provider": "safe"}})}
    )
    target = tmp_path / "reprollm.lock"
    write_lock(target, document)
    assert target.read_text(encoding="utf-8") == dump_yaml(document)


@pytest.mark.parametrize("value", ["file:///external-private/cache", "file://machine/share"])
def test_absolute_local_file_uri_is_rejected(tmp_path: Path, value: str) -> None:
    with pytest.raises(UserError):
        write_lock(
            tmp_path / "reprollm.lock",
            _lock().model_copy(update={"inference": _inference({"cache": value})}),
        )
    assert list(tmp_path.iterdir()) == []


def test_serialization_cannot_introduce_an_unchecked_structured_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unsafe = _lock().model_copy(update={"inference": _inference({"api_key": "plainCanaryABC"})})
    monkeypatch.setattr(
        "reprollm.lock.writer.dump_yaml",
        lambda _: dump_yaml(unsafe).replace("    api_key:", '    "api_key":'),
    )
    with pytest.raises(UserError):
        write_lock(tmp_path / "reprollm.lock", _lock())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("in_note", [False, True])
def test_contextual_capture_failure_is_a_safe_lock_usage_error(
    tmp_path: Path, in_note: bool
) -> None:
    import json

    canary = "syntheticPlainCanaryABC123"
    malformed = json.dumps({"message": '{"api_key": "' + canary})
    inference = _inference(
        {} if in_note else {"message": malformed}, note=malformed if in_note else None
    )
    target = tmp_path / "reprollm.lock"
    target.write_bytes(b"previous lock bytes\n")
    with pytest.raises(UserError, match="remove secrets") as error:
        write_lock(target, _lock().model_copy(update={"inference": inference}))
    assert canary not in str(error.value)
    assert target.read_bytes() == b"previous lock bytes\n"
    assert not list(tmp_path.glob(".reprollm.lock.*.tmp"))
