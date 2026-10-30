"""SK15: stalled pipes and special metadata never block a short broker."""

from __future__ import annotations

import contextlib
import dataclasses
import os
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_operations as operations  # noqa: E402
from skill_request import Grants, Request  # noqa: E402

pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(
        not sys.platform.startswith("linux"), reason="Linux private FIFO and pipe ownership"
    ),
]


def test_stalled_worker_input_returns_unknown_before_owned_child_ends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    home = tmp_path / "home"
    environment = tmp_path / "environment"
    environment.mkdir()
    claim = {"schema_version": 1, "environment": "a" * 32, "lease_id": "b" * 32}
    lease = type(
        "Lease",
        (),
        {
            "environment": environment,
            "claim": claim,
            "cleanup_failed": False,
            "transfer": lambda self: setattr(self, "transferred", True),
            "reclaim": lambda self: setattr(self, "transferred", False),
        },
    )()

    @contextlib.contextmanager
    def leases(*args: Any):
        yield lease

    # Bundle verification is separately exercised; the transport substitute below
    # starts only our own sleeping Python process and never loads native work.
    monkeypatch.setattr(operations, "_bundle", lambda store: "c" * 64)
    monkeypatch.setattr(operations, "_verify_bundle", lambda *args: None)
    monkeypatch.setattr(operations, "IPC_SEND_TIMEOUT_SECONDS", 0.1, raising=False)
    req = Request(
        "lock",
        str(root),
        {"offline": True, "hash_large_files": True},
        Grants(
            write=True,
            expected_hashes={f"file-{index:04d}-" + "a" * 40: "f" * 64 for index in range(1500)},
        ),
    )
    assert len(operations._json(dataclasses.asdict(req))) < operations.MAX_REQUEST_BYTES
    original = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def stalled(argv: list[str], **kwargs: Any) -> subprocess.Popen[bytes]:
        child = original(
            [sys.executable, "-I", "-B", "-c", "import time; time.sleep(30)"], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(operations.subprocess, "Popen", stalled)
    args = dict(
        home=home,
        root=root,
        identity="d" * 64,
        manager=object(),
        environment_name="a" * 32,
        lease_factory=leases,
    )
    prepared = operations.start(req, **args)
    token = prepared.data["operation"]["operation_id"]
    start = dataclasses.replace(req, options={**req.options, "operation_id": token})
    exceeded = False
    alive_at_return = False
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(operations.start, start, **args)
        try:
            try:
                reply = future.result(timeout=2)
                alive_at_return = len(children) == 1 and children[0].poll() is None
            except TimeoutError:
                exceeded = True
        finally:
            # Bound the RED harness too; signal only the Popen objects created here.
            for child in children:
                if child.poll() is None:
                    child.terminate()
                child.wait(timeout=5)
            reply = future.result(timeout=5)
    assert not exceeded, "The broker blocked on a worker that never reads its input pipe"
    assert alive_at_return
    assert reply.data["operation"]["state"] == "UNKNOWN"
    assert reply.data["operation"]["operation_id"] == token
    record = operations._read(home / "operations/claims" / token / "status.json")
    assert record["lease"] == claim and lease.transferred
    assert len(children) == 1 and not (root / "reprollm.lock").exists()


def test_fifo_metadata_is_rejected_without_waiting_for_a_writer(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    home = tmp_path / "home"
    store = home / "operations"
    store.mkdir(parents=True, mode=0o700)
    fifo = store / "owner.json"
    os.mkfifo(fifo, 0o600)
    req = Request("operation.status", str(root), {"operation_id": "0" * 32})
    exceeded = False
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(operations.control, req, home=home, root=root)
        try:
            reply = future.result(timeout=1)
        except TimeoutError:
            exceeded = True
            descriptor = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
            try:
                reply = future.result(timeout=5)
            finally:
                os.close(descriptor)
    assert not exceeded, "Type checking must happen before a blocking FIFO open"
    assert reply is not None and reply.invocation == "blocked"
    assert stat.S_ISFIFO(fifo.lstat().st_mode)
    assert not list(store.glob("claims/*"))


@pytest.mark.parametrize("kind", ["empty", "large"])
def test_nonblocking_send_preserves_the_complete_frame(kind: str) -> None:
    raw = b"" if kind == "empty" else operations._json({"padding": "量" * 80_000})
    assert len(raw) < operations.MAX_REQUEST_BYTES
    reader, writer = os.pipe()

    def drain() -> bytes:
        with os.fdopen(reader, "rb") as source:
            return source.read()

    with ThreadPoolExecutor(max_workers=1) as pool:
        received = pool.submit(drain)
        stream = os.fdopen(writer, "wb")
        operations._send_input(stream, raw)
        assert stream.closed
        assert received.result(timeout=5) == len(raw).to_bytes(4, "big") + raw


def test_nonblocking_metadata_read_keeps_regular_files_and_refuses_links(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    raw = b'{"schema_version":1,"owner":"public"}\n'
    path.write_bytes(raw)
    path.chmod(0o600)
    assert operations._raw(path, 1024) == raw
    alias = path.with_name("alias.json")
    alias.symlink_to(path)
    with pytest.raises(OSError):
        operations._raw(alias, 1024)
    assert path.read_bytes() == raw and alias.is_symlink()
