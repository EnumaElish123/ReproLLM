"""Python AST scanning (M2-T03 imports, extended in M2-T04 for detection).

Deterministic static analysis only: imports, HF repo-id string constants in
``from_pretrained``/``LLM(model=…)`` calls, ``trust_remote_code=True`` keyword
arguments, and Transformers trainer imports. Files over the read cap or with
syntax errors are skipped with a warning — never a crash.
"""

from __future__ import annotations

import ast
import re
import warnings
from dataclasses import dataclass, field

from reprollm.core.scanner import RepoScanner
from reprollm.schemas.finding import HfIdHint

#: ``org/name`` style identifiers (spec §13).
HF_ID_RE = re.compile(r"^[\w.-]+/[\w.-]+$")

_TRAINER_NAMES = {"Trainer", "Seq2SeqTrainer", "TrainingArguments"}


@dataclass(frozen=True)
class ImportInfo:
    module: str
    path: str
    line: int


@dataclass
class PyScanResult:
    imports: list[ImportInfo] = field(default_factory=list)
    hf_ids: list[HfIdHint] = field(default_factory=list)
    trust_remote_code: bool = False
    trainer_import: bool = False
    warnings: list[str] = field(default_factory=list)

    def module_names(self) -> set[str]:
        """Full dotted names plus their top-level segments."""
        names: set[str] = set()
        for info in self.imports:
            names.add(info.module)
            names.add(info.module.split(".", 1)[0])
        return names


def scan_python(scanner: RepoScanner) -> PyScanResult:
    result = PyScanResult()
    for path in scanner.python_files():
        text = scanner.read_text(path)
        if text is None:
            result.warnings.append(f"{path}: unreadable or over the size cap; skipped")
            continue
        try:
            # Target-repo code may emit SyntaxWarnings (e.g. invalid escapes);
            # they belong in our warnings list, not on the user's stdout.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text, filename=path)
        except SyntaxError as exc:
            result.warnings.append(f"{path}:{exc.lineno or 0}: syntax error; skipped")
            continue
        _scan_tree(tree, path, result)
    result.hf_ids.sort(key=lambda hint: (hint.path, hint.line, hint.value))
    result.imports.sort(key=lambda info: (info.path, info.line, info.module))
    return result


def _scan_tree(tree: ast.AST, path: str, result: PyScanResult) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append(ImportInfo(alias.name, path, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                result.imports.append(ImportInfo(node.module, path, node.lineno))
                if node.module == "transformers" and any(
                    alias.name in _TRAINER_NAMES for alias in node.names
                ):
                    result.trainer_import = True
        elif isinstance(node, ast.Call):
            _scan_call(node, path, result)


def _scan_call(node: ast.Call, path: str, result: PyScanResult) -> None:
    for keyword in node.keywords:
        if keyword.arg == "trust_remote_code" and _is_true(keyword.value):
            result.trust_remote_code = True

    func = node.func
    name = (
        func.attr
        if isinstance(func, ast.Attribute)
        else (func.id if isinstance(func, ast.Name) else None)
    )
    if name == "from_pretrained" and node.args:
        hint = _string_const(node.args[0])
        if hint is not None:
            result.hf_ids.append(HfIdHint(value=hint, path=path, line=node.lineno))
    elif name == "LLM":
        for keyword in node.keywords:
            if keyword.arg == "model":
                hint = _string_const(keyword.value)
                if hint is not None:
                    result.hf_ids.append(HfIdHint(value=hint, path=path, line=node.lineno))


def _string_const(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.strip()
        return value if HF_ID_RE.match(value) else None
    return None


def _is_true(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is True
