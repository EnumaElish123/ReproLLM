# M5 — Runtime Capture (`reprollm run`) + Secret Redaction (P0)

> Sprint：Week 5，2026-10-05 → 2026-10-11（10-05 → 10-07 仍在假期内；T01 是本周唯一不可顺延的任务）
> 目标版本：`0.3.0`
> GitHub Milestone：`M5`

---

## 0. 给 coding agent 的阅读顺序

1. `00` §6 D-15、D-16、D-18、D-19、D-20、D-41；§9
2. `01` §5（Run record 全文，含 5.1 R-01…R-12）、§15（Bindings）、§16（Redaction，**逐字实现**）、§12.12（`consistency.*` 的 run 侧）、§22 T-05、T-06
3. `AGENTS.md` §3「Redaction is a security boundary」
4. 本文档

---

## 1. 本周目标

实现 **Runtime truth**：`reprollm run -- <cmd>` 在不改变用户命令行为的前提下记录代码、环境、硬件、命令、文件哈希与声明绑定的观测值，并且**任何写出的字节都经过 redaction**。本周结束时：

- `core/redaction.py` 完成，100 % 分支覆盖，正负语料齐备；
- `run` / `runs list` / `runs show` 可用；
- 声明式 bindings 的 CLI / config / env 观测可用；
- `consistency.file_hashes`（run 侧）、`consistency.generation_params`、`consistency.model_identity`、`consistency.env_vs_lock`、`consistency.custom_fields` 可用；
- 「泄漏金测试」：向 run 注入伪造密钥，整个 run 目录 grep 不到任一密钥；
- 在 Project A 的真实 GPU 节点上完成一次真实 `run`。

---

## 2. 人工任务

| # | 任务 |
|---|---|
| H1 | 从 §3 创建 Issue，挂 `M5`；**T01 必须第一个合并**，其它任务的 PR 在 T01 合并前不得合并 |
| H2 | 在 Project A 的 GPU 节点（若有 SLURM 则通过 `srun`/`sbatch`）用 `reprollm run -- <真实评测命令>` 跑一次短任务；把 `run.json`（脱敏后）贴到 issue；亲自 `grep` 一遍 run 目录里是否有 token、主机名、用户名、绝对路径 |
| H3 | 在 Project B 上设置真实 `OPENAI_API_KEY` 后 `run`，确认记录为 `{present: true}` |
| H4 | 审阅 T01 PR：这是本 sprint 唯一需要逐行读的 PR |
| H5 | 合并 T10 后打 tag `v0.3.0` |

---

## 3. 任务清单

分支前缀 `m5/`。

### M5-T01 Redaction 模块与语料（L，P0，首个合并）

**范围**（`core/redaction.py`, `tests/fixtures/secrets/`）
- `is_secret_env_name(name: str) -> bool`：`01 §16.1` 分段规则 + `KNOWN_SECRET_NAMES`。
- `redact_text(text: str) -> tuple[str, int]`：`01 §16.2` 全部 9 类模式，按表中顺序应用；`generic_kv` 只替换捕获组 2；返回替换次数。
- `redact_env(env: Mapping[str,str], mode: "allowlist"|"all", extra_allowlist: Sequence[str]) -> dict[str, str | dict]`：`01 §16.3`；名字规则优先于白名单；`allowlist` 模式下非白名单变量**不出现**在结果中；secret name → `{"present": True}`；其余值经 `redact_text`。
- `is_forbidden_file(rel_path: str) -> bool`：`01 §16.4` 含模板名免除。
- `redact_lines(iter[str]) -> iter[str]`：供 `--capture-output` 逐行使用（PEM 多行块跨行时以「开始标记出现后直到结束标记」整体屏蔽，实现为状态机）。
- 语料：`positive.txt`（每类 ≥3 条，含边界：`sk-` 后恰 16 字符、`sk-proj-`、JWT 带 `=` 填充变体、PEM 含 `RSA`/`EC`/`OPENSSH` 三种头、`https://user:p%40ss@host`、`api_key: "abcdefgh1234"`、`password=…`）；`negative.txt`（`MAX_TOKENS=2048`、`TOKENIZERS_PARALLELISM=false`、`Qwen/Qwen3-32B`、40 位 commit sha、`sk-short`、`hf_` 后 19 字符、`eyJ` 但只有两段、URL 无凭据、`token_count: 512`、`secret_santa.py`）；`env_cases.yaml`（≥ 30 个名字 → 布尔，含 `HF_TOKEN: true`、`MAX_TOKENS: false`、`TOKENIZERS_PARALLELISM: false`、`SSH_AUTH_SOCK: true`、`KEY_FRAMES: true`、`CUDA_VISIBLE_DEVICES: false`、`DATABASE_URL: true`）。
- CI：在 pytest 之后增加步骤 `coverage report --fail-under=100 --include='src/reprollm/core/redaction.py'`（分支覆盖需 `[tool.coverage.run] branch = true`）。

