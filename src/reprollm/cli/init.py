"""``reprollm init`` — scaffold ``reprollm.yaml`` from detected signals (spec §3.2).

The manifest is rendered from a Jinja template (comments preserved), never
dumped from a model. Required fields of the selected profiles become ``TODO``
keys; null values are allowed so the result loads and audits immediately.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any

import jinja2
import typer

from reprollm.core.context import AuditContext
from reprollm.core.errors import UserError
from reprollm.core.paths import MANIFEST
from reprollm.profiles import loader
from reprollm.schemas.finding import DetectionResult

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
    rendered = template.render(
        project_name=project_name,
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
) -> list[dict[str, Any]]:
    trees: dict[str, dict[str, Any]] = {}
    commented: dict[str, list[str]] = {}

    for field_path in required_fields:
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
                    comment=f"detected: {path}:{line}",
                    todo=False,
                    extra=[f"also detected: {p}:{ln}" for _v, p, ln in other_detections],
                )
            else:
                node[parts[-1]] = _leaf()
        elif field_path in _LIST_FIELDS:
            node[parts[-1]] = _leaf(
                value="[]", comment="TODO: list of {name, implementation}", todo=False
            )
        else:
            provided = values.get(field_path)
            node[parts[-1]] = _leaf(value=provided, todo=provided is None)

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


def _prompt_required(
    required_fields: list[str],
    values: dict[str, Any],
) -> None:
    """--interactive: prompt for every scalar required field (empty keeps null)."""
    for field_path in required_fields:
        if field_path == "project.name":
            continue  # already set from the directory name
        if field_path in _COMMENTED_FIELDS or field_path in _LIST_FIELDS:
            typer.echo(f"  {field_path}: edit manually in reprollm.yaml")
            continue
        current = values.get(field_path)
        answer = typer.prompt(
            f"  {field_path}",
            default=str(current) if current is not None else "",
            show_default=current is not None,
        )
        if str(answer).strip():
            values[field_path] = _parse_scalar(field_path, str(answer))
        else:
            values[field_path] = current


def init(
    path: Annotated[Path, typer.Argument(help="Directory to initialize (default: .)")] = Path("."),
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing manifest.")] = False,
    interactive: Annotated[
        bool, typer.Option("--interactive", help="Prompt for required fields.")
    ] = False,
    profiles: Annotated[
        str | None,
        typer.Option("--profiles", help="Comma-separated profile names (default: detected)."),
    ] = None,
) -> None:
    """Create reprollm.yaml and .reprollm/ from detected experiment signals."""
    root = path.resolve()
    manifest_path = root / MANIFEST
    if manifest_path.exists() and not force:
        raise UserError(
            f"{manifest_path} already exists; pass --force to overwrite it "
            "(files under .reprollm/ are never overwritten)"
        )

    ctx = AuditContext(root, level=0)
    detection = ctx.detection

    if profiles is not None:
        profile_list = [name.strip() for name in profiles.split(",") if name.strip()]
        if not profile_list:
            raise UserError("--profiles requires at least one profile name")
    else:
        profile_list = [
            entry.profile
            for entry in detection.profiles
            if entry.shipped and entry.confidence in {"high", "medium"}
        ]

    resolved = loader.resolve(profile_list, root)  # validates names and rule IDs
    required_fields = resolved.required_fields

    values: dict[str, Any] = {}
    if interactive:
        _prompt_required(required_fields, values)

    manifest_text = build_manifest_text(
        project_name=root.name,
        profiles=profile_list,
        required_fields=required_fields,
        detection=detection,
        values=values,
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    dotdir = root / ".reprollm"
    dotdir.mkdir(parents=True, exist_ok=True)
    config_path = dotdir / "config.yaml"
    if not config_path.exists():
        config_path.write_text(_config_template_text(), encoding="utf-8")
    project_rules_path = dotdir / "project-rules.yaml"
    if not project_rules_path.exists():
        project_rules_path.write_text(_PROJECT_RULES_TEMPLATE, encoding="utf-8")

    # The generated manifest must load; fail loudly instead of leaving a broken file.
    from reprollm.core.yaml_io import load_manifest

    try:
        load_manifest(manifest_path)
    except UserError as exc:
        manifest_path.unlink(missing_ok=True)
        raise UserError(f"generated manifest failed validation (bug): {exc}") from exc

    if profile_list:
        typer.echo(
            f"Created {manifest_path} (profiles: {', '.join(profile_list)}; "
            f"{len(required_fields)} required fields to fill)"
        )
    else:
        typer.echo(
            f"Created {manifest_path} (no profiles detected; "
            "pass --profiles or edit experiment.profiles)"
        )
    typer.echo("Next: fill the TODO fields, then run `reprollm audit .`")
