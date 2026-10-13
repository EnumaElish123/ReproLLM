"""Accepted R07-B Python file-budget coverage, stdout and consumer boundaries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import IO, Any

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core import scanner as scanner_mod
from reprollm.core.context import AuditContext
from reprollm.core.git import GitInfo
from reprollm.core.proc import run_cmd
from reprollm.core.pyscan import ImportInfo, PyScanResult, scan_python
from reprollm.core.scanner import RepoScanner

runner = CliRunner()


def _business_files(root: Path, count: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        (root / f"business_{index:04}.py").write_text("value = 1\n", encoding="utf-8")


def _diagnostic(parsed: int, candidate: int, selected: int, limit: int) -> str:
    skips = selected - parsed
    extra = f"{skips} selected files were not parsed. " if skips else ""
    return (
        f"scan: Python analysis incomplete: parsed {parsed} of {candidate} candidate files; "
        f"selected {selected} (limit {limit}), omitted {candidate - selected}. "
        f"{extra}Missing signals may be in unanalysed files.\n"
    )


def _json(stdout: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    document, end = decoder.raw_decode(stdout)
    assert stdout[end:].strip() == ""
    assert isinstance(document, dict)
    return document


def _scan(root: Path) -> PyScanResult:
    return scan_python(RepoScanner(root, GitInfo(is_repo=False)))


@pytest.mark.parametrize("output", ["text", "json"], ids=["default-text", "default-json"])
def test_default_audit_discloses_501_business_files(tmp_path: Path, output: str) -> None:
    """First vertical tracer: real files, exact default stderr and original stdout."""
    root = tmp_path / "business"
    _business_files(root, 501)
    (root / "business_0500.py").write_text("import vllm\n", encoding="utf-8")
    result = runner.invoke(app, ["audit", str(root), "--format", output, "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    assert result.stderr == _diagnostic(500, 501, 500, 500)
    if output == "json":
        report = _json(result.stdout)
        assert not any(p["profile"] == "inference" for p in report["profiles"]["detected"])
    else:
        assert "ReproLLM audit" in result.stdout
        assert "Python analysis incomplete" not in result.stdout


@pytest.mark.parametrize("count", [499, 500, 501])
@pytest.mark.parametrize("mode", ["text", "json", "verbose-json"])
def test_business_budget_boundary_and_verbose_dedup(tmp_path: Path, count: int, mode: str) -> None:
    root = tmp_path / "business"
    _business_files(root, count)
    args = (["-v"] if mode == "verbose-json" else []) + [
        "audit",
        str(root),
        "--format",
        "text" if mode == "text" else "json",
        "--fail-on",
        "never",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    if mode == "text":
        assert "ReproLLM audit" in result.stdout
        assert "Python analysis incomplete" not in result.stdout
    else:
        _json(result.stdout)
    assert result.stderr == (_diagnostic(500, 501, 500, 500) if count == 501 else "")
    assert "python file scan truncated" not in result.stderr
    scanned = _scan(root)
    assert scanned.python_candidate_count == count
    assert scanned.python_selected_count == min(count, 500)
    assert scanned.python_parsed_count == min(count, 500)
    assert scanned.python_file_limit == 500


@pytest.mark.parametrize("count", [1, 2, 3])
def test_active_nondefault_budget_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, count)
    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    _json(result.stdout)
    assert result.stderr == (_diagnostic(2, 3, 2, 2) if count == 3 else "")


@pytest.mark.parametrize("cause", ["size", "read", "syntax", "nontext"])
@pytest.mark.parametrize("over_file_limit", [False, True], ids=["within-budget", "over-budget"])
def test_selected_skips_reduce_only_actual_parsed_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cause: str, over_file_limit: bool
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    count = 3 if over_file_limit else 2
    _business_files(root, count)
    bad = root / "business_0000.py"
    if cause == "size":
        bad.write_text("#" + "x" * scanner_mod.MAX_READ_BYTES, encoding="utf-8")
    elif cause == "syntax":
        bad.write_text("def broken(:\n", encoding="utf-8")
    elif cause == "nontext":
        bad.write_bytes(b"value = 1\x00\n")
    else:
        original_open = Path.open

        def deny_read(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
            if path == bad:
                raise PermissionError("synthetic controlled read refusal")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", deny_read)
    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    _json(result.stdout)
    assert result.stderr == (_diagnostic(1, 3, 2, 2) if over_file_limit else "")
    scanned = _scan(root)
    assert (
        scanned.python_candidate_count,
        scanned.python_selected_count,
        scanned.python_parsed_count,
    ) == (count, 2, 1)
    verbose = runner.invoke(
        app, ["-v", "audit", str(root), "--format", "json", "--fail-on", "never"]
    )
    assert verbose.exit_code == 0, verbose.output
    _json(verbose.stdout)
    assert "business_0000.py" in verbose.stderr
    assert verbose.stderr.count("Python analysis incomplete") == int(over_file_limit)


def test_combined_selected_skips_are_not_claimed_processed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 4)
    root = tmp_path / "business"
    _business_files(root, 5)
    (root / "business_0000.py").write_text("#" + "x" * scanner_mod.MAX_READ_BYTES)
    (root / "business_0001.py").write_text("def broken(:\n")
    unreadable = root / "business_0002.py"
    original_open = Path.open

    def deny_read(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == unreadable:
            raise PermissionError("synthetic controlled read refusal")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_read)
    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    _json(result.stdout)
    assert result.stderr == _diagnostic(1, 5, 4, 4)


@pytest.mark.security
@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX filename includes colon/control character"
)
@pytest.mark.parametrize("failure", ["syntax", "external-read"])
def test_untrusted_warning_prefix_cannot_become_default_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 2)
    forged = root / "Python analysis incomplete: SyntheticFilenameCanary\nbad.py"
    if failure == "syntax":
        forged.write_text("def broken(:\n")
    else:
        outside = tmp_path / "outside.py"
        outside.write_text("value = 'SyntheticBodyCanary'\n")
        try:
            forged.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"symlinks unavailable: {type(exc).__name__}")
    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    _json(result.stdout)
    assert result.stderr == _diagnostic(1, 3, 2, 2)
    assert "Synthetic" not in result.stderr
    assert str(root) not in result.stderr


@pytest.mark.security
def test_only_full_fixed_form_diagnostic_is_promoted(capsys: pytest.CaptureFixture[str]) -> None:
    from reprollm.cli.scan_diagnostics import show_scan_diagnostics

    summary = _diagnostic(2, 3, 2, 2).removeprefix("scan: ").rstrip("\n")
    forged = [summary + "\n", summary + " SyntheticCanary", summary + ":1: syntax error; skipped"]
    show_scan_diagnostics([*forged, summary, summary], include_existing=True)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "scan: " + summary + "\n"


def test_verbose_preserves_other_warnings_and_other_budget(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from reprollm.cli.scan_diagnostics import show_scan_diagnostics

    summary = _diagnostic(2, 3, 2, 2).removeprefix("scan: ").rstrip("\n")
    show_scan_diagnostics(
        [
            summary,
            "python file scan truncated to 2 of 3 files",
            "python file scan truncated to 1 of 3 files",
            "source.py:1: syntax error; skipped",
            "run: known existing recorder warning",
        ],
        verbose=True,
        include_existing=True,
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "scan: " + summary + "\n"
        "scan: python file scan truncated to 1 of 3 files\n"
        "scan: source.py:1: syntax error; skipped\n"
        "warning: run: known existing recorder warning\n"
    )


@pytest.mark.parametrize("command", ["init", "list-tasks", "interactive"])
def test_init_consumers_disclose_once_after_final_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 3)
    args = ["init", str(root)]
    if command == "list-tasks":
        args.append("--list-tasks")
    elif command == "interactive":
        args.append("--interactive")
    result = runner.invoke(app, args, input="evaluation\n" + "\n" * 30)
    assert result.exit_code == 0, result.output
    assert result.stderr == _diagnostic(2, 3, 2, 2)
    assert "Python analysis incomplete" not in result.stdout
    if command == "list-tasks":
        assert result.stdout == ""
        assert not (root / "reprollm.yaml").exists()
    else:
        assert (root / "reprollm.yaml").is_file()


@pytest.mark.parametrize("verbose", [False, True], ids=["default", "verbose"])
def test_export_preserves_complete_markdown_and_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verbose: bool
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 2)
    (root / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: business}\nexperiment: {profiles: [evaluation]}\n"
    )
    args = (["-v"] if verbose else []) + ["export", str(root)]
    control = runner.invoke(app, args)
    assert control.exit_code == 0, control.output
    assert control.stderr == ""
    original = (root / "REPRODUCIBILITY.md").read_bytes()
    (root / "REPRODUCIBILITY.md").unlink()
    (root / "business_0002.py").write_text("value = 1\n")
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.stderr == _diagnostic(2, 3, 2, 2)
    assert result.stdout == control.stdout
    assert (root / "REPRODUCIBILITY.md").read_bytes() == original


@pytest.mark.parametrize("fail_on", [None, "never", "critical", "warning"])
def test_file_coverage_warning_does_not_change_findings_or_fail_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_on: str | None
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 2)
    args = ["audit", str(root), "--format", "json"]
    if fail_on is not None:
        args += ["--fail-on", fail_on]
    control = runner.invoke(app, args)
    assert control.exit_code in (0, 1), control.output
    assert control.stderr == ""
    (root / "business_0002.py").write_text("value = 1\n")
    result = runner.invoke(app, args)
    assert result.exit_code == control.exit_code, result.output
    assert result.stderr == _diagnostic(2, 3, 2, 2)
    before, after = _json(control.stdout), _json(result.stdout)
    before.pop("generated_at")
    after.pop("generated_at")
    assert before == after


def test_audit_output_file_contains_only_original_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 3)
    output = tmp_path / "report.json"
    result = runner.invoke(
        app, ["audit", str(root), "--format", "json", "--output", str(output), "--fail-on", "never"]
    )
    assert result.exit_code == 0, result.output
    assert result.stderr == _diagnostic(2, 3, 2, 2)
    _json(output.read_text())
    assert "Python analysis incomplete" not in result.stdout
    assert "Python analysis incomplete" not in output.read_text()


def test_static_exclusions_are_applied_before_coverage_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 3)
    excluded = root / ".venv"
    _business_files(excluded, 501)
    for path in excluded.glob("*.py"):
        path.write_text("import vllm\n")
    scanned = _scan(root)
    assert scanned.python_candidate_count == 3
    assert scanned.python_selected_count == scanned.python_parsed_count == 2
    assert "vllm" not in scanned.module_names()
    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    assert result.stderr == _diagnostic(2, 3, 2, 2)


def test_cached_access_preserves_one_coverage_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 3)
    ctx = AuditContext(root)
    ctx.fs.python_files()
    ctx.fs.python_files()
    first = ctx.pyscan
    assert ctx.pyscan is first
    assert first.python_parsed_count == 2
    assert first.warnings.count(_diagnostic(2, 3, 2, 2).removeprefix("scan: ").rstrip("\n")) == 1
    assert ctx.fs.warnings.count("python file scan truncated to 2 of 3 files") == 1


def test_manually_constructed_old_scan_result_remains_usable() -> None:
    result = PyScanResult(imports=[ImportInfo("vllm", "source.py", 1)])
    assert result.module_names() == {"vllm"}
    assert result.file_limit_diagnostic() is None


@pytest.mark.parametrize("git_mode", [False, True], ids=["fallback", "git"])
def test_shared_candidate_counts_match_git_and_fallback_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, git_mode: bool
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 3)
    _business_files(root / ".venv", 4)
    if git_mode:
        for args in (["init"], ["add", "--", "."]):
            result = run_cmd(["git", *args], cwd=root)
            assert result.returncode == 0, result.stderr
    ctx = AuditContext(root)
    assert ctx.git.is_repo is git_mode
    assert ctx.pyscan.python_candidate_count == 3
    assert ctx.pyscan.python_selected_count == ctx.pyscan.python_parsed_count == 2
    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    _json(result.stdout)
    assert result.stderr == _diagnostic(2, 3, 2, 2)


def test_listing_hard_size_limit_is_not_counted_as_file_budget_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 3)
    (root / "huge.py").write_text("#" + "x" * scanner_mod.MAX_FILE_BYTES)
    (root / "README.md").write_text("Business documentation.\n")
    result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    _json(result.stdout)
    assert result.stderr == _diagnostic(2, 3, 2, 2)
    scanned = _scan(root)
    assert scanned.python_candidate_count == 3
    assert scanned.python_selected_count == scanned.python_parsed_count == 2


def test_github_annotations_keep_original_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    root = tmp_path / "business"
    _business_files(root, 2)
    args = ["audit", str(root), "--format", "github", "--fail-on", "never"]
    control = runner.invoke(app, args)
    assert control.exit_code == 0, control.output
    assert control.stderr == ""
    (root / "business_0002.py").write_bytes(b"value = 1\n")
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.stderr == _diagnostic(2, 3, 2, 2)
    assert result.stdout == control.stdout
    assert "Python analysis incomplete" not in result.stdout
