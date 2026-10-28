"""Primary Python parser limits through the accepted public CLI boundary."""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

import reprollm
from reprollm.cli.main import app
from tests.conftest import commit_all, make_git_repo
from tests.unit.cli.test_audit import (
    _coverage_cli_json,
    _coverage_cli_repo,
    _declared_profile_absence_repo,
)

runner = CliRunner()


def _fail_parse(monkeypatch: pytest.MonkeyPatch, failed_filename: str, failure: Exception) -> None:
    original_parse = ast.parse

    def limited_parse(
        source: str | bytes,
        filename: str = "<unknown>",
        mode: str = "exec",
        **kwargs: Any,
    ) -> ast.AST:
        if filename == failed_filename:
            raise failure
        return original_parse(source, filename=filename, mode=mode, **kwargs)

    monkeypatch.setattr(ast, "parse", limited_parse)


def _input_bytes(repo: Path) -> dict[str, bytes]:
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }


def _uninitialized_repo(tmp_path: Path) -> Path:
    repo = make_git_repo(tmp_path / "parser-init")
    (repo / "a_bad.py").write_text("import peft\n", encoding="utf-8")
    (repo / "z_ok.py").write_text(
        "import vllm\n"
        "from transformers import AutoTokenizer\n"
        "AutoTokenizer.from_pretrained('org/model')\n",
        encoding="utf-8",
    )
    (repo / "requirements.txt").write_text("vllm==0.6.0\ntransformers==4.46.0\n", encoding="utf-8")
    (repo / "README.md").write_text("User-owned research input.\n", encoding="utf-8")
    tasks = repo / "tasks"
    tasks.mkdir()
    (tasks / "demo.yaml").write_text(
        "task: demo_task\ndataset_path: demo/corpus\n", encoding="utf-8"
    )
    commit_all(repo)
    return repo


@pytest.mark.security
def test_audit_skips_parser_recursion_and_keeps_positive_sibling_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "a.py").write_text("import vllm\n", encoding="utf-8")
    (repo / "z.py").write_text("import peft\n", encoding="utf-8")
    (repo / "requirements.txt").write_text("torch==2.5.1\nvllm==0.6.0\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.chdir(repo)
    canary = f"SyntheticParserSecretCanary {repo / 'private-source.py'}"
    _fail_parse(monkeypatch, "z.py", RecursionError(canary))

    result = runner.invoke(app, ["-v", "audit", ".", "--format", "json", "--fail-on", "warning"])

    assert result.exit_code == 0, result.output
    assert result.stderr == "scan: z.py: Python parser recursion limit exceeded; skipped\n"
    assert canary not in result.stdout + result.stderr
    assert str(repo) not in result.stdout + result.stderr
    report = _coverage_cli_json(result.stdout)
    assert report["target"] == "."
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 1,
        "pass": 4,
        "suppressed": 0,
        "skipped": 1,
    }
    by_id = {finding["rule_id"]: finding for finding in report["findings"]}
    assert len(report["findings"]) == len(by_id) == 6
    assert set(by_id) == {
        "code.git_repo",
        "code.git_commit",
        "code.clean_tree",
        "code.no_untracked",
        "env.llm_critical_deps_pinned",
        "exec.profile_detection_mismatch",
    }
    assert all(
        finding["status"] == "pass" for rid, finding in by_id.items() if rid.startswith("code.")
    )
    gap = by_id["env.llm_critical_deps_pinned"]
    assert (gap["status"], gap["severity"], gap["severity_origin"]) == (
        "skipped",
        "INFO",
        "default",
    )
    assert gap["message"] == (
        "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 2 (limit 500); no rule-wide PASS is established."
    )
    assert gap["evidence"] == []
    positive = by_id["exec.profile_detection_mismatch"]
    assert (positive["status"], positive["severity"]) == ("fail", "INFO")
    assert positive["message"] == (
        "detected profile 'inference' (high confidence) is not declared in experiment.profiles"
    )
    assert [(item["path"], item["line"], item["note"]) for item in positive["evidence"]] == [
        ("a.py", 1, "import vllm")
    ]
    assert [(item["profile"], item["confidence"]) for item in report["profiles"]["detected"]] == [
        ("inference", "high")
    ]


