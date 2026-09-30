"""M11-T01: evaluation framework integrations — detect, task hints, capture."""

from pathlib import Path

from reprollm.core.git import inspect_git
from reprollm.core.scanner import RepoScanner
from reprollm.integrations.inspect_ai import InspectAIIntegration
from reprollm.integrations.lighteval import LightEvalIntegration
from reprollm.integrations.lm_eval import LmEvalIntegration


def _detect(tmp_path: Path):
    results = {}
    for integration in (LmEvalIntegration(), LightEvalIntegration(), InspectAIIntegration()):
        scanner = RepoScanner(tmp_path, inspect_git(tmp_path))
        evidence = integration.detect(scanner)
        hints = integration.extract_task_hints(scanner)
        results[integration.name] = (evidence, hints)
    return results


def test_lm_eval_detection_via_import(tmp_path: Path) -> None:
    (tmp_path / "eval.py").write_text("import lm_eval\n")
    results = _detect(tmp_path)
    evidence, _ = results["lm_eval"]
    assert evidence, "lm_eval import must be detected"
    assert any("lm_eval" in (e.note or "") for e in evidence)


def test_lm_eval_task_yaml_extraction(tmp_path: Path) -> None:
    (tmp_path / "eval.py").write_text("import lm_eval\n")
    tasks = tmp_path / "lm_eval" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "gsm8k.yaml").write_text(
        "task: gsm8k\ndataset_path: gsm8k\nmetric_list:\n  - metric: exact_match\n"
    )
    (tasks / "mmlu_custom.yaml").write_text("task: mmlu_abstract\ndataset_path: cais/mmlu\n")
    results = _detect(tmp_path)
    _, hints = results["lm_eval"]
    assert "gsm8k" in hints.task_names
    assert "mmlu_abstract" in hints.task_names


def test_lm_eval_capture() -> None:
    captured = LmEvalIntegration().capture()
    assert isinstance(captured, dict)
    assert "lm_eval" in captured


def test_lighteval_detection(tmp_path: Path) -> None:
    (tmp_path / "run.py").write_text("from lighteval import evaluate\n")
    results = _detect(tmp_path)
    evidence, _ = results["lighteval"]
    assert evidence


def test_inspect_ai_detection_and_task_decorator(tmp_path: Path) -> None:
    (tmp_path / "eval_task.py").write_text(
        "from inspect_ai import eval\nfrom inspect_ai.scorer import scorers\n\n"
        "@task\n"
        "def gsm8k_solver():\n"
        "    pass\n"
    )
    results = _detect(tmp_path)
    evidence, hints = results["inspect_ai"]
    assert evidence
    assert "gsm8k_solver" in hints.task_names


def test_no_detection_on_empty_repo(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")
    results = _detect(tmp_path)
    for name, (evidence, _) in results.items():
        assert not evidence, f"{name} must not detect on an unrelated repo"


def test_integration_protocol_shape() -> None:

    for cls in (LmEvalIntegration, LightEvalIntegration, InspectAIIntegration):
        integration = cls()
        assert isinstance(integration.name, str)
        assert callable(integration.detect)
        assert callable(integration.capture)
        assert callable(integration.extract_task_hints)
