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
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

import yaml
from packaging.requirements import Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from reprollm.core._toml import tomllib
from reprollm.core.scanner import RepoScanner, content_source_path

#: Distribution-name overrides applied before canonicalization (spec M2-T03).
_NAME_OVERRIDES = {"pytorch": "torch"}

DeclarationReadIssue = Literal[
    "unreadable",
    "invalid_syntax",
    "invalid_structure",
    "unparsed_requirement",
    "unparsed_conda",
    "unparsed_conda_specifier",
    "parser_limit",
]
LockReadIssue = Literal["unreadable", "invalid_syntax", "invalid_structure", "parser_limit"]
_FORMAT_LOCK_NAMES = frozenset({"uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"})


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
    # Only bounded read/syntax/structure failures; None does not certify all package grammar.
    read_issue: LockReadIssue | None = None


@dataclass
class Declarations:
    declarations: list[DependencyDeclaration] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    lockfiles: list[Lockfile] = field(default_factory=list)
    manifest_present: bool = False
    _project_manifests: dict[str, frozenset[str]] = field(default_factory=dict, repr=False)
    _uncertain_directories: set[PurePosixPath] = field(default_factory=set, repr=False)
    declaration_read_issues: dict[str, DeclarationReadIssue] = field(default_factory=dict)
    unexpanded_requirement_targets: tuple[str, ...] = ()
    excluded_requirement_targets: tuple[str, ...] = ()

    def qualified_lock_packages(self, import_origins: Iterable[tuple[str, str]]) -> frozenset[str]:
        """Return lock credit supported by an associated actual package origin."""
        qualified = {
            name
            for lock in self.lockfiles
            if _is_requirements_name(lock.path)
            for name in lock.packages
        }
        qualified.update(
            name
            for lock, origins in self._format_lock_origins(import_origins).items()
            for name in origins
            if name in lock.packages
        )
        return frozenset(qualified)

    def unverified_lock_paths(
        self, import_origins: Iterable[tuple[str, str]]
    ) -> dict[str, tuple[str, ...]]:
        """Known failed locks associated with captured package-use origins."""
        failed = {
            lock
            for lock in self.lockfiles
            if lock.read_issue is not None and PurePosixPath(lock.path).name in _FORMAT_LOCK_NAMES
        }
        if not failed:
            return {}
        paths: dict[str, set[str]] = {}
        for lock, origins in self._format_lock_origins(import_origins).items():
            if lock not in failed:
                continue
            for name in origins:
                paths.setdefault(name, set()).add(lock.path)
        return {name: tuple(sorted(paths[name])) for name in sorted(paths)}

    def _format_lock_origins(
        self, import_origins: Iterable[tuple[str, str]]
    ) -> dict[Lockfile, set[str]]:
        """Associate captured origins before testing package membership or read state."""
        origins: dict[Lockfile, set[str]] = {}
        paired: dict[PurePosixPath, set[Lockfile]] = {}
        for lock in self.lockfiles:
            location = PurePosixPath(lock.path)
            for manifest, formats in self._project_manifests.items():
                if (
                    location.name not in formats
                    or PurePosixPath(manifest).parent != location.parent
                ):
                    continue
                paired.setdefault(location.parent, set()).add(lock)
                origins.setdefault(lock, set()).update(
                    declaration.name
                    for declaration in self.declarations
                    if declaration.source_file == manifest
                )
        project_roots = {PurePosixPath(path).parent for path in self._project_manifests}
        boundaries = project_roots | self._uncertain_directories
        for name, source in import_origins:
            normalized = content_source_path(source)
            if normalized is None:
                continue
            owner = next(
                (parent for parent in PurePosixPath(normalized).parents if parent in boundaries),
                None,
            )
            if owner is not None and owner not in self._uncertain_directories:
                for lock in paired.get(owner, ()):
                    origins.setdefault(lock, set()).add(name)
        return origins


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
    files = scanner.analysis_files()
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

    requirements_graph = _RequirementsGraph(scanner, result)
    requirements_graph.parse(requirements)

    for environment in environments:
        _parse_environment(environment, scanner, result)

    environment_paths = {PurePosixPath(path) for path in environments}
    for environment in environments:
        path = PurePosixPath(environment)
        if (
            path.with_name("environment.yml") in environment_paths
            and path.with_name("environment.yaml") in environment_paths
            and environment in result._project_manifests
        ):
            # Keep the project boundary while withholding the ambiguous Conda pair.
            result._project_manifests[environment] = frozenset()

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

    _collect_lockfiles(scanner, result, requirements, requirements_graph)
    return result


