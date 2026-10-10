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
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from packaging.requirements import Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from reprollm.core._toml import tomllib
from reprollm.core.scanner import RepoScanner, content_source_path

#: Distribution-name overrides applied before canonicalization (spec M2-T03).
_NAME_OVERRIDES = {"pytorch": "torch"}

_EXACT_VERSION_RE = re.compile(r"^\d+(\.\d+)*$")


def canonical_dep_name(name: str) -> str:
    return canonicalize_name(_NAME_OVERRIDES.get(name.strip().lower(), name.strip()))


def _python_exact_version(specifier: SpecifierSet) -> str | None:
    clauses = sorted({(clause.operator, clause.version) for clause in specifier})
    if len(clauses) != 1 or clauses[0][0] != "==" or "*" in clauses[0][1]:
        return None
    version = clauses[0][1]
    try:
        Version(version)
    except InvalidVersion:
        return None
    return version


def _version_field_exact(version: str, *, allow_bare: bool) -> str | None:
    version = version.strip()
    if allow_bare:
        try:
            Version(version)
        except InvalidVersion:
            pass
        else:
            return version
    try:
        specifier = SpecifierSet(version)
    except InvalidSpecifier:
        return None
    return _python_exact_version(specifier)


def _dependency_version_field(value: object, *, allow_bare: bool) -> tuple[str | None, str | None]:
    version = value.get("version") if isinstance(value, dict) else value
    if not isinstance(version, str):
        return None, None
    specifier = version.strip() or None
    # A version alongside a transport source does not prove a Python version pin.
    if isinstance(value, dict) and any(
        key in value for key in ("url", "git", "path", "file", "hg", "svn", "bzr")
    ):
        return specifier, None
    exact = _version_field_exact(version, allow_bare=allow_bare)
    return (None if exact is not None else specifier), exact


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


def dependency_file_paths(files: Iterable[str], *basenames: str) -> list[str]:
    """Preserve every candidate, with root entries before deterministic paths."""
    names = set(basenames)
    return sorted(
        (path for path in files if not names or Path(path).name in names),
        key=lambda path: (len(Path(path).parts) > 1, path),
    )


def _dependency_basenames(files: Iterable[str]) -> dict[str, list[str]]:
    candidates: dict[str, list[str]] = {}
    for path in dependency_file_paths(files):
        candidates.setdefault(Path(path).name, []).append(path)
    return candidates


def scan_dependencies(scanner: RepoScanner) -> Declarations:
    result = Declarations()
    files = scanner.files()
    basenames = _dependency_basenames(files)

    pyprojects = basenames.get("pyproject.toml", [])
    requirements = sorted(p for p in files if _is_requirements_name(p))
    environments = dependency_file_paths(files, "environment.yml", "environment.yaml")
    pipfiles = basenames.get("Pipfile", [])

    # A pyproject.toml is only a dependency manifest when it carries a
    # [project] or [tool.poetry] table (spec §12.2, M2F-T03/F-04); parse it
    # once and reuse the qualification below.
    pyproject_qualified = False
    for pyproject in pyprojects:
        qualified = _parse_pyproject(pyproject, scanner, result)
        pyproject_qualified = pyproject_qualified or qualified

    seen_requirements: set[str] = set()
    for path in requirements:
        _parse_requirements(path, scanner, result, seen_requirements)

    for environment in environments:
        _parse_environment(environment, scanner, result)

    for pipfile in pipfiles:
        _parse_pipfile(pipfile, scanner, result)

    result.manifest_present = bool(
        pyproject_qualified
        or requirements
        or environments
        or basenames.get("uv.lock")
        or basenames.get("poetry.lock")
        or pipfiles
    )

    _collect_lockfiles(scanner, result, requirements)
    return result


def _is_requirements_name(path: str) -> bool:
    name = Path(path).name
    return name.startswith("requirements") and name.endswith(".txt")


# --- requirements*.txt ------------------------------------------------------


def _parse_requirements(
    path: str,
    scanner: RepoScanner,
    result: Declarations,
    seen: set[str],
    depth: int = 0,
    included_from: tuple[str, int] | None = None,
) -> None:
    if path in seen or depth > 10:
        return
    seen.add(path)
    text = scanner.read_text(path)
    if text is None:
        source = content_source_path(path)
        if source is None and included_from is not None:
            parent, include_line = included_from
            parent_source = content_source_path(parent) or "requirements include"
            result.unparsed.append(f"{parent_source}:{include_line}: include unreadable")
        else:
            result.unparsed.append(f"{source or 'requirements include'}:0: unreadable")
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
            _parse_requirements(resolved, scanner, result, seen, depth + 1, (path, lineno))
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
    exact = _python_exact_version(req.specifier)
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


