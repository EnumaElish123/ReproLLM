"""Init scaffold service (spec §3.2, M2F-T09).

Planning, manifest rendering, and owned-file writes for ``reprollm init``.
The CLI layer only parses arguments, performs Typer prompting, and prints;
all domain construction lives here. The manifest is rendered from a Jinja
template (comments preserved), never dumped from a model. Required fields
become ``TODO`` keys; null values keep the result loadable.
"""

from __future__ import annotations

import getpass
import json
import os
import socket
import stat
import tempfile
import unicodedata
from contextlib import suppress
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

import jinja2
import yaml
from pydantic import ValidationError

from reprollm.core.context import AuditContext
from reprollm.core.errors import UserError
from reprollm.core.paths import MANIFEST
from reprollm.core.persistence import redact_keyed_values
from reprollm.core.saved_command import parse_saved_command
from reprollm.core.yaml_io import parse_manifest_text
from reprollm.integrations.frameworks import detected_frameworks
from reprollm.profiles import loader
from reprollm.profiles.policy import judge_only_exception
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.finding import DetectionResult
from reprollm.schemas.manifest import Project

#: Section order follows the manifest schema (spec §3).
SECTION_ORDER = (
    "models",
    "datasets",
    "prompts",
    "generation",
    "inference",
    "training",
    "evaluation",
    "privacy",
    "execution",
)

#: Required fields that cannot hold a null value are rendered as commented
#: examples instead (a null key would fail manifest validation).
_COMMENTED_FIELDS: dict[str, tuple[str, list[str]]] = {
    "evaluation.definitions.refusal": (
        "evaluation",
        ["definitions:", "  refusal: definitions/refusal.txt  # text or relative path"],
    ),
    "evaluation.definitions.asr": (
        "evaluation",
        ["definitions:", "  asr: definitions/asr.txt  # text or relative path"],
    ),
    "privacy.mechanism.name": (
        "privacy",
        ["mechanism:", "  name: orthogonal_noise", "  params: {alpha: 0.25}"],
    ),
}

#: Required fields rendered as an empty list with a TODO (null would be invalid).
_LIST_FIELDS = {"evaluation.metrics"}

#: Numeric required fields (interactive answers are parsed to numbers).
_NUMERIC_FIELDS = {
    "generation.temperature",
    "generation.max_tokens",
    "training.learning_rate",
    "evaluation.judge.params.temperature",
    "evaluation.judge.params.max_tokens",
}

#: Static example blocks appended for sections the profiles did not require.
_EXAMPLE_BLOCKS: dict[str, list[str]] = {
    "generation": [
        "generation:",
        "  temperature: 0.0",
        "  top_p: 1.0",
        "  max_tokens: 2048",
        "  seed: 42",
    ],
    "inference": [
        "inference:",
        "  backend: vllm  # vllm | transformers | sglang | openai | other",
        "  dtype: bfloat16",
        "  tensor_parallel_size: 1",
    ],
    "execution": [
        "execution:",
        "  command: python eval.py --config configs/eval.yaml",
        "  seed: 42",
        "  config_files: [configs/eval.yaml]",
    ],
    "prompts": [
        "prompts:",
        "  system:",
        "    path: prompts/system.txt",
        "    format: plain",
    ],
    "datasets": [
        "datasets:",
        "  eval:",
        "    provider: huggingface",
        "    id: cais/mmlu",
        "    split: test",
    ],
    "models": [
        "models:",
        "  primary:",
        "    provider: huggingface",
        "    id: org/model",
        "    revision: <commit sha>",
    ],
    "training": [
        "training:",
        "  method: lora",
        "  learning_rate: 0.0001",
        "  batch_size: 8",
    ],
    "evaluation": [
        "evaluation:",
        "  metrics:",
        "    - {name: accuracy, implementation: eval.py}",
        "  aggregation: mean",
        "  repetitions: 1",
    ],
    "privacy": [
        "privacy:",
        "  threat_model: honest-but-curious server",
        "  mechanism: {name: orthogonal_noise, params: {alpha: 0.25}}",
    ],
}

_PROJECT_RULES_TEMPLATE = """\
# .reprollm/project-rules.yaml — repository-specific accepted rules (spec §7).
# Add rules with `reprollm rules add` (M7) or edit manually.
schema_version: 1
rules: []
ignored_candidates: []
"""


