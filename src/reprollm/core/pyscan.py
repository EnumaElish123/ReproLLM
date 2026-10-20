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

from reprollm.core import scanner as scanner_mod
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


@dataclass(frozen=True)
class EndpointInfo:
    """An endpoint's provider and source location; never retain its URL or key."""

    provider: str
    path: str
    line: int


@dataclass(frozen=True)
class PythonCandidateCoverage:
    """Coverage of the captured primary-Python candidate view, not the repository."""

    observed: bool
    candidate_count: int
    selected_count: int
    parsed_count: int
    file_limit: int

    def pass_skip_reason(self) -> str | None:
        if not self.observed or not (
            0 <= self.parsed_count <= self.selected_count <= self.candidate_count
            and self.file_limit >= 0
            and self.selected_count <= self.file_limit
        ):
            return "Python candidate coverage is unavailable; no rule-wide PASS is established."
        if self.parsed_count == self.candidate_count:
            return None
        return (
            f"Python candidate analysis incomplete: parsed {self.parsed_count} of "
            f"{self.candidate_count} candidate files; selected {self.selected_count} "
            f"(limit {self.file_limit}); no rule-wide PASS is established."
        )


@dataclass
class PyScanResult:
    imports: list[ImportInfo] = field(default_factory=list)
    hf_ids: list[HfIdHint] = field(default_factory=list)
    endpoints: list[EndpointInfo] = field(default_factory=list)
    trust_remote_code: bool = False
    trainer_import: bool = False
    warnings: list[str] = field(default_factory=list)
    python_candidate_count: int = 0
    python_selected_count: int = 0
    python_parsed_count: int = 0
    python_file_limit: int = 0
    coverage_observed: bool = False

    def coverage(self) -> PythonCandidateCoverage:
        return PythonCandidateCoverage(
            observed=self.coverage_observed,
            candidate_count=self.python_candidate_count,
            selected_count=self.python_selected_count,
            parsed_count=self.python_parsed_count,
            file_limit=self.python_file_limit,
        )

    def file_limit_diagnostic(self) -> str | None:
        if self.python_candidate_count <= self.python_file_limit:
            return None
        omitted = self.python_candidate_count - self.python_selected_count
        skipped = self.python_selected_count - self.python_parsed_count
        skipped_text = f"{skipped} selected files were not parsed. " if skipped else ""
        return (
            f"Python analysis incomplete: parsed {self.python_parsed_count} of "
            f"{self.python_candidate_count} candidate files; selected "
            f"{self.python_selected_count} (limit {self.python_file_limit}), "
            f"omitted {omitted}. {skipped_text}"
            "Missing signals may be in unanalysed files."
        )

    def module_names(self) -> set[str]:
        """Full dotted names plus their top-level segments."""
        names: set[str] = set()
        for info in self.imports:
            names.add(info.module)
            names.add(info.module.split(".", 1)[0])
        return names


def scan_python(scanner: RepoScanner) -> PyScanResult:
    candidate_count = sum(path.endswith(".py") for path in scanner.analysis_files())
    file_limit = scanner_mod.MAX_PYTHON_FILES
    selected = scanner.python_files()
    result = PyScanResult(
        python_candidate_count=candidate_count,
        python_selected_count=len(selected),
        python_file_limit=file_limit,
    )
    for path in selected:
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
        result.python_parsed_count += 1
        _scan_tree(tree, path, result)
    diagnostic = result.file_limit_diagnostic()
    if diagnostic is not None:
        result.warnings.append(diagnostic)
    result.hf_ids.sort(key=lambda hint: (hint.path, hint.line, hint.value))
    result.imports.sort(key=lambda info: (info.path, info.line, info.module))
    result.endpoints.sort(key=lambda info: (info.path, info.line, info.provider))
    result.coverage_observed = True
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
        elif (
            keyword.arg == "base_url"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
            and "openrouter.ai" in keyword.value.value.lower()
        ):
            result.endpoints.append(
                EndpointInfo(provider="openrouter", path=path, line=keyword.value.lineno)
            )

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
