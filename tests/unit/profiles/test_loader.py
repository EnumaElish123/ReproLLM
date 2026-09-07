"""Profile loader tests: closure, cycles, user overrides, merge (M2-T05)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app, cli
from reprollm.core.errors import UserError
from reprollm.profiles import loader

runner = CliRunner()


def test_builtin_profile_names() -> None:
    assert loader.builtin_profile_names() == [
        "core",
        "evaluation",
        "finetuning",
        "inference",
        "llm_judge",
        "privacy",
        "safety",
    ]


def test_unknown_profile_lists_known(tmp_path: Path) -> None:
    with pytest.raises(UserError, match="unknown profile.*known profiles"):
        loader.resolve(["made_up"], tmp_path)


def test_core_may_not_be_declared(tmp_path: Path) -> None:
    with pytest.raises(UserError, match="core"):
        loader.resolve(["core"], tmp_path)


def test_inheritance_closure_llm_judge(tmp_path: Path) -> None:
    resolved = loader.resolve(["llm_judge"], tmp_path)
    assert resolved.names == ["core", "inference", "evaluation", "llm_judge"]
    assert loader.inheritance_chain(tmp_path, "llm_judge") == [
        "core",
        "inference",
        "evaluation",
        "llm_judge",
    ]


def test_rules_union_and_required_fields_union(tmp_path: Path) -> None:
    resolved = loader.resolve(["llm_judge"], tmp_path)
    core = loader.load_builtin("core")
    assert set(core.rules) <= set(resolved.rules)
    assert "models.judge.id" in resolved.required_fields
    assert "inference.backend" in resolved.required_fields  # inherited from inference
    assert "project.name" in resolved.required_fields  # from core


def test_severity_override_child_wins(tmp_path: Path) -> None:
    resolved = loader.resolve(["llm_judge"], tmp_path)
    assert resolved.severity_overrides["exec.seed_declared"] == "CRITICAL"


def test_cycle_detection(tmp_path: Path) -> None:
    user_dir = tmp_path / ".reprollm" / "profiles"
    user_dir.mkdir(parents=True)
    (user_dir / "loop_a.yaml").write_text(
        "schema_version: 1\nname: loop_a\ndescription: a\nextends: [loop_b]\nrules: []\n"
    )
    (user_dir / "loop_b.yaml").write_text(
        "schema_version: 1\nname: loop_b\ndescription: b\nextends: [loop_a]\nrules: []\n"
    )
    with pytest.raises(UserError, match="cycle"):
        loader.resolve(["loop_a"], tmp_path)


def test_user_profile_overrides_builtin(tmp_path: Path) -> None:
    user_dir = tmp_path / ".reprollm" / "profiles"
    user_dir.mkdir(parents=True)
    (user_dir / "inference.yaml").write_text(
        "schema_version: 1\nname: inference\ndescription: my custom inference\n"
        "extends: [core]\nrules: [code.git_repo]\nrequired_fields: [custom.field]\n"
    )
    resolved = loader.resolve(["inference"], tmp_path)
    assert loader.load_profile(tmp_path, "inference").description == "my custom inference"
    assert resolved.rules == sorted(set(loader.load_builtin("core").rules) | {"code.git_repo"})
    assert "custom.field" in resolved.required_fields


def test_unknown_rule_id_is_user_error(tmp_path: Path) -> None:
    user_dir = tmp_path / ".reprollm" / "profiles"
    user_dir.mkdir(parents=True)
    (user_dir / "broken.yaml").write_text(
        "schema_version: 1\nname: broken\ndescription: x\nextends: []\nrules: [not.a_rule]\n"
    )
    with pytest.raises(UserError, match="not.a_rule"):
        loader.resolve(["broken"], tmp_path)


def test_profiles_list_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["profiles", "list"])
    assert result.exit_code == 0, result.output
    for name in ("core", "inference", "evaluation", "llm_judge", "finetuning", "safety", "privacy"):
        assert name in result.output


def test_profiles_show_llm_judge_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["profiles", "show", "llm_judge"])
    assert result.exit_code == 0, result.output
    expected_path = Path(__file__).parent / "expected_profiles_show_llm_judge.txt"
    import os

    if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
        expected_path.write_text(result.output, encoding="utf-8")
    else:
        assert result.output == expected_path.read_text(encoding="utf-8")


def test_profiles_show_unknown_exits_2(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["reprollm", "profiles", "show", "nope"])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2


def test_detect_signals_union(tmp_path: Path) -> None:
    resolved = loader.resolve(["llm_judge"], tmp_path)
    assert "vllm" in resolved.detect.imports  # from inference
    assert "judge" in resolved.detect.keywords  # own
    assert "mmlu" in resolved.detect.keywords  # from evaluation
