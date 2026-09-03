"""Interpreter, platform, and installed-package information (spec §4.4).

Versions are read with ``importlib.metadata`` only; ReproLLM never imports the
target packages (D-30).
"""

from __future__ import annotations

import importlib.metadata
import platform
import sys
from collections.abc import Iterable

#: The LLM-critical package list (spec §4.4). Keys as used in declarations;
#: values are the distribution names on PyPI when they differ.
LLM_CRITICAL_PACKAGES: tuple[str, ...] = (
    "torch",
    "transformers",
    "tokenizers",
    "datasets",
    "accelerate",
    "peft",
    "trl",
    "vllm",
    "sglang",
    "openai",
    "anthropic",
    "numpy",
    "safetensors",
    "deepspeed",
    "flash_attn",
    "xformers",
    "bitsandbytes",
    "sentencepiece",
    "evaluate",
    "lm_eval",
    "lighteval",
    "inspect_ai",
)

#: Name-as-listed → distribution name (importlib.metadata).
_DISTRIBUTION_NAMES: dict[str, str] = {
    "flash_attn": "flash-attn",
    "inspect_ai": "inspect-ai",
}


def distribution_name(name: str) -> str:
    return _DISTRIBUTION_NAMES.get(name, name)


def installed_versions(names: Iterable[str] | None = None) -> dict[str, str]:
    """Versions of installed packages, keyed by the name as listed; absent → omitted."""
    if names is None:
        names = LLM_CRITICAL_PACKAGES
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(distribution_name(name))
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions


def python_version() -> str:
    return platform.python_version()


def platform_name() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform == "win32":
        return "windows"
    return sys.platform


def os_description() -> str:
    return platform.platform()
