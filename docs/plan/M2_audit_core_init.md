# M2 — Audit Core + `init`

> Sprint：Week 2，2026-09-14 → 2026-09-20
> 目标版本：`0.1.0`（第一个「可用」版本：Level 0/1 audit + init）
> GitHub Milestone：`M2`

---

## 0. 给 coding agent 的阅读顺序

1. `00` §4、§6（D-04、D-05、D-07、D-08、D-09、D-10、D-12、D-25、D-30、D-33）
2. `01` §1、§3（含 3.2 init 模板）、§6（Profile schema 与 6.1 表）、§8、§9–§11、§12.1–§12.3、§13、§21、§22
3. `AGENTS.md`
4. 本文档

---

## 1. 本周目标

让 `reprollm audit .` 在**任何 Python 研究仓库**上给出有价值的 Level 0 结果（代码状态、依赖声明、secret 文件、检测到的实验类型），并让 `reprollm init` 生成一份带检测预填的 `reprollm.yaml`，从而进入 Level 1。本周结束时：

- `code.*`、`env.*`、`exec.*` 全部规则实现并有测试；
- 确定性 Profile 检测（`01 §13`）可用，结果进入 audit 报告 `profiles.detected`；
- 7 个内置 Profile 的 YAML 文件存在（`rules` 字段本周只含已实现的规则，M3 补齐）；Profile loader 支持继承闭包、环检测、用户覆盖；
- `init`（非交互 / 交互 / `--force` / `--profiles`）可用；
- Level 1 引擎路径可用：有 manifest 时执行声明 profile 选中的规则；
- 在 Project A 上完成第一次真实 dogfooding。

---

## 2. 人工任务

| # | 任务 |
|---|---|
| H1 | 从本文档 §3 创建 Issue 并挂到 Milestone `M2` |
| H2 | 确认 Project A 仓库在 Linux 开发机上可 clone；本周 T10 需要在其根目录运行 `audit` 与 `init` |
| H3 | 审阅 T04 的 PR 时重点看关键词表（`01 §13`）是否需要按你的研究领域增删；这是最需要人判断的部分 |
| H4 | 合并 T10 后打 tag `v0.1.0` |

---

## 3. 任务清单

分支前缀 `m2/`。

### M2-T01 `RepoScanner` 完整实现（M）

**范围**（`core/scanner.py`）
- `RepoScanner(root, git: GitInfo)`：
  - `files() -> list[RelPath]`：git 仓库内用 `git ls-files --cached --others --exclude-standard -z`；非 git 时 `os.walk` + 内置忽略列表（`.git`, `.reprollm/runs`, `node_modules`, `__pycache__`, `.venv`, `venv`, 含 `pyvenv.cfg` 的目录, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `dist`, `build`, `*.egg-info`）；两种模式都再过滤 `.reprollm/runs/**` 与 > 2 MiB 文件；结果排序、缓存。
  - `glob(pattern) -> list[RelPath]`（`fnmatch` 全路径）、`exists(rel)`, `read_text(rel, max_bytes=512KiB) -> str|None`（非文本返回 None，缓存）、`size(rel)`。
  - `python_files()`（≤ 500 个，超出截断并记录 `warnings`）、`readme_files()`（`README*` 不区分大小写，根目录与一级子目录）、`config_files()`（`*.yaml|*.yml|*.json|*.toml`，排除 `uv.lock`、`poetry.lock`、`pyproject.toml` 以外的 lockfile、`.reprollm/**`、`package-lock.json`）。
  - `dir_names() -> set[str]`（所有目录段名，小写）。
- `AuditContext.fs` 改为返回该实现。

**验收标准**：在 `hf_vllm_eval` 上 `files()` 与 `git ls-files` 一致；`.gitignore` 中的 `outputs/` 下新建文件不出现在列表；非 git 目录退化路径测试；大文件过滤测试；`read_text` 对二进制返回 None。

