"""Lock schema (spec §4): ``reprollm.lock`` — resolved reality with provenance.

Written only by ``reprollm lock``. Only *resolved* fields carry a :class:`Provenance`
object; declared fields pass through unchanged. Passthrough sections reuse the manifest
models so the two documents cannot drift apart.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .manifest import (
    Generation,
    Privacy,
    SchemaVersion,
    Training,
)


class Confidence(str, Enum):
    EXACT = "exact"
    DECLARED = "declared"
    UNRESOLVED = "unresolved"


class Provenance(BaseModel):
    """A resolved value: where it came from and how certain it is (spec §4.1)."""

    model_config = ConfigDict(extra="forbid")

    value: object | None = None
    source: str
    confidence: Confidence
    resolved_at: datetime | None = None
    note: str | None = None


class ResolutionMode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["online", "offline"]


class TokenizerLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    revision: Provenance


class ChatTemplateLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: Provenance
    status: Literal["present", "absent", "custom_file"]


class AdapterLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    revision: Provenance
    config_sha256: Provenance | None = None


class WeightsLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hashed: bool
    total_size_bytes: int
    sha256: str | None = None


class LocalModelLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    config_sha256: Provenance | None = None
    weights: WeightsLock


class ModelLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    id: str
    pinnability: Literal["exact", "snapshot_alias", "unpinnable"]
    revision: Provenance
    observed_at: datetime | None = None
    tokenizer: TokenizerLock | None = None
    chat_template: ChatTemplateLock | None = None
    config_sha256: Provenance | None = None
    adapter: AdapterLock | None = None
    local: LocalModelLock | None = None
    dtype: str | None = None
    quantization: str | None = None
    trust_remote_code: bool | None = None


class ContentFingerprint(BaseModel):
    """D-22: dataset content fingerprints are not computed in Beta."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["not_computed"] = "not_computed"


class DatasetFileLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    size_bytes: int


class DatasetLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    id: str
    revision: Provenance
    subset: str | None = None
    split: str | None = None
    content_fingerprint: ContentFingerprint = Field(default_factory=ContentFingerprint)
    files: list[DatasetFileLock] | None = None


class PromptPathLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    size_bytes: int


class PromptTextLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_sha256: str


class PromptLock(BaseModel):
    """Either a hashed prompt file or a hash of inline text (discriminated by field)."""

    model_config = ConfigDict(extra="forbid")

    path: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    text_sha256: str | None = None


class FileEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    size_bytes: int


class InferenceLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str
    version: Provenance
    mode: Literal["offline", "serving"] | None = None
    dtype: str | None = None
    tensor_parallel_size: int | None = None
    gpu_memory_utilization: float | None = None
    quantization: str | None = None
    max_model_len: int | None = None
    kv_cache_dtype: str | None = None
    params: dict[str, object] = Field(default_factory=dict)


class MetricLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    implementation: str | None = None
    implementation_sha256: str | None = None
    implementation_version: Provenance | None = None


class EvaluationLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[MetricLock] = Field(default_factory=list)
    aggregation: str | None = None
    repetitions: int | None = None
    thresholds: dict[str, float] | None = None
    definitions: dict[str, str] | None = None
    query_budget: int | None = None
    judge: object | None = None


class GpuEnvLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    driver: str | None = None
    cuda_driver_max: str | None = None
    source: Literal["nvidia_smi", "unavailable"]


class EnvironmentLock(BaseModel):
    """Expected environment at lock time (spec §4.2)."""

    model_config = ConfigDict(extra="forbid")

    python: str
    platform: Literal["linux", "darwin", "windows"]
    packages: dict[str, str] = Field(default_factory=dict)
    gpu: GpuEnvLock


class Lock(BaseModel):
    """``reprollm.lock`` (spec §4.2)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    reprollm_version: str
    generated_at: datetime
    manifest_sha256: str
    project_rules_sha256: str | None = None
    resolution: ResolutionMode
    models: dict[str, ModelLock] = Field(default_factory=dict)
    datasets: dict[str, DatasetLock] = Field(default_factory=dict)
    prompts: dict[str, PromptLock] = Field(default_factory=dict)
    files: list[FileEntry] = Field(default_factory=list)
    generation: Generation | None = None
    inference: InferenceLock | None = None
    training: Training | None = None
    evaluation: EvaluationLock | None = None
    privacy: Privacy | None = None
    environment: EnvironmentLock | None = None
