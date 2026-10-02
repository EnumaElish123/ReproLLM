"""UX2-T01: a framework inventory is not an experiment's selected tasks."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app, cli
from reprollm.core.manifest_scaffold import plan_init
from reprollm.core.yaml_io import load_manifest

runner = CliRunner()


def _tasks(root: Path, names: list[str]) -> None:
    tasks = root / "lm_eval" / "tasks"
    tasks.mkdir(parents=True)
    for index, name in enumerate(names):
        (tasks / f"{index}.yaml").write_text(
            f"task: {json.dumps(name)}\ndataset_path: demo/corpus\n", encoding="utf-8"
        )


def test_default_keeps_inventory_without_declaring_tasks(tmp_path: Path) -> None:
    _tasks(tmp_path, ["gsm8k", "arc_easy"])
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None
    assert manifest.evaluation.metrics == []
    assert "Applied detected profiles: evaluation" in result.output
    assert "Task candidates: 2; selected: 0" in result.output
    assert "--list-tasks" in result.output and "--task NAME" in result.output


def test_list_is_complete_sorted_and_never_writes(tmp_path: Path) -> None:
    names = [f"task_{i:05}" for i in range(1001)] + ["普通_task", "arabic_(general)", "task_00000"]
    _tasks(tmp_path, names)
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    result = runner.invoke(app, ["init", str(tmp_path), "--list-tasks"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == sorted(set(names))
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == before
    (tmp_path / "reprollm.yaml").write_text("# existing author content\n")
    repeated = runner.invoke(app, ["init", str(tmp_path), "--list-tasks"])
    assert repeated.output == result.output and repeated.exit_code == 0
    assert (tmp_path / "reprollm.yaml").read_text() == "# existing author content\n"
    assert not (tmp_path / ".reprollm").exists()


def test_selected_tasks_deduplicate_sort_and_preserve_unicode(tmp_path: Path) -> None:
    names = ["gsm8k", "alpha: [quoted]", "普通_task", "arabic_(general)"]
    _tasks(tmp_path, names)
    args = [arg for name in [*reversed(names), "gsm8k"] for arg in ("--task", name)]
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "evaluation", *args])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None
    assert [m.name for m in manifest.evaluation.metrics] == sorted(names)
    assert all(m.implementation is None for m in manifest.evaluation.metrics)
    before = (tmp_path / "reprollm.yaml").read_bytes()
    again = runner.invoke(
        app, ["init", str(tmp_path), "--profiles", "evaluation", "--force", *args]
    )
    assert again.exit_code == 0, again.output
    assert (tmp_path / "reprollm.yaml").read_bytes() == before
    assert "Applied selected profiles: evaluation" in result.output
    assert "Task candidates: 4; selected: 4" in result.output


def test_inventory_does_not_depend_on_selected_profile(tmp_path: Path) -> None:
    _tasks(tmp_path, ["gsm8k"])
    plan = plan_init(tmp_path, profiles_override=["privacy"])
    assert plan.task_names == ["gsm8k"]
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "privacy"])
    assert result.exit_code == 0, result.output
    assert load_manifest(tmp_path / "reprollm.yaml").evaluation is None


@pytest.mark.parametrize(
    "extra",
    [
        ["--task", "missing"],
        ["--profiles", "privacy", "--task", "gsm8k"],
        ["--list-tasks", "--force"],
        ["--list-tasks", "--interactive"],
        ["--list-tasks", "--profiles", "evaluation"],
        ["--list-tasks", "--task", "gsm8k"],
    ],
)
def test_invalid_selection_exits_two_before_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: list[str]
) -> None:
    _tasks(tmp_path, ["gsm8k"])
    monkeypatch.setattr("sys.argv", ["reprollm", "init", str(tmp_path), *extra])
    with pytest.raises(SystemExit) as raised:
        cli()
    assert raised.value.code == 2
    assert not (tmp_path / "reprollm.yaml").exists()
    assert not (tmp_path / ".reprollm").exists()


@pytest.mark.parametrize(
    "name",
    [
        "bad\nname",
        "bad\rname",
        "bad\tname",
        "bad\x1bname",
        "bad\u2028name",
        "bad\u202ename",
        "",
        "sk-" + "a" * 40,
    ],
)
def test_unsafe_names_neither_listed_nor_selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    _tasks(tmp_path, ["safe", name])
    listed = runner.invoke(app, ["init", str(tmp_path), "--list-tasks"])
    assert listed.exit_code == 0, listed.output
    assert listed.output == "safe\n"
    monkeypatch.setattr("sys.argv", ["reprollm", "init", str(tmp_path), "--task", name])
    with pytest.raises(SystemExit) as raised:
        cli()
    assert raised.value.code == 2
    assert not (tmp_path / "reprollm.yaml").exists()


def test_interactive_selects_profiles_then_exact_task_names(tmp_path: Path) -> None:
    _tasks(tmp_path, ["gsm8k", "task,with,commas"])
    answers = "evaluation\ntask,with,commas\ngsm8k\n\n" + "\n" * 10
    result = runner.invoke(app, ["init", str(tmp_path), "--interactive"], input=answers)
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.experiment.profiles == ["evaluation"]
    assert manifest.evaluation is not None
    assert [m.name for m in manifest.evaluation.metrics] == ["gsm8k", "task,with,commas"]
    assert "Task candidates: 2; selected: 2" in result.output