def _render_manifest(
    project_name: str,
    profiles: list[str],
    sections: list[dict[str, Any]],
    examples: list[list[str]],
    detected: bool,
) -> str:
    source = (files("reprollm.cli") / "templates" / "manifest.yaml.j2").read_text(encoding="utf-8")
    environment = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )
    template = environment.from_string(source)
    try:
        scalar = (
            project_name
            if yaml.safe_load(project_name) == project_name
            else json.dumps(project_name)
        )
    except yaml.YAMLError:
        scalar = json.dumps(project_name)
    rendered = template.render(
        project_name=scalar,
        profiles=profiles,
        detected_profiles=detected,
        sections=sections,
        examples=examples,
    )
    # Leading newlines leak from the macro definitions at the top of the file.
    return rendered.lstrip("\n")


def _config_template_text() -> str:
    return (files("reprollm.cli") / "templates" / "config.yaml.j2").read_text(encoding="utf-8")


def _leaf(
    value: Any = None,
    comment: str | None = None,
    todo: bool = True,
    extra: list[str] | None = None,
) -> dict[str, Any]:
    # All keys always present: the template uses StrictUndefined.
    return {
        "comment_only": False,
        "children": None,
        "value": value,
        "comment": comment,
        "todo": todo,
        "extra": extra or [],
    }


def _build_sections(
    required_fields: list[str],
    values: dict[str, Any],
    primary_detection: tuple[str, str, int] | None,
    other_detections: list[tuple[str, str, int]],
    task_names: list[str] | None = None,
    task_sources: list[str] | None = None,
    saved_command: str | None = None,
) -> list[dict[str, Any]]:
    trees: dict[str, dict[str, Any]] = {}
    commented: dict[str, list[str]] = {}

    fields = list(required_fields)
    if saved_command is not None:
        values = {**values, "execution.command": json.dumps(saved_command, ensure_ascii=False)}
        if "execution.command" not in fields:
            fields.append("execution.command")
    for field_path in fields:
        if field_path == "project.name":
            continue  # rendered explicitly from the directory name
        if field_path in _COMMENTED_FIELDS:
            section, lines = _COMMENTED_FIELDS[field_path]
            commented.setdefault(section, []).extend(lines)
            continue
        parts = field_path.split(".")
        node = trees.setdefault(parts[0], {})
        for part in parts[1:-1]:
            node = node.setdefault(part, {})
        if field_path == "models.primary.id":
            interactive_value = values.get(field_path)
            if interactive_value is not None:
                node[parts[-1]] = _leaf(value=interactive_value, todo=False)
            elif primary_detection is not None:
                value, path, line = primary_detection
                node[parts[-1]] = _leaf(
                    value=value,
                    comment=f"detected candidate; verify role: {path}:{line}",
                    todo=False,
                    extra=[f"also detected candidate: {p}:{ln}" for _v, p, ln in other_detections],
                )
            else:
                node[parts[-1]] = _leaf()
        elif field_path in _LIST_FIELDS:
            if field_path in values:
                node[parts[-1]] = _leaf(value=json.dumps(values[field_path]), todo=False)
            elif task_names:
                node[parts[-1]] = _leaf(
                    value=json.dumps([{"name": name} for name in task_names], ensure_ascii=False),
                    comment="selected task candidates; verify tasks and set implementation",
                    todo=False,
                    extra=[
                        f"task candidates from: {', '.join(task_sources or [])}",
                        "Confirm each metric name and implementation for this experiment.",
                    ],
                )
            else:
                node[parts[-1]] = _leaf(
                    value="[]", comment="TODO: list of {name, implementation}", todo=False
                )
        else:
            provided = values.get(field_path)
            node[parts[-1]] = _leaf(value=provided, todo=provided is None)

    if primary_detection is None and other_detections:
        commented.setdefault("models", []).extend(
            f"detected model candidate (unassigned): {value} ({path}:{line})"
            for value, path, line in other_detections
        )

    def materialize(node: dict[str, Any]) -> dict[str, Any]:
        children: dict[str, Any] = {}
        for key, value in node.items():
            if "value" in value:  # leaf built by _leaf
                children[key] = value
            else:
                children[key] = {
                    "comment_only": False,
                    "children": materialize(value),
                }
        return children

    sections: list[dict[str, Any]] = []
    for name in SECTION_ORDER:
        if name in trees:
            sections.append(
                {
                    "name": name,
                    "children": materialize(trees[name]),
                    "comments": commented.get(name, []),
                }
            )
        elif name in commented:
            sections.append({"name": name, "children": {}, "comments": commented[name]})
    return sections


def _example_blocks(sections: list[dict[str, Any]]) -> list[list[str]]:
    rendered = {section["name"] for section in sections}
    return [
        _EXAMPLE_BLOCKS[name]
        for name in SECTION_ORDER
        if name not in rendered and name in _EXAMPLE_BLOCKS
    ]


def _parse_scalar(field_path: str, answer: str) -> Any:
    text = answer.strip().strip("'\"")
    if field_path in _NUMERIC_FIELDS:
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text
    return text


