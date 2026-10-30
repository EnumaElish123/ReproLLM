"""Own stdlib children exercise the real recorder; hardware/Git metadata is stubbed."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux isolated run worker"),
]

WORKER = r"""
import json,os,socket,sys,traceback
from pathlib import Path
repository=Path(sys.argv[1]);project=Path(sys.argv[2])
options=json.loads(sys.argv[3]);reply_path=Path(sys.argv[4])
sys.path.insert(0,str(repository/'src'));sys.path.insert(0,str(repository/'skills/reprollm/scripts'))
def forbidden(*a,**k):raise AssertionError('No network from SK18 stdlib worker')
socket.socket.connect=forbidden
try:
 from reprollm.core import proc
 from reprollm.run import wrapper
 from reprollm.schemas.run_record import HardwareInfo
 from skill_request import Grants,Request,encode_reply
 from skill_run import preview_run,execute_run
 proc.run_cmd=lambda *a,**k:proc.CmdResult(127,'','instrumented metadata unavailable')
 wrapper.capture_hardware=lambda:HardwareInfo(cpu_count=1)
 p=preview_run(Request('run.preview',str(project),options),root=project,identity='b'*64)
 assert p.data['start_ready'],p.as_dict()
 class Lifecycle:
  def check_cancel(self):pass
  def bind_run(self,run_id):
   binding={'schema_version':1,'run_id':run_id,'plan_hash':p.data['plan_hash'],
            'preflight_available':p.data['preflight']['available']}
   Path(os.environ['PUBLIC_BINDING_FILE']).write_text(json.dumps(binding))
 grant=Grants(install=False,write=True,run=True,plan_hash=p.data['plan_hash'])
 request=Request('run.start',str(project),options,grant)
 reply=execute_run(request,root=project,identity='b'*64,lifecycle=Lifecycle())
 reply_path.write_bytes(encode_reply(reply)+b'\n')
except BaseException as error:
 failure={'harness_error_type':type(error).__name__,'traceback':traceback.format_exc()}
 reply_path.write_text(json.dumps(failure))
 raise
"""

CHILD = r"""
import hashlib,json,os,signal,sys
from pathlib import Path
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
source=Path('config.json');initial=json.loads(source.read_text())['alpha']
binding=json.loads(Path(os.environ['PUBLIC_BINDING_FILE']).read_text())
env_names=('PATH','PYTHONPATH','CUDA_VISIBLE_DEVICES','HTTPS_PROXY',
           'PUBLIC_TEST_API_KEY','PUBLIC_RUN_CONTROL','PYTHONPYCACHEPREFIX')
