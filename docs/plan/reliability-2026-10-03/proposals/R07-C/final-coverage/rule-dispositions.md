# R07-C finite closure recommendation — read-only rules survey

Date: 2026-10-29. Base: `bfe355cc7f1369aed3c92196c133e5e5cd133b31`.
Status: **PROPOSED DESIGN INPUT ONLY**. No implementation/specification patch is applied by this survey.
The root agent must bind the final concrete specification and implementation patch, obtain the specific decision required by execution guide §5.9, and perform acceptance before marking R07-C closed.

## Scope and authority

The original finite task is to classify per-rule conclusions under incomplete analysis, preserve concrete positive violations, and prevent absence-derived success without appropriate support. It is not a request for unbounded dependency/Conda syntax, a solver, full filesystem completeness, or proof that a real experiment is reproducible.

Authoritative current boundaries:

- `docs/plan/01_specification.md:964–993`: the two-rule primary-Python empty-result veto, and the explicit remaining captured-view warnings/open domains.
- `docs/plan/01_specification.md:999–1049`: profile absence branch and preservation of positive high-confidence mismatches.
- `docs/plan/01_specification.md:1977–2047`: accepted D-I remains narrow; broader domains require a specific decision.
- `docs/plan/reliability-2026-10-03/05_Policy_and_Compatibility.md:260–286`: required rule table, concrete witnesses, four-way conditions, full comparisons and explicit protected-module review where applicable.
- `docs/plan/00_architecture_and_decisions.md:194,269`: Python-only/static target scope and protected engine/redaction/schema review.

The current 69 builtin literal IDs were re-enumerated with Python AST from the actual source. The older rule-evidence packet remains historical rather than being silently rewritten.

## A: one bounded six-rule decision

### Eligible-view boundary

Keep the existing captured eligible file view: Git listing or non-Git walk, existing hard run exclusion, size cap, environment/generated exclusions, supported file grammars, safe physical path and consumer budgets. A deliberate exclusion or known over-2-MiB file is part of that boundary, not a producer failure. Do not retry, broaden roots, read excluded files, infer hidden imports, or infer complete filesystem coverage.

Record only a known failure encountered by an existing operation, with typed internal facts and safe relative source paths. Do not derive facts from warnings, stderr, absence of a finding, or a new second traversal. A successful listing can still be a changing, non-atomic view; state no stronger guarantee.

Listing gaps: failed `git ls-files`, observed non-Git `os.walk` error, observed stat error during listing. Preserve `ls_files()` compatibility for other consumers and use one existing subprocess result; do not issue an extra Git command.

Non-Python detection gaps: actual eligible README/config/framework body unavailable within its existing budget, actual JSON/YAML/TOML decode failure, actual supported shell tokenization failure, or a recorded existing framework cap preventing visited candidate analysis. Intentional early success/short-circuit does not create a failure for unvisited files. Generic unreadable config facts do not contaminate critical dependency credit. A successfully decoded nonmapping value is an intentional nonmatching value unless current parser semantics explicitly require a mapping.

Dependency detection gaps may reuse existing declaration-read, supported unexpanded-include and excluded-include facts when those can conceal a supported dependency signal. Do not turn every `unparsed` prose entry or every unsupported grammar into a new failure. Actual qualified/exact credit and all accepted D-F/S→D-L→D-M→D-G→D-I findings preserve their current priority, complete message, hints and evidence.

The public persisted DetectionResult/AuditReport schemas remain unchanged. Use internal source-specific coverage objects or scanner facts; only explicit consumers choose a veto. The existing Rule.pass_skip_reason hook can handle new empty-result vetoes without editing engine.py; nonempty absence findings are changed in the owning rule.

### Exact rule dispositions

