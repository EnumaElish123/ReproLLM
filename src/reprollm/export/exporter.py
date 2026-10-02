"""REPRODUCIBILITY.md exporter (spec §19, M7-T01).

Renders the merged State (manifest + latest lock + selected/latest run) into a
deterministic template: same inputs → byte-identical output (no wall-clock
time in the template; only recorded run/lock timestamps appear). The whole
document passes :func:`reprollm.core.redaction.redact_text` as a final gate,
and an audit runs at export time to embed its summary verbatim.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
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
    model_details: list[dict[str, Any]] = field(default_factory=list)
    dataset_details: list[dict[str, Any]] = field(default_factory=list)
    prompt_details: list[dict[str, Any]] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    evaluation_details: list[dict[str, Any]] = field(default_factory=list)
    judge_details: list[dict[str, Any]] = field(default_factory=list)
    privacy_details: list[dict[str, Any]] = field(default_factory=list)
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
    if (
        text.startswith("sha256:")
        and len(text) == 71
        and all(char in "0123456789abcdefABCDEF" for char in text[7:])
    ):
        return text[:19]  # prefix + 12 hex
    if len(text) >= 32 and all(c in "0123456789abcdefABCDEF" for c in text):
        return text[:12]
    return text


def _revision(flat: dict[str, Leaf], path: str, *, unresolved_detail: bool = True) -> str:
    leaf = flat.get(path)
    if leaf is None:
        return "not locked"
    if leaf.source == "run":
        return f"{_short(leaf.value)} (observed)"
    if leaf.source == "lock":
        if leaf.confidence == "exact":
            return _short(leaf.value)
        return f"not locked ({leaf.confidence})" if unresolved_detail else "not locked"
    return "not locked"


def _model_rows(flat: dict[str, Leaf]) -> list[dict[str, Any]]:
    roles = sorted({p.split(".", 2)[1] for p in flat if p.startswith("models.")})
    rows: list[dict[str, Any]] = []
    for role in roles:
        prefix = f"models.{role}"
        chat = flat.get(f"{prefix}.chat_template.sha256")
        chat_template = "—"
        if chat is not None:
            chat_template = (
                _short(chat.value)
                if chat.confidence == "exact" or chat.source == "run"
                else f"{_value(flat, f'{prefix}.chat_template.status')} (unresolved)"
            )
        rows.append(
            {
                "role": role,
                "provider": _value(flat, f"{prefix}.provider") or "—",
                "id": _value(flat, f"{prefix}.id") or "—",
                "revision": _revision(flat, f"{prefix}.revision"),
                "pinnability": _value(flat, f"{prefix}.pinnability") or "",
                "tokenizer": (
                    _revision(flat, f"{prefix}.tokenizer.revision", unresolved_detail=False)
                    if f"{prefix}.tokenizer.revision" in flat
                    else "—"
                ),
                "chat_template": chat_template,
            }
        )
    return rows


def _dataset_rows(flat: dict[str, Leaf]) -> list[dict[str, Any]]:
    roles = sorted({p.split(".", 2)[1] for p in flat if p.startswith("datasets.")})
    return [
        {
            "role": role,
            "provider": _value(flat, f"datasets.{role}.provider") or "—",
            "id": _value(flat, f"datasets.{role}.id") or "—",
            "split": _value(flat, f"datasets.{role}.split"),
            "revision": _revision(flat, f"datasets.{role}.revision"),
            "fingerprint": _value(flat, f"datasets.{role}.content_fingerprint.status") or "",
        }
        for role in roles
    ]


def _prompt_rows(flat: dict[str, Leaf]) -> list[dict[str, Any]]:
    roles = sorted({p.split(".", 2)[1] for p in flat if p.startswith("prompts.")})
    rows: list[dict[str, Any]] = []
    for role in roles:
        prefix = f"prompts.{role}"
        digest = _value(flat, f"{prefix}.sha256") or _value(flat, f"{prefix}.text_sha256")
        rows.append(
            {
                "role": role,
                "path": _value(flat, f"{prefix}.path") or "(inline text)",
                "sha256": _short(digest) if digest else "not locked",
            }
        )
    return rows


def _section(flat: dict[str, Leaf], prefix: str) -> dict[str, Any]:
    return {
        path[len(prefix) + 1 :]: leaf.value
        for path, leaf in flat.items()
        if path.startswith(prefix + ".") and leaf.value is not None
    }


def _source(leaf: Leaf) -> str:
    if leaf.source == "run":
        return "observed (run)"
    if leaf.source == "lock":
        return f"locked ({leaf.confidence})"
    if leaf.source == "manifest":
        return "declared (manifest)"
    return f"{leaf.source} ({leaf.confidence})"


def _detail_rows(
    flat: dict[str, Leaf],
    prefix: str,
    *,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    full_paths: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path, leaf in sorted(flat.items()):
        if not path.startswith(prefix + ".") or leaf.value is None:
            continue
        suffix = path[len(prefix) + 1 :]
        if include and not any(suffix == key or suffix.startswith(key + ".") for key in include):
            continue
        if any(suffix == key or suffix.startswith(key + ".") for key in exclude):
            continue
        rows.append(
            {
                "field": path if full_paths else suffix,
                # Keep the original field/key context before display rows and JSON hide it.
                "value": _redact_keyed_values(leaf.value, (path,)),
                "source": _source(leaf),
            }
        )
    return rows


def _role_details(
    flat: dict[str, Leaf], section: str, fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    roles = sorted({path.split(".", 2)[1] for path in flat if path.startswith(section + ".")})
    return [
        row
        for role in roles
        for row in _detail_rows(flat, f"{section}.{role}", include=fields, full_paths=True)
    ]


def _metric_rows(flat: dict[str, Leaf]) -> list[dict[str, Any]]:
    leaf = flat.get("evaluation.metrics")
    if leaf is None or not isinstance(leaf.value, list):
        return []
    return [
        {
            "name": metric.get("name", "not declared"),
            "implementation": metric.get("implementation") or "not declared",
            "sha256": _short(metric.get("implementation_sha256")) or "not recorded",
            "version": metric.get("implementation_version") or "not recorded",
            "params": _redact_keyed_values(
                metric.get("params", "not recorded"), ("evaluation.metrics.params",)
            ),
            "source": _source(leaf),
        }
        for metric in leaf.value
        if isinstance(metric, dict) and isinstance(metric.get("name"), str)
    ]


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
        models=_model_rows(flat),
        datasets=_dataset_rows(flat),
        prompts=_prompt_rows(flat),
        model_details=_role_details(flat, "models", ("dtype", "quantization", "adapter")),
        dataset_details=_role_details(flat, "datasets", ("subset", "split", "preprocessing")),
        prompt_details=_role_details(flat, "prompts", ("format", "few_shot")),
        metrics=_metric_rows(flat),
        evaluation_details=_detail_rows(flat, "evaluation", exclude=("metrics", "judge")),
        judge_details=_detail_rows(flat, "evaluation.judge"),
        privacy_details=_detail_rows(flat, "privacy"),
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


def _redact_keyed_values(value: Any, keys: tuple[str, ...] = ()) -> Any:
    """Keep secret-key context before Markdown punctuation or nested repr hides it."""
    if isinstance(value, dict):
        return {key: _redact_keyed_values(item, (*keys, str(key))) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_keyed_values(item, keys) for item in value]
    original = str(value)
    safe = original
    for key in keys:
        # Test raw context first: escaping a newline in a secret-bearing key can
        # conceal the key/value separator from the normative redaction patterns.
        prefix = f"{key}=\n"
        safe_prefix, _ = redact_text(prefix)
        redacted, _ = redact_text(prefix + safe)
        safe = (
            redacted[len(safe_prefix) :]
            if redacted.startswith(safe_prefix)
            else "<REDACTED:generic_kv>"
        )
    return value if safe == original else safe


def _render_input(data: ExportInput) -> ExportInput:
    return ExportInput(**_redact_keyed_values(asdict(data)))


def _portable_value(value: Any, sanitize: Callable[[str], str] | None) -> Any:
    if sanitize is None:
        return value
    if isinstance(value, str):
        return sanitize(value)
    if isinstance(value, dict):
        return {
            sanitize(str(key)): _portable_value(item, sanitize)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_portable_value(item, sanitize) for item in value]
    return value


def _display_value(value: Any, sanitize: Callable[[str], str] | None) -> str:
    value = _portable_value(value, sanitize)
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


class _CodeSpan(str):
    """A code span whose content already crossed the privacy boundary."""


def _code_span(
    value: Any, sanitize: Callable[[str], str] | None, code_spans: set[str]
) -> _CodeSpan:
    content = str(_portable_value(value, sanitize))
    content, _count = redact_text(content)
    # Markdown normalizes single newlines inside code spans to spaces. Keep
    # blank lines from turning a displayed value into a separate block.
    content = content.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    longest = max((len(match[0]) for match in re.finditer(r"`+", content)), default=0)
    delimiter = "`" * (longest + 1)
    pad = (
        " "
        if content.startswith("`")
        or content.endswith("`")
        or (content.startswith(" ") and content.endswith(" ") and not content.isspace())
        else ""
    )
    rendered = f"{delimiter}{pad}{content}{pad}{delimiter}"
    code_spans.add(rendered)
    return _CodeSpan(rendered)


def _display_text(value: Any, sanitize: Callable[[str], str] | None) -> str:
    if isinstance(value, _CodeSpan):
        return str(value)
    text = str(_portable_value(value, sanitize))
    # Check privacy first; entities keep free text from creating HTML, links,
    # images or emphasis while preserving its rendered Unicode and URL text.
    return (
        html.escape(text, quote=False)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("`", "&#96;")
        .replace("[", "&#91;")
        .replace("]", "&#93;")
        .replace("*", "&#42;")
        .replace("_", "&#95;")
        .replace("~", "&#126;")
        .replace("\r\n", "<br>")
        .replace("\r", "<br>")
        .replace("\n", "<br>")
    )


def _escape_markers(text: str) -> str:
    return re.sub(r"<REDACTED:[a-z_]+>", lambda match: html.escape(match[0]), text)


def _final_redaction(document: str, code_spans: set[str]) -> str:
    safe, _count = redact_text(document)
    if not code_spans:
        return _escape_markers(safe)
    # Entities are literal text inside Markdown code spans. Preserve only the
    # exact spans created by our filter; escape any new marker in ordinary text.
    pattern = "|".join(re.escape(span) for span in sorted(code_spans, key=lambda s: (-len(s), s)))
    result: list[str] = []
    start = 0
    for match in re.finditer(pattern, safe):
        result.extend((_escape_markers(safe[start : match.start()]), match[0]))
        start = match.end()
    result.append(_escape_markers(safe[start:]))
    return "".join(result)


def render(data: ExportInput, *, sanitize: Callable[[str], str] | None = None) -> str:
    source = (files("reprollm.export") / "templates" / "REPRODUCIBILITY.md.j2").read_text(
        encoding="utf-8"
    )
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        finalize=lambda value: _display_text(value, sanitize),
    )
    code_spans: set[str] = set()
    environment.filters["code"] = lambda value: _code_span(value, sanitize, code_spans)
    environment.filters["display"] = lambda value: _display_value(value, sanitize)
    template = environment.from_string(source)
    rendered = template.render(data=_render_input(data), short=_short)
    return _final_redaction(rendered, code_spans).lstrip("\n")


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

    model_details = {row["field"]: row["value"] for row in data.model_details}
    adapters = [
        f"{value} @ {model_details.get(path.removesuffix('.id') + '.revision', 'unpinned')}"
        for path, value in sorted(model_details.items())
        if path.endswith(".adapter.id")
    ]
    data.adapter_summary = ", ".join(adapters) if adapters else "none"
    formats = [
        f"{row['field'].split('.')[1]}:{row['value']}"
        for row in data.prompt_details
        if row["field"].endswith(".format")
    ]
    data.prompt_formats = ", ".join(formats) if formats else "not declared"

    data.has_judge = any(key.startswith("judge.") for key in data.evaluation)
    data.judge_model_ref = str(data.evaluation.get("judge.model_ref", "judge"))
    judge_id = next(
        (model["id"] for model in data.models if model["role"] == data.judge_model_ref), None
    )
    data.judge_summary = judge_id if judge_id is not None else "unknown"
    data.has_privacy = bool(data.privacy_details)


def render_checklist_mapping(
    data: ExportInput, *, venue: str, sanitize: Callable[[str], str] | None = None
) -> str:
    """Render the venue-specific checklist-mapping template."""
    source = (files("reprollm.export") / "templates" / "checklist_mapping.md.j2").read_text(
        encoding="utf-8"
    )
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        finalize=lambda value: _display_text(value, sanitize),
    )
    code_spans: set[str] = set()
    environment.filters["code"] = lambda value: _code_span(value, sanitize, code_spans)
    environment.filters["display"] = lambda value: _display_value(value, sanitize)
    template = environment.from_string(source)
    rendered = template.render(data=_render_input(data), venue=venue)
    return _final_redaction(rendered, code_spans).lstrip("\n").rstrip("\n") + "\n"
