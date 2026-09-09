# M4 — Lockfile (`reprollm lock`)

> Sprint：Week 4，2026-09-28 → 2026-10-04（与国庆假期 10-01 → 10-07 重叠，本周按「轻周」规划；T06/T08 允许滑入 W5 前两天）
> 目标版本：`0.2.0`
> GitHub Milestone：`M4`

---

## 0. 给 coding agent 的阅读顺序

1. `00` §6 D-03、D-13、D-14、D-21、D-22、D-30、D-32
2. `01` §4（Lock 全文，逐条实现）、§9–§11、§12.4–§12.9 中 `min_level = 2` 的行、§12.12 的 `consistency.lock_fresh`、`consistency.file_hashes`（working tree 部分）、§22 T-04
3. `AGENTS.md`
4. 本文档

---

## 1. 本周目标

实现 **Intent → Resolved Reality**：`reprollm lock` 把 manifest 解析为带 provenance 的 `reprollm.lock`，并让 audit 进入 Level 2。本周结束时：

- HF 模型 / tokenizer / chat template / config / adapter / 数据集的 revision 与 hash 解析可用（在线与 `--offline`）；
- API provider 的 pinnability 正确分类且默认不联网；
- local provider 的文件 hash 与权重大文件策略实现；
- prompts、声明文件、metrics 实现、backend 版本、环境快照写入 lock；
- `lock --check` 与 `consistency.lock_fresh`、`consistency.file_hashes`（工作树部分）可用；
- M3 的 9 个占位 L2 规则替换为真实实现；
- 三个 fixture 有 `expected/lock.yaml` 与 `expected/audit_L2.json`。

---

## 2. 人工任务

| # | 任务 |
|---|---|
| H1 | 从 §3 创建 Issue，挂 `M4` |
| H2 | 在有网络的 Linux 机器上对 Project A 运行 `reprollm lock`，把 lock 文件（脱敏）贴到 dogfooding issue；若 A 使用 gated 模型，准备好 `HF_TOKEN` 环境变量以验证 401/403 路径与 token 不落盘 |
| H3 | 为 Project C 写 manifest（若 M3 未做） |
| H4 | 合并 T09 后打 tag `v0.2.0` |

---

## 3. 任务清单

分支前缀 `m4/`。

### M4-T01 HF Hub HTTP 客户端与录制 fixture（M）

**范围**（`lock/hf_client.py`）
- `HfClient(http: httpx.Client, token: str|None)`：`base_url` 可配（默认 `https://huggingface.co`，环境变量 `HF_ENDPOINT` 覆盖以支持镜像）；超时 10 s；对 5xx / 连接错误重试 2 次（0.5 s、1.5 s 退避）；`Authorization: Bearer <token>` 仅在 token 非空时加，token 来自 `HF_TOKEN` 或 `HUGGING_FACE_HUB_TOKEN`，**任何日志、错误信息、lock 内容都不得包含 token**。
- 方法：`model_info(repo_id, revision="main") -> RepoInfo(sha, siblings: list[str])`（`GET /api/models/{id}/revision/{rev}`）；`dataset_info(...)`（`/api/datasets/...`）；`fetch_file(kind, repo_id, sha, filename, max_bytes=2 MiB) -> bytes`（`GET /{id}/resolve/{sha}/{filename}`，datasets 为 `/datasets/{id}/resolve/...`；超过 `max_bytes` → `FileTooLarge`）。
- 异常：`HfForbidden`（401/403）、`HfNotFound`（404）、`HfNetworkError`（其余）；每个异常携带 `source` 字符串供 Provenance 使用（`hf_api_forbidden`, `hf_api_not_found`, `network_error`）。
- `tests/fixtures/hf_api/`：手工编写的最小 JSON 响应（字段只需 `sha`、`siblings[].rfilename`）与文件内容：
  - `models/Qwen__Qwen3-32B/revision_main.json`（`sha: "8fa23e7c1a0000000000000000000000000000aa"`，siblings 含 `config.json`, `tokenizer_config.json`, `tokenizer.json`）；`files/Qwen__Qwen3-32B/tokenizer_config.json`（含 `chat_template` 字符串）；`files/Qwen__Qwen3-32B/config.json`；
  - `datasets/cais__mmlu/revision_main.json`（`sha: "b77a9100…"`）；
  - `models/meta-llama__Llama-3.1-8B-Instruct/revision_main.403.json`（模拟 gated）；
  - `models/gpt2/revision_main.json`（doctor 用）。
  - `tests/unit/lock/conftest.py` 提供 `hf_mock` fixture：用 respx 把上述文件挂到对应 URL；未挂载 URL 由全局 `assert_all_mocked` 拦截。

