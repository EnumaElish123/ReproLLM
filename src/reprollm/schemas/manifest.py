"""Manifest schema (spec §3): ``reprollm.yaml`` is declared intent.

Design note on required-ness: beyond V-01 (``project.name``, ``experiment.profiles``)
the schema enforces *types, enums, patterns, ranges, paths, and unknown-key rejection*
(``extra="forbid"``). Presence of experimental content (model ids, seeds, metrics, …)
is deliberately **not** enforced here: it is the job of the Level 1 presence rules
(spec §12) so that ``reprollm init`` scaffolding and partially-filled manifests load
and produce actionable findings instead of exit 2. This matches the spec's own rule
catalog, which FAILs on absent fields.
"""

from __future__ import annotations

import re
import types
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

_UNION_ORIGINS = (Union, getattr(types, "UnionType", Union))

SchemaVersion = Literal[1]

#: Role keys and profile names share the same identifier grammar (spec §6).
RoleKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,31}$")]
ProfileName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,31}$")]

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def _check_rel_path(value: str) -> str:
    """V-03: relative POSIX path, no ``..``, no leading ``/``, no drive letter."""
    if not value or not value.strip():
        raise ValueError("path must not be empty")
    if value.startswith("/") or value.startswith("\\"):
        raise ValueError(f"path {value!r} must be relative (POSIX style), not absolute")
    if _DRIVE_RE.match(value):
        raise ValueError(f"path {value!r} must not contain a drive letter")
    if "\\" in value:
        raise ValueError(f"path {value!r} must use POSIX '/' separators")
    if any(part == ".." for part in value.split("/")):
        raise ValueError(f"path {value!r} must not contain '..' segments")
    return value


RelPath = Annotated[str, AfterValidator(_check_rel_path)]


