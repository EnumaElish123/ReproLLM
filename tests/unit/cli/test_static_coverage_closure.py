"""PROPOSED §12.3.16 acceptance: write before policy implementation.

This file is a nonexecuted draft outside the product worktree. Expected findings
come from the frozen normative patch; fault injection uses external interfaces.
"""

import json
import os
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core import proc
from reprollm.core._toml import tomllib
from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.proc import CmdResult
from reprollm.integrations.lm_eval import LmEvalIntegration
from reprollm.schemas.finding import AuditReport

runner = CliRunner()
_CANARY = "SyntheticStaticCoverageFailureCanary"
_LISTING_REASON = (
    "Repository listing is incomplete in the captured eligible view; "
    "no rule-wide PASS is established."
)
_PROFILE_REASON = (
    "Static profile detection is incomplete in the captured eligible view; "
    "no rule-wide PASS is established."
)
_HINTS = {
    "env.dependency_manifest_present": (
        "Add a pyproject.toml, requirements*.txt, or environment.yml that declares "
        "the dependencies of this experiment."
    ),
    "env.lockfile_present": (
        "Commit a uv.lock/poetry.lock, or pin every dependency with `==` in "
        "requirements.txt so the environment can be rebuilt exactly."
    ),
    "env.llm_critical_deps_pinned": (
        "Pin the package exactly (see the message for the suggested version)."
    ),
    "env.python_version_declared": (
        "Add `requires-python` to pyproject.toml, a .python-version file, or a "
        "`python=3.x` entry in environment.yml."
    ),
    "env.secret_files_ignored": (
        "Remove the secret file from the repository, rotate the secret, and add the "
        "pattern to .gitignore (keep only .env.example-style templates)."
    ),
    "exec.profile_detection_mismatch": (
        "Review experiment.profiles in reprollm.yaml against the detection evidence; "
        "add or remove a profile only to describe the selected experiment. Capabilities "
        "used by other repository workflows need no manifest change."
    ),
}


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _manifest(root: Path, profiles: Sequence[str] = ()) -> None:
    _write(
        root,
        "reprollm.yaml",
        yaml.safe_dump(
            {
                "schema_version": 1,
                "project": {"name": "captured-view"},
                "experiment": {"profiles": list(profiles)},
            }
        ),
    )


def _core(root: Path, rules: Sequence[str], severity: str | None = None) -> None:
    _write(
        root,
        ".reprollm/profiles/core.yaml",
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Captured static evidence acceptance.",
                "rules": list(rules),
                "severity_overrides": {rules[0]: severity} if severity else {},
            }
        ),
    )


def _inputs(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _rows(report: AuditReport, rule: str) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in report.findings if item.rule_id == rule]


def _file(path: str | None, note: str, *, line: int | None = None) -> dict[str, Any]:
    return {
        "kind": "file",
        "path": path,
        "field": None,
        "line": line,
        "value": None,
        "expected": None,
        "note": note,
    }


