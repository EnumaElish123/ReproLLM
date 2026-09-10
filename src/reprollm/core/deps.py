"""Dependency-declaration parsing (M2-T03).

Parses ``requirements*.txt``, ``pyproject.toml`` (PEP 621 + Poetry),
``environment.yml`` (conda, incl. embedded ``pip:`` lists), and ``Pipfile``;
detects lockfiles and the packages they pin. Parsers never raise on malformed
input — bad lines are recorded as ``unparsed`` (M2 risk table: a researcher's
requirements file must never crash the audit).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from reprollm.core._toml import tomllib
from reprollm.core.scanner import RepoScanner

#: Distribution-name overrides applied before canonicalization (spec M2-T03).
_NAME_OVERRIDES = {"pytorch": "torch"}

_EXACT_VERSION_RE = re.compile(r"^\d+(\.\d+)*$")


def canonical_dep_name(name: str) -> str:
    return canonicalize_name(_NAME_OVERRIDES.get(name.strip().lower(), name.strip()))


@dataclass(frozen=True)
class DependencyDeclaration:
    name: str  # canonicalized (pytorch → torch)
    display_name: str  # as written
    specifier: str | None
    exact_version: str | None
    source_file: str
    line: int

    @property
    def is_exact(self) -> bool:
        return self.exact_version is not None


@dataclass(frozen=True)
class Lockfile:
    path: str
    packages: frozenset[str]  # canonicalized names


@dataclass
class Declarations:
    declarations: list[DependencyDeclaration] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    lockfiles: list[Lockfile] = field(default_factory=list)
    manifest_present: bool = False


def scan_dependencies(scanner: RepoScanner) -> Declarations:
    result = Declarations()
    files = scanner.files()
    basenames = {Path(p).name: p for p in files}

    pyproject = basenames.get("pyproject.toml")
    requirements = sorted(p for p in files if _is_requirements_name(p))
    environment = basenames.get("environment.yml") or basenames.get("environment.yaml")
    pipfile = basenames.get("Pipfile")

    # A pyproject.toml is only a dependency manifest when it carries a
    # [project] or [tool.poetry] table (spec §12.2, M2F-T03/F-04); parse it
    # once and reuse the qualification below.
    pyproject_qualified = False
    if pyproject:
        pyproject_qualified = _parse_pyproject(pyproject, scanner, result)

    seen_requirements: set[str] = set()
    for path in requirements:
        _parse_requirements(path, scanner, result, seen_requirements)

    if environment:
        _parse_environment(environment, scanner, result)

    if pipfile:
        _parse_pipfile(pipfile, scanner, result)

    result.manifest_present = bool(
        pyproject_qualified
        or requirements
        or environment
        or basenames.get("uv.lock")
        or basenames.get("poetry.lock")
        or pipfile
    )

    _collect_lockfiles(scanner, result, requirements)
    return result


def _is_requirements_name(path: str) -> bool:
    name = Path(path).name
    return name.startswith("requirements") and name.endswith(".txt")


# --- requirements*.txt ------------------------------------------------------


def _parse_requirements(
    path: str, scanner: RepoScanner, result: Declarations, seen: set[str], depth: int = 0
) -> None:
    if path in seen or depth > 10:
        return
    seen.add(path)
    text = scanner.read_text(path)
    if text is None:
        result.unparsed.append(f"{path}:0: unreadable")
        return
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r") or line.startswith("--requirement"):
            parts = line.split(None, 1)
            if len(parts) != 2:
                result.unparsed.append(f"{path}:{lineno}: {line}")
                continue
            target = parts[1].strip()
            base = Path(path).parent
            resolved = (base / target).as_posix() if not target.startswith("/") else target
            _parse_requirements(resolved, scanner, result, seen, depth + 1)
            continue
        if line.startswith("-") or " @ " in line:
            result.unparsed.append(f"{path}:{lineno}: {line}")
            continue
        _add_requirement_line(line, path, lineno, result)


def _add_requirement_line(line: str, path: str, lineno: int, result: Declarations) -> None:
    try:
        req = Requirement(line)
    except Exception:  # noqa: BLE001 - never crash on odd requirements syntax
        result.unparsed.append(f"{path}:{lineno}: {line}")
        return
    specs = list(req.specifier)
    exact = None
    if len(specs) == 1 and specs[0].operator == "==":
        exact = specs[0].version
    result.declarations.append(
        DependencyDeclaration(
            name=canonical_dep_name(req.name),
            display_name=req.name,
            specifier=str(req.specifier) or None,
            exact_version=exact,
            source_file=path,
            line=lineno,
        )
    )


# --- pyproject.toml ---------------------------------------------------------


def _parse_pyproject(path: str, scanner: RepoScanner, result: Declarations) -> bool:
    """Parse once; return True only when a ``[project]`` or ``[tool.poetry]``
    table qualifies the file as a dependency manifest (spec §12.2, M2F-T03)."""
    text = scanner.read_text(path)
    if text is None:
        result.unparsed.append(f"{path}:0: unreadable")
        return False
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        result.unparsed.append(f"{path}:0: {exc}")
        return False
    qualified = isinstance(doc.get("project"), dict) or isinstance(
        (doc.get("tool") or {}).get("poetry"), dict
    )
    if not qualified:
        return False  # tool-only pyproject (e.g. [tool.ruff]) is not a manifest

    project = doc.get("project") or {}
    if isinstance(project, dict):
        deps = project.get("dependencies") or []
        if isinstance(deps, list):
            for lineno, entry in enumerate(deps, start=1):
                if isinstance(entry, str):
                    _add_requirement_line(entry, path, lineno, result)
        optional = project.get("optional-dependencies") or {}
        if isinstance(optional, dict):
            for entries in optional.values():
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, str):
                            _add_requirement_line(entry, path, 0, result)

    poetry = (doc.get("tool") or {}).get("poetry") or {}
    poetry_deps = poetry.get("dependencies") or {}
    if isinstance(poetry_deps, dict):
        for lineno, (name, value) in enumerate(poetry_deps.items(), start=1):
            version = value if isinstance(value, str) else value.get("version")
            exact = None
            specifier = None
            if isinstance(version, str):
                if _EXACT_VERSION_RE.match(version.strip()):
                    exact = version.strip()
                else:
                    specifier = version.strip() or None
            result.declarations.append(
                DependencyDeclaration(
                    name=canonical_dep_name(name),
                    display_name=name,
                    specifier=specifier,
                    exact_version=exact,
                    source_file=path,
                    line=lineno,
                )
            )
    return qualified


# --- environment.yml --------------------------------------------------------


_CONDA_OPERATOR_RE = re.compile(r"[<>=!*/]")


def _parse_environment(path: str, scanner: RepoScanner, result: Declarations) -> None:
    text = scanner.read_text(path)
    if text is None:
        result.unparsed.append(f"{path}:0: unreadable")
        return
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        result.unparsed.append(f"{path}:0: {exc}")
        return
    if not isinstance(doc, dict):
        return
    for lineno, entry in enumerate(doc.get("dependencies") or [], start=1):
        if isinstance(entry, str):
            _add_conda_entry(entry, path, lineno, result)
        elif isinstance(entry, dict) and isinstance(entry.get("pip"), list):
            for pip_line in entry["pip"]:
                if isinstance(pip_line, str) and pip_line.strip():
                    _add_requirement_line(pip_line.strip(), path, lineno, result)


def _add_conda_entry(entry: str, path: str, lineno: int, result: Declarations) -> None:
    operator_pos = len(entry)
    for match in _CONDA_OPERATOR_RE.finditer(entry):
        operator_pos = match.start()
        break
    head, rest = entry[:operator_pos].strip(), entry[operator_pos:].strip()
    if not head:
        result.unparsed.append(f"{path}:{lineno}: {entry}")
        return
    if not rest:
        result.declarations.append(DependencyDeclaration(head, head, None, None, path, lineno))
        return
    if rest.startswith("="):
        # name=ver (single '=') or name=ver=build both pin the version
        version = rest.removeprefix("=").split("=", 1)[0].strip()
        exact = version if _EXACT_VERSION_RE.match(version) else None
        specifier = version if exact is None else None
    else:
        exact = None
        specifier = rest
    result.declarations.append(
        DependencyDeclaration(canonical_dep_name(head), head, specifier, exact, path, lineno)
    )


# --- Pipfile ----------------------------------------------------------------


def _parse_pipfile(path: str, scanner: RepoScanner, result: Declarations) -> None:
    text = scanner.read_text(path)
    if text is None:
        result.unparsed.append(f"{path}:0: unreadable")
        return
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        result.unparsed.append(f"{path}:0: {exc}")
        return
    for section in ("packages", "dev-packages"):
        table = doc.get(section) or {}
        if not isinstance(table, dict):
            continue
        for lineno, (name, value) in enumerate(table.items(), start=1):
            version = value if isinstance(value, str) else value.get("version")
            exact = None
            specifier = None
            if isinstance(version, str):
                spec = version.strip()
                if spec.startswith("==") and _EXACT_VERSION_RE.match(spec[2:]):
                    exact = spec[2:]
                else:
                    specifier = spec or None
            result.declarations.append(
                DependencyDeclaration(
                    canonical_dep_name(name), name, specifier, exact, path, lineno
                )
            )


# --- lockfiles --------------------------------------------------------------


def _collect_lockfiles(scanner: RepoScanner, result: Declarations, requirements: list[str]) -> None:
    files = scanner.files()
    basenames = {Path(p).name: p for p in files}

    for name in ("uv.lock", "poetry.lock"):
        path = basenames.get(name)
        if path:
            packages = _toml_lockfile_packages(scanner, path)
            result.lockfiles.append(
                Lockfile(path, frozenset(canonical_dep_name(n) for n in packages))
            )

    path = basenames.get("Pipfile.lock")
    if path:
        packages = _pipfile_lock_packages(scanner, path)
        result.lockfiles.append(Lockfile(path, frozenset(canonical_dep_name(n) for n in packages)))

    path = basenames.get("conda-lock.yml")
    if path:
        packages = _conda_lock_packages(scanner, path)
        result.lockfiles.append(Lockfile(path, frozenset(canonical_dep_name(n) for n in packages)))

    # A requirements file where every non-comment line pins with == is a lockfile.
    for path in requirements:
        if path in {lock.path for lock in result.lockfiles}:
            continue
        if _requirements_all_pinned(path, scanner, result, set()):
            names = {d.name for d in result.declarations if d.is_exact and _declares_from(d, path)}
            result.lockfiles.append(Lockfile(path, frozenset(names)))


def _toml_lockfile_packages(scanner: RepoScanner, path: str) -> list[str]:
    text = scanner.read_text(path)
    if text is None:
        return []
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    packages = doc.get("package") or []
    return [p["name"] for p in packages if isinstance(p, dict) and p.get("name")]


def _pipfile_lock_packages(scanner: RepoScanner, path: str) -> list[str]:
    text = scanner.read_text(path)
    if text is None:
        return []
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return []
    names: list[str] = []
    for section in ("default", "develop"):
        table = doc.get(section) or {}
        if isinstance(table, dict):
            names.extend(table.keys())
    return names


def _conda_lock_packages(scanner: RepoScanner, path: str) -> list[str]:
    text = scanner.read_text(path)
    if text is None:
        return []
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    packages = doc.get("package") or [] if isinstance(doc, dict) else []
    return [p["name"] for p in packages if isinstance(p, dict) and p.get("name")]


def _declares_from(decl: DependencyDeclaration, root_file: str) -> bool:
    """A declaration belongs to a requirements tree rooted at ``root_file``
    (directly or via ``-r`` includes). We conservatively attribute all
    requirements-parsed declarations whose source lies in the same directory
    subtree; precision loss is acceptable for lockfile package sets."""
    return decl.source_file == root_file or decl.source_file.startswith(
        Path(root_file).parent.as_posix().rstrip("/") + "/"
    )


def _requirements_all_pinned(
    path: str, scanner: RepoScanner, result: Declarations, seen: set[str]
) -> bool:
    if path in seen:
        return True
    seen.add(path)
    text = scanner.read_text(path)
    if text is None:
        return False
    if any(entry.startswith(f"{path}:") for entry in result.unparsed):
        return False
    exact_lines = {(d.source_file, d.line) for d in result.declarations if d.is_exact}
    has_lines = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r") or line.startswith("--requirement"):
            has_lines = True
            parts = line.split(None, 1)
            if len(parts) != 2:
                return False
            target = parts[1].strip()
            base = Path(path).parent
            resolved = (base / target).as_posix() if not target.startswith("/") else target
            if not _requirements_all_pinned(resolved, scanner, result, seen):
                return False
            continue
        has_lines = True
        if (path, lineno) not in exact_lines:
            return False
    return has_lines
