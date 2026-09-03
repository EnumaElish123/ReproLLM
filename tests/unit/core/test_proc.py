"""run_cmd tests (spec §22 T-05)."""

from reprollm.core.proc import NOT_FOUND, TIMEOUT, run_cmd


def test_captures_stdout_and_exit_code() -> None:
    result = run_cmd(["echo", "hello"])
    assert result.returncode == 0
    assert result.stdout == "hello\n"
    assert result.stderr == ""


def test_captures_nonzero_exit() -> None:
    assert run_cmd(["false"]).returncode == 1


def test_missing_binary_returns_127() -> None:
    result = run_cmd(["reprollm-definitely-missing-binary-xyz"])
    assert result.returncode == NOT_FOUND
    assert "command not found" in result.stderr


def test_timeout_returns_124() -> None:
    result = run_cmd(["sleep", "30"], timeout=0.2)
    assert result.returncode == TIMEOUT
    assert "timeout" in result.stderr


def test_stderr_captured() -> None:
    result = run_cmd(["python3", "-c", "import sys; sys.stderr.write('boom\\n')"])
    assert result.returncode == 0
    assert "boom" in result.stderr
