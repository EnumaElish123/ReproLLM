"""The additive recovery schema does not change project-rules v1."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from reprollm.schemas.project_rules import ProjectRule
from reprollm.schemas.rule_archive import RuleArchive


def payload() -> dict:
    original = ProjectRule(
        id="project.alpha",
        field="custom.alpha",
        severity="WARNING",
        reason="Keep alpha.",
        source="manual",
        accepted_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    return {
        "schema_version": 1,
        "archive_id": "ra-" + "0" * 16,
        "archived_at": "2026-10-02T00:00:00Z",
        "reason": "Retired",
        "rule": original,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": 2},
        {"archive_id": "../elsewhere"},
        {"reason": " "},
        {"archived_at": "2026-10-02T00:00:00"},
        {"unexpected": True},
    ],
)
def test_invalid_archive_contract_is_rejected(changes: dict) -> None:
    with pytest.raises(ValidationError):
        RuleArchive.model_validate({**payload(), **changes})


def test_identity_depends_on_complete_original_and_reason() -> None:
    archive = RuleArchive.model_validate(payload())
    assert archive.content_id() == RuleArchive.model_validate(payload()).content_id()
    assert archive.content_id() != archive.model_copy(update={"reason": "Different"}).content_id()
    changed = archive.rule.model_copy(update={"severity": "CRITICAL"})
    assert archive.content_id() != archive.model_copy(update={"rule": changed}).content_id()
