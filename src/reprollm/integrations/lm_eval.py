"""lm-evaluation-harness integration (M11-T01).

Detects usage via imports and CLI entry points; extracts task names from
``lm_eval/tasks/**/*.yaml`` (``task:`` field) for `init` pre-filling. Never
imports the library.
"""

from __future__ import annotations

from reprollm.core.envinfo import installed_versions
from reprollm.core.scanner import RepoScanner
from reprollm.integrations.base import TaskHints
from reprollm.schemas.finding import Evidence

#: Import module names that indicate lm-eval usage.
_IMPORTS = ("lm_eval",)

#: Directories where lm-eval task YAMLs live.
_TASK_DIRS = ("lm_eval/tasks", "tasks", "lm_eval/tasks/")


class LmEvalIntegration:
    name = "lm_eval"

    def detect(self, scanner: RepoScanner) -> list[Evidence]:
        evidence: list[Evidence] = []
        for path in scanner.python_files():
            text = scanner.read_text(path)
            if text is None:
                continue
            if any(f"import {mod}" in text or f"from {mod}" in text for mod in _IMPORTS):
                evidence.append(Evidence(kind="detection", path=path, note="import lm_eval"))
        # CLI entry: lm_eval or python -m lm_eval
        for path in scanner.files():
            if path.endswith((".sh",)) or path == "Makefile":
                text = scanner.read_text(path)
                if text and ("lm_eval " in text or "lm-eval " in text):
                    evidence.append(Evidence(kind="detection", path=path, note="CLI: lm_eval"))
        return evidence

    def capture(self) -> dict[str, str]:
        versions = installed_versions(["lm_eval"])
        return {"lm_eval": versions.get("lm_eval", "not installed")}

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints:
        import yaml

        task_names: list[str] = []
        metrics: list[str] = []
        for path in scanner.files():
            if not any(
                path.startswith(d.rstrip("/")) and path.endswith(".yaml") for d in _TASK_DIRS
            ):
                continue
            text = scanner.read_text(path)
            if text is None:
                continue
            try:
                data = yaml.safe_load(text)
            except Exception:  # noqa: BLE001 - malformed task YAML is skipped
                continue
            if not isinstance(data, dict):
                continue
            task = data.get("task")
            if isinstance(task, str) and task:
                task_names.append(task)
            for entry in data.get("metric_list") or []:
                if isinstance(entry, dict) and isinstance(entry.get("metric"), str):
                    metric = entry["metric"]
                    if metric not in metrics:
                        metrics.append(metric)
        return TaskHints(task_names=sorted(set(task_names)), metrics=sorted(set(metrics)))
