"""UXR01: save an explicit experiment command without executing or rewriting it."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app, cli
from reprollm.core.yaml_io import load_manifest

runner = CliRunner()


@pytest.mark.parametrize(
    "command",
    [
        "python eval.py --config configs/eval.yaml",
        'python eval.py --label "alpha: # beta" --empty ""',
        "python eval.py --label '普通 实验'",
        "  python eval.py --limit 32  ",
        'python -c \'open("unexpected", "w").write("ran")\'',
    ],
)
def test_init_saves_exact_command_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--command", command])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.execution is not None
    assert manifest.execution.command == command
    assert not (tmp_path / "unexpected").exists()
    assert "reprollm run --dry-run" in result.output
    assert command not in result.output


def test_init_without_command_keeps_execution_an_example(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "inference"])
    assert result.exit_code == 0, result.output
    assert load_manifest(tmp_path / "reprollm.yaml").execution is None
    assert (
        "#   command: python eval.py --config configs/eval.yaml"
        in (tmp_path / "reprollm.yaml").read_text()
    )


def test_init_command_does_not_add_interactive_question(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--profiles",
            "inference",
            "--interactive",
            "--command",
            "python eval.py",
        ],
        input="\norg/model\nother\n0\n32\n",
    )
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.execution is not None and manifest.execution.command == "python eval.py"
    assert manifest.models["primary"].id == "org/model"


def test_explicit_command_satisfies_custom_required_field_without_reprompt(tmp_path: Path) -> None:
    profiles = tmp_path / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "saved.yaml").write_text(
        "schema_version: 1\nname: saved\ndescription: Saved command trial\n"
        "extends: [core]\nrules: []\nrequired_fields: [execution.command]\n"
        "severity_overrides: {}\ndrift_overrides: {}\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--profiles",
            "saved",
            "--interactive",
            "--command",
            "python eval.py",
        ],
        input="\norg/model\n",
    )
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.execution is not None and manifest.execution.command == "python eval.py"
    assert manifest.models["primary"].id == "org/model"
    assert (tmp_path / "reprollm.yaml").read_text().count('  command: "python eval.py"') == 1


def test_existing_interactive_required_command_keeps_its_rendering(tmp_path: Path) -> None:
    profiles = tmp_path / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "saved.yaml").write_text(
        "schema_version: 1\nname: saved\ndescription: Saved command trial\n"
        "extends: [core]\nrules: []\nrequired_fields: [execution.command]\n"
        "severity_overrides: {}\ndrift_overrides: {}\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["init", str(tmp_path), "--profiles", "saved", "--interactive"],
        input="\norg/model\npython eval.py\n",
    )
    assert result.exit_code == 0, result.output
    assert "  command: python eval.py\n" in (tmp_path / "reprollm.yaml").read_text()
    assert "Saved execution.command" not in result.output


@pytest.mark.parametrize(
    "command",
    [
        "",
        "   ",
        'python "unclosed',
        "python eval.py && python other.py",
        "python eval.py > result.txt",
        "LIMIT=32 python eval.py",
        "python eval.py\npython other.py",
        "python eval.py \x1b[31m",
        "python eval.py --api-key=abcdefghijk",
        "python eval.py --password abcdefghijk",
        "python eval.py --token hf_" + "a" * 30,
        "python eval.py --data /private/input.json",
    ],
)
@pytest.mark.parametrize("force", [False, True])
def test_invalid_or_private_command_fails_before_any_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    force: bool,
) -> None:
    owned = [
        tmp_path / "reprollm.yaml",
        tmp_path / ".reprollm" / "config.yaml",
        tmp_path / ".reprollm" / "project-rules.yaml",
    ]
    if force:
        owned[1].parent.mkdir()
        for path in owned:
            path.write_text("# preserve original\n")
            path.chmod(0o640)
    before = {p: (p.read_bytes(), p.stat().st_mode) for p in owned if p.exists()}
    args = ["reprollm", "init", str(tmp_path), "--profiles", "inference", "--command", command]
    if force:
        args.append("--force")
    monkeypatch.setattr("sys.argv", args)
    with pytest.raises(SystemExit) as error:
        cli()
    assert error.value.code == 2
    assert {p: (p.read_bytes(), p.stat().st_mode) for p in owned if p.exists()} == before
    assert (tmp_path / ".reprollm").exists() == force
    assert not list(tmp_path.glob(".reprollm.yaml.*.tmp"))
    output = capsys.readouterr()
    assert "execution.command" in output.err or "--command" in output.err
    if command.strip():
        assert command not in output.out + output.err
    assert "abcdefghijk" not in output.out + output.err


@pytest.mark.parametrize("identity", ["manual-user-canary", "manual-host-canary"])
def test_command_machine_identity_is_rejected_without_echo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    identity: str,
) -> None:
    monkeypatch.setattr(
        "reprollm.core.manifest_scaffold.getpass.getuser", lambda: "manual-user-canary"
    )
    monkeypatch.setattr(
        "reprollm.core.manifest_scaffold.socket.gethostname", lambda: "manual-host-canary"
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "reprollm",
            "init",
            str(tmp_path),
            "--profiles",
            "inference",
            "--command",
            f"python eval.py {identity}",
        ],
    )
    with pytest.raises(SystemExit) as error:
        cli()
    assert error.value.code == 2
    assert not (tmp_path / "reprollm.yaml").exists()
    assert not (tmp_path / ".reprollm").exists()
    output = capsys.readouterr()
    assert identity not in output.out + output.err


def test_task_listing_rejects_command_before_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "reprollm.cli.init.plan_init",
        lambda *args, **kwargs: pytest.fail("listing conflict must fail before detection"),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["reprollm", "init", str(tmp_path), "--list-tasks", "--command", "python eval.py"],
    )
    with pytest.raises(SystemExit) as error:
        cli()
    assert error.value.code == 2
    assert not (tmp_path / "reprollm.yaml").exists()
    assert not (tmp_path / ".reprollm").exists()


@pytest.mark.parametrize("depth", [65, 1100])
@pytest.mark.parametrize("force", [False, True])
def test_uninspectable_command_is_private_usage_error_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    depth: int,
    force: bool,
) -> None:
    command = "python eval.py '" + "[" * depth + '"private-canary"' + "]" * depth + "'"
    owned = [tmp_path / "reprollm.yaml", tmp_path / ".reprollm/config.yaml"]
    if force:
        owned[1].parent.mkdir()
        for path in owned:
            path.write_text("# preserve original\n")
            path.chmod(0o640)
    before = {p: (p.read_bytes(), p.stat().st_mode) for p in owned if p.exists()}
    monkeypatch.setattr(
        "sys.argv",
        ["reprollm", "init", str(tmp_path), "--command", command, *(["--force"] if force else [])],
    )
    with pytest.raises(SystemExit) as error:
        cli()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert "execution.command" in output.err and "private-canary" not in output.err + output.out
    assert "internal error" not in output.err
    assert before == {p: (p.read_bytes(), p.stat().st_mode) for p in owned if p.exists()}
    assert not (tmp_path / ".reprollm/project-rules.yaml").exists()
    assert (tmp_path / ".reprollm").exists() == force