def test_default_audit_parser_gap_is_quiet_and_repeated_reports_keep_input_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    monkeypatch.chdir(repo)
    before = _input_bytes(repo)
    _fail_parse(monkeypatch, "z.py", RecursionError("controlled parser recursion"))
    args = ["audit", ".", "--format", "json", "--fail-on", "warning"]

    first = runner.invoke(app, args)
    repeated = runner.invoke(app, args)

    assert first.exit_code == repeated.exit_code == 0
    assert first.stderr == repeated.stderr == ""
    report = _coverage_cli_json(first.stdout)
    second = _coverage_cli_json(repeated.stdout)
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 2,
    }
    gaps = [finding for finding in report["findings"] if finding["status"] == "skipped"]
    assert [finding["rule_id"] for finding in gaps] == [
        "env.llm_critical_deps_pinned",
        "exec.profile_detection_mismatch",
    ]
    assert all(
        finding["message"]
        == (
            "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
            "selected 2 (limit 500); no rule-wide PASS is established."
        )
        for finding in gaps
    )
    report.pop("generated_at")
    second.pop("generated_at")
    assert second == report
    assert _input_bytes(repo) == before


def test_audit_parser_skip_and_real_file_budget_share_one_exact_default_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    for index in range(499):
        (repo / f"business_{index:04}.py").write_text("value = 1\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.chdir(repo)
    _fail_parse(monkeypatch, "a.py", RecursionError("controlled parser recursion"))
    args = ["audit", ".", "--format", "json", "--fail-on", "warning"]

    default = runner.invoke(app, args)
    verbose = runner.invoke(app, ["-v", *args])

    assert default.exit_code == verbose.exit_code == 0
    summary = (
        "scan: Python analysis incomplete: parsed 499 of 501 candidate files; "
        "selected 500 (limit 500), omitted 1. 1 selected files were not parsed. "
        "Missing signals may be in unanalysed files.\n"
    )
    assert default.stderr == summary
    assert verbose.stderr == (
        summary + "scan: a.py: Python parser recursion limit exceeded; skipped\n"
    )
    report = _coverage_cli_json(default.stdout)
    verbose_report = _coverage_cli_json(verbose.stdout)
    gaps = [finding for finding in report["findings"] if finding["status"] == "skipped"]
    assert len(gaps) == 2
    assert all(
        finding["message"]
        == (
            "Python candidate analysis incomplete: parsed 499 of 501 candidate files; "
            "selected 500 (limit 500); no rule-wide PASS is established."
        )
        for finding in gaps
    )
    assert report["profiles"]["detected"] == []
    report.pop("generated_at")
    verbose_report.pop("generated_at")
    assert verbose_report == report


@pytest.mark.parametrize(("fail_on", "exit_code"), [("warning", 1), ("critical", 0)])
def test_audit_parser_gap_keeps_independent_warning_gate_and_later_positive_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fail_on: str,
    exit_code: int,
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "requirements.txt").write_text("torch>=2.5.1\nvllm==0.6.0\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.chdir(repo)
    _fail_parse(monkeypatch, "a.py", RecursionError("controlled parser recursion"))

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", fail_on])

    assert result.exit_code == exit_code, result.output
    assert result.stderr == ""
    report = _coverage_cli_json(result.stdout)
    assert report["summary"] == {
        "critical": 0,
        "warning": 1,
        "info": 1,
        "pass": 4,
        "suppressed": 0,
        "skipped": 0,
    }
    by_id = {finding["rule_id"]: finding for finding in report["findings"]}
    warning = by_id["env.llm_critical_deps_pinned"]
    assert (warning["status"], warning["severity"]) == ("fail", "WARNING")
    assert warning["message"].startswith("torch is used but not pinned to an exact version ")
    assert [
        (item["path"], item["line"], item["value"], item["note"]) for item in warning["evidence"]
    ] == [("requirements.txt", 1, ">=2.5.1", "declared as >=2.5.1")]
    positive = by_id["exec.profile_detection_mismatch"]
    assert (positive["status"], positive["severity"]) == ("fail", "INFO")
    assert positive["message"] == (
        "detected profile 'inference' (high confidence) is not declared in experiment.profiles"
    )
    assert [(item["path"], item["line"], item["note"]) for item in positive["evidence"]] == [
        ("z.py", 1, "import vllm")
    ]


def test_audit_parser_gap_uses_existing_declared_profile_absence_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _declared_profile_absence_repo(tmp_path)
    monkeypatch.chdir(repo)
    before = _input_bytes(repo)
    args = ["audit", ".", "--format", "json", "--fail-on", "critical"]

    with monkeypatch.context() as parser_boundary:
        _fail_parse(parser_boundary, "z.py", RecursionError("controlled parser recursion"))
        gap_result = runner.invoke(app, args)
    completed_result = runner.invoke(app, args)

    assert gap_result.exit_code == 0, gap_result.output
    assert completed_result.exit_code == 1, completed_result.output
    assert gap_result.stderr == completed_result.stderr == ""
    report = _coverage_cli_json(gap_result.stdout)
    assert report["profiles"]["declared"] == ["inference"]
    assert report["profiles"]["detected"] == []
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 2,
    }
    absence = next(
        finding
        for finding in report["findings"]
        if finding["rule_id"] == "exec.profile_detection_mismatch"
    )
    assert (absence["status"], absence["severity"], absence["severity_origin"]) == (
        "skipped",
        "INFO",
        "default",
    )
    assert absence["message"] == (
        "declared profile 'inference' has no detection evidence in the analysed inputs; "
        "Python candidate analysis is incomplete or unavailable, so absence is not established"
    )
    assert [(item["kind"], item["field"], item["note"]) for item in absence["evidence"]] == [
        ("field", "experiment.profiles", "inference declared; detection absence unverified")
    ]
    completed = _coverage_cli_json(completed_result.stdout)
    completed_absence = next(
        finding
        for finding in completed["findings"]
        if finding["rule_id"] == "exec.profile_detection_mismatch"
    )
    assert (completed_absence["status"], completed_absence["severity"]) == ("fail", "CRITICAL")
    assert completed_absence["severity_origin"] == "profile:core"
    assert completed_absence["message"] == (
        "declared profile 'inference' has no detection evidence in this repository"
    )
    assert _input_bytes(repo) == before


