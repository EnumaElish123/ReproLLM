"""``exec.*`` rules: execution declarations (spec §12.3)."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import Rule, register_rule
from reprollm.schemas.finding import Evidence, Finding, Severity


def _has_manifest(ctx: AuditContext) -> bool:
    return ctx.manifest is not None


@register_rule
class CommandDeclaredRule(Rule):
    id = "exec.command_declared"
    category = "exec"
    default_severity = Severity.WARNING
    min_level = 1
    description = "The command that reproduces the experiment is declared."
    fix_hint = (
        "Set execution.command in reprollm.yaml, e.g. "
        "`execution: {command: 'python eval.py --config configs/eval.yaml'}`."
    )

    def applies(self, ctx: AuditContext) -> bool:
        return _has_manifest(ctx)

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "no manifest (Level 0)" if not _has_manifest(ctx) else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        execution = ctx.manifest.execution
        if execution is not None and execution.command is not None:
            return []
        return [
            self.finding(
                ctx,
                message="execution.command is missing; the experiment command is not recorded",
                evidence=[Evidence(kind="field", field="execution.command", note="absent")],
            )
        ]


@register_rule
class SeedDeclaredRule(Rule):
    id = "exec.seed_declared"
    category = "exec"
    default_severity = Severity.WARNING
    min_level = 1
    description = "A random seed is declared somewhere (execution/generation/training)."
    fix_hint = "Set execution.seed (or generation.seed / training.seed) in reprollm.yaml."

    _FIELDS = ("execution.seed", "generation.seed", "training.seed")

    def applies(self, ctx: AuditContext) -> bool:
        return _has_manifest(ctx)

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "no manifest (Level 0)" if not _has_manifest(ctx) else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        manifest = ctx.manifest
        present = [
            field
            for field, value in (
                ("execution.seed", manifest.execution.seed if manifest.execution else None),
                ("generation.seed", manifest.generation.seed if manifest.generation else None),
                ("training.seed", manifest.training.seed if manifest.training else None),
            )
            if value is not None
        ]
        if present:
            return []
        return [
            self.finding(
                ctx,
                message="no seed is declared (checked " + ", ".join(self._FIELDS) + ")",
                evidence=[
                    Evidence(kind="field", field=field, note="absent") for field in self._FIELDS
                ],
            )
        ]


@register_rule
class RunRecordedRule(Rule):
    id = "exec.run_recorded"
    category = "exec"
    default_severity = Severity.INFO
    min_level = 1
    description = "At least one run record captures what actually executed."
    fix_hint = "Wrap your command with `reprollm run -- <command>` to record runtime truth."

    def applies(self, ctx: AuditContext) -> bool:
        return _has_manifest(ctx)

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "no manifest (Level 0)" if not _has_manifest(ctx) else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        if ctx.runs:
            return []
        return [
            self.finding(
                ctx,
                message="no run records found under .reprollm/runs",
                evidence=[Evidence(kind="run", path=".reprollm/runs", note="no run.json found")],
            )
        ]


@register_rule
class ProfileDetectionMismatchRule(Rule):
    id = "exec.profile_detection_mismatch"
    category = "exec"
    default_severity = Severity.INFO
    min_level = 1
    description = "Declared profiles and detected signals agree."
    fix_hint = (
        "Adjust experiment.profiles in reprollm.yaml to match what the repository "
        "actually contains (see the detection evidence)."
    )

    def applies(self, ctx: AuditContext) -> bool:
        return _has_manifest(ctx)

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "no manifest (Level 0)" if not _has_manifest(ctx) else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        declared = ctx.declared_profiles
        detected = {entry.profile: entry for entry in ctx.detection.profiles}
        findings: list[Finding] = []

        for profile in sorted(declared):
            if profile == "core":
                continue  # implicit; never mismatched
            if profile not in detected:
                findings.append(
                    self.finding(
                        ctx,
                        message=(
                            f"declared profile {profile!r} has no detection evidence "
                            "in this repository"
                        ),
                        evidence=[
                            Evidence(
                                kind="field",
                                field="experiment.profiles",
                                note=f"{profile} declared, nothing detected",
                            )
                        ],
                    )
                )

        for name, entry in sorted(detected.items()):
            if entry.confidence != "high" or not entry.shipped:
                continue  # only high-confidence, shippable profiles are expected to be declared
            if name in declared:
                continue
            findings.append(
                self.finding(
                    ctx,
                    message=(
                        f"detected profile {name!r} (high confidence) is not declared "
                        "in experiment.profiles"
                    ),
                    evidence=[
                        Evidence(
                            kind="detection",
                            path=item.path or None,
                            line=item.line,
                            note=item.note,
                        )
                        for item in entry.evidence[:3]
                    ],
                )
            )
        return findings
