"""A complete shell comment never continues into the next physical command."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.core.yaml_io import load_manifest
from reprollm.integrations.lm_eval import LmEvalIntegration

runner = CliRunner()


def _project(root: Path, text: str, *, with_task: bool = False) -> Path:
    root.mkdir()
    (root / "run.sh").write_text(text, encoding="utf-8")
    if with_task:
        config = root / "configs"
        config.mkdir()
        (config / "safe.yaml").write_text("task: safe\n", encoding="utf-8")
    return root


def _input_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("prefix", ["# ignored ", " \t# ignored "])
def test_backslash_in_standalone_comment_keeps_next_command_on_line_two(
    tmp_path: Path, prefix: str
) -> None:
    root = _project(tmp_path / "shell-project", prefix + "\\\nlm_eval --tasks safe\n")
    before = _input_bytes(root)

    evidence = LmEvalIntegration().detect(AuditContext(root).fs)

    assert [item.model_dump(exclude_none=True) for item in evidence] == [
        {"kind": "detection", "path": "run.sh", "line": 2, "note": "CLI: lm_eval"}
    ]
    assert _input_bytes(root) == before


def test_multiple_standalone_comments_keep_the_real_physical_line(tmp_path: Path) -> None:
    root = _project(
        tmp_path / "shell-project",
        "# first \\\n  # lm_eval --tasks fake \\\nlm_eval --tasks safe\n",
    )

    evidence = LmEvalIntegration().detect(AuditContext(root).fs)

    assert [item.model_dump(exclude_none=True) for item in evidence] == [
        {"kind": "detection", "path": "run.sh", "line": 3, "note": "CLI: lm_eval"}
    ]


def test_comment_contents_do_not_become_framework_commands(tmp_path: Path) -> None:
    root = _project(tmp_path / "shell-project", "# lm_eval --tasks fake \\\nprintf done\n")

    assert LmEvalIntegration().detect(AuditContext(root).fs) == []


@pytest.mark.parametrize(
    ("text", "expected_line"),
    [
        ("python3 \\\n  -m lm_eval --tasks safe\n", 1),
        ('lm_eval --tag "# quoted" --tasks safe\n', 1),
        ("python3 \\\n # lm_eval --tasks hidden \\\n -m lm_eval\n", None),
    ],
)
def test_supported_continuations_quoted_hash_and_pending_comments_are_unchanged(
    tmp_path: Path, text: str, expected_line: int | None
) -> None:
    root = _project(tmp_path / "shell-project", text)

    evidence = LmEvalIntegration().detect(AuditContext(root).fs)

    assert [item.model_dump(exclude_none=True) for item in evidence] == (
        []
        if expected_line is None
        else [
            {
                "kind": "detection",
                "path": "run.sh",
                "line": expected_line,
                "note": "CLI: lm_eval",
            }
        ]
    )


def test_audit_reports_the_real_command_after_a_standalone_comment(tmp_path: Path) -> None:
    root = _project(tmp_path / "shell-project", "# ignored \\\nlm_eval --tasks safe\n")
    before = _input_bytes(root)

    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])

    assert result.exit_code == 0, result.output
    detected = json.loads(result.stdout)["profiles"]["detected"]
    evaluation = next(entry for entry in detected if entry["profile"] == "evaluation")
    assert evaluation["confidence"] == "high"
    assert evaluation["evidence"] == [
        {
            "kind": "detection",
            "path": "run.sh",
            "field": None,
            "line": 2,
            "value": None,
            "expected": None,
            "note": "CLI: lm_eval",
        }
    ]
    assert result.stderr == ""
    assert _input_bytes(root) == before


def test_list_tasks_retains_framework_candidates_after_a_standalone_comment(tmp_path: Path) -> None:
    root = _project(
        tmp_path / "shell-project",
        "# ignored \\\nlighteval accelerate --tasks safe\n",
        with_task=True,
    )
    before = _input_bytes(root)

    result = runner.invoke(app, ["init", str(root), "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "safe\n"
    assert result.stderr == ""
    assert _input_bytes(root) == before
    assert not (root / "reprollm.yaml").exists()
    assert not (root / ".reprollm").exists()


def test_init_keeps_selected_tasks_after_a_standalone_comment(tmp_path: Path) -> None:
    root = _project(
        tmp_path / "shell-project",
        "# ignored \\\nlighteval accelerate --tasks safe\n",
        with_task=True,
    )
    before = _input_bytes(root)

    result = runner.invoke(app, ["init", str(root), "--task", "safe"])

    assert result.exit_code == 0, result.output
    manifest = load_manifest(root / "reprollm.yaml")
    assert "evaluation" in manifest.experiment.profiles
    assert manifest.evaluation is not None
    assert [metric.name for metric in manifest.evaluation.metrics] == ["safe"]
    assert all(metric.implementation is None for metric in manifest.evaluation.metrics)
    after = _input_bytes(root)
    assert {name: after[name] for name in before} == before