def _is_requirements_name(path: str) -> bool:
    name = Path(path).name
    return name.startswith("requirements") and name.endswith(".txt")


# --- requirements*.txt ------------------------------------------------------


_REQUIREMENTS_MAX_DEPTH = 10


@dataclass(frozen=True)
class _RequirementInclude:
    line: int
    target: str | None
    error: str | None = None


@dataclass(frozen=True)
class _RequirementFile:
    readable: bool
    events: tuple[DependencyDeclaration | _RequirementInclude | str, ...] = ()


@dataclass(frozen=True)
class _RequirementsClosure:
    complete: bool
    sources: frozenset[str] = frozenset()
    declarations: frozenset[DependencyDeclaration] = frozenset()

    @property
    def is_exact(self) -> bool:
        return (
            self.complete
            and bool(self.declarations)
            and all(declaration.is_exact for declaration in self.declarations)
        )

    @property
    def packages(self) -> frozenset[str]:
        return frozenset(declaration.name for declaration in self.declarations)


def _requirement_include(line: str, source: str, lineno: int) -> _RequirementInclude | None:
    parts = line.split(None, 1)
    if parts[0] not in {"-r", "--requirement"}:
        if line.startswith("-r") or line.startswith("--requirement"):
            return _RequirementInclude(lineno, None, "include unsupported syntax")
        return None
    if len(parts) != 2:
        return _RequirementInclude(lineno, None, "include malformed")
    target = parts[1].strip()
    if "\x00" in target:
        return _RequirementInclude(lineno, None, "include malformed")
    if any(char in target for char in "\"'$`") or any(char.isspace() for char in target):
        return _RequirementInclude(lineno, None, "include unsupported syntax")
    if "://" in target:
        return _RequirementInclude(lineno, None, "include unsupported syntax")
    if Path(target).is_absolute() or PureWindowsPath(target).anchor:
        return _RequirementInclude(lineno, None, "include unreadable")
    normalized = content_source_path((Path(source).parent / target).as_posix())
    if normalized is None:
        return _RequirementInclude(lineno, None, "include unreadable")
    return _RequirementInclude(lineno, normalized)


def _requirement_comment_prefix(line: str) -> str | None:
    comment = re.search(r"[ \t]#", line)
    if comment is None:
        return None
    prefix = line[: comment.start()].strip()
    try:
        requirement = Requirement(prefix)
    except Exception:  # noqa: BLE001 - preserve the original failed-line diagnostic
        return None
    return prefix if requirement.url is None else None