def _skip(
    rule: str,
    message: str,
    gaps: Sequence[tuple[str, str | None]] = (),
    *,
    first: Sequence[dict[str, Any]] = (),
    level: int = 0,
) -> dict[str, Any]:
    return {
        "rule_id": rule,
        "aliases": [],
        "category": rule.split(".", 1)[0],
        "severity": "INFO",
        "status": "skipped",
        "level": level,
        "message": message,
        "evidence": [
            *first,
            *[
                _file(path, f"{scope} analysis incomplete in the captured eligible view")
                for scope, path in gaps
            ],
        ],
        "fix_hint": _HINTS[rule],
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


def _git(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    listing_failure: bool = False,
    files: Sequence[str] | None = None,
    is_repo: bool = True,
) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []
    captured = list(files) if files is not None else list(_inputs(root))

    def command(
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float = 30,
        env: Mapping[str, str] | None = None,
    ) -> CmdResult:
        del cwd, timeout, env
        args = tuple(argv)
        calls.append(args)
        assert args[0] == "git", args
        if args[1:] == ("rev-parse", "--is-inside-work-tree"):
            return CmdResult(0, "true\n", "") if is_repo else CmdResult(128, "", "not git")
        if args[1:] == ("rev-parse", "--show-toplevel"):
            return CmdResult(0, str(root) + "\n", "")
        if args[1:] == ("rev-parse", "HEAD"):
            return CmdResult(0, "a" * 40 + "\n", "")
        if args[1:] in (("branch", "--show-current"), ("rev-parse", "--abbrev-ref", "HEAD")):
            return CmdResult(0, "main\n", "")
        if args[1:] == ("status", "--porcelain"):
            return CmdResult(0, "", "")
        if args[1:] == ("remote", "get-url", "origin"):
            return CmdResult(0, "https://example.invalid/repo.git\n", "")
        if args[1:2] == ("ls-files",):
            if listing_failure:
                return CmdResult(128, "", f"{_CANARY}: {root / 'private'}")
            return CmdResult(0, "\0".join(captured) + "\0", "")
        raise AssertionError(f"Unexpected external command: {args}")

    monkeypatch.setattr(proc, "run_cmd", command)
    return calls


def _deny_open(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    original = Path.open

    def open_file(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == path:
            raise PermissionError(f"{_CANARY}: {path}")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)


def _stat_failure(
    monkeypatch: pytest.MonkeyPatch, path: Path, failure: OSError | None = None
) -> None:
    original = Path.stat
    error = failure if failure is not None else PermissionError(_CANARY)

    def stat_file(self: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        if self == path:
            raise error
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_file)


def test_failed_git_listing_skips_manifest_absence_without_leaking_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "requirements.txt", "torch==2.6.0\n")
    calls = _git(monkeypatch, tmp_path, listing_failure=True)

    report = run_audit(tmp_path)

    assert _rows(report, "env.dependency_manifest_present") == [
        _skip(
            "env.dependency_manifest_present",
            "dependency manifest absence is not established because repository "
            "listing is incomplete in the captured eligible view",
            [("listing", None)],
        )
    ]
    assert _CANARY not in report.model_dump_json()
    assert str(tmp_path) not in report.model_dump_json()
    assert sum(args[1:2] == ("ls-files",) for args in calls) == 1


def test_fallback_walk_error_is_a_source_free_listing_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(monkeypatch, tmp_path, is_repo=False)
    original = os.walk

    def walk(top: Any, *args: Any, **kwargs: Any) -> Iterator[Any]:
        yield from original(top, *args, **kwargs)
        callback = kwargs.get("onerror")
        if callback is not None:
            callback(PermissionError(f"{_CANARY}: /private/unavailable"))

    monkeypatch.setattr(os, "walk", walk)

    report = run_audit(tmp_path)

    assert _rows(report, "env.dependency_manifest_present")[0]["evidence"] == [
        _file(None, "listing analysis incomplete in the captured eligible view")
    ]
    assert _rows(report, "env.dependency_manifest_present")[0]["status"] == "skipped"
    assert _CANARY not in report.model_dump_json()


def test_observed_positive_witnesses_and_secret_violation_survive_listing_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "requirements.txt", "torch==2.6.0\n")
    _write(tmp_path, ".python-version", "3.12\n")
    _write(tmp_path, ".env", "SYNTHETIC_VALUE=example\n")
    _write(tmp_path, "lost.bin", "not relevant\n")
    _git(monkeypatch, tmp_path)
    _stat_failure(monkeypatch, tmp_path / "lost.bin")

    report = run_audit(tmp_path)

    for rule in [
        "env.dependency_manifest_present",
        "env.lockfile_present",
        "env.python_version_declared",
    ]:
        assert _rows(report, rule)[0]["status"] == "pass"
    # Existing package credit survives; the chosen empty aggregate veto is conservative.
    assert _rows(report, "env.llm_critical_deps_pinned") == [
        _skip("env.llm_critical_deps_pinned", _LISTING_REASON)
    ]
    secret = _rows(report, "env.secret_files_ignored")
    assert len(secret) == 1
    assert (secret[0]["status"], secret[0]["severity"]) == ("fail", "CRITICAL")
    assert secret[0]["evidence"] == [_file(".env", "matches a forbidden file pattern (§16.4)")]


