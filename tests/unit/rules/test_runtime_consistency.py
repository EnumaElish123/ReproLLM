"""M5-T06 compares captured structured sources without choosing away conflicts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.hashing import sha256_file
from reprollm.rules.consistency import (
    CustomFieldsRule,
    EnvVsLockRule,
    FileHashesRule,
    GenerationParamsRule,
    ModelIdentityRule,
)
from reprollm.schemas.finding import Severity
from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.project_rules import ProjectRules
from reprollm.schemas.run_record import RunRecord

NOW = datetime(2026, 10, 5, 9, 30, tzinfo=timezone.utc)
RUN_ID = "20261005T093000Z-a1b2c3"


def run_record(**fields: Any) -> RunRecord:
    return RunRecord.model_validate(
        {
            "reprollm_version": "0.1.1",
            "run_id": RUN_ID,
            "status": "completed",
            "started_at": NOW,
            "command": {"argv": ["python", "eval.py"], "cwd": "."},
            **fields,
        }
    )


def lock_record(**fields: Any) -> Lock:
    return Lock.model_validate(
        {
            "reprollm_version": "0.1.1",
            "generated_at": NOW,
            "manifest_sha256": "sha256:manifest",
            "resolution": {"mode": "offline"},
            **fields,
        }
    )


def manifest(**fields: Any) -> Manifest:
    return Manifest.model_validate(
        {
            "project": {"name": "runtime-test"},
            "experiment": {"profiles": []},
            **fields,
        }
    )


def observation(
    value: Any, *, kind: str = "cli", key: str = "--temperature", path: str | None = None
) -> dict:
    return {"value": value, "source": {"type": kind, "key": key, "path": path}}


def test_generation_reports_one_conflict_with_all_sources(tmp_path: Path) -> None:
    run = run_record(
        bindings_observed={
            "generation.temperature": [
                observation("0"),
                observation("1.0"),
                observation(
                    0.0, kind="config", key="sampling.temperature", path="configs/eval.yaml"
                ),
            ]
        }
    )
    ctx = AuditContext(
        tmp_path, level=2, manifest=manifest(generation={"temperature": 0.0}), runs=[run]
    )
    rule = GenerationParamsRule()
    assert rule.applies(ctx)
    found = rule.check(ctx)
    assert len(found) == 1 and found[0].severity == Severity.CRITICAL
    assert "generation.temperature: manifest 0.0" in found[0].message
    assert "config(configs/eval.yaml:sampling.temperature) 0.0" in found[0].message
    assert "cli(--temperature)" in found[0].message
    assert [e.value for e in found[0].evidence] == [0.0, "0", "1.0", 0.0]
    assert all(e.path == f".reprollm/runs/{RUN_ID}/run.json" for e in found[0].evidence[1:])


def test_generation_matches_normalized_values_and_ignores_other_fields(tmp_path: Path) -> None:
    run = run_record(
        bindings_observed={
            "generation.temperature": [observation("0")],
            "generation.stop": [observation(["END"])],
            "models.primary.id": [observation("unrelated")],
        }
    )
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(generation={"temperature": 0.0, "stop": ["END"]}),
        runs=[run],
    )
    assert GenerationParamsRule().check(ctx) == []
    ctx.runs = [run_record()]
    assert not GenerationParamsRule().applies(ctx)


def test_observation_for_absent_generation_declaration_is_conflict(tmp_path: Path) -> None:
    run = run_record(bindings_observed={"generation.temperature": [observation(0.0)]})
    ctx = AuditContext(tmp_path, level=2, manifest=manifest(), runs=[run])
    found = GenerationParamsRule().check(ctx)
    assert len(found) == 1 and found[0].evidence[0].value is None


@pytest.mark.parametrize(
    "tree_changed,run_changed", [(False, False), (True, False), (False, True), (True, True)]
)
def test_file_conflicts_keep_lock_tree_and_run_evidence_once(
    tmp_path: Path,
    tree_changed: bool,
    run_changed: bool,
) -> None:
    path = tmp_path / "config.json"
    path.write_text("before")
    locked_hash = sha256_file(path)
    lock = lock_record(files=[{"path": "config.json", "sha256": locked_hash, "size_bytes": 6}])
    run_hash = "sha256:changed-in-run" if run_changed else locked_hash
    run = run_record(
        files=[{"path": "config.json", "sha256": run_hash, "size_bytes": 6, "origin": "argv"}]
    )
    if tree_changed:
        path.write_text("after")
    ctx = AuditContext(tmp_path, level=2, lock=lock, runs=[run])
    found = FileHashesRule().check(ctx)
    if not (tree_changed or run_changed):
        assert found == []
    else:
        assert len(found) == 1 and found[0].severity == Severity.CRITICAL
        by_kind = {e.kind.value: e.value for e in found[0].evidence}
        assert by_kind == {"lock": locked_hash, "file": sha256_file(path), "run": run_hash}


def test_missing_tree_file_retains_conflicting_run_evidence(tmp_path: Path) -> None:
    lock = lock_record(files=[{"path": "missing.txt", "sha256": "sha256:locked", "size_bytes": 1}])
    run = run_record(
        files=[{"path": "missing.txt", "sha256": "sha256:run", "size_bytes": 2, "origin": "argv"}]
    )
    found = FileHashesRule().check(AuditContext(tmp_path, level=2, lock=lock, runs=[run]))
    assert len(found) == 1
    assert {e.kind.value: e.value for e in found[0].evidence} == {
        "lock": "sha256:locked",
        "file": None,
        "run": "sha256:run",
    }


@pytest.mark.parametrize("observed,expected_count", [("org/model", 0), ("org/other", 1)])
def test_model_ids_compare_manifest_and_lock(
    tmp_path: Path, observed: str, expected_count: int
) -> None:
    lock = lock_record(
        models={
            "primary": {
                "provider": "huggingface",
                "id": "org/model",
                "pinnability": "exact",
                "revision": {"value": "abc", "source": "hf_api", "confidence": "exact"},
            }
        }
    )
    run = run_record(
        bindings_observed={"models.primary.id": [observation(observed, key="--model")]}
    )
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(models={"primary": {"id": "org/model"}}),
        lock=lock,
        runs=[run],
    )
    assert ModelIdentityRule().applies(ctx)
    found = ModelIdentityRule().check(ctx)
    assert len(found) == expected_count
    if found:
        assert found[0].severity == Severity.CRITICAL
        assert [e.kind.value for e in found[0].evidence] == ["field", "lock", "run"]


def test_model_revision_uses_resolved_lock_and_falls_back_to_declaration(tmp_path: Path) -> None:
    lock = lock_record(
        models={
            "primary": {
                "provider": "huggingface",
                "id": "org/model",
                "pinnability": "exact",
                "revision": {"value": "a" * 40, "source": "hf_api", "confidence": "exact"},
            }
        }
    )
    run = run_record(
        bindings_observed={"models.primary.revision": [observation("a" * 40, key="--revision")]}
    )
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(models={"primary": {"id": "org/model", "revision": "main"}}),
        lock=lock,
        runs=[run],
    )
    assert ModelIdentityRule().check(ctx) == []
    ctx.manifest.models["primary"].revision = "b" * 40
    assert len(ModelIdentityRule().check(ctx)) == 1
    ctx.manifest.models["primary"].revision = "main"
    ctx.lock = None
    assert len(ModelIdentityRule().check(ctx)) == 1
    ctx.manifest.models["primary"].revision = "a" * 40
    assert ModelIdentityRule().check(ctx) == []


def environment(packages: dict[str, str], *, runtime: bool) -> dict:
    base = {"python": "3.12.0", "platform": "linux", "packages": packages}
    if runtime:
        base.update(os="Linux", hostname_sha256="sha256:host", env={})
    else:
        base.update(gpu={"source": "unavailable"})
    return base


def test_environment_compares_critical_packages_and_presence(tmp_path: Path) -> None:
    lock = lock_record(
        environment=environment({"torch": "2.7.0", "numpy": "2.0.0", "pytest": "7"}, runtime=False)
    )
    run = run_record(
        environment=environment(
            {"torch": "2.8.0", "transformers": "4.57.0", "pytest": "8"}, runtime=True
        )
    )
    ctx = AuditContext(tmp_path, level=2, lock=lock, runs=[run])
    rule = EnvVsLockRule()
    assert rule.applies(ctx)
    found = rule.check(ctx)
    assert [(f.evidence[0].field, f.severity) for f in found] == [
        ("environment.packages.numpy", Severity.INFO),
        ("environment.packages.torch", Severity.WARNING),
        ("environment.packages.transformers", Severity.INFO),
    ]
    assert "only lock" in found[0].message and "only run" in found[2].message
    run.environment.packages = {"torch": "2.7.0", "numpy": "2.0.0"}
    assert rule.check(ctx) == []
    run.environment = None
    assert not rule.applies(ctx)


def project_rules(severity: str = "WARNING") -> ProjectRules:
    return ProjectRules.model_validate(
        {
            "rules": [
                {
                    "id": "project.alpha",
                    "field": "custom.privacy.alpha",
                    "severity": severity,
                    "reason": "noise scale",
                    "source": "manual",
                    "accepted_at": NOW,
                    "bindings": {"cli": "--alpha"},
                }
            ]
        }
    )


@pytest.mark.parametrize("severity", ["INFO", "WARNING", "CRITICAL"])
def test_custom_fields_keep_project_severity_and_normalize(tmp_path: Path, severity: str) -> None:
    run = run_record(
        bindings_observed={"custom.privacy.alpha": [observation("0.25", key="--alpha")]}
    )
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(custom={"privacy": {"alpha": 0.25}}),
        runs=[run],
        project_rules=project_rules(severity),
    )
    rule = CustomFieldsRule()
    assert rule.applies(ctx) and rule.check(ctx) == []
    run.bindings_observed["custom.privacy.alpha"][0].value = "0.5"
    found = rule.check(ctx)
    assert len(found) == 1 and found[0].severity.value == severity
    assert found[0].severity_origin == "project_rule"
    assert any("project.alpha" in (e.note or "") for e in found[0].evidence)
    ctx.project_rules = None
    assert not rule.applies(ctx)


def test_findings_redact_captured_values_without_changing_comparison(tmp_path: Path) -> None:
    secret = "hf_01234567890123456789"
    run = run_record(
        bindings_observed={"custom.privacy.alpha": [observation(secret, key="--alpha")]}
    )
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(custom={"privacy": {"alpha": "public"}}),
        runs=[run],
        project_rules=project_rules(),
    )
    found = CustomFieldsRule().check(ctx)
    assert len(found) == 1 and secret not in found[0].model_dump_json()
    assert "<REDACTED:huggingface>" in found[0].model_dump_json()
