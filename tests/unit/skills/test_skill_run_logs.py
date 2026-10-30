"""Finite complete-line log snapshots through the public run.logs adapter."""

from __future__ import annotations

import dataclasses
import importlib
import json
import os
import signal
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_operations as operations  # noqa: E402
import skill_runtime as runtime  # noqa: E402
from skill_request import Request  # noqa: E402
from tests.unit.skills import test_skill_operations as contract  # noqa: E402
from tests.unit.skills.test_skill_run_operations import run_request  # noqa: E402

pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned run logs"),
]


@pytest.fixture
def logs(tmp_path, monkeypatch):
    setup = contract.setup.__wrapped__(tmp_path, monkeypatch)
    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    run_id = "20261031T000000Z-abcdef"
    folder = setup["root"] / ".reprollm/runs" / run_id
    folder.mkdir(parents=True)
    contract.edit_record(
        setup,
        token,
        native_run_id=run_id,
        native_run_identity=operations.run_directory_identity(setup["root"], run_id),
    )
    module = importlib.import_module("skill_run_logs")
    return setup, folder, Request("run.logs", str(setup["root"]), {"operation_id": token}), module


def read(logs):
    setup, _, request, module = logs
    return module.read_logs(request, home=setup["home"], root=setup["root"])


def test_live_partial_credential_line_is_withheld_until_complete(logs):
    _, folder, _, _ = logs
    target = folder / "stdout.log"
    secret = "OpaqueSyntheticSplitCredentialNeverSent"
    target.write_text("ready\napi_key=" + secret[:17], encoding="utf-8")
    first = read(logs)
    assert first.data["text"] == "ready\n" and first.data["withheld_partial_line"]
    assert secret[:17] not in json.dumps(first.as_dict())
    with target.open("a", encoding="utf-8") as stream:
        stream.write(secret[17:] + "\ncomplete\n")
    second = read(logs)
    assert "complete\n" in second.data["text"] and "<REDACTED" in second.data["text"]
    assert secret not in json.dumps(second.as_dict())


@pytest.mark.parametrize("kind", ["symlink", "fifo", "run_replacement"])
def test_unsafe_log_or_run_mapping_is_refused_without_reading_foreign_bytes(logs, kind):
    setup, folder, _, _ = logs
    target = folder / "stdout.log"
    if kind == "symlink":
        foreign = setup["root"].parent / "foreign.log"
        foreign.write_bytes(b"foreign secret data\n")
        target.symlink_to(foreign)
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        folder.rename(folder.with_name("held-original"))
        folder.mkdir()
        target.write_bytes(b"foreign replacement data\n")
    reply = read(logs)
    assert reply.invocation == "blocked" and not reply.complete
    assert "foreign" not in json.dumps(reply.as_dict())


def test_capture_disabled_or_pending_logs_do_not_create_an_artifact(logs):
    setup, folder, request, _ = logs
    contract.edit_record(setup, request.options["operation_id"], capture_output=False)
    reply = read(logs)
    assert reply.data["log_available"] is False and reply.data["text"] == ""
    assert reply.data["capture_output"] is False and list(folder.iterdir()) == []


def test_line_budget_withholds_whole_overlong_line(logs, monkeypatch):
    _, folder, _, module = logs
    monkeypatch.setattr(module, "MAX_LOG_BYTES", 128)
    (folder / "stdout.log").write_bytes(b"ready\n" + b"X" * 1000 + b"\n")
    reply = read(logs)
    assert reply.data["text"] == "ready\n" and reply.data["limit_reached"]
    assert not reply.complete and any(
        d["code"] == "run_log_prefix_limit" for d in reply.diagnostics
    )


def test_log_control_characters_use_existing_display_privacy(logs):
    _, folder, _, _ = logs
    (folder / "stdout.log").write_text("ready\x1b[31m\n标签\n", encoding="utf-8")
    text = read(logs).data["text"]
    assert "\x1b" not in text and "\\u001b" in text and "标签" in text


