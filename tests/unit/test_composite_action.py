"""Execute the composite audit step with fake CLI results (M9-T01, D-11)."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ACTION_FILE = Path(__file__).resolve().parents[2] / "action" / "action.yml"


@pytest.mark.parametrize("audit_exit", [0, 1])
def test_audit_step_preserves_exit_code_after_writing_outputs(
    tmp_path: Path, audit_exit: int
) -> None:
    bash = shutil.which("bash")
    assert bash is not None, "The composite action requires bash."
    action = yaml.safe_load(ACTION_FILE.read_text(encoding="utf-8"))
    step = next(step for step in action["runs"]["steps"] if step.get("id") == "audit")
    script = step["run"].replace("${{ inputs.fail-on }}", "critical")
    script = script.replace(
        "${{ inputs.level != 'auto' && format('--level {0}', inputs.level) || '' }}", ""
    )
    assert "${{" not in script

    python = shlex.quote(Path(sys.executable).as_posix())
    payload = json.dumps(
        {
            "schema_version": 1,
            "reprollm_version": "0.6.1",
            "generated_at": "2026-10-02T00:00:00Z",
            "target": ".",
            "level": 1,
            "profiles": {"resolved": ["core"]},
            "documents": {},
            "summary": {"critical": 1, "warning": 2},
            "findings": [
                {
                    "rule_id": "project.example",
                    "category": "project",
                    "severity": "WARNING",
                    "status": "fail",
                    "level": 1,
                    "message": "Example finding",
                    "fix_hint": "",
                }
            ],
        }
    )
    stubs = f"""
    python() {{ {python} "$@"; }}
    reprollm() {{
      case " $* " in
        *" --format json "*)
          printf '%s\\n' {shlex.quote(payload)} > reprollm-audit.json
          return {audit_exit}
          ;;
        *) return 99 ;;
      esac
    }}
    """
    output = tmp_path / "github-output"
    summary = tmp_path / "github-summary"
    env = {
        "GITHUB_OUTPUT": output.as_posix(),
        "GITHUB_STEP_SUMMARY": summary.as_posix(),
    }
    # Windows needs this for native Python DLL loading; no user shell config is read.
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    result = subprocess.run(
        [bash, "--noprofile", "--norc", "-e", "-o", "pipefail"],
        input=stubs + script,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=10,
        check=False,
    )
    assert result.returncode == audit_exit, result.stderr
    assert output.read_text(encoding="utf-8").splitlines() == [
        "report-written=true",
        "critical-count=1",
        "warning-count=2",
    ]
    step_summary = summary.read_text(encoding="utf-8")
    assert "| CRITICAL | 1 |" in step_summary
    assert "| WARNING | 2 |" in step_summary
    assert "::warning title=WARNING%3A project.example::Example finding" in result.stdout
    assert "1 critical, 2 warning" in result.stdout


def _run_error_step(
    tmp_path: Path, audit_exit: int, *, renderer_fails: bool
) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    assert bash is not None
    action = yaml.safe_load(ACTION_FILE.read_text(encoding="utf-8"))
    step = next(step for step in action["runs"]["steps"] if step.get("id") == "audit")
    script = (
        step["run"]
        .replace("${{ inputs.fail-on }}", "critical")
        .replace("${{ inputs.level != 'auto' && format('--level {0}', inputs.level) || '' }}", "")
    )
    if renderer_fails:
        write_report = (
            'printf \'%s\\n\' \'{"summary":{"critical":1,"warning":2}}\' > reprollm-audit.json'
        )
        python_stub = "python() { return 42; }"
    else:
        write_report = ":"
        python = shlex.quote(Path(sys.executable).as_posix())
        python_stub = f'python() {{ {python} "$@"; }}'
    stubs = f"""
    {python_stub}
    reprollm() {{
      {write_report}
      return {audit_exit}
    }}
    """
    env = {
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return subprocess.run(
        [bash, "--noprofile", "--norc", "-e", "-o", "pipefail"],
        input=stubs + script,
        cwd=tmp_path,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize("audit_exit", [2, 3])
def test_audit_error_without_report_preserves_actual_exit(tmp_path: Path, audit_exit: int) -> None:
    result = _run_error_step(tmp_path, audit_exit, renderer_fails=False)
    assert result.returncode == audit_exit, result.stderr
    assert not (tmp_path / "reprollm-audit.json").exists()
    assert not (tmp_path / "outputs").exists(), "No unavailable count may become zero."
    assert "counts unavailable" in result.stdout


@pytest.mark.parametrize(("audit_exit", "expected_exit"), [(0, 3), (1, 1)])
def test_presentation_error_never_overrides_original_finding_failure(
    tmp_path: Path, audit_exit: int, expected_exit: int
) -> None:
    result = _run_error_step(tmp_path, audit_exit, renderer_fails=True)
    assert result.returncode == expected_exit, result.stderr
    assert "Cannot render reprollm-audit.json" in result.stdout


@pytest.mark.parametrize(("audit_exit", "expected_exit"), [(0, 3), (1, 1)])
def test_missing_report_never_becomes_success(
    tmp_path: Path, audit_exit: int, expected_exit: int
) -> None:
    result = _run_error_step(tmp_path, audit_exit, renderer_fails=False)
    assert result.returncode == expected_exit, result.stderr
    assert not (tmp_path / "outputs").exists(), "Unavailable counts must not be published."
    assert "No reprollm-audit.json was generated; counts unavailable" in result.stdout
