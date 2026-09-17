"""Cross-document consistency rules (spec §12.12)."""

from __future__ import annotations

import re
from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.core.hashing import sha256_file
from reprollm.core.registry import Rule, register_rule
from reprollm.rules._stubs import LevelTwoStubRule
from reprollm.schemas.finding import Evidence, Finding, Severity

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


@register_rule
class LockFreshRule(Rule):
    id = "consistency.lock_fresh"
    category = "consistency"
    default_severity = Severity.WARNING
    min_level = 2
    description = "The lock matches the manifest and accepted project rules."
    fix_hint = "Run `reprollm lock` to refresh reprollm.lock after declaration changes."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.lock is not None

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "reprollm.lock is absent"

    def check(self, ctx: AuditContext) -> list[Finding]:
        lock = ctx.lock
        if lock is None:  # pragma: no cover - guarded by applies
            return []
        findings: list[Finding] = []
        manifest = ctx.root / "reprollm.yaml"
        current_manifest = sha256_file(manifest) if manifest.is_file() else None
        if lock.manifest_sha256 != current_manifest:
            findings.append(
                self.finding(
                    ctx,
                    message="reprollm.yaml changed after reprollm.lock was generated",
                    evidence=[
                        Evidence(
                            kind="lock",
                            path="reprollm.lock",
                            field="manifest_sha256",
                            value=current_manifest,
                            expected=lock.manifest_sha256,
                        )
                    ],
                )
            )

        project_rules = ctx.root / ".reprollm/project-rules.yaml"
        current_rules = sha256_file(project_rules) if project_rules.is_file() else None
        if lock.project_rules_sha256 != current_rules:
            findings.append(
                self.finding(
                    ctx,
                    message=(
                        ".reprollm/project-rules.yaml changed after reprollm.lock was generated"
                    ),
                    evidence=[
                        Evidence(
                            kind="lock",
                            path="reprollm.lock",
                            field="project_rules_sha256",
                            value=current_rules,
                            expected=lock.project_rules_sha256,
                        )
                    ],
                )
            )
        return findings


@register_rule
class FileHashesRule(Rule):
    id = "consistency.file_hashes"
    category = "consistency"
    default_severity = Severity.CRITICAL
    min_level = 2
    description = "Declared file hashes agree between the lock, working tree, and latest run."
    fix_hint = "Reconcile reprollm.lock prompts/files hashes with the intended files and rerun."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.lock is not None

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "reprollm.lock is absent"

    def check(self, ctx: AuditContext) -> list[Finding]:
        lock = ctx.lock
        if lock is None:  # pragma: no cover - guarded by applies
            return []
        entries: dict[str, tuple[str, str]] = {}
        for role, prompt in sorted(lock.prompts.items()):
            if prompt.path is not None and prompt.sha256 is not None:
                entries.setdefault(
                    prompt.path,
                    (prompt.sha256, f"prompts.{role}.path"),
                )
        for index, entry in enumerate(lock.files):
            entries.setdefault(entry.path, (entry.sha256, f"files[{index}].path"))

        findings: list[Finding] = []
        for relative, (locked_hash, field) in sorted(entries.items()):
            path = _safe_working_tree_file(ctx.root, relative)
            if path is None:
                findings.append(_invalid_path_finding(self, ctx, field, locked_hash))
                continue
            if not path.is_file():
                findings.append(
                    self.finding(
                        ctx,
                        message=f"{relative} is missing from the working tree",
                        evidence=[
                            Evidence(
                                kind="file",
                                path=relative,
                                value=None,
                                expected=locked_hash,
                                note="missing",
                            )
                        ],
                    )
                )
                continue
            try:
                current_hash = sha256_file(path)
            except OSError as exc:
                findings.append(
                    self.finding(
                        ctx,
                        message=f"{relative} cannot be read from the working tree",
                        evidence=[
                            Evidence(
                                kind="file",
                                path=relative,
                                value=None,
                                expected=locked_hash,
                                note=exc.strerror or type(exc).__name__,
                            )
                        ],
                    )
                )
                continue
            if current_hash != locked_hash:
                findings.append(
                    self.finding(
                        ctx,
                        message=f"{relative} content differs from reprollm.lock",
                        evidence=[
                            Evidence(
                                kind="file",
                                path=relative,
                                value=current_hash,
                                expected=locked_hash,
                                note="working tree hash differs",
                            )
                        ],
                    )
                )
        return findings


def _safe_working_tree_file(root: Path, relative: str) -> Path | None:
    if (
        not relative
        or relative.startswith(("/", "\\"))
        or "\\" in relative
        or _DRIVE_RE.match(relative)
        or ".." in relative.split("/")
    ):
        return None
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved


def _invalid_path_finding(
    rule: FileHashesRule,
    ctx: AuditContext,
    field: str,
    locked_hash: str,
) -> Finding:
    return rule.finding(
        ctx,
        message=f"{field} contains an invalid path in reprollm.lock",
        evidence=[
            Evidence(
                kind="lock",
                field=field,
                expected=locked_hash,
                note="path must stay inside the repository",
            )
        ],
    )


@register_rule
class GenerationParamsRule(LevelTwoStubRule):
    id = "consistency.generation_params"
    category = "consistency"
    default_severity = Severity.CRITICAL
    description = "Observed generation parameters agree with their manifest declarations."
    fix_hint = "Reconcile generation.* in reprollm.yaml with the declared runtime bindings."


@register_rule
class ModelIdentityRule(LevelTwoStubRule):
    id = "consistency.model_identity"
    category = "consistency"
    default_severity = Severity.CRITICAL
    description = "Observed model identities agree with the manifest and lock."
    fix_hint = "Reconcile models.<role>.id and revision in reprollm.yaml and reprollm.lock."


@register_rule
class EnvVsLockRule(LevelTwoStubRule):
    id = "consistency.env_vs_lock"
    category = "consistency"
    default_severity = Severity.WARNING
    description = "Runtime LLM-critical package versions agree with the lock."
    fix_hint = "Use the environment.packages versions recorded in reprollm.lock and rerun."


@register_rule
class CustomFieldsRule(LevelTwoStubRule):
    id = "consistency.custom_fields"
    category = "consistency"
    severity_from_project_rule = True
    # Type sentinel for this non-executable stub; actual failures take their
    # severity from the matching project rule (spec §12.12), never this value.
    default_severity = Severity.INFO
    description = "Observed custom values agree with the manifest and accepted project rules."
    fix_hint = "Reconcile custom.* in reprollm.yaml with bindings in .reprollm/project-rules.yaml."
