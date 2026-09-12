"""Small in-memory manifests for Level 1 rule acceptance tests."""

from pathlib import Path
from typing import Any

from reprollm.core.context import AuditContext
from reprollm.schemas.finding import DetectionHints, DetectionResult, Finding, FindingStatus
from reprollm.schemas.manifest import Manifest


def context(root: Path, *, hints: DetectionHints | None = None, **sections: Any) -> AuditContext:
    manifest = Manifest.model_validate(
        {"project": {"name": "acceptance"}, "experiment": {"profiles": []}, **sections}
    )
    ctx = AuditContext(root, level=1, manifest=manifest)
    ctx._detection = DetectionResult(hints=hints or DetectionHints())
    return ctx


def failures(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.status == FindingStatus.FAIL]