---

### M2-T02 `code.*` 规则补齐（S）

**范围**：`code.clean_tree`、`code.no_untracked`、`code.submodules_initialized`、`code.remote_recorded`（P1，若时间紧可留到 M3）。Evidence：`clean_tree` 列出前 10 个修改文件与总数；`no_untracked` 同理；`submodules_initialized` 列出未初始化路径。`fix_hint` 分别为：提交或 stash 改动；提交或加入 `.gitignore`；`git submodule update --init --recursive`；`git remote add origin <url>`。

**验收标准**：`dirty_tree` fixture 上 `clean_tree` 与 `no_untracked` 均 WARNING 且 evidence 路径正确；`hf_vllm_eval` 上均 PASS；`submodules_initialized` 用 stub `run_cmd` 返回 `-<sha> path` 行测试 FAIL，无 `.gitmodules` 时 skipped。

---

### M2-T03 依赖声明解析与 `env.*` 规则（L）

**范围**
- `core/deps.py`：
  - `DependencyDeclaration(name_normalized, specifier: str|None, exact_version: str|None, source_file, line)`；
  - 解析器：`requirements*.txt`（`packaging.requirements.Requirement`；支持 `-r other.txt` 递归、跳过 `-e`/URL/`--index-url` 行但记录为 `unparsed`）、`pyproject.toml`（PEP 621 `project.dependencies` + `project.optional-dependencies`；`tool.poetry.dependencies` 中 `^`/`~` 视为非精确，`"1.2.3"` 与 `{version = "1.2.3"}` 视为精确；`tool.uv.sources` 忽略）、`environment.yml`（conda `name=ver` / `name=ver=build` 视为精确，`name` 无版本非精确；`pip:` 子列表按 requirements 语法）、`Pipfile`（`[packages]` 精确当且仅当 `== x`）；
  - lockfile 存在性：`uv.lock`, `poetry.lock`, `Pipfile.lock`, `conda-lock.yml`, 以及「全 `==` 的 requirements 文件」；lockfile 内含的包名集合（`uv.lock`/`poetry.lock` 解析 `[[package]] name`；`Pipfile.lock` JSON keys；`conda-lock.yml` 的 `package[].name`）；
  - 名字规范化：`packaging.utils.canonicalize_name`；`pytorch`→`torch`。
- `core/pyscan.py`（本周实现导入部分，T04 复用）：对 `python_files()` 做 `ast.parse`（语法错误跳过并记 warning），收集顶层与 `from` 导入的模块名（取第一段与完整点分名）。
- `rules/env.py`：`01 §12.2` 六条规则。`env.llm_critical_deps_pinned` 的 `applies`：某包出现在依赖声明**或**被导入（导入名 → 分发名映射：`flash_attn`→`flash-attn`, `lm_eval`→`lm-eval`, `inspect_ai`→`inspect-ai`，其余同名）；FAIL 逐包一条 finding，evidence 指向声明行或导入位置；`fix_hint` 给出具体 `pkg==<installed or latest>` 建议（已安装版本可用 `envinfo.installed_versions`，否则写 `pkg==<version>`）。`env.secret_files_ignored`：遍历 `files()` 匹配 `01 §16.4`（减去模板名），对 git 仓库用 `git check-ignore`；被 git 跟踪的文件一定视为未忽略；非 git 仓库仅报 WARNING（降级，evidence 注明 "not a git repo"）。`env.reprollm_initialized`：仅 Level 0；message 附上检测到的 high/medium profile 并给出 `reprollm init --profiles a,b`。

