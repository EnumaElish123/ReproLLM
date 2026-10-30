"""Platform typing must not resolve unavailable native features during import."""

from __future__ import annotations

import builtins
import importlib.util
import os
import signal
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_operations as operations  # noqa: E402
from skill_request import Request  # noqa: E402


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_modeled_portable_import_and_status_never_resolve_linux_features(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    touched: list[str] = []

    def proxy(real: ModuleType, blocked: set[str]) -> ModuleType:
        value = ModuleType("modeled_" + real.__name__)

        def lookup(name: str) -> Any:
            if name in blocked:
                touched.append(name)
                pytest.fail("Unsupported operation feature resolved during portable import/status")
            return getattr(real, name)

        value.__dict__["__getattr__"] = lookup
        return value

    native_os = proxy(os, {"O_NOFOLLOW", "O_NONBLOCK", "geteuid", "pidfd_open", "set_blocking"})
    native_signal = proxy(signal, {"SIGKILL", "pidfd_send_signal"})
    name = "modeled_skill_operations_" + platform
    original_import = builtins.__import__

    def isolated_import(
        target: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if globals is not None and globals.get("__name__") == name:
            if target == "os":
                return native_os
            if target == "signal":
                return native_signal
        return original_import(target, globals, locals, fromlist, level)

    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "skill_operations.py")
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, loaded)
    monkeypatch.setattr(builtins, "__import__", isolated_import)
    spec.loader.exec_module(loaded)
    monkeypatch.setattr(loaded, "sys", SimpleNamespace(platform=platform))
    result = loaded.control(
        Request("operation.status", str(tmp_path), {"operation_id": "c" * 32}),
        home=tmp_path / "not-created",
        root=tmp_path,
    )
    assert result is not None and result.invocation == "blocked"
    assert {"code": "operation_platform_unavailable"} in result.diagnostics
    assert not (tmp_path / "not-created").exists()
    assert touched == []


def test_native_feature_interfaces_are_lazy_and_preserve_missing_attribute_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_os = SimpleNamespace()
    native_signal = SimpleNamespace()
    monkeypatch.setattr(operations, "os", native_os)
    monkeypatch.setattr(operations, "signal", native_signal)

    assert operations._operation_os() is native_os
    assert operations._operation_signal() is native_signal
    with pytest.raises(AttributeError):
        _ = operations._operation_os().O_NOFOLLOW
    with pytest.raises(AttributeError):
        _ = operations._operation_signal().SIGKILL


def test_native_interfaces_call_the_exact_owned_pidfd_apis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []
    native_os = SimpleNamespace(
        pidfd_open=lambda pid: calls.append(("pidfd_open", pid)) or 73,
        getpid=lambda: 41,
        close=lambda descriptor: calls.append(("close", descriptor)),
    )
    native_signal = SimpleNamespace(
        pidfd_send_signal=lambda descriptor, number: calls.append(
            ("pidfd_send_signal", descriptor, number)
        )
    )
    monkeypatch.setattr(operations, "os", native_os)
    monkeypatch.setattr(operations, "signal", native_signal)
    monkeypatch.setattr(operations, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(operations, "_process_identity", lambda pid: "owned-generation")

    assert operations._signal_owned({"worker_pid": 41, "worker_identity": "owned-generation"}, 9)
    assert calls == [
        ("pidfd_open", 41),
        ("close", 73),
        ("pidfd_open", 41),
        ("pidfd_send_signal", 73, 9),
        ("close", 73),
    ]