def test_immutable_log_pages_allow_append_but_refuse_prefix_rewrite(logs, monkeypatch):
    setup, folder, request, _ = logs
    target = folder / "stdout.log"
    target.write_text("public log line\n" * 30000, encoding="utf-8")
    monkeypatch.setattr(
        runtime, "input_signature", lambda *a: pytest.fail("No experiment tree hash")
    )
    first = runtime.execute(request, cache_home=setup["home"] / "responses", identity="public")
    assert first.next_cursor and first.snapshot and not first.complete
    follow = dataclasses.replace(
        request, response=dataclasses.replace(request.response, cursor=first.next_cursor)
    )
    with target.open("a", encoding="utf-8") as stream:
        stream.write("new complete line\n")
    second = runtime.execute(follow, cache_home=setup["home"] / "responses", identity="public")
    assert second.invocation == "handled_result" and second.snapshot == first.snapshot
    target.write_text("replaced prefix\n", encoding="utf-8")
    stale = runtime.execute(follow, cache_home=setup["home"] / "responses", identity="public")
    assert stale.invocation in {"blocked", "user_error"} and not stale.complete


def test_long_multiline_log_continues_bounded_windows_without_losing_lines(logs):
    setup, folder, request, module = logs
    raw = ("public line 标签\n" * 40).encode()
    (folder / "stdout.log").write_bytes(raw)
    offset = 0
    observed = []
    while True:
        selected = dataclasses.replace(
            request, options={**request.options, "offset_bytes": offset, "limit_bytes": 128}
        )
        reply = module.read_logs(selected, home=setup["home"], root=setup["root"])
        assert reply.invocation == "handled_result", reply.as_dict()
        observed.append(reply.data["text"])
        assert reply.data["offset_bytes"] == offset
        next_offset = reply.data["next_offset_bytes"]
        if next_offset is None:
            break
        assert next_offset > offset
        offset = next_offset
    assert "".join(observed).encode() == raw


@pytest.mark.parametrize("offset", [1, 4, 10_000])
def test_unaligned_or_past_end_log_offset_is_refused(logs, offset):
    setup, folder, request, module = logs
    (folder / "stdout.log").write_bytes(b"first line\nsecond line\n")
    selected = dataclasses.replace(request, options={**request.options, "offset_bytes": offset})
    assert (
        module.read_logs(selected, home=setup["home"], root=setup["root"]).invocation == "blocked"
    )


def test_unfinished_or_overlong_line_does_not_offer_unsafe_progress(logs, monkeypatch):
    _, folder, _, module = logs
    monkeypatch.setattr(module, "MAX_LOG_BYTES", 128)
    (folder / "stdout.log").write_bytes(b"api_key=" + b"SyntheticLongValue" * 50 + b"\n")
    reply = read(logs)
    assert reply.data["text"] == "" and reply.data["next_offset_bytes"] is None
    assert reply.data["line_exceeds_window"] and not reply.complete
    assert "SyntheticLongValue" not in json.dumps(reply.as_dict())


def test_seeked_window_reconstructs_pem_context_beyond_sixteen_mib(logs):
    setup, folder, request, module = logs
    offset = 16 * 1024 * 1024
    with (folder / "stdout.log").open("wb") as stream:
        header = b"-----BEGIN PRIVATE KEY-----\n"
        end = b"-----END PRIVATE KEY-----\n"
        remaining = offset - len(header) - len(end)
        stream.write(header)
        while remaining:
            count = min(4096, remaining)
            stream.write(b"A" * (count - 1) + b"\n")
            remaining -= count
        stream.write(end + b"tail after first window\n")
    selected = dataclasses.replace(
        request, options={**request.options, "offset_bytes": offset, "limit_bytes": 128}
    )
    reply = module.read_logs(selected, home=setup["home"], root=setup["root"])
    assert reply.data["text"] == "tail after first window\n" and reply.complete


def test_window_boundary_keeps_whole_secret_line_for_next_window(logs):
    setup, folder, request, module = logs
    secret = "OpaqueSyntheticWindowCredentialNeverSent" * 2
    (folder / "stdout.log").write_text("P" * 60 + "\napi_key=" + secret + "\n", encoding="utf-8")
    first_request = dataclasses.replace(request, options={**request.options, "limit_bytes": 128})
    first = module.read_logs(first_request, home=setup["home"], root=setup["root"])
    assert first.data["text"] == "P" * 60 + "\n" and first.data["next_offset_bytes"] == 61
    second_request = dataclasses.replace(
        first_request, options={**first_request.options, "offset_bytes": 61}
    )
    second = module.read_logs(second_request, home=setup["home"], root=setup["root"])
    assert "<REDACTED" in second.data["text"] and second.complete
    assert secret not in json.dumps([first.as_dict(), second.as_dict()])