**验收标准**：重试次数与退避测试（respx side_effect）；403 → `HfForbidden` 且异常字符串不含 token；`HF_ENDPOINT` 生效；`fetch_file` 大小上限。

---

### M4-T02 Resolvers（L）

**范围**（`lock/resolver.py` 编排；`hf_resolver.py`、`api_resolver.py`、`local_resolver.py`）
- 严格按 `01 §4.3` 表实现每一行。要点：
  - HF 模型：`revision` 用户声明时向 API 传该 revision（可能是 branch/tag/sha），得到的 `sha` 为 `exact`；tokenizer 同仓库时复用同一 `RepoInfo`（不重复请求）；chat template 三态（`present` / `absent` / `custom_file`——manifest 声明 `chat_template.path` 时 hash 本地文件并跳过远端）；`chat_template.jinja` 优先于 `tokenizer_config.json`；`config_sha256` 从 `config.json`。
  - HF 数据集：只解析 `sha`；`content_fingerprint: {status: not_computed}` 固定写入。
  - adapter（`provider: peft`，id 形如 HF 仓库）：解析 sha + `adapter_config.json` hash；id 为本地路径 → local 逻辑。
  - API provider：正则 `-\d{4}-\d{2}-\d{2}$` 或 `@\d{8}$` → `snapshot_alias`，否则 `unpinnable`；`observed_at`；`revision.value: null, source: provider_no_pinning, confidence: unresolved`；`--verify-api` 时 `GET {base_url or 默认}/models/{id}`（默认 base_url：openai `https://api.openai.com/v1`、openrouter `https://openrouter.ai/api/v1`、anthropic `https://api.anthropic.com/v1`），key 从 `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` 读取；无 key → note `verify skipped: no api key`。
  - local：目录 / 单文件；权重文件 hash 策略（≤ 100 MiB 总量或 `--hash-large-files`）；`weights.total_size_bytes` 总是记录。
  - prompts（path → sha256/size；text → `text_sha256`）；`files`（`execution.config_files` ∪ bindings config 路径 ∪ `training.deepspeed.config` ∪ `models.*.chat_template.path` ∪ `evaluation.definitions.*` 中存在的路径 ∪ `privacy.threat_model` 若为路径），去重排序；缺失文件不写入、由 audit 报告。
  - `inference.version`：backend → 分发名映射（`vllm`→`vllm`, `transformers`→`transformers`, `sglang`→`sglang`, `openai`→`openai`）；`other` → 不解析。
  - `evaluation.metrics[].implementation`：路径 → `implementation_sha256`；`pkg==ver`/`pkg` → `implementation_version`（installed）。
  - `environment`：`python`, `platform`, `packages`（仅已安装的 LLM-critical）, `gpu`（`nvidia-smi --query-gpu=driver_version --format=csv,noheader` 与头部 CUDA 版本；不可用 → `source: unavailable`）。
- `--offline`：跳过全部 HTTP；声明 `revision` → `confidence: declared`；否则 `unresolved, source: offline`。
- 每个 unresolved 项在命令结束时汇总打印（不是失败，exit 0）。

**验收标准**：每一行 `01 §4.3` 至少一个单测；`hf_vllm_eval` complete manifest 在 `hf_mock` 下生成的 lock 与 `expected/lock.yaml` 一致（忽略时间字段）；gated 模型 → `unresolved/hf_api_forbidden`；offline 模式 snapshot；`gpt-4o` → `unpinnable`，`gpt-4o-2024-08-06` → `snapshot_alias`。

