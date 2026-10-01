"""lm-evaluation-harness integration (M11-T01).

Detects usage via imports and CLI entry points; extracts task names from
``lm_eval/tasks/**/*.yaml`` (``task:`` field) for `init` pre-filling. Never
imports the library.
"""

from __future__ import annotations

from collections.abc import Iterator

from yaml.nodes import MappingNode, Node, SequenceNode

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

#: Directories where lm-eval task YAMLs live.
_TASK_DIRS = ("lm_eval/tasks/", "tasks/")


class LmEvalIntegration:
    name = "lm_eval"

    def detect(self, scanner: RepoScanner, *, pyscan: PyScanResult | None = None) -> list[Evidence]:
        evidence = import_evidence(scanner, self.name, pyscan)
        evidence.extend(cli_evidence(scanner, (("lm_eval",), ("lm-eval",)), module=self.name))
        if not evidence:
            for path, data in self._task_configs(scanner):
                if scalar_string(data.get("task")) and any(
                    key in data for key in ("dataset_path", "metric_list", "include")
                ):
                    evidence.append(Evidence(kind="detection", path=path, note="lm_eval task YAML"))
                    break
        return evidence

    def capture(self) -> dict[str, str]:
        versions = installed_versions(["lm_eval"])
        return {"lm_eval": versions.get("lm_eval", "not installed")}

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints:
        task_names: list[str] = []
        metrics: list[str] = []
        for _path, data in self._task_configs(scanner):
            task = scalar_string(data.get("task"))
            if task:
                task_names.append(task)
            entries = data.get("metric_list")
            if not isinstance(entries, SequenceNode):
                continue
            for entry in entries.value:
                if not isinstance(entry, MappingNode):
                    continue
                for key, value in entry.value:
                    metric = scalar_string(value)
                    if scalar_string(key) == "metric" and metric:
                        metrics.append(metric)
        return TaskHints(task_names=sorted(set(task_names)), metrics=sorted(set(metrics)))

    @staticmethod
    def _task_configs(scanner: RepoScanner) -> Iterator[tuple[str, dict[str, Node]]]:
        for path in scanner.files():
            if not any(
                path.startswith(directory) and path.endswith((".yaml", ".yml"))
                for directory in _TASK_DIRS
            ):
                continue
            data = task_mapping(scanner, path)
            if data is not None:
                yield path, data