**验收标准**：`positive.txt` 每行经 `redact_text` 后不含原始密钥片段且计数 ≥1；`negative.txt` 每行原样返回、计数 0；`env_cases.yaml` 全部匹配；`redact_env` 两种模式的完整用例；分支覆盖 100 %。

---

### M5-T02 硬件与调度器捕获（S）

**范围**（`run/hardware.py`, `run/slurm.py`）
- `capture_hardware() -> Hardware`：`cpu_count`（`os.cpu_count()`）；两次 `nvidia-smi` 查询（`01 §5.1 R-07`）；解析 CSV；`uuid_sha256`；`nvidia-smi` 头部行解析 `CUDA Version: 12.6`（`nvidia-smi` 无参数输出的首屏，取 `CUDA Version:\s*([\d.]+)`）；任何失败 → `source: unavailable`，其余字段为空列表/None；总耗时上限 5 s（`run_cmd` timeout）。
- `capture_scheduler(env) -> Scheduler|None`：`SLURM_*`、`PBS_*`、`LSB_*`，经 `is_secret_env_name` 过滤。
- `tests/fixtures/nvidia_smi/`：`query_gpu_2x.csv`（两卡）、`driver.csv`、`header.txt`、`missing.txt`（模拟 127）。

**验收标准**：两卡解析；缺失二进制；SLURM 变量过滤（构造 `SLURM_JOB_ACCOUNT_TOKEN`（假想）应被过滤）。

---

### M5-T03 文件捕获与 bindings 观测（L）

**范围**（`run/capture.py`, `core/bindings.py`, `core/configread.py`）
- `resolve_argv_files(argv, root, cwd) -> list[FileRef]`：对每个 token 及 `--k=v` 的 `v`：相对 `cwd` 解析；必须落在 `root` 内的**常规文件**（symlink 解析后仍在 root 内）；去重；`origin: argv`。
- `declared_files(manifest) -> list[FileRef]`（与 M4 `files` 集合相同的来源 + prompts 路径）`origin: declared`；bindings 的 config 路径 `origin: binding`。
- `hash_and_snapshot(refs, run_dir, *, snapshot: bool, max_bytes)`：sha256/size；文本判定；forbidden → `redacted: true, snapshot: null`；文本 ≤ max → `redact_text` 后写 `files/<sha256>`（注意：sha256 是**原文**的哈希，snapshot 是脱敏文本，spec 如此，文档要说明）；`files[].redacted` 在 redaction 计数 > 0 时为 true。
- `core/configread.py`：`read_config_value(path, dotted_key)`：按扩展名 YAML/JSON/TOML；列表索引为整数段；缺失 → `KeyError` 由调用方转 warning。
- `core/bindings.py`：`observe(bindings, argv, env, root) -> dict[field_path, list[Observation]]` 按 `01 §15.1`；`normalize(value)` 按 `§15.2`；`values_equal(a, b)`。project-rules 的 bindings 也在此合并（M7 之前 project-rules 为空）。
- `artifacts.outputs` 在子进程结束后按 glob 收集并 hash（不快照）。

**验收标准**：argv 文件解析（含 `--config=configs/eval.yaml`、不存在的路径、root 外路径被拒、符号链接逃逸被拒）；forbidden 文件不快照；文本/二进制判定；bindings 三种来源观测与 `--temperature=1.0` / `--temperature 1.0` / 重复 flag；normalization 用例（`"0"` vs `0.0`、`"True"` vs `true`、列表）。

---

### M5-T04 子进程包装器（L）

**范围**（`run/wrapper.py`）
- `execute(argv, *, root, cwd, run_dir, capture_output, env_capture, extra_allowlist, snapshot) -> RunRecord`，按 `01 §5.1` R-01、R-02、R-05、R-06、R-10、R-11、R-12：
  - 预写 `run.json`（`status: running`，最小字段）；
  - `Popen(argv, cwd, env=os.environ | {REPROLLM_RUN_ID, REPROLLM_RUN_DIR})`；`--capture-output` 时 `stdout=PIPE/stderr=PIPE` 两个线程逐行 `redact_lines` 写日志**并**回显到父进程 stdout/stderr（用户不能因为用了 reprollm 就看不到输出）；否则继承父进程 fd；
  - SIGINT/SIGTERM 转发给子进程（Windows 下只处理 `CTRL_C_EVENT`，标 `linux_only` 测试）；子进程被信号终止 → `status: interrupted`，`exit_code` 为 `-signal`；
  - 结束后：`code`（含 `patch.diff`：`git diff` 经 `redact_text`，`patch_sha256` 为脱敏后内容的哈希）、`environment`（`redact_env`、`hostname_sha256`、`packages`）、`hardware`、`scheduler`、manifest/lock 快照（存在则复制原文——manifest/lock 本身不含秘密，但仍过一次 `redact_text` 以防用户把 key 写进 params）、`files`、`bindings_observed`、`artifacts`、`warnings`；
  - 原子写 `run.json`；返回记录；调用方以子进程退出码退出。
