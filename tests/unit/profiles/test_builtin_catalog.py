"""Built-in profile selection and severity contracts (spec §6.1, M3-T06)."""

from pathlib import Path

import pytest

import reprollm.rules  # noqa: F401 — register the catalog before resolving profiles
from reprollm.core.registry import get_rule
from reprollm.profiles.loader import builtin_profile_names, load_builtin, resolve

OWN_RULES = {
    "core": {
        "code.git_repo",
        "code.git_commit",
        "code.clean_tree",
        "code.no_untracked",
        "code.submodules_initialized",
        "code.remote_recorded",
        "env.dependency_manifest_present",
        "env.lockfile_present",
        "env.llm_critical_deps_pinned",
        "env.python_version_declared",
        "env.secret_files_ignored",
        "env.reprollm_initialized",
        "exec.command_declared",
        "exec.seed_declared",
        "exec.run_recorded",
        "exec.profile_detection_mismatch",
        "model.primary_declared",
        "model.provider_known",
        "model.revision_pinned",
        "model.tokenizer_pinned",
        "model.dtype_declared",
        "model.trust_remote_code_declared",
        "dataset.revision_pinned",
        "dataset.split_declared",
        "dataset.local_files_hashed",
        "prompt.file_exists",
        "prompt.hashed",
        "gen.backend_version_locked",
        "consistency.lock_fresh",
        "consistency.file_hashes",
        "consistency.generation_params",
        "consistency.model_identity",
        "consistency.env_vs_lock",
        "consistency.custom_fields",
    },
    "inference": {
        "gen.params_declared",
        "gen.backend_declared",
        "gen.backend_config_declared",
        "gen.seed_declared",
        "gen.stop_declared",
        "model.chat_template_hashed",
        "model.quantization_declared",
        "prompt.declared",
        "prompt.few_shot_declared",
    },
    "evaluation": {
        "dataset.declared",
        "dataset.preprocessing_declared",
        "dataset.sampling_seed_declared",
        "dataset.subset_declared",
        "eval.metrics_declared",
        "eval.metric_implementation_referenced",
        "eval.aggregation_declared",
        "eval.repetitions_declared",
    },
    "llm_judge": {
        "judge.model_declared",
        "judge.prompt_declared",
        "judge.prompt_hashed",
        "judge.params_declared",
        "judge.pinnability_recorded",
        "judge.repetitions_declared",
    },
    "finetuning": {
        "model.adapter_declared",
        "dataset.declared",
        "dataset.preprocessing_declared",
        "train.method_declared",
        "train.hyperparameters_declared",
        "train.optimizer_declared",
        "train.precision_declared",
        "train.lora_config_complete",
    },
    "safety": {"eval.definitions_declared", "eval.query_budget_declared"},
    "privacy": {
        "privacy.threat_model_declared",
        "privacy.mechanism_declared",
        "privacy.metrics_declared",
        "privacy.attack_config_declared",
    },
}

OVERRIDES = {
    "core": {},
    "inference": {
        "gen.params_declared": "CRITICAL",
        "gen.backend_declared": "CRITICAL",
        "model.quantization_declared": "WARNING",
    },
    "evaluation": {
        "dataset.declared": "CRITICAL",
        "dataset.revision_pinned": "CRITICAL",
        "dataset.sampling_seed_declared": "CRITICAL",
        "eval.metrics_declared": "CRITICAL",
        "exec.seed_declared": "CRITICAL",
        "gen.seed_declared": "CRITICAL",
    },
    "llm_judge": {},
    "finetuning": {"exec.seed_declared": "CRITICAL", "dataset.declared": "CRITICAL"},
    "safety": {"eval.definitions_declared": "CRITICAL"},
    "privacy": {},
}


@pytest.mark.parametrize("name", sorted(OWN_RULES))
def test_builtin_own_rules_match_specification(name: str) -> None:
    profile = load_builtin(name)
    assert set(profile.rules) == OWN_RULES[name]
    assert len(profile.rules) == len(set(profile.rules))


@pytest.mark.parametrize("name", sorted(OVERRIDES))
def test_builtin_severity_overrides_match_specification(name: str) -> None:
    assert load_builtin(name).severity_overrides == OVERRIDES[name]


@pytest.mark.parametrize("name", sorted(OWN_RULES))
def test_every_builtin_resolves_only_registered_rules(name: str, tmp_path: Path) -> None:
    resolved = resolve([] if name == "core" else [name], tmp_path)
    assert OWN_RULES[name] <= set(resolved.rules)
    assert all(get_rule(rule_id) is not None for rule_id in resolved.rules)


def test_builtin_catalog_has_exactly_the_seven_beta_profiles() -> None:
    assert builtin_profile_names() == sorted(OWN_RULES)


@pytest.mark.parametrize("name", sorted(OWN_RULES))
def test_builtin_drift_overrides_use_only_specified_profile_policy(name: str) -> None:
    expected = {"evaluation.judge.*": "HIGH"} if name == "llm_judge" else {}
    assert load_builtin(name).drift_overrides == expected
