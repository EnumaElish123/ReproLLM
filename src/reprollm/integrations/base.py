"""Integration protocol: detect, capture, task hints (spec §14, M11-T01).

Integrations never import their target library (D-30); they detect usage
patterns, extract task names for `init` pre-filling, and report installed
versions via `importlib.metadata`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from reprollm.core.scanner import RepoScanner
from reprollm.schemas.finding import Evidence


@dataclass(frozen=True)
class TaskHints:
    """Task names extracted from framework config files, for init pre-fill."""

    task_names: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)


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

    def detect(self, scanner: RepoScanner) -> list[Evidence]: ...

    def capture(self) -> dict[str, str]: ...

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints: ...