---

### M4-T03 `reprollm lock` 命令（M）

**范围**（`cli/lock.py`, `lock/writer.py`）
- 加载 manifest（无 → exit 2 提示 `init`）；构造 `Lock`（字段顺序按 `01 §4.2`）；`manifest_sha256`、`project_rules_sha256`（文件不存在 → null）；原子写入；`reprollm_version`、`generated_at`。
- `--check`：不写文件；lock 缺失 / `manifest_sha256` 不符 / `project_rules_sha256` 不符 → 打印原因、exit 1；否则 exit 0。
- 结束摘要：`Resolved: 7 exact · 1 declared · 2 unresolved · 1 unpinnable (models.judge)`，unresolved/unpinnable 逐项列出原因。
- YAML 输出：`dump_yaml` 保序；Provenance 对象内联写法（`{value: …, source: …, confidence: …}` 用块格式而非 flow，便于 diff）。

**验收标准**：CliRunner：在线 / offline / `--check` 三态；两次 `lock` 之间仅 `generated_at`/`resolved_at`/`observed_at` 不同（其余字节相同）；exit codes。

---

### M4-T04 Level 2 上下文与 `consistency.lock_fresh` / `consistency.file_hashes`（M）

**范围**
- `AuditContext.lock`：存在则加载（schema 错误 → exit 2 并提示重新 `lock`；`schema_version` 更新版 → 明确报错）；`detect_level` 返回 2。
- `rules/consistency.py`：`consistency.lock_fresh`（manifest hash 与 project-rules hash 两个分支，各一条 finding）；`consistency.file_hashes` **工作树部分**：对 `lock.prompts.*.path` 与 `lock.files[]` 逐个重算当前 sha256，不同 → CRITICAL（evidence：路径、lock 值、当前值）；文件缺失 → 同规则 CRITICAL，message 区分。run 部分在 M5 接入（本周 `ctx.latest_run` 为 None 时只做工作树比较）。

**验收标准**：场景测试——lock 后修改 manifest（`consistency.lock_fresh` WARNING）；lock 后编辑 `prompts/system.txt`（`consistency.file_hashes` CRITICAL）；lock 后新增 project rule（`lock_fresh` WARNING，第二分支）。

---

### M4-T05 替换 9 个 L2 占位规则（L）

`model.revision_pinned`（HF：`confidence != exact` → CRITICAL；API：`unpinnable` → 规则返回 WARNING，`snapshot_alias` → INFO；local：缺 `config_sha256` → CRITICAL；evidence 含 provenance 的 `source`/`note`）、`model.tokenizer_pinned`、`model.chat_template_hashed`（`status: absent` 时 PASS 但 evidence note "model has no chat template"；`unresolved` → WARNING）、`dataset.revision_pinned`、`dataset.local_files_hashed`、`gen.backend_version_locked`、`prompt.hashed`、`judge.prompt_hashed`、`judge.pinnability_recorded`。删除 `stub` 标记；`docs/rules.md` 重新生成。

**验收标准**：每条 ≥1 PASS + ≥1 FAIL，用手工构造的 `Lock` 对象；`model.revision_pinned` 三种 provider 分支各一测试；`openai_judge_eval` complete + lock：`models.judge`（snapshot_alias）→ INFO，`models.primary`（`gpt-4o-mini` unpinnable）→ WARNING。

---

### M4-T06 Fixture：`expected/lock.yaml` 与 `audit_L2.json`（M）

**范围**：三个正向 fixture，在 `hf_mock` 下用 `complete` manifest 生成 `expected/lock.yaml`；随后 `audit` 生成 `expected/audit_L2.json`。预期要点：
- `hf_vllm_eval`：全部 exact；`inference.version` 在测试环境无 vllm → `unresolved`，因而 `gen.backend_version_locked` WARNING（这是**有意保留**的，展示「解析不到就说不知道」）；其余 PASS。
- `openai_judge_eval`：`model.revision_pinned` 对 primary WARNING、judge INFO；local dataset 文件 hash PASS。
- `privacy_custom_params`：primary gated → `revision unresolved (hf_api_forbidden)` → `model.revision_pinned` CRITICAL、`tokenizer_pinned` WARNING、`chat_template_hashed` WARNING；这是 Project C 真实会遇到的情形，fix_hint 必须提到 `HF_TOKEN`。

