"""Framework CLI/task evidence is static, bounded and grounded in source files."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.integrations.lm_eval import LmEvalIntegration


@pytest.mark.parametrize(
    "command",
    [
        "lm_eval --tasks custom\n",
        "lm-eval --tasks custom\n",
        "python3.12 -m lm_eval --tasks custom\n",
        "python3 \\" + "\n  -m lm_eval --tasks custom\n",
        "env DEVICE=cpu lm_eval --tasks custom\n",
        "uv run lm_eval --tasks custom\n",
        "echo ready && lm_eval --tasks custom\n",
    ],
)
def test_real_cli_entry_is_reported_with_relative_path_and_line(
    tmp_path: Path, command: str
) -> None:
    (tmp_path / "run.sh").write_text(command, encoding="utf-8", newline="\n")
    evidence = LmEvalIntegration().detect(AuditContext(tmp_path).fs)
    assert evidence
    assert all(item.path == "run.sh" and item.line == 1 for item in evidence)


@pytest.mark.parametrize(
    "command",
    [
        "# lm_eval --tasks custom\n",
        'echo "lm_eval --tasks custom"\n',
        "prefix_lm_eval --tasks custom\n",
        "python -m lm_eval_extra --tasks custom\n",
        'lm_eval "unterminated\n',
    ],
)
def test_non_entry_text_never_creates_a_framework_signal(tmp_path: Path, command: str) -> None:
    (tmp_path / "run.sh").write_text(command, encoding="utf-8", newline="\n")
    (tmp_path / "note.py").write_text(
        'note = "import lm_eval"\n# from lm_eval import evaluator\n',
        encoding="utf-8",
        newline="\n",
    )
    assert LmEvalIntegration().detect(AuditContext(tmp_path).fs) == []


def test_task_directory_matching_and_malformed_yaml_are_bounded(tmp_path: Path) -> None:
    unrelated = tmp_path / "tasks_extra"
    unrelated.mkdir()
    (unrelated / "config.yaml").write_text(
        "task: should_not_appear\ndataset_path: demo/corpus\n",
        encoding="utf-8",
        newline="\n",
    )
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "invalid.yaml").write_text("task: [\n", encoding="utf-8", newline="\n")
    (tasks / "sequence.yaml").write_text("- task: nested\n", encoding="utf-8", newline="\n")
    hints = LmEvalIntegration().extract_task_hints(AuditContext(tmp_path).fs)
    assert hints.task_names == []
    assert hints.metrics == []
