"""envinfo tests (spec §4.4)."""

from reprollm.core.envinfo import (
    LLM_CRITICAL_PACKAGES,
    distribution_name,
    installed_versions,
    os_description,
    platform_name,
    python_version,
)


def test_llm_critical_package_list_matches_spec() -> None:
    assert LLM_CRITICAL_PACKAGES == (
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


def test_distribution_name_overrides() -> None:
    assert distribution_name("flash_attn") == "flash-attn"
    assert distribution_name("inspect_ai") == "inspect-ai"
    assert distribution_name("lm_eval") == "lm_eval"
    assert distribution_name("torch") == "torch"


def test_installed_versions_reports_installed_only() -> None:
    versions = installed_versions(["pytest", "reprollm-not-a-real-pkg-xyz"])
    assert "pytest" in versions
    assert "reprollm-not-a-real-pkg-xyz" not in versions


def test_installed_versions_default_is_llm_critical() -> None:
    versions = installed_versions()
    assert set(versions).issubset(set(LLM_CRITICAL_PACKAGES))


def test_platform_and_python() -> None:
    assert platform_name() in {"linux", "darwin", "windows"}
    assert python_version().count(".") == 2
    assert os_description()
