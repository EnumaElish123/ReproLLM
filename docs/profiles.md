# Built-in profiles

This file is generated from `src/reprollm/profiles/*.yaml`.
Run `python scripts/gen_profiles_doc.py` after changing a built-in profile.

`core` is included implicitly and must not appear in `experiment.profiles`.

## `core`

Baseline rules applied to every repository.

- Extends: —
- Resolution order: `core`
- Required fields: `project.name`, `models.primary.id`
- Severity overrides: —
- Drift overrides: —
- Detection imports: —
- Detection dependencies: —
- Detection keywords: —
- Detection files: —

Effective rules (34):

- `code.clean_tree`
- `code.git_commit`
- `code.git_repo`
- `code.no_untracked`
- `code.remote_recorded`
- `code.submodules_initialized`
- `consistency.custom_fields`
- `consistency.env_vs_lock`
- `consistency.file_hashes`
- `consistency.generation_params`
- `consistency.lock_fresh`
- `consistency.model_identity`
- `dataset.local_files_hashed`
- `dataset.revision_pinned`
- `dataset.split_declared`
- `env.dependency_manifest_present`
- `env.llm_critical_deps_pinned`
- `env.lockfile_present`
- `env.python_version_declared`
- `env.reprollm_initialized`
- `env.secret_files_ignored`
- `exec.command_declared`
- `exec.profile_detection_mismatch`
- `exec.run_recorded`
- `exec.seed_declared`
- `gen.backend_version_locked`
- `model.dtype_declared`
- `model.primary_declared`
- `model.provider_known`
- `model.revision_pinned`
- `model.tokenizer_pinned`
- `model.trust_remote_code_declared`
- `prompt.file_exists`
- `prompt.hashed`

## `evaluation`

Benchmark and evaluation experiments (datasets and metrics).

- Extends: `inference`
- Resolution order: `core`, `inference`, `evaluation`
- Required fields: `project.name`, `models.primary.id`, `inference.backend`, `generation.temperature`, `generation.max_tokens`, `datasets.eval.id`, `evaluation.metrics`
- Severity overrides: `dataset.declared`: CRITICAL, `dataset.revision_pinned`: CRITICAL, `dataset.sampling_seed_declared`: CRITICAL, `eval.metrics_declared`: CRITICAL, `exec.seed_declared`: CRITICAL, `gen.backend_declared`: CRITICAL, `gen.params_declared`: CRITICAL, `gen.seed_declared`: CRITICAL, `model.quantization_declared`: WARNING
- Drift overrides: —
- Detection imports: `vllm`, `sglang`, `lm_eval`, `lighteval`, `inspect_ai`, `evaluate`
- Detection dependencies: `vllm`, `sglang`, `lm_eval`, `lighteval`, `inspect_ai`, `evaluate`
- Detection keywords: `mmlu`, `gsm8k`, `benchmark`, `accuracy`
- Detection files: —

Effective rules (51):

- `code.clean_tree`
- `code.git_commit`
- `code.git_repo`
- `code.no_untracked`
- `code.remote_recorded`
- `code.submodules_initialized`
- `consistency.custom_fields`
- `consistency.env_vs_lock`
- `consistency.file_hashes`
- `consistency.generation_params`
- `consistency.lock_fresh`
- `consistency.model_identity`
- `dataset.declared`
- `dataset.local_files_hashed`
- `dataset.preprocessing_declared`
- `dataset.revision_pinned`
- `dataset.sampling_seed_declared`
- `dataset.split_declared`
- `dataset.subset_declared`
- `env.dependency_manifest_present`
- `env.llm_critical_deps_pinned`
- `env.lockfile_present`
- `env.python_version_declared`
- `env.reprollm_initialized`
- `env.secret_files_ignored`
- `eval.aggregation_declared`
- `eval.metric_implementation_referenced`
- `eval.metrics_declared`
- `eval.repetitions_declared`
- `exec.command_declared`
- `exec.profile_detection_mismatch`
- `exec.run_recorded`
- `exec.seed_declared`
- `gen.backend_config_declared`
- `gen.backend_declared`
- `gen.backend_version_locked`
- `gen.params_declared`
- `gen.seed_declared`
- `gen.stop_declared`
- `model.chat_template_hashed`
- `model.dtype_declared`
- `model.primary_declared`
- `model.provider_known`
- `model.quantization_declared`
- `model.revision_pinned`
- `model.tokenizer_pinned`
- `model.trust_remote_code_declared`
- `prompt.declared`
- `prompt.few_shot_declared`
- `prompt.file_exists`
- `prompt.hashed`

