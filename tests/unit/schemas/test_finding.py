"""Finding / Severity / AuditReport schema tests (spec §9, §10)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from reprollm.schemas.finding import (
    SEVERITY_RANK,
    AuditReport,
    DetectionResult,
    Evidence,
    Finding,
    FindingStatus,
    ProfilesSection,
    Severity,
)


def test_severity_ordering() -> None:
    assert (
        SEVERITY_RANK[Severity.CRITICAL]
        > SEVERITY_RANK[Severity.WARNING]
        > SEVERITY_RANK[Severity.INFO]
        > SEVERITY_RANK[Severity.PASS]
    )


def test_severity_serializes_as_plain_name() -> None:
    assert Severity.CRITICAL.value == "CRITICAL"
    assert Severity("WARNING") is Severity.WARNING


def test_finding_serialization_field_order_matches_spec() -> None:
    finding = Finding(
        rule_id="model.revision_pinned",
        category="model",
        severity=Severity.CRITICAL,
        status=FindingStatus.FAIL,
        level=2,
        message="models.primary has no resolved revision",
        evidence=[Evidence(kind="lock", field="models.primary.revision", note="unresolved")],
        fix_hint="Run `reprollm lock` with network access.",
    )
    assert list(finding.model_dump().keys()) == [
        "rule_id",
        "aliases",
        "category",
        "severity",
        "status",
        "level",
        "message",
        "evidence",
        "fix_hint",
        "profile_origin",
        "severity_origin",
        "suppressed_reason",
    ]


def test_finding_json_serialization() -> None:
    finding = Finding(
        rule_id="code.git_repo",
        category="code",
        severity=Severity.CRITICAL,
        status=FindingStatus.FAIL,
        level=0,
        message="not a git work tree",
        fix_hint="Run `git init`.",
    )
    data = finding.model_dump(mode="json")
    assert data["severity"] == "CRITICAL"
    assert data["status"] == "fail"


def test_finding_level_bounds() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="x.y",
            category="x",
            severity=Severity.INFO,
            status=FindingStatus.SKIPPED,
            level=3,
            message="m",
            fix_hint="f",
        )


def test_audit_report_summary_uses_pass_alias() -> None:
    report = AuditReport(
        reprollm_version="0.0.1.dev0",
        generated_at=datetime(2026, 9, 3, tzinfo=timezone.utc),
        target=".",
        level=1,
        profiles=ProfilesSection(declared=[], resolved=["core"]),
        documents={"manifest": None, "lock": None, "runs": 0},
        summary={"critical": 1, "warning": 2, "info": 3, "pass": 4, "suppressed": 0, "skipped": 0},
        findings=[],
    )
    data = report.model_dump(mode="json", by_alias=True)
    assert data["summary"]["pass"] == 4
    assert report.summary.pass_ == 4  # noqa: SLF001 — attribute check on our own model


def test_detection_result_structure() -> None:
    result = DetectionResult.model_validate(
        {
            "profiles": [
                {
                    "profile": "llm_judge",
                    "confidence": "medium",
                    "evidence": [
                        {"kind": "detection", "path": "README.md", "line": 12, "note": "keyword"}
                    ],
                }
            ],
            "hints": {
                "providers": ["openai"],
                "hf_ids": [{"value": "Qwen/Qwen3-32B", "path": "eval.py", "line": 5}],
                "trust_remote_code": False,
            },
        }
    )
    assert result.profiles[0].profile == "llm_judge"
    assert result.hints.providers == ["openai"]
    assert result.hints.hf_ids[0].value == "Qwen/Qwen3-32B"
    assert result.hints.adapter is False
