"""Read-only capture readiness contract (UX3-T03, spec §5.2)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.errors import UserError
from reprollm.schemas.run_record import CommandInfo, RunRecord, RunStatus

runner = CliRunner()
LIMIT = 2 * 1024 * 1024


def write_manifest(root: Path, **sections: Any) -> dict[str, Any]:
    data = {"schema_version": 1, "project": {"name": "preview"}, "experiment": {"profiles": []}}
    data.update(sections)
    (root / "reprollm.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return data


def rules(root: Path, entries: list[dict[str, Any]]) -> None:
    (root / ".reprollm").mkdir(exist_ok=True)
    (root / ".reprollm/project-rules.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "rules": entries}), encoding="utf-8"
    )


def rule(field: str, **bindings: str) -> dict[str, Any]:
    return {
        "id": "project.setting",
        "field": field,
        "severity": "WARNING",
        "reason": "record this setting",
        "source": "manual",
        "accepted_at": "2026-10-02T00:00:00Z",
        "bindings": bindings,
    }


def tree(root: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
        if not path.is_symlink()
    }


def invoke(*args: str) -> Any:
    return runner.invoke(app, ["run", "--dry-run", *args])


def usage(result: Any) -> None:
    assert result.exit_code == 2 or isinstance(result.exception, UserError), result.output


@pytest.fixture(autouse=True)
def no_effects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("preflight performed a prohibited side effect")

    for target in (
        "reprollm.cli.run.execute",
        "reprollm.cli.run.create_run_dir",
        "reprollm.core.proc.run_cmd",
        "subprocess.Popen",
        "httpx.Client",
        "httpx.AsyncClient",
    ):
        monkeypatch.setattr(target, forbidden)


def test_preview_is_deterministic_and_does_not_execute_or_write(tmp_path: Path) -> None:
    write_manifest(tmp_path, generation={"temperature": 0.3})
    before = tree(tmp_path)
    first = invoke("--", "nonexistent-command", "--secret=private-command-value")
    second = invoke("--", "nonexistent-command", "--secret=private-command-value")
    assert first.exit_code == second.exit_code == 0, first.output
    assert first.stdout == second.stdout
    assert tree(tmp_path) == before
    assert "nonexistent-command" not in first.output
    assert "private-command-value" not in first.output
    assert "not executed" in first.stdout
    assert "Lock: missing" in first.stdout
    assert "generation.temperature" in first.stdout
    assert "No run" in first.stdout
    assert "can change" in first.stdout


def test_nearest_manifest_root_and_effective_options(tmp_path: Path) -> None:
    write_manifest(tmp_path)
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/config.yaml").write_text(
        "schema_version: 1\nrun: {capture_output: true, env_capture: all, snapshot_max_bytes: 4}\n"
    )
    (nested / "tiny.txt").write_text("hello")
    result = invoke("--cwd", str(nested), "--", "python", "tiny.txt")
    assert result.exit_code == 0, result.output
    assert "Working directory: nested" in result.stdout
    assert "Output capture: enabled" in result.stdout
    assert "Environment policy: all" in result.stdout
    assert "nested/tiny.txt [argv]: hash-only (size)" in result.stdout
    overridden = invoke("--no-snapshot", "--env-capture", "allowlist", "--", "python")
    assert "Snapshots: disabled" in overridden.stdout
    assert "Environment policy: allowlist" in overridden.stdout
    assert str(tmp_path) not in result.output


@pytest.mark.parametrize("arguments", [[], ["--", "python"], ["--cwd", "absent", "--", "python"]])
def test_missing_command_manifest_and_directory_are_safe_usage_errors(
    tmp_path: Path, arguments: list[str]
) -> None:
    before = tree(tmp_path)
    result = invoke(*arguments)
    usage(result)
    assert tree(tmp_path) == before
    assert str(tmp_path) not in str(result.exception)


@pytest.mark.parametrize(
    "name",
    ["reprollm.yaml", "reprollm.lock", ".reprollm/config.yaml", ".reprollm/project-rules.yaml"],
)
@pytest.mark.parametrize(
    "contents",
    [b"[private-parser-value", b"\xff", b"schema_version: 999\n", b" " * (LIMIT + 1)],
    ids=["malformed", "utf8", "future-version", "oversized"],
)
def test_invalid_documents_do_not_disclose_input_or_write(
    tmp_path: Path, name: str, contents: bytes
) -> None:
    write_manifest(tmp_path)
    path = tmp_path / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(contents)
    before = tree(tmp_path)
    result = invoke("--", "python")
    usage(result)
    assert tree(tmp_path) == before
    assert "private-parser-value" not in result.output + str(result.exception)
    assert str(tmp_path) not in result.output + str(result.exception)


@pytest.mark.parametrize(
    "name",
    ["reprollm.yaml", "reprollm.lock", ".reprollm/config.yaml", ".reprollm/project-rules.yaml"],
)
def test_document_symlink_escapes_and_dangling_links_are_usage_errors(
    tmp_path: Path, name: str
) -> None:
    write_manifest(tmp_path)
    outside = tmp_path.parent / (tmp_path.name + "-outside.yaml")
    outside.write_text("private-outside-document")
    path = tmp_path / name
    path.parent.mkdir(exist_ok=True)
    path.unlink(missing_ok=True)
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    for _ in range(2):
        result = invoke("--", "python")
        usage(result)
        assert "private-outside-document" not in result.output + str(result.exception)
        outside.unlink(missing_ok=True)


def test_file_discovery_optional_declarations_and_capture_dedup(tmp_path: Path) -> None:
    write_manifest(
        tmp_path,
        models={"primary": {"chat_template": {"path": "chat.txt"}}},
        execution={
            "config_files": ["args.yaml", "missing.yaml", ".env", "binary.dat", "large.txt"]
        },
        prompts={"system": {"path": "prompt.txt"}},
        training={"deepspeed": {"config": "train.json"}},
        evaluation={"definitions": {"rule": "textual definition"}},
        privacy={"threat_model": "a threat description"},
        bindings={"generation.temperature": {"config": "args.yaml:x"}},
    )
    rules(tmp_path, [rule("custom.x", config="rule.toml:x")])
    for name in ("chat.txt", "prompt.txt", "train.json", "rule.toml", "args.yaml", "script.py"):
        (tmp_path / name).write_text("x: 1")
    (tmp_path / ".env").write_text("do not read me")
    (tmp_path / "binary.dat").write_bytes(b"\x00\x01")
    (tmp_path / "large.txt").write_bytes(b"x" * (LIMIT + 1))
    result = invoke("--", "python", "script.py", "--config=args.yaml", "missing-argv.file")
    assert result.exit_code == 0, result.output
    for name in ("chat.txt", "prompt.txt", "train.json"):
        assert f"{name} [declared]: snapshot eligible" in result.stdout
    assert "rule.toml [binding]: snapshot eligible" in result.stdout
    assert "script.py [argv]: snapshot eligible" in result.stdout
    assert "args.yaml [declared]: snapshot eligible" in result.stdout
    assert "args.yaml [argv]" not in result.stdout
    assert "missing.yaml [declared]: unavailable" in result.stdout
    assert "textual definition [declared]: not a file (optional declaration)" in result.stdout
    assert "a threat description [declared]: not a file (optional declaration)" in result.stdout
    assert ".env [declared]: hash-only (forbidden name)" in result.stdout
    assert "binary.dat [declared]: hash-only (binary)" in result.stdout
    assert "large.txt [declared]: not inspected (over 2 MiB; hash-only)" in result.stdout
    assert "missing-argv.file" not in result.stdout


def test_forbidden_files_are_never_opened_even_through_safe_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_manifest(
        tmp_path,
        execution={"config_files": ["alias.yaml", ".env"]},
        bindings={"custom.x": {"config": "alias.yaml:key"}},
    )
    secret = tmp_path / ".env"
    secret.write_text("key: private-file-value")
    try:
        (tmp_path / "alias.yaml").symlink_to(secret)
    except OSError:
        pytest.skip("symlinks unavailable")
    original = Path.open

    def checked(path: Path, *args: Any, **kwargs: Any) -> Any:
        assert path.resolve() != secret, "forbidden file was opened"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    assert "forbidden config file" in result.stdout
    assert "private-file-value" not in result.stdout


def test_snapshot_limit_is_applied_before_inspection(tmp_path: Path) -> None:
    names = [f"f{index:03}.txt" for index in range(201)]
    write_manifest(tmp_path, execution={"config_files": names})
    for name in names:
        (tmp_path / name).write_text("text")
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    assert result.stdout.count("hash-only (200-file limit)") == 201


def test_binding_locations_counts_nulls_lists_and_names_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_manifest(
        tmp_path,
        execution={"env_requirements": ["Z_PRESENT", "OPENAI_API_KEY", "ABSENT", "Z_PRESENT"]},
        bindings={
            "custom.x": {"cli": "--value", "config": "values.yaml:items.0", "env": "Z_PRESENT"},
            "custom.null": {"config": "values.yaml:none"},
            "custom.list": {"config": "values.json:items"},
            "custom.toml": {"config": "values.toml:sample.x"},
            "custom.secret": {"env": "OPENAI_API_KEY"},
            "custom.absent": {"cli": "--absent", "env": "ABSENT"},
        },
    )
    rules(tmp_path, [rule("custom.x", cli="--value", env="SECOND_ENV")])
    (tmp_path / "values.yaml").write_text("items: [private-config-value]\nnone: null\n")
    (tmp_path / "values.json").write_text(json.dumps({"items": ["private-json-value"]}))
    (tmp_path / "values.toml").write_text('[sample]\nx = "private-toml-value"\n')
    monkeypatch.setenv("Z_PRESENT", "")
    monkeypatch.setenv("SECOND_ENV", "private-env-value")
    monkeypatch.setenv("OPENAI_API_KEY", "private-key-value")
    monkeypatch.delenv("ABSENT", raising=False)
    result = invoke(
        "--", "python", "--value", "private-cli-value", "--value=other-value", "--value"
    )
    assert result.exit_code == 0, result.output
    assert "cli --value: located (3 occurrences)" in result.stdout
    assert result.stdout.count("cli --value:") == 1
    for location in (
        "values.yaml:items.0",
        "values.yaml:none",
        "values.json:items",
        "values.toml:sample.x",
    ):
        assert f"config {location}: located" in result.stdout
    assert "env OPENAI_API_KEY: refused (secret environment binding)" in result.stdout
    assert "env Z_PRESENT: present" in result.stdout
    assert "env SECOND_ENV: present" in result.stdout
    assert "env ABSENT: missing" in result.stdout
    required = result.stdout.split("Required environment:\n")[1].split("Unbound declarations:")[0]
    assert required == "  ABSENT: missing\n  OPENAI_API_KEY: present\n  Z_PRESENT: present\n"
    assert all(value not in result.stdout for value in ("private-", "other-value"))


@pytest.mark.parametrize(
    ("location", "contents", "status"),
    [
        ("input.yaml:missing", b"x: null", "key not found"),
        ("input.yaml:items.99", b"items: [one]", "key not found"),
        ("input.yaml:items.no", b"items: [one]", "key not found"),
        ("input.yaml:x", b"[private-parser-value", "cannot read config"),
        ("input.yaml:x", b"\xff", "cannot read config"),
        ("input.txt:x", b"x: 1", "unsupported config format"),
        ("input.yaml:", b"x: 1", "path/key unavailable"),
        ("input.yaml:x", b"x" * (LIMIT + 1), "not inspected (over 2 MiB)"),
    ],
    ids=["missing", "index", "bad-index", "malformed", "utf8", "format", "empty-key", "oversized"],
)
def test_unavailable_binding_configs_are_safe_advisories(
    tmp_path: Path, location: str, contents: bytes, status: str
) -> None:
    write_manifest(tmp_path, bindings={"custom.x": {"config": location}})
    (tmp_path / location.partition(":")[0]).write_bytes(contents)
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    assert status in result.stdout
    assert "private-parser-value" not in result.stdout


def test_unbound_advisory_has_fixed_scope_and_atomic_lists(tmp_path: Path) -> None:
    write_manifest(
        tmp_path,
        models={
            "primary": {"id": "private-model-value", "revision": "main", "dtype": "float32"},
            "judge": {},
        },
        prompts={"judge": {}},
        generation={"temperature": 0.2, "stop": ["private-stop-value"], "top_p": 0.9},
        evaluation={"judge": {"params": {"max_tokens": 2}}, "aggregation": "mean"},
        inference={"params": {"nested": {"x": 2}}},
        training={"params": {"x": 1}, "learning_rate": 0.1},
        privacy={"mechanism": {"name": "dp", "params": {"x": 1}}, "attack": {"params": {"x": 1}}},
        custom={"list": [1, 2], "none": None, "bound": 1, "empty": 2},
        bindings={
            "custom.bound": {"cli": "--absent"},
            "custom.empty": {},
            "generation.top_p": {"env": "P"},
        },
    )
    rules(tmp_path, [rule("training.learning_rate")])
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    unbound = result.stdout.split("Unbound declarations:\n")[1].split("Lock:")[0]
    for field in (
        "models.primary.id",
        "models.primary.revision",
        "generation.temperature",
        "generation.stop",
        "evaluation.judge.params.max_tokens",
        "inference.params.nested.x",
        "training.params.x",
        "training.learning_rate",
        "privacy.mechanism.params.x",
        "privacy.attack.params.x",
        "custom.list",
        "custom.empty",
    ):
        assert f"  {field}\n" in unbound
    for field in (
        "models.primary.dtype",
        "evaluation.aggregation",
        "custom.none",
        "custom.bound",
        "generation.top_p",
        "custom.list.0",
        "generation.stop.0",
    ):
        assert field not in unbound
    assert "private-" not in result.stdout


def write_lock(root: Path) -> None:
    def digest(path: Path) -> str:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

    project_rules = root / ".reprollm/project-rules.yaml"
    document = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "generated_at": "2026-10-02T00:00:00Z",
        "manifest_sha256": digest(root / "reprollm.yaml"),
        "project_rules_sha256": digest(project_rules) if project_rules.is_file() else None,
        "resolution": {"mode": "offline"},
    }
    (root / "reprollm.lock").write_text(yaml.safe_dump(document))


@pytest.mark.parametrize(
    "mutation", ["none", "manifest", "add_rules", "remove_rules", "change_rules"]
)
def test_lock_freshness_uses_exact_document_bytes(tmp_path: Path, mutation: str) -> None:
    write_manifest(tmp_path)
    if mutation in {"remove_rules", "change_rules"}:
        rules(tmp_path, [])
    write_lock(tmp_path)
    if mutation == "manifest":
        with (tmp_path / "reprollm.yaml").open("a") as handle:
            handle.write("\n# comment only change\n")
    elif mutation == "add_rules":
        rules(tmp_path, [])
    elif mutation == "remove_rules":
        (tmp_path / ".reprollm/project-rules.yaml").unlink()
    elif mutation == "change_rules":
        with (tmp_path / ".reprollm/project-rules.yaml").open("a") as handle:
            handle.write("\n# comment only change\n")
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    assert f"Lock: {'fresh' if mutation == 'none' else 'stale'}" in result.stdout
    assert "not revalidated" in result.stdout


def test_variable_text_is_sanitized_but_fixed_statuses_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "sk-" + "x" * 30
    write_manifest(
        tmp_path,
        custom={"fresh": 1, "name\x1b\nfield": 2, secret: 3, str(tmp_path): 4},
        execution={"env_requirements": ["host-secret", "fresh", "NAME\x1b\n"]},
    )
    write_lock(tmp_path)
    monkeypatch.setattr("getpass.getuser", lambda: "fresh")
    monkeypatch.setattr("socket.gethostname", lambda: "host-secret")
    result = invoke("--name", "private-command-label", "--", "python", secret)
    assert result.exit_code == 0, result.output
    assert "Lock: fresh" in result.stdout
    assert "<REDACTED:username>" in result.stdout
    assert "<REDACTED:hostname>" in result.stdout
    assert "\\x1b\\n" in result.stdout
    for value in ("\x1b", secret, str(tmp_path), "host-secret", "private-command-label"):
        assert value not in result.stdout


def test_child_dry_run_argument_keeps_normal_run_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_manifest(tmp_path)
    commands = []

    def execute(command: list[str], **kwargs: Any) -> RunRecord:
        commands.append(command)
        return RunRecord(
            reprollm_version="0.6.1",
            run_id="20261002T000000Z-abcdef",
            status=RunStatus.COMPLETED,
            started_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
            command=CommandInfo(argv=command, cwd="."),
            exit_code=0,
        )

    monkeypatch.setattr("reprollm.cli.run.execute", execute)
    monkeypatch.setattr("reprollm.cli.run.create_run_dir", lambda root: root / "unused")
    result = runner.invoke(app, ["run", "--", "python", "script.py", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert commands == [["python", "script.py", "--dry-run"]]
    assert "Recorded run" in result.stdout
    assert "Run preflight" not in result.stdout


@pytest.mark.parametrize(
    "name",
    ["reprollm.yaml", "reprollm.lock", ".reprollm/config.yaml", ".reprollm/project-rules.yaml"],
)
def test_documents_accept_safe_internal_symlinks(tmp_path: Path, name: str) -> None:
    write_manifest(tmp_path)
    rules(tmp_path, [])
    (tmp_path / ".reprollm/config.yaml").write_text("schema_version: 1\n")
    write_lock(tmp_path)
    path = tmp_path / name
    destination = tmp_path / "linked.yaml"
    path.rename(destination)
    try:
        path.symlink_to(destination)
    except OSError:
        pytest.skip("symlinks unavailable")
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    assert "Lock: fresh" in result.stdout


def test_preflight_cap_is_not_a_snapshot_policy(tmp_path: Path) -> None:
    write_manifest(tmp_path, execution={"config_files": ["large.txt"]})
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/config.yaml").write_text(
        f"schema_version: 1\nrun: {{snapshot_max_bytes: {LIMIT * 3}}}\n"
    )
    (tmp_path / "large.txt").write_bytes(b"x" * (LIMIT + 1))
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    assert "large.txt [declared]: not inspected (over 2 MiB)\n" in result.stdout
    assert "hash-only" not in result.stdout


@pytest.mark.parametrize("present", [False, True])
def test_accepted_unbound_rule_is_reported_even_without_declared_value(
    tmp_path: Path, present: bool
) -> None:
    write_manifest(tmp_path, custom={"setting": None} if present else {})
    rules(tmp_path, [rule("custom.setting")])
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    assert "Unbound declarations:\n  custom.setting\n" in result.stdout


@pytest.mark.parametrize("kind", ["binding", "directory"])
def test_outside_binding_and_metadata_directory_are_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    write_manifest(tmp_path, bindings={"custom.x": {"config": "outside.yaml:x"}})
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    target = outside / "project-rules.yaml"
    target.write_text("private-outside-value")
    try:
        if kind == "binding":
            (tmp_path / "outside.yaml").symlink_to(target)
        else:
            (tmp_path / ".reprollm").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    original = Path.open

    def checked(path: Path, *args: Any, **kwargs: Any) -> Any:
        assert not path.resolve().is_relative_to(outside), "outside file was opened"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    result = invoke("--", "python")
    if kind == "binding":
        assert result.exit_code == 0, result.output
        assert "outside repository" in result.stdout
    else:
        usage(result)


def test_actual_cli_error_boundary_keeps_exit_two_and_safe_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from reprollm.cli import main
    from reprollm.run.preflight import preview

    (tmp_path / "reprollm.yaml").write_text("[private-parser-value")

    def command() -> None:
        preview(["python"], cwd=tmp_path)

    monkeypatch.setattr(main, "app", command)
    with pytest.raises(SystemExit) as caught:
        main.cli()
    assert caught.value.code == 2
    stderr = capsys.readouterr().err
    assert "reprollm.yaml" in stderr and "repair" in stderr
    assert "private-parser-value" not in stderr and str(tmp_path) not in stderr
    assert "Traceback" not in stderr


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_lock_freshness_does_not_normalize_line_endings(tmp_path: Path, newline: bytes) -> None:
    write_manifest(tmp_path)
    content = (tmp_path / "reprollm.yaml").read_bytes().replace(b"\r\n", b"\n")
    (tmp_path / "reprollm.yaml").write_bytes(content)
    write_lock(tmp_path)
    (tmp_path / "reprollm.yaml").write_bytes(content.replace(b"\n", newline))
    result = invoke("--", "python")
    assert result.exit_code == 0, result.output
    expected = "fresh" if newline == b"\n" else "stale"
    assert f"Lock: {expected}" in result.stdout


@pytest.mark.parametrize("kind", ["document", "input", "config"])
def test_oversized_reads_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    write_manifest(
        tmp_path,
        execution={"config_files": ["large.yaml"]},
        bindings={"custom.x": {"config": "large.yaml:x"}} if kind == "config" else {},
    )
    name = "reprollm.yaml" if kind == "document" else "large.yaml"
    target = tmp_path / name
    target.write_bytes(b"x" * (LIMIT + 1))
    original = Path.open
    reads = []

    class Guard:
        def __init__(self, handle: Any) -> None:
            self.handle = handle

        def __enter__(self) -> Guard:
            self.handle.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            return self.handle.__exit__(*args)

        def fileno(self) -> int:
            return self.handle.fileno()

        def read(self, size: int = -1) -> bytes:
            reads.append(size)
            assert 0 <= size <= LIMIT
            return self.handle.read(size)

    def checked(path: Path, *args: Any, **kwargs: Any) -> Any:
        handle = original(path, *args, **kwargs)
        return Guard(handle) if path == target else handle

    monkeypatch.setattr(Path, "open", checked)
    result = invoke("--", "python")
    if kind == "document":
        usage(result)
    else:
        assert result.exit_code == 0, result.output
        assert "not inspected" in result.stdout
    assert reads == []


def test_shared_file_is_read_once_and_input_content_is_never_hashed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.run import preflight

    write_manifest(
        tmp_path,
        execution={"config_files": ["values.yaml"]},
        bindings={"custom.x": {"config": "values.yaml:x"}, "custom.y": {"config": "values.yaml:y"}},
    )
    content = b"x: private-value-x\ny: private-value-y\n"
    (tmp_path / "values.yaml").write_bytes(content)
    write_lock(tmp_path)
    original_read = preflight._read
    read_calls = []
    original_hash = preflight.sha256_bytes
    hashed = []

    def read(path: Path) -> bytes | None:
        read_calls.append(path)
        return original_read(path)

    def digest(data: bytes) -> str:
        hashed.append(data)
        assert data != content
        return original_hash(data)

    monkeypatch.setattr(preflight, "_read", read)
    monkeypatch.setattr(preflight, "sha256_bytes", digest)
    result = invoke("--", "python", "values.yaml")
    assert result.exit_code == 0, result.output
    assert read_calls.count(tmp_path / "values.yaml") == 1
    assert hashed == [(tmp_path / "reprollm.yaml").read_bytes()]


def test_optional_documents_may_be_absent_and_existing_files_stay_unchanged(tmp_path: Path) -> None:
    write_manifest(tmp_path)
    old_run = tmp_path / ".reprollm/runs/existing/run.json"
    old_run.parent.mkdir(parents=True)
    old_run.write_text("existing unrelated evidence")
    before = tree(tmp_path)
    result = invoke("--capture-output", "--name", "not-displayed", "--", "python")
    assert result.exit_code == 0, result.output
    assert "Output capture: enabled" in result.stdout
    assert "Lock: missing" in result.stdout
    assert tree(tmp_path) == before