def test_directory_name_walk_failure_only_vetoes_detection_after_earlier_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest(tmp_path)
    _git(monkeypatch, tmp_path, is_repo=False)
    original = os.walk
    calls = 0

    def walk(top: Any, *args: Any, **kwargs: Any) -> Iterator[Any]:
        nonlocal calls
        calls += 1
        if calls == 2:
            callback = kwargs.get("onerror")
            if callback is not None:
                callback(PermissionError(_CANARY))
            return
        yield from original(top, *args, **kwargs)

    monkeypatch.setattr(os, "walk", walk)

    report = run_audit(tmp_path)

    assert _rows(report, "env.dependency_manifest_present")[0]["status"] == "fail"
    assert _rows(report, "env.python_version_declared")[0]["status"] == "fail"
    assert _rows(report, "env.secret_files_ignored")[0]["status"] == "pass"
    assert _rows(report, "exec.profile_detection_mismatch") == [
        _skip("exec.profile_detection_mismatch", _PROFILE_REASON, level=1)
    ]


def test_silently_missing_file_remains_outside_observed_gap_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "vanished.txt", "placeholder\n")
    _git(monkeypatch, tmp_path)
    _stat_failure(monkeypatch, tmp_path / "vanished.txt", FileNotFoundError(2, "gone"))

    report = run_audit(tmp_path)

    assert _rows(report, "env.dependency_manifest_present")[0]["status"] == "fail"
    assert _rows(report, "env.secret_files_ignored")[0]["status"] == "pass"


def test_remaining_known_package_skip_keeps_use_evidence_before_listing_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "worker.py", "import torch\n")
    _write(tmp_path, "lost.bin", "placeholder\n")
    _git(monkeypatch, tmp_path)
    _stat_failure(monkeypatch, tmp_path / "lost.bin")

    report = run_audit(tmp_path)

    assert _rows(report, "env.llm_critical_deps_pinned") == [
        _skip(
            "env.llm_critical_deps_pinned",
            "torch is used; repository listing is incomplete in the captured eligible "
            "view, so missing pin evidence is not established",
            [("listing", "lost.bin")],
            first=[_file("worker.py", "imported", line=1)],
        )
    ]


@pytest.mark.parametrize(
    "cause", ["associated_lock", "python_lock", "declaration", "depth", "include"]
)
def test_accepted_dependency_cause_retains_complete_finding_before_listing_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    _write(tmp_path, "worker.py", "import torch\n")
    _write(tmp_path, "lost.bin", "placeholder\n")
    if cause == "associated_lock":
        _write(tmp_path, "pyproject.toml", '[project]\nname="example"\n')
        _write(tmp_path, "uv.lock", "package = [\n")
        message = "an associated format lock could not be read or parsed"
    elif cause == "python_lock":
        _write(tmp_path, "broken.py", "def invalid(\n")
        _write(tmp_path, "uv.lock", '[[package]]\nname="torch"\n')
        message = "a captured format lock lists the package"
    elif cause == "declaration":
        _write(tmp_path, "environment.yml", "dependencies: [\n")
        message = "a dependency declaration body could not be read or parsed"
    elif cause == "depth":
        _write(tmp_path, "requirements.txt", "-r nested/0.txt\n")
        for index in range(15):
            _write(tmp_path, f"nested/{index}.txt", f"-r {index + 1}.txt\n")
        _write(tmp_path, "nested/15.txt", "torch==2.6.0\n")
        message = "a supported requirements include was not expanded within the depth budget"
    else:
        _write(tmp_path, "requirements.txt", "-r build/pins.txt\n")
        _write(tmp_path, "build/pins.txt", "torch==2.6.0\n")
        message = "a supported requirements include target was excluded from static analysis"
    _git(monkeypatch, tmp_path)
    settled = _rows(run_audit(tmp_path), "env.llm_critical_deps_pinned")
    assert settled[0]["status"] == "skipped"
    assert message in settled[0]["message"]
    _stat_failure(monkeypatch, tmp_path / "lost.bin")

    report = run_audit(tmp_path)

    assert _rows(report, "env.llm_critical_deps_pinned") == settled