1. **env.dependency_manifest_present**: an observed supported presence witness still suffices for PASS. If no witness is captured and listing is known incomplete, emit SKIPPED/INFO with an explicit unavailable-listing reason instead of the former CRITICAL absence. Body parsing is not newly required for this existence rule.
2. **env.lockfile_present**: an observed existing qualified lock witness still suffices for PASS, even if some unrelated source failed. If the rule is applicable and no lock qualifies, known listing incompleteness produces SKIPPED/INFO. Otherwise preserve the existing lock existence/requirements qualification contract, including false qualification on incomplete closures. New declaration-body uncertainty does not by itself redefine that qualification contract. If no manifest is known, retain the old applicability-SKIP.
3. **env.llm_critical_deps_pinned**: retain known-use applicability, all credit and old cause precedence. Only a remaining known-used, uncredited package receives new listing-uncertainty SKIPPED/INFO. If check is empty, the conservative rule-wide veto consumes either the existing primary-Python gap or a new listing gap (fixed precedence must be documented). It must not claim complete detection of all actual use.
4. **env.python_version_declared**: preserve any existing observed witness, including the current presence-only .python-version witness and current supported environment substring contract. Without a witness, skip for a known listing gap or an actual relevant pyproject/environment read/decode failure, including a caught pyproject TOML RecursionError. Do not interpret any unrelated config as a Python-version failure, or strengthen old successful witness validation in this batch.
5. **env.secret_files_ignored**: retain all currently observed forbidden-file failures, severities, sorting and path/evidence caps. An empty check only receives a listing-gap veto; no AST/dependency/parser failure suppresses this rule. Intentional existing listing size/exclusion policy remains its bounded view. This is not a content secret scanner and does not modify redaction.py.
6. **exec.profile_detection_mismatch**: after the existing detection has actually run, preserve all observed positive shipped/high mismatches. Each declared-but-undetected profile skips if existing Python gap or a relevant new listing/dependency/detection gap exists. An empty aggregate check conservatively skips under those same gaps. Do not add an extra aggregate result to a nonempty list. Positive detected profiles in the effective declaration closure remain settled. Keep existing sorted direction order and final engine sorting.

For every new SKIP preserve rule ID, category, audit level and aliases; use status SKIPPED/severity INFO, stable path-free or safe-relative-path reason/evidence, and a specific restore/review hint. Apply severity overrides only to FAIL as before. Preserve suppression on every status, appended suppression evidence, and threshold values. The concrete patch must freeze exact new strings, evidence order and precedence before candidate execution.

### Compatibility costs requiring the specific decision

- A formerly CRITICAL missing-manifest finding or promoted absence WARNING may change to SKIPPED/INFO, including isolated exit 1→0. This is a compatible chosen uncertainty policy only after explicit acceptance, not a consequence of unchanged default thresholds.
- An unrelated malformed eligible config or shell line may conservatively veto profile-wide/declared-absence conclusions even when a more expensive per-profile sufficiency proof could settle them. No such optimization is required; consistent conservative handling is the chosen finite policy.
- Empty secret-file output may change from PASS to SKIP when listing failed; an actually observed forbidden file still fails.
- Default text can show Findings: PASS with skips; export may lose notable absence warnings; complete JSON retains SKIP. Profiles/hints/init task content and source reads are not broadened.
- Pinned real repositories may contain malformed or specially tagged configs. Their source-derived exact affected results must be predeclared and fully compared. Do not assume zero delta for the five-project portfolio.
- No new persisted fields/schema versions, rule IDs, default severities, dependencies, version bump, automatic file fixes, provider calls or release are part of A.

## Finite acceptance and honest closure

CLOSE-01: freeze the 69-rule disposition matrix below and the exact eligible-view scope. Freeze one concrete accepted patch/strings/precedence and explicit non-goals. Old PROPOSED and accepted snapshots retain their original identities.

CLOSE-02: implement only typed producer facts and the six selected rule consumers; first write real failure regressions on old source. Existing positive evidence, accepted credit/cause precedence, full-view old behavior, zero-candidate observed coverage, internal source-cache behavior, user profile overrides and default/overridden fail-on/suppression must have independent acceptance.

CLOSE-03: fix independently demonstrated crashes already within the supported contract, including deep YAML node composition and the root agent's six current dependency decoder observations. At each existing dependency decoder try, catch only RecursionError separately, record the internal parser_limit issue and reuse existing D-M/D-F consumers; PythonVersionDeclaredRule also catches TOML RecursionError and records its own python_version gap. A finite RecursionError fallback is an old robustness repair. Do not swallow MemoryError, arbitrary ValueError or unrelated exceptions, and do not add arbitrary traversal/alias budgets: those would change accepted semantics and require their own concrete inclusion in A. Broader resource-exhaustion resistance remains unclaimed.