def build_manifest_text(
    project_name: str,
    profiles: list[str],
    required_fields: list[str],
    detection: DetectionResult,
    values: dict[str, Any] | None = None,
) -> str:
    values = values or {}
    hf_ids = sorted(
        ((hint.value, hint.path, hint.line) for hint in detection.hints.hf_ids),
        key=lambda item: (item[1], item[2], item[0]),
    )
    primary = hf_ids[0] if hf_ids else None
    others = hf_ids[1:] if primary else []

    sections = _build_sections(required_fields, values, primary, others)
    return _render_manifest(
        project_name=project_name,
        profiles=profiles,
        sections=sections,
        examples=_example_blocks(sections),
        detected=bool(detection.profiles),
    )


@dataclass(frozen=True)
class InitPlan:
    """Everything the renderer needs, produced once by :func:`plan_init`."""

    project_name: str
    profiles: list[str]
    required_fields: list[str]
    detection: DetectionResult
    primary_detection: tuple[str, str, int] | None
    other_detections: list[tuple[str, str, int]]
    task_names: list[str] = field(default_factory=list)
    task_sources: list[str] = field(default_factory=list)
    project_name_defaulted: bool = False
    diagnostics: list[str] = field(default_factory=list)


def plan_init(root: Path, *, profiles_override: list[str] | None) -> InitPlan:
    """Detection + profile resolution + required-field union for one repo."""
    ctx = AuditContext(root, level=0)
    detection = ctx.detection
    if profiles_override is not None:
        profile_list = list(profiles_override)
        if not profile_list:
            raise UserError("--profiles requires at least one profile name")
    else:
        profile_list = [
            entry.profile
            for entry in detection.profiles
            if entry.shipped and entry.confidence in {"high", "medium"}
        ]
    resolved = loader.resolve(profile_list, root)  # validates names and rule IDs
    judge_only = judge_only_exception(root, profile_list, resolved.names)
    required_fields = [
        name
        for name in resolved.required_fields
        if not (judge_only and name == "models.primary.id")
    ]
    hf_ids = sorted(
        ((hint.value, hint.path, hint.line) for hint in detection.hints.hf_ids),
        key=lambda item: (item[1], item[2], item[0]),
    )
    task_names: set[str] = set()
    task_sources: set[str] = set()
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    try:
        project_name = Project(name=root.name).name
    except ValidationError:
        project_name = "experiment"
    if privacy.text(project_name)[1]:
        project_name = "experiment"
    for integration, _evidence in detected_frameworks(ctx.fs, ctx.pyscan):
        names = integration.extract_task_hints(ctx.fs).task_names
        # Inventory is independent of selection. Never sanitize an identifier
        # into a different task or let it inject extra terminal rows.
        safe_names = {
            name
            for name in names
            if name
            and not any(unicodedata.category(c) in {"Cc", "Cf", "Zl", "Zp"} for c in name)
            and privacy.text(name)[1] == 0
        }
        if safe_names:
            task_names.update(safe_names)
            task_sources.add(integration.name)
    diagnostic = ctx.pyscan.file_limit_diagnostic()
    return InitPlan(
        project_name=project_name,
        profiles=profile_list,
        required_fields=required_fields,
        detection=detection,
        primary_detection=hf_ids[0] if hf_ids and not judge_only else None,
        other_detections=hf_ids if judge_only else hf_ids[1:],
        task_names=sorted(task_names),
        task_sources=sorted(task_sources),
        project_name_defaulted=project_name != root.name,
        diagnostics=[diagnostic] if diagnostic is not None else [],
    )


def select_tasks(plan: InitPlan, names: list[str]) -> list[str]:
    """Validate exact selections before any scaffold files are written."""
    if names and "evaluation.metrics" not in plan.required_fields:
        raise UserError(
            "--task requires profiles with evaluation.metrics; select this experiment's "
            "evaluation profile with --profiles"
        )
    if set(names) - set(plan.task_names):
        # Invalid names may contain credentials or terminal control sequences.
        raise UserError(
            "unknown or unsafe task name; run `reprollm init PATH --list-tasks` "
            "and select an exact name with --task NAME"
        )
    return sorted(set(names))


def validate_init_command(root: Path, command: str) -> str:
    """Check an explicit command before saving its original, executable string."""
    argv = parse_saved_command(command)
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    try:
        safe, replaced = privacy.text(command)
        unsafe = bool(replaced or safe != command)
        for index, token in enumerate(argv):
            context = (argv[index - 1],) if index and argv[index - 1].startswith("-") else ()
            keyed = str(redact_keyed_values(token, context))
            safe, replaced = privacy.text(keyed)
            unsafe = unsafe or bool(replaced or safe != token)
    except (ValueError, RecursionError):
        # Privacy limits reject input; never save an unchecked command or echo its values.
        raise UserError(
            "execution.command could not be checked safely; simplify its arguments "
            "or move them to a configuration file"
        ) from None
    if unsafe:
        # Rewriting would save a different command; reject without echoing private input.
        raise UserError(
            "execution.command cannot contain secrets, absolute paths or machine identity; "
            "supply credentials through the environment and use relative paths or a PATH executable"
        )
    return command


