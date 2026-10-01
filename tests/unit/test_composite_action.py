"""Execute the composite audit step with fake CLI results (M9-T01, D-11)."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ACTION_FILE = Path(__file__).resolve().parents[2] / "action" / "action.yml"


@pytest.mark.parametrize("audit_exit", [0, 1, 2, 3])
@pytest.mark.parametrize("annotation_exit", [0, 1])
def test_audit_step_preserves_exit_code_after_writing_outputs(
    tmp_path: Path, audit_exit: int, annotation_exit: int
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
    stubs = f"""
    python() {{ {python} "$@"; }}
    reprollm() {{
      case " $* " in
        *" --format json "*)
          printf '%s\\n' '{{"summary":{{"critical":1,"warning":2}}}}' > reprollm-audit.json
          return {audit_exit}
          ;;
        *" --format github "*)
          printf '%s\\n' '::warning title=ReproLLM::Example finding'
          return {annotation_exit}
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
        "critical-count=1",
        "warning-count=2",
    ]
    step_summary = summary.read_text(encoding="utf-8")
    assert "| CRITICAL | 1 |" in step_summary
    assert "| WARNING | 2 |" in step_summary
    assert "::warning title=ReproLLM::Example finding" in result.stdout