CLOSE-04: full final quality and fresh five-project affected audit/init/list/export plus complete source-derived comparisons and exact-final-head five CI. If any pin changes, prepare a separate independently justified forward gold amendment rather than copying output. Shared final candidate/resource validation follows the existing workflow; ordinary new static policy does not itself claim new GPU/paid-provider results.

R07-C may then be marked complete **for this explicitly accepted six-rule, captured-view contract**, only when the closure decision explicitly supersedes older broad OPEN statements. No claim is made of arbitrary grammar support, unknown imports, full filesystem or execution completeness, solver validation, or universal sufficient certificates. These exclusions must be part of the reviewed closing contract; this survey alone cannot transfer unfinished work to backlog.

## Minimal regression seeds (design, not executed results)

- Listing failure: external proc boundary returns nonzero for only the existing git ls-files call; a physical eligible dependency file/forbidden file exists. Check the fixed-view unknown result, then successful listing recovers old result; do not infer domain failures from stderr.
- Non-Git walk/stat: external filesystem errors on an eligible listed path or subdirectory, preserve unrelated valid witnesses and known forbidden files.
- Profile content absence: no .py candidates; manifest declares safety/evaluation and an eligible README/config/framework source is unreadable or decode-invalid. Old primary coverage is complete at 0/0 but absence remains FAIL; proposed result is SKIP. Include positive high evidence before and after the failed input.
- Mixed profile result: one declared profile lacks evidence under a gap, while a different shipped/high profile is concrete and undeclared. New list must contain SKIP plus preserved positive FAIL in stable order.
- Python version: a malformed/read-failed pyproject without any other witness skips; add a .python-version witness and keep old PASS. A malformed unrelated JSON config must not change Python-version outcome.
- Existing dependency priority: failed associated format lock/D-L/D-M/D-G/D-I still wins before new listing fallback; exact/qualified credit still wins before all skip branches.
- Framework composer crash: eligible tasks/deep.yaml below current content limit with a sufficiently deep valid node tree and task/dataset_path root keys. Verify actual old exit 3 first; proposal fallback skips the unrecoverable static source without fabricating a task.

## Current complete builtin disposition matrix (69 IDs)

The row count is a source inventory, not a count of new implementation tasks. No candidate tests or full quality run were executed by this survey.

