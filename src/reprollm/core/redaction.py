"""Normative secret policy (spec §16); retain 100% branch coverage."""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import PurePosixPath
from typing import Literal

SECRET_SEGMENTS: frozenset[str] = frozenset(
    {
        "KEY",
        "TOKEN",
        "SECRET",
        "PASSWORD",
        "PASSWD",
        "CREDENTIAL",
        "CREDENTIALS",
        "AUTH",
        "PRIVATE",
        "COOKIE",
        "SESSION",
    }
)
KNOWN_SECRET_NAMES: frozenset[str] = frozenset(
    {
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "HUGGINGFACEHUB_API_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "WANDB_API_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "DATABASE_URL",
        "AZURE_OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    }
)
ENV_ALLOWLIST: tuple[str, ...] = (
    "CUDA_",
    "NCCL_",
    "TORCH_",
    "PYTORCH_",
    "OMP_",
    "MKL_",
    "TRANSFORMERS_",
    "HF_HOME",
    "HF_HUB_OFFLINE",
    "HF_HUB_DISABLE",
    "VLLM_",
    "SLURM_",
    "PBS_",
    "LSB_",
    "PYTHON",
    "VIRTUAL_ENV",
    "CONDA_",
    "TOKENIZERS_PARALLELISM",
    "WANDB_MODE",
    "LD_LIBRARY_PATH",
    "PATH",
    "LANG",
    "LC_",
    "TZ",
)

# Order is normative: overlapping classes are applied in this sequence (§16.2).
_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    ("huggingface", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    (
        "github",
        re.compile(
            r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b"
        ),
    ),
    ("aws", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{8,}={0,2}\.[A-Za-z0-9_-]{8,}={0,2}\.[A-Za-z0-9_-]{8,}={0,2}(?![A-Za-z0-9_=-])"
        ),
    ),
    (
        "pem",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    ),
    ("url_cred", re.compile(r"(?<=://)[^/\s:@]+:[^/\s@]+(?=@)")),
    (
        "generic_kv",
        re.compile(
            r"""(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd)\b\s*[:=]\s*["']?([^\s"']{8,})"""
        ),
    ),
)
_PEM_BEGIN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_PEM_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY-----")


def is_secret_env_name(name: str) -> bool:
    upper = name.upper()
    return upper in KNOWN_SECRET_NAMES or any(part in SECRET_SEGMENTS for part in upper.split("_"))


def _redact_generic_value(match: re.Match[str]) -> str:
    return match.group(0)[: match.start(2) - match.start()] + "<REDACTED:generic_kv>"


def redact_text(text: str) -> tuple[str, int]:
    """Apply the nine value patterns and count substitutions in policy order."""
    total = 0
    for kind, pattern in _VALUE_PATTERNS:
        if kind == "generic_kv":
            text, count = pattern.subn(_redact_generic_value, text)
        else:
            text, count = pattern.subn(f"<REDACTED:{kind}>", text)
        total += count
    return text, total


def redact_env(
    env: Mapping[str, str],
    mode: Literal["allowlist", "all"],
    extra_allowlist: Sequence[str] = (),
) -> dict[str, str | dict[str, bool]]:
    """Known credentials retain presence only; custom unlisted names are omitted."""
    if mode not in ("allowlist", "all"):
        raise ValueError("env_capture must be allowlist or all")
    prefixes = ENV_ALLOWLIST + tuple(extra_allowlist)
    captured: dict[str, str | dict[str, bool]] = {}
    for name in sorted(env):
        if (
            mode == "allowlist"
            and name.upper() not in KNOWN_SECRET_NAMES
            and not name.startswith(prefixes)
        ):
            continue
        if is_secret_env_name(name):
            captured[name] = {"present": True}
        else:
            captured[name] = redact_text(env[name])[0]
    return captured


def redact_lines(lines: Iterable[str]) -> Iterator[str]:
    """Redact text incrementally, discarding PEM bodies even if EOF lacks an end marker."""
    inside_pem = False
    for line in lines:
        remaining = line
        while remaining:
            marker = (_PEM_END if inside_pem else _PEM_BEGIN).search(remaining)
            if marker is None:
                if not inside_pem:
                    yield redact_text(remaining)[0]
                break
            if inside_pem:
                inside_pem = False
            else:
                yield redact_text(remaining[: marker.start()])[0] + "<REDACTED:pem>"
                inside_pem = True
            remaining = remaining[marker.end() :]


#: Never snapshot or send these; their hashes MAY be recorded (spec §16.4).
FORBIDDEN_GLOBS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "id_ed25519*",
    "credentials*",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*_rsa",
    ".netrc",
    ".npmrc",
    ".pypirc",
)

#: Template names exempt from the forbidden list (still value-redacted).
EXEMPT_TEMPLATE_NAMES: frozenset[str] = frozenset({".env.example", ".env.sample", ".env.template"})


def is_forbidden_file(rel_path: str) -> bool:
    """True for secret-bearing file names (§16.4), exempting the templates.

    Matches on the basename, case-insensitively; directory components are
    irrelevant (``config/.env`` is as forbidden as ``.env``).
    """
    name = PurePosixPath(rel_path).name.lower()
    if name in EXEMPT_TEMPLATE_NAMES:
        return False
    return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in FORBIDDEN_GLOBS)
