"""init CLI tests (M2-T07 acceptance)."""

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from reprollm.cli.main import app
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