- 目录创建：`run_id = <UTC yyyymmddThhmmssZ>-<secrets.token_hex(3)>`；冲突重试。
- 若 reprollm 自身在子进程结束后异常：尽力写入已收集字段 + `warnings` 记录异常类名，然后仍以子进程退出码退出（D-11）。

**验收标准**：`python -c "import os,sys; print(os.environ['REPROLLM_RUN_ID']); sys.exit(3)"` → exit 3、`status: completed`、`exit_code: 3`；`--capture-output` 下 stdout 中的伪造密钥在 `stdout.log` 里被脱敏而回显仍完整（回显不脱敏——这是用户自己的终端）；SIGINT 场景（linux_only）；预写记录存在性；`dirty_tree` fixture 下 `patch.diff` 生成并脱敏。

---

### M5-T05 CLI：`run`、`runs list`、`runs show`（M）

**范围**（`cli/run.py`, `cli/runs.py`）
- `reprollm run [--name] [--capture-output] [--env-capture] [--no-snapshot] [--cwd] -- CMD…`：`--` 之后原样传递；无 manifest 时仍可运行但打印 warning「no reprollm.yaml; bindings and declared files unavailable」；config 的 `run.*` 作为默认值。
- 结束打印一行：`Recorded run 20261005T093000Z-a1b2c3 (exit 0, 12.3 s, 3 files hashed, 2 bindings observed, 1 warning) → .reprollm/runs/…`。
- `runs list`：表格（run_id、started_at、status、exit、duration、name、dirty）；`--json`。
- `runs show RUN_ID`：人类可读摘要（命令、代码、环境关键包、GPU、文件、bindings 观测、warnings）；`--json` 输出 run.json 原文。RUN_ID 支持前缀匹配（唯一时）。

**验收标准**：CliRunner 端到端：在 `hf_vllm_eval`（complete manifest + lock from `hf_mock`）上运行 `run -- python -c pass --config configs/eval.yaml --temperature 1.0`（注意 `python -c pass` 会忽略多余参数），生成的 `run.json` 与 `expected/run.json` 一致（忽略：`run_id`、时间字段、`duration_seconds`、`hostname_sha256`、`environment.packages`、`environment.os`、`environment.python`、`hardware`（改用 canned nvidia-smi fixture 后可比较）、`cpu_count`）；`bindings_observed["generation.temperature"]` 含 cli=1.0 与 config=0.0 两条。

---

### M5-T06 `consistency.*` run 侧规则（M）

**范围**（`rules/consistency.py`）
- `ctx.runs`（按 `started_at` 排序，只读 `run.json`；损坏文件 → warning 跳过）、`ctx.latest_run`。
- `consistency.file_hashes`：增加 run 侧——`latest_run.files[]` 中与 lock 同路径者 sha256 不同 → CRITICAL（evidence 三列：lock / working tree / run）。
- `consistency.generation_params`：对 `bindings_observed` 中 `generation.*` 的每个字段，任一观测值 ≠ manifest 值 → CRITICAL；message 形如 `generation.temperature: manifest 0.0 · config(configs/eval.yaml:sampling.temperature) 0.0 · cli(--temperature) 1.0`。
- `consistency.model_identity`：`models.*.id` / `models.*.revision` 的观测 ≠ manifest/lock → CRITICAL。
- `consistency.env_vs_lock`：`latest_run.environment.packages` 与 `lock.environment.packages` 逐包比较；不同 → WARNING（每包一条）；仅 run 有 / 仅 lock 有 → INFO。
- `consistency.custom_fields`：对 project rules 中带 bindings 的字段（M7 起有数据）；本周实现逻辑并用手写 project-rules 文件测试。
- `exec.run_recorded` 现在在有 run 时 PASS。

**验收标准**：T05 的端到端场景后 `audit` → `consistency.generation_params` CRITICAL；`expected/audit_L2_after_run.json` snapshot；`env_vs_lock` 用手工构造的 lock/run 测试三种分支。

---

### M5-T07 泄漏金测试（M）

