"""M4 rule placeholders remain metadata-only during M3 (spec §12, M3-T06)."""

from pathlib import Path

import pytest

import reprollm.rules  # noqa: F401 — register rule classes
from reprollm.core.context import AuditContext
from reprollm.core.registry import all_rules, get_rule
from reprollm.schemas.finding import Severity

M4_RULES = {
    "model.revision_pinned": Severity.CRITICAL,
    "model.tokenizer_pinned": Severity.WARNING,
    "model.chat_template_hashed": Severity.WARNING,
    "dataset.revision_pinned": Severity.WARNING,
    "dataset.local_files_hashed": Severity.CRITICAL,
    "gen.backend_version_locked": Severity.WARNING,
    "prompt.hashed": Severity.WARNING,
    "judge.prompt_hashed": Severity.WARNING,
    "judge.pinnability_recorded": Severity.WARNING,
}

CONSISTENCY_STUB_RULES = {
    "consistency.generation_params": Severity.CRITICAL,
    "consistency.model_identity": Severity.CRITICAL,
    "consistency.env_vs_lock": Severity.WARNING,
}


@pytest.mark.parametrize("rule_id,severity", sorted((M4_RULES | CONSISTENCY_STUB_RULES).items()))
def test_l2_stub_metadata_and_empty_check(rule_id: str, severity: Severity, tmp_path: Path) -> None:
    rule_type = get_rule(rule_id)
    assert rule_type is not None, f"unregistered M4 placeholder: {rule_id}"
    assert rule_type.category == rule_id.split(".", 1)[0]
    assert rule_type.min_level == 2
    assert getattr(rule_type, "stub", False) is True
    assert rule_type.default_severity == severity
    assert rule_type.description.strip()
    assert any(path in rule_type.fix_hint for path in ("reprollm.yaml", "reprollm.lock"))
    assert rule_type().check(AuditContext(tmp_path, level=2)) == []


def test_level_zero_and_one_rules_are_not_stubs() -> None:
    assert all(
        not getattr(rule_type, "stub", False)
        for rule_type in all_rules()
        if rule_type.min_level < 2
    )


@pytest.mark.parametrize(
    ("rule_id", "severity"),
    [
        ("consistency.lock_fresh", Severity.WARNING),
        ("consistency.file_hashes", Severity.CRITICAL),
    ],
)
def test_m4_consistency_rules_are_implemented(rule_id: str, severity: Severity) -> None:
    rule_type = get_rule(rule_id)
    assert rule_type is not None
    assert rule_type.min_level == 2
    assert rule_type.stub is False
    assert rule_type.default_severity == severity


def test_custom_fields_stub_preserves_project_rule_severity(tmp_path: Path) -> None:
    rule_type = get_rule("consistency.custom_fields")
    assert rule_type is not None
    assert rule_type.category == "consistency"
    assert rule_type.min_level == 2
    assert getattr(rule_type, "stub", False) is True
    assert getattr(rule_type, "severity_from_project_rule", False) is True
    assert rule_type.description.strip()
    assert "project-rules.yaml" in rule_type.fix_hint
    assert rule_type().check(AuditContext(tmp_path, level=2)) == []