**验收标准**
- `tests/unit/core/test_deps.py`：每种文件格式至少 3 个精确/非精确/递归用例；`pytorch` 归一化。
- 六个 fixture 的 `expected/audit_L0.json` 更新为完整 Level 0 结果，并与 `01 §12.1–12.2` 逐条核对：
  - `hf_vllm_eval`：`env.lockfile_present` WARNING；`env.llm_critical_deps_pinned` 对 `vllm` WARNING（`transformers`、`datasets` 已 pin）；`env.python_version_declared` WARNING；其余 PASS；
  - `openai_judge_eval`：`lockfile_present` WARNING；`llm_critical_deps_pinned` 对 `openai` WARNING；`python_version_declared` PASS；`secret_files_ignored` PASS（`.env.example` 免除）；
  - `privacy_custom_params`：`secret_files_ignored` CRITICAL（`.env`）；`llm_critical_deps_pinned` PASS（torch 由 conda 精确、transformers 由 pip 精确）；`lockfile_present` WARNING；
  - `not_a_git_repo`：`code.git_repo` CRITICAL，其它 `code.*` skipped，`secret_files_ignored` 走非 git 降级路径；
  - `no_deps_file`：`dependency_manifest_present` CRITICAL，`lockfile_present` skipped，`llm_critical_deps_pinned` skipped，`python_version_declared` WARNING。

---

### M2-T04 确定性 Profile 检测（L）

**范围**（`profiles/detect.py` + `core/pyscan.py` 扩展）
- `pyscan` 扩展：提取 `from_pretrained(` / `LLM(model=` / `AutoTokenizer.from_pretrained(` 的首个字符串常量参数（匹配 `^[\w.-]+/[\w.-]+$`），记录 `(value, path, line)`；检测关键字参数 `trust_remote_code=True`；提取 `from transformers import Trainer|Seq2SeqTrainer|TrainingArguments`。
- `detect(scanner, deps) -> DetectionResult`：严格按 `01 §13` 表实现；关键词扫描对象：README 文本、配置文件的**键名**（递归取 YAML/JSON/TOML 的 key，不取值）、目录名、文件名（去扩展名）；大小写不敏感；同一 profile 取最高置信；`rag`/`agent` 出现在结果中但标注 `shipped: false`。
- 检测结果写入 `AuditReport.profiles.detected`；`init` 使用 high+medium。
- 性能：`hf_vllm_eval` 规模仓库 < 200 ms；500 文件仓库 < 3 s（用生成的临时仓库测）。

**验收标准**
- `hf_vllm_eval`：`inference` high（vllm import）、`evaluation` medium（`mmlu`+`accuracy` ≥2 关键词）、hint `hf_ids` 含 `Qwen/Qwen3-32B`、`cais/mmlu` 不应作为 hf_id（它出自 `load_dataset`，本周不提取数据集 id）。
- `openai_judge_eval`：`llm_judge` medium（`judge`+`rubric`）、provider hint `openai`；`evaluation` low 或 medium 均可接受，但 snapshot 固定后不得漂移。
- `privacy_custom_params`：`privacy` medium（≥2 关键词）、`safety` low/medium（`asr`、`attack success rate`）、`trust_remote_code: true`、`hf_ids` 含 `meta-llama/Llama-3.1-8B-Instruct`。
- 关键词误报防护测试：README 中出现 "manager" 不触发 `agent`；"storage" 不触发 `rag`（`01 §13` 已规定词边界匹配，`-`/`_`/空格视为等价分隔符）。

---

### M2-T05 Profile loader 与 7 个内置 Profile 骨架（M）

**范围**
- `profiles/loader.py`：`load_builtin(name)`、`load_user(root, name)`（`.reprollm/profiles/<name>.yaml` 覆盖同名内置）、`resolve(names) -> ResolvedProfiles`（含 `core`；`extends` 闭包，左到右合并；环 → `UserError`；未知 rule id → `UserError` 列出未知项；`core` 出现在 `experiment.profiles` → `UserError`）；合并语义按 `01 §6`。
- 7 个 YAML：`core`, `inference`, `evaluation`, `llm_judge`, `finetuning`, `safety`, `privacy`。本周 `rules` 只写已实现的规则（`core` 列出全部 `code.*`、`env.*`、`exec.*`；其余六个 `rules: []`），`required_fields`、`severity_overrides`（只写涉及 `exec.seed_declared` 的项）、`detect` 按 `01 §6.1` 与 `§13` 完整填写。文件顶部注释：`# rules are completed in M3`。
- `cli/profiles.py`：`profiles list`（名字 + 描述 + 是否用户覆盖）、`profiles show NAME`（解析后的规则列表、继承链、required_fields）。spec 表里标为 M3，但本周实现成本低，直接完成。

