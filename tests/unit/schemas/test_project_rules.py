"""Project rules schema tests (spec §7)."""

import pytest
from pydantic import ValidationError

from reprollm.schemas.project_rules import ProjectRule, ProjectRules


def valid_rule() -> dict:
    return {
        "id": "project.alpha",
        "field": "custom.privacy_method.alpha",
        "severity": "CRITICAL",
        "reason": "controls noise scale; results not comparable across values",
        "source": "manual",
        "accepted_at": "2026-09-03T12:00:00Z",
        "bindings": {"config": "configs/privacy.yaml:method.alpha"},
    }


def test_valid_rule_loads() -> None:
    r = ProjectRule.model_validate(valid_rule())
    assert r.id == "project.alpha"
    assert r.bindings is not None
    assert r.bindings.config == "configs/privacy.yaml:method.alpha"


def test_id_pattern() -> None:
    with pytest.raises(ValidationError):
        ProjectRule.model_validate({**valid_rule(), "id": "alpha"})
    with pytest.raises(ValidationError):
        ProjectRule.model_validate({**valid_rule(), "id": "model.alpha"})


def test_field_must_be_custom_or_valid_schema_path() -> None:
    with pytest.raises(ValidationError, match="unknown field"):
        ProjectRule.model_validate({**valid_rule(), "field": "generation.nope"})
    ok = ProjectRule.model_validate({**valid_rule(), "field": "generation.temperature"})
    assert ok.field == "generation.temperature"


def test_reason_mandatory_non_empty() -> None:
    with pytest.raises(ValidationError):
        ProjectRule.model_validate({**valid_rule(), "reason": ""})
    with pytest.raises(ValidationError):
        data = valid_rule()
        del data["reason"]
        ProjectRule.model_validate(data)


def test_discover_source_requires_candidate_id() -> None:
    with pytest.raises(ValidationError, match="candidate_id"):
        ProjectRule.model_validate({**valid_rule(), "source": "discover"})
    r = ProjectRule.model_validate(
        {**valid_rule(), "source": "discover", "candidate_id": "c-3f9a1b"}
    )
    assert r.candidate_id == "c-3f9a1b"


def test_severity_restricted_to_audit_levels() -> None:
    with pytest.raises(ValidationError):
        ProjectRule.model_validate({**valid_rule(), "severity": "PASS"})


def test_duplicate_ids_rejected() -> None:
    rule = valid_rule()
    with pytest.raises(ValidationError, match="duplicate"):
        ProjectRules.model_validate(
            {"schema_version": 1, "rules": [rule, rule], "ignored_candidates": []}
        )


def test_ignored_candidates_entries() -> None:
    doc = ProjectRules.model_validate(
        {
            "schema_version": 1,
            "rules": [],
            "ignored_candidates": [
                {"candidate_id": "c-abc123", "ignored_at": "2026-09-03T12:00:00Z"}
            ],
        }
    )
    assert doc.ignored_candidates[0].candidate_id == "c-abc123"
