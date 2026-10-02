"""M11-T01 framework signals and task candidates reach the public init command."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.core.manifest_scaffold import plan_init, render_manifest
from reprollm.core.yaml_io import load_manifest

runner = CliRunner()


@pytest.mark.parametrize(
    ("command", "task_path", "task_text", "expected_names"),
    [
        (
            "lm_eval --model hf --tasks custom\n",
            "lm_eval/tasks/custom.yaml",
            "task: custom\ndataset_path: demo/corpus\nmetric_list:\n  - metric: accuracy\n",
            ["custom"],
        ),
        (
            "python -m lm_eval --model hf --tasks custom\n",
            "tasks/custom.yml",
            "task: custom\ndataset_path: demo/corpus\n",
            ["custom"],
        ),
        (
            "lighteval accelerate --tasks custom\n",
            "configs/task.yaml",
            "task: custom\n",
            ["custom"],
        ),
        (
            "inspect eval task.py\n",
            "task.py",
            "from inspect_ai import task\n@task\ndef custom():\n    return None\n",
            ["custom"],
        ),
    ],
)
def test_framework_cli_selects_evaluation_and_prefills_selected_tasks(
    tmp_path: Path,
    command: str,
    task_path: str,
    task_text: str,
    expected_names: list[str],
) -> None:
    (tmp_path / "run.sh").write_text(command, encoding="utf-8", newline="\n")
    task = tmp_path / task_path
    task.parent.mkdir(parents=True, exist_ok=True)
    task.write_text(task_text, encoding="utf-8", newline="\n")

    selectors = [value for name in expected_names for value in ("--task", name)]
    result = runner.invoke(app, ["init", str(tmp_path), *selectors])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert "evaluation" in manifest.experiment.profiles
    assert manifest.evaluation is not None
    assert [metric.name for metric in manifest.evaluation.metrics] == expected_names
    assert all(metric.implementation is None for metric in manifest.evaluation.metrics)
    detection = AuditContext(tmp_path).detection
    evaluation = next(entry for entry in detection.profiles if entry.profile == "evaluation")
    assert evaluation.confidence == "high"
    assert all(not (e.path or "").startswith(str(tmp_path)) for e in evaluation.evidence)
    assert "verify task" in (tmp_path / "reprollm.yaml").read_text(encoding="utf-8")


def test_lm_eval_task_structure_selects_evaluation_without_import_or_command(
    tmp_path: Path,
) -> None:
    tasks = tmp_path / "lm_eval" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "custom.yaml").write_text(
        "task: custom\ndataset_path: demo/corpus\n", encoding="utf-8", newline="\n"
    )
    result = runner.invoke(app, ["init", str(tmp_path), "--task", "custom"])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert "evaluation" in manifest.experiment.profiles
    assert manifest.evaluation is not None
    assert [metric.name for metric in manifest.evaluation.metrics] == ["custom"]


def test_task_names_are_deduplicated_quoted_and_sorted(tmp_path: Path) -> None:
    (tmp_path / "run.sh").write_text("lm_eval --tasks custom\n", encoding="utf-8", newline="\n")
    tasks = tmp_path / "lm_eval" / "tasks"
    tasks.mkdir(parents=True)
    for filename, task_name in [
        ("z.yaml", "alpha: [quoted]"),
        ("a.yaml", "zeta"),
        ("b.yaml", "zeta"),
    ]:
        (tasks / filename).write_text(
            f"task: {json.dumps(task_name)}\ndataset_path: demo/corpus\n",
            encoding="utf-8",
            newline="\n",
        )
    plan = plan_init(tmp_path, profiles_override=None)
    first = render_manifest(plan, {})
    assert first == render_manifest(plan_init(tmp_path, profiles_override=None), {})
    result = runner.invoke(
        app,
        ["init", str(tmp_path), "--task", "zeta", "--task", "alpha: [quoted]", "--task", "zeta"],
    )
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None
    assert [metric.name for metric in manifest.evaluation.metrics] == ["alpha: [quoted]", "zeta"]


def test_unrelated_task_config_and_commented_import_do_not_prefill(tmp_path: Path) -> None:
    (tmp_path / "worker.py").write_text("# import lighteval\n", encoding="utf-8", newline="\n")
    (tmp_path / "run.sh").write_text("# lm_eval --tasks task\n", encoding="utf-8", newline="\n")
    (tmp_path / "config.yaml").write_text("task: unrelated\n", encoding="utf-8", newline="\n")
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "evaluation"])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None
    assert manifest.evaluation.metrics == []
    assert not any(
        entry.confidence == "high" for entry in AuditContext(tmp_path).detection.profiles
    )


def test_explicit_profile_without_evaluation_does_not_gain_task_declarations(
    tmp_path: Path,
) -> None:
    (tmp_path / "task.py").write_text(
        "from inspect_ai import task\n@task\ndef custom():\n    return None\n",
        encoding="utf-8",
        newline="\n",
    )
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "inference"])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is None


def test_task_yaml_custom_tags_are_read_statically(tmp_path: Path) -> None:
    tasks = tmp_path / "lm_eval" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "custom.yaml").write_text(
        "task: custom\ndataset_path: demo/corpus\ndoc_to_text: !function never_import.prompt\n",
        encoding="utf-8",
        newline="\n",
    )
    result = runner.invoke(app, ["init", str(tmp_path), "--task", "custom"])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None
    assert [metric.name for metric in manifest.evaluation.metrics] == ["custom"]


@pytest.mark.parametrize("value", ["null", "23", "[group, members]", "!function never_import.task"])
def test_task_name_requires_an_actual_string_scalar(tmp_path: Path, value: str) -> None:
    tasks = tmp_path / "lm_eval" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "custom.yaml").write_text(
        f"task: {value}\ndataset_path: demo/corpus\n", encoding="utf-8", newline="\n"
    )
    result = runner.invoke(app, ["init", str(tmp_path), "--profiles", "evaluation"])
    assert result.exit_code == 0, result.output
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None
    assert manifest.evaluation.metrics == []


def test_secret_looking_task_names_are_not_persisted(tmp_path: Path) -> None:
    (tmp_path / "run.sh").write_text("lm_eval --tasks custom\n", encoding="utf-8", newline="\n")
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    secret = "sk-" + "a" * 40
    (tasks / "custom.yaml").write_text(f"task: {secret}\n", encoding="utf-8", newline="\n")
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert secret not in (tmp_path / "reprollm.yaml").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "/Users/example/private-experiment",
        r"C:\Users\example\private-experiment",
        r"\\private-host\shared\task",
        "task for example-user",
        "task on private-host",
    ],
)
def test_task_candidates_drop_host_paths_and_machine_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe_name: str
) -> None:
    monkeypatch.setattr("getpass.getuser", lambda: "example-user")
    monkeypatch.setattr("socket.gethostname", lambda: "private-host")
    (tmp_path / "run.sh").write_text("lm_eval --tasks custom\n", encoding="utf-8", newline="\n")
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    for index, name in enumerate(
        ["relative/task", "普通_task", unsafe_name, str(tmp_path / "task")]
    ):
        (tasks / f"{index}.yaml").write_text(
            f"task: {json.dumps(name)}\n", encoding="utf-8", newline="\n"
        )

    result = runner.invoke(
        app, ["init", str(tmp_path), "--task", "relative/task", "--task", "普通_task"]
    )
    assert result.exit_code == 0, result.output
    text = (tmp_path / "reprollm.yaml").read_text(encoding="utf-8")
    manifest = load_manifest(tmp_path / "reprollm.yaml")
    assert manifest.evaluation is not None
    assert [metric.name for metric in manifest.evaluation.metrics] == ["relative/task", "普通_task"]
    assert "example-user" not in text
    assert "private-host" not in text
    assert str(tmp_path) not in text