**验收标准**：继承闭包测试（`llm_judge` → `evaluation` → `inference` → `core`）；环检测；用户覆盖；未知规则报错信息含名字；`profiles show llm_judge` 输出 snapshot。

---

### M2-T06 `exec.*` 规则与 Level 1 引擎路径（M）

**范围**
- `core/engine.py`：读取 manifest（错误 → exit 2 并打印字段路径）；level 检测；从 `experiment.profiles` 解析 profile（`--profiles` 覆盖）；规则选择按 `01 §11` 第 4 步；`AuditReport.profiles.declared/resolved` 填充；Level 1 下仍执行检测并填 `detected`。
- `rules/exec_.py`：`exec.command_declared`、`exec.seed_declared`、`exec.run_recorded`、`exec.profile_detection_mismatch`（`01 §12.3`）。

**验收标准**：在 `hf_vllm_eval` 上写入一份最小 manifest（`profiles: [inference]`，无 `execution`）后：level 1；`exec.command_declared` WARNING；`exec.seed_declared` WARNING；`exec.run_recorded` INFO；`exec.profile_detection_mismatch`：声明 `inference` 有检测证据 → 不因它报；`evaluation` medium 未声明 → 不报（只有 high 才报）；再加一个声明 `finetuning`（无证据）→ INFO。`--level 0` 强制降级测试。

---

### M2-T07 `reprollm init`（L）

**范围**（`cli/init.py`, `cli/templates/manifest.yaml.j2`, `cli/templates/config.yaml.j2`）
- 默认非交互：运行检测；`experiment.profiles` = high+medium 检测结果（`rag`/`agent` 排除）或 `--profiles` 指定；`models.primary.id` 若 `hf_ids` 恰好一个则预填并注释 `# detected: <path>:<line>`，多个则预填第一个并把其余写成注释；`project.name` = 目录名；所选 profile 的 `required_fields` 并集渲染为带 `# TODO` 的键（值为 `null`），其它章节以注释形式给出示例（不生成会导致校验失败的内容）。
- 生成的 manifest **必须**能被 `load_manifest` 加载（`null` 值允许；`extra=forbid` 不受注释影响）。
- 创建 `.reprollm/config.yaml`（模板含全部默认值与注释）、`.reprollm/project-rules.yaml`（`schema_version: 1`, `rules: []`, `ignored_candidates: []`）。
- 已存在 `reprollm.yaml` → exit 2 提示 `--force`；`--force` 覆盖 manifest 但**不**覆盖 `.reprollm/` 下已有文件。
- `--interactive`：对 `required_fields` 逐项 `typer.prompt`，默认值为检测结果；空输入保留 `null`。
- 结束时打印下一步：`reprollm audit .`。

**验收标准**
- 三个正向 fixture 各有 `expected/init.yaml`（snapshot，`project.name` 用固定值以避免临时目录名漂移：`init --name` 隐藏选项或测试后替换）。
- 生成的 manifest 立即 `audit` 不 crash，且 level 为 1。
- `--force` 行为测试；`--interactive` 用 CliRunner `input=` 测试。

---

### M2-T08 文本 reporter 完善与 `--show-passed/--show-skipped`（S）

**范围**：按 `01 §21` 完整实现分组、计数行、Result 行；`detected profiles` 在 Level 0 输出末尾单独一段 `Detected profiles: inference (high), evaluation (medium) — run: reprollm init --profiles inference,evaluation`；宽度自适应；长 message 不截断。

