"""D03: publication must be downstream of candidate quality and artifact checks."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40
REPOSITORY = "EnumaElish123/ReproLLM"


def _workflow(name: str) -> dict[str, Any]:
    # BaseLoader preserves GitHub's `on` key rather than YAML 1.1 boolean coercion.
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def _needs(job: dict[str, Any]) -> set[str]:
    value = job.get("needs", [])
    return {value} if isinstance(value, str) else set(value)


def _step(job: dict[str, Any], name: str) -> dict[str, Any]:
    return next(step for step in job["steps"] if step.get("name") == name)


def test_ci_and_release_use_the_same_five_platform_quality_gate() -> None:
    ci = _workflow("ci.yml")["jobs"]["quality"]
    release = _workflow("release.yml")["jobs"]["quality"]
    assert ci["uses"] == release["uses"] == "./.github/workflows/quality.yml"
    assert ci["with"]["commit"] == "${{ github.sha }}"
    assert release["with"]["commit"] == "${{ needs.prepare.outputs.commit }}"
    quality = _workflow("quality.yml")
    assert quality["on"]["workflow_call"]["inputs"]["commit"]["required"] == "true"
    job = quality["jobs"]["quality"]
    assert {(item["os"], item["python"]) for item in job["strategy"]["matrix"]["include"]} == {
        ("ubuntu-latest", "3.10"),
        ("ubuntu-latest", "3.11"),
        ("ubuntu-latest", "3.12"),
        ("macos-latest", "3.12"),
        ("windows-latest", "3.12"),
    }
    assert _step(job, "Install dependencies")["run"] == "uv sync --locked --dev"
    assert job["steps"][0]["with"]["ref"] == "${{ inputs.commit }}"
    assert _step(job, "Verify candidate checkout")["env"]["EXPECTED_COMMIT"] == (
        "${{ inputs.commit }}"
    )
    names = [step.get("name") for step in job["steps"]]
    assert names.index("Redaction branch coverage") < names.index("Security leakage gate")
    assert {
        "Lint",
        "Format check",
        "Type check",
        "Test",
        "Schema freshness",
        "Generated documentation freshness",
        "Examples stay valid",
        "ReproLLM self-audit (bootstrapped dogfooding)",
        "ReproLLM self-audit via the published Action",
    } <= set(names)


def test_release_dependency_graph_does_not_allow_partial_or_wrong_commit_success() -> None:
    jobs = _workflow("release.yml")["jobs"]
    assert _needs(jobs["quality"]) == {"prepare"}
    assert _needs(jobs["build"]) == {"prepare", "quality"}
    assert _needs(jobs["publish"]) == {"prepare", "quality", "build"}
    assert _needs(jobs["github-release"]) == {"prepare", "quality", "build", "publish"}
    for name in ("publish", "github-release"):
        condition = jobs[name]["if"]
        assert "github.event_name == 'push'" in condition
        assert "startsWith(github.ref, 'refs/tags/v')" in condition
        for dependency in _needs(jobs[name]):
            assert f"needs.{dependency}.result == 'success'" in condition
        assert "always()" not in condition
    # Every artifact consumer checks out the resolved commit, rather than moving main.
    for name in ("build", "publish", "github-release"):
        checkout = next(step for step in jobs[name]["steps"] if "checkout@" in step.get("uses", ""))
        assert checkout["with"]["ref"] == "${{ needs.prepare.outputs.commit }}"


def _condition(node: ast.AST) -> Any:
    """Evaluate only the GitHub condition subset used by publication jobs."""
    if isinstance(node, ast.Expression):
        return _condition(node.body)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        return all(_condition(value) for value in node.values)
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
        return _condition(node.left) == _condition(node.comparators[0])
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "startsWith"
        and len(node.args) == 2
        and not node.keywords
    ):
        return _condition(node.args[0]).startswith(_condition(node.args[1]))
    pytest.fail(f"unreviewed workflow condition syntax: {ast.dump(node)}")


def _can_start(job: dict[str, Any], states: dict[str, str], event: str, ref: str) -> bool:
    if any(states.get(name) != "success" for name in _needs(job)):
        return False
    expression = re.sub(r"needs\.([\w-]+)\.result", lambda match: repr(states[match[1]]), job["if"])
    expression = expression.replace("github.event_name", repr(event)).replace(
        "github.ref", repr(ref)
    )
    return bool(_condition(ast.parse(expression.replace("&&", " and ").strip(), mode="eval")))


@pytest.mark.parametrize("job_name", ["publish", "github-release"])
@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", "missing"])
def test_publication_is_blocked_for_every_unsuccessful_prerequisite(
    job_name: str, result: str
) -> None:
    job = _workflow("release.yml")["jobs"][job_name]
    success = dict.fromkeys(_needs(job), "success")
    assert _can_start(job, success, "push", "refs/tags/v0.7.0")
    for dependency in _needs(job):
        states = {**success, dependency: result}
        assert not _can_start(job, states, "push", "refs/tags/v0.7.0")


@pytest.mark.parametrize(
    "event,ref",
    [
        ("workflow_dispatch", "refs/tags/v0.7.0"),
        ("workflow_dispatch", "refs/heads/main"),
        ("push", "refs/heads/main"),
        ("push", "refs/tags/other"),
    ],
)
def test_manual_rehearsal_and_non_release_events_can_never_publish(event: str, ref: str) -> None:
    workflow = _workflow("release.yml")
    assert {"tag", "validation_run_id"} <= set(workflow["on"]["workflow_dispatch"]["inputs"])
    for name in ("publish", "github-release"):
        job = workflow["jobs"][name]
        assert not _can_start(job, dict.fromkeys(_needs(job), "success"), event, ref)


@pytest.mark.parametrize("actual", [SHA, "b" * 40, "main"])
def test_reusable_quality_executes_an_exact_checkout_guard(
    monkeypatch: pytest.MonkeyPatch, actual: str
) -> None:
    job = _workflow("quality.yml")["jobs"]["quality"]
    guard = _step(job, "Verify candidate checkout")
    monkeypatch.setenv("EXPECTED_COMMIT", SHA)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: actual + "\n")
    if actual == SHA:
        exec(compile(guard["run"], "quality-checkout", "exec"), {})
    else:
        with pytest.raises(SystemExit, match="candidate checkout"):
            exec(compile(guard["run"], "quality-checkout", "exec"), {})


def test_release_builds_once_and_reauthorizes_downloaded_artifacts_before_both_writes() -> None:
    jobs = _workflow("release.yml")["jobs"]
    builds = [
        (name, step)
        for name, job in jobs.items()
        for step in job.get("steps", [])
        if step.get("run", "").strip() == "uv build"
    ]
    assert len(builds) == 1 and builds[0][0] == "build"
    dist = next(
        step
        for step in jobs["build"]["steps"]
        if "upload-artifact@" in step.get("uses", "") and step["with"]["name"] == "dist"
    )
    assert set(dist["with"]["path"].split()) == {"dist/*.whl", "dist/*.tar.gz"}
    for name, writer in (
        ("publish", "Publish to PyPI"),
        ("github-release", "Create GitHub Release"),
    ):
        steps = jobs[name]["steps"]
        auth = _step(jobs[name], "Authorize downloaded release artifacts")
        assert "scripts/release_gate.py authorize" in auth["run"]
        assert auth["env"]["QUALITY_RESULT"] == "${{ needs.quality.result }}"
        assert steps.index(auth) < steps.index(_step(jobs[name], writer))
        downloads = [step for step in steps if "download-artifact@" in step.get("uses", "")]
        assert {step["with"]["name"] for step in downloads} == {
            "dist",
            "release-evidence",
            "validated-release-inputs",
        }
        assert all(steps.index(step) < steps.index(auth) for step in downloads)
    assert jobs["publish"]["permissions"] == {"contents": "read", "id-token": "write"}
    assert jobs["github-release"]["permissions"] == {"contents": "write"}
    assert _step(jobs["github-release"], "Create GitHub Release")["with"]["body_path"] == (
        "release-evidence/release-notes.md"
    )


def _metadata(tmp_path: Path, changes: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    prepare = _workflow("release.yml")["jobs"]["prepare"]
    program = _step(prepare, "Verify validation run metadata")["run"]
    assert _step(prepare, "Verify validation run metadata")["shell"] == "python"
    metadata = {
        "id": 123,
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
    }
    metadata.update(changes)
    (tmp_path / "validation-run.json").write_text(json.dumps(metadata), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={
            **os.environ,
            "RUNNER_TEMP": str(tmp_path),
            "EXPECTED_COMMIT": SHA,
            "EXPECTED_REPOSITORY": REPOSITORY,
            "VALIDATION_RUN_ID": "123",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_validation_artifact_requires_a_successful_same_repository_run(tmp_path: Path) -> None:
    result = _metadata(tmp_path, {})
    assert result.returncode == 0, result.stderr
    receipt = json.loads((tmp_path / "release-evidence/validation-run.json").read_text())
    assert receipt == {
        "schema_version": 1,
        "id": 123,
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"head_sha": "b" * 40},
        {"conclusion": "failure"},
        {"conclusion": "cancelled"},
        {"status": "in_progress"},
        {"id": 124},
        {"id": True},
        {"repository": {"full_name": "other/repo"}},
        {"head_repository": {"full_name": "other/fork"}},
        {"head_repository": None},
    ],
)
def test_validation_artifact_rejects_untrusted_or_incomplete_run(
    tmp_path: Path, changes: dict[str, Any]
) -> None:
    result = _metadata(tmp_path, changes)
    assert result.returncode != 0
    assert not (tmp_path / "release-evidence/validation-run.json").exists()


def test_validation_run_receipt_excludes_api_actor_data(tmp_path: Path) -> None:
    result = _metadata(tmp_path, {"actor": {"login": "synthetic-user"}, "path": "/host/private"})
    assert result.returncode == 0, result.stderr
    receipt = (tmp_path / "release-evidence/validation-run.json").read_text()
    assert "synthetic-user" not in receipt and "/host/private" not in receipt