def test_list_tasks_survives_primary_parser_recursion_without_writing_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _uninitialized_repo(tmp_path)
    monkeypatch.chdir(repo)
    before = _input_bytes(repo)
    _fail_parse(monkeypatch, "a_bad.py", RecursionError("SyntheticParserSecretCanary"))

    result = runner.invoke(app, ["-v", "init", ".", "--list-tasks"])

    assert result.exit_code == 0, result.output
    assert result.stdout == "demo_task\n"
    assert result.stderr == ""
    assert _input_bytes(repo) == before
    assert not (repo / ".reprollm").exists()
    assert not (repo / "reprollm.yaml").exists()


def test_init_keeps_normal_hints_and_selected_task_after_primary_parser_recursion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _uninitialized_repo(tmp_path)
    monkeypatch.chdir(repo)
    before = _input_bytes(repo)
    _fail_parse(monkeypatch, "a_bad.py", RecursionError("SyntheticParserSecretCanary"))

    result = runner.invoke(app, ["-v", "init", ".", "--task", "demo_task"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert "Applied detected profiles: evaluation, inference." in result.stdout
    manifest_text = (repo / "reprollm.yaml").read_text(encoding="utf-8")
    manifest = yaml.safe_load(manifest_text)
    assert manifest["schema_version"] == 1
    assert manifest["experiment"]["profiles"] == ["evaluation", "inference"]
    assert manifest["models"]["primary"]["id"] == "org/model"
    assert manifest["inference"]["backend"] is None
    assert [metric["name"] for metric in manifest["evaluation"]["metrics"]] == ["demo_task"]
    assert all(metric.get("implementation") is None for metric in manifest["evaluation"]["metrics"])
    assert "SyntheticParserSecretCanary" not in manifest_text
    assert str(repo) not in manifest_text
    after = _input_bytes(repo)
    assert {name: after[name] for name in before} == before
    assert set(after) - set(before) == {
        "reprollm.yaml",
        ".reprollm/config.yaml",
        ".reprollm/project-rules.yaml",
    }


def test_export_survives_parser_recursion_and_keeps_repeatable_document_and_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    monkeypatch.chdir(repo)
    before = _input_bytes(repo)
    _fail_parse(monkeypatch, "z.py", RecursionError("SyntheticParserSecretCanary"))
    args = ["-v", "export", "."]

    first = runner.invoke(app, args)

    assert first.exit_code == 0, first.output
    assert first.stderr == ""
    output = repo / "REPRODUCIBILITY.md"
    document = output.read_bytes()
    assert "0 critical · 0 warning ·\n0 info · 4 passed." in document.decode("utf-8")
    assert "Python parser recursion" not in document.decode("utf-8")
    assert "Python candidate analysis" not in document.decode("utf-8")
    assert "SyntheticParserSecretCanary" not in document.decode("utf-8")
    output.unlink()
    assert _input_bytes(repo) == before

    repeated = runner.invoke(app, args)

    assert repeated.exit_code == 0, repeated.output
    assert repeated.stderr == ""
    assert repeated.stdout == first.stdout
    assert output.read_bytes() == document
    after = _input_bytes(repo)
    assert {name: after[name] for name in before} == before
    assert set(after) - set(before) == {"REPRODUCIBILITY.md"}


def test_native_parser_recursion_under_read_cap_completes_public_console_audit(
    tmp_path: Path,
) -> None:
    expression = "value = " + " + ".join(["value"] * 10000) + "\n"
    assert len(expression.encode("utf-8")) == 80006
    probe_code = (
        "import ast, sys\n"
        "try:\n"
        "    ast.parse(sys.stdin.read())\n"
        "except RecursionError:\n"
        "    print('recursion')\n"
        "else:\n"
        "    print('parsed')\n"
    )
    try:
        probe = subprocess.run(
            [sys.executable, "-c", probe_code],
            input=expression,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("Native AST probe exceeded 30 seconds; no parser-recovery proof is claimed.")
    if probe.returncode < 0 or (sys.platform == "win32" and probe.returncode & 0x80000000):
        pytest.skip(
            f"Native AST probe exited with process failure {probe.returncode}; "
            "this fix handles Python RecursionError, not native process crashes."
        )
    assert probe.returncode == 0 and probe.stderr == "", probe.stderr
    if probe.stdout == "parsed\n":
        pytest.skip(
            "This interpreter parses the native 80-KiB expression; injected boundary cases "
            "cover parser RecursionError without changing its recursion limit."
        )
    assert probe.stdout == "recursion\n"
    repo = _coverage_cli_repo(tmp_path)
    (repo / "z.py").write_text(expression, encoding="utf-8")
    commit_all(repo)
    before = _input_bytes(repo)
    source_root = Path(reprollm.__file__).resolve().parent.parent
    console_code = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); from reprollm.cli.main import cli; cli()"
    )

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                console_code,
                str(source_root),
                "-v",
                "audit",
                ".",
                "--format",
                "json",
                "--fail-on",
                "warning",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("Native console probe exceeded 30 seconds; no recovery proof is claimed.")
    if result.returncode < 0 or (sys.platform == "win32" and result.returncode & 0x80000000):
        pytest.skip(
            f"Native console probe exited with process failure {result.returncode}; "
            "this fix does not protect against native process crashes."
        )

    assert result.returncode == 0, result.stderr
    assert result.stderr == "scan: z.py: Python parser recursion limit exceeded; skipped\n"
    report = _coverage_cli_json(result.stdout)
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 2,
    }
    assert [
        finding["message"] for finding in report["findings"] if finding["status"] == "skipped"
    ] == [
        "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 2 (limit 500); no rule-wide PASS is established.",
        "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 2 (limit 500); no rule-wide PASS is established.",
    ]
    assert _input_bytes(repo) == before


