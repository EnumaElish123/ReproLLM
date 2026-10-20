# R07-C：逐规则覆盖与证据语义清单

只读来源 `055c5fb880f4e374555a1d229b79d0d612c80350`。状态：**P-A 设计输入，未批准、未实施**。共69个builtin ID及动态project.*；40个源码/规范文件逐字节匹配该Git候选。 [完整JSON](rule-evidence-inventory.json)保留每条规则的applies、FAIL、PASS/空结果、直接/间接依赖、限制和实际行号。

engine只有适用规则check=[]时合成rule-level、evidence为空的PASS；非空显式field PASS/混合角色结果直接保留。min_level以上不执行，applies=false为SKIPPED。audit规则选择来自core＋manifest/CLI profiles，而非自动选detected profiles。引用：core/engine.py:234–269、core/registry.py:19–25、rules/_presence.py:19–68。

推荐A的唯一opt-in范围为env.llm_critical_deps_pinned、exec.profile_detection_mismatch的空结果分支＋已知Python candidate>parsed；其他67条和dynamic均保留。下表的事实限制是审议材料，不是已经批准的新结论合同。

| Rule ID / class source | 主要事实域 | 当前FAIL条件 | 当前成功条件及边界 |
|---|---|---|---|
| code.clean_tree — src/reprollm/rules/code.py:90 | git_fact | ctx.git.modified is nonempty | No modified tracked paths in the collected git status result. |
| code.git_commit — src/reprollm/rules/code.py:46 | git_fact | commit is None | HEAD command returned a commit string. |
| code.git_repo — src/reprollm/rules/code.py:16 | git_fact | GitInfo.is_repo is false | The Git rev-parse probe positively identifies a work tree. |
| code.no_untracked — src/reprollm/rules/code.py:121 | git_fact | ctx.git.untracked is nonempty | No untracked paths in the collected git status result. |
| code.remote_recorded — src/reprollm/rules/code.py:189 | git_fact | remote_origin is None | Collected git origin string is present. |
| code.submodules_initialized — src/reprollm/rules/code.py:152 | git_and_direct_file_fact | Collected submodule has initialized=false | No uninitialized submodules in collected status. |
| consistency.custom_fields — src/reprollm/rules/consistency.py:441 | document_facts | Any observed eligible custom value differs from declared manifest custom value. | All recorded eligible custom observations agree with declarations under accepted rules; child consumption unverified. |
| consistency.env_vs_lock — src/reprollm/rules/consistency.py:345 | document_facts | For any critical package, recorded lock and run versions differ, including only-lock/only-run presence difference. | Recorded critical-package metadata agrees in compatible recorder contexts; child environment explicitly unverified. |
| consistency.file_hashes — src/reprollm/rules/consistency.py:85 | document_facts | A comparable locked path is invalid, missing, unreadable, current digest differs, or a present run digest differs. | All comparable declared lock prompt/file digests agree with current tree and optional run digest. |
| consistency.generation_params — src/reprollm/rules/consistency.py:262 | document_facts | Any captured eligible observation differs from current manifest value for its field. | All recorded eligible generation observations agree with declarations; child consumption remains unverified. |
| consistency.lock_fresh — src/reprollm/rules/consistency.py:23 | document_facts | Either current document digest differs from corresponding lock digest. | Both document digests agree with lock. |
| consistency.model_identity — src/reprollm/rules/consistency.py:291 | document_facts | Observed id differs from required declared/locked identities; observed revision differs from resolved lock revision when available, otherwise declaration, and also from exact 40-hex declaration when one is present. | Recorded observed model identity values agree with applicable expected declarations/resolved lock identities; child consumption remains unverified. |
| dataset.declared — src/reprollm/rules/dataset.py:95 | document_facts | datasets mapping empty. | At least one dataset role is declared. |
| dataset.local_files_hashed — src/reprollm/rules/dataset.py:42 | document_facts | A local dataset has no same-role lock dataset, or locked.files is None, or any declared file is absent from nonempty locked hash map. | Every declared file has a nonempty locked sha256 and locked files list exists. |
| dataset.preprocessing_declared — src/reprollm/rules/dataset.py:150 | document_facts | A declared dataset preprocessing is None. | Preprocessing is declared for each declared dataset. |
| dataset.revision_pinned — src/reprollm/rules/dataset.py:16 | document_facts | Any locked Hugging Face dataset revision confidence != exact. | Every locked HF dataset has exact revision confidence. |
| dataset.sampling_seed_declared — src/reprollm/rules/dataset.py:167 | document_facts | A declared sampling.n exists but its seed is None. | Declared sampled roles have a seed; no sampling.n produces per-role SKIPPED. |
| dataset.split_declared — src/reprollm/rules/dataset.py:132 | document_facts | Any declared Hugging Face dataset has split=None. | Every declared HF dataset has split; non-HF roles explicitly SKIPPED. |
| dataset.subset_declared — src/reprollm/rules/dataset.py:141 | document_facts | Any declared Hugging Face dataset has subset=None. | Every declared HF dataset has subset; non-HF roles explicitly SKIPPED. |
| env.dependency_manifest_present — src/reprollm/rules/env.py:30 | dependency_inventory_presence | deps.manifest_present=false | At least one supported dependency-manifest/artifact candidate qualifies under existing presence policy. |
| env.llm_critical_deps_pinned — src/reprollm/rules/env.py:99 | mixed_python_import_and_dependency_aggregation | For each observed canonical in-use critical package, neither any repository exact declaration nor a qualified lock-origin association supplies credit. | Every currently observed in-use critical package has repository-existential credit; current empty result is a rule-level aggregate, not all real imports or one selected environment. |
| env.lockfile_present — src/reprollm/rules/env.py:60 | dependency_inventory_presence | deps.lockfiles is empty | Existing format-lock artifact inventory or an independently qualified exact requirements closure exists. |
| env.python_version_declared — src/reprollm/rules/env.py:177 | independent_non_python_content_presence | No supported Python declaration witness found | At least one readable project requires-python, listed .python-version, or readable environment python= witness is found. |
| env.reprollm_initialized — src/reprollm/rules/env.py:297 | direct_file_fact_with_advisory_detection | Neither direct reprollm.yaml file nor .reprollm directory exists | Direct owned artifact existence suffices. |
| env.secret_files_ignored — src/reprollm/rules/env.py:237 | security_filename_inventory | A filename matching forbidden patterns appears in ctx.fs.files(); CRITICAL in Git, WARNING outside Git | No forbidden path appears in the existing file listing; no content secret search is performed. |
| eval.aggregation_declared — src/reprollm/rules/eval_.py:129 | document_facts | evaluation.aggregation=None. | aggregation is declared. |
| eval.definitions_declared — src/reprollm/rules/eval_.py:145 | document_facts | evaluation definitions lacks both refusal and asr keys. | At least refusal or asr definition key exists. |
| eval.metric_implementation_referenced — src/reprollm/rules/eval_.py:60 | explicit_path_is_file | Any implementation missing, invalid relative file grammar/URL, or nonexistent relative file that is not valid package==version pin. | Every declared metric references an existing file or syntactically valid exact package pin. |
| eval.metrics_declared — src/reprollm/rules/eval_.py:33 | document_facts | evaluation absent or metrics list empty. | At least one evaluation metric is declared. |
| eval.query_budget_declared — src/reprollm/rules/eval_.py:172 | document_facts | evaluation absent or query_budget=None. | Query budget declaration exists. |
| eval.repetitions_declared — src/reprollm/rules/eval_.py:137 | document_facts | evaluation.repetitions=None. | repetitions is declared. |
| exec.command_declared — src/reprollm/rules/exec_.py:15 | manifest_fact | execution or execution.command is None | Manifest execution.command is non-null. |
| exec.profile_detection_mismatch — src/reprollm/rules/exec_.py:116 | mixed_positive_and_absence_detection | Direction1: declared non-core profile absent from detection (negative evidence). Direction2: positively detected high-confidence shipped profile absent from effective/resolved declarations (positive evidence). | All declared non-core profiles have some detected evidence, and all detected high shipped profiles are effective. Empty result currently synthesizes aggregate PASS. |
| exec.run_recorded — src/reprollm/rules/exec_.py:89 | loaded_run_inventory | No readable/valid run record is in ctx.runs | At least one loaded run record exists. |
| exec.seed_declared — src/reprollm/rules/exec_.py:47 | manifest_fact | All execution/generation/training seeds are None | Any declared seed is non-null, including zero. |
| gen.backend_config_declared — src/reprollm/rules/gen.py:115 | document_facts | Any required vLLM configuration field is None. | The four required configuration fields are declared. |
| gen.backend_declared — src/reprollm/rules/gen.py:97 | document_facts | inference or backend absent. | Inference backend declaration exists. |
| gen.backend_version_locked — src/reprollm/rules/gen.py:14 | document_facts | lock.inference absent or its version confidence != exact. | Declared eligible backend has exact recorded version confidence. |
| gen.params_declared — src/reprollm/rules/gen.py:53 | document_facts | Any of three required generation fields is None. | All three fields are explicitly declared; zero temperature is present. |
| gen.seed_declared — src/reprollm/rules/gen.py:77 | document_facts | Applicable declared sampling has seed=None. | Declared sampling has a declared seed. |
| gen.stop_declared — src/reprollm/rules/gen.py:140 | document_facts | generation absent or stop=None. | Stop declared, including explicit empty list. |
| judge.model_declared — src/reprollm/rules/judge.py:94 | document_facts | Outside judge_only exception, referenced model role absent. Within exact exception, role missing or id absent/empty/whitespace-only. | Judge role declared; stronger id check only under explicit narrow profile exception. |
| judge.params_declared — src/reprollm/rules/judge.py:146 | document_facts | Judge absent or either required parameter is None. | Both judge parameters explicitly declared. |
| judge.pinnability_recorded — src/reprollm/rules/judge.py:55 | document_facts | Referenced role absent from lock.models. | The judge model role has a lock entry (ModelLock schema requires pinnability). |
| judge.prompt_declared — src/reprollm/rules/judge.py:120 | document_facts | Outside judge_only exception, referenced prompt role absent. Within exact exception, role missing or both path and inline text absent. | Judge prompt role declared; exact judge_only exception additionally requires source declaration. Explicit empty inline string counts. |
| judge.prompt_hashed — src/reprollm/rules/judge.py:15 | document_facts | Appropriate hash missing or falsey in lock. | Referenced judge prompt has a corresponding recorded hash. |
| judge.repetitions_declared — src/reprollm/rules/judge.py:170 | document_facts | Judge absent or repetitions=None. | Judge repetitions declared; zero remains a declaration. |
| model.adapter_declared — src/reprollm/rules/model.py:309 | positive_python_hint | Applicable detected peft use and no manifest model has adapter. | At least one adapter declaration exists for a positive detected signal; no role-to-import binding is checked. |
| model.chat_template_hashed — src/reprollm/rules/model.py:135 | document_facts | A qualifying model has no chat_template, or non-absent template sha256 confidence != exact. | Recorded absent status is itself a positive lock fact; present/custom_file must have exact hash confidence. |
| model.dtype_declared — src/reprollm/rules/model.py:291 | document_facts | Any non-API declared role has neither role dtype nor inference.dtype. | Every non-API role has a dtype declaration or fallback; API roles explicitly SKIPPED. |
| model.primary_declared — src/reprollm/rules/model.py:196 | document_facts | Outside exact judge_only exception, primary role or its id is None. | Declared primary id is present; exact explicit judge_only exception returns SKIPPED. |
| model.provider_known — src/reprollm/rules/model.py:220 | document_facts | Any declared provider equals other. | Each explicitly declared non-other provider is known; provider None is SKIPPED. |
| model.quantization_declared — src/reprollm/rules/model.py:300 | document_facts | Any non-API declared role has neither role quantization nor inference.quantization. | Every non-API role has a quantization declaration or fallback; API roles explicitly SKIPPED. |
| model.revision_pinned — src/reprollm/rules/model.py:18 | document_facts | API role: pinnability is snapshot_alias (INFO failure) or anything other than exact (WARNING failure); local role: local.config_sha256 object is absent; remaining non-API role: revision.confidence != exact. | No violations among locked model roles under effective API classification. This is lock identity bookkeeping, not discovery of all real model uses. |
| model.tokenizer_pinned — src/reprollm/rules/model.py:96 | document_facts | Any locked Hugging Face model has no tokenizer or tokenizer revision confidence != exact. | All locked Hugging Face models have an exact tokenizer revision. |
| model.trust_remote_code_declared — src/reprollm/rules/model.py:337 | positive_python_hint | Positive detected trust_remote_code=True and no declared model has true or false trust_remote_code. | At least one explicit boolean declaration accompanies a detected positive signal; value matching/role binding is not checked. |
| privacy.attack_config_declared — src/reprollm/rules/privacy.py:77 | manifest_fact | attack.method or query_budget is None | Both declared attack fields are non-null. |
| privacy.mechanism_declared — src/reprollm/rules/privacy.py:32 | manifest_fact | privacy mechanism name missing or params empty/absent | Both mechanism name and nonempty params are declared. |
| privacy.metrics_declared — src/reprollm/rules/privacy.py:61 | manifest_fact | privacy metrics is empty/absent | Nonempty manifest privacy.metrics. |
| privacy.threat_model_declared — src/reprollm/rules/privacy.py:12 | manifest_fact | privacy/threat_model is None | Manifest privacy.threat_model is non-null. |
| prompt.declared — src/reprollm/rules/prompt.py:48 | document_facts | prompts mapping empty. | At least one prompt role declared. |
| prompt.few_shot_declared — src/reprollm/rules/prompt.py:98 | document_facts | No prompt role has few_shot object. | At least one prompt explicitly declares few_shot, including n=0. |
| prompt.file_exists — src/reprollm/rules/prompt.py:61 | explicit_path_is_file | A declared path with no inline text is not a file. | Inline text exists, including explicit empty string, or referenced path is a file; absent both gives SKIPPED. |
| prompt.hashed — src/reprollm/rules/prompt.py:13 | document_facts | Any declared prompt lacks truthy appropriate lock hash. | All declared prompt roles have corresponding recorded hash. |
| train.hyperparameters_declared — src/reprollm/rules/train.py:39 | document_facts | learning_rate or batch_size absent, or both epochs and max_steps absent. | Learning rate and batch size declared with at least one duration declaration. |
| train.lora_config_complete — src/reprollm/rules/train.py:106 | document_facts | No single adapter has all three fields non-None. | One adapter has alpha, rank and target_modules together. |
| train.method_declared — src/reprollm/rules/train.py:31 | document_facts | training absent or method=None. | Training method is declared. |
| train.optimizer_declared — src/reprollm/rules/train.py:78 | document_facts | training absent or optimizer/scheduler is None. | Both optimizer and scheduler are declared. |
| train.precision_declared — src/reprollm/rules/train.py:98 | document_facts | training absent or precision=None. | Training precision is declared. |