## `finetuning`

Fine-tuning experiments (method, hyperparameters, adapters).

- Extends: `core`
- Resolution order: `core`, `finetuning`
- Required fields: `project.name`, `models.primary.id`, `training.method`, `training.learning_rate`, `datasets.train.id`
- Severity overrides: `dataset.declared`: CRITICAL, `exec.seed_declared`: CRITICAL
- Drift overrides: —
- Detection imports: `peft`, `trl`, `deepspeed`, `accelerate`
- Detection dependencies: `peft`, `trl`, `deepspeed`, `accelerate`
- Detection keywords: `lora`, `fine-tun`, `finetun`, `sft`, `dpo`, `rlhf`
- Detection files: —

Effective rules (42):

- `code.clean_tree`
- `code.git_commit`
- `code.git_repo`
- `code.no_untracked`
- `code.remote_recorded`
- `code.submodules_initialized`
- `consistency.custom_fields`
- `consistency.env_vs_lock`
- `consistency.file_hashes`
- `consistency.generation_params`
- `consistency.lock_fresh`
- `consistency.model_identity`
- `dataset.declared`
- `dataset.local_files_hashed`
- `dataset.preprocessing_declared`
- `dataset.revision_pinned`
- `dataset.split_declared`
- `env.dependency_manifest_present`
- `env.llm_critical_deps_pinned`
- `env.lockfile_present`
- `env.python_version_declared`
- `env.reprollm_initialized`
- `env.secret_files_ignored`
- `exec.command_declared`
- `exec.profile_detection_mismatch`
- `exec.run_recorded`
- `exec.seed_declared`
- `gen.backend_version_locked`
- `model.adapter_declared`
- `model.dtype_declared`
- `model.primary_declared`
- `model.provider_known`
- `model.revision_pinned`
- `model.tokenizer_pinned`
- `model.trust_remote_code_declared`
- `prompt.file_exists`
- `prompt.hashed`
- `train.hyperparameters_declared`
- `train.lora_config_complete`
- `train.method_declared`
- `train.optimizer_declared`
- `train.precision_declared`

## `inference`

LLM inference experiments (generation parameters and backend).

- Extends: `core`
- Resolution order: `core`, `inference`
- Required fields: `project.name`, `models.primary.id`, `inference.backend`, `generation.temperature`, `generation.max_tokens`
- Severity overrides: `gen.backend_declared`: CRITICAL, `gen.params_declared`: CRITICAL, `model.quantization_declared`: WARNING
- Drift overrides: —
- Detection imports: `vllm`, `sglang`
- Detection dependencies: `vllm`, `sglang`
- Detection keywords: —
- Detection files: —

Effective rules (43):

- `code.clean_tree`
- `code.git_commit`
- `code.git_repo`
- `code.no_untracked`
- `code.remote_recorded`
- `code.submodules_initialized`
- `consistency.custom_fields`
- `consistency.env_vs_lock`
- `consistency.file_hashes`
- `consistency.generation_params`
- `consistency.lock_fresh`
- `consistency.model_identity`
- `dataset.local_files_hashed`
- `dataset.revision_pinned`
- `dataset.split_declared`
- `env.dependency_manifest_present`
- `env.llm_critical_deps_pinned`
- `env.lockfile_present`
- `env.python_version_declared`
- `env.reprollm_initialized`
- `env.secret_files_ignored`
- `exec.command_declared`
- `exec.profile_detection_mismatch`
- `exec.run_recorded`
- `exec.seed_declared`
- `gen.backend_config_declared`
- `gen.backend_declared`
- `gen.backend_version_locked`
- `gen.params_declared`
- `gen.seed_declared`
- `gen.stop_declared`
- `model.chat_template_hashed`
- `model.dtype_declared`
- `model.primary_declared`
- `model.provider_known`
- `model.quantization_declared`
- `model.revision_pinned`
- `model.tokenizer_pinned`
- `model.trust_remote_code_declared`
- `prompt.declared`
- `prompt.few_shot_declared`
- `prompt.file_exists`
- `prompt.hashed`