def test_normal_binary_expression_keeps_successful_parsing_and_pass_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "z.py").write_text("value = " + " + ".join(["value"] * 100) + "\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["-v", "audit", ".", "--format", "json", "--fail-on", "warning"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = _coverage_cli_json(result.stdout)
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 6,
        "suppressed": 0,
        "skipped": 0,
    }
    assert all(finding["status"] == "pass" for finding in report["findings"])


def test_parser_recursion_keeps_existing_syntax_diagnostic_and_both_parse_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "m_syntax.py").write_text("def f(:\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.chdir(repo)
    _fail_parse(monkeypatch, "z.py", RecursionError("controlled parser recursion"))

    result = runner.invoke(app, ["-v", "audit", ".", "--format", "json", "--fail-on", "warning"])

    assert result.exit_code == 0, result.output
    assert result.stderr == (
        "scan: m_syntax.py:1: syntax error; skipped\n"
        "scan: z.py: Python parser recursion limit exceeded; skipped\n"
    )
    report = _coverage_cli_json(result.stdout)
    gaps = [finding for finding in report["findings"] if finding["status"] == "skipped"]
    assert [finding["rule_id"] for finding in gaps] == [
        "env.llm_critical_deps_pinned",
        "exec.profile_detection_mismatch",
    ]
    assert all(
        finding["message"]
        == (
            "Python candidate analysis incomplete: parsed 1 of 3 candidate files; "
            "selected 3 (limit 500); no rule-wide PASS is established."
        )
        for finding in gaps
    )


@pytest.mark.parametrize(
    ("boundary", "exception_type"),
    [
        pytest.param("parse", MemoryError, id="parser-memory-error"),
        pytest.param("parse", RuntimeError, id="parser-unexpected-error"),
        pytest.param("walk", RecursionError, id="tree-walk-recursion-error"),
    ],
)
def test_unrelated_parser_errors_and_tree_walk_recursion_are_not_silently_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    exception_type: type[Exception],
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    monkeypatch.chdir(repo)
    if boundary == "parse":
        _fail_parse(monkeypatch, "z.py", exception_type("controlled external parser failure"))
    else:

        def failed_walk(node: ast.AST) -> Any:
            raise RecursionError("controlled external tree-walk failure")

        monkeypatch.setattr(ast, "walk", failed_walk)

    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "warning"])

    assert result.exit_code != 0
    assert isinstance(result.exception, exception_type)
    assert result.stdout == result.stderr == ""