## 动态规则与证据边界

动态 `project.*` 来自已接受项目规则；其manifest custom字段存在性以及独立runtime一致性均依赖显式声明/记录，不因AST cap全局SKIP。具体check、applies、字段路径与来源引用在完整JSON的dynamic_project_family中。

R06-B interaction：存在一个全仓exact或合格关联来源就足够。未知AST可能带来新包，也可能为嵌套lock补上唯一import来源；未读exact可能移除现有WARNING。因此“已有loose来源”不是与新增事实单调的完整pin违规。empty aggregate PASS也不能以一个已覆盖包证明未知包均已覆盖。

exec mismatch两方向不同：检测到的high/shipped未声明是正证据；declared却没检测到是absence。profile义务可能已经被有限充分证书全部满足，A选择保守SKIP仍是兼容代价，并非唯一必然语义；若未来选精细方案，必须使用实际loaded overrides/signals。

Python计数只覆盖现有候选视图；listing/stat/2MiB过滤、512KiB读界、非Python/config/README/framework读取、deps grammar、Git命令失败和真实执行完整性均另有边界。A不顺手重做这些通道。Git和已知禁止文件finding不因无关AST cap改变。adapter规范中的dependency与当前仅AST hint差异另列backlog，不借coverage扩实现。

[原实现观察与资格](implementation-evidence.md)提供11份全量JSON。未调用提供商、网络、真实子进程、重依赖或资源；未读凭据、未改仓库。
