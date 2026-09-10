"""M2F-T02: CLI error, exit-code, and traceback contract (F-03)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli import main as cli_main
from reprollm.cli.main import app, cli
from tests.conftest import materialize_repo

runner = CliRunner()


def _run_cli(monkeypatch, argv: list[str], capture: pytest.CaptureFixture):
    monkeypatch.setattr("sys.argv", ["reprollm", *argv])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    captured = capture.readouterr()
    return excinfo.value.code, captured


def test_missing_output_parent_is_user_error(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    target = tmp_path / "missing-parent" / "report.json"
    code, captured = _run_cli(
        monkeypatch,
        ["audit", str(repo), "--format", "json", "--fail-on", "never", "--output", str(target)],
        capsys,
    )
    assert code == 2
    assert "cannot write the audit report" in captured.err
    assert str(target) in captured.err
    assert "Traceback" not in captured.err + captured.out


def test_unexpected_exception_exits_3_without_traceback(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    import reprollm.cli.audit as audit_module

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    monkeypatch.setattr(
        audit_module, "run_audit", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    code, captured = _run_cli(monkeypatch, ["audit", str(repo), "--fail-on", "never"], capsys)
    assert code == 3
    assert "internal error" in captured.err
    assert "RuntimeError" in captured.err
    assert "Traceback" not in captured.err + captured.out


def test_verbose_unexpected_exception_prints_traceback(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    import reprollm.cli.audit as audit_module

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    monkeypatch.setattr(
        audit_module, "run_audit", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    code, captured = _run_cli(monkeypatch, ["-v", "audit", str(repo), "--fail-on", "never"], capsys)
    assert code == 3
    assert "Traceback" in captured.err
    assert "internal error" in captured.err


def test_threshold_exit_1_unchanged(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    monkeypatch.setattr("sys.argv", ["reprollm", "audit", str(repo)])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 1


def test_user_error_exit_2_unchanged(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.argv", ["reprollm", "profiles", "show", "nope"])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2


def test_cli_state_flags_set_by_callback(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    result = runner.invoke(app, ["-v", "-q", "audit", str(repo), "--fail-on", "never"])
    assert result.exit_code == 0
    assert cli_main.STATE["verbose"] is True
    assert cli_main.STATE["quiet"] is True
    cli_main.STATE.update(verbose=False, quiet=False)  # reset for other tests
