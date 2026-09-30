"""lighteval integration (M11-T01)."""

from __future__ import annotations

from reprollm.core.envinfo import installed_versions
from reprollm.core.scanner import RepoScanner
from reprollm.integrations.base import TaskHints
from reprollm.schemas.finding import Evidence

_IMPORTS = ("lighteval",)


class LightEvalIntegration:
    name = "lighteval"

    def detect(self, scanner: RepoScanner) -> list[Evidence]:
        evidence: list[Evidence] = []
        for path in scanner.python_files():
            text = scanner.read_text(path)
            if text is None:
                continue
            if any(f"import {mod}" in text or f"from {mod}" in text for mod in _IMPORTS):
                evidence.append(Evidence(kind="detection", path=path, note="import lighteval"))
        for path in scanner.files():
            if path.endswith(".sh") or path == "Makefile":
                text = scanner.read_text(path)
                if text and "lighteval " in text:
                    evidence.append(Evidence(kind="detection", path=path, note="CLI: lighteval"))
        return evidence

    def capture(self) -> dict[str, str]:
        versions = installed_versions(["lighteval"])
        return {"lighteval": versions.get("lighteval", "not installed")}

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints:
        import yaml

        task_names: list[str] = []
        for path in scanner.files():
            if not path.endswith(".yaml"):
                continue
            text = scanner.read_text(path)
            if text is None:
                continue
            try:
                data = yaml.safe_load(text)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(data, dict) and isinstance(data.get("task"), str):
                task_names.append(data["task"])
        return TaskHints(task_names=sorted(set(task_names)))
