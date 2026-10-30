"""Pinned installation identities, usable before ReproLLM or its dependencies exist."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

_COMMIT = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_VERSION = re.compile(r"[0-9][A-Za-z0-9.!+_-]*")
_ID = re.compile(r"[a-z0-9][a-z0-9.-]{0,63}")
_HEAVY = frozenset({"torch", "transformers", "vllm", "huggingface-hub", "numpy"})
_SOURCE_ROOT = "https://codeload.github.com/EnumaElish123/ReproLLM/tar.gz/"


class CatalogError(ValueError):
    """A fixed diagnostic code that never includes untrusted values or local paths."""


@dataclass(frozen=True)
class Artifact:
    name: str
    version: str
    filename: str
    url: str
    sha256: str


@dataclass(frozen=True)
class Candidate:
    id: str
    version: str
    source_commit: str
    source_url: str
    source_sha256: str
    wheel_filename: str
    python_min: tuple[int, int]
    python_max: tuple[int, int]
    platforms: tuple[str, ...]
    capabilities: tuple[str, ...]
    runtime_artifacts: tuple[Artifact, ...]
    build_artifacts: tuple[Artifact, ...]

    def supports(self, python: tuple[int, int], platform: str) -> bool:
        return self.python_min <= python <= self.python_max and platform in self.platforms

    def requirements(self, stage: str = "runtime") -> tuple[str, ...]:
        if stage not in {"runtime", "build"}:
            raise CatalogError("unknown_dependency_stage")
        artifacts = self.runtime_artifacts if stage == "runtime" else self.build_artifacts
        groups: dict[tuple[str, str], set[str]] = {}
        for artifact in artifacts:
            groups.setdefault((artifact.name, artifact.version), set()).add(artifact.sha256)
        return tuple(
            f"{name}=={version} " + " ".join(f"--hash=sha256:{sha}" for sha in sorted(hashes))
            for (name, version), hashes in sorted(groups.items())
        )


@dataclass(frozen=True)
class Catalog:
    schema_version: int
    default_candidate: str
    candidates: tuple[Candidate, ...]

    def get_candidate(self, id: str | None = None) -> Candidate:
        target = self.default_candidate if id is None else id
        for candidate in self.candidates:
            if candidate.id == target:
                return candidate
        raise CatalogError("unknown_candidate")


def _require(condition: bool, code: str = "invalid_catalog") -> None:
    if not condition:
        raise CatalogError(code)


def _mapping(value: Any, keys: set[str]) -> dict[str, Any]:
    _require(isinstance(value, dict) and set(value) == keys)
    return dict(value)


def _text(value: Any, pattern: re.Pattern[str]) -> str:
    _require(isinstance(value, str) and pattern.fullmatch(value) is not None)
    return str(value)


def _strings(value: Any, pattern: re.Pattern[str]) -> tuple[str, ...]:
    _require(isinstance(value, list) and bool(value))
    items = tuple(_text(item, pattern) for item in value)
    _require(len(set(items)) == len(items))
    return items


def _python(value: Any) -> tuple[int, int]:
    _require(
        isinstance(value, list) and len(value) == 2 and all(type(part) is int for part in value)
    )
    result = (int(value[0]), int(value[1]))
    _require((3, 10) <= result <= (3, 12))
    return result


def _artifact(value: Any) -> Artifact:
    data = _mapping(value, {"name", "version", "filename", "url", "sha256"})
    name = _text(data["name"], _NAME)
    _require(name not in _HEAVY, "heavy_dependency_forbidden")
    version = _text(data["version"], _VERSION)
    filename = _text(data["filename"], re.compile(r"[A-Za-z0-9_.+-]+\.whl"))
    _require(filename.startswith(name.replace("-", "_") + "-" + version + "-"))
    url = data["url"]
    _require(isinstance(url, str) and url.isascii() and not any(c.isspace() for c in url))
    try:
        parsed = urlsplit(url)
        _require(
            parsed.scheme == "https"
            and parsed.hostname == "files.pythonhosted.org"
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
            and parsed.path.startswith("/packages/")
            and unquote(parsed.path.rsplit("/", 1)[-1]) == filename
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError as error:
        raise CatalogError("invalid_catalog") from error
    return Artifact(name, version, filename, url, _text(data["sha256"], _SHA256))


def _artifacts(value: Any) -> tuple[Artifact, ...]:
    _require(isinstance(value, list) and bool(value))
    artifacts = tuple(_artifact(item) for item in value)
    versions: dict[str, str] = {}
    filenames: set[str] = set()
    for artifact in artifacts:
        _require(artifact.filename not in filenames, "duplicate_artifact")
        _require(versions.get(artifact.name, artifact.version) == artifact.version)
        filenames.add(artifact.filename)
        versions[artifact.name] = artifact.version
    return artifacts


def _candidate(value: Any) -> Candidate:
    data = _mapping(
        value,
        {
            "id",
            "version",
            "source",
            "wheel_filename",
            "python",
            "platforms",
            "capabilities",
            "runtime_artifacts",
            "build_artifacts",
        },
    )
    source = _mapping(data["source"], {"commit", "url", "sha256"})
    commit = _text(source["commit"], _COMMIT)
    _require(source["url"] == _SOURCE_ROOT + commit, "untrusted_source")
    version = _text(data["version"], _VERSION)
    _require(data["wheel_filename"] == f"reprollm-{version}-py3-none-any.whl")
    python = _mapping(data["python"], {"min", "max"})
    lower, upper = _python(python["min"]), _python(python["max"])
    _require(lower <= upper)
    platforms = _strings(data["platforms"], re.compile(r"linux|darwin|win32"))
    capabilities = _strings(data["capabilities"], re.compile(r"[a-z][a-z0-9_]*"))
    return Candidate(
        id=_text(data["id"], _ID),
        version=version,
        source_commit=commit,
        source_url=source["url"],
        source_sha256=_text(source["sha256"], _SHA256),
        wheel_filename=data["wheel_filename"],
        python_min=lower,
        python_max=upper,
        platforms=platforms,
        capabilities=capabilities,
        runtime_artifacts=_artifacts(data["runtime_artifacts"]),
        build_artifacts=_artifacts(data["build_artifacts"]),
    )


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in data, "duplicate_catalog_key")
        data[key] = value
    return data


def load_catalog(path: Path) -> Catalog:
    try:
        raw = path.read_bytes()
        _require(len(raw) <= 2 * 1024 * 1024, "catalog_size_limit")
        data = _mapping(
            json.loads(raw, object_pairs_hook=_unique_keys),
            {"schema_version", "default_candidate", "candidates"},
        )
        _require(type(data["schema_version"]) is int and data["schema_version"] == 1)
        items = data["candidates"]
        _require(isinstance(items, list) and bool(items))
        candidates = tuple(_candidate(item) for item in items)
        _require(len({candidate.id for candidate in candidates}) == len(candidates))
        default = _text(data["default_candidate"], _ID)
        catalog = Catalog(1, default, candidates)
        catalog.get_candidate()
        return catalog
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise CatalogError("catalog_unreadable") from error


def validate_blob(identity: Artifact | Candidate, data: bytes) -> None:
    expected = identity.sha256 if isinstance(identity, Artifact) else identity.source_sha256
    _require(hashlib.sha256(data).hexdigest() == expected, "artifact_hash_mismatch")
