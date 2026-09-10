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

#: Keyword lists per profile (§13 signal table). Order is irrelevant; hits are
#: counted as *distinct keywords*.
PROFILE_KEYWORDS: dict[str, list[str]] = {
    "llm_judge": ["judge", "llm-as-a-judge", "llm_judge", "rubric", "grader"],
    "safety": [
        "jailbreak",
        "attack success rate",
        "asr",
        "refusal",
        "harmbench",
        "advbench",
        "red team",
        "red-team",
    ],
    "privacy": [
        "differential privacy",
        "epsilon",
        "membership inference",
        "threat model",
        "privacy budget",
        "dp-sgd",
        "dp_sgd",
    ],
    "finetuning": ["lora", "fine-tun", "finetun", "sft", "dpo", "rlhf"],
    "evaluation": ["mmlu", "gsm8k", "benchmark", "accuracy"],
    # rag/agent are reported with shipped=False (profiles not in the Beta set)
    "rag": ["retriev", "rag", "vector store", "faiss", "chroma"],
    "agent": ["agent", "tool call", "tool_call", "function calling"],
}

#: Keywords that intentionally match word prefixes (fine-tuning, retrieval…),
#: stored in normalized form (see :func:`keyword_matches`).
_PREFIX_KEYWORDS = {"fine tun", "finetun", "retriev"}

#: Profiles that are detected but not shipped in the Beta.
_UNSHIPPED_PROFILES = {"rag", "agent"}

#: Import module name → (profile, confidence, hint kind or None).
_IMPORT_SIGNALS: dict[str, tuple[str, str, str | None]] = {
    "peft": ("finetuning", "high", "adapter"),
    "trl": ("finetuning", "high", None),
    "deepspeed": ("finetuning", "high", None),
    "accelerate": ("finetuning", "medium", None),
    "vllm": ("inference", "high", "backend"),
    "sglang": ("inference", "high", "backend"),
    "lm_eval": ("evaluation", "high", None),
    "lighteval": ("evaluation", "high", None),
    "inspect_ai": ("evaluation", "high", None),
    "evaluate": ("evaluation", "high", None),
}

#: Imports recorded as hints only.
_HINT_ONLY_IMPORTS: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "datasets": "datasets",
}

#: Dependency names (canonical) that imply their profile at medium confidence.
_DEPENDENCY_SIGNALS: dict[str, tuple[str, str]] = {
    canonical_dep_name("peft"): ("finetuning", "medium"),
    canonical_dep_name("trl"): ("finetuning", "medium"),
    canonical_dep_name("deepspeed"): ("finetuning", "medium"),
    canonical_dep_name("accelerate"): ("finetuning", "medium"),
    canonical_dep_name("vllm"): ("inference", "medium"),
    canonical_dep_name("sglang"): ("inference", "medium"),
    canonical_dep_name("lm_eval"): ("evaluation", "medium"),
    canonical_dep_name("lighteval"): ("evaluation", "medium"),
    canonical_dep_name("inspect_ai"): ("evaluation", "medium"),
    canonical_dep_name("evaluate"): ("evaluation", "medium"),
}

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
    scanner: RepoScanner, pyscan: PyScanResult, deps: Declarations
) -> DetectionResult:
    """Detect experiment profiles and hints deterministically (§13)."""
    entries: dict[str, tuple[str, list[Evidence]]] = {}
    providers: list[str] = []
    backends: list[str] = []
    datasets_hint = False
    adapter_hint = False

    modules = pyscan.module_names()
    for module, (profile, confidence, hint) in _IMPORT_SIGNALS.items():
        hits = [info for info in pyscan.imports if info.module.split(".", 1)[0] == module]
        if not hits:
            continue
        _record(
            entries,
            profile,
            confidence,
            [
                Evidence(
                    kind="detection", path=hits[0].path, line=hits[0].line, note=f"import {module}"
                )
            ],
        )
        if hint == "adapter":
            adapter_hint = True
        elif hint == "backend" and module not in backends:
            backends.append(module)

    if pyscan.trainer_import:
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

    for module, hint_value in _HINT_ONLY_IMPORTS.items():
        if module in modules:
            if hint_value in {"openai", "anthropic"}:
                if hint_value not in providers:
                    providers.append(hint_value)
            else:
                datasets_hint = True

    declared = {d.name for d in deps.declarations}
    for dep_name, (profile, confidence) in _DEPENDENCY_SIGNALS.items():
        if dep_name not in declared:
            continue
        best = next(d for d in deps.declarations if d.name == dep_name)
        _record(
            entries,
            profile,
            confidence,
            [
                Evidence(
                    kind="detection",
                    path=best.source_file,
                    line=best.line,
                    note=f"dependency {best.display_name}",
                )
            ],
        )

    _scan_keywords(scanner, entries)

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


def _scan_keywords(scanner: RepoScanner, entries: dict[str, tuple[str, list[Evidence]]]) -> None:
    """Count *canonical keyword concepts*, not alias spellings (M2F-T05, F-06).

    ``red team`` / ``red-team`` / ``red_team`` normalize to one concept; one
    matching span therefore counts once, and medium confidence requires two
    genuinely distinct concepts.
    """
    sources = _keyword_sources(scanner)
    hits: dict[str, list[Evidence]] = {}
    for profile, keywords in PROFILE_KEYWORDS.items():
        matched_concepts: set[str] = set()
        for keyword in keywords:
            concept = _normalize(keyword).strip()
            if concept in matched_concepts:
                continue  # an equivalent spelling already recorded this concept
            for source in sources:
                if keyword_matches(keyword, source.subject):
                    matched_concepts.add(concept)
                    hits.setdefault(profile, []).append(
                        Evidence(
                            kind="detection",
                            path=source.path,
                            note=f"keyword '{keyword}' in {source.kind}",
                        )
                    )
                    break  # one representative location per concept
    for profile, evidence in hits.items():
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
