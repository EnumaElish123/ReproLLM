"""The deterministic audit engine (spec §11).

Same repository + documents ⇒ byte-identical report (modulo ``generated_at``).
No LLM, no network (D-04).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import reprollm.rules  # noqa: F401 — imports register the rule catalog
from reprollm import __version__
from reprollm.core.context import AuditContext
from reprollm.core.errors import InternalError, UserError
from reprollm.core.hashing import sha256_file
from reprollm.core.levels import count_runs, detect_level
from reprollm.core.paths import repo_paths
from reprollm.core.registry import Rule, get_rule
from reprollm.profiles import loader
from reprollm.schemas.config import Config
from reprollm.schemas.finding import (
    SEVERITY_RANK,
    AuditReport,
    DocumentsSection,
    Finding,
    FindingStatus,
    ProfilesSection,
    Severity,
    Summary,
)
from reprollm.schemas.manifest import Manifest


def _count(findings: list[Finding], status: FindingStatus, severity: Severity | None) -> int:
    return sum(
        1
        for finding in findings
        if finding.status == status and (severity is None or finding.severity == severity)
    )


#: Category display order (spec §0); drives deterministic finding order.
CATEGORY_ORDER: tuple[str, ...] = (
    "code",
    "env",
    "exec",
    "model",
    "dataset",
    "gen",
    "prompt",
    "eval",
    "judge",
    "train",
    "privacy",
    "consistency",
    "project",
)


def _category_rank(category: str) -> int:
    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:
        return len(CATEGORY_ORDER)


def _load_config(root: Path) -> Config | None:
    path = root / ".reprollm" / "config.yaml"
    if not path.is_file():
        return None
    from pydantic import ValidationError

    from reprollm.core.yaml_io import load_yaml

    try:
        return Config.model_validate(load_yaml(path))
    except ValidationError as exc:
        raise UserError(f"invalid config {path}:\n{exc}") from exc


def _load_manifest(root: Path) -> Manifest | None:
    path = root / "reprollm.yaml"
    if not path.is_file():
        return None
    from reprollm.core.yaml_io import load_manifest

    return load_manifest(path)


def _skipped_finding(rule: type[Rule], ctx: AuditContext, reason: str | None) -> Finding:
    return Finding(
        rule_id=rule.id,
        aliases=list(rule.aliases),
        category=rule.category,
        severity=Severity.INFO,
        status=FindingStatus.SKIPPED,
        level=ctx.level,
        message=reason or "not applicable",
        evidence=[],
        fix_hint=rule.fix_hint,
    )


def _pass_finding(rule: type[Rule], ctx: AuditContext) -> Finding:
    return Finding(
        rule_id=rule.id,
        aliases=list(rule.aliases),
        category=rule.category,
        severity=Severity.PASS,
        status=FindingStatus.PASS,
        level=ctx.level,
        message=rule.description,
        evidence=[],
        fix_hint=rule.fix_hint,
    )


def run_audit(
    root: Path,
    *,
    level: int | None = None,
    profile_names: list[str] | None = None,
    target: str = ".",
) -> AuditReport:
    """Execute spec §11 steps 1–8 for the repository at ``root``."""
    root = root.resolve()
    paths = repo_paths(root)

    config = _load_config(root)
    manifest = _load_manifest(root)

    detected = detect_level(paths)
    effective = detected if level is None else min(level, detected)

    if profile_names is None:
        declared = list(manifest.experiment.profiles) if manifest is not None else []
    else:
        declared = list(profile_names)
    resolved = loader.resolve(declared, root)

    ctx = AuditContext(
        root,
        level=effective,
        target=target,
        manifest=manifest,
        lock=None,  # lock loading arrives in M4
        runs=[],  # run record loading arrives in M5
        config=config,
    )

    findings: list[Finding] = []
    for rule_id in resolved.rules:
        rule_class = get_rule(rule_id)
        if rule_class is None:  # pragma: no cover - resolve() already validated
            raise InternalError(f"rule {rule_id!r} vanished from the registry")
        if rule_class.min_level > effective:
            continue  # selected but not executed at this level; emits nothing
        rule = rule_class()  # rules are stateless; instance carries no config
        if not rule.applies(ctx):
            reason = rule.skip_reason(ctx)
            findings.append(_skipped_finding(rule_class, ctx, reason))
            continue
        produced = rule.check(ctx)
        findings.extend(produced if produced else [_pass_finding(rule_class, ctx)])
    # Severity overrides and suppression wiring arrive in M3.

    findings.sort(key=lambda f: (-SEVERITY_RANK[f.severity], _category_rank(f.category), f.rule_id))

    summary = Summary(
        critical=_count(findings, FindingStatus.FAIL, Severity.CRITICAL),
        warning=_count(findings, FindingStatus.FAIL, Severity.WARNING),
        info=_count(findings, FindingStatus.FAIL, Severity.INFO),
        pass_=_count(findings, FindingStatus.PASS, None),
        suppressed=_count(findings, FindingStatus.SUPPRESSED, None),
        skipped=_count(findings, FindingStatus.SKIPPED, None),
    )

    documents = DocumentsSection(
        manifest=sha256_file(paths.manifest) if paths.manifest.is_file() else None,
        lock=sha256_file(paths.lock) if paths.lock.is_file() else None,
        runs=count_runs(paths),
    )

    # Deterministic detection runs at every level; at Level 0 it is the main
    # signal (§11 step 3), at Level 1+ it feeds exec.profile_detection_mismatch.
    detected_profiles = list(ctx.detection.profiles)

    return AuditReport(
        reprollm_version=__version__,
        generated_at=datetime.now(timezone.utc),
        target=target,
        level=effective,
        profiles=ProfilesSection(
            declared=declared,
            resolved=resolved.names,
            detected=detected_profiles,
        ),
        documents=documents,
        summary=summary,
        findings=findings,
    )
