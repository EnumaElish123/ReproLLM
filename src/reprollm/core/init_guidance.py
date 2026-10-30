"""Field guidance and in-memory answer validation for interactive init (UXR04)."""

from __future__ import annotations

import getpass
import re
import socket
import unicodedata
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.core.manifest_scaffold import SECTION_ORDER, InitPlan, parse_scalar, render_manifest
from reprollm.core.redaction import redact_text
from reprollm.core.yaml_io import parse_manifest_text
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.manifest import Manifest, validate_field_path

MANUAL_FIELDS = frozenset(
    {
        "evaluation.definitions.refusal",
        "evaluation.definitions.asr",
        "privacy.mechanism.name",
        "evaluation.metrics",
    }
)

_GUIDANCE = {
    "models.primary.id": (
        "Model identifier used for generation or training; verify any detected candidate."
    ),
    "inference.backend": "Inference engine: vllm, transformers, sglang, openai or other.",
    "generation.temperature": (
        "Sampling temperature used by the experiment; enter a number from 0 to 2."
    ),
    "generation.max_tokens": "Maximum generated tokens; enter a whole number of at least 1.",
    "datasets.eval.id": "Evaluation dataset identifier used by this experiment.",
    "datasets.train.id": "Training dataset identifier used by this experiment.",
    "training.method": "Training method: full, lora, qlora or other.",
    "training.learning_rate": (
        "Learning rate used by the training command or configuration; enter a number."
    ),
    "models.judge.id": (
        "Identifier of the model that scores the outputs, separate from the primary model."
    ),
    "prompts.judge.path": (
        "Judge rubric file relative to the project; use / separators and no .. components."
    ),
    "evaluation.judge.params.temperature": (
        "Judge sampling temperature; enter a number from 0 to 2."
    ),
    "evaluation.judge.params.max_tokens": (
        "Maximum tokens per judge response; enter a whole number of at least 1."
    ),
    "privacy.threat_model": (
        "Describe the adversary, its access and the information the experiment protects."
    ),
    "evaluation.metrics": "Review actual metric names and their implementations in reprollm.yaml.",
    "evaluation.definitions.refusal": (
        "Define what counts as a refusal in reprollm.yaml; use text or a relative file path."
    ),
    "evaluation.definitions.asr": (
        "Define attack success in reprollm.yaml; use text or a relative file path."
    ),
    "privacy.mechanism.name": (
        "Declare the privacy mechanism and its parameters together in reprollm.yaml."
    ),
}


def field_label(field_path: str, privacy: RunPrivacy | None = None) -> str:
    """Display a bounded field identifier without terminal controls or secret patterns."""
    try:
        safe = redact_text(field_path)[0]
        if privacy is not None:
            safe = privacy.text(safe)[0]
    except (ValueError, RecursionError):
        return "<required field in reprollm.yaml>"
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", safe):
        return "<required field in reprollm.yaml>"
    return safe if len(safe) <= 160 else safe[:157] + "..."


def field_guidance(field_path: str) -> str:
    return _GUIDANCE.get(
        field_path,
        "Enter the value used by this experiment; use reprollm.yaml for structured values.",
    )


class InvalidAnswer(UserError):
    """A single answer can be corrected without changing the scaffold."""


def _scaffold_error() -> UserError:
    return UserError(
        "reprollm.yaml interactive scaffold is invalid; review the selected profiles' "
        "required_fields or create the manifest manually"
    )


def _validate_pending_manifest(plan: InitPlan, text: str, current_field: str | None = None) -> None:
    """Defer only scalar type errors at explicit null fields still awaiting input."""
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        raise ValueError("invalid scaffold YAML") from None
    if not isinstance(document, dict):
        raise ValueError("invalid scaffold document")
    try:
        Manifest.model_validate(document)
    except ValidationError as exc:
        active_errors: list[str] = []
        for error in exc.errors(include_input=False, include_context=False, include_url=False):
            location = error["loc"]
            field_path = ".".join(str(segment) for segment in location)
            current: Any = document
            for segment in location:
                if not isinstance(current, dict) or segment not in current:
                    current = ...
                    break
                current = current[segment]
            if (
                field_path in plan.required_fields
                and current is None
                and error["type"]
                in {"string_type", "int_type", "float_type", "bool_type", "literal_error"}
            ):
                continue
            active_errors.append(field_path)
        if active_errors:
            if current_field is not None and all(path == current_field for path in active_errors):
                raise
            raise _scaffold_error() from None


def check_interactive_plan(
    plan: InitPlan,
    values: dict[str, Any],
    selected_tasks: list[str],
    saved_command: str | None,
    privacy: RunPrivacy,
) -> None:
    """Fail unsupported baseline scaffolds once, before entering a retry loop."""
    try:
        for field_path in plan.required_fields:
            if field_path != "project.name" and field_path.split(".")[0] not in SECTION_ORDER:
                raise ValueError("unsupported scaffold section")
            if field_path not in MANUAL_FIELDS:
                validate_field_path(field_path)
        _validate_pending_manifest(
            plan,
            render_manifest(
                plan, values, selected_tasks=selected_tasks, saved_command=saved_command
            ),
        )
        if plan.primary_detection is not None:
            detected = plan.primary_detection[0]
            safe, replaced = privacy.text(detected)
            if replaced or safe != detected or any(not char.isprintable() for char in detected):
                raise ValueError("unsafe detected candidate")
    except (UserError, ValueError, RecursionError):
        raise _scaffold_error() from None


def validate_answer(
    plan: InitPlan,
    values: dict[str, Any],
    field_path: str,
    answer: str,
    *,
    selected_tasks: list[str],
    saved_command: str | None,
    privacy: RunPrivacy,
) -> Any:
    """Check one tentative answer without changing accepted answers or writing files."""
    error = (
        f"Invalid value for {field_label(field_path, privacy)}. "
        "Use the described type and range, or press Enter to keep it unknown/current."
    )
    try:
        if any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for c in answer):
            raise ValueError("control character")
        safe, replaced = privacy.text(answer, keys=tuple(field_path.split(".")))
        if replaced or safe != answer:
            raise ValueError("unsafe answer")
        value = parse_scalar(field_path, answer)
        if isinstance(value, str):
            value = answer.strip()
        tentative = {**values, field_path: value}
        _validate_pending_manifest(
            plan,
            render_manifest(
                plan, tentative, selected_tasks=selected_tasks, saved_command=saved_command
            ),
            current_field=field_path,
        )
    except (ValueError, RecursionError, UnicodeError):
        raise InvalidAnswer(error) from None
    return value


def missing_required_fields(plan: InitPlan, manifest_text: str) -> list[str]:
    """Count only absent/null/empty declarations, without treating defaults as input."""
    try:
        parse_manifest_text(manifest_text)
        document = yaml.safe_load(manifest_text)
    except (UserError, ValueError, RecursionError, UnicodeError):
        raise UserError(
            "reprollm.yaml failed validation; correct the init answers and retry"
        ) from None
    missing: list[str] = []
    for field_path in plan.required_fields:
        value: Any = document
        for segment in field_path.split("."):
            value = value.get(segment) if isinstance(value, dict) else None
        if value is None or value == "" or value == [] or value == {}:
            missing.append(field_path)
    return missing


def answer_privacy(root: Path) -> RunPrivacy:
    """Reuse the existing init persistence privacy policy for answers."""
    return RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