## `llm_judge`

LLM-as-a-judge evaluation (judge model, prompt, and parameters).

- Extends: `evaluation`
- Resolution order: `core`, `inference`, `evaluation`, `llm_judge`
- Required fields: `project.name`, `models.primary.id`, `inference.backend`, `generation.temperature`, `generation.max_tokens`, `datasets.eval.id`, `evaluation.metrics`, `models.judge.id`, `prompts.judge.path`, `evaluation.judge.params.temperature`
- Severity overrides: `dataset.declared`: CRITICAL, `dataset.revision_pinned`: CRITICAL, `dataset.sampling_seed_declared`: CRITICAL, `eval.metrics_declared`: CRITICAL, `exec.seed_declared`: CRITICAL, `gen.backend_declared`: CRITICAL, `gen.params_declared`: CRITICAL, `gen.seed_declared`: CRITICAL, `model.quantization_declared`: WARNING
- Drift overrides: `evaluation.judge.*`: HIGH
- Detection imports: `vllm`, `sglang`, `lm_eval`, `lighteval`, `inspect_ai`, `evaluate`
- Detection dependencies: `vllm`, `sglang`, `lm_eval`, `lighteval`, `inspect_ai`, `evaluate`
- Detection keywords: `mmlu`, `gsm8k`, `benchmark`, `accuracy`, `judge`, `llm-as-a-judge`, `llm_judge`, `rubric`, `grader`
- Detection files: —

Effective rules (57):

- `code.clean_tree`
- `code.git_commit`
- `code.git_repo`
- `code.no_untracked`
- `code.remote_recorded`
- `code.submodules_initialized`
- `consistency.custom_fields`
- `consistency.env_vs_lock`
- `consistency.file_hashes`
- `consistency.generation_params`
- `consistency.lock_fresh`
- `consistency.model_identity`
- `dataset.declared`
- `dataset.local_files_hashed`
- `dataset.preprocessing_declared`
- `dataset.revision_pinned`
- `dataset.sampling_seed_declared`
- `dataset.split_declared`
- `dataset.subset_declared`
- `env.dependency_manifest_present`
- `env.llm_critical_deps_pinned`
- `env.lockfile_present`
- `env.python_version_declared`
- `env.reprollm_initialized`
- `env.secret_files_ignored`
- `eval.aggregation_declared`
- `eval.metric_implementation_referenced`
- `eval.metrics_declared`
- `eval.repetitions_declared`
- `exec.command_declared`
- `exec.profile_detection_mismatch`
- `exec.run_recorded`
- `exec.seed_declared`
- `gen.backend_config_declared`
- `gen.backend_declared`
- `gen.backend_version_locked`
- `gen.params_declared`
- `gen.seed_declared`
- `gen.stop_declared`
- `judge.model_declared`
- `judge.params_declared`
- `judge.pinnability_recorded`
- `judge.prompt_declared`
- `judge.prompt_hashed`
- `judge.repetitions_declared`
- `model.chat_template_hashed`
- `model.dtype_declared`
- `model.primary_declared`
- `model.provider_known`
- `model.quantization_declared`
- `model.revision_pinned`
- `model.tokenizer_pinned`
- `model.trust_remote_code_declared`
- `prompt.declared`
- `prompt.few_shot_declared`
- `prompt.file_exists`
- `prompt.hashed`

## `privacy`

Privacy-preserving LLM experiments (threat model and mechanism).

- Extends: `core`
- Resolution order: `core`, `privacy`
- Required fields: `project.name`, `models.primary.id`, `privacy.threat_model`, `privacy.mechanism.name`
- Severity overrides: —
- Drift overrides: —
- Detection imports: —
- Detection dependencies: —
- Detection keywords: `differential privacy`, `epsilon`, `membership inference`, `threat model`, `privacy budget`, `dp-sgd`, `dp_sgd`
- Detection files: —

Effective rules (38):