# --- TOML source-location index (M2F-T04, F-05) ------------------------------
#
# tomllib discards physical positions; PEP 621 lists would otherwise carry
# array indexes and Poetry entries mapping-iteration indexes as "lines". The
# index below records, per dependency-relevant section, the physical lines on
# which each entry/key occurs, matched in source order.


class _TomlLineIndex:
    """Physical line locations for dependency entries inside a TOML document."""

    def __init__(self, text: str) -> None:
        # section key → {entry text → [line numbers, ascending]}
        self._requirements: dict[str, dict[str, list[int]]] = {}
        # section key → {key name → [line numbers, ascending]}
        self._keys: dict[str, dict[str, list[int]]] = {}
        self._header_lines: dict[str, int] = {}
        self._cursor: dict[str, int] = {}  # monotonic consumption per bucket

        section = ""
        requirement_array_depth = 0
        for lineno, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.strip()
            header = stripped.startswith("[") and stripped.endswith("]")
            if header:
                section = self._normalize_header(stripped)
                requirement_array_depth = 0
                if section:
                    self._header_lines.setdefault(section, lineno)
                continue
            if not section:
                continue
            if section in ("project", "project.optional-dependencies"):
                stripped = _toml_line_without_comment(stripped)
                if not requirement_array_depth:
                    key = _leading_key(stripped)
                    if key is None or (section == "project" and key != "dependencies"):
                        continue
                    stripped = stripped.split("=", 1)[1].lstrip()
                    if not stripped.startswith("["):
                        continue
                unquoted = _TOML_QUOTED_RE.sub("", stripped)
                requirement_array_depth += unquoted.count("[") - unquoted.count("]")
                for entry in _quoted_strings(stripped):
                    bucket = self._requirements.setdefault(section, {})
                    bucket.setdefault(entry, []).append(lineno)
            elif section in ("tool.poetry.dependencies", "pipfile.packages"):
                key = _leading_key(stripped)
                if key is not None:
                    bucket = self._keys.setdefault(section, {})
                    bucket.setdefault(key, []).append(lineno)

    @staticmethod
    def _normalize_header(header: str) -> str:
        if header in ("[project]", "[tool.poetry.dependencies]"):
            return header[1:-1]
        if header == "[project.optional-dependencies]":
            return "project.optional-dependencies"
        inner = header[1:-1]
        if inner.startswith("project.optional-dependencies."):
            return "project.optional-dependencies"
        if inner in ("packages", "dev-packages"):  # Pipfile
            return "pipfile.packages"
        return ""

    def requirement_line(self, section: str, entry: str, fallback_header: int) -> int:
        """Next physical line containing ``entry`` in ``section`` (source order)."""
        bucket = self._requirements.get(section, {})
        lines = bucket.get(entry, [])
        consumed = self._cursor.get(f"{section}:{entry}", 0)
        self._cursor[f"{section}:{entry}"] = consumed + 1
        if consumed < len(lines):
            return lines[consumed]
        return fallback_header

    def key_line(self, section: str, key: str, fallback_header: int) -> int:
        bucket = self._keys.get(section, {})
        lines = bucket.get(key, [])
        consumed = self._cursor.get(f"{section}:{key}", 0)
        self._cursor[f"{section}:{key}"] = consumed + 1
        if consumed < len(lines):
            return lines[consumed]
        return fallback_header

    def header_line(self, section: str) -> int:
        return self._header_lines.get(section, 1)


_TOML_QUOTED_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'')


def _toml_line_without_comment(line: str) -> str:
    unquoted = _TOML_QUOTED_RE.sub(lambda match: " " * len(match.group(0)), line)
    comment = unquoted.find("#")
    return line if comment < 0 else line[:comment]


def _quoted_strings(line: str) -> list[str]:
    entries = []
    for match in _TOML_QUOTED_RE.finditer(line):
        # Match the decoded dependency string, including escaped marker quotes.
        try:
            value = tomllib.loads(f"value = {match.group(0)}")["value"]
        except tomllib.TOMLDecodeError:
            continue
        if isinstance(value, str):
            entries.append(value)
    return entries


_TOML_KEY_RE = re.compile(r'^(?:"([^"]+)"|\'([^\']+)\'|([A-Za-z0-9_.-]+))\s*=')


