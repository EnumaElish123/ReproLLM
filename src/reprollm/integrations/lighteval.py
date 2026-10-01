"""lighteval integration (M11-T01)."""

from __future__ import annotations

from reprollm.core.envinfo import installed_versions
from reprollm.core.pyscan import PyScanResult
from reprollm.core.scanner import RepoScanner
from reprollm.integrations._static import (
    cli_evidence,
    import_evidence,
    scalar_string,
    task_mapping,
)
from reprollm.integrations.base import TaskHints
from reprollm.schemas.finding import Evidence


class LightEvalIntegration:
    name = "lighteval"

    def detect(self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None) -> list[Evidence]:
        evidence = import_evidence(scanner, self.name, pyscan)
        evidence.extend(cli_evidence(scanner, (("lighteval",),), module=self.name))
        return evidence

    def capture(self) -> dict[str, str]:
        versions = installed_versions(["lighteval"])
        return {"lighteval": versions.get("lighteval", "not installed")}

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints:
        task_names: list[str] = []
        for path in scanner.files():
            if not path.endswith((".yaml", ".yml")):
                continue
            data = task_mapping(scanner, path)
            task = scalar_string(data.get("task")) if data is not None else None
            if task:
                task_names.append(task)
        return TaskHints(task_names=sorted(set(task_names)))