- `code.clean_tree`
- `code.git_commit`
- `code.git_repo`
- `code.no_untracked`
- `code.remote_recorded`
- `code.submodules_initialized`
- `consistency.custom_fields`
- `consistency.env_vs_lock`
- `consistency.file_hashes`
- `consistency.generation_params`
- `consistency.lock_fresh`
- `consistency.model_identity`
- `dataset.local_files_hashed`
- `dataset.revision_pinned`
- `dataset.split_declared`
- `env.dependency_manifest_present`
- `env.llm_critical_deps_pinned`
- `env.lockfile_present`
- `env.python_version_declared`
- `env.reprollm_initialized`
- `env.secret_files_ignored`
- `exec.command_declared`
- `exec.profile_detection_mismatch`
- `exec.run_recorded`
- `exec.seed_declared`
- `gen.backend_version_locked`
- `model.dtype_declared`
- `model.primary_declared`
- `model.provider_known`
- `model.revision_pinned`
- `model.tokenizer_pinned`
- `model.trust_remote_code_declared`
- `privacy.attack_config_declared`
- `privacy.mechanism_declared`
- `privacy.metrics_declared`
- `privacy.threat_model_declared`
- `prompt.file_exists`
- `prompt.hashed`

## `safety`

Safety and red-team evaluations (definitions and query budgets).

- Extends: `evaluation`
- Resolution order: `core`, `inference`, `evaluation`, `safety`
- Required fields: `project.name`, `models.primary.id`, `inference.backend`, `generation.temperature`, `generation.max_tokens`, `datasets.eval.id`, `evaluation.metrics`, `evaluation.definitions.refusal`, `evaluation.definitions.asr`
- Severity overrides: `dataset.declared`: CRITICAL, `dataset.revision_pinned`: CRITICAL, `dataset.sampling_seed_declared`: CRITICAL, `eval.definitions_declared`: CRITICAL, `eval.metrics_declared`: CRITICAL, `exec.seed_declared`: CRITICAL, `gen.backend_declared`: CRITICAL, `gen.params_declared`: CRITICAL, `gen.seed_declared`: CRITICAL, `model.quantization_declared`: WARNING
- Drift overrides: —
- Detection imports: `vllm`, `sglang`, `lm_eval`, `lighteval`, `inspect_ai`, `evaluate`
- Detection dependencies: `vllm`, `sglang`, `lm_eval`, `lighteval`, `inspect_ai`, `evaluate`
- Detection keywords: `mmlu`, `gsm8k`, `benchmark`, `accuracy`, `jailbreak`, `attack success rate`, `asr`, `refusal`, `harmbench`, `advbench`, `red team`, `red-team`
- Detection files: —

Effective rules (53):

- `code.clean_tree`
- `code.git_commit`
- `code.git_repo`
- `code.no_untracked`
- `code.remote_recorded`
- `code.submodules_initialized`
- `consistency.custom_fields`
- `consistency.env_vs_lock`
- `consistency.file_hashes`
- `consistency.generation_params`
- `consistency.lock_fresh`
- `consistency.model_identity`
- `dataset.declared`
- `dataset.local_files_hashed`
- `dataset.preprocessing_declared`
- `dataset.revision_pinned`
- `dataset.sampling_seed_declared`
- `dataset.split_declared`
- `dataset.subset_declared`
- `env.dependency_manifest_present`
- `env.llm_critical_deps_pinned`
- `env.lockfile_present`
- `env.python_version_declared`
- `env.reprollm_initialized`
- `env.secret_files_ignored`
- `eval.aggregation_declared`
- `eval.definitions_declared`
- `eval.metric_implementation_referenced`
- `eval.metrics_declared`
- `eval.query_budget_declared`
- `eval.repetitions_declared`
- `exec.command_declared`
- `exec.profile_detection_mismatch`
- `exec.run_recorded`
- `exec.seed_declared`
- `gen.backend_config_declared`
- `gen.backend_declared`
- `gen.backend_version_locked`
- `gen.params_declared`
- `gen.seed_declared`
- `gen.stop_declared`
- `model.chat_template_hashed`
- `model.dtype_declared`
- `model.primary_declared`
- `model.provider_known`
- `model.quantization_declared`
- `model.revision_pinned`
- `model.tokenizer_pinned`
- `model.trust_remote_code_declared`
- `prompt.declared`
- `prompt.few_shot_declared`
- `prompt.file_exists`
- `prompt.hashed`