| Rule ID | Current source/class line | Proposed disposition |
|---|---|---|
| `code.git_repo` | `src/reprollm/rules/code.py:16` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `code.git_commit` | `src/reprollm/rules/code.py:46` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `code.clean_tree` | `src/reprollm/rules/code.py:90` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `code.no_untracked` | `src/reprollm/rules/code.py:121` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `code.submodules_initialized` | `src/reprollm/rules/code.py:152` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `code.remote_recorded` | `src/reprollm/rules/code.py:189` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `consistency.lock_fresh` | `src/reprollm/rules/consistency.py:23` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `consistency.file_hashes` | `src/reprollm/rules/consistency.py:85` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `consistency.generation_params` | `src/reprollm/rules/consistency.py:262` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `consistency.model_identity` | `src/reprollm/rules/consistency.py:291` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `consistency.env_vs_lock` | `src/reprollm/rules/consistency.py:345` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `consistency.custom_fields` | `src/reprollm/rules/consistency.py:441` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `dataset.revision_pinned` | `src/reprollm/rules/dataset.py:16` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `dataset.local_files_hashed` | `src/reprollm/rules/dataset.py:42` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `dataset.declared` | `src/reprollm/rules/dataset.py:95` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `dataset.split_declared` | `src/reprollm/rules/dataset.py:132` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `dataset.subset_declared` | `src/reprollm/rules/dataset.py:141` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `dataset.preprocessing_declared` | `src/reprollm/rules/dataset.py:150` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `dataset.sampling_seed_declared` | `src/reprollm/rules/dataset.py:167` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `env.dependency_manifest_present` | `src/reprollm/rules/env.py:32` | listing gap: missing manifest SKIP; present witness retains PASS |
| `env.lockfile_present` | `src/reprollm/rules/env.py:62` | listing gap: absent qualified lock SKIP; observed qualified lock retains PASS; body qualification rules otherwise unchanged |
| `env.llm_critical_deps_pinned` | `src/reprollm/rules/env.py:101` | existing credit and accepted causes win; residual missing pin/list-wide empty PASS veto consumes listing gap |
| `env.python_version_declared` | `src/reprollm/rules/env.py:358` | listing or actual relevant body/decoder gap: absent witness SKIP; observed witness retains PASS |
| `env.secret_files_ignored` | `src/reprollm/rules/env.py:418` | listing gap: no forbidden witness SKIP; each observed forbidden finding retains FAIL |
| `env.reprollm_initialized` | `src/reprollm/rules/env.py:478` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `eval.metrics_declared` | `src/reprollm/rules/eval_.py:33` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `eval.metric_implementation_referenced` | `src/reprollm/rules/eval_.py:60` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `eval.aggregation_declared` | `src/reprollm/rules/eval_.py:129` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `eval.repetitions_declared` | `src/reprollm/rules/eval_.py:137` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `eval.definitions_declared` | `src/reprollm/rules/eval_.py:145` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `eval.query_budget_declared` | `src/reprollm/rules/eval_.py:172` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `exec.command_declared` | `src/reprollm/rules/exec_.py:15` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `exec.seed_declared` | `src/reprollm/rules/exec_.py:47` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `exec.run_recorded` | `src/reprollm/rules/exec_.py:89` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `exec.profile_detection_mismatch` | `src/reprollm/rules/exec_.py:116` | listing/dependency/detection gap: declared absence and empty aggregate SKIP; observed high-confidence mismatch retains FAIL |
| `gen.backend_version_locked` | `src/reprollm/rules/gen.py:14` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `gen.params_declared` | `src/reprollm/rules/gen.py:53` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `gen.seed_declared` | `src/reprollm/rules/gen.py:77` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `gen.backend_declared` | `src/reprollm/rules/gen.py:97` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `gen.backend_config_declared` | `src/reprollm/rules/gen.py:115` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `gen.stop_declared` | `src/reprollm/rules/gen.py:140` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `judge.prompt_hashed` | `src/reprollm/rules/judge.py:15` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `judge.pinnability_recorded` | `src/reprollm/rules/judge.py:55` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `judge.model_declared` | `src/reprollm/rules/judge.py:94` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `judge.prompt_declared` | `src/reprollm/rules/judge.py:120` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `judge.params_declared` | `src/reprollm/rules/judge.py:146` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `judge.repetitions_declared` | `src/reprollm/rules/judge.py:170` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.revision_pinned` | `src/reprollm/rules/model.py:18` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.tokenizer_pinned` | `src/reprollm/rules/model.py:96` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.chat_template_hashed` | `src/reprollm/rules/model.py:135` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.primary_declared` | `src/reprollm/rules/model.py:196` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.provider_known` | `src/reprollm/rules/model.py:220` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.dtype_declared` | `src/reprollm/rules/model.py:291` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.quantization_declared` | `src/reprollm/rules/model.py:300` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `model.adapter_declared` | `src/reprollm/rules/model.py:309` | PRESERVE: positive observed hint triggers explicit declaration requirement; missing hint already applicability-SKIP |
| `model.trust_remote_code_declared` | `src/reprollm/rules/model.py:337` | PRESERVE: positive observed hint triggers explicit declaration requirement; missing hint already applicability-SKIP |
| `privacy.threat_model_declared` | `src/reprollm/rules/privacy.py:12` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `privacy.mechanism_declared` | `src/reprollm/rules/privacy.py:32` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `privacy.metrics_declared` | `src/reprollm/rules/privacy.py:61` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `privacy.attack_config_declared` | `src/reprollm/rules/privacy.py:77` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `prompt.hashed` | `src/reprollm/rules/prompt.py:13` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `prompt.declared` | `src/reprollm/rules/prompt.py:48` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `prompt.file_exists` | `src/reprollm/rules/prompt.py:61` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `prompt.few_shot_declared` | `src/reprollm/rules/prompt.py:98` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `train.method_declared` | `src/reprollm/rules/train.py:31` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `train.hyperparameters_declared` | `src/reprollm/rules/train.py:39` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `train.optimizer_declared` | `src/reprollm/rules/train.py:78` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `train.precision_declared` | `src/reprollm/rules/train.py:98` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
| `train.lora_config_complete` | `src/reprollm/rules/train.py:106` | PRESERVE: existing explicit Git/document/owned-file/runtime fact; unrelated static coverage is not a new veto |
