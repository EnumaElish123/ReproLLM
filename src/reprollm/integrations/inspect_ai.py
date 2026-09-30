"""inspect-ai integration (M11-T01).

Detects usage via imports; extracts task names from ``@task`` decorated
functions in Python source. Never imports the library.
"""

from __future__ import annotations

import ast
import re

from reprollm.core.envinfo import installed_versions
from reprollm.core.scanner import RepoScanner
from reprollm.integrations.base import TaskHints
from reprollm.schemas.finding import Evidence

_IMPORTS = ("inspect_ai",)


class InspectAIIntegration:
    name = "inspect_ai"

    def detect(self, scanner: RepoScanner) -> list[Evidence]:
        evidence: list[Evidence] = []
        for path in scanner.python_files():
            text = scanner.read_text(path)
            if text is None:
                continue
            if any(f"import {mod}" in text or f"from {mod}" in text for mod in _IMPORTS):
                evidence.append(Evidence(kind="detection", path=path, note="import inspect_ai"))
        for path in scanner.files():
            if path.endswith(".sh") or path == "Makefile":
                text = scanner.read_text(path)
                if text and "inspect eval" in text:
                    evidence.append(Evidence(kind="detection", path=path, note="CLI: inspect eval"))
        return evidence

    def capture(self) -> dict[str, str]:
        versions = installed_versions(["inspect_ai"])
        return {"inspect_ai": versions.get("inspect_ai", "not installed")}

    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints:
        task_names: list[str] = []
        for path in scanner.python_files():
            text = scanner.read_text(path)
            if text is None or "inspect_ai" not in text:
                continue
            task_names.extend(_task_decorated_functions(text))
        return TaskHints(task_names=sorted(set(task_names)))


def _task_decorated_functions(text: str) -> list[str]:
    """Names of functions carrying a bare ``@task`` or ``@task(...)`` decorator."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _task_regex(text)
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(target, ast.Name) and target.id == "task":
                names.append(node.name)
                break
            if isinstance(target, ast.Attribute) and target.attr == "task":
                names.append(node.name)
                break
    return names


def _task_regex(text: str) -> list[str]:
    """Fallback for files ast cannot parse."""
    return re.findall(r"@task(?:\(|\s*\n)\s*def\s+(\w+)", text)