def render_manifest(
    plan: InitPlan,
    values: dict[str, Any],
    *,
    selected_tasks: list[str] | None = None,
    saved_command: str | None = None,
) -> str:
    """Render reprollm.yaml text for the plan (values from interactive input)."""
    sections = _build_sections(
        plan.required_fields,
        values,
        plan.primary_detection,
        plan.other_detections,
        select_tasks(plan, selected_tasks or []),
        plan.task_sources,
        saved_command,
    )
    return _render_manifest(
        project_name=plan.project_name,
        profiles=plan.profiles,
        sections=sections,
        examples=_example_blocks(sections),
        detected=bool(plan.detection.profiles),
    )


@dataclass(frozen=True)
class ScaffoldResult:
    manifest_written: bool
    config_written: bool
    project_rules_written: bool


def check_scaffold_paths(root: Path, *, force: bool) -> None:
    """Reject unsafe owned output nodes before detection or writes."""
    for relative, directory in (
        (MANIFEST, False),
        (".reprollm", True),
        (".reprollm/config.yaml", False),
        (".reprollm/project-rules.yaml", False),
    ):
        try:
            mode = (root / relative).lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise UserError(f"cannot inspect {relative}; check its permissions and retry") from exc
        expected = stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)
        if not expected:
            raise UserError(
                f"{relative} must be a regular {'directory' if directory else 'file'}; "
                "move the existing node before running init"
            )
    if (root / MANIFEST).exists() and not force:
        raise UserError(
            "reprollm.yaml already exists; pass --force to overwrite it "
            "(files under .reprollm/ are never overwritten)"
        )


def write_scaffold(root: Path, manifest_text: str, *, force: bool) -> ScaffoldResult:
    """Validate first, prepare missing auxiliaries, then replace the manifest.

    Roll back only files created by this call on ordinary failures. This is
    not a transaction across files under power loss or concurrent writers.
    """
    check_scaffold_paths(root, force=force)
    manifest_path = root / MANIFEST
    try:
        parse_manifest_text(manifest_text)
        manifest_text.encode("utf-8")
    except (UserError, UnicodeError) as exc:
        raise UserError(
            "reprollm.yaml failed validation; correct the init answers and retry"
        ) from exc
    dotdir = root / ".reprollm"
    created: list[Path] = []
    created_dotdir = False
    temporary: Path | None = None
    descriptor: int | None = None
    try:
        auxiliary = (
            (dotdir / "config.yaml", _config_template_text()),
            (dotdir / "project-rules.yaml", _PROJECT_RULES_TEMPLATE),
        )
        old_mode = stat.S_IMODE(manifest_path.stat().st_mode) if manifest_path.exists() else None
        descriptor, name = tempfile.mkstemp(dir=root, prefix=".reprollm.yaml.", suffix=".tmp")
        temporary = Path(name)
        stream = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
        descriptor = None
        with stream:
            stream.write(manifest_text)
            stream.flush()
            os.fsync(stream.fileno())
        if old_mode is not None:
            temporary.chmod(old_mode)
        if not dotdir.exists():
            dotdir.mkdir()
            created_dotdir = True
        for path, text in auxiliary:
            if not path.exists():
                with path.open("x", encoding="utf-8", newline="\n") as stream:
                    # Track immediately: a failed write can leave a partial file.
                    created.append(path)
                    stream.write(text)
                    stream.flush()
                    os.fsync(stream.fileno())
        check_scaffold_paths(root, force=force)
        os.replace(temporary, manifest_path)
    except Exception as exc:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)
        for path in reversed(created):
            with suppress(OSError):
                path.unlink()
        if created_dotdir:
            with suppress(OSError):
                dotdir.rmdir()
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
        if isinstance(exc, (OSError, UnicodeError)):
            raise UserError(
                "cannot create reprollm.yaml scaffold; check project permissions and retry"
            ) from exc
        raise
    return ScaffoldResult(True, auxiliary[0][0] in created, auxiliary[1][0] in created)


def parse_scalar(field_path: str, answer: str) -> Any:
    """Interactive answers: numbers for numeric fields, strings otherwise."""
    text = answer.strip().strip("'\"")
    if field_path in _NUMERIC_FIELDS:
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text
    return text
