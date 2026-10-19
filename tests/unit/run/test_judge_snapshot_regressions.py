"""R02-R follow-up: preserve the exact public judge inputs through real capture."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from reprollm.core import proc
from reprollm.diff.differ import diff_states
from reprollm.diff.severity import SeverityResolver
from reprollm.diff.state import from_run
from reprollm.run import wrapper
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.run_record import HardwareInfo, RunRecord
from tests.conftest import CmdStub

pytestmark = pytest.mark.security

FIXTURE = Path(__file__).parents[2] / "fixtures/run/judge-source-fidelity"
MINIMAL_PYTHON = 'print(f"x: {a[\'b\']}")\nopenai.api_key = api_dict["api_key"]\n'
SECRET = "syntheticJudgeCanaryABC123"


@pytest.fixture(autouse=True)
def bounded_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(proc, "run_cmd", CmdStub().on("git", returncode=128))
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    monkeypatch.setattr(wrapper.envinfo, "installed_versions", lambda: {})
    monkeypatch.setattr(wrapper.socket, "gethostname", lambda: "judge-capture-host")
    monkeypatch.setattr(wrapper.getpass, "getuser", lambda: "judge-capture-user")


def _execute(root: Path, cap: int = 256, *, snapshot: bool = True) -> tuple[RunRecord, Path]:
    manifest = {
        "schema_version": 1,
        "project": {"name": "judge-source-fidelity"},
        "experiment": {"profiles": []},
        "models": {"judge": {"provider": "other", "id": "fixed-judge"}},
        "prompts": {"judge": {"text": "Use a finite score."}},
        "execution": {"config_files": ["common.py", "judge_prompts.jsonl"]},
        "evaluation": {"judge": {"params": {"max_tokens": cap}}},
        "bindings": {"evaluation.judge.params.max_tokens": {"cli": "--max-tokens"}},
    }
    (root / "reprollm.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    child = (
        "import ast, hashlib, json, pathlib, sys\n"
        "source = pathlib.Path('common.py').read_bytes()\n"
        "rubric = pathlib.Path('judge_prompts.jsonl').read_bytes()\n"
        "ast.parse(source)\n"
        "rows = [json.loads(line) for line in rubric.splitlines() if line.strip()]\n"
        "receipt = {'source_sha256': hashlib.sha256(source).hexdigest(),\n"
        " 'rubric_sha256': hashlib.sha256(rubric).hexdigest(), 'rows': len(rows),\n"
        " 'max_tokens': int(sys.argv[2])}\n"
        "pathlib.Path('consumed.json').write_text(json.dumps(receipt))\n"
        "sys.exit(7)\n"
    )
    (root / "child.py").write_text(child, encoding="utf-8")
    record = wrapper.execute(
        [sys.executable, "child.py", "--max-tokens", str(cap)],
        root=root,
        cwd=root,
        run_dir=wrapper.create_run_dir(root),
        capture_output=True,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=snapshot,
    )
    return record, root / ".reprollm/runs" / record.run_id


def _write_originals(root: Path) -> dict[str, bytes]:
    provenance = json.loads((FIXTURE / "provenance.json").read_text())
    originals = {}
    for entry in provenance["entries"]:
        raw = (FIXTURE / entry["retained_file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        name = Path(entry["source_path"]).name
        (root / name).write_bytes(raw)
        originals[name] = raw
    return originals


def test_minimal_python_symbols_and_fstring_keep_exact_source(tmp_path: Path) -> None:
    ast.parse(MINIMAL_PYTHON)
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    assert privacy.text(MINIMAL_PYTHON, python_source=True) == (MINIMAL_PYTHON, 0)


def test_jsonl_role_labels_and_newline_escapes_keep_exact_source(tmp_path: Path) -> None:
    source = (
        '{"prompt": "### Assistant A:\\n{answer}", "stop": "</s>"}\r\n'
        '{"prompt": "### Assistant B:\\n{other}", "limit": 32}\r\n'
    )
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    assert privacy.text(source) == (source, 0)


@pytest.mark.parametrize("serialized", [False, True])
@pytest.mark.parametrize(
    "path",
    [
        r"C:\new\file",
        r"A:\new",
        r"\\private-server\share\file",
        "/private-owner/file",
        "file:///private-owner/file",
    ],
)
def test_decoded_json_paths_still_redact_beside_safe_role_labels(
    tmp_path: Path, path: str, serialized: bool
) -> None:
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    prompt = "### Assistant A:\n{answer}"
    content = {"prompt": prompt, "path": path}
    source = json.dumps({"nested": json.dumps(content)} if serialized else content)
    safe, count = privacy.text(source)
    decoded = json.loads(safe)
    if serialized:
        decoded = json.loads(decoded["nested"])
    assert decoded == {"prompt": prompt, "path": "<REDACTED:path>"}
    assert count > 0 and privacy.text(safe) == (safe, 0)


def test_jsonl_escaped_secret_keys_on_later_rows_keep_context(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    source = '{"prompt":"### Assistant A:\\n{answer}"}\n'
    source += '{"settings":{"api\\u005fkey":"' + SECRET + '"}}\n'
    safe, count = privacy.text(source)
    rows = [json.loads(line) for line in safe.splitlines()]
    assert rows == [
        {"prompt": "### Assistant A:\n{answer}"},
        {"settings": {"api_key": "<REDACTED:generic_kv>"}},
    ]
    assert count > 0 and SECRET not in safe
    assert privacy.text(safe) == (safe, 0)


def test_plain_scalar_identity_is_not_exempted_by_json_recognition(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="12345", username="null")
    assert privacy.text("12345") == ("<REDACTED:hostname>", 1)
    assert privacy.text("null") == ("<REDACTED:username>", 1)


@pytest.mark.parametrize("snapshot", [False, True])
def test_original_judge_sources_survive_real_capture_and_child_exit(
    tmp_path: Path, snapshot: bool
) -> None:
    originals = _write_originals(tmp_path)
    record, folder = _execute(tmp_path, snapshot=snapshot)
    assert record.exit_code == 7 and record.warnings == []
    consumed = json.loads((tmp_path / "consumed.json").read_text())
    assert consumed == {
        "source_sha256": hashlib.sha256(originals["common.py"]).hexdigest(),
        "rubric_sha256": hashlib.sha256(originals["judge_prompts.jsonl"]).hexdigest(),
        "rows": 8,
        "max_tokens": 256,
    }
    for name, raw in originals.items():
        captured = next(item for item in record.files if item.path == name)
        assert captured.sha256 == "sha256:" + hashlib.sha256(raw).hexdigest()
        assert captured.size_bytes == len(raw) and captured.redacted is False
        assert (captured.snapshot is not None) is snapshot
        if captured.snapshot is not None:
            assert (folder / captured.snapshot).read_bytes() == raw
        assert (tmp_path / name).read_bytes() == raw
    assert record.input_capture is not None
    assert record.input_capture.consumption == "unverified"
    assert all(check.change == "unchanged" for check in record.input_capture.checks)
    flat = from_run(record, run_dir=folder).flatten()
    assert flat["evaluation.judge.params.max_tokens"].value == 256


def test_exact_sources_do_not_mask_the_real_judge_cap_diff(tmp_path: Path) -> None:
    _write_originals(tmp_path)
    a, a_dir = _execute(tmp_path, 256)
    b, b_dir = _execute(tmp_path, 384)
    states = [from_run(record, run_dir=folder) for record, folder in ((a, a_dir), (b, b_dir))]
    report = diff_states(*states, SeverityResolver())
    changes = [c for c in report.changes if c.path == "evaluation.judge.params.max_tokens"]
    assert len(changes) == 1
    assert (changes[0].a, changes[0].b, changes[0].severity) == (256, 384, "HIGH")
    assert diff_states(states[0], states[0], SeverityResolver()).changes == []


@pytest.mark.parametrize("kind", ["python", "jsonl", "malformed-python", "malformed-jsonl"])
def test_capture_keeps_secret_protection_after_lexical_fidelity_repair(
    tmp_path: Path, kind: str
) -> None:
    _write_originals(tmp_path)
    if kind.endswith("python"):
        source = MINIMAL_PYTHON + f'payload = \'{{"api_key":"{SECRET}"}}\'\n'
        if kind.startswith("malformed"):
            source += f'password = "{SECRET}'
        (tmp_path / "common.py").write_text(source, encoding="utf-8")
    else:
        source = '{"prompt":"### Assistant A:\\n{answer}"}\n'
        source += json.dumps({"settings": {"api_key": SECRET}}) + "\n"
        if kind.startswith("malformed"):
            source += '{"password":"' + SECRET
        (tmp_path / "judge_prompts.jsonl").write_text(source, encoding="utf-8")
    # A failing child still leaves a safe record; malformed inputs are not executed.
    record, folder = _execute(tmp_path)
    for path in folder.rglob("*"):
        if path.is_file():
            raw = path.read_bytes()
            assert SECRET.encode() not in raw
            assert b"judge-capture-host" not in raw and b"judge-capture-user" not in raw
    assert record.exit_code in {1, 7}
    if not kind.startswith("malformed"):
        assert record.exit_code == 7 and record.warnings == []
        name = "common.py" if kind == "python" else "judge_prompts.jsonl"
        captured = next(item for item in record.files if item.path == name)
        assert captured.redacted and captured.snapshot is not None
    assert not list(folder.glob("*.tmp"))
