"""REPRODUCIBILITY.md exporter (spec §19, M7-T01).

Renders the merged State (manifest + latest lock + selected/latest run) into a
deterministic template: same inputs → byte-identical output (no wall-clock
time in the template; only recorded run/lock timestamps appear). The whole
document passes :func:`reprollm.core.redaction.redact_text` as a final gate,
and an audit runs at export time to embed its summary verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any

import jinja2

from reprollm.core.redaction import redact_text
from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import Leaf, State


@dataclass
class ExportInput:
    """Everything the template renders; built once from persisted documents."""

    project_name: str = ""
    models: list[dict[str, Any]] = field(default_factory=list)
    datasets: list[dict[str, Any]] = field(default_factory=list)
    prompts: list[dict[str, Any]] = field(default_factory=list)
    generation: dict[str, Any] = field(default_factory=dict)
    inference: dict[str, Any] = field(default_factory=dict)
    training: dict[str, Any] = field(default_factory=dict)
    evaluation: dict[str, Any] = field(default_factory=dict)
    privacy: dict[str, Any] = field(default_factory=dict)
    code: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    hardware: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    audit_summary: dict[str, int] = field(default_factory=dict)
    audit_notable: list[dict[str, str]] = field(default_factory=list)
    profiles: list[str] = field(default_factory=list)
    reprollm_version: str = ""
    schema_versions: dict[str, int | None] = field(default_factory=dict)
    # Checklist-template summaries (populated by enrich_for_checklist)
    metrics_summary: str = ""
    adapter_summary: str = ""
    prompt_formats: str = ""
    has_judge: bool = False
    judge_summary: str = ""
    judge_model_ref: str = "judge"
    has_privacy: bool = False

    def has_run(self) -> bool:
        return bool(self.execution)


def _value(flat: dict[str, Leaf], path: str) -> Any:
    leaf = flat.get(path)
    return None if leaf is None else leaf.value


def _short(hash_value: Any) -> str:
    """Display form: 12 leading chars for sha256: digests and bare hex SHAs."""
    text = str(hash_value or "")
    if text.startswith("sha256:"):
        return text[:19]  # prefix + 12 hex
    if len(text) >= 32 and all(c in "0123456789abcdefABCDEF" for c in text):
        return text[:12]
    return text


def _model_rows(flat: dict[str, Leaf], lock: Lock | None) -> list[dict[str, Any]]:
    roles = sorted({p.split(".", 2)[1] for p in flat if p.startswith("models.")})
    rows: list[dict[str, Any]] = []
    for role in roles:
        prefix = f"models.{role}"
        row: dict[str, Any] = {
            "role": role,
            "provider": _value(flat, f"{prefix}.provider") or "—",
            "id": _value(flat, f"{prefix}.id") or "—",
        }
        if lock is not None and role in lock.models:
            locked = lock.models[role]
            revision = locked.revision
            row["revision"] = (
                _short(revision.value)
                if revision.confidence.value == "exact"
                else f"not locked ({revision.confidence.value})"
            )
            row["pinnability"] = locked.pinnability
            if locked.tokenizer is not None:
                row["tokenizer"] = (
                    _short(locked.tokenizer.revision.value)
                    if locked.tokenizer.revision.confidence.value == "exact"
                    else "not locked"
                )
            if locked.chat_template is not None:
                row["chat_template"] = (
                    _short(locked.chat_template.sha256.value)
                    if locked.chat_template.sha256.confidence.value == "exact"
                    else f"{locked.chat_template.status} (unresolved)"
                )
        else:
            row["revision"] = "not locked"
            row["pinnability"] = ""
        row.setdefault("tokenizer", "—")
        row.setdefault("chat_template", "—")
        rows.append(row)
    return rows


def _dataset_rows(flat: dict[str, Leaf], lock: Lock | None) -> list[dict[str, Any]]:
    roles = sorted({p.split(".", 2)[1] for p in flat if p.startswith("datasets.")})
    rows: list[dict[str, Any]] = []
    for role in roles:
        prefix = f"datasets.{role}"
        row = {
            "role": role,
            "provider": _value(flat, f"{prefix}.provider") or "—",
            "id": _value(flat, f"{prefix}.id") or "—",
            "split": _value(flat, f"{prefix}.split"),
        }
        if lock is not None and role in lock.datasets:
            revision = lock.datasets[role].revision
            row["revision"] = (
                _short(revision.value)
                if revision.confidence.value == "exact"
                else f"not locked ({revision.confidence.value})"
            )
            row["fingerprint"] = lock.datasets[role].content_fingerprint.status
        else:
            row["revision"] = "not locked"
            row["fingerprint"] = ""
        rows.append(row)
    return rows


def _prompt_rows(flat: dict[str, Leaf], lock: Lock | None) -> list[dict[str, Any]]:
    roles = sorted({p.split(".", 2)[1] for p in flat if p.startswith("prompts.")})
    rows: list[dict[str, Any]] = []
    for role in roles:
        prefix = f"prompts.{role}"
        row: dict[str, Any] = {
            "role": role,
            "path": _value(flat, f"{prefix}.path") or "(inline text)",
        }
        digest = None
        if lock is not None and role in lock.prompts:
            entry = lock.prompts[role]
            digest = entry.sha256 or entry.text_sha256
        row["sha256"] = _short(digest) if digest else "not locked"
        rows.append(row)
    return rows


def _section(flat: dict[str, Leaf], prefix: str) -> dict[str, Any]:
    return {
        path[len(prefix) + 1 :]: leaf.value
        for path, leaf in flat.items()
        if path.startswith(prefix + ".") and leaf.value is not None
    }


def _limitations(flat: dict[str, Leaf], lock: Lock | None, manifest: Manifest | None) -> list[str]:
    found: list[str] = []
    if lock is not None:
        for role, model in sorted(lock.models.items()):
            if model.revision.confidence.value != "exact":
                note = f"models.{role}: revision unresolved ({model.revision.source})"
                if model.revision.note:
                    note += f" — {model.revision.note}"
                found.append(note)
            if model.pinnability == "unpinnable":
                found.append(
                    f"models.{role}: closed-source API alias is unpinnable;"
                    " identity is observation-based only"
                )
        for role, dataset in sorted(lock.datasets.items()):
            if dataset.revision.confidence.value != "exact":
                found.append(f"datasets.{role}: revision unresolved ({dataset.revision.source})")
            if dataset.content_fingerprint.status == "not_computed":
                found.append(f"datasets.{role}: content fingerprint not computed")
        if lock.environment is not None and lock.environment.gpu.source == "unavailable":
            found.append("hardware: GPU information unavailable at lock time")
    else:
        for path in sorted(flat):
            if path.startswith(("models.", "datasets.")) and path.endswith((".id", ".revision")):
                found.append(f"{path}: no lock exists; value unresolved")
    if manifest is not None and manifest.bindings:
        found.append(
            "bindings: "
            + ", ".join(sorted(manifest.bindings))
            + " — runtime agreement is only checked when run records exist"
        )
    return list(dict.fromkeys(found))


def build_input(
    manifest: Manifest | None,
    lock: Lock | None,
    run: RunRecord | None,
    state: State,
    *,
    reprollm_version: str,
    audit_report: Any = None,
) -> ExportInput:
    flat = state.flatten()
    data = ExportInput(
        project_name=(manifest.project.name if manifest else "experiment"),
        profiles=(manifest.experiment.profiles if manifest else []),
        models=_model_rows(flat, lock),
        datasets=_dataset_rows(flat, lock),
        prompts=_prompt_rows(flat, lock),
        generation=_section(flat, "generation"),
        inference=_section(flat, "inference"),
        training=_section(flat, "training"),
        evaluation=_section(flat, "evaluation"),
        privacy=_section(flat, "privacy"),
        code=dict(_section(flat, "code")),
        environment=dict(_section(flat, "environment")),
        hardware=dict(_section(flat, "hardware")),
        execution={},
        limitations=_limitations(flat, lock, manifest),
        reprollm_version=reprollm_version,
        schema_versions={
            "manifest": (manifest.schema_version if manifest else None),
            "lock": (lock.schema_version if lock else None),
            "run_record": (run.schema_version if run else None),
        },
    )
    if run is not None:
        data.execution = {
            "command": " ".join(run.command.argv),
            "run_id": run.run_id,
            "started_at": run.started_at,
            "ended_at": run.ended_at,
            "duration_seconds": run.duration_seconds,
            "exit_code": run.exit_code,
            "status": run.status.value,
        }
    if audit_report is not None:
        summary = audit_report.summary
        data.audit_summary = {
            "critical": summary.critical,
            "warning": summary.warning,
            "info": summary.info,
            "pass": summary.pass_,
        }
        data.audit_notable = [
            {"severity": f.severity.value, "rule": f.rule_id, "message": f.message}
            for f in audit_report.findings
            if f.severity.value in ("CRITICAL", "WARNING")
        ]
    return data


def render(data: ExportInput) -> str:
    source = (files("reprollm.export") / "templates" / "REPRODUCIBILITY.md.j2").read_text(
        encoding="utf-8"
    )
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.from_string(source)
    rendered = template.render(data=data, short=_short)
    safe, _count = redact_text(rendered)
    return safe.lstrip("\n")


def enrich_for_checklist(
    data: ExportInput,
    manifest: Manifest | None,
    lock: Lock | None,
) -> None:
    """Add the derived summaries the checklist template needs."""
    effective_metrics = data.evaluation.get("metrics")
    metric_rows = effective_metrics if isinstance(effective_metrics, list) else []
    metrics = [
        metric["name"]
        for metric in metric_rows
        if isinstance(metric, dict) and isinstance(metric.get("name"), str)
    ]
    data.metrics_summary = ", ".join(metrics) if metrics else "not declared"

    models = manifest.models if manifest is not None else {}
    adapters = [
        f"{spec.adapter.id} @ {spec.adapter.revision or 'unpinned'}"
        for spec in models.values()
        if spec.adapter is not None
    ]
    data.adapter_summary = adapters[0] if adapters else "none"

    prompts = manifest.prompts if manifest is not None else {}
    formats = [f"{role}:{spec.format or 'plain'}" for role, spec in prompts.items()]
    data.prompt_formats = ", ".join(formats) if formats else "none"

    data.has_judge = any(key.startswith("judge.") for key in data.evaluation)
    data.judge_model_ref = str(data.evaluation.get("judge.model_ref", "judge"))
    judge_id = next(
        (model["id"] for model in data.models if model["role"] == data.judge_model_ref), None
    )
    data.judge_summary = judge_id if judge_id is not None else "unknown"
    data.has_privacy = bool(data.privacy.get("mechanism.name"))


def render_checklist_mapping(data: ExportInput, *, venue: str) -> str:
    """Render the venue-specific checklist-mapping template."""
    source = (files("reprollm.export") / "templates" / "checklist_mapping.md.j2").read_text(
        encoding="utf-8"
    )
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.from_string(source)
    rendered = template.render(data=data, venue=venue)
    safe, _count = redact_text(rendered)
    return safe.lstrip("\n").rstrip("\n") + "\n"
