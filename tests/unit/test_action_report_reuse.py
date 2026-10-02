"""M9-T01: each composite audit uses one JSON report for every presentation."""

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

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "example,fail_on,expected_exit,missing_primary,inherited_exit",
    [
        ("openai_judge_eval", "critical", 0, False, None),
        ("openai_judge_eval", "warning", 1, False, None),
        ("hf_vllm_eval", "critical", 0, False, None),
        ("hf_vllm_eval", "critical", 0, False, "2"),
        ("hf_vllm_eval", "critical", 0, False, "3"),
        ("openai_judge_eval", "critical", 1, True, None),
    ],
)
def test_json_outputs_summary_annotations_share_same_audit(
    tmp_path: Path,
    example: str,
    fail_on: str,
    expected_exit: int,
    missing_primary: bool,
    inherited_exit: str | None,
) -> None:
    repo = tmp_path / "experiment"
    shutil.copytree(ROOT / "examples" / example, repo)
    if missing_primary:
        # Explicit negative input: the core rule requires models.primary.id.
        manifest_path = repo / "reprollm.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["models"]["primary"]["id"] = None
        manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
        (repo / "reprollm.lock").unlink()
    git = shutil.which("git")
    bash = shutil.which("bash")
    assert git is not None and bash is not None
    env = {
        "PATH": os.pathsep.join(
            (
                str(Path(git).parent),
                str(Path(bash).parent),
                str(Path(sys.executable).parent),
                os.defpath,
            )
        ),
        "NO_COLOR": "1",
        "USERNAME": "trial-user",
        "USER": "trial-user",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(ROOT / "src"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Fake Trial",
        "GIT_AUTHOR_EMAIL": "trial@example.invalid",
        "GIT_COMMITTER_NAME": "Fake Trial",
        "GIT_COMMITTER_EMAIL": "trial@example.invalid",
        "GIT_AUTHOR_DATE": "2026-10-02T00:00:00Z",
        "GIT_COMMITTER_DATE": "2026-10-02T00:00:00Z",
        "GITHUB_OUTPUT": str(tmp_path / "outputs.txt"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
    }
    if inherited_exit is not None:
        env["AUDIT_EXIT"] = inherited_exit
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    for argv in (
        ["git", "init"],
        ["git", "add", "-A"],
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", "Fake baseline"],
    ):
        subprocess.run([git, *argv[1:]], cwd=repo, env=env, capture_output=True, check=True)
    action = yaml.safe_load((ROOT / "action/action.yml").read_text(encoding="utf-8"))
    step = next(step for step in action["runs"]["steps"] if step.get("id") == "audit")
    script = (
        step["run"]
        .replace("${{ inputs.fail-on }}", fail_on)
        .replace("${{ inputs.level != 'auto' && format('--level {0}', inputs.level) || '' }}", "")
    )
    python = shlex.quote(Path(sys.executable).as_posix())
    prefix = (
        f'python() {{ {python} "$@"; }}\n'
        f"reprollm() {{ {python} -c "
        "'from reprollm.cli.main import cli; cli()' \"$@\"; }\n"
    )
    result = subprocess.run(
        [bash, "--noprofile", "--norc", "-e", "-o", "pipefail"],
        input=prefix + script,
        cwd=repo,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stderr
    report = json.loads((repo / "reprollm-audit.json").read_text(encoding="utf-8"))
    critical, warning = report["summary"]["critical"], report["summary"]["warning"]
    if missing_primary:
        assert any(
            finding["rule_id"] == "model.primary_declared"
            and finding["severity"] == "CRITICAL"
            and finding["status"] == "fail"
            for finding in report["findings"]
        )
    notice = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("::notice title=ReproLLM audit::")
    )
    assert f"{critical} critical, {warning} warning" in notice
    assert "code.no_untracked,file=reprollm-audit.json" not in result.stdout
    outputs = (tmp_path / "outputs.txt").read_text(encoding="utf-8")
    assert f"critical-count={critical}" in outputs
    assert f"warning-count={warning}" in outputs
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert f"| CRITICAL | {critical} |" in summary
    assert f"| WARNING | {warning} |" in summary


def test_report_upload_explicitly_runs_after_finding_failure() -> None:
    action = yaml.safe_load((ROOT / "action/action.yml").read_text(encoding="utf-8"))
    upload = next(
        step
        for step in action["runs"]["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    # This is the workflow's failure-upload policy, not a cloud upload claim.
    assert upload.get("if") == "${{ !cancelled() && steps.audit.outputs.report-written == 'true' }}"