@pytest.mark.parametrize("failure", ["read", "decode"])
def test_python_version_absence_uses_only_actual_relevant_body_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\nname="example"\n')
    if failure == "read":
        _deny_open(monkeypatch, tmp_path / "pyproject.toml")
    else:
        _write(tmp_path, "pyproject.toml", "[project\n")

    report = run_audit(tmp_path)

    assert _rows(report, "env.python_version_declared") == [
        _skip(
            "env.python_version_declared",
            "Python version declaration absence is not established because eligible "
            "static inputs could not be fully analysed",
            [("python_version", "pyproject.toml")],
        )
    ]


def test_positive_python_version_witness_overrides_an_unrelated_failed_source(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "pyproject.toml", "[project\n")
    _write(tmp_path, ".python-version", "3.12\n")

    assert _rows(run_audit(tmp_path), "env.python_version_declared")[0]["status"] == "pass"


@pytest.mark.parametrize("source", ["README.md", "config.json", "run.sh"])
def test_non_python_detection_gaps_skip_declared_absence_but_not_python_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    _manifest(tmp_path, ["safety"])
    _write(
        tmp_path, source, {"README.md": "notes\n", "config.json": "{", "run.sh": 'echo "\n'}[source]
    )
    if source == "README.md":
        _deny_open(monkeypatch, tmp_path / source)

    report = run_audit(tmp_path)

    profile = _rows(report, "exec.profile_detection_mismatch")
    field = {
        "kind": "field",
        "path": None,
        "field": "experiment.profiles",
        "line": None,
        "value": None,
        "expected": None,
        "note": "safety declared; detection absence unverified",
    }
    assert profile == [
        _skip(
            "exec.profile_detection_mismatch",
            "declared profile 'safety' has no detection evidence in the analysed inputs; "
            "static profile detection is incomplete in the captured eligible view, "
            "so absence is not established",
            [("detection", source)],
            first=[field],
            level=1,
        )
    ]
    assert _rows(report, "env.python_version_declared")[0]["status"] == "fail"


def test_non_python_gap_vetoes_empty_profile_pass_with_zero_python_candidates(
    tmp_path: Path,
) -> None:
    _manifest(tmp_path)
    _write(tmp_path, "config.json", "{")

    report = run_audit(tmp_path)

    assert _rows(report, "exec.profile_detection_mismatch") == [
        _skip("exec.profile_detection_mismatch", _PROFILE_REASON, level=1)
    ]


def test_profile_gap_does_not_suppress_observed_high_confidence_mismatch(tmp_path: Path) -> None:
    _manifest(tmp_path, ["safety"])
    _write(tmp_path, "config.json", "{")
    _write(tmp_path, "worker.py", "import peft\n")

    report = run_audit(tmp_path)

    findings = _rows(report, "exec.profile_detection_mismatch")
    assert [(item["status"], item["severity"]) for item in findings] == [
        ("skipped", "INFO"),
        ("fail", "INFO"),
    ]
    positive = findings[1]
    assert positive["message"] == (
        "detected profile 'finetuning' (high confidence) is not declared in experiment.profiles"
    )
    assert [(item["path"], item["line"]) for item in positive["evidence"]] == [("worker.py", 1)]