@pytest.mark.parametrize("kind", ["pem", "yaml", "toml", "repeated_pem_end"])
def test_offset_retains_native_multiline_privacy_context(logs, kind):
    setup, folder, request, module = logs
    secret = "OpaqueSyntheticMultilinePrivateMaterialNeverSent"
    if kind in {"pem", "repeated_pem_end"}:
        header = "-----BEGIN PRIVATE KEY-----\n"
        tail = secret + "\n-----END PRIVATE KEY-----\n"
        if kind == "repeated_pem_end":
            tail += "-----END PRIVATE KEY-----\n"
    elif kind == "yaml":
        header = "api_key:\n"
        tail = "  value: " + secret + "\n"
    else:
        header = "[api_key]\n"
        tail = 'value = "' + secret + '"\n'
    (folder / "stdout.log").write_text(header + tail, encoding="utf-8")
    selected = dataclasses.replace(
        request, options={**request.options, "offset_bytes": len(header.encode())}
    )
    full = module.read_logs(request, home=setup["home"], root=setup["root"])
    window = module.read_logs(selected, home=setup["home"], root=setup["root"])
    assert secret not in json.dumps(full.as_dict())
    assert window.invocation == "handled_result" and secret not in json.dumps(window.as_dict())
    assert window.data["text"] != tail


def test_snapshot_rejects_changed_privacy_context_before_unchanged_window(logs):
    setup, folder, request, _ = logs
    target = folder / "stdout.log"
    header = "groupA:\n"
    tail = "  public log text 标签\n" * 20000
    target.write_text(header + tail, encoding="utf-8")
    selected = dataclasses.replace(
        request, options={**request.options, "offset_bytes": len(header.encode())}
    )
    first = runtime.execute(selected, cache_home=setup["home"] / "responses", identity="public")
    assert first.next_cursor
    follow = dataclasses.replace(
        selected, response=dataclasses.replace(selected.response, cursor=first.next_cursor)
    )
    target.write_text("groupB:\n" + tail, encoding="utf-8")
    stale = runtime.execute(follow, cache_home=setup["home"] / "responses", identity="public")
    assert stale.invocation in {"blocked", "user_error"} and not stale.complete


def test_unprovable_context_limit_withholds_entire_window(logs, monkeypatch):
    setup, folder, request, module = logs
    header = "-----BEGIN PRIVATE KEY-----\n"
    secret = "OpaqueSyntheticUnprovablePrivateMaterial"
    (folder / "stdout.log").write_text(header + secret + "\n", encoding="utf-8")
    monkeypatch.setattr(module, "MAX_CONTEXT_BYTES", 8, raising=False)
    selected = dataclasses.replace(
        request, options={**request.options, "offset_bytes": len(header.encode())}
    )
    reply = module.read_logs(selected, home=setup["home"], root=setup["root"])
    assert not reply.complete and reply.invocation == "blocked"
    assert secret not in json.dumps(reply.as_dict())


def test_context_deadline_restores_timer_and_withholds_entire_window(logs, monkeypatch):
    _, folder, _, module = logs
    (folder / "stdout.log").write_text("public first\npublic second\n", encoding="utf-8")
    ticks = iter([100.0, 100.0, 106.0])
    monkeypatch.setattr(
        module, "time", SimpleNamespace(monotonic=lambda: next(ticks, 106.0)), raising=False
    )
    previous = signal.getsignal(signal.SIGALRM)
    timer = signal.getitimer(signal.ITIMER_REAL)
    reply = read(logs)
    assert reply.invocation == "blocked" and not reply.complete
    assert signal.getsignal(signal.SIGALRM) == previous
    assert signal.getitimer(signal.ITIMER_REAL) == timer
    assert any(d["code"] == "run_log_context_deadline" for d in reply.diagnostics)


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_unsupported_log_platform_refuses_before_linux_file_primitives(logs, monkeypatch, platform):
    _, folder, _, module = logs
    target = folder / "stdout.log"
    target.write_bytes(b"public line\n")
    original = module.os.open

    def owned_state_only(path, *args, **kwargs):
        assert Path(path) != target
        return original(path, *args, **kwargs)

    monkeypatch.setattr(module.sys, "platform", platform)
    monkeypatch.setattr(module.os, "open", owned_state_only)
    reply = read(logs)
    assert reply.invocation == "blocked" and not reply.complete