class _RequirementsGraph:
    """One captured parse graph; depth and active-stack results stay per root."""

    def __init__(self, scanner: RepoScanner, result: Declarations) -> None:
        self.scanner = scanner
        self.result = result
        self.nodes: dict[str, _RequirementFile] = {}
        self.closures: dict[str, _RequirementsClosure] = {}
        self._expanded_depth: dict[str, int] = {}
        self._emitted_sources: set[str] = set()
        self._excluded_sources: set[str] = set()
        self._diagnostics: set[str] = set(result.unparsed)

    def parse(self, roots: list[str]) -> None:
        for root in roots:
            self._expand(root, 0, set())
        # A later, shallower root can capture an earlier depth-limited target.
        self.result.unexpanded_requirement_targets = tuple(
            sorted(
                {
                    event.target
                    for node in self.nodes.values()
                    if node.readable
                    for event in node.events
                    if isinstance(event, _RequirementInclude)
                    and event.target is not None
                    and event.target not in self.nodes
                }
            )
        )
        self.result.excluded_requirement_targets = tuple(
            sorted(
                {
                    event.target
                    for node in self.nodes.values()
                    if node.readable
                    for event in node.events
                    if isinstance(event, _RequirementInclude)
                    and event.target is not None
                    and event.target in self._excluded_sources
                }
            )
        )
        for root in roots:
            if not self.nodes[root].readable:
                self._diagnostic(f"{root}:0: unreadable")
            self.closures[root] = self._closure(root, 0, set(), {})

    def _diagnostic(self, diagnostic: str) -> None:
        if diagnostic not in self._diagnostics:
            self._diagnostics.add(diagnostic)
            self.result.unparsed.append(diagnostic)

    def _node(self, source: str) -> _RequirementFile:
        cached = self.nodes.get(source)
        if cached is not None:
            return cached
        if self.scanner.is_analysis_candidate(source):
            text = self.scanner.read_text(source)
            if text is None:
                self.result.declaration_read_issues[source] = "unreadable"
        else:
            self._excluded_sources.add(source)
            text = None
        if text is None:
            node = _RequirementFile(False)
        else:
            events: list[DependencyDeclaration | _RequirementInclude | str] = []
            include_targets: set[str] = set()
            lines = text.splitlines()
            allow_inline_comments = not any(raw.rstrip().endswith("\\") for raw in lines)
            for lineno, raw in enumerate(lines, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                include = _requirement_include(line, source, lineno)
                if include is not None:
                    if include.target is None or include.target not in include_targets:
                        events.append(include)
                    if include.target is not None:
                        include_targets.add(include.target)
                elif line.startswith("-") or " @ " in line:
                    events.append(f"{source}:{lineno}: {line}")
                else:
                    parsed = Declarations()
                    _add_requirement_line(line, source, lineno, parsed)
                    if parsed.unparsed and allow_inline_comments:
                        prefix = _requirement_comment_prefix(line)
                        if prefix is not None:
                            parsed = Declarations()
                            _add_requirement_line(prefix, source, lineno, parsed)
                    events.extend(parsed.declarations)
                    events.extend(parsed.unparsed)
            node = _RequirementFile(True, tuple(events))
        self.nodes[source] = node
        return node

    def _expand(self, source: str, depth: int, active: set[str]) -> None:
        if source in active or depth > _REQUIREMENTS_MAX_DEPTH:
            return
        previous_depth = self._expanded_depth.get(source)
        if previous_depth is not None and previous_depth <= depth:
            return
        self._expanded_depth[source] = depth
        node = self._node(source)
        first_encounter = source not in self._emitted_sources
        self._emitted_sources.add(source)
        active.add(source)
        for event in node.events:
            if isinstance(event, DependencyDeclaration):
                if first_encounter:
                    self.result.declarations.append(event)
            elif isinstance(event, str):
                if first_encounter:
                    self._diagnostic(event)
            elif event.target is not None:
                self._expand(event.target, depth + 1, active)
        active.remove(source)

    def _closure(
        self,
        source: str,
        depth: int,
        active: set[str],
        memo: dict[tuple[str, int], _RequirementsClosure],
    ) -> _RequirementsClosure:
        if source in active or depth > _REQUIREMENTS_MAX_DEPTH:
            return _RequirementsClosure(False)
        key = (source, _REQUIREMENTS_MAX_DEPTH - depth)
        cached = memo.get(key)
        if cached is not None:
            return cached
        node = self.nodes[source]
        complete = node.readable
        sources = {source}
        declarations: set[DependencyDeclaration] = set()
        active.add(source)
        for event in node.events:
            if isinstance(event, DependencyDeclaration):
                declarations.add(event)
                continue
            if isinstance(event, str):
                complete = False
                continue
            reason = event.error
            child: _RequirementsClosure | None = None
            if event.target is not None:
                if event.target in active:
                    reason = "include cycle"
                elif depth >= _REQUIREMENTS_MAX_DEPTH:
                    reason = "include depth limit"
                elif not self.nodes[event.target].readable:
                    reason = "include unreadable"
                else:
                    child = self._closure(event.target, depth + 1, active, memo)
                    if not child.complete:
                        reason = "include incomplete"
            if child is not None:
                sources.update(child.sources)
                declarations.update(child.declarations)
            if reason is not None:
                self._diagnostic(f"{source}:{event.line}: {reason}")
                complete = False
        active.remove(source)
        closure = _RequirementsClosure(complete, frozenset(sources), frozenset(declarations))
        memo[key] = closure
        return closure


def _add_requirement_line(line: str, path: str, lineno: int, result: Declarations) -> bool:
    try:
        req = Requirement(line)
    except Exception:  # noqa: BLE001 - never crash on odd requirements syntax
        result.unparsed.append(f"{path}:{lineno}: {line}")
        return False
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
    return True


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


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _invalid_pyproject_structure(doc: dict[str, object]) -> bool:
    project = doc.get("project", {})
    tool = doc.get("tool", {})
    if not isinstance(project, dict) or not isinstance(tool, dict):
        return True
    poetry = tool.get("poetry", {})
    if not isinstance(poetry, dict):
        return True
    optional = project.get("optional-dependencies", {})
    return (
        not _is_string_list(project.get("dependencies", []))
        or not isinstance(optional, dict)
        or any(not _is_string_list(group) for group in optional.values())
        or not isinstance(poetry.get("dependencies", {}), dict)
    )


def _parse_pyproject(path: str, scanner: RepoScanner, result: Declarations) -> bool:
    """Parse once; return True only when a ``[project]`` or ``[tool.poetry]``
    table qualifies the file as a dependency manifest (spec §12.2, M2F-T03)."""
    text = scanner.read_text(path)
    if text is None:
        result.declaration_read_issues[path] = "unreadable"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: unreadable")
        return False
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        result.declaration_read_issues[path] = "invalid_syntax"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: {exc}")
        return False
    except RecursionError:
        result.declaration_read_issues[path] = "parser_limit"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: decoder recursion limit; skipped")
        return False
    # Inspect raw shapes before legacy falsey defaults and qualification discard them.
    if _invalid_pyproject_structure(doc):
        result.declaration_read_issues[path] = "invalid_structure"
    if "project" in doc and not isinstance(doc["project"], dict):
        result._uncertain_directories.add(PurePosixPath(path).parent)
    raw_tool = doc.get("tool", {})
    if not isinstance(raw_tool, dict) or (
        "poetry" in raw_tool and not isinstance(raw_tool["poetry"], dict)
    ):
        result._uncertain_directories.add(PurePosixPath(path).parent)
    tool = doc.get("tool") or {}
    if not isinstance(tool, dict):
        result.unparsed.append(f"{path}:0: invalid tool table")
        tool = {}
    poetry = tool.get("poetry") or {}
    qualified = isinstance(doc.get("project"), dict) or isinstance(tool.get("poetry"), dict)
    if not qualified:
        return False  # tool-only pyproject (e.g. [tool.ruff]) is not a manifest

    result._project_manifests[path] = frozenset(
        {"uv.lock", "poetry.lock"} if isinstance(doc.get("project"), dict) else {"poetry.lock"}
    )

    index = _TomlLineIndex(text)

    project = doc.get("project") or {}
    if isinstance(project, dict):
        deps = project.get("dependencies") or []
        header = index.header_line("project")
        if isinstance(deps, list):
            for entry in deps:
                if isinstance(entry, str):
                    lineno = index.requirement_line("project", entry, header)
                    if not _add_requirement_line(entry, path, lineno, result):
                        result.declaration_read_issues.setdefault(path, "unparsed_requirement")
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
                            if not _add_requirement_line(entry, path, lineno, result):
                                result.declaration_read_issues.setdefault(
                                    path, "unparsed_requirement"
                                )

    if not isinstance(poetry, dict):
        result.unparsed.append(f"{path}:0: invalid poetry table")
        poetry = {}
    poetry_deps = poetry.get("dependencies") or {}
    if isinstance(poetry_deps, dict):
        header = index.header_line("tool.poetry.dependencies")
        for name, value in poetry_deps.items():
            if (
                isinstance(value, dict)
                and "version" in value
                and not isinstance(value["version"], str)
            ):
                result.declaration_read_issues.setdefault(path, "invalid_structure")
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


# Numeric MatchSpecs only (spec §12.2); Conda equality is separate from PEP 440.
_CONDA_NAME_RE = re.compile(r"(?P<name>[A-Za-z0-9_.-]+)(?P<rest>.*)")
_CONDA_VERSION_RE = re.compile(
    r"(?P<operator>==?)(?P<version>[0-9]+(?:\.[0-9]+)*)(?:=(?P<build>[A-Za-z0-9._+\-]+))?"
)
_CONDA_RANGE_RE = re.compile(r"(?:>=|<=|!=|>|<|~=)[0-9]+(?:\.[0-9]+)*")


def _invalid_environment_structure(doc: object) -> bool:
    if doc is None:
        return False  # Retain the legacy empty/top-level-null boundary (spec §12.3.7).
    if not isinstance(doc, dict):
        return True
    dependencies = doc.get("dependencies", [])
    if not isinstance(dependencies, list):
        return True
    for entry in dependencies:
        if not isinstance(entry, (str, dict)):
            return True
        if isinstance(entry, dict) and "pip" in entry and not _is_string_list(entry["pip"]):
            return True
    return False


def _parse_environment(path: str, scanner: RepoScanner, result: Declarations) -> None:
    text = scanner.read_text(path)
    if text is None:
        result.declaration_read_issues[path] = "unreadable"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: unreadable")
        return
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        result.declaration_read_issues[path] = "invalid_syntax"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: {exc}")
        return
    except RecursionError:
        result.declaration_read_issues[path] = "parser_limit"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: decoder recursion limit; skipped")
        return
    if _invalid_environment_structure(doc):
        result.declaration_read_issues[path] = "invalid_structure"
    if not isinstance(doc, dict):
        return
    if "dependencies" in doc and not isinstance(doc["dependencies"], list):
        result._uncertain_directories.add(PurePosixPath(path).parent)
    dependencies = doc.get("dependencies") or []
    if not isinstance(dependencies, list):
        result.unparsed.append(f"{path}:0: invalid dependencies collection")
        return
    if isinstance(doc.get("dependencies"), list):
        result._project_manifests[path] = frozenset({"conda-lock.yml"})
    for lineno, entry in enumerate(dependencies, start=1):
        if isinstance(entry, str):
            _add_conda_entry(entry, path, lineno, result)
        elif isinstance(entry, dict) and isinstance(entry.get("pip"), list):
            for pip_line in entry["pip"]:
                if (
                    isinstance(pip_line, str)
                    and pip_line.strip()
                    and not _add_requirement_line(pip_line.strip(), path, lineno, result)
                ):
                    result.declaration_read_issues.setdefault(path, "unparsed_requirement")


def _add_conda_entry(entry: str, path: str, lineno: int, result: Declarations) -> None:
    parsed = _CONDA_NAME_RE.fullmatch(entry.strip())
    if parsed is None:
        result.declaration_read_issues.setdefault(path, "unparsed_conda")
        result.unparsed.append(f"{path}:{lineno}: unsupported conda declaration")
        return
    head, rest = parsed.group("name"), parsed.group("rest")
    # A channel or subdir prefix does not identify a package in the bounded subset.
    if rest.startswith(("::", "/")):
        result.declaration_read_issues.setdefault(path, "unparsed_conda")
        result.unparsed.append(f"{path}:{lineno}: unsupported conda declaration")
        return
    exact = None
    specifier = rest or None
    version = _CONDA_VERSION_RE.fullmatch(rest) if rest else None
    if version is not None:
        # Single '=' without a build is prefix matching; this is not Python grammar.
        if version.group("operator") == "==" or version.group("build") is not None:
            exact = version.group("version")
    elif rest:
        result.unparsed.append(f"{path}:{lineno}: unsupported conda declaration")
        # Only known numeric ranges retain legacy evidence; arbitrary text is unsafe.
        if _CONDA_RANGE_RE.fullmatch(rest) is None:
            result.declaration_read_issues.setdefault(path, "unparsed_conda_specifier")
            specifier = "(unsupported conda declaration)"
    result.declarations.append(
        DependencyDeclaration(canonical_dep_name(head), head, specifier, exact, path, lineno)
    )


# --- Pipfile ----------------------------------------------------------------


def _parse_pipfile(path: str, scanner: RepoScanner, result: Declarations) -> None:
    text = scanner.read_text(path)
    if text is None:
        result.declaration_read_issues[path] = "unreadable"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: unreadable")
        return
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        result.declaration_read_issues[path] = "invalid_syntax"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: {exc}")
        return
    except RecursionError:
        result.declaration_read_issues[path] = "parser_limit"
        result._uncertain_directories.add(PurePosixPath(path).parent)
        result.unparsed.append(f"{path}:0: decoder recursion limit; skipped")
        return
    if any(
        section in doc and not isinstance(doc[section], dict)
        for section in ("packages", "dev-packages")
    ):
        result.declaration_read_issues[path] = "invalid_structure"
        result._uncertain_directories.add(PurePosixPath(path).parent)
    if any(isinstance(doc.get(section), dict) for section in ("packages", "dev-packages")):
        result._project_manifests[path] = frozenset({"Pipfile.lock"})
    index = _TomlLineIndex(text)
    header = index.header_line("pipfile.packages")
    for section in ("packages", "dev-packages"):
        table = doc.get(section) or {}
        if not isinstance(table, dict):
            continue
        for name, value in table.items():
            if (
                isinstance(value, dict)
                and "version" in value
                and not isinstance(value["version"], str)
            ):
                result.declaration_read_issues.setdefault(path, "invalid_structure")
            specifier, exact = _dependency_version_field(value, allow_bare=False)
            lineno = index.key_line("pipfile.packages", name, header)
            result.declarations.append(
                DependencyDeclaration(
                    canonical_dep_name(name), name, specifier, exact, path, lineno
                )
            )


# --- lockfiles --------------------------------------------------------------


def _collect_lockfiles(
    scanner: RepoScanner,
    result: Declarations,
    requirements: list[str],
    graph: _RequirementsGraph,
) -> None:
    files = scanner.analysis_files()
    basenames = _dependency_basenames(files)

    for name in ("uv.lock", "poetry.lock"):
        for path in basenames.get(name, []):
            packages, issue = _toml_lockfile_packages(scanner, path, result)
            result.lockfiles.append(
                Lockfile(path, frozenset(canonical_dep_name(n) for n in packages), issue)
            )

    for path in basenames.get("Pipfile.lock", []):
        packages, issue = _pipfile_lock_packages(scanner, path, result)
        result.lockfiles.append(
            Lockfile(path, frozenset(canonical_dep_name(n) for n in packages), issue)
        )

    for path in basenames.get("conda-lock.yml", []):
        packages, issue = _conda_lock_packages(scanner, path, result)
        result.lockfiles.append(
            Lockfile(path, frozenset(canonical_dep_name(n) for n in packages), issue)
        )

    # Qualification and packages use the same captured include closure.
    for path in requirements:
        if path in {lock.path for lock in result.lockfiles}:
            continue
        if _requirements_all_pinned(path, graph):
            result.lockfiles.append(Lockfile(path, graph.closures[path].packages))


def _lock_package_names(
    packages: list[object], path: str, result: Declarations
) -> tuple[list[str], LockReadIssue | None]:
    names: list[str] = []
    issue: LockReadIssue | None = None
    for package in packages:
        if not isinstance(package, dict):
            issue = "invalid_structure"
            continue
        name = package.get("name")
        if isinstance(name, str):
            if name:
                names.append(name)
            else:
                issue = "invalid_structure"
        else:
            issue = "invalid_structure"
            if name is not None:
                result.unparsed.append(f"{path}:0: invalid package name")
    return names, issue


def _toml_lockfile_packages(
    scanner: RepoScanner, path: str, result: Declarations
) -> tuple[list[str], LockReadIssue | None]:
    text = scanner.read_text(path)
    if text is None:
        return [], "unreadable"
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return [], "invalid_syntax"
    except RecursionError:
        return [], "parser_limit"
    raw_packages = doc.get("package", [])
    # Preserve legacy extraction and diagnostics for falsey unsupported containers.
    packages = raw_packages or []
    if not isinstance(packages, list):
        result.unparsed.append(f"{path}:0: invalid package collection")
        return [], "invalid_structure"
    names, issue = _lock_package_names(packages, path, result)
    return names, "invalid_structure" if not isinstance(raw_packages, list) else issue


def _pipfile_lock_packages(
    scanner: RepoScanner, path: str, result: Declarations
) -> tuple[list[str], LockReadIssue | None]:
    text = scanner.read_text(path)
    if text is None:
        return [], "unreadable"
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return [], "invalid_syntax"
    except RecursionError:
        return [], "parser_limit"
    if not isinstance(doc, dict):
        result.unparsed.append(f"{path}:0: invalid lock document")
        return [], "invalid_structure"
    names: list[str] = []
    issue: LockReadIssue | None = None
    for section in ("default", "develop"):
        raw_table = doc.get(section, {})
        table = raw_table or {}
        if isinstance(table, dict):
            names.extend(table.keys())
        if not isinstance(raw_table, dict):
            issue = "invalid_structure"
    return names, issue


def _conda_lock_packages(
    scanner: RepoScanner, path: str, result: Declarations
) -> tuple[list[str], LockReadIssue | None]:
    text = scanner.read_text(path)
    if text is None:
        return [], "unreadable"
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return [], "invalid_syntax"
    except RecursionError:
        return [], "parser_limit"
    if doc is None:
        return [], None
    if not isinstance(doc, dict):
        return [], "invalid_structure"
    raw_packages = doc.get("package", [])
    packages = raw_packages or []
    if not isinstance(packages, list):
        result.unparsed.append(f"{path}:0: invalid package collection")
        return [], "invalid_structure"
    names, issue = _lock_package_names(packages, path, result)
    return names, "invalid_structure" if not isinstance(raw_packages, list) else issue


def _requirements_all_pinned(path: str, graph: _RequirementsGraph) -> bool:
    return graph.closures[path].is_exact