def test_primary_python_gap_reason_still_has_priority_over_non_python_gap(tmp_path: Path) -> None:
    _manifest(tmp_path)
    _write(tmp_path, "broken.py", "def invalid(\n")
    _write(tmp_path, "config.json", "{")

    report = run_audit(tmp_path)

    assert _rows(report, "exec.profile_detection_mismatch") == [
        _skip(
            "exec.profile_detection_mismatch",
            "Python candidate analysis incomplete: parsed 0 of 1 candidate files; "
            "selected 1 (limit 500); no rule-wide PASS is established.",
            level=1,
        )
    ]


def test_task_hint_collection_does_not_invent_a_detection_attempt_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "tasks/failed.yaml", "task: bad\n")
    _write(tmp_path, "tasks/working.yaml", "task: safe\ndataset_path: demo/corpus\n")
    _deny_open(monkeypatch, tmp_path / "tasks/failed.yaml")
    scanner = AuditContext(tmp_path).fs

    hints = LmEvalIntegration().extract_task_hints(scanner)

    assert hints.task_names == ["safe"]
    assert scanner.static_gaps("detection") == ()


@pytest.mark.parametrize(
    "rule", ["env.dependency_manifest_present", "env.llm_critical_deps_pinned"]
)
def test_isolated_absence_gate_changes_from_one_to_zero_without_threshold_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rule: str
) -> None:
    _core(tmp_path, [rule], "CRITICAL")
    if rule.endswith("pinned"):
        _write(tmp_path, "worker.py", "import torch\n")
        _write(tmp_path, "lost.bin", "placeholder\n")
        _git(monkeypatch, tmp_path)
        _stat_failure(monkeypatch, tmp_path / "lost.bin")
    else:
        _git(monkeypatch, tmp_path, listing_failure=True)

    result = runner.invoke(
        app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "critical"]
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert len(report["findings"]) == 1
    assert (report["findings"][0]["status"], report["findings"][0]["severity"]) == (
        "skipped",
        "INFO",
    )
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }


def test_suppression_keeps_new_gap_evidence_and_original_info_severity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rule = "env.dependency_manifest_present"
    _core(tmp_path, [rule])
    _write(
        tmp_path,
        ".reprollm/config.yaml",
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.dependency_manifest_present\n      reason: Reviewed listing.\n",
    )
    _git(monkeypatch, tmp_path, listing_failure=True)

    result = runner.invoke(
        app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "critical"]
    )

    assert result.exit_code == 0, result.output
    item = json.loads(result.stdout)["findings"][0]
    assert (item["status"], item["severity"], item["suppressed_reason"]) == (
        "suppressed",
        "INFO",
        "Reviewed listing.",
    )
    assert item["evidence"][:-1] == [
        _file(None, "listing analysis incomplete in the captured eligible view")
    ]
    assert item["evidence"][-1]["note"] == (
        "suppressed: original severity INFO; reason: Reviewed listing."
    )


def test_default_text_json_and_export_keep_gap_visibility_and_owned_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest(tmp_path)
    _core(tmp_path, ["exec.profile_detection_mismatch"])
    _write(tmp_path, "config.json", "{")
    before = _inputs(tmp_path)
    default = runner.invoke(app, ["audit", str(tmp_path), "--no-color", "--fail-on", "warning"])
    shown = runner.invoke(
        app, ["audit", str(tmp_path), "--no-color", "--show-skipped", "--fail-on", "warning"]
    )
    structured = runner.invoke(
        app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "warning"]
    )

    assert default.exit_code == shown.exit_code == structured.exit_code == 0
    assert "Findings: PASS" in default.stdout and _PROFILE_REASON not in default.stdout
    assert _PROFILE_REASON in shown.stdout
    assert json.loads(structured.stdout)["findings"] == [
        _skip("exec.profile_detection_mismatch", _PROFILE_REASON, level=1)
    ]
    assert _inputs(tmp_path) == before
    exported = runner.invoke(app, ["export", str(tmp_path), "--output", "reports/result.md"])
    assert exported.exit_code == 0, exported.output
    after = _inputs(tmp_path)
    assert set(after) - set(before) == {"reports/result.md"}
    assert {name: after[name] for name in before} == before
    assert _PROFILE_REASON not in after["reports/result.md"].decode("utf-8")


