"""Finite own-session stdlib experiments through the actual operation worker.

Safety: only new nonce projects, DEVNULL, explicit safe environment, 12s child
deadline; no existing process signals, GPU/provider, numeric kill or killpg.
Tool interpreter is reused read-only; lease release is an explicit test fault.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_operations as operations  # noqa: E402
from skill_request import Grants, Request  # noqa: E402
from skill_run import preview_run  # noqa: E402

pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux pidfd run worker"),
]

CHILD = r"""
import hashlib,json,os,signal,sys,time
from pathlib import Path
nonce,mode=sys.argv[1:]
signal.signal(signal.SIGALRM, lambda *a: sys.exit(23))
signal.alarm(12)
if mode.startswith('term'):
 signal.signal(signal.SIGTERM,lambda *a: sys.exit(int(mode[4:])))
elif mode=='force':signal.signal(signal.SIGTERM,signal.SIG_IGN)
claim=next(Path(os.environ['PUBLIC_OWNED_HOME']).glob('operations/claims/*/status.json'))
owned=json.loads(claim.read_bytes())
assert owned['native_run_id']==os.environ['REPROLLM_RUN_ID']
witness={'nonce':nonce,'run_id':os.environ['REPROLLM_RUN_ID'],
 'bytecode':os.environ.get('PYTHONDONTWRITEBYTECODE','MISSING'),
 'path_sha256':hashlib.sha256(os.environ['PATH'].encode()).hexdigest()}
Path('witness.json').write_text(json.dumps(witness))
os.write(1,b'public stdout line\n');os.write(2,b'public stderr line\n')
if mode in ('term0','term7','force','signal'):
 while True:time.sleep(.02)
raise SystemExit(int(mode))
"""


@pytest.mark.parametrize(
    "mode,expected",
    [("0", 0), ("7", 7), ("term0", 0), ("term7", 7), ("signal", -15), ("force", -9)],
)
def test_actual_owned_run_worker_result_and_cancellation(tmp_path, monkeypatch, mode, expected):
    if not operations._platform():
        pytest.skip("Linux pidfd run ownership primitives unavailable")
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "owned-home"
    nonce = uuid.uuid4().hex
    (project / "child.py").write_text(CHILD, encoding="utf-8")
    (project / "reprollm.yaml").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": {"name": "public-owned"},
                "experiment": {"profiles": []},
            }
        ),
        encoding="utf-8",
    )
    selected = tmp_path / "selected-bin"
    selected.mkdir()
    (selected / "python").symlink_to(sys._base_executable)
    safe_env = {
        "PATH": str(selected),
        "PUBLIC_OWNED_HOME": str(home),
        "PYTHONPYCACHEPREFIX": str(tmp_path / "bytecode"),
    }
    real_popen = subprocess.Popen
    workers = []

    def owned_worker(argv, **kw):
        assert kw["stdout"] == kw["stderr"] == subprocess.DEVNULL and kw["start_new_session"]
        assert "env" not in kw
        process = real_popen(argv, env=safe_env, **kw)
        workers.append(process)
        return process

    monkeypatch.setattr(operations.subprocess, "Popen", owned_worker)

    class Lease:
        environment = Path(sys.executable).parent.parent
        claim = {"schema_version": 1, "environment": "a" * 32, "lease_id": "b" * 32}
        cleanup_failed = False

        def transfer(self):
            pass

        def reclaim(self):
            pass

    @contextlib.contextmanager
    def lease_factory(*args):
        yield Lease()

    options = {
        "argv": ["python", "child.py", nonce, mode],
        "capture_output": True,
        "no_snapshot": True,
    }
    preview = preview_run(
        Request("run.preview", str(project), options), root=project, identity="c" * 64
    )
    assert preview.data["start_ready"]
    request = Request(
        "run.start",
        str(project),
        options,
        Grants(install=False, run=True, write=True, plan_hash=preview.data["plan_hash"]),
    )

    def start(req):
        return operations.start(
            req,
            home=home,
            root=project,
            identity="c" * 64,
            manager=None,
            environment_name="a" * 32,
            lease_factory=lease_factory,
        )

    prepared = start(request)
    token = prepared.data["operation"]["operation_id"]
    assert prepared.data["operation"]["state"] == "PREPARED" and workers == []
    assert not (project / ".reprollm/runs").exists()
    request = dataclasses.replace(request, options={**options, "operation_id": token})
    started = start(request)
    assert started.data["operation"]["state"] == "STARTING" and len(workers) == 1

    def query(action):
        return operations.control(
            Request(
                action,
                str(project),
                {"operation_id": token},
                Grants(install=False, run=True, write=True),
            ),
            home=home,
            root=project,
        )

    try:
        deadline = time.monotonic() + 10
        while not (project / "witness.json").exists() and time.monotonic() < deadline:
            time.sleep(0.025)
        assert (project / "witness.json").exists(), query("run.status").as_dict()
        if mode in {"term0", "term7", "signal", "force"}:
            cancel = query("run.cancel")
            assert cancel.data["operation"]["cancel_requested"]
            assert cancel.data["operation"]["state"] in {"RUNNING", "FINALIZING", "COMPLETED"}
            if mode == "force":
                time.sleep(5.1)
                query("run.cancel")
        workers[0].wait(timeout=18)
        result = query("run.result")
        assert result.child_exit_code == expected, result.as_dict()
        assert result.data["result"]["data"]["record"]["exit_code"] == expected
        assert result.data["result"]["data"]["record_scope"] == "native_return"
        assert (
            result.data["operation"]["native_run_id"]
            == json.loads((project / "witness.json").read_bytes())["run_id"]
        )
        assert result.data["operation"]["cleanup_scope"] == "unknown_descendants"
        assert start(request).data["operation"]["operation_id"] == token and len(workers) == 1
        witness = json.loads((project / "witness.json").read_bytes())
        assert witness["nonce"] == nonce and witness["bytecode"] == "MISSING"
        assert witness["path_sha256"] == hashlib.sha256(str(selected).encode()).hexdigest()
    finally:
        for worker in workers:
            worker.wait(timeout=20)
