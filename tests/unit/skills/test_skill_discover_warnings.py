"""Keep source-parse warnings out of worker streams without changing discovery."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_runtime as runtime  # noqa: E402
from skill_request import Grants, Reply, Request, encode_reply  # noqa: E402
from tests.unit.skills.test_skill_runtime import VerifiedManagerStub  # noqa: E402

SOURCE = r"""import argparse
p = argparse.ArgumentParser()
p.add_argument("--pattern", default="\D")
"""


def worker_preview(
    tmp_path: Path, project: Path, warning_filter: str
) -> subprocess.CompletedProcess[bytes]:
    request = {
        "schema_version": 1,
        "action": "discover.preview",
        "project": str(project),
        "options": {"experimental": True, "show_content": True},
        "grants": {"install": False, "write": False, "network": False, "run": False},
    }
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8"}
    if "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-W",
            warning_filter,
            str(ROOT / "skills/reprollm/scripts/skill_runtime.py"),
            "--worker",
            "--cache-home",
            str(tmp_path / "state/responses"),
            "--identity",
            "b" * 64,
        ],
        input=json.dumps(request).encode(),
        env=environment,
        capture_output=True,
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize("warning_filter", ["always", "default"])
def test_public_invalid_escape_preview_keeps_worker_stream_private(
    tmp_path: Path, warning_filter: str
) -> None:
    # The pinned lm-eval process_sorted_buckets.py:38 has the same valid Python
    # literal. Parsing it warns without executing any author code.
    project = tmp_path / "research"
    project.mkdir()
    (project / "train.py").write_text(SOURCE, encoding="utf-8")
    result = worker_preview(tmp_path, project, warning_filter)
    assert result.returncode == 0
    reply = json.loads(result.stdout)
    assert reply["invocation"] == "handled_result" and reply["complete"] is True
    assert result.stderr == b""
    assert reply["diagnostics"] == [
        {
            "code": "discover_collection_warning",
            "category": "syntax_warning" if sys.version_info >= (3, 12) else "deprecation_warning",
            "count": 1,
            "count_is_lower_bound": False,
        }
    ]
    assert 'default="\\D"' in reply["data"]["messages"][1]["content"]
    assert (project / "train.py").read_text(encoding="utf-8") == SOURCE


def test_caller_warning_filter_does_not_change_discovery_input_bindings(tmp_path: Path) -> None:
    project = tmp_path / "research"
    project.mkdir()
    (project / "train.py").write_text(SOURCE, encoding="utf-8")
    displayed = worker_preview(tmp_path, project, "always")
    ignored = worker_preview(tmp_path, project, "ignore")
    assert displayed.returncode == ignored.returncode == 0
    assert displayed.stderr == ignored.stderr == b""
    first, second = json.loads(displayed.stdout), json.loads(ignored.stdout)
    assert first["data"] == second["data"]
    assert len(first["diagnostics"]) == 1 and second["diagnostics"] == []


def test_unexpected_nonwarning_worker_stderr_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import bootstrap

    class Manager(VerifiedManagerStub):
        def __init__(self, *args: Any) -> None:
            pass

        def status(self) -> dict[str, Any]:
            return {
                "state": "READY",
                "environment": "owned",
                "capabilities": ["contextual_word_scan"],
            }

        def environment_path(self, name: str) -> Path:
            return tmp_path / name

    monkeypatch.setattr(bootstrap, "Bootstrap", Manager)
    frame = Reply("discover.preview", cli_exit_code=0, data={"nothing_sent": True})
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 0, encode_reply(frame) + b"\n", b"UNEXPECTED_OS_STDERR_CANARY"
        ),
    )
    project = tmp_path / "research"
    project.mkdir()
    result = runtime.RuntimeExecutor(tmp_path / "owned")(
        Request("discover.preview", str(project), {"experimental": True}, Grants(install=False))
    )
    assert result.invocation == "internal_error" and not result.complete
    assert result.cli_exit_code == 0
    assert result.diagnostics == [{"code": "runtime_worker_stderr", "worker_exit_code": 0}]
    assert "UNEXPECTED_OS_STDERR_CANARY" not in json.dumps(result.as_dict())
