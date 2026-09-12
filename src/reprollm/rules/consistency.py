"""Cross-document consistency placeholders (spec §12.12, M3-T06)."""

from __future__ import annotations

from reprollm.core.registry import register_rule
from reprollm.rules._stubs import LevelTwoStubRule
from reprollm.schemas.finding import Severity


@register_rule
class LockFreshRule(LevelTwoStubRule):
    id = "consistency.lock_fresh"
    category = "consistency"
    default_severity = Severity.WARNING
    description = "The lock matches the manifest and accepted project rules."
    fix_hint = "Run `reprollm lock` to refresh reprollm.lock after declaration changes."


@register_rule
class FileHashesRule(LevelTwoStubRule):
    id = "consistency.file_hashes"
    category = "consistency"
    default_severity = Severity.CRITICAL
    description = "Declared file hashes agree between the lock, working tree, and latest run."
    fix_hint = "Reconcile reprollm.lock prompts/files hashes with the intended files and rerun."


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
