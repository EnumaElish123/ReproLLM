"""Cross-document consistency rules (spec §12.12)."""

from __future__ import annotations

import getpass
import json
import re
import socket
from pathlib import Path
from typing import Any

from reprollm.core.bindings import values_equal
from reprollm.core.context import AuditContext
from reprollm.core.envinfo import LLM_CRITICAL_PACKAGES
from reprollm.core.hashing import sha256_file
from reprollm.core.registry import Rule, register_rule
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.finding import Evidence, Finding, Severity
from reprollm.schemas.project_rules import ProjectRule
from reprollm.schemas.run_record import Observation

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
        run = ctx.latest_run
        run_files = {} if run is None else {entry.path: entry.sha256 for entry in run.files}
        for relative, (locked_hash, field) in sorted(entries.items()):
            path = _safe_working_tree_file(ctx.root, relative)
            if path is None:
                findings.append(_invalid_path_finding(self, ctx, field, locked_hash))
                continue
            current_hash = None
            message = f"{relative} content differs from reprollm.lock"
            note = "working tree hash differs"
            if not path.is_file():
                message, note = f"{relative} is missing from the working tree", "missing"
            else:
                try:
                    current_hash = sha256_file(path)
                except OSError as exc:
                    message = f"{relative} cannot be read from the working tree"
                    note = exc.strerror or type(exc).__name__
            run_hash = run_files.get(relative)
            if current_hash == locked_hash and (run_hash is None or run_hash == locked_hash):
                continue
            evidence = [
                Evidence(
                    kind="file", path=relative, value=current_hash, expected=locked_hash, note=note
                )
            ]
            if relative in run_files:
                # One conflict per path, retaining agreeing sources as well as differing ones.
                message = f"{relative} hashes disagree between reprollm.lock, working tree and run"
                evidence[0].note = "working tree hash" if current_hash is not None else note
                evidence.insert(
                    0, Evidence(kind="lock", path="reprollm.lock", field=field, value=locked_hash)
                )
                evidence.append(
                    Evidence(
                        kind="run",
                        path=_run_path(ctx),
                        field="files",
                        value=run_hash,
                        expected=locked_hash,
                        note=relative,
                    )
                )
            findings.append(
                _safe_finding(ctx, self.finding(ctx, message=message, evidence=evidence))
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


def _run_path(ctx: AuditContext) -> str:
    assert ctx.latest_run is not None
    return f".reprollm/runs/{ctx.latest_run.run_id}/run.json"


def _manifest_value(ctx: AuditContext, field: str) -> Any:
    value: Any = ctx.manifest.model_dump() if ctx.manifest is not None else {}
    for part in field.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def _observations(ctx: AuditContext, pattern: str) -> dict[str, list[Observation]]:
    run = ctx.latest_run
    return (
        {}
        if run is None
        else {
            field: values
            for field, values in sorted(run.bindings_observed.items())
            if values and re.fullmatch(pattern, field)
        }
    )


def _safe_finding(ctx: AuditContext, finding: Finding) -> Finding:
    # Compare original values first; redaction must not turn distinct secrets into equality.
    privacy = RunPrivacy(ctx.root, hostname=socket.gethostname(), username=getpass.getuser())
    return Finding.model_validate(privacy.value(finding))


def _binding_finding(
    rule: Rule,
    ctx: AuditContext,
    field: str,
    observations: list[Observation],
    *,
    locked: Any = None,
    include_lock: bool = False,
) -> Finding:
    declared = _manifest_value(ctx, field)
    evidence = [Evidence(kind="field", path="reprollm.yaml", field=field, value=declared)]
    parts = [f"{field}: manifest {json.dumps(declared, ensure_ascii=False, sort_keys=True)}"]
    if include_lock:
        evidence.append(Evidence(kind="lock", path="reprollm.lock", field=field, value=locked))
        parts.append(f"lock {json.dumps(locked, ensure_ascii=False, sort_keys=True)}")
    for observation in observations:
        source = observation.source
        location = f"{source.path}:" if source.path is not None else ""
        label = f"{source.type}({location}{source.key})"
        parts.append(f"{label} {json.dumps(observation.value, ensure_ascii=False, sort_keys=True)}")
        evidence.append(
            Evidence(
                kind="run",
                path=_run_path(ctx),
                field=field,
                value=observation.value,
                note=label,
            )
        )
    return _safe_finding(ctx, rule.finding(ctx, message=" · ".join(parts), evidence=evidence))


@register_rule
class GenerationParamsRule(Rule):
    id = "consistency.generation_params"
    category = "consistency"
    default_severity = Severity.CRITICAL
    min_level = 2
    description = "Observed generation parameters agree with their manifest declarations."
    fix_hint = "Reconcile generation.* in reprollm.yaml with the declared runtime bindings."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None and bool(_observations(ctx, r"generation\..+"))

    def skip_reason(self, ctx: AuditContext) -> str:
        return "manifest and latest-run generation.* observations are required"

    def check(self, ctx: AuditContext) -> list[Finding]:
        return [
            _binding_finding(self, ctx, field, observations)
            for field, observations in _observations(ctx, r"generation\..+").items()
            if any(
                not values_equal(_manifest_value(ctx, field), item.value) for item in observations
            )
        ]


@register_rule
class ModelIdentityRule(Rule):
    id = "consistency.model_identity"
    category = "consistency"
    default_severity = Severity.CRITICAL
    min_level = 2
    description = "Observed model identities agree with the manifest and lock."
    fix_hint = "Reconcile models.<role>.id and revision in reprollm.yaml and reprollm.lock."

    def applies(self, ctx: AuditContext) -> bool:
        return (ctx.manifest is not None or ctx.lock is not None) and bool(
            _observations(ctx, r"models\.[^.]+\.(id|revision)")
        )

    def skip_reason(self, ctx: AuditContext) -> str:
        return "model declarations and latest-run models.*.id/revision observations are required"

    def check(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        for field, observations in _observations(ctx, r"models\.[^.]+\.(id|revision)").items():
            _, role, name = field.split(".")
            model = ctx.lock.models.get(role) if ctx.lock is not None else None
            locked = (model.id if name == "id" else model.revision.value) if model else None
            declared = _manifest_value(ctx, field)
            # A resolved revision is the exact identity of the manifest's mutable reference.
            expected = [locked] if name == "revision" and locked is not None else [declared]
            if (
                name == "revision"
                and isinstance(declared, str)
                and re.fullmatch(r"[a-fA-F0-9]{40}", declared)
            ):
                expected.append(declared)
            if name == "id" and model is not None:
                expected = ([declared] if ctx.manifest is not None else []) + [locked]
            if any(
                not values_equal(value, item.value) for value in expected for item in observations
            ):
                findings.append(
                    _binding_finding(
                        self,
                        ctx,
                        field,
                        observations,
                        locked=locked,
                        include_lock=model is not None,
                    )
                )
        return findings


@register_rule
class EnvVsLockRule(Rule):
    id = "consistency.env_vs_lock"
    category = "consistency"
    default_severity = Severity.WARNING
    min_level = 2
    description = "Runtime LLM-critical package versions agree with the lock."
    fix_hint = "Use the environment.packages versions recorded in reprollm.lock and rerun."

    def applies(self, ctx: AuditContext) -> bool:
        return (
            ctx.lock is not None
            and ctx.lock.environment is not None
            and ctx.latest_run is not None
            and ctx.latest_run.environment is not None
        )

    def skip_reason(self, ctx: AuditContext) -> str:
        return "lock and latest-run environment.packages are required"

    def check(self, ctx: AuditContext) -> list[Finding]:
        if not self.applies(ctx):
            return []
        assert ctx.lock and ctx.lock.environment and ctx.latest_run and ctx.latest_run.environment
        locked = ctx.lock.environment.packages
        observed = ctx.latest_run.environment.packages
        findings = []
        for name in sorted(set(LLM_CRITICAL_PACKAGES) & (locked.keys() | observed.keys())):
            before, after = locked.get(name), observed.get(name)
            if before == after:
                continue
            field = f"environment.packages.{name}"
            presence = "only run" if before is None else "only lock" if after is None else None
            findings.append(
                _safe_finding(
                    ctx,
                    self.finding(
                        ctx,
                        message=f"{field}: {presence or 'run version differs from lock'}",
                        severity=Severity.INFO if presence else Severity.WARNING,
                        evidence=[
                            Evidence(kind="lock", path="reprollm.lock", field=field, value=before),
                            Evidence(kind="run", path=_run_path(ctx), field=field, value=after),
                        ],
                    ),
                )
            )
        return findings


def _custom_rules(ctx: AuditContext) -> list[ProjectRule]:
    if ctx.project_rules is None or ctx.manifest is None or ctx.latest_run is None:
        return []
    return sorted(
        (
            rule
            for rule in ctx.project_rules.rules
            if rule.field.startswith("custom.")
            and rule.bindings is not None
            and any(rule.bindings.model_dump().values())
            and ctx.latest_run.bindings_observed.get(rule.field)
        ),
        key=lambda rule: rule.id,
    )


@register_rule
class CustomFieldsRule(Rule):
    id = "consistency.custom_fields"
    category = "consistency"
    severity_from_project_rule = True
    min_level = 2
    # Failures take their severity from the accepted project rule (§12.12).
    default_severity = Severity.INFO
    description = "Observed custom values agree with the manifest and accepted project rules."
    fix_hint = "Reconcile custom.* in reprollm.yaml with bindings in .reprollm/project-rules.yaml."

    def applies(self, ctx: AuditContext) -> bool:
        return bool(_custom_rules(ctx))

    def skip_reason(self, ctx: AuditContext) -> str:
        return "accepted custom.* bindings and latest-run observations are required"

    def check(self, ctx: AuditContext) -> list[Finding]:
        findings = []
        for project_rule in _custom_rules(ctx):
            assert ctx.latest_run is not None
            field = project_rule.field
            observations = ctx.latest_run.bindings_observed[field]
            if all(values_equal(_manifest_value(ctx, field), item.value) for item in observations):
                continue
            finding = _binding_finding(self, ctx, field, observations)
            finding.severity = Severity(project_rule.severity)
            finding.severity_origin = "project_rule"
            finding.evidence.append(
                Evidence(
                    kind="field",
                    path=".reprollm/project-rules.yaml",
                    field=field,
                    note=f"{project_rule.id}: severity {project_rule.severity}",
                )
            )
            findings.append(finding)
        return findings
