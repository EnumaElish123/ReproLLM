"""M6-T05: current audit evidence and historical diff evidence stay distinct."""

from pathlib import Path

import pytest

from reprollm.core.context import AuditContext
from reprollm.rules.consistency import CustomFieldsRule, FileHashesRule, GenerationParamsRule
from reprollm.schemas.state import Leaf, State
from tests.unit.rules.test_runtime_consistency import (
    lock_record,
    manifest,
    observation,
    project_rules,
    run_record,
)


def test_three_sources_survive_projection_and_finding(tmp_path: Path) -> None:
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(generation={"temperature": 0.0}),
        runs=[
            run_record(
                bindings_observed={
                    "generation.temperature": [
                        observation(1.0),
                        observation(
                            0.7, kind="config", path="configs/eval.yaml", key="temperature"
                        ),
                    ]
                }
            )
        ],
    )
    assert ctx.state is not None
    leaf = ctx.state.flatten()["generation.temperature"]
    assert leaf.value == 1.0 and leaf.detail == "cli:--temperature"
    assert [(item.source, item.value) for item in leaf.alternatives] == [
        ("run", 0.7),
        ("manifest", 0.0),
    ]
    (finding,) = GenerationParamsRule().check(ctx)
    assert [item.value for item in finding.evidence] == [0.0, 1.0, 0.7]
    assert finding.evidence[-1].note == "config(configs/eval.yaml:temperature)"


def test_rules_use_state_even_when_raw_observations_are_absent(tmp_path: Path) -> None:
    ctx = AuditContext(tmp_path, level=2, manifest=manifest(), runs=[run_record()])
    ctx.state = State.from_flat(
        {
            "generation.temperature": Leaf(
                value=1.0,
                source="run",
                detail="cli:--temperature",
                confidence="observed",
                alternatives=[Leaf(value=0.0, source="manifest", confidence="declared")],
            )
        }
    )
    assert GenerationParamsRule().applies(ctx)
    assert len(GenerationParamsRule().check(ctx)) == 1


def test_audit_uses_current_documents_without_requiring_historical_snapshots(
    tmp_path: Path,
) -> None:
    run = run_record(
        manifest={"path": "reprollm.yaml", "sha256": "sha256:old", "snapshot": "missing.yaml"},
        lock={"path": "reprollm.lock", "sha256": "sha256:old", "snapshot": "missing.lock"},
        bindings_observed={"generation.temperature": [observation(0.0)]},
    )
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(generation={"temperature": 0.0}),
        lock=lock_record(),
        runs=[run],
    )
    assert GenerationParamsRule().check(ctx) == []
    assert ctx.state is not None
    assert len(ctx.state.flatten()["generation.temperature"].alternatives) == 1


def test_lower_levels_do_not_project_runtime_state(tmp_path: Path) -> None:
    assert AuditContext(tmp_path, level=1, runs=[run_record()]).state is None


def test_object_binding_preserves_structured_custom_value(tmp_path: Path) -> None:
    ctx = AuditContext(
        tmp_path,
        level=2,
        manifest=manifest(custom={"privacy": {"alpha": {"schedule": [0.1, 0.2]}}}),
        runs=[
            run_record(
                bindings_observed={
                    "custom.privacy.alpha": [observation({"schedule": [0.1, 0.3]}, key="--alpha")]
                }
            )
        ],
        project_rules=project_rules(),
    )
    (finding,) = CustomFieldsRule().check(ctx)
    assert finding.evidence[0].value == {"schedule": [0.1, 0.2]}
    assert finding.evidence[1].value == {"schedule": [0.1, 0.3]}


@pytest.mark.parametrize("path", ["", "../outside.txt", "/outside.txt", "C:\\outside.txt"])
def test_invalid_lock_file_remains_an_audit_finding(tmp_path: Path, path: str) -> None:
    ctx = AuditContext(
        tmp_path,
        level=2,
        lock=lock_record(files=[{"path": path, "sha256": "sha256:locked", "size_bytes": 1}]),
    )
    (finding,) = FileHashesRule().check(ctx)
    assert finding.message == "files[0].path contains an invalid path in reprollm.lock"
    assert finding.evidence[0].path is None