@pytest.mark.parametrize("failure", [RecursionError, MemoryError])
def test_dependency_decoder_limit_is_typed_without_swallowing_other_resource_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: type[Exception]
) -> None:
    marker = "# bounded-decoder-failure"
    _write(tmp_path, "pyproject.toml", marker + '\n[project]\nname="example"\n')
    _write(tmp_path, "worker.py", "import torch\n")
    original = tomllib.loads

    def decode(text: str, **kwargs: Any) -> Any:
        if marker in text:
            raise failure(_CANARY)
        return original(text, **kwargs)

    monkeypatch.setattr(tomllib, "loads", decode)
    if failure is MemoryError:
        with pytest.raises(MemoryError, match=_CANARY):
            run_audit(tmp_path)
        return

    report = run_audit(tmp_path)

    assert _rows(report, "env.llm_critical_deps_pinned")[0]["status"] == "skipped"
    assert _rows(report, "env.python_version_declared")[0]["status"] == "skipped"
    assert _CANARY not in report.model_dump_json()
    assert AuditContext(tmp_path).deps.declaration_read_issues == {"pyproject.toml": "parser_limit"}


def test_known_manifest_without_lock_skips_only_lock_absence_under_listing_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "requirements.txt", "torch>=2\n")
    _write(tmp_path, "lost.bin", "placeholder\n")
    _git(monkeypatch, tmp_path)
    _stat_failure(monkeypatch, tmp_path / "lost.bin")

    report = run_audit(tmp_path)

    assert _rows(report, "env.dependency_manifest_present")[0]["status"] == "pass"
    assert _rows(report, "env.lockfile_present") == [
        _skip(
            "env.lockfile_present",
            "lockfile absence is not established because repository listing is "
            "incomplete in the captured eligible view",
            [("listing", "lost.bin")],
        )
    ]


def test_actual_environment_marker_inspection_failure_records_its_safe_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "environment/worker.py", "import torch\n")
    _git(monkeypatch, tmp_path)
    original = Path.exists

    def exists(self: Path) -> bool:
        if self == tmp_path / "environment/pyvenv.cfg":
            raise PermissionError(f"{_CANARY}: {self}")
        return original(self)

    monkeypatch.setattr(Path, "exists", exists)

    report = run_audit(tmp_path)

    item = _rows(report, "env.dependency_manifest_present")[0]
    assert item["status"] == "skipped"
    assert item["evidence"] == [
        _file("environment", "listing analysis incomplete in the captured eligible view")
    ]
    assert _CANARY not in report.model_dump_json()
    assert not any(
        finding["status"] == "fail" for finding in _rows(report, "env.llm_critical_deps_pinned")
    )


def test_init_and_task_listing_keep_healthy_signals_and_only_owned_output_files(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "config.json", "{")
    _write(tmp_path, "run.sh", "inspect eval tasks.py\n")
    _write(
        tmp_path,
        "tasks.py",
        "from inspect_ai import task\n@task\ndef alpha():\n    return None\n",
    )
    before = _inputs(tmp_path)

    listed = runner.invoke(app, ["init", str(tmp_path), "--list-tasks"])

    assert listed.exit_code == 0, listed.output
    assert listed.stdout == "alpha\n"
    assert _inputs(tmp_path) == before
    initialized = runner.invoke(app, ["init", str(tmp_path), "--task", "alpha"])
    assert initialized.exit_code == 0, initialized.output
    after = _inputs(tmp_path)
    assert {name: after[name] for name in before} == before
    assert set(after) - set(before) == {
        "reprollm.yaml",
        ".reprollm/config.yaml",
        ".reprollm/project-rules.yaml",
    }
    manifest = yaml.safe_load(after["reprollm.yaml"])
    assert [metric["name"] for metric in manifest["evaluation"]["metrics"]] == ["alpha"]
