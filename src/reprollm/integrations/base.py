"""Integration protocol: detect, capture, task hints (spec §14, M11-T01).

Integrations never import their target library (D-30); they detect usage
patterns, extract task names for `init` pre-filling, and report installed
versions via `importlib.metadata`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from reprollm.core.scanner import RepoScanner
from reprollm.schemas.finding import Evidence

if TYPE_CHECKING:
    import httpx

    from reprollm.core.pyscan import PyScanResult
    from reprollm.schemas.lock import AdapterLock, DatasetLock, InferenceLock, ModelLock
    from reprollm.schemas.manifest import Manifest


@dataclass(frozen=True)
class TaskHints:
    """Task names extracted from framework config files, for init pre-fill."""

    task_names: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LockFragment:
    """Internal provider results; not a persisted document or exported schema."""

    models: dict[str, ModelLock] = field(default_factory=dict)
    datasets: dict[str, DatasetLock] = field(default_factory=dict)
    adapters: dict[str, AdapterLock] = field(default_factory=dict)
    inference: InferenceLock | None = None


class ProviderIntegration:
    """Shared context and optional capabilities for provider integrations."""

    def __init__(self, root: Path | None = None, *, now: datetime | None = None) -> None:
        self.root = root if root is not None else Path(".")
        self.now = now if now is not None else datetime.now(timezone.utc).replace(microsecond=0)

    def capture(self) -> dict[str, str]:
        return {}

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints:
        return TaskHints()


@runtime_checkable
class ResolverIntegration(Protocol):
    """Optional resolution capability; evaluation frameworks need not implement it."""

    name: str

    def resolve(
        self, manifest: Manifest, *, offline: bool, http: httpx.Client | None
    ) -> LockFragment: ...


@runtime_checkable
class Integration(Protocol):
    """A framework or provider integration (spec §14).

    ``detect`` returns Evidence when the framework is in use; ``capture``
    returns installed package versions; ``extract_task_hints`` pulls task
    names from framework config files so `init` can pre-fill
    ``evaluation.metrics[].name``. Implementations MUST NOT import the
    target library.
    """

    name: str

    def detect(
        self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None
    ) -> list[Evidence]: ...

    def capture(self) -> dict[str, str]: ...

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints: ...