class Paper(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    url: str | None = None
    doi: str | None = None


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    description: str | None = None
    paper: Paper | None = None


class Experiment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    profiles: list[ProfileName]


class TokenizerSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    revision: str | None = None


class ChatTemplateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: RelPath


class EndpointSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str | None = None
    api_version: str | None = None


class AdapterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["peft", "other"]
    id: str
    revision: str | None = None
    type: Literal["lora", "qlora", "ia3", "other"]
    rank: int | None = None
    alpha: float | None = None
    dropout: float | None = None
    target_modules: list[str] | None = None


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: (
        Literal["huggingface", "openai", "openrouter", "anthropic", "local", "other"] | None
    ) = None
    id: str | None = None
    revision: str | None = None
    tokenizer: TokenizerSpec | None = None
    dtype: str | None = None
    quantization: str | None = None
    adapter: AdapterSpec | None = None
    trust_remote_code: bool | None = None
    chat_template: ChatTemplateSpec | None = None
    endpoint: EndpointSpec | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class PreprocessingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script: RelPath | None = None
    description: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class SamplingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int | None = None
    method: str | None = None
    seed: int | None = None


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["huggingface", "local", "other"] | None = None
    id: str | None = None
    revision: str | None = None
    subset: str | None = None
    split: str | None = None
    files: list[RelPath] | None = None
    preprocessing: PreprocessingSpec | None = None
    sampling: SamplingSpec | None = None


class FewShotSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: RelPath | None = None
    n: int | None = None


class PromptSpec(BaseModel):
    """A prompt role; at most one of ``path`` / ``text`` (V-04).

    Both ``None`` is the ``init``-scaffolding "TODO" state and loads fine; the
    ``prompt.*`` rules report the missing content.
    """

    model_config = ConfigDict(extra="forbid")

    path: RelPath | None = None
    text: str | None = None
    format: Literal["jinja", "fstring", "plain"] | None = None
    few_shot: FewShotSpec | None = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> PromptSpec:
        if self.path is not None and self.text is not None:
            raise ValueError("prompts.<role> must set only one of 'path' or 'text' (both are set)")
        return self


class Generation(BaseModel):
    """Generation parameters. V-08 ranges are enforced when values are present."""

    model_config = ConfigDict(extra="forbid")

    temperature: float | None = Field(None, ge=0, le=2)
    top_p: float | None = Field(None, gt=0, le=1)
    top_k: int | None = None
    max_tokens: int | None = Field(None, ge=1)
    seed: int | None = None
    do_sample: bool | None = None
    stop: list[str] | None = None
    repetition_penalty: float | None = None
    n: int | None = None


class Inference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["vllm", "transformers", "sglang", "openai", "other"] | None = None
    version: str | None = None
    mode: Literal["offline", "serving"] | None = None
    dtype: str | None = None
    tensor_parallel_size: int | None = None
    gpu_memory_utilization: float | None = Field(None, gt=0, le=1)
    quantization: str | None = None
    max_model_len: int | None = None
    kv_cache_dtype: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class DeepSpeedSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: RelPath


class Training(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["full", "lora", "qlora", "other"] | None = None
    learning_rate: float | None = None
    optimizer: str | None = None
    scheduler: str | None = None
    batch_size: int | None = None
    gradient_accumulation: int | None = None
    epochs: int | None = None
    max_steps: int | None = None
    precision: str | None = None
    seed: int | None = None
    deepspeed: DeepSpeedSpec | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class MetricSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    implementation: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class JudgeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature: float | None = Field(None, ge=0, le=2)
    top_p: float | None = Field(None, gt=0, le=1)
    max_tokens: int | None = Field(None, ge=1)
    seed: int | None = None


class JudgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_ref: str = "judge"
    prompt_ref: str = "judge"
    params: JudgeParams = Field(default_factory=JudgeParams)
    repetitions: int | None = None
    parser: str | None = None


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[MetricSpec] = Field(default_factory=list)
    aggregation: str | None = None
    repetitions: int | None = None
    thresholds: dict[str, float] | None = None
    definitions: dict[str, str] | None = None
    query_budget: int | None = None
    judge: JudgeSpec | None = None


class MechanismSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class AttackSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    query_budget: int | None = None


class Privacy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threat_model: str | None = None
    mechanism: MechanismSpec | None = None
    metrics: list[str] | None = None
    attack: AttackSpec | None = None


class Execution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str | None = None
    cwd: RelPath | None = None
    seed: int | None = None
    config_files: list[RelPath] | None = None
    env_requirements: list[str] | None = None


class BindingSpec(BaseModel):
    """Runtime locations of a manifest field (D-40, spec §15)."""

    model_config = ConfigDict(extra="forbid")

    cli: str | None = None
    config: str | None = None
    env: str | None = None


class Artifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outputs: list[RelPath] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Manifest(BaseModel):
    """``reprollm.yaml`` — what the researcher intends to run (D-13)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: SchemaVersion = 1
    project: Project
    experiment: Experiment
    models: dict[RoleKey, ModelSpec] = Field(default_factory=dict)
    datasets: dict[RoleKey, DatasetSpec] = Field(default_factory=dict)
    prompts: dict[RoleKey, PromptSpec] = Field(default_factory=dict)
    generation: Generation | None = None
    inference: Inference | None = None
    training: Training | None = None
    evaluation: Evaluation | None = None
    privacy: Privacy | None = None
    execution: Execution | None = None
    bindings: dict[str, BindingSpec] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    artifacts: Artifacts | None = None

    @model_validator(mode="after")
    def _cross_field_checks(self) -> Manifest:
        self._check_core_not_declared()
        self._check_judge_refs()
        self._check_local_model_paths()
        self._check_binding_paths()
        return self

    def _check_core_not_declared(self) -> None:
        if "core" in self.experiment.profiles:
            raise ValueError(
                "experiment.profiles must not list 'core'; it is always included implicitly"
            )

    def _check_judge_refs(self) -> None:
        judge = self.evaluation.judge if self.evaluation is not None else None
        if judge is None:
            return
        if judge.model_ref not in self.models:
            raise ValueError(
                f"evaluation.judge.model_ref {judge.model_ref!r} does not reference a key "
                f"in models (found: {sorted(self.models) or 'none'})"
            )
        if judge.prompt_ref not in self.prompts:
            raise ValueError(
                f"evaluation.judge.prompt_ref {judge.prompt_ref!r} does not reference a key "
                f"in prompts (found: {sorted(self.prompts) or 'none'})"
            )

    def _check_local_model_paths(self) -> None:
        for role, spec in self.models.items():
            if spec.provider == "local":
                if spec.id is None:
                    raise ValueError(
                        f"models.{role}.provider is 'local', which requires "
                        f"models.{role}.id to be a relative path"
                    )
                try:
                    _check_rel_path(spec.id)
                except ValueError as exc:
                    raise ValueError(f"models.{role}.id: {exc}") from exc

    def _check_binding_paths(self) -> None:
        for path in self.bindings:
            try:
                validate_field_path(path)
            except ValueError as exc:
                raise ValueError(f"bindings key {path!r}: {exc}") from exc


# ---------------------------------------------------------------------------
# Field-path validation (V-06, reused by project rules §7)
# ---------------------------------------------------------------------------

#: Fields whose subtree is free-form: paths below them are accepted as-is.
_FREE_FORM_FIELDS = {"params", "metadata"}


def _peel_annotation(annotation: Any) -> Any:
    """Strip Annotated wrappers and Optional[...] (PEP 604 and typing.Union)."""
    while hasattr(annotation, "__metadata__"):
        annotation = get_args(annotation)[0]
    if get_origin(annotation) in _UNION_ORIGINS:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            annotation = args[0]
            while hasattr(annotation, "__metadata__"):
                annotation = get_args(annotation)[0]
    return annotation


def _is_leaf(annotation: Any) -> bool:
    """True when the annotation holds scalar values (a valid binding target)."""
    origin = get_origin(annotation)
    if annotation is Any or annotation is None or annotation is object:
        return True
    if origin is Literal:
        return True
    if annotation in (str, int, float, bool):
        return True
    if origin is list:
        return True
    if origin is dict:
        _, value_ann = get_args(annotation)
        return _is_leaf(_peel_annotation(value_ann))
    return False


def _is_model(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def validate_field_path(path: str) -> None:
    """Validate a dotted field path against the flattened Manifest schema (V-06).

    Wildcards are rejected. Paths descending into a free-form block (``custom.*``,
    ``*.params.*``, ``artifacts.metadata.*``) are accepted without structural
    validation. Raises ``ValueError`` with an actionable message otherwise.
    """
    if not path:
        raise ValueError("field path must not be empty")
    if "*" in path:
        raise ValueError(f"wildcards are not allowed in field paths (got {path!r})")
    segments = path.split(".")
    if any(not segment for segment in segments):
        raise ValueError(f"field path {path!r} contains an empty segment")

    model: type[BaseModel] | None = Manifest
    i = 0
    n = len(segments)
    while i < n:
        segment = segments[i]
        if model is None:
            return  # inside a free-form tail
        if segment in _FREE_FORM_FIELDS and segment in model.model_fields:
            return  # everything below a free-form field is accepted as-is
        if segment == "custom" and model is Manifest:
            return  # top-level free-form block; any tail is accepted
        fields = model.model_fields
        if segment not in fields:
            raise ValueError(
                f"unknown field {segment!r} in {model.__name__} "
                f"(valid fields: {', '.join(sorted(fields))})"
            )
        annotation = _peel_annotation(fields[segment].annotation)
        is_last = i == n - 1
        origin = get_origin(annotation)
        if _is_model(annotation):
            if is_last:
                raise ValueError(
                    f"field path {path!r} targets the section '{segment}', not a field"
                )
            model = annotation
            i += 1
            continue
        if origin is dict:
            key_type, value_ann = get_args(annotation)
            del key_type
            value_ann = _peel_annotation(value_ann)
            if _is_model(value_ann):
                if is_last:
                    raise ValueError(
                        f"field path {path!r} targets the map '{segment}', not a field"
                    )
                if i + 1 >= n:
                    raise ValueError(f"field path {path!r} ends on a map key")
                model = value_ann
                i += 2  # consume the map key segment
                continue
            if not is_last:
                raise ValueError(f"field path {path!r} has segments after the field '{segment}'")
            return
        if not is_last:
            raise ValueError(f"field path {path!r} has segments after the field '{segment}'")
        return
    if model is not None:
        raise ValueError(f"field path {path!r} ends on a section or map key, not a field")
