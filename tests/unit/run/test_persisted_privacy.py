"""R02-R real runtime evidence and every owned persistence surface."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from reprollm.core import proc
from reprollm.core._toml import tomllib
from reprollm.core.bindings import observe
from reprollm.core.errors import UserError
from reprollm.core.yaml_io import dump_yaml, load_lock, load_manifest
from reprollm.diff.differ import diff_states
from reprollm.diff.severity import SeverityResolver
from reprollm.diff.state import from_run
from reprollm.export.exporter import build_input, render
from reprollm.run import wrapper
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.lock import InferenceLock, Lock, Provenance, ResolutionMode
from reprollm.schemas.manifest import BindingSpec
from reprollm.schemas.run_record import HardwareInfo, RunRecord, RunStatus
from tests.conftest import CmdStub

pytestmark = pytest.mark.security

SECRET = "syntheticPlainCanaryABC123"
SECOND_SECRET = "secondPlainCanaryXYZ456"
SAFE = "<REDACTED:generic_kv>"
BENIGN = {
    "max_tokens": 32,
    "TOKENIZERS_PARALLELISM": False,
    "model": "Qwen/Qwen3-32B",
    "cache": "cache/models",
    "glob": "outputs/**/*.json",
    "stop": "</s>",
}
SCRIPT = (
    "import hashlib,json,pathlib,sys; "
    "data=json.loads(pathlib.Path('config.json').read_text()); "
    "receipt={'secret_sha256':hashlib.sha256(data['settings']['api_key'].encode()).hexdigest(),"
    "'max_tokens':data['settings']['max_tokens'],'argv':sys.argv[1:]}; "
    "pathlib.Path('consumed.json').write_text(json.dumps(receipt)); "
    "print(json.dumps(data)); print(json.dumps(data),file=sys.stderr); sys.exit(7)"
)


@pytest.fixture(autouse=True)
def bounded_metadata(monkeypatch: pytest.MonkeyPatch) -> CmdStub:
    stub = CmdStub().on("git", returncode=128)
    monkeypatch.setattr(proc, "run_cmd", stub)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    monkeypatch.setattr(wrapper.envinfo, "installed_versions", lambda: {})
    monkeypatch.setattr(wrapper.socket, "gethostname", lambda: "capture-test-host")
    monkeypatch.setattr(wrapper.getpass, "getuser", lambda: "capture-test-user")
    return stub


def _seed(root: Path, secret: str = SECRET) -> dict[str, Any]:
    settings = {"api_key": secret, "nested": [{"password": secret}], **BENIGN}
    data = {"settings": settings}
    (root / "config.json").write_text(json.dumps(data), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "project": {"name": "example"},
        "experiment": {"profiles": []},
        "execution": {"config_files": ["config.json"]},
        "bindings": {
            "custom.settings": {"config": "config.json:settings"},
            "custom.api_key": {"config": "config.json:settings.api_key"},
            "custom.auth_token": {"cli": "--auth-token"},
        },
        "custom": {"embedded": json.dumps({"api_key": secret})},
    }
    (root / "reprollm.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    # Legacy unsafe input is intentional: the R02 writer now rejects new writes.
    lock = Lock(
        reprollm_version="0.1.1",
        generated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        manifest_sha256="sha256:legacy",
        resolution=ResolutionMode(mode="offline"),
        inference=InferenceLock(
            backend="other",
            version=Provenance(value=None, source="unsupported_backend", confidence="unresolved"),
            params={"api_key": secret, **BENIGN},
        ),
    )
    (root / "reprollm.lock").write_text(dump_yaml(lock), encoding="utf-8")
    return data


def _execute(
    root: Path,
    *,
    snapshot: bool = True,
    output: bool = True,
    argv: list[str] | None = None,
) -> RunRecord:
    return wrapper.execute(
        argv or [sys.executable, "-c", SCRIPT],
        root=root,
        cwd=root,
        run_dir=wrapper.create_run_dir(root),
        capture_output=output,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=snapshot,
    )


def _folder(root: Path, record: RunRecord) -> Path:
    return root / ".reprollm/runs" / record.run_id


def _assert_owned_safe(folder: Path, *secrets: str) -> None:
    for path in folder.rglob("*"):
        if path.is_file():
            contents = path.read_bytes()
            for secret in (*secrets, "capture-test-host", "capture-test-user"):
                assert secret.encode() not in contents, path.relative_to(folder)
    assert not list(folder.glob("*.tmp"))


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("output", [False, True])
def test_real_child_keyed_values_are_safe_on_every_owned_surface(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    bounded_metadata: CmdStub,
    snapshot: bool,
    output: bool,
) -> None:
    data = _seed(tmp_path)
    original = (tmp_path / "config.json").read_bytes()
    bounded_metadata.on("git", "rev-parse", "--is-inside-work-tree", stdout="true\n")
    bounded_metadata.on("git", "status", "--porcelain", stdout=" M config.json\n")
    bounded_metadata.on("git", "diff", stdout=f'+ "api_key": "{SECRET}",\n')
    record = _execute(tmp_path, snapshot=snapshot, output=output)
    assert record.exit_code == 7 and record.status == RunStatus.COMPLETED
    receipt = json.loads((tmp_path / "consumed.json").read_text())
    assert receipt["secret_sha256"] == hashlib.sha256(SECRET.encode()).hexdigest()
    assert receipt["max_tokens"] == 32
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET)
    assert record.warnings == []
    observed = record.bindings_observed["custom.settings"][0].value
    assert observed == {"api_key": SAFE, "nested": [{"password": SAFE}], **BENIGN}
    leaf = record.bindings_observed["custom.api_key"][0]
    assert leaf.value == SAFE and leaf.source.key == "settings.api_key"
    source = next(item for item in record.files if item.path == "config.json")
    assert source.sha256 == "sha256:" + hashlib.sha256(original).hexdigest()
    assert source.redacted is snapshot
    assert (source.snapshot is not None) is snapshot
    if snapshot:
        saved = json.loads((folder / source.snapshot).read_text())
        assert saved == {"settings": observed}
    assert load_manifest(folder / "manifest.yaml").bindings["custom.api_key"].config == (
        "config.json:settings.api_key"
    )
    assert load_lock(folder / "lock.yaml").inference.params["api_key"] == SAFE
    assert b"<REDACTED:generic_kv>" in (folder / "patch.diff").read_bytes()
    terminal = capsys.readouterr()
    if output:
        assert SECRET in terminal.out and SECRET in terminal.err
        assert json.loads((folder / "stdout.log").read_text()) == {"settings": observed}
        assert json.loads((folder / "stderr.log").read_text()) == {"settings": observed}
    else:
        assert not (folder / "stdout.log").exists() and not (folder / "stderr.log").exists()
    assert json.loads((tmp_path / "config.json").read_text()) == data


@pytest.mark.parametrize("equals", [False, True])
def test_split_and_equals_secret_argv_preserves_child_and_source(
    tmp_path: Path, equals: bool
) -> None:
    _seed(tmp_path)
    args = [f"--auth-token={SECOND_SECRET}"] if equals else ["--auth-token", SECOND_SECRET]
    record = _execute(tmp_path, output=False, argv=[sys.executable, "-c", SCRIPT, *args])
    assert json.loads((tmp_path / "consumed.json").read_text())["argv"] == args
    assert record.bindings_observed["custom.auth_token"][0].value == SAFE
    assert record.bindings_observed["custom.auth_token"][0].source.key == "--auth-token"
    assert record.command.redactions >= 1
    _assert_owned_safe(_folder(tmp_path, record), SECRET, SECOND_SECRET)


@pytest.mark.parametrize(
    "text",
    [
        '{"api_key":"VALUE","nested":[{"password":"VALUE"}],"max_tokens":32}',
        "api_key: VALUE\nnested:\n  - password: VALUE\nmax_tokens: 32\n",
        "'api_key': 'VALUE'\nnested:\n  - \"password\": \"VALUE\"\nmax_tokens: 32\n",
        "{api_key: VALUE, password: [VALUE, {other: VALUE}], max_tokens: 32}",
        '{"api\\u005fkey": "VALUE", "max_tokens": 32}',
        "password: |\n  VALUE\nmax_tokens: 32\n",
        '+ "api_key": "VALUE",\n',
    ],
)
def test_text_context_preserves_valid_source_structure(tmp_path: Path, text: str) -> None:
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    source = text.replace("VALUE", SECRET)
    safe, count = privacy.text(source)
    assert SECRET not in safe and SAFE in safe and count > 0
    if not source.startswith("+"):
        assert yaml.safe_load(safe)["max_tokens"] == 32


def test_structured_capture_does_not_cross_from_a_key_into_another_field(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    source = "password:\n  max_tokens: 2048\nTOKENIZERS_PARALLELISM: false\n"
    assert privacy.text(source) == (source, 0)


@pytest.mark.parametrize("quoted", [False, True])
def test_yaml_declared_capture_keeps_hashes_and_benign_values(tmp_path: Path, quoted: bool) -> None:
    data = _seed(tmp_path)
    contents = yaml.safe_dump(data)
    if quoted:
        contents = contents.replace("api_key:", "'api_key':").replace("password:", '"password":')
    (tmp_path / "config.yaml").write_text(contents, encoding="utf-8")
    original = (tmp_path / "config.yaml").read_bytes()
    manifest_path = tmp_path / "reprollm.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["execution"]["config_files"].append("config.yaml")
    manifest["bindings"]["custom.yaml_settings"] = {"config": "config.yaml:settings"}
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    record = _execute(tmp_path, output=False)
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET)
    ref = next(item for item in record.files if item.path == "config.yaml")
    assert ref.sha256 == "sha256:" + hashlib.sha256(original).hexdigest()
    assert ref.redacted and ref.snapshot
    saved = yaml.safe_load((folder / ref.snapshot).read_text())
    assert saved == {"settings": {"api_key": SAFE, "nested": [{"password": SAFE}], **BENIGN}}
    assert record.bindings_observed["custom.yaml_settings"][0].value == saved["settings"]


def test_binding_data_context_never_redacts_transport_metadata(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"api_key": SECRET}))
    result = observe(
        {"custom.api_key": BindingSpec(config="config.json:api_key")}, [], {}, tmp_path
    )
    item = result["custom.api_key"][0]
    assert item.value == SAFE
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    safe = privacy.value(result)
    assert safe["custom.api_key"][0]["source"] == {
        "type": "config",
        "key": "api_key",
        "path": "config.json",
    }


@pytest.mark.parametrize("operation", ["text", "record"])
def test_privacy_failure_keeps_safe_completed_record_and_original_child_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    _seed(tmp_path)
    method = getattr(RunPrivacy, "text" if operation == "text" else "value")

    def fail(self: RunPrivacy, value: Any, *args: Any, **kwargs: Any) -> Any:
        is_record = isinstance(value, RunRecord) and value.status == RunStatus.COMPLETED
        if (operation == "text" and isinstance(value, str) and SECRET in value) or is_record:
            raise RuntimeError(SECRET)
        return method(self, value, *args, **kwargs)

    monkeypatch.setattr(RunPrivacy, "text" if operation == "text" else "value", fail)
    record = _execute(tmp_path)
    assert record.exit_code == 7 and record.status == RunStatus.COMPLETED
    saved = json.loads((_folder(tmp_path, record) / "run.json").read_text())
    assert saved["exit_code"] == 7 and saved["status"] == "completed"
    assert any("failed" in warning for warning in record.warnings)
    _assert_owned_safe(_folder(tmp_path, record), SECRET)


@pytest.mark.parametrize("persistent", [False, True])
def test_record_replace_failure_never_exposes_secrets_or_changes_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, persistent: bool
) -> None:
    _seed(tmp_path)
    original_replace = os.replace
    calls = 0

    def replace(source: Any, destination: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 2 or (persistent and calls > 2):
            assert SECRET not in Path(source).read_text()
            raise PermissionError(SECRET)
        original_replace(source, destination)

    monkeypatch.setattr(wrapper.os, "replace", replace)
    record = _execute(tmp_path, output=False)
    assert record.exit_code == 7 and record.status == RunStatus.COMPLETED
    _assert_owned_safe(_folder(tmp_path, record), SECRET)
    saved = json.loads((_folder(tmp_path, record) / "run.json").read_text())
    assert saved["status"] == ("running" if persistent else "completed")


def test_output_privacy_failure_continues_draining_verbose_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed(tmp_path)
    original_text = RunPrivacy.text

    def fail(self: RunPrivacy, text: str, *args: Any, **kwargs: Any) -> Any:
        if SECRET in text:
            raise RuntimeError(SECRET)
        return original_text(self, text, *args, **kwargs)

    monkeypatch.setattr(RunPrivacy, "text", fail)
    script = (
        "import json,pathlib,sys; "
        "data=json.loads(pathlib.Path('config.json').read_text()); print(json.dumps(data)); "
        "[print('remaining-output-' * 1000) for _ in range(100)]; "
        "pathlib.Path('drained.json').write_text(json.dumps({'finished':True})); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and json.loads((tmp_path / "drained.json").read_text())["finished"]
    assert "remaining-output-" in capsys.readouterr().out
    _assert_owned_safe(_folder(tmp_path, record), SECRET)


def test_capture_context_corpus_preserves_existing_policy(tmp_path: Path) -> None:
    corpus_path = Path(__file__).parents[2] / "fixtures/secrets/capture_context.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    assert corpus["schema_version"] == 1
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    for original in corpus["positive"]:
        safe, count = privacy.text(original)
        assert "plainABC" not in safe and "plainXYZ" not in safe and "plainDEF" not in safe
        assert SAFE in safe and count > 0
        assert yaml.safe_load(safe)["max_tokens"] == 32
        assert privacy.text(safe) == (safe, 0)
    for original in corpus["negative"]:
        assert privacy.text(original) == (original, 0)


@pytest.mark.parametrize("truncated", [False, True])
def test_malformed_nested_secret_text_fails_closed_with_safe_completed_evidence(
    tmp_path: Path, truncated: bool
) -> None:
    _seed(tmp_path)
    text = json.dumps({"message": '{"api_key": "' + SECRET})
    if truncated:
        text = text[:-1]
    (tmp_path / "malformed.txt").write_text(text, encoding="utf-8")
    manifest_path = tmp_path / "reprollm.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["execution"]["config_files"].append("malformed.txt")
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    script = "import pathlib,sys; print(pathlib.Path('malformed.txt').read_text()); sys.exit(7)"
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.status == RunStatus.COMPLETED
    assert any("capture failed" in warning for warning in record.warnings)
    _assert_owned_safe(_folder(tmp_path, record), SECRET)


def test_unsafe_command_sanitation_failure_is_safe_before_start(tmp_path: Path) -> None:
    folder = wrapper.create_run_dir(tmp_path)
    script = "import pathlib; pathlib.Path('must-not-exist').write_text('started')"
    with pytest.raises(UserError, match="recorded command") as error:
        wrapper.execute(
            [sys.executable, "-c", script, 'api_key="' + SECRET],
            root=tmp_path,
            cwd=tmp_path,
            run_dir=folder,
            capture_output=True,
            env_capture="allowlist",
            extra_allowlist=[],
            snapshot=True,
        )
    assert SECRET not in str(error.value) and "simplify command arguments" in str(error.value)
    assert not (tmp_path / "must-not-exist").exists()
    assert list(folder.iterdir()) == []


def test_local_file_uris_are_portable_and_https_remains_unchanged(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    for original in (
        "file:///private/cache",
        "file://private-server/share",
        "FILE://C:/private/cache",
    ):
        safe, count = privacy.text(original)
        assert safe == "<REDACTED:path>" and count == 1
    original = "https://example.org/models/config.json"
    assert privacy.text(original) == (original, 0)


def test_yaml_anchor_value_remains_parseable_after_context_redaction(tmp_path: Path) -> None:
    privacy = RunPrivacy(tmp_path, hostname="", username="")
    source = f"api_key: &shared {SECRET}\nother: *shared\nmax_tokens: 32\n"
    safe, count = privacy.text(source)
    assert SECRET not in safe and count == 1
    assert yaml.safe_load(safe) == {"api_key": SAFE, "other": SAFE, "max_tokens": 32}


def test_yaml_output_parent_context_protects_lists_and_block_scalars(tmp_path: Path) -> None:
    _seed(tmp_path)
    text = f"api_key:\n  - {SECRET}\npassword: |\n  {SECOND_SECRET}\nmax_tokens: 32\n"
    (tmp_path / "printed.yaml").write_text(text, encoding="utf-8")
    script = (
        "import pathlib,sys; print(pathlib.Path('printed.yaml').read_text(),end=''); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.warnings == []
    folder = _folder(tmp_path, record)
    saved = yaml.safe_load((folder / "stdout.log").read_text())
    assert saved == {"api_key": [SAFE], "password": SAFE + "\n", "max_tokens": 32}
    _assert_owned_safe(folder, SECRET, SECOND_SECRET)


@pytest.mark.parametrize("entry", [f"- {SECRET}\n", f"-\n  {SECRET}\n"])
def test_indentless_yaml_output_retains_secret_parent(tmp_path: Path, entry: str) -> None:
    _seed(tmp_path)
    (tmp_path / "printed.yaml").write_text("api_key:\n" + entry, encoding="utf-8")
    script = (
        "import pathlib,sys; print(pathlib.Path('printed.yaml').read_text(),end=''); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.warnings == []
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET)
    assert yaml.safe_load((folder / "stdout.log").read_text()) == {"api_key": [SAFE]}


def test_yaml_pem_output_preserves_streaming_private_key_boundary(tmp_path: Path) -> None:
    _seed(tmp_path)
    text = "password: |\n  -----BEGIN PRIVATE KEY-----\n  abcdef\n  -----END PRIVATE KEY-----\n"
    (tmp_path / "printed.yaml").write_text(text, encoding="utf-8")
    script = (
        "import pathlib,sys; print(pathlib.Path('printed.yaml').read_text(),end=''); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.warnings == []
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET, "abcdef", "BEGIN PRIVATE KEY", "END PRIVATE KEY")
    saved = yaml.safe_load((folder / "stdout.log").read_text())
    assert saved["password"].strip() in {SAFE, "<REDACTED:pem>"}


def test_negative_secret_argv_preserves_child_and_sanitizes_saved_command(tmp_path: Path) -> None:
    _seed(tmp_path)
    negative_secret = "-123456789012345"
    script = (
        "import argparse,json,pathlib,sys; p=argparse.ArgumentParser(); "
        "p.add_argument('--password'); p.add_argument('--temperature',type=float); "
        "a=p.parse_args(); pathlib.Path('receipt.json').write_text(json.dumps(vars(a))); "
        "sys.exit(7)"
    )
    record = _execute(
        tmp_path,
        argv=[sys.executable, "-c", script, "--password", negative_secret, "--temperature", "-0.1"],
    )
    assert record.exit_code == 7 and record.warnings == []
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert receipt == {"password": negative_secret, "temperature": -0.1}
    assert record.command.argv[-4:] == ["--password", SAFE, "--temperature", "-0.1"]
    _assert_owned_safe(_folder(tmp_path, record), SECRET, negative_secret)


@pytest.mark.parametrize(
    "text",
    [
        "password: |\n  -----BEGIN PRIVATE KEY-----abcdef-----END PRIVATE KEY-----"
        "-----BEGIN RSA PRIVATE KEY-----ghijkl-----END RSA PRIVATE KEY-----\n",
        "password: |\n  -----BEGIN PRIVATE KEY-----\n  abcdef\n",
        f'"sk-0123456789abcdef api_key": {SECRET}\n',
    ],
)
def test_streaming_pem_and_shielded_keys_never_restore_secrets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    _seed(tmp_path)
    (tmp_path / "printed.yaml").write_text(text, encoding="utf-8")
    script = (
        "import pathlib,sys; text=pathlib.Path('printed.yaml').read_text(); "
        "print(text,end=''); print(text,end='',file=sys.stderr); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.warnings == []
    terminal = capsys.readouterr()
    assert terminal.out == text and terminal.err == text
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET, "abcdef", "ghijkl", "sk-0123456789abcdef")
    for label in ("stdout", "stderr"):
        saved = (folder / f"{label}.log").read_text()
        assert "<REDACTED:" in saved
        assert yaml.safe_load(saved) is not None


@pytest.mark.parametrize(
    ("text", "key"),
    [
        (f'[password]\nvalue = "{SECRET}"\nmax_tokens = 32\n', "password"),
        (f'["password"]\nvalue = "{SECRET}"\nmax_tokens = 32\n', "password"),
        (f'password.value = "{SECRET}"\npassword.max_tokens = 32\n', "password"),
        (f'[settings.password]\nvalue = "{SECRET}"\nmax_tokens = 32\n', "settings.password"),
        (f'[[password]]\nvalue = "{SECRET}"\nmax_tokens = 32\n', "password.0"),
        (f'password = {{ value = "{SECRET}", max_tokens = 32 }}\n', "password"),
        (f'[password]\nvalue = """{SECRET}"""\nmax_tokens = 32\n', "password"),
        (f'[password]\nvalue = """\n{SECRET}"""\nmax_tokens = 32\n', "password"),
    ],
)
def test_toml_snapshot_retains_table_and_dotted_key_context(
    tmp_path: Path, text: str, key: str
) -> None:
    _seed(tmp_path)
    text = (
        "ordinary = { max_tokens = 2048, TOKENIZERS_PARALLELISM = false, "
        'temperature = -0.1, model = "Qwen/Qwen3-32B", cache = "cache/models", '
        'glob = "outputs/**/*.json", stop = "</s>" }\n' + text
    )
    source = tmp_path / "config.toml"
    source.write_text(text, encoding="utf-8")
    original = source.read_bytes()
    manifest_path = tmp_path / "reprollm.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["execution"]["config_files"].append("config.toml")
    manifest["bindings"]["custom.toml_settings"] = {"config": "config.toml:" + key}
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    toml_module = "tomllib" if sys.version_info >= (3, 11) else "tomli"
    script = (
        f"import hashlib,json,pathlib,sys; import {toml_module} as toml"
        "; data=toml.loads(pathlib.Path('config.toml').read_text()); "
        "value=data; "
        "\nfor segment in sys.argv[1].split('.'): "
        "value=value[int(segment)] if isinstance(value,list) else value[segment]"
        "\nreceipt={'sha256':hashlib.sha256(value['value'].encode()).hexdigest(),"
        "'max_tokens':value['max_tokens']}; "
        "pathlib.Path('receipt.json').write_text(json.dumps(receipt)); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script, key])
    assert record.exit_code == 7 and record.warnings == []
    original_settings: Any = tomllib.loads(text)
    for segment in key.split("."):
        original_settings = (
            original_settings[int(segment)]
            if isinstance(original_settings, list)
            else original_settings[segment]
        )
    assert json.loads((tmp_path / "receipt.json").read_text()) == {
        "sha256": hashlib.sha256(original_settings["value"].encode()).hexdigest(),
        "max_tokens": 32,
    }
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET)
    captured = next(item for item in record.files if item.path == "config.toml")
    assert captured.sha256 == "sha256:" + hashlib.sha256(original).hexdigest()
    assert captured.redacted is True and captured.snapshot is not None
    saved = tomllib.loads((folder / captured.snapshot).read_text())
    expected = tomllib.loads(text.replace(SECRET, SAFE))
    assert saved == expected
    assert record.bindings_observed["custom.toml_settings"][0].value == {
        "value": SAFE,
        "max_tokens": 32,
    }


@pytest.mark.parametrize("sibling", ["", "max_tokens: 32\n"])
def test_unterminated_keyed_pem_snapshot_discards_short_body(tmp_path: Path, sibling: str) -> None:
    _seed(tmp_path)
    source = tmp_path / "printed.yaml"
    source.write_text(
        "password: |\n  -----BEGIN PRIVATE KEY-----\n  abcdef\n" + sibling, encoding="utf-8"
    )
    original = source.read_bytes()
    manifest_path = tmp_path / "reprollm.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["execution"]["config_files"].append("printed.yaml")
    manifest["bindings"]["custom.pem"] = {"config": "printed.yaml:password"}
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    script = (
        "import pathlib,sys; text=pathlib.Path('printed.yaml').read_text(); "
        "print(text,end=''); print(text,end='',file=sys.stderr); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.warnings == []
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET, "abcdef", "BEGIN PRIVATE KEY")
    captured = next(item for item in record.files if item.path == "printed.yaml")
    assert captured.sha256 == "sha256:" + hashlib.sha256(original).hexdigest()
    assert captured.redacted is True and captured.snapshot is not None
    saved = yaml.safe_load((folder / captured.snapshot).read_text())
    assert saved["password"].strip() in {SAFE, "<REDACTED:pem>"}
    if sibling:
        assert saved["max_tokens"] == 32
    assert record.bindings_observed["custom.pem"][0].value.strip() in {SAFE, "<REDACTED:pem>"}


@pytest.mark.parametrize("extension", ["yaml", "toml"])
def test_snapshot_comment_keeps_quoted_secret_context(tmp_path: Path, extension: str) -> None:
    _seed(tmp_path)
    separator = ":" if extension == "yaml" else " ="
    text = f'max_tokens{separator} 32\n# {{"api_key":"{SECRET}"}}\n'
    source = tmp_path / ("commented." + extension)
    source.write_text(text, encoding="utf-8")
    original = source.read_bytes()
    manifest_path = tmp_path / "reprollm.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["execution"]["config_files"].append(source.name)
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    record = _execute(tmp_path, output=False)
    assert record.exit_code == 7 and record.warnings == []
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET)
    captured = next(item for item in record.files if item.path == source.name)
    assert captured.sha256 == "sha256:" + hashlib.sha256(original).hexdigest()
    assert captured.redacted is True and captured.snapshot is not None
    saved = (folder / captured.snapshot).read_text()
    parsed = yaml.safe_load(saved) if extension == "yaml" else tomllib.loads(saved)
    assert parsed == {"max_tokens": 32} and SAFE in saved


@pytest.mark.parametrize("unsafe_key", [False, True])
def test_toml_container_comments_and_serialized_keys_never_leak(
    tmp_path: Path, unsafe_key: bool
) -> None:
    _seed(tmp_path)
    text = (
        json.dumps(json.dumps({"api_key": SECRET})) + " = 32\n"
        if unsafe_key
        else f'choices = [1, # {{"api_key":"{SECRET}"}}\n2]\nmax_tokens = 32\n'
    )
    source = tmp_path / "nested.toml"
    source.write_text(text, encoding="utf-8")
    manifest_path = tmp_path / "reprollm.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["execution"]["config_files"].append(source.name)
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    record = _execute(tmp_path, output=False)
    assert record.exit_code == 7 and record.status == RunStatus.COMPLETED
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET)
    if unsafe_key:
        assert "input file snapshot unavailable" in record.warnings
        captured = next(item for item in record.files if item.path == source.name)
        assert captured.snapshot is None
        assert captured.sha256 == "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    else:
        assert record.warnings == []
        captured = next(item for item in record.files if item.path == source.name)
        assert captured.redacted and captured.snapshot is not None
        saved = (folder / captured.snapshot).read_text()
        assert tomllib.loads(saved) == {"choices": [1, 2], "max_tokens": 32}
        assert SAFE in saved


def test_toml_parent_context_protects_saved_streams_and_patch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], bounded_metadata: CmdStub
) -> None:
    _seed(tmp_path)
    text = f'[password]\nvalue = "{SECRET}"\nmax_tokens = 32\n'
    (tmp_path / "printed.toml").write_text(text, encoding="utf-8")
    patch = "diff --git a/printed.toml b/printed.toml\n" + "".join(
        "+" + line for line in text.splitlines(keepends=True)
    )
    bounded_metadata.on("git", "rev-parse", "--is-inside-work-tree", stdout="true\n")
    bounded_metadata.on("git", "status", "--porcelain", stdout=" M printed.toml\n")
    bounded_metadata.on("git", "diff", stdout=patch)
    script = (
        "import pathlib,sys; text=pathlib.Path('printed.toml').read_text(); "
        "print(text,end=''); print(text,end='',file=sys.stderr); sys.exit(7)"
    )
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.warnings == []
    terminal = capsys.readouterr()
    assert terminal.out == text and terminal.err == text
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET)
    for label in ("stdout", "stderr"):
        assert tomllib.loads((folder / f"{label}.log").read_text()) == {
            "password": {"value": SAFE, "max_tokens": 32}
        }
    assert SAFE in (folder / "patch.diff").read_text()


def test_toml_patch_without_parent_table_is_omitted_safely(
    tmp_path: Path, bounded_metadata: CmdStub
) -> None:
    _seed(tmp_path)
    text = "[password]\n" + "".join(f"count_{index} = {index}\n" for index in range(20))
    text += f'value = "{SECRET}"\n'
    (tmp_path / "printed.toml").write_text(text, encoding="utf-8")
    old_secret = "syntheticOldCanaryABC123"
    patch = (
        "diff --git a/printed.toml b/printed.toml\n"
        "index 0123456..abcdef0 100644\n--- a/printed.toml\n+++ b/printed.toml\n"
        "@@ -19,4 +19,4 @@ count_16 = 16\n count_17 = 17\n count_18 = 18\n count_19 = 19\n"
        f'-value = "{old_secret}"\n+value = "{SECRET}"\n'
    )
    bounded_metadata.on("git", "rev-parse", "--is-inside-work-tree", stdout="true\n")
    bounded_metadata.on("git", "status", "--porcelain", stdout=" M printed.toml\n")
    bounded_metadata.on("git", "diff", stdout=patch)
    script = "import pathlib,sys; pathlib.Path('printed.toml').read_text(); sys.exit(7)"
    record = _execute(tmp_path, argv=[sys.executable, "-c", script])
    assert record.exit_code == 7 and record.status == RunStatus.COMPLETED
    assert any("code capture failed" in warning for warning in record.warnings)
    folder = _folder(tmp_path, record)
    _assert_owned_safe(folder, SECRET, old_secret)
    assert not (folder / "patch.diff").exists()


def test_two_secret_values_stay_safe_in_existing_diff_and_export_consumers(tmp_path: Path) -> None:
    records: list[RunRecord] = []
    for secret in (SECRET, SECOND_SECRET):
        _seed(tmp_path, secret)
        records.append(_execute(tmp_path, output=False))
    states = [from_run(record, run_dir=_folder(tmp_path, record)) for record in records]
    report = diff_states(*states, SeverityResolver())
    assert states[0].flatten()["custom.api_key"].value == SAFE
    assert states[1].flatten()["custom.api_key"].value == SAFE
    assert not any(change.path == "custom.api_key" for change in report.changes)
    assert any(change.path == "files.config.json.sha256" for change in report.changes)
    assert SECRET not in report.model_dump_json() and SECOND_SECRET not in report.model_dump_json()
    for record, state in zip(records, states, strict=True):
        folder = _folder(tmp_path, record)
        manifest = load_manifest(folder / "manifest.yaml")
        lock = load_lock(folder / "lock.yaml")
        exported = render(
            build_input(manifest, lock, record, state, reprollm_version="test"),
            sanitize=lambda value: RunPrivacy(tmp_path, hostname="", username="").text(value)[0],
        )
        assert SECRET not in exported and SECOND_SECRET not in exported
        _assert_owned_safe(folder, SECRET, SECOND_SECRET)
