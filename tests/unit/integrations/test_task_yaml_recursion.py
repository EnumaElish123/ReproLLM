"""Failed task YAML composition leaves other framework candidates usable."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner
from yaml.nodes import Node

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.core.yaml_io import load_manifest
from reprollm.integrations.lighteval import LightEvalIntegration
from reprollm.integrations.lm_eval import LmEvalIntegration

runner = CliRunner()
_MARKER = "# synthetic-task-yaml-parser-recursion"
_CANARY = "SyntheticTaskYamlParserSecretCanary"


def _project(root: Path, framework: str = "lm_eval", *, shallow: bool = True) -> Path:
    root.mkdir()
    tasks = root / "tasks"
    tasks.mkdir()
    (tasks / "a_unavailable.yaml").write_text(
        f"{_MARKER}\ntask: unavailable\ndataset_path: demo/corpus\n", encoding="utf-8"
    )
    if shallow:
        (tasks / "z_safe.yaml").write_text(
            "task: safe\ndataset_path: demo/corpus\nmetric_list:\n  - metric: accuracy\n",
            encoding="utf-8",
        )
    if framework == "lighteval":
        (root / "run.sh").write_text("lighteval accelerate --tasks safe\n", encoding="utf-8")
    return root


def _input_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _composition_failure(monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    original_compose = yaml.compose

    def limited_compose(stream: str, **kwargs: Any) -> Node | None:
        if _MARKER in stream:
            raise failure
        return original_compose(stream, **kwargs)

    monkeypatch.setattr(yaml, "compose", limited_compose)


@pytest.mark.parametrize("framework", ["lm_eval", "lighteval"])
def test_task_inventory_keeps_shallow_candidates_after_composer_recursion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, framework: str
) -> None:
    root = _project(tmp_path / "tasks-project", framework)
    before = _input_bytes(root)
    _composition_failure(monkeypatch, RecursionError(_CANARY))
    integration = LmEvalIntegration() if framework == "lm_eval" else LightEvalIntegration()

    hints = integration.extract_task_hints(AuditContext(root).fs)

    assert hints.task_names == ["safe"]
    assert hints.metrics == (["accuracy"] if framework == "lm_eval" else [])
    assert _input_bytes(root) == before


def test_lm_eval_detection_uses_next_recognizable_yaml_after_composer_recursion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path / "tasks-project")
    _composition_failure(monkeypatch, RecursionError(_CANARY))

    evidence = LmEvalIntegration().detect(AuditContext(root).fs)

    assert [item.model_dump(exclude_none=True) for item in evidence] == [
        {"kind": "detection", "path": "tasks/z_safe.yaml", "note": "lm_eval task YAML"}
    ]


@pytest.mark.security
def test_audit_does_not_invent_framework_evidence_from_failed_task_composition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path / "tasks-project", shallow=False)
    before = _input_bytes(root)
    _composition_failure(monkeypatch, RecursionError(f"{_CANARY}: {root / 'private.yaml'}"))

    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert not any(
        entry["profile"] == "evaluation" and entry["confidence"] == "high"
        for entry in report["profiles"]["detected"]
    )
    assert result.stderr == ""
    assert _CANARY not in result.stdout + result.stderr
    assert str(root) not in result.stdout + result.stderr
    assert _input_bytes(root) == before


@pytest.mark.parametrize("framework", ["lm_eval", "lighteval"])
def test_list_tasks_retains_complete_shallow_inventory_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, framework: str
) -> None:
    root = _project(tmp_path / "tasks-project", framework)
    before = _input_bytes(root)
    _composition_failure(monkeypatch, RecursionError(_CANARY))

    result = runner.invoke(app, ["init", str(root), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "safe\n"
    assert result.stderr == ""
    assert _input_bytes(root) == before
    assert not (root / "reprollm.yaml").exists()
    assert not (root / ".reprollm").exists()


@pytest.mark.parametrize("framework", ["lm_eval", "lighteval"])
def test_init_persists_selected_shallow_task_and_preserves_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, framework: str
) -> None:
    root = _project(tmp_path / "tasks-project", framework)
    before = _input_bytes(root)
    _composition_failure(monkeypatch, RecursionError(_CANARY))

    result = runner.invoke(app, ["init", str(root), "--task", "safe"])

    assert result.exit_code == 0, result.output
    manifest = load_manifest(root / "reprollm.yaml")
    assert "evaluation" in manifest.experiment.profiles
    assert manifest.evaluation is not None
    assert [metric.name for metric in manifest.evaluation.metrics] == ["safe"]
    assert all(metric.implementation is None for metric in manifest.evaluation.metrics)
    after = _input_bytes(root)
    assert {name: after[name] for name in before} == before
    assert _CANARY not in after["reprollm.yaml"].decode("utf-8")


@pytest.mark.parametrize("failure_type", [RuntimeError, MemoryError])
def test_task_composition_preserves_unexpected_exceptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    root = _project(tmp_path / "tasks-project")
    _composition_failure(monkeypatch, failure_type(_CANARY))

    with pytest.raises(failure_type, match=_CANARY):
        LmEvalIntegration().extract_task_hints(AuditContext(root).fs)


def test_task_composition_retains_existing_malformed_yaml_skip(tmp_path: Path) -> None:
    root = _project(tmp_path / "tasks-project")
    (root / "tasks" / "a_unavailable.yaml").write_text("task: [\n", encoding="utf-8")

    for integration in (LmEvalIntegration(), LightEvalIntegration()):
        hints = integration.extract_task_hints(AuditContext(root).fs)
        assert hints.task_names == ["safe"]
