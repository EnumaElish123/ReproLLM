"""init CLI tests (M2-T07 acceptance)."""

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app, cli
from reprollm.core.yaml_io import load_manifest
from tests.conftest import materialize_repo

runner = CliRunner()

POSITIVE_FIXTURES = ["hf_vllm_eval", "openai_judge_eval", "privacy_custom_params"]


def _init(repo: Path, *args: str):
    return runner.invoke(app, ["init", str(repo), *args])


def test_init_snapshots(tmp_path: Path) -> None:
    for name in POSITIVE_FIXTURES:
        repo = materialize_repo(name, tmp_path / name)
        result = _init(repo)
        assert result.exit_code == 0, result.output
        generated = (repo / "reprollm.yaml").read_text(encoding="utf-8")
        expected_path = (
            Path(__file__).resolve().parents[2]
            / "fixtures"
            / "repos"
            / name
            / "expected"
            / "init.yaml"
        )
        if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
            expected_path.parent.mkdir(parents=True, exist_ok=True)
            expected_path.write_text(generated, encoding="utf-8")
        else:
            assert generated == expected_path.read_text(encoding="utf-8"), name


def test_init_generated_manifest_loads_and_audits_at_level_1(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    assert _init(repo).exit_code == 0
    audit = runner.invoke(app, ["audit", str(repo), "--format", "json"])
    assert audit.exit_code in (0, 1), audit.output
    report = json.loads(audit.output)
    assert report["level"] == 1
    assert report["profiles"]["declared"] == ["evaluation", "inference"]


def test_init_creates_dotdir_artifacts(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    assert _init(repo).exit_code == 0
    config = repo / ".reprollm" / "config.yaml"
    project_rules = repo / ".reprollm" / "project-rules.yaml"
    assert config.is_file() and project_rules.is_file()
    assert "schema_version: 1" in project_rules.read_text(encoding="utf-8")


def test_init_refuses_to_overwrite_without_force(tmp_path: Path, monkeypatch) -> None:
    import pytest

    from reprollm.cli.main import cli

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    assert _init(repo).exit_code == 0
    (repo / "reprollm.yaml").write_text("# hand-edited\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["reprollm", "init", str(repo)])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2
    assert (repo / "reprollm.yaml").read_text(encoding="utf-8") == "# hand-edited\n"


def test_init_force_overwrites_manifest_but_not_dotdir(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    assert _init(repo).exit_code == 0
    config = repo / ".reprollm" / "config.yaml"
    config.write_text("# custom config\n", encoding="utf-8")

    result = _init(repo, "--force")
    assert result.exit_code == 0, result.output
    assert config.read_text(encoding="utf-8") == "# custom config\n"  # untouched
    assert "schema_version: 1" in (repo / "reprollm.yaml").read_text(encoding="utf-8")


def test_init_explicit_profiles(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    result = _init(repo, "--profiles", "llm_judge")
    assert result.exit_code == 0, result.output
    text = (repo / "reprollm.yaml").read_text(encoding="utf-8")
    assert "profiles: [llm_judge]" in text
    assert "judge:" in text  # models.judge.id / prompts.judge.path TODOs


def test_init_interactive_prompts(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    # required scalars for core+evaluation+llm_judge, in order:
    # models.primary.id, inference.backend, generation.temperature,
    # generation.max_tokens, datasets.eval.id, models.judge.id,
    # prompts.judge.path, evaluation.judge.params.temperature
    answers = "\n".join(
        [
            "",  # accept the explicitly selected profile before required fields
            "gpt-4o-mini",  # models.primary.id
            "openai",  # inference.backend
            "0.7",  # generation.temperature
            "512",  # generation.max_tokens
            "data",  # datasets.eval.id
            "gpt-4o",  # models.judge.id
            "prompts/judge.txt",  # prompts.judge.path
            "0.0",  # evaluation.judge.params.temperature
        ]
    )
    result = runner.invoke(
        app, ["init", str(repo), "--interactive", "--profiles", "llm_judge"], input=answers
    )
    assert result.exit_code == 0, result.output
    text = (repo / "reprollm.yaml").read_text(encoding="utf-8")
    assert "id: gpt-4o-mini" in text
    assert "temperature: 0.7" in text
    assert "path: prompts/judge.txt" in text


def test_init_interactive_empty_keeps_null(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    result = runner.invoke(
        app,
        ["init", str(repo), "--interactive"],
        input="\n" * 8,
    )
    assert result.exit_code == 0, result.output
    assert "id: Qwen/Qwen3-32B" in (repo / "reprollm.yaml").read_text(encoding="utf-8")
    audit = runner.invoke(app, ["audit", str(repo), "--format", "json"])
    assert json.loads(audit.output)["level"] == 1


def test_init_unknown_profile_exits_2(tmp_path: Path, monkeypatch) -> None:
    import pytest

    from reprollm.cli.main import cli

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    monkeypatch.setattr("sys.argv", ["reprollm", "init", str(repo), "--profiles", "nope"])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2
    assert not (repo / "reprollm.yaml").exists()  # nothing written on failure


def test_init_force_invalid_answer_preserves_owned_bytes_and_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path, manifest="complete")
    dotdir = repo / ".reprollm"
    dotdir.mkdir(exist_ok=True)
    (dotdir / "config.yaml").write_bytes(b"# custom config\n")
    (dotdir / "project-rules.yaml").write_bytes(b"# custom rules\n")
    owned = [repo / "reprollm.yaml", dotdir / "config.yaml", dotdir / "project-rules.yaml"]
    for path in owned:
        path.chmod(0o640)
    before = {path: (path.read_bytes(), path.stat().st_mode) for path in owned}
    monkeypatch.setattr(
        "sys.argv",
        ["reprollm", "init", str(repo), "--force", "--interactive", "--profiles", "inference"],
    )
    with (
        runner.isolation(input="\norg/model\nother\nnot-a-number\n32\n"),
        pytest.raises(SystemExit) as error,
    ):
        cli()
    assert error.value.code == 2
    assert {path: (path.read_bytes(), path.stat().st_mode) for path in owned} == before


@pytest.mark.parametrize("name", ["实验项目", "space name", "a" * 65])
def test_init_invalid_directory_name_uses_safe_fallback(tmp_path: Path, name: str) -> None:
    repo = tmp_path / name
    repo.mkdir()
    result = _init(repo, "--profiles", "inference")
    assert result.exit_code == 0, result.output
    assert load_manifest(repo / "reprollm.yaml").project.name == "experiment"
    assert "project.name" in result.output


@pytest.mark.parametrize(
    "name", ["123", "true", "null", "on", "yes", "0x10", "2026-10-10", "-", "1.0", "ordinary"]
)
def test_init_valid_directory_name_remains_a_string(tmp_path: Path, name: str) -> None:
    repo = tmp_path / name
    repo.mkdir()
    result = _init(repo, "--profiles", "inference")
    assert result.exit_code == 0, result.output
    assert load_manifest(repo / "reprollm.yaml").project.name == repo.name


@pytest.mark.parametrize(
    "owned", ["reprollm.yaml", ".reprollm", ".reprollm/config.yaml", ".reprollm/project-rules.yaml"]
)
@pytest.mark.parametrize("dangling", [False, True])
def test_init_rejects_owned_symlinks_before_detection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    owned: str,
    dangling: bool,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"external data\n")
    target = outside if owned == ".reprollm" else sentinel
    if dangling:
        target = outside / "missing"
    link = repo / owned
    link.parent.mkdir(exist_ok=True)
    try:
        link.symlink_to(target, target_is_directory=owned == ".reprollm")
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    monkeypatch.setattr(
        "sys.argv", ["reprollm", "init", str(repo), "--force", "--profiles", "inference"]
    )
    with pytest.raises(SystemExit) as error:
        cli()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert owned in output.err
    assert str(tmp_path) not in output.err
    assert link.is_symlink()
    assert sentinel.read_bytes() == b"external data\n"
    assert sorted(p.name for p in outside.iterdir()) == ["sentinel"]
    assert not list(repo.glob(".reprollm.yaml.*.tmp"))


def test_init_force_in_chinese_directory_replaces_with_loadable_manifest(tmp_path: Path) -> None:
    source = materialize_repo("hf_vllm_eval", tmp_path, manifest="complete")
    repo = source.rename(tmp_path / "实验项目")
    result = _init(repo, "--force", "--profiles", "inference")
    assert result.exit_code == 0, result.output
    assert load_manifest(repo / "reprollm.yaml").project.name == "experiment"


def test_init_rejects_symlinked_profile_directory_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    profiles = outside / "profiles"
    profiles.mkdir(parents=True)
    hostile = profiles / "core.yaml"
    hostile.write_bytes(b"CANARY_SECRET: [\n")
    try:
        (repo / ".reprollm").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    monkeypatch.setattr("sys.argv", ["reprollm", "init", str(repo), "--profiles", "inference"])
    with pytest.raises(SystemExit) as error:
        cli()
    assert error.value.code == 2
    output = capsys.readouterr()
    assert ".reprollm must be a regular directory" in output.err
    assert "CANARY_SECRET" not in output.err
    assert str(tmp_path) not in output.err
    assert hostile.read_bytes() == b"CANARY_SECRET: [\n"


def test_init_directory_name_with_machine_identity_uses_safe_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = "machine-canary"
    monkeypatch.setattr("reprollm.core.manifest_scaffold.socket.gethostname", lambda: name)
    repo = tmp_path / name
    repo.mkdir()
    result = _init(repo, "--profiles", "inference")
    assert result.exit_code == 0, result.output
    assert load_manifest(repo / "reprollm.yaml").project.name == "experiment"
    assert name not in result.output