**验收标准**：`--no-color` 文本 snapshot（六个 fixture）。

---

### M2-T09 CHANGELOG、README Quick Start 初稿、0.1.0（S）

**范围**：README 增加「Quick start (0.1.0)」：`pip install reprollm` → `reprollm audit .` → `reprollm init` → `reprollm audit .`，并附一段真实输出（来自 `hf_vllm_eval`）；去掉 "not yet usable" 标注，改为 "Alpha: audit Level 0/1 and init are usable; lock/run/diff arrive in 0.2–0.4"；CHANGELOG `0.1.0` 段；版本号。

---

### M2-T10 Dogfooding on Project A（人工 + agent 协作，M）

**流程**
1. 维护者在 Project A 根目录运行 `reprollm audit . --format json --output /tmp/a_L0.json` 与 `reprollm audit .`，把输出（脱敏后）贴到 issue `M2 dogfooding: Project A`。
2. 运行 `reprollm init`，检查预填是否正确；把生成的 manifest 贴到 issue。
3. 记录三类问题：crash；误报/漏报（逐条列 rule id）；检测错误。
4. Agent 针对每条问题开 PR 修复，或在 spec 有歧义时开 `spec` issue。
5. 至少修复全部 crash 与明显误报；漏报可进 M3。

**验收标准**：issue 中每条问题都有 PR 链接或明确的推迟理由。

---

## 4. 本周禁区

- 不实现 `model.*`、`dataset.*`、`gen.*`、`prompt.*`、`eval.*`、`judge.*`、`train.*`、`privacy.*`（M3）。
- 不实现 `lock`、`run`、`diff`、`export`、`discover`。
- 检测不得读取文件**值**中的自由文本来推断（只读 README 文本、配置**键名**、目录/文件名、AST）；不得调用任何 LLM。
- 不在 `init` 中写入用户仓库除 `reprollm.yaml` 与 `.reprollm/` 以外的任何文件。
- `requirements.txt` 解析不得联网解析 `-r https://…`。

---

## 5. Dogfooding

见 T10。Project B、C 本周不要求，但若时间允许可跑 `audit .` 看是否 crash。

---

## 6. Definition of Done（M2）

- [ ] `code.*`、`env.*`、`exec.*` 共 16 条规则实现，每条 ≥1 PASS + ≥1 FAIL 测试
- [ ] 六个 fixture 的 `audit_L0.json` 为完整 Level 0 结果并通过
- [ ] 三个正向 fixture 有 `init.yaml` snapshot
- [ ] 7 个内置 profile YAML 存在，loader 测试通过，`profiles list/show` 可用
- [ ] Project A dogfooding issue 关闭或所有条目有归属
- [ ] 覆盖率 ≥ 80 %（M3 起 85 %）
- [ ] `v0.1.0` 发布至 PyPI，干净环境验证 `audit` 与 `init`

---

## 7. 发布步骤

同 M1 §7，tag `v0.1.0`。Release notes 必须包含一段 `hf_vllm_eval` 上的真实 `audit` 输出。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| 关键词检测在真实仓库上误报多（如 README 泛泛提到 "agent"） | 词边界匹配；单关键词只给 low；`init` 不采用 low；把 Project A 的误报逐条加入负向测试 |
| requirements 语法千奇百怪导致解析崩溃 | 解析器任何异常都降级为 `unparsed` 行并记 warning，绝不让 audit crash；对崩溃样本加测试 |
| `git ls-files` 在超大仓库（数十万文件）慢 | 本周先接受；在 `RepoScanner` 记录耗时到 `-v` 输出，为 M8 优化留数据 |
| `init` 生成的 manifest 让用户觉得「一堆 TODO」 | 只渲染所选 profile 的 `required_fields`，其它以注释示例给出；文本末尾一句话说明哪些是必填 |