**验收标准**：三组 snapshot 通过；`audit_L2.json` 通过 JSON Schema 校验。

---

### M4-T07 `doctor --check-network` 复用客户端；`docs/lockfile.md`（S）

**范围**：doctor 改用 `HfClient.model_info("gpt2")`（respx fixture 已有）；`docs/lockfile.md`：provenance 对象、confidence 三态、pinnability 三态、offline 语义、staleness、为什么不算 dataset fingerprint、token 不落盘的保证。README 「Quick start」增加 `reprollm lock` 一步与一段真实 lock 片段。

---

### M4-T08 Dogfooding A/B/C（M）

**流程**：A 在线 `lock` → 检查 revision 是否与 HF 页面一致、chat template hash 是否稳定（连续两次 lock 相同）；B `lock` → judge pinnability 分类是否符合预期；C `lock`（有/无 `HF_TOKEN`）→ 验证 403 路径与 token 不出现在任何输出（`grep -r hf_ .reprollm reprollm.lock` 应为空）。三仓库随后 `audit` 看 Level 2 finding 是否合理。所有问题进 issue，修复或归属。

---

### M4-T09 发布 0.2.0（S）

CHANGELOG（含「lock schema v1 首次发布」）、版本、tag。Release notes 附 B 仓库脱敏后的 `models.judge` lock 片段（展示 `pinnability: snapshot_alias`——差异化叙事）。

---

## 4. 本周禁区

- 不引入 `huggingface_hub`、`requests`；HTTP 只用 `httpx`。
- 不下载模型权重、不下载数据集内容（只取 `config.json`、`tokenizer_config.json`、`chat_template.jinja`、`adapter_config.json`）。
- `lock` 默认不对 API provider 联网；不把任何 token / key 写入 lock、日志、异常消息。
- 不实现 `run`、`diff`、`export`、`discover`；不实现 `consistency.file_hashes` 的 run 侧比较。
- 不在测试中访问真实网络（包括 doctor 的网络检查）。

---

## 5. Dogfooding

见 T08。假期期间若维护者不可用，agent 可先完成 T01–T05、T07，T06 的 privacy fixture 部分与 T08 顺延到 W5 前两天，但 `0.2.0` 的 tag 不晚于 10-06。

---

## 6. Definition of Done（M4）

- [ ] `01 §4.3` 每一行有实现与测试
- [ ] `lock` 在线 / offline / `--check` 可用；两次 lock 字节级稳定（除时间字段）
- [ ] 9 个 L2 规则实现，无 stub 残留（CI 增加检查：registry 中 `stub=True` 的规则数为 0）
- [ ] `consistency.lock_fresh`、`consistency.file_hashes`（工作树）可用
- [ ] 三个 fixture 的 `lock.yaml` + `audit_L2.json` snapshot 通过
- [ ] A/B/C dogfooding 完成，token 不落盘经 grep 验证
- [ ] `docs/lockfile.md` 完成
- [ ] `v0.2.0` 发布

---

## 7. 发布步骤

同前，tag `v0.2.0`。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| HF API 响应结构变化 / 镜像站字段不全 | 只依赖 `sha` 与 `siblings[].rfilename`；缺字段 → `unresolved` 而非崩溃；`HF_ENDPOINT` 支持镜像 |
| 用户在无网 GPU 节点上 `lock` 失败 | `--offline` 明确语义 + 摘要提示「在有网机器上运行 lock 并提交」 |
| chat template 在不同 HF 仓库布局下不一致（`tokenizer_config.json` vs `chat_template.jinja`） | 两种都支持，`source` 字段记录来源；Project A 连续两次 lock 验证稳定性 |
| 假期导致 review 延迟 | 本周任务已压缩；T06/T08 可顺延；不允许把 M5 的 `run` 提前进来填空 |