witness={
 'argv':sys.argv[1:],'cwd_name':Path.cwd().name,
 'python_sha256':digest(sys.executable),'prefix_sha256':digest(sys.prefix),
 'bytecode':os.environ.get('PYTHONDONTWRITEBYTECODE','MISSING'),
 'env_sha256':{k:digest(os.environ[k]) for k in env_names},
 'binding_matches':binding['run_id']==os.environ['REPROLLM_RUN_ID'],
 'alpha_consumed':initial,
}
Path('witness.json').write_text(json.dumps(witness))
source.write_text(json.dumps({'alpha':9})+'\n')
"""
CHILD += r"""
secret=os.environ['PUBLIC_TEST_API_KEY']
os.write(1,('api_key='+secret+'\n').encode())
os.write(2,('password='+secret+'\n').encode())
code=int(sys.argv[2])
if code<0:os.kill(os.getpid(),-code)
raise SystemExit(code)
"""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(tmp_path: Path, *, saved: bool, code: int, capture: bool, no_snapshot: bool):
    project = tmp_path / "public-experiment"
    project.mkdir()
    work = project / "work" if saved else project
    work.mkdir(exist_ok=True)
    (work / "child.py").write_text(CHILD, encoding="utf-8")
    before = b'{"alpha": 1}\n'
    (work / "config.json").write_bytes(before)
    command = ["python", "child.py", "--exit-code", str(code), "", "标签 with space"]
    relative = "work/" if saved else ""
    manifest = {
        "schema_version": 1,
        "project": {"name": "stdlib-control"},
        "experiment": {"profiles": []},
        "custom": {"alpha": 1},
        "execution": {
            "command": shlex.join(command) if saved else "python invalid | saved",
            "cwd": "work" if saved else None,
            "config_files": [relative + "config.json"],
        },
        "bindings": {"custom.alpha": {"config": relative + "config.json:alpha"}},
        "artifacts": {"outputs": [relative + "witness.json"]},
    }
    (project / "reprollm.yaml").write_text(json.dumps(manifest), encoding="utf-8")
    d = project / ".reprollm"
    d.mkdir()
    (d / "config.yaml").write_text("schema_version: 1\nrun: {env_capture: all}\n")
    options = {"capture_output": capture, "no_snapshot": no_snapshot, "name": "public-native"}
    if not saved:
        options["argv"] = command
    return project, work, options, before


@pytest.mark.parametrize(
    "saved,code,capture,no_snapshot,bytecode",
    [
        (True, 0, False, False, None),
        (False, 7, True, False, "0"),
        (False, 127, True, True, "1"),
        (False, -15, True, False, None),
    ],
    ids=["saved-zero-no-capture", "explicit-seven-capture", "explicit-127-no-snapshot", "signal"],
)
def test_real_native_run_evidence_and_original_environment(
    tmp_path, saved, code, capture, no_snapshot, bytecode
):
    from reprollm.run.codec import read_run_record
    from reprollm.schemas.state import State

    project, work, options, before = prepare(
        tmp_path, saved=saved, code=code, capture=capture, no_snapshot=no_snapshot
    )
    selected = tmp_path / "selected-bin"
    selected.mkdir()
    python = selected / "python"
    python.symlink_to(sys._base_executable)
    reply_path, binding_path = tmp_path / "safe-reply.json", tmp_path / "bound.json"
    secret = "OpaqueSyntheticSelectedCredential20261031"
    env = {
        "PATH": str(selected) + os.pathsep + os.defpath,
        "LANG": "C.UTF-8",
        "PYTHONPATH": "public-child-path-marker",
        "CUDA_VISIBLE_DEVICES": "public-no-gpu-control",
        "HTTPS_PROXY": "http://public-no-network.invalid:9",
        "PUBLIC_TEST_API_KEY": secret,
        "PUBLIC_RUN_CONTROL": "selected-public-baseline",
        "PUBLIC_BINDING_FILE": str(binding_path),
        "PYTHONPYCACHEPREFIX": str(tmp_path / "selected-bytecode-cache"),
    }
    if bytecode is not None:
        env["PYTHONDONTWRITEBYTECODE"] = bytecode
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            WORKER,
            str(ROOT),
            str(project),
            json.dumps(options),
            str(reply_path),
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    reply = json.loads(reply_path.read_bytes())
    assert result.returncode == 0, reply
    assert reply["invocation"] == "handled_result" and reply["child_exit_code"] == code
    assert reply["cli_exit_code"] is None and reply["gate_failed"] is None
    run_id = reply["data"]["run_id"]
    folder = project / ".reprollm/runs" / run_id
    assert len(list(folder.parent.iterdir())) == 1
    record, _ = read_run_record(folder / "run.json")
    assert record.exit_code == code and record.schema_version == 2
    assert record.status.value == ("interrupted" if code < 0 else "completed")
    assert record.command.argv[0] == "python"
    witness = json.loads((work / "witness.json").read_bytes())
    assert witness["argv"] == ["--exit-code", str(code), "", "标签 with space"]
    assert witness["binding_matches"] and witness["alpha_consumed"] == 1
    assert witness["cwd_name"] == work.name
    assert witness["python_sha256"] == sha(str(python).encode())
    assert witness["bytecode"] == (bytecode if bytecode is not None else "MISSING")
    for name in witness["env_sha256"]:
        assert witness["env_sha256"][name] == sha(env[name].encode())
    value = record.bindings_observed["custom.alpha"][0]
    assert value.value == 1 and value.source.type == "config"
    relative = ("work/" if saved else "") + "config.json"
    reference = next(item for item in record.files if item.path == relative)
    assert reference.sha256 == "sha256:" + sha(before)
    check = next(item for item in record.input_capture.checks if item.path == relative)
    assert check.change == "changed" and check.before.sha256 == reference.sha256
    assert check.after.sha256 == "sha256:" + sha((work / "config.json").read_bytes())
    if no_snapshot:
        assert reference.snapshot is None
    else:
        assert (folder / reference.snapshot).read_bytes() == before
    assert record.input_capture.consumption == "unverified"
    state = State.from_run(record, run_dir=folder).flatten()
    assert state["custom.alpha"].value == 1
    assert state["environment.python"].context.subject == "recorder"
    assert state["environment.python"].context.verification == "unverified"
    assert (folder / "stdout.log").exists() is capture
    assert (folder / "stderr.log").exists() is capture
    if capture:
        assert "<REDACTED:generic_kv>" in (folder / "stdout.log").read_text()
    for path in folder.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
    assert (
        secret.encode() not in reply_path.read_bytes()
        and secret.encode() not in binding_path.read_bytes()
    )
    source = next(item for item in record.files if item.path.endswith("child.py"))
    if source.snapshot is not None:
        ast.parse((folder / source.snapshot).read_bytes())


def test_actual_missing_executable_keeps_native_failed_record_and_unknown_exit(tmp_path):
    project = tmp_path / "missing-executable"
    project.mkdir()
    (project / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: public}\nexperiment: {profiles: []}\n"
    )
    reply_path = tmp_path / "safe-reply.json"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            WORKER,
            str(ROOT),
            str(project),
            json.dumps({"argv": ["/nonexistent-owned-SK18-executable"]}),
            str(reply_path),
        ],
        env={"PATH": os.defpath, "PUBLIC_BINDING_FILE": str(tmp_path / "bound.json")},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    reply = json.loads(reply_path.read_bytes())
    assert result.returncode == 0 and reply["invocation"] == "user_error"
    assert reply["child_exit_code"] is None and reply["data"]["run_id"]
    assert reply["data"]["record"]["status"] == "failed"
    assert reply["data"]["record"]["exit_code"] is None


def test_actual_explicit_no_manifest_runs_despite_unavailable_native_preflight(tmp_path):
    project = tmp_path / "explicit-no-manifest"
    project.mkdir()
    reply_path = tmp_path / "safe-reply.json"
    binding_path = tmp_path / "bound.json"
    code = (
        "import os;from pathlib import Path;"
        "Path('witness.txt').write_text(os.environ['REPROLLM_RUN_ID'])"
    )
    options = {"argv": [sys._base_executable, "-c", code]}
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            WORKER,
            str(ROOT),
            str(project),
            json.dumps(options),
            str(reply_path),
        ],
        env={
            "PATH": os.defpath,
            "PUBLIC_BINDING_FILE": str(binding_path),
            "PYTHONPYCACHEPREFIX": str(tmp_path / "selected-bytecode-cache"),
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    reply = json.loads(reply_path.read_bytes())
    binding = json.loads(binding_path.read_bytes())
    assert result.returncode == 0 and reply["invocation"] == "handled_result"
    assert reply["child_exit_code"] == 0 and not binding["preflight_available"]
    assert (project / "witness.txt").read_text() == binding["run_id"]
    assert reply["data"]["record"]["manifest"] is None
    assert any("no reprollm.yaml" in warning for warning in reply["data"]["record"]["warnings"])
    assert not (project / "reprollm.yaml").exists()
