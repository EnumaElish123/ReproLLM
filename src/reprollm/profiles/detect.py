"""Deterministic profile detection (spec §13, D-25).

No LLM, no free-text config *values*: only Python AST imports, dependency
names, README text, configuration **key** names, directory names, and file
stems. Keyword matching is case-insensitive and word-boundary based, with
``-``/``_``/space treated as equivalent separators — a bare substring never
matches ("storage" must not match ``rag``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from reprollm.core._toml import tomllib
from reprollm.core.deps import Declarations, canonical_dep_name
from reprollm.core.pyscan import PyScanResult
from reprollm.core.scanner import RepoScanner
from reprollm.schemas.finding import DetectionResult, Evidence, ProfileDetection
from reprollm.schemas.profile import DetectSignals

#: Keyword lists per profile (§13 signal table). Order is irrelevant; hits are
#: counted as *distinct keywords*.
#: Report-only profile descriptors (rag/agent are not shipped in the Beta).
#: Kept in this single internal source until those profiles ship; shipped
#: profiles' signals come from their YAML ``detect`` blocks (M2F-T10, F-11).
_REPORT_ONLY_PROFILES: dict[str, DetectSignals] = {
    "rag": DetectSignals(keywords=["retriev", "rag", "vector store", "faiss", "chroma"]),
    "agent": DetectSignals(keywords=["agent", "tool call", "tool_call", "function calling"]),
}

#: Profiles that are detected but not shipped in the Beta.
_UNSHIPPED_PROFILES: set[str] = set(_REPORT_ONLY_PROFILES)

#: Confidence rules that the profile schema cannot express (§13): imports are
#: high except these documented downgrades.
_IMPORT_CONFIDENCE_OVERRIDES: dict[str, str] = {"accelerate": "medium"}

#: Import module → hint recorded in DetectionHints (providers/backends/
#: datasets/adapter). These are hints, never profile signals.
_IMPORT_HINTS: dict[str, str] = {
    "openai": "provider:openai",
    "anthropic": "provider:anthropic",
    "datasets": "datasets",
    "vllm": "backend:vllm",
    "sglang": "backend:sglang",
    "peft": "adapter",
}

#: Exact directory-segment signals (§13): one canonical concept per profile
#: regardless of alias count; cannot be expressed as the schema's file globs.
_DIRECTORY_SIGNALS: dict[str, tuple[str, ...]] = {
    "evaluation": ("eval", "evaluation"),
}

#: Prefix keywords (normalized form) that intentionally match word stems.
_PREFIX_KEYWORDS = {"fine tun", "finetun", "retriev"}


def detection_signals(root: Path) -> dict[str, DetectSignals]:
    """The single source of detection signals: shipped profile YAML ``detect``
    blocks (user overrides honored) plus the report-only descriptors."""
    from reprollm.profiles import loader

    signals: dict[str, DetectSignals] = {}
    for name in loader.known_profile_names(root):
        signals[name] = loader.load_profile(root, name).detect
    signals.update(_REPORT_ONLY_PROFILES)
    return signals


_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
_EVIDENCE_CAP = 5


@dataclass(frozen=True)
class KeywordSource:
    """Where a keyword was found (README text / config key / dir / file stem)."""

    kind: str  # "readme" | "config-key" | "dir" | "file-stem"
    path: str
    subject: str  # the key name / dir name / stem that matched


def _normalize(text: str) -> str:
    return text.replace("-", " ").replace("_", " ").lower()


def keyword_matches(keyword: str, haystack: str) -> bool:
    """Word-boundary match with ``-``/``_``/space treated as equivalent."""
    keyword = _normalize(keyword).strip()
    if not keyword:
        return False
    haystack = _normalize(haystack)
    body = re.escape(keyword).replace(r"\ ", r"\s+")
    suffix = "" if keyword in _PREFIX_KEYWORDS else r"(?!\w)"
    return re.search(rf"(?<!\w){body}{suffix}", haystack) is not None


def run_detection(
    scanner: RepoScanner,
    pyscan: PyScanResult,
    deps: Declarations,
    signals: dict[str, DetectSignals] | None = None,
) -> DetectionResult:
    """Detect experiment profiles and hints deterministically (§13).

    Generic signals (imports/dependencies/keywords) come from the profile
    definitions in ``signals`` — normally :func:`detection_signals`, i.e. the
    shipped YAML plus user overrides; only schema-inexpressible semantics
    (confidence downgrades, Trainer AST recognition, hints, directory
    segments, report-only metadata, canonical keyword matching) live here.
    """
    if signals is None:
        signals = detection_signals(scanner.root)

    entries: dict[str, tuple[str, list[Evidence]]] = {}
    providers: list[str] = []
    backends: list[str] = []
    datasets_hint = False
    adapter_hint = False

    modules = pyscan.module_names()
    for profile, sig in sorted(signals.items()):
        for module in sorted(sig.imports):
            hits = [info for info in pyscan.imports if info.module.split(".", 1)[0] == module]
            if not hits:
                continue
            confidence = _IMPORT_CONFIDENCE_OVERRIDES.get(module, "high")
            _record(
                entries,
                profile,
                confidence,
                [
                    Evidence(
                        kind="detection",
                        path=hits[0].path,
                        line=hits[0].line,
                        note=f"import {module}",
                    )
                ],
            )

        for dep in sorted(sig.dependencies):
            canonical = canonical_dep_name(dep)
            matching = [d for d in deps.declarations if d.name == canonical]
            if not matching:
                continue
            best = matching[0]
            _record(
                entries,
                profile,
                "medium",
                [
                    Evidence(
                        kind="detection",
                        path=best.source_file,
                        line=best.line,
                        note=f"dependency {best.display_name}",
                    )
                ],
            )

    # AST-only signal: from transformers import Trainer|Seq2SeqTrainer|
    # TrainingArguments → finetuning high (schema cannot express symbols).
    if pyscan.trainer_import and "finetuning" in signals:
        trainer_hits = [info for info in pyscan.imports if info.module == "transformers"]
        path = trainer_hits[0].path if trainer_hits else ""
        line = trainer_hits[0].line if trainer_hits else None
        _record(
            entries,
            "finetuning",
            "high",
            [
                Evidence(
                    kind="detection",
                    path=path,
                    line=line,
                    note="from transformers import Trainer|Seq2SeqTrainer|TrainingArguments",
                )
            ],
        )

    # Hints never create profile signals (§13).
    for module, hint in _IMPORT_HINTS.items():
        if module not in modules:
            continue
        if hint.startswith("provider:"):
            provider = hint.split(":", 1)[1]
            if provider not in providers:
                providers.append(provider)
        elif hint.startswith("backend:"):
            backend = hint.split(":", 1)[1]
            if backend not in backends:
                backends.append(backend)
        elif hint == "datasets":
            datasets_hint = True
        elif hint == "adapter":
            adapter_hint = True

    _scan_keywords(scanner, entries, signals)

    detected = [
        ProfileDetection(
            profile=profile,
            confidence=confidence,
            evidence=sorted(
                evidence,
                key=lambda e: (e.path or "", e.line or 0, e.note or ""),
            )[:_EVIDENCE_CAP],
            shipped=profile not in _UNSHIPPED_PROFILES,
        )
        for profile, (confidence, evidence) in sorted(entries.items())
    ]
    from reprollm.schemas.finding import DetectionHints

    return DetectionResult(
        profiles=detected,
        hints=DetectionHints(
            providers=providers,
            backends=backends,
            datasets=datasets_hint,
            adapter=adapter_hint,
            trust_remote_code=pyscan.trust_remote_code,
            hf_ids=pyscan.hf_ids,
        ),
    )


def _record(
    entries: dict[str, tuple[str, list[Evidence]]],
    profile: str,
    confidence: str,
    evidence: list[Evidence],
) -> None:
    existing = entries.get(profile)
    if existing is None or _CONFIDENCE_RANK[confidence] > _CONFIDENCE_RANK[existing[0]]:
        entries[profile] = (confidence, list(evidence))
    elif confidence == existing[0]:
        existing[1].extend(evidence)


def _scan_keywords(
    scanner: RepoScanner,
    entries: dict[str, tuple[str, list[Evidence]]],
    signals: dict[str, DetectSignals],
) -> None:
    """Count *canonical keyword concepts*, not alias spellings (M2F-T05, F-06).

    ``red team`` / ``red-team`` / ``red_team`` normalize to one concept; one
    matching span therefore counts once, and medium confidence requires two
    genuinely distinct concepts. Exact directory segments (§13) enter the
    same concept counting as one additional typed concept (M2F-T06, F-07).
    """
    sources = _keyword_sources(scanner)
    hits: dict[str, list[Evidence]] = {}
    for profile, sig in signals.items():
        keywords = sig.keywords
        matched_concepts: set[str] = set()
        profile_evidence = hits.setdefault(profile, [])

        dir_aliases = _DIRECTORY_SIGNALS.get(profile, ())
        present_dirs = [name for name in dir_aliases if name in scanner.dir_names()]
        if present_dirs:
            matched_concepts.add("directory:" + dir_aliases[0])
            representative = next(
                (p for p in scanner.files() if p.split("/", 1)[0] in dir_aliases), ""
            )
            profile_evidence.append(
                Evidence(
                    kind="detection",
                    path=representative or None,
                    note=f"directory '{present_dirs[0]}'",
                )
            )

        for keyword in keywords:
            concept = _normalize(keyword).strip()
            if concept in matched_concepts:
                continue  # an equivalent spelling already recorded this concept
            for source in sources:
                if keyword_matches(keyword, source.subject):
                    matched_concepts.add(concept)
                    profile_evidence.append(
                        Evidence(
                            kind="detection",
                            path=source.path,
                            note=f"keyword '{keyword}' in {source.kind}",
                        )
                    )
                    break  # one representative location per concept

    for profile, evidence in hits.items():
        if not evidence:
            continue
        confidence = "medium" if len(evidence) >= 2 else "low"
        _record(entries, profile, confidence, evidence)


def _keyword_sources(scanner: RepoScanner) -> list[KeywordSource]:
    sources: list[KeywordSource] = []
    for path in scanner.readme_files():
        text = scanner.read_text(path)
        if text is not None:
            sources.append(KeywordSource("readme text", path, text))
    for path in scanner.config_files():
        for key in _config_keys(scanner, path):
            sources.append(KeywordSource("config key", path, key))
    for name in sorted(scanner.dir_names()):
        sources.append(KeywordSource("directory name", "", name))
    for path in scanner.files():
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        sources.append(KeywordSource("file stem", path, stem))
    return sources


def _config_keys(scanner: RepoScanner, path: str) -> list[str]:
    text = scanner.read_text(path)
    if text is None:
        return []
    data: object = None
    suffix = Path(path).suffix.lower()
    try:
        if suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        elif suffix == ".json":
            data = json.loads(text)
        elif suffix == ".toml":
            data = tomllib.loads(text)
    except Exception:  # noqa: BLE001 - unreadable configs are skipped silently
        return []
    keys: list[str] = []
    _collect_keys(data, keys)
    return keys


def _collect_keys(node: object, keys: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str):
                keys.append(key)
            _collect_keys(value, keys)
    elif isinstance(node, list):
        for item in node:
            _collect_keys(item, keys)
