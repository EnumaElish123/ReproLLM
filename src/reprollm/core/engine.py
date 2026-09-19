"""The deterministic audit engine (spec §11).

Same repository + documents ⇒ byte-identical report (modulo ``generated_at``).
No LLM, no network (D-04).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import reprollm.rules  # noqa: F401 — imports register the rule catalog
from reprollm import __version__
from reprollm.core.config import load_config
from reprollm.core.context import AuditContext
from reprollm.core.errors import InternalError, UserError
from reprollm.core.hashing import sha256_file
from reprollm.core.levels import detect_level
from reprollm.core.paths import repo_paths
from reprollm.core.project_rules import load_project_rules
from reprollm.core.registry import Rule, get_rule
from reprollm.profiles import loader
from reprollm.run.reader import list_runs
from reprollm.schemas.config import Config
from reprollm.schemas.finding import (
    SEVERITY_RANK,
    AuditReport,
    DocumentsSection,
    Evidence,
    Finding,
    FindingStatus,
    ProfilesSection,
    Severity,
    Summary,
)
from reprollm.schemas.lock import Lock
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


def _load_manifest(root: Path) -> Manifest | None:
    path = root / "reprollm.yaml"
    if not path.is_file():
        return None
    from reprollm.core.yaml_io import load_manifest

    return load_manifest(path)


def _load_lock(root: Path) -> Lock | None:
    path = root / "reprollm.lock"
    if not path.is_file():
        return None
    from reprollm.core.yaml_io import load_lock

    return load_lock(path)


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


def _suppress(findings: list[Finding], config: Config) -> None:
    ignores: dict[str, str] = {}
    for entry in config.audit.ignore:
        rule = get_rule(entry.rule)
        ignores.setdefault(rule.id if rule is not None else entry.rule, entry.reason)
    for finding in findings:
        reason = ignores.get(finding.rule_id)
        if reason is None:
            continue
        finding.evidence.append(
            Evidence(
                kind="field",
                path=".reprollm/config.yaml",
                field="audit.ignore",
                note=f"suppressed: original severity {finding.severity.value}; reason: {reason}",
            )
        )
        finding.status = FindingStatus.SUPPRESSED
        finding.severity = Severity.INFO
        finding.suppressed_reason = reason


def run_audit(
    root: Path,
    *,
    level: int | None = None,
    profile_names: list[str] | None = None,
    target: str = ".",
    diagnostics: list[str] | None = None,
    config: Config | None = None,
) -> AuditReport:
    """Execute spec §11 steps 1–8 for the repository at ``root``.

    ``diagnostics``, when provided, receives the merged/deduplicated/sorted
    scan warnings (truncation, syntax errors, unreadable files) gathered while
    the rules ran (M2F-T07). They are a CLI-only channel and are never part of
    the persisted report.
    """
    root = root.resolve()
    paths = repo_paths(root)

    config = load_config(root) if config is None else config
    manifest = _load_manifest(root)
    lock = _load_lock(root)
    project_rules = load_project_rules(root)
    try:
        runs, run_warnings = list_runs(root)
    except UserError as exc:
        runs, run_warnings = [], [str(exc)]

    detected = detect_level(paths, run_count=len(runs))
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
        lock=lock,
        runs=runs,
        config=config,
        project_rules=project_rules,
    )
    ctx.declared_profiles = declared
    ctx.resolved_profiles = resolved.names

    findings: list[Finding] = []
    for rule_id in resolved.rules:
        rule_class = get_rule(rule_id)
        if rule_class is None:  # pragma: no cover - resolve() already validated
            raise InternalError(f"rule {rule_id!r} vanished from the registry")
        if rule_class.min_level > effective:
            continue  # selected but not executed at this level; emits nothing
        if rule_class.stub:
            finding = _skipped_finding(rule_class, ctx, "not implemented yet")
            finding.evidence.append(Evidence(kind="lock", note="not implemented yet"))
            findings.append(finding)
            continue
        rule = rule_class()  # rules are stateless; instance carries no config
        if not rule.applies(ctx):
            reason = rule.skip_reason(ctx)
            findings.append(_skipped_finding(rule_class, ctx, reason))
            continue
        produced = rule.check(ctx)
        findings.extend(produced if produced else [_pass_finding(rule_class, ctx)])
    for finding in findings:
        # PASS and SKIPPED describe execution outcomes, not failure severity.
        if finding.status != FindingStatus.FAIL or finding.severity_origin == "project_rule":
            continue
        override = resolved.severity_overrides.get(finding.rule_id)
        if override is not None:
            finding.severity = Severity(override)
            finding.severity_origin = f"profile:{resolved.severity_origins[finding.rule_id]}"
    _suppress(findings, config)

    if diagnostics is not None:
        # Touch every lazy scan the rules may not have reached, then merge.
        ctx.fs.files()
        _ = (ctx.pyscan, ctx.deps)
        diagnostics.extend(
            sorted(
                {
                    *ctx.fs.warnings,
                    *ctx.pyscan.warnings,
                    *ctx.deps.unparsed,
                    *(f"run: {warning}" for warning in run_warnings),
                }
            )
        )

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
        runs=len(runs),
    )

    # Deterministic detection runs at every level; at Level 0 it is the main
    # signal (§11 step 3), at Level 1+ it feeds exec.profile_detection_mismatch.
    detected_profiles = list(ctx.detection.profiles)

    return AuditReport(
        reprollm_version=__version__,
        # Spec §0: timestamps are second-precision UTC with the Z suffix (M2F-T01).
        generated_at=datetime.now(timezone.utc).replace(microsecond=0),
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