def _leading_key(line: str) -> str | None:
    match = _TOML_KEY_RE.match(line)
    if match is None:
        return None
    return match.group(1) or match.group(2) or match.group(3)


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
    tool = doc.get("tool") or {}
    if not isinstance(tool, dict):
        result.unparsed.append(f"{path}:0: invalid tool table")
        tool = {}
    poetry = tool.get("poetry") or {}
    qualified = isinstance(doc.get("project"), dict) or isinstance(tool.get("poetry"), dict)
    if not qualified:
        return False  # tool-only pyproject (e.g. [tool.ruff]) is not a manifest

    index = _TomlLineIndex(text)

    project = doc.get("project") or {}
    if isinstance(project, dict):
        deps = project.get("dependencies") or []
        header = index.header_line("project")
        if isinstance(deps, list):
            for entry in deps:
                if isinstance(entry, str):
                    lineno = index.requirement_line("project", entry, header)
                    _add_requirement_line(entry, path, lineno, result)
        optional = project.get("optional-dependencies") or {}
        header = index.header_line("project.optional-dependencies")
        if isinstance(optional, dict):
            for entries in optional.values():
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, str):
                            lineno = index.requirement_line(
                                "project.optional-dependencies", entry, header
                            )
                            _add_requirement_line(entry, path, lineno, result)

    if not isinstance(poetry, dict):
        result.unparsed.append(f"{path}:0: invalid poetry table")
        poetry = {}
    poetry_deps = poetry.get("dependencies") or {}
    if isinstance(poetry_deps, dict):
        header = index.header_line("tool.poetry.dependencies")
        for name, value in poetry_deps.items():
            specifier, exact = _dependency_version_field(value, allow_bare=True)
            lineno = index.key_line("tool.poetry.dependencies", name, header)
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
    dependencies = doc.get("dependencies") or []
    if not isinstance(dependencies, list):
        result.unparsed.append(f"{path}:0: invalid dependencies collection")
        return
    for lineno, entry in enumerate(dependencies, start=1):
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
    index = _TomlLineIndex(text)
    header = index.header_line("pipfile.packages")
    for section in ("packages", "dev-packages"):
        table = doc.get(section) or {}
        if not isinstance(table, dict):
            continue
        for name, value in table.items():
            specifier, exact = _dependency_version_field(value, allow_bare=False)
            lineno = index.key_line("pipfile.packages", name, header)
            result.declarations.append(
                DependencyDeclaration(
                    canonical_dep_name(name), name, specifier, exact, path, lineno
                )
            )


# --- lockfiles --------------------------------------------------------------


def _collect_lockfiles(scanner: RepoScanner, result: Declarations, requirements: list[str]) -> None:
    files = scanner.files()
    basenames = _dependency_basenames(files)

    for name in ("uv.lock", "poetry.lock"):
        for path in basenames.get(name, []):
            packages = _toml_lockfile_packages(scanner, path, result)
            result.lockfiles.append(
                Lockfile(path, frozenset(canonical_dep_name(n) for n in packages))
            )

    for path in basenames.get("Pipfile.lock", []):
        packages = _pipfile_lock_packages(scanner, path, result)
        result.lockfiles.append(Lockfile(path, frozenset(canonical_dep_name(n) for n in packages)))

    for path in basenames.get("conda-lock.yml", []):
        packages = _conda_lock_packages(scanner, path, result)
        result.lockfiles.append(Lockfile(path, frozenset(canonical_dep_name(n) for n in packages)))

    # A requirements file where every non-comment line pins with == is a lockfile.
    for path in requirements:
        if path in {lock.path for lock in result.lockfiles}:
            continue
        if _requirements_all_pinned(path, scanner, result, set()):
            names = {d.name for d in result.declarations if d.is_exact and _declares_from(d, path)}
            result.lockfiles.append(Lockfile(path, frozenset(names)))


def _lock_package_names(packages: list[object], path: str, result: Declarations) -> list[str]:
    names: list[str] = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = package.get("name")
        if isinstance(name, str):
            if name:
                names.append(name)
        elif name is not None:
            result.unparsed.append(f"{path}:0: invalid package name")
    return names


def _toml_lockfile_packages(scanner: RepoScanner, path: str, result: Declarations) -> list[str]:
    text = scanner.read_text(path)
    if text is None:
        return []
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    packages = doc.get("package") or []
    if not isinstance(packages, list):
        result.unparsed.append(f"{path}:0: invalid package collection")
        return []
    return _lock_package_names(packages, path, result)


def _pipfile_lock_packages(scanner: RepoScanner, path: str, result: Declarations) -> list[str]:
    text = scanner.read_text(path)
    if text is None:
        return []
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(doc, dict):
        result.unparsed.append(f"{path}:0: invalid lock document")
        return []
    names: list[str] = []
    for section in ("default", "develop"):
        table = doc.get(section) or {}
        if isinstance(table, dict):
            names.extend(table.keys())
    return names


def _conda_lock_packages(scanner: RepoScanner, path: str, result: Declarations) -> list[str]:
    text = scanner.read_text(path)
    if text is None:
        return []
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    packages = doc.get("package") or [] if isinstance(doc, dict) else []
    if not isinstance(packages, list):
        result.unparsed.append(f"{path}:0: invalid package collection")
        return []
    return _lock_package_names(packages, path, result)


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
