# Paper checklist mapping

ReproLLM's `export --template <venue>` appends a mapping section to
`REPRODUCIBILITY.md` connecting what ReproLLM records to the reproducibility
items of three conference checklists. ReproLLM provides **evidence**, not
Yes/No answers — deciding whether the evidence satisfies a checklist item
remains the author's judgment.

Checklist versions reviewed 2026-09-29; checklists evolve, verify against the
current version when submitting.

## NeurIPS Paper Checklist — reproducibility-relevant items

| Checklist item | ReproLLM evidence |
|---|---|
| 1.6 Details on baselines and comparisons | `models.<role>.id` + revision/pinnability; `datasets.<role>.id` + revision; `evaluation.metrics` |
| 2.1 Hyperparameter search details | `training.*` section; `custom.*` project rules |
| 2.2 Range of hyperparameters | `training.learning_rate`, `training.batch_size`, `training.epochs`; `generation.temperature`, `generation.top_p` |
| 2.3 Summary of training hyperparameters | Training section of `REPRODUCIBILITY.md`; `reprollm.lock` |
| 2.4 Number of algorithms runs | `evaluation.repetitions`; `execution.seed`; run records |
| 2.5 Experimental protocol (training/inference) | `execution.command`; `.reprollm/runs/<id>/run.json` |
| 3.1 Datasets used (link, version, license) | `datasets.<role>.id` + `revision` + `content_fingerprint.status`; `preprocessing.description` |
| 3.2 Preprocessing/cleaning routines | `datasets.<role>.preprocessing.script` (hashed by lock) |
| 3.3 Data splits | `datasets.<role>.split`, `subset` |
| 3.5 Crowd-worker details | *not covered by ReproLLM* |
| 4.1 Description of evaluation metrics | `evaluation.metrics[].name` + `implementation` |
| 4.2 Details of evaluation protocol | `evaluation.aggregation`, `evaluation.repetitions`, `execution.command` |
| 4.3 Generation protocol for LLM experiments | `generation.*` section; `inference.backend`, `version`, `dtype`, `tensor_parallel_size`; `gen.params_declared` rule |
| 5.1 Information about model checkpoints | `models.<role>.revision` (exact HF commit sha); `chat_template.sha256`; `adapter.id` + `revision` |
| 5.2 Name, version, and source of LLMs | `models.<role>.id`, `provider`, `revision`, `pinnability`; `model.revision_pinned` rule |
| 5.3 Fine-tuning details | `training.method`, hyperparameters; `model.adapter_declared` rule; `consistency.model_identity` |
| 5.4 Details about prompts | `prompts.<role>` content hashes; `prompt.file_exists` rule; `prompts.<role>.path` |
| 5.5 Post-processing and decoding parameters | `generation.temperature`, `top_p`, `max_tokens`, `stop`, `seed`; `inference.*` |
| 5.6 LLM judge details | `models.judge.*`, `evaluation.judge.params`, `judge.*` rules |
| 5.7 Details of attack/defense methods | `privacy.*` section; `privacy.threat_model_declared` rule |
| 6.1 Software dependencies | `env.llm_critical_deps_pinned` rule; `reprollm.lock` `environment.packages` |
| 6.2 Software versions | `reprollm.lock` `environment.packages` (importlib.metadata); run records |
| 6.3 Hardware and compute | `hardware` section; `run -- nvidia-smi` capture |
| 6.4 Statistics needed to replicate | `evaluation.repetitions`; run-record `bindings_observed` |

## ACL Responsible NLP Research Checklist — Section B/C (reproducibility)

| Checklist item | ReproLLM evidence |
|---|---|
| B4 Research artifacts/code | `code.git_repo`, `code.clean_tree`, `code.remote_recorded`; run records |
| B5 Computational experiments reproducibility | Full pipeline: `init → lock → run → diff → export` |
| B6 Data usage | `datasets.<role>.id`, `revision`, `preprocessing`; `content_fingerprint` |
| B7 Experimental setup/details | `generation.*`, `inference.*`, `training.*`; `REPRODUCIBILITY.md` |
| B9 Model/LLM details | `models.<role>.id`, `revision`, `tokenizer`, `chat_template.sha256`, `dtype`, `quantization`, `adapter` |
| C1 NLP tasks and evaluation | `evaluation.metrics`, `aggregation`, `repetitions`; `datasets.<role>.split` |
| C3 Prompt details | `prompts.<role>.path` or inline text (hashed); `prompt.few_shot_declared` |
| C5 Human subjects | *not covered by ReproLLM* |

## ACM Artifact Review and Badging

| Badge requirement | ReproLLM evidence |
|---|---|
| **Artifacts Available** (archived, identifiable) | `reprollm.yaml` + `reprollm.lock` + `.reprollm/runs/` committed in the artifact repo |
| **Artifacts Evaluated – Reusable** (complete docs, executability) | `REPRODUCIBILITY.md` (all sections); `export --template acm` adds this mapping |
| **Artifacts Evaluated – Functional** (can reproduce results) | `reprollm run` records; `reprollm diff` between recorded and reported runs; `consistency.*` rules |
| Identity of model artifacts | `models.<role>.revision` (exact commit); `pinnability` record |
| Identity of data artifacts | `datasets.<role>.revision`; file hashes for local datasets |
| Software environment | `reprollm.lock` `environment.packages`; `env.llm_critical_deps_pinned` |
| Results reproducibility | `reprollm diff <reported-run> <your-run>`; `REPRODUCIBILITY.md` Execution section |

## Items not covered

- Human-subject research details (IRB, consent, demographics)
- Crowd-worker payment and demographics
- Statistical significance testing beyond descriptive repetitions
- License terms of datasets (ReproLLM records identity, not legal status)
- Novelty or contribution claims