**范围**（`tests/integration/test_no_leaks.py`）
- 构造环境：`OPENAI_API_KEY=sk-FAKE…(48 chars)`、`HF_TOKEN=hf_FAKE…`、`MY_SERVICE_PASSWORD=hunter2hunter2`、`AWS_SECRET_ACCESS_KEY=…`、白名单变量 `CUDA_VISIBLE_DEVICES=0`；argv 含 `--api-key sk-FAKE…`、`--config configs/eval.yaml`、`.env`（forbidden 文件）；工作树 dirty 且 diff 中含 `password = "hunter2hunter2"`；`--capture-output` 且子进程打印 `hf_FAKE…`。
- 断言：递归读取 run 目录所有文件（含 JSON、日志、快照、patch），任一伪造密钥字符串出现 0 次；`OPENAI_API_KEY` 记录为 `{present: true}`；`CUDA_VISIBLE_DEVICES` 记录为 `"0"`；`MY_SERVICE_PASSWORD` 在 allowlist 模式下不出现，在 `all` 模式下为 `{present: true}`；`.env` 在 `files[]` 中 `redacted: true, snapshot: null`；`patch.diff` 中 `hunter2hunter2` 已替换。
- 同时断言 run 目录中不出现：真实主机名（`socket.gethostname()`）、当前用户名、`root` 的绝对路径。

**验收标准**：测试通过；此测试标记为 `security`，CI 单独一步运行并在失败时阻断发布 workflow（release.yml 先跑该测试）。

---

### M5-T08 文档与 README（S）

**范围**：`docs/run.md`：捕获了什么 / 没捕获什么；redaction 保证与已知误报（`SSH_AUTH_SOCK`）；`allowlist` vs `all`；为什么 `sha256` 是原文哈希而快照是脱敏文本；如何提交 `.reprollm/runs/`；`REPROLLM_RUN_ID` 用法示例（在用户代码中把输出写到 `$REPROLLM_RUN_DIR/artifacts/`）。README Quick start 加 `reprollm run -- python eval.py …`。`SECURITY.md` 补充「redaction 覆盖范围与报告方式」。

---

### M5-T09 Dogfooding A/B（M，人工主导）

见 §2 H2、H3。Agent 负责：把维护者贴出的问题转成 issue/PR；对真实 `nvidia-smi` 输出新增 fixture（若解析失败）；对真实 SLURM 变量集新增测试。

---

### M5-T10 发布 0.3.0（S）

CHANGELOG（含「run record schema v1 首次发布」「redaction policy」）、版本、tag。Release notes 附一段脱敏 `runs show` 输出与 `consistency.generation_params` 的 CRITICAL 示例。

---

## 4. 本周禁区

- 在 T01 合并前，任何写 run 目录的代码不得合并。
- 不做启发式 flag 解析（只有 bindings 声明的 flag 才被解读为参数值；其它 argv token 只做「是否文件」判断）。
- 不记录环境变量的非白名单值；不记录主机名明文、用户名、绝对路径。
- 不捕获 stdout/stderr 除非 `--capture-output`。
- 不实现 `diff` / `export` / `discover`；不实现 ExperimentState（M6）。
- 不在 `run/wrapper.py` 与 `core/proc.py` 之外调用 `subprocess`。

---

## 5. Dogfooding

见 T09。C 仓库本周不强制；若 C 的评测命令能在 10 分钟内跑完，可作为第三个真实样本。

---

## 6. Definition of Done（M5）

- [ ] `core/redaction.py` 100 % 分支覆盖，CI 单独门槛生效
- [ ] `run` / `runs list` / `runs show` 可用；`expected/run.json`、`expected/audit_L2_after_run.json` snapshot 通过
- [ ] 5 条 `consistency.*` run 侧规则实现并测试
- [ ] 泄漏金测试通过并接入 release workflow
- [ ] Project A 真实 GPU 节点 run 成功，维护者 grep 确认无泄漏；Project B `OPENAI_API_KEY` 记录为 `present: true`
- [ ] `docs/run.md` 完成
- [ ] `v0.3.0` 发布

---

## 7. 发布步骤

同前，tag `v0.3.0`。release.yml 在 publish 前运行 `pytest -m security`。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| Redaction 误报把合法配置值改坏（如某个真实模型名匹配 `generic_kv`） | `generic_kv` 要求值 ≥8 字符且键名命中；快照与原文 sha256 分离，用户可核对；误报进 negative 语料 |
| `--capture-output` 逐行脱敏影响长任务性能 | 只在显式开启时生效；线程 + 行缓冲；不做正则以外的处理 |
| 信号转发在 SLURM `srun` 下行为差异（srun 自己也转发） | 只转发一次；记录 `status: interrupted`；文档说明在 sbatch 脚本内包裹 `reprollm run` 的推荐写法 |
| 用户 argv 里有几十个文件路径（如数据分片列表） | 快照上限 1 MiB/文件；文件数 > 200 时只 hash 不快照并 warning |
| 假期导致 H2 延迟 | T01–T07 不依赖 H2；`0.3.0` 可在 H2 完成前发布，但 H2 的发现进入 M6 首日修复 |
