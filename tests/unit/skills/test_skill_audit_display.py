"""Project binding displays only after native audit rules have compared values."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_audit_display as display  # noqa: E402
import skill_runtime as runtime  # noqa: E402

RUN_ID = "20261030T010000Z-aaaaaa"
CANARY = "OpaqueHistoricalAuditSource123456"
MARKER = "<REDACTED:generic_kv>"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "研究 project"
    root.mkdir()
    return root


def inventory(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def bundle(
    root: Path,
    *,
    field: str = "custom.alpha",
    declared: Any = "public-declared-value",
    observations: list[dict[str, Any]] | None = None,
    severity: str = "WARNING",
) -> None:
    from reprollm.schemas.manifest import Manifest
    from reprollm.schemas.run_record import RunRecord

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "project": {"name": "public-audit-probe"},
        "experiment": {"profiles": []},
    }
    current: dict[str, Any] = manifest
    parts = field.split(".")
    for name in parts[:-1]:
        current = current.setdefault(name, {})
    current[parts[-1]] = declared
    if field.startswith("models."):
        manifest["models"][parts[1]]["provider"] = "huggingface"
    Manifest.model_validate(manifest)
    (root / "reprollm.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    (root / ".reprollm").mkdir(exist_ok=True)
    if field.startswith("custom."):
        (root / ".reprollm/project-rules.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "rules": [
                        {
                            "id": "project.alpha",
                            "field": field,
                            "severity": severity,
                            "reason": "Public synthetic audit display check",
                            "source": "manual",
                            "accepted_at": "2026-10-30T00:00:00Z",
                            "bindings": {"cli": "--alpha"},
                        }
                    ],
                },
                sort_keys=False,
            )
        )
    record = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "run_id": RUN_ID,
        "status": "completed",
        "exit_code": 0,
        "command": {"argv": ["python", "eval.py"], "cwd": "."},
        "bindings_observed": {
            field: observations
            if observations is not None
            else [{"value": CANARY, "source": {"type": "cli", "key": "--api-key"}}]
        },
    }
    RunRecord.model_validate(record)
    folder = root / ".reprollm/runs" / RUN_ID
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(json.dumps(record, ensure_ascii=False) + "\n")


def arguments(root: Path, format: str = "json", *, fail_on: str = "never") -> list[str]:
    return [
        "audit",
        str(root),
        "--level",
        "2",
        "--format",
        format,
        "--fail-on",
        fail_on,
        *(["--details", "--show-passed", "--show-skipped"] if format == "text" else []),
    ]


def invoke(root: Path, argv: list[str]) -> tuple[runtime.CliResult, list[dict[str, Any]]]:
    return display.invoke_private_audit(
        argv,
        root,
        invoke_cli=runtime.invoke_cli,
        sanitize=lambda value, notes: runtime._sanitize(
            value, root, action="runs.show", diagnostics=notes
        ),
    )


def normalized(report: dict[str, Any]) -> dict[str, Any]:
    report = copy.deepcopy(report)
    report.pop("generated_at", None)
    return report


def conclusions(report: dict[str, Any]) -> dict[str, Any]:
    report = normalized(report)
    for finding in report["findings"]:
        finding.pop("message")
        finding.pop("evidence")
    return report


def target(report: dict[str, Any], rule_id: str = "consistency.custom_fields") -> dict[str, Any]:
    return next(finding for finding in report["findings"] if finding["rule_id"] == rule_id)


@pytest.mark.parametrize("format", ["json", "text", "github"])
@pytest.mark.parametrize(
    "source",
    [
        {"type": "cli", "key": "--api-key"},
        {"type": "config", "key": "credentials.password", "path": "configs/options.yaml"},
        {"type": "env", "key": "HF_TOKEN"},
    ],
)
def test_private_binding_is_masked_after_raw_comparison_on_every_report_surface(
    project: Path, format: str, source: dict[str, Any]
) -> None:
    bundle(project, observations=[{"value": CANARY, "source": source}])
    before = inventory(project)
    raw_json = runtime.invoke_cli(arguments(project), project)
    assert raw_json.exit_code == 0 and CANARY in raw_json.stdout
    raw = json.loads(raw_json.stdout)
    assert target(raw)["status"] == "fail"
    result, diagnostics = invoke(project, arguments(project, format))
    assert result.exit_code == raw_json.exit_code and CANARY not in result.stdout
    assert MARKER in result.stdout and not result.stderr and diagnostics
    if format == "json":
        safe = json.loads(result.stdout)
        assert conclusions(safe) == conclusions(raw)
        actual = target(safe)
        assert actual["evidence"][0]["value"] == "public-declared-value"
        assert actual["evidence"][1]["value"] == MARKER
        assert actual["evidence"][-1] == target(raw)["evidence"][-1]
    assert inventory(project) == before


@pytest.mark.parametrize("format", ["json", "text", "github"])
def test_public_report_matches_complete_native_result_and_calls_engine_once(
    project: Path, format: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle(
        project,
        observations=[
            {"value": "public-observed-value", "source": {"type": "cli", "key": "--alpha"}}
        ],
    )
    args = arguments(project, format)
    native = runtime.invoke_cli(args, project)
    commands = importlib.import_module("reprollm.cli.audit")
    engine = importlib.import_module("reprollm.core.engine")
    original = commands.run_audit
    engine_function = engine.run_audit
    calls = []

    def count(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(commands, "run_audit", count)
    before = inventory(project)
    actual, diagnostics = invoke(project, args)
    assert actual.exit_code == native.exit_code and actual.stderr == native.stderr
    assert len(calls) == 1 and engine.run_audit is engine_function
    if format == "json":
        assert normalized(json.loads(actual.stdout)) == normalized(json.loads(native.stdout))
    else:
        assert actual.stdout == native.stdout
    assert not diagnostics and inventory(project) == before


@pytest.mark.parametrize(
    "field,declared,rule_id",
    [
        ("generation.temperature", 0, "consistency.generation_params"),
        ("models.primary.id", "public/model", "consistency.model_identity"),
        ("custom.alpha", "declared", "consistency.custom_fields"),
    ],
)
def test_all_native_binding_finding_families_keep_original_decisions(
    project: Path, field: str, declared: Any, rule_id: str
) -> None:
    bundle(project, field=field, declared=declared)
    native = runtime.invoke_cli(arguments(project, fail_on="warning"), project)
    raw = json.loads(native.stdout)
    assert target(raw, rule_id)["status"] == "fail" and CANARY in native.stdout
    actual, _ = invoke(project, arguments(project, fail_on="warning"))
    safe = json.loads(actual.stdout)
    assert actual.exit_code == native.exit_code and conclusions(safe) == conclusions(raw)
    assert CANARY not in actual.stdout and MARKER in json.dumps(target(safe, rule_id))


def test_private_and_public_observations_with_equal_bytes_are_not_globally_replaced(
    project: Path,
) -> None:
    bundle(
        project,
        declared=CANARY,
        observations=[
            {"value": CANARY, "source": {"type": "cli", "key": "--api-key"}},
            {"value": CANARY, "source": {"type": "cli", "key": "--alpha"}},
            {"value": "different-public-value", "source": {"type": "cli", "key": "--alpha"}},
        ],
    )
    native = runtime.invoke_cli(arguments(project), project)
    actual, _ = invoke(project, arguments(project))
    safe, raw = json.loads(actual.stdout), json.loads(native.stdout)
    assert conclusions(safe) == conclusions(raw)
    finding = target(safe)
    assert finding["evidence"][0]["value"] == CANARY
    observations = [item for item in finding["evidence"] if item["kind"] == "run"]
    assert any(item["value"] == MARKER and "--api-key" in item["note"] for item in observations)
    assert any(item["value"] == CANARY and "--alpha" in item["note"] for item in observations)
    assert f'manifest "{CANARY}"' in finding["message"]


@pytest.mark.parametrize("severity", ["INFO", "WARNING", "CRITICAL"])
@pytest.mark.parametrize("ignored", [False, True])
def test_suppression_and_project_severity_remain_original_engine_decisions(
    project: Path, severity: str, ignored: bool
) -> None:
    bundle(project, severity=severity)
    if ignored:
        (project / ".reprollm/config.yaml").write_text(
            "schema_version: 1\naudit:\n  ignore:\n"
            "    - rule: consistency.custom_fields\n      reason: Public reviewed ignore\n"
        )
    native = runtime.invoke_cli(arguments(project, fail_on="warning"), project)
    actual, _ = invoke(project, arguments(project, fail_on="warning"))
    raw, safe = json.loads(native.stdout), json.loads(actual.stdout)
    assert conclusions(safe) == conclusions(raw) and actual.exit_code == native.exit_code
    assert target(safe)["status"] == ("suppressed" if ignored else "fail")
    assert target(safe)["evidence"][-1] == target(raw)["evidence"][-1]
    assert CANARY not in actual.stdout


def test_native_output_file_is_private_before_publication(project: Path) -> None:
    bundle(project)
    raw = json.loads(runtime.invoke_cli(arguments(project), project).stdout)
    output = project / "report.json"
    actual, _ = invoke(project, [*arguments(project), "--output", str(output)])
    assert actual.exit_code == 0 and output.is_file()
    emitted = output.read_text()
    assert CANARY not in emitted and MARKER in emitted
    assert conclusions(json.loads(emitted)) == conclusions(raw)


def test_native_formatter_binding_is_restored_after_projection_failure(project: Path) -> None:
    bundle(project)
    consistency = importlib.import_module("reprollm.rules.consistency")
    original = consistency._binding_finding

    def broken(value: Any, notes: list[dict[str, Any]]) -> Any:
        raise ValueError("private audit projection unavailable")

    result, _ = display.invoke_private_audit(
        arguments(project), project, invoke_cli=runtime.invoke_cli, sanitize=broken
    )
    assert result.exit_code == 3 and CANARY not in result.stdout + result.stderr
    assert consistency._binding_finding is original
    native = runtime.invoke_cli(arguments(project), project)
    assert native.exit_code == 0 and CANARY in native.stdout


def test_context_manager_restores_binding_when_invocation_itself_raises(project: Path) -> None:
    consistency = importlib.import_module("reprollm.rules.consistency")
    original = consistency._binding_finding

    def broken(argv: list[str], root: Path) -> runtime.CliResult:
        raise OSError("synthetic private display failure")

    with pytest.raises(OSError, match="synthetic private display failure"):
        display.invoke_private_audit(
            [], project, invoke_cli=broken, sanitize=lambda value, notes: value
        )
    assert consistency._binding_finding is original


def test_native_rule_check_runs_once_and_original_ctx_objects_are_never_modified(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.rules.consistency import CustomFieldsRule

    bundle(
        project,
        observations=[
            {"value": CANARY, "source": {"type": "cli", "key": "--api-key"}},
            {"value": {"safe": [0, False, "public"]}, "source": {"type": "cli", "key": "--alpha"}},
        ],
    )
    native_check = CustomFieldsRule.check
    calls = []

    def check(self: Any, ctx: Any) -> Any:
        calls.append(ctx)
        original_state = ctx.state
        original_manifest = ctx.manifest
        original_run = ctx.latest_run
        before = {
            "state": original_state.model_dump_json(),
            "manifest": original_manifest.model_dump_json(),
            "run": original_run.model_dump_json(),
            "rules": ctx.project_rules.model_dump_json(),
        }
        findings = native_check(self, ctx)
        assert ctx.state is original_state and ctx.manifest is original_manifest
        assert ctx.latest_run is original_run
        after = {
            "state": ctx.state.model_dump_json(),
            "manifest": ctx.manifest.model_dump_json(),
            "run": ctx.latest_run.model_dump_json(),
            "rules": ctx.project_rules.model_dump_json(),
        }
        assert after == before
        return findings

    monkeypatch.setattr(CustomFieldsRule, "check", check)
    before = inventory(project)
    actual, _ = invoke(project, arguments(project))
    assert actual.exit_code == 0 and len(calls) == 1
    assert CANARY not in actual.stdout and inventory(project) == before


@pytest.mark.parametrize(
    "source",
    [
        {"type": "config", "key": "namespace:api_key", "path": "configs/colon:name.yaml"},
        {"type": "cli", "key": "--alpha"},
    ],
)
def test_source_key_and_path_keep_their_typed_identity(
    project: Path, source: dict[str, Any]
) -> None:
    bundle(project, observations=[{"value": CANARY, "source": source}])
    native = runtime.invoke_cli(arguments(project), project)
    actual, _ = invoke(project, arguments(project))
    if source["key"] == "--alpha":
        assert normalized(json.loads(actual.stdout)) == normalized(json.loads(native.stdout))
    else:
        assert CANARY not in actual.stdout and MARKER in actual.stdout
        assert "configs/colon:name.yaml" in actual.stdout


def test_unknown_latest_source_context_fails_closed_without_raw_report(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import skill_diff_display

    bundle(project)

    def missing(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("private diff source context is unavailable")

    monkeypatch.setattr(skill_diff_display, "project_leaf_value", missing)
    result, _ = invoke(project, arguments(project))
    assert result.exit_code == 3 and CANARY not in result.stdout + result.stderr


def test_public_lock_and_manifest_remain_distinct_from_private_observation(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import datetime, timezone

    from reprollm.core.hashing import sha256_file
    from reprollm.rules.consistency import ModelIdentityRule
    from reprollm.schemas.lock import Lock, ModelLock, Provenance, ResolutionMode

    bundle(project, field="models.primary.id", declared="public/model")
    lock = Lock(
        reprollm_version="0.6.1",
        generated_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
        manifest_sha256=sha256_file(project / "reprollm.yaml"),
        resolution=ResolutionMode(mode="offline"),
        models={
            "primary": ModelLock(
                provider="huggingface",
                id="public/locked-model",
                pinnability="exact",
                revision=Provenance(value="a" * 40, source="declared", confidence="exact"),
            )
        },
    )
    (project / "reprollm.lock").write_text(yaml.safe_dump(lock.model_dump(mode="json")))
    native = runtime.invoke_cli(arguments(project), project)
    raw = json.loads(native.stdout)
    original_check = ModelIdentityRule.check
    checked = []

    def check(self: Any, ctx: Any) -> Any:
        checked.append(ctx)
        state, locked = ctx.state, ctx.lock
        source_json = [
            state.model_dump_json(),
            locked.model_dump_json(),
            ctx.manifest.model_dump_json(),
            ctx.latest_run.model_dump_json(),
        ]
        result = original_check(self, ctx)
        assert ctx.state is state and ctx.lock is locked
        assert source_json == [
            ctx.state.model_dump_json(),
            ctx.lock.model_dump_json(),
            ctx.manifest.model_dump_json(),
            ctx.latest_run.model_dump_json(),
        ]
        return result

    monkeypatch.setattr(ModelIdentityRule, "check", check)
    before = inventory(project)
    result, _ = invoke(project, arguments(project))
    safe = json.loads(result.stdout)
    assert conclusions(safe) == conclusions(raw) and len(checked) == 1
    finding = target(safe, "consistency.model_identity")
    assert finding["evidence"][0]["value"] == "public/model"
    assert finding["evidence"][1]["value"] == "public/locked-model"
    assert finding["evidence"][2]["value"] == MARKER
    assert 'manifest "public/model"' in finding["message"]
    assert 'lock "public/locked-model"' in finding["message"]
    assert inventory(project) == before


def test_profile_override_is_applied_after_private_formatter_returns(project: Path) -> None:
    bundle(project, field="generation.temperature", declared=0)
    profiles = project / ".reprollm/profiles"
    profiles.mkdir()
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Public synthetic narrow audit policy",
                "rules": ["consistency.generation_params"],
                "severity_overrides": {"consistency.generation_params": "INFO"},
            }
        )
    )
    native = runtime.invoke_cli(arguments(project, fail_on="warning"), project)
    actual, _ = invoke(project, arguments(project, fail_on="warning"))
    raw, safe = json.loads(native.stdout), json.loads(actual.stdout)
    assert actual.exit_code == native.exit_code == 0
    assert conclusions(safe) == conclusions(raw)
    finding = target(safe, "consistency.generation_params")
    assert finding["status"] == "fail" and finding["severity"] == "INFO"
    assert finding["severity_origin"] == "profile:core"
    assert CANARY not in actual.stdout


def test_no_new_runs_are_read_after_native_context_was_already_captured(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.rules.consistency import CustomFieldsRule

    bundle(project)
    original_check = CustomFieldsRule.check
    record = project / ".reprollm/runs" / RUN_ID / "run.json"
    original_data = json.loads(record.read_text())
    alternate = copy.deepcopy(original_data)
    alternate["bindings_observed"]["custom.alpha"][0]["source"]["key"] = "--alpha"

    def change_file_after_capture(self: Any, ctx: Any) -> Any:
        record.write_text(json.dumps(alternate) + "\n")
        # The native engine has already captured the actual typed context.
        assert ctx.latest_run.bindings_observed["custom.alpha"][0].source.key == "--api-key"
        return original_check(self, ctx)

    monkeypatch.setattr(CustomFieldsRule, "check", change_file_after_capture)
    result, _ = invoke(project, arguments(project))
    assert result.exit_code == 0 and CANARY not in result.stdout
    assert json.loads(record.read_text()) == alternate


def test_private_reports_context_can_wrap_another_native_audit_caller(project: Path) -> None:
    from reprollm.core.engine import run_audit
    from reprollm.reporters.json_ import audit_report_to_json

    bundle(project)
    with display.private_binding_reports(
        lambda value, notes: runtime._sanitize(
            value, project, action="runs.show", diagnostics=notes
        )
    ) as diagnostics:
        report = run_audit(project, level=2)
    assert CANARY not in audit_report_to_json(report) and diagnostics
    assert target(report.model_dump(mode="json"))["status"] == "fail"
