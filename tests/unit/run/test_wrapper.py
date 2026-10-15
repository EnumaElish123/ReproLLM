"""M5-T04 child behavior, crash evidence and safe artifact persistence."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import sys
from pathlib import Path
from typing import Any

import pytest

from reprollm.core import proc
from reprollm.core.errors import UserError
from reprollm.run import wrapper
from reprollm.schemas.run_record import HardwareInfo, RunStatus
from tests.conftest import CmdStub, materialize_repo

REAL_RUN_CMD = proc.run_cmd


@pytest.fixture(autouse=True)
def bounded_metadata(monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub) -> None:
    stub_run_cmd.on("git", returncode=128)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    monkeypatch.setattr(wrapper.envinfo, "installed_versions", lambda: {"torch": "2.8.0"})
    monkeypatch.setattr(wrapper.socket, "gethostname", lambda: "private-test-host")
    monkeypatch.setattr(wrapper.getpass, "getuser", lambda: "private-test-user")


def execute(root: Path, script: str, **options: Any) -> Any:
    return wrapper.execute(
        [sys.executable, "-c", script],
        root=root,
        cwd=root,
        run_dir=wrapper.create_run_dir(root),
        capture_output=options.pop("capture_output", False),
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=True,
        **options,
    )


def run_dir(root: Path, record: Any) -> Path:
    return root / ".reprollm/runs" / record.run_id


def test_input_baseline_precedes_child_config_rewrite(tmp_path: Path) -> None:
    """The child's witness is independent of the recorder's config observation."""
    from reprollm.schemas.state import State

    before = b'{"temperature": 0.1}\n'
    after = b'{"temperature": 0.9}\n'
    (tmp_path / "config.json").write_bytes(before)
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: example}\nexperiment: {profiles: []}\n"
        "execution: {config_files: [config.json]}\n"
        "bindings:\n  generation.temperature: {config: 'config.json:temperature'}\n"
        "artifacts: {outputs: [consumed.json]}\n"
    )
    record = execute(
        tmp_path,
        "import json; from pathlib import Path; "
        "value=json.loads(Path('config.json').read_text())['temperature']; "
        "Path('consumed.json').write_text(json.dumps({'temperature':value})); "
        f"Path('config.json').write_bytes({after!r})",
    )
    assert record.exit_code == 0
    assert json.loads((tmp_path / "consumed.json").read_text()) == {"temperature": 0.1}
    assert (tmp_path / "config.json").read_bytes() == after
    assert record.bindings_observed["generation.temperature"][0].value == 0.1
    reference = next(item for item in record.files if item.path == "config.json")
    assert reference.sha256 == "sha256:" + hashlib.sha256(before).hexdigest()
    assert (run_dir(tmp_path, record) / reference.snapshot).read_bytes() == before
    state = State.from_run(record, run_dir=run_dir(tmp_path, record))
    assert state.flatten()["generation.temperature"].value == 0.1
    assert [item.path for item in record.artifacts] == ["consumed.json"]


@pytest.mark.security
def test_snapshot_keeps_executable_source_and_regex_while_removing_private_values(
    tmp_path: Path,
) -> None:
    import ast

    import yaml

    from tests.conftest import FIXTURES_ROOT

    source = (FIXTURES_ROOT / "secrets/run_source_fidelity.py.txt").read_bytes()
    regex = b'patterns: ["\\\\$", "\\\\.", "(\\\\-?[0-9.,]+)"]\n'
    unsafe = (
        b"# cache=/private-owner/cache unc=\\\\private-server\\share\\file\n"
        b"# token=hf_01234567890123456789\n"
    )
    (tmp_path / "entry.py").write_bytes(source + unsafe)
    (tmp_path / "task.yaml").write_bytes(regex)
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: fidelity}\nexperiment: {profiles: []}\n"
        "execution: {config_files: [entry.py, task.yaml]}\n"
    )
    record = wrapper.execute(
        [sys.executable, "entry.py"],
        root=tmp_path,
        cwd=tmp_path,
        run_dir=wrapper.create_run_dir(tmp_path),
        capture_output=True,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=True,
    )
    assert record.exit_code == 0
    folder = run_dir(tmp_path, record)
    refs = {item.path: item for item in record.files}
    saved_source = (folder / refs["entry.py"].snapshot).read_bytes()
    assert saved_source == source + (
        b"# cache=<REDACTED:path> unc=<REDACTED:path>\n# token=<REDACTED:huggingface>\n"
    )
    ast.parse(saved_source)
    assert (folder / refs["task.yaml"].snapshot).read_bytes() == regex
    assert yaml.safe_load(regex)["patterns"] == [r"\$", r"\.", r"(\-?[0-9.,]+)"]
    assert refs["entry.py"].sha256 == "sha256:" + hashlib.sha256(source + unsafe).hexdigest()
    assert refs["entry.py"].redacted and not refs["task.yaml"].redacted
    assert (folder / "stdout.log").read_text() == "source consumed\n"
    for artifact in folder.rglob("*"):
        if artifact.is_file():
            data = artifact.read_bytes()
            for canary in (b"private-owner", b"private-server", b"hf_01234567890123456789"):
                assert canary not in data


def test_child_document_rewrites_keep_original_baselines_and_exit_seven(tmp_path: Path) -> None:
    from reprollm.schemas.state import State

    manifest = (
        b"schema_version: 1\nproject: {name: example}\nexperiment: {profiles: []}\n"
        b"generation: {temperature: 0.1}\n"
        b"execution: {config_files: [config.json]}\n"
        b"prompts: {system: {path: prompt.txt}}\n"
        b"bindings: {generation.temperature: {config: 'config.json:temperature'}}\n"
        b"artifacts: {outputs: [witness.json]}\n"
    )
    lock = (
        "schema_version: 1\nreprollm_version: 0.6.2\n"
        "generated_at: 2026-10-14T01:00:00Z\nresolution: {mode: offline}\n"
        f"manifest_sha256: sha256:{hashlib.sha256(manifest).hexdigest()}\n"
        "generation: {temperature: 0.1}\n"
    ).encode()
    before = {
        "reprollm.yaml": manifest,
        "reprollm.lock": lock,
        "config.json": b'{"temperature": 0.1}\n',
        "prompt.txt": b"baseline prompt\n",
    }
    for name, data in before.items():
        (tmp_path / name).write_bytes(data)
    record = execute(
        tmp_path,
        "import json,hashlib,sys; from pathlib import Path; "
        "names=['reprollm.yaml','reprollm.lock','config.json','prompt.txt']; "
        "witness={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in names}; "
        "Path('witness.json').write_text(json.dumps(witness)); "
        f"Path('reprollm.yaml').write_bytes({manifest.replace(b'0.1', b'0.9')!r}); "
        f"Path('reprollm.lock').write_bytes({lock.replace(b'0.1', b'0.9')!r}); "
        "Path('config.json').write_text('{\"temperature\": 0.9}'); "
        "Path('prompt.txt').write_text('changed prompt'); sys.exit(7)",
    )
    assert record.exit_code == 7
    assert json.loads((tmp_path / "witness.json").read_text()) == {
        name: hashlib.sha256(data).hexdigest() for name, data in before.items()
    }
    assert record.input_capture is not None
    assert {item.path: item.change for item in record.input_capture.checks} == {
        name: "changed" for name in before
    }
    for reference in (record.manifest, record.lock):
        assert reference is not None
        assert reference.sha256 == "sha256:" + hashlib.sha256(before[reference.path]).hexdigest()
        assert (run_dir(tmp_path, record) / reference.snapshot).read_bytes() == before[
            reference.path
        ]
    state = State.from_run(record, run_dir=run_dir(tmp_path, record))
    assert state.flatten()["generation.temperature"].value == 0.1
    assert state.flatten()["generation.temperature"].context.phase == "pre_child"
    assert [item.path for item in record.artifacts] == ["witness.json"]


def test_child_environment_prewrite_and_nonzero_exit(tmp_path: Path) -> None:
    record = execute(
        tmp_path,
        "import os,json,pathlib,sys; "
        "p=pathlib.Path(os.environ['REPROLLM_RUN_DIR']); "
        "r=json.loads((p/'run.json').read_text()); "
        "assert r['status']=='running'; "
        "assert r['run_id']==os.environ['REPROLLM_RUN_ID']; "
        "sys.exit(3)",
    )
    assert record.status == RunStatus.COMPLETED and record.exit_code == 3
    assert record.command.cwd == "."
    assert record.started_at is not None and record.ended_at is not None
    assert record.duration_seconds >= 0
    folder = run_dir(tmp_path, record)
    data = json.loads((folder / "run.json").read_text())
    assert data["status"] == "completed" and data["exit_code"] == 3
    assert not (folder / "stdout.log").exists()
    assert not (folder / "stderr.log").exists()
    assert not list(folder.glob("*.tmp"))


def test_capture_tees_raw_output_but_redacts_saved_streams(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "hf_01234567890123456789"
    record = execute(
        tmp_path,
        "import sys; "
        f"print('{secret}'); "
        "print('-----BEGIN RSA PRIVATE KEY-----'); print('private-body'); "
        "print('-----END RSA PRIVATE KEY-----'); "
        "print('sk-0123456789abcdef', file=sys.stderr)",
        capture_output=True,
    )
    terminal = capsys.readouterr()
    assert secret in terminal.out and "private-body" in terminal.out
    assert "sk-0123456789abcdef" in terminal.err
    folder = run_dir(tmp_path, record)
    saved = (folder / "stdout.log").read_text()
    assert secret not in saved and "private-body" not in saved
    assert "<REDACTED:huggingface>" in saved and "<REDACTED:pem>" in saved
    assert (folder / "stderr.log").read_text() == "<REDACTED:openai>\n"


def test_no_shell_and_original_environment_are_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNLISTED_CHILD_INPUT", "child-value")
    script = (
        "import os,sys; assert os.environ['UNLISTED_CHILD_INPUT']=='child-value'; "
        "assert sys.argv[1:] == ['literal; not-a-command', '$UNLISTED_CHILD_INPUT']"
    )
    record = wrapper.execute(
        [sys.executable, "-c", script, "literal; not-a-command", "$UNLISTED_CHILD_INPUT"],
        root=tmp_path,
        cwd=tmp_path,
        run_dir=wrapper.create_run_dir(tmp_path),
        capture_output=False,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=True,
    )
    assert record.exit_code == 0
    assert "UNLISTED_CHILD_INPUT" not in record.environment.env


def test_all_persisted_surfaces_remove_machine_identity_and_absolute_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stub_run_cmd: CmdStub,
) -> None:
    private = f"{tmp_path}/input.txt private-test-host private-test-user /opt/private/path"
    (tmp_path / "input.txt").write_text(private)
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: example}\nexperiment: {profiles: []}\n"
        f"execution: {{config_files: [input.txt]}}\ncustom: {{note: '{private}'}}\n"
    )
    (tmp_path / "reprollm.lock").write_text(f"schema_version: 1\nnote: '{private}'\n")
    monkeypatch.setenv("SLURM_NODELIST", "private-test-host")
    monkeypatch.setenv("PYTHON_NOTE", private)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-0123456789abcdef")
    record = execute(tmp_path, f"print({private!r})", capture_output=True, name=private)
    assert record.environment.env["OPENAI_API_KEY"].present is True
    assert record.environment.hostname_sha256 == (
        "sha256:" + hashlib.sha256(b"private-test-host").hexdigest()
    )
    assert record.files[0].redacted is True
    for path in run_dir(tmp_path, record).rglob("*"):
        if path.is_file():
            content = path.read_text()
            for value in (
                str(tmp_path),
                "private-test-host",
                "private-test-user",
                "/opt/private/path",
            ):
                assert value not in content, path.name


def test_dirty_patch_is_redacted_and_hashes_saved_bytes(
    tmp_path: Path, stub_run_cmd: CmdStub
) -> None:
    stub_run_cmd.on("git", "rev-parse", "--is-inside-work-tree", stdout="true\n")
    stub_run_cmd.on("git", "status", "--porcelain", stdout=" M config.py\n?? notes.txt\n")
    stub_run_cmd.on("git", "diff", stdout='+password = "hunter2hunter2"\n')
    record = execute(tmp_path, "pass")
    assert record.code.dirty and record.code.modified_count == 1
    assert record.code.untracked_count == 1
    patch = (run_dir(tmp_path, record) / "patch.diff").read_bytes()
    assert b"hunter2hunter2" not in patch and b"<REDACTED:generic_kv>" in patch
    assert record.code.patch_sha256 == "sha256:" + hashlib.sha256(patch).hexdigest()
    assert record.code.patch_file == "patch.diff"


def test_metadata_failure_keeps_child_exit_and_other_captures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> HardwareInfo:
        raise RuntimeError("sensitive exception text")

    monkeypatch.setattr(wrapper, "capture_hardware", fail)
    record = execute(tmp_path, "import sys; sys.exit(7)")
    assert record.exit_code == 7 and record.status == RunStatus.COMPLETED
    assert record.environment is not None
    assert any("hardware" in w and "RuntimeError" in w for w in record.warnings)
    assert "sensitive exception text" not in (run_dir(tmp_path, record) / "run.json").read_text()


def test_failure_to_start_keeps_evidence_and_is_usage_error(tmp_path: Path) -> None:
    folder = wrapper.create_run_dir(tmp_path)
    with pytest.raises(UserError, match="command"):
        wrapper.execute(
            ["reprollm-test-no-such-executable"],
            root=tmp_path,
            cwd=tmp_path,
            run_dir=folder,
            capture_output=False,
            env_capture="allowlist",
            extra_allowlist=[],
            snapshot=True,
        )
    saved = json.loads((folder / "run.json").read_text())
    assert saved["status"] == "failed"


def test_run_id_collision_is_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hexes = iter(["abcdef", "abcdef", "012345"])
    monkeypatch.setattr(wrapper.secrets, "token_hex", lambda n: next(hexes))
    one = wrapper.create_run_dir(tmp_path)
    two = wrapper.create_run_dir(tmp_path)
    assert one != two and one.name.endswith("-abcdef") and two.name.endswith("-012345")


@pytest.mark.linux_only
@pytest.mark.skipif(sys.platform != "linux", reason="POSIX forwarding runs on Linux CI")
@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_signal_is_forwarded_and_handlers_restored(tmp_path: Path, sig: signal.Signals) -> None:
    previous = signal.getsignal(sig)
    script = (
        "import os,signal,time; "
        "signal.signal(signal.SIGINT, signal.SIG_DFL); "
        f"os.kill(os.getppid(), {int(sig)}); time.sleep(10)"
    )
    record = execute(tmp_path, script)
    assert record.exit_code == -int(sig) and record.status == RunStatus.INTERRUPTED
    assert signal.getsignal(sig) == previous


def test_run_directory_symlink_cannot_write_outside_repository(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / ".reprollm").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    with pytest.raises(UserError, match="run directory"):
        wrapper.create_run_dir(root)
    assert list(outside.iterdir()) == []


def test_dirty_tree_fixture_patch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = materialize_repo("dirty_tree", tmp_path)
    monkeypatch.setattr(proc, "run_cmd", REAL_RUN_CMD)
    config = root / "configs/run.yaml"
    config.write_text(config.read_text() + '\npassword: "hunter2hunter2"\n')
    record = execute(root, "pass")
    patch = (run_dir(root, record) / "patch.diff").read_text()
    assert record.code.dirty and record.code.modified_count == 1
    assert "extra: 1" in patch and "hunter2hunter2" not in patch
    assert "<REDACTED:generic_kv>" in patch


def test_final_record_write_retries_without_losing_child_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replace = os.replace
    attempts = 0
    failed_final = False

    def fail_once(source: Path, destination: Path) -> None:
        nonlocal attempts, failed_final
        attempts += 1
        status = json.loads(source.read_text())["status"]
        if status == "completed" and not failed_final:
            failed_final = True
            raise PermissionError("private-error-content")
        replace(source, destination)

    monkeypatch.setattr(wrapper.os, "replace", fail_once)
    record = execute(tmp_path, "import sys; sys.exit(5)")
    assert failed_final and attempts == 4 and record.exit_code == 5
    saved = (run_dir(tmp_path, record) / "run.json").read_text()
    assert '"exit_code": 5' in saved and "PermissionError" in saved
    assert "private-error-content" not in saved
    assert not list(run_dir(tmp_path, record).glob("*.tmp"))


def test_input_baseline_and_outputs_use_separate_phases(tmp_path: Path) -> None:
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: example}\nexperiment: {profiles: []}\n"
        "execution: {config_files: [config.json]}\nbindings:\n"
        "  generation.temperature: {config: 'config.json:temperature'}\n"
        "artifacts: {outputs: ['result.json']}\n"
    )
    (tmp_path / "config.json").write_text('{"temperature":0.0}')
    record = execute(
        tmp_path,
        "import pathlib; pathlib.Path('result.json').write_text('{\"score\":1}')",
    )
    assert [(x.path, x.size_bytes) for x in record.artifacts] == [("result.json", 11)]
    assert record.bindings_observed["generation.temperature"][0].value == 0.0
    assert record.files[0].path == "config.json" and record.files[0].snapshot is not None
    assert record.schema_version == 2 and record.input_capture is not None
    assert record.input_capture.consumption == "unverified"
    check = next(item for item in record.input_capture.checks if item.path == "config.json")
    assert check.change == "unchanged"
    assert check.before.sha256 == check.after.sha256 == record.files[0].sha256


def test_invalid_manifest_prevents_child_execution(tmp_path: Path) -> None:
    (tmp_path / "reprollm.yaml").write_text("secret: [sensitive-payload")
    with pytest.raises(UserError, match="cannot load reprollm.yaml") as exc:
        execute(tmp_path, "raise RuntimeError('must not run')")
    assert "sensitive-payload" not in str(exc.value)


def test_baseline_sanitizer_failure_does_not_hide_command_start_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = wrapper.RunPrivacy.value

    def fail_captured_inputs(self: Any, value: Any, keys: tuple[str, ...] = ()) -> Any:
        if getattr(value, "input_capture", None) is not None and value.input_capture.checks:
            raise ValueError("private-input-failure-canary")
        return original(self, value, keys)

    monkeypatch.setattr(wrapper.RunPrivacy, "value", fail_captured_inputs)
    directory = wrapper.create_run_dir(tmp_path)
    with pytest.raises(UserError, match="cannot start command") as failure:
        wrapper.execute(
            [str(tmp_path / "missing-child")],
            root=tmp_path,
            cwd=tmp_path,
            run_dir=directory,
            capture_output=False,
            env_capture="allowlist",
            extra_allowlist=[],
            snapshot=True,
        )
    saved = json.loads((directory / "run.json").read_text())
    assert saved["status"] == "failed" and saved["schema_version"] == 2
    assert "private-input-failure-canary" not in str(failure.value)
    assert "private-input-failure-canary" not in json.dumps(saved)
