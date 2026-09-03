"""JSON reporter: exactly one JSON document on stdout (spec §1.2)."""

from __future__ import annotations

import json

from reprollm.schemas.finding import AuditReport


def audit_report_to_json(report: AuditReport) -> str:
    """Serialize an audit report deterministically (field order, 2-space indent)."""
    return json.dumps(report.model_dump(mode="json", by_alias=True), indent=2) + "\n"
