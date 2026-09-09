# M1 — Foundation

> Sprint：Week 1，2026-09-07 → 2026-09-13
> 目标版本：`0.0.1`（发布到 PyPI 以占名；README 明确标注 "pre-alpha, not yet usable"）
> GitHub Milestone：`M1`

---

## 0. 给 coding agent 的阅读顺序

1. `00_architecture_and_decisions.md`（全文，重点 §6 Decision Register）
2. `01_specification.md` §0、§1、§2、§3、§6、§7、§8、§9、§10、§11、§22、§23
3. `AGENTS.md`
4. 本文档

本周不需要读 `01` 的 §4（Lock）、§5（Run）、§12（Rule catalog 除 12.1）、§13–§20。

---

## 1. 本周目标

建立一个 **可安装、可测试、CI 全绿、schema 已定型** 的包骨架，并让「一条规则从 registry 到 reporter」的完整通路跑通（用 `code.git_repo`、`code.git_commit` 两条真实规则验证）。本周结束时：

- `pip install reprollm==0.0.1 && reprollm --version` 在干净虚拟环境中可用；
- `reprollm doctor` 可用；
- `reprollm audit .` 在任意目录可运行，只输出两条 `code.*` 规则的结果（Level 0 的其余规则在 M2）；
- 所有 pydantic schema（Manifest / Profile / ProjectRules / Config / Finding / AuditReport / Lock / RunRecord）已定义并导出 JSON Schema；
- 6 个黄金 fixture 仓库的文件内容已就位，`materialize_repo` 可确定性地生成 git 仓库。

---

## 2. 人工任务（维护者，agent 无法代做）

按顺序，建议在 09-07 当天完成：

| # | 任务 | 说明 |
|---|---|---|
| H1 | 创建 GitHub org `reprollm`，仓库 `reprollm/reprollm`，Public，Apache-2.0 | 初始只含 README 即可，其余由 agent PR 补齐 |
| H2 | 仓库设置：默认分支 `main`；Branch protection：要求 CI 通过、禁止 force push；允许 squash merge，禁用 merge commit / rebase merge | D-35 |
| H3 | 创建 Labels：`M1`…`M8`、`spec`、`rule`、`profile`、`integration`、`redaction`、`security`、`docs`、`good first issue`、`help wanted`、`blocked` | |
| H4 | 创建 Milestones `M1`…`M8`，due date 为各周周日 | 见 `00 §10` |
| H5 | PyPI：注册账号（若无）；在 PyPI「Publishing」中添加 *pending trusted publisher*：project `reprollm`，owner `reprollm`，repo `reprollm`，workflow `release.yml`，environment `pypi` | 必须在 T02 的 release workflow 首次运行之前完成 |
| H6 | GitHub 仓库创建 environment `pypi`（可加 required reviewer = 你本人，作为发布前最后一道人工确认） | |
| H7 | 在本地/远程 Linux 开发机安装 `uv`、`git ≥ 2.30`、Python 3.10–3.12 | `doctor` 会检查 |
| H8 | 把 `plan/00`、`plan/01`、`plan/AGENTS.md` 放入仓库：`docs/plan/00_architecture_and_decisions.md`、`docs/plan/01_specification.md`、根目录 `AGENTS.md` | 可以由 agent 的 T01 PR 一起提交，但内容以本目录为准 |
| H9 | 用 `gh` 从本文档 §3 批量创建 Issue 并挂到 Milestone M1（可让 agent 生成命令，你确认后执行） | |

---

## 3. 任务清单

规模标记：S ≈ 半天以内，M ≈ 1 天，L ≈ 2 天。每个任务一个 PR，分支 `m1/t01-<slug>` 等。

### M1-T01 仓库骨架与工具链（M）

**范围**
- `pyproject.toml`：`hatchling` 构建；`[project]` 元数据（name `reprollm`、description 用 `00 §2` 的 positioning statement、license Apache-2.0、`requires-python = ">=3.10"`、classifiers、urls）；依赖：`typer`、`pydantic>=2`、`pyyaml`、`rich`, `jinja2`, `httpx`, `packaging`, `tomli; python_version<"3.11"`；dev 依赖：`pytest`, `pytest-cov`, `respx`, `ruff`, `mypy`, `types-PyYAML`, `jsonschema`（校验导出的 JSON Schema）；snapshot 比较用 T08 的自定义 helper，不引入 syrupy；`[project.scripts] reprollm = "reprollm.cli.main:app"`。
- 版本单一来源：`src/reprollm/__init__.py` 的 `__version__`，hatch `[tool.hatch.version] path`。
- `src/reprollm/` 目录树按 `00 §8` 建立（空模块带 docstring 即可）。
- `ruff`（`select = ["E","F","I","UP","B","SIM"]`, line-length 100）、`mypy --strict`（`src/`）、`pytest` 配置（`testpaths=tests`，markers：`linux_only`, `network`）。
- 根文件：`LICENSE`（Apache-2.0）、`README.md`（positioning statement + 「Status: pre-alpha (0.0.x). Not yet usable. First usable release: 0.1.0.」+ 计划链接）、`CONTRIBUTING.md`（引用 AGENTS.md 的流程节；如何跑测试；Conventional Commits）、`SECURITY.md`（私密披露邮箱；明确 redaction bypass 属安全漏洞）、`CODE_OF_CONDUCT.md`（Contributor Covenant 2.1）、`CHANGELOG.md`（Keep a Changelog，`Unreleased` 段）、`.gitignore`（Python + `.reprollm/runs/` 不忽略——注意：**不要**忽略 `.reprollm/`，用户需要提交它）。
- `.github/PULL_REQUEST_TEMPLATE.md`：勾选项「实现的 spec 章节 / 新增或修改的测试 / fixture 或 snapshot 是否更新及原因 / CHANGELOG 已更新 / 测试无网络访问 / 未新增重依赖」。
- `.github/ISSUE_TEMPLATE/`：`bug_report.yml`、`feature_request.yml`、`spec_change.yml`、`new_rule.yml`。
- `AGENTS.md`、`docs/plan/00_*.md`、`docs/plan/01_*.md` 入库。

**验收标准**
- `uv sync --dev && uv run reprollm --version` 输出 `reprollm 0.0.1.dev0`（或 0.0.1）。
- `uv run ruff check . && uv run ruff format --check . && uv run mypy src/` 全部通过（空模块也要过 strict）。
- `uv build` 产出 sdist + wheel；wheel 内不含 tests。

**测试要求**：`tests/unit/test_version.py` 验证 `--version` 与 `__version__` 一致。

---

### M1-T02 CI 与发布流水线（M）

**范围**
- `.github/workflows/ci.yml`：触发 `push`（main）与 `pull_request`；矩阵按 `01 §22 T-09`；步骤：`uv sync --dev` → `ruff check` → `ruff format --check` → `mypy src/` → `pytest --cov=reprollm --cov-report=xml`（Windows 加 `-m "not linux_only"`）→ `reprollm schema export --out /tmp/schemas && diff -r schemas /tmp/schemas`（schema freshness，仅 ubuntu 3.12）→ 上传 coverage artifact。并发取消同分支旧任务。
- `.github/workflows/release.yml`：触发 `push` tag `v*`；job 1 `build`（`uv build`，上传 dist）；job 2 `publish`（environment `pypi`，`permissions: id-token: write`，`pypa/gh-action-pypi-publish`，trusted publishing，不使用 token）；job 3 `github-release`（用 CHANGELOG 对应段落生成 Release notes）。
- 发布前校验：tag 版本必须等于 `__version__`，否则 job 失败。

**验收标准**
- 一个故意失败 lint 的 PR 会被 CI 拦截；修复后绿。
- 在 fork 或临时 tag（如 `v0.0.1rc1`，发布到 TestPyPI 可选）上验证 release workflow 能走到 publish 步骤——如果 H5 尚未完成，本项可在 T10 时一并验证。

**测试要求**：无代码测试；PR 描述附 CI 运行链接。

---

### M1-T03 Schema：Manifest / Profile / ProjectRules / Config（L）

**范围**
- `schemas/manifest.py`：完整实现 `01 §3`，`extra="forbid"`（`custom`、`*.params`、`artifacts.metadata` 例外），验证规则 V-01…V-08。角色 map 用 `dict[RoleKey, ModelSpec]`，`RoleKey = Annotated[str, StringConstraints(pattern=...)]`。路径字段统一用 `RelPath` 类型（自定义验证器：POSIX、相对、无 `..`、无盘符）。
- `schemas/profile.py`：`01 §6`。
- `schemas/project_rules.py`：`01 §7`。
- `schemas/config.py`：`01 §8`（`ignore[].reason` 非空）。
- 所有模型：`model_config = ConfigDict(extra="forbid", populate_by_name=True)`；字段顺序与 spec 一致（决定 YAML 输出顺序）。
- `core/yaml_io.py`：`load_yaml(path) -> dict`（安全加载，空文件 → `{}`）、`dump_yaml(obj) -> str`（不排序键、保持模型字段顺序、2 空格、`allow_unicode`、宽行不折叠）、`load_manifest(path) -> Manifest`（pydantic 错误转换为 `UserError`，消息含字段路径与行号——行号可用 `yaml` 的 mark 信息，做不到时省略）。

**验收标准**
- `tests/unit/schemas/test_manifest.py`：覆盖每条 V-01…V-08 的正反例；`00 §10 reprollm.yaml` 示例（改成角色 map 形式）能加载；未知顶层键报错并指出键名；`custom` 任意结构可通过。
- `tests/unit/schemas/test_profile.py`、`test_project_rules.py`、`test_config.py`：基本正反例。
- `dump_yaml(load_yaml(x))` 对一个含全部字段的 manifest 输出字段顺序稳定（snapshot）。

---

### M1-T04 Schema：Finding / AuditReport / Lock / RunRecord / DetectionResult + `schema export`（M）

**范围**
- `schemas/finding.py`：`Severity` 枚举（含排序 CRITICAL>WARNING>INFO>PASS）、`Evidence`、`Finding`（`01 §9`）、`AuditReport`（`01 §10`）、`DetectionResult`（`01 §13` 输出结构）。
- `schemas/lock.py`：`Provenance`、`Lock` 全部字段（`01 §4`），本周只需模型与导出，不需要生产者。
- `schemas/run_record.py`：`RunRecord` 全部字段（`01 §5`），同上。
- `cli/schema.py`：`reprollm schema export [--out DIR]` 写出 `01 §23` 列出的文件（`diff_report`、`discover_candidates` 两个模型本周先给最小占位：只含 `schema_version`、`reprollm_version`，在 M6/M7 补全；但文件必须存在以便 CI freshness 检查从本周起生效）。JSON Schema 使用 pydantic `model_json_schema()`，`$id` 为 `https://reprollm.dev/schemas/<name>.schema.json`，输出 `json.dumps(indent=2, sort_keys=True)` + 尾换行。
- 提交 `schemas/*.schema.json`。

**验收标准**
- `uv run reprollm schema export --out schemas/` 后 `git status` 干净（幂等）。
- 每个 JSON Schema 文件能被 `jsonschema` 校验器加载（测试里用 `jsonschema.Draft202012Validator.check_schema`；`jsonschema` 仅作为 dev 依赖）。
- `Severity` 排序测试；`Finding` 序列化字段顺序与 spec 一致。

---

### M1-T05 Core 工具层：paths / hashing / proc / git / envinfo / errors（M）

**范围**
- `core/errors.py`：`ReproLLMError`、`UserError(exit_code=2)`、`InternalError(3)`。
- `core/paths.py`：常量（`01 §2`）；`find_root(start) -> Path`（含 `reprollm.yaml` 的最近祖先 → git toplevel → start）；`RepoPaths` 数据类。
- `core/hashing.py`：`sha256_bytes`, `sha256_file(path, chunk=1MiB)`, `sha256_text(str)`，返回带 `sha256:` 前缀；`is_text_file(path, max_bytes)`（UTF-8 可解码且无 NUL）。
- `core/proc.py`：`run_cmd(argv, cwd=None, timeout=30, env=None) -> CmdResult(returncode, stdout, stderr)`；不用 shell；`FileNotFoundError` → `CmdResult(returncode=127, …)`；这是唯一允许调用 `subprocess` 的位置（`run/wrapper.py` 在 M5 例外，需在 AGENTS.md 备注）。
- `core/git.py`：`GitInfo` 数据类 + `inspect_git(root) -> GitInfo`：`is_repo`, `toplevel`, `commit`, `branch`（detached 时 `HEAD`）, `modified: list[str]`（`status --porcelain` 中非 `??` 行）, `untracked: list[str]`, `submodules: list[(path, initialized)]`, `remote_origin: str|None`（凭据剥离：`https://user:pass@` → `https://`）；`check_ignore(paths) -> set[str]`；`ls_files(include_untracked=True) -> list[str]`。全部走 `run_cmd`。
- `core/envinfo.py`：`LLM_CRITICAL_PACKAGES`（`01 §4.4`）、`installed_versions(names) -> dict[str,str]`（`importlib.metadata`，分发名映射：`flash_attn`→`flash-attn`, `lm_eval`→`lm_eval`, `inspect_ai`→`inspect-ai`）、`python_version()`, `platform_name()`（linux/darwin/windows）、`os_description()`。

**验收标准**
- `tests/unit/core/`：hashing 已知向量；`find_root` 三种分支；`inspect_git` 在 `materialize_repo("hf_vllm_eval")` 上返回确定 commit（sha 写死在测试中，验证 T-03 的确定性）；`remote_origin` 凭据剥离；`run_cmd` 缺失二进制返回 127；`installed_versions` 对未安装包返回缺省。

---

### M1-T06 Rule registry、AuditContext、engine 骨架、reporters、首批两条规则（L）

**范围**
- `core/registry.py`：`Rule` 基类（属性见 AGENTS.md §6；`aliases: tuple[str,...] = ()`）、`@register_rule`、`get_rule(id_or_alias)`、`all_rules()`、重复 ID 注册报 `InternalError`。
- `core/context.py`：`AuditContext`（`01 §11` 字段），惰性属性（`git`、`fs`、`detection` 等在首次访问时计算；本周 `detection` 返回空结果，`fs` 提供 `RepoScanner` 的最小实现：文件列表 + 跳过规则 + 大小上限）。
- `core/levels.py`：`detect_level(paths) -> 0|1|2`。
- `core/engine.py`：`run_audit(root, *, level=None, profiles=None, config=None) -> AuditReport`，实现 `01 §11` 全部 8 步；profile 解析本周只支持隐式 `core`（`profiles/loader.py` 最小版：加载 `core.yaml`；继承与用户 profile 在 M3）。`core.yaml` 本周只列 `code.git_repo`, `code.git_commit`。
- `rules/code.py`：`code.git_repo`, `code.git_commit`（`01 §12.1`），含 `fix_hint`。
- `reporters/json_.py`：AuditReport → JSON（`01 §10` 排序）。
- `reporters/text.py`：`01 §21` 格式（rich；`--no-color`/非 TTY/`NO_COLOR` 处理；ASCII 备用符号）。
- `cli/audit.py`：`reprollm audit [PATH] --format --output --fail-on --level --show-passed --show-skipped`；退出码 `01 §1.1`。`--profiles` 本周接受但仅校验为已知名（只有 core），M3 生效。

**验收标准**
- 在 `materialize_repo("hf_vllm_eval")` 上 `audit --format json` 输出与 `tests/fixtures/repos/hf_vllm_eval/expected/audit_L0.json` 一致（本周该文件仅含两条 PASS + summary + `level: 0` + 空 detection）。
- 在 `not_a_git_repo` 上：`code.git_repo` CRITICAL，`code.git_commit` skipped，退出码 1；`--fail-on never` 退出 0。
- 在一个 `git init` 后无提交的目录上：`code.git_commit` CRITICAL。
- 文本输出 snapshot（`--no-color`）。
- JSON 输出通过 `audit_report.schema.json` 校验。

---

### M1-T07 `doctor` 命令（S）

**范围**：`cli/doctor.py`。检查项与状态（ok / warn / missing）：Python 版本（≥3.10）；`git` 可用及版本（≥2.30 建议）；`nvidia-smi` 可用（缺失 → warn，说明 GPU 捕获不可用）；`uv` 可用（informational）；LLM-critical 包已安装版本列表；若存在 `reprollm.yaml`/`.reprollm/config.yaml` 则校验并报告；`--check-network`：`HEAD https://huggingface.co/api/models/gpt2`（10 s 超时）；`--json`。退出码：任何 `missing` 的必需项（Python、git）→ 1，否则 0。

**验收标准**：CliRunner 测试覆盖 git 缺失（stub `run_cmd` 返回 127）、`--json` 结构、`--check-network` 在 respx mock 下 ok/fail 两种路径。

---

### M1-T08 测试基础设施与黄金 fixture 仓库（L）

**范围**
- `tests/conftest.py`：
  - autouse session fixture：`respx.mock(assert_all_mocked=True)` 全局开启，未 mock 的 HTTP 请求直接失败；
  - `stub_run_cmd` fixture：按 argv 前缀返回预设 `CmdResult`；
  - `materialize_repo(name, tmp_path) -> Path`：复制 `tests/fixtures/repos/<name>/tree/` 到临时目录；读取 `tests/fixtures/repos/<name>/fixture.yaml`（`git: bool`，`branch: main`，`post_commit: [{op: write|append|delete, path, content}]`）；若 `git: true`：`git init -b main`、`git add -A`、`git commit -m "fixture"`，环境变量固定为 `01 §22 T-03`（另加 `GIT_CONFIG_GLOBAL=/dev/null`、`GIT_CONFIG_NOSYSTEM=1`，避免本机 hooks/签名影响）；然后执行 `post_commit`；
  - `assert_json_snapshot(actual, expected_path, ignore=("generated_at","reprollm_version","resolved_at","observed_at"))`，环境变量 `REPROLLM_UPDATE_SNAPSHOTS=1` 时写回。
- 六个 fixture 的 `tree/` 内容（**必须按下面写，后续 sprint 的 expected 依赖它们**）：

  **`hf_vllm_eval`**（`git: true`）
  - `README.md`：标题 "MMLU evaluation with vLLM"；正文提到 "accuracy on MMLU abstract_algebra", "temperature 0", "greedy decoding"。
  - `eval.py`：`import argparse, yaml`；`from vllm import LLM, SamplingParams`；`from datasets import load_dataset`；`from transformers import AutoTokenizer`；`AutoTokenizer.from_pretrained("Qwen/Qwen3-32B")`；`load_dataset("cais/mmlu", "abstract_algebra", split="test")`；argparse 参数 `--config`（默认 `configs/eval.yaml`）、`--temperature`（float）、`--max-tokens`（int）、`--seed`（int）；读取 config 后构造 `SamplingParams(temperature=..., top_p=..., max_tokens=...)`；不需要可运行，但必须是合法 Python。
  - `configs/eval.yaml`：`model: Qwen/Qwen3-32B`；`sampling: {temperature: 0.0, top_p: 1.0, max_tokens: 2048}`；`dataset: {name: cais/mmlu, subset: abstract_algebra, split: test}`；`backend: {tensor_parallel_size: 2, dtype: bfloat16}`。
  - `prompts/system.txt`：三行任意英文 system prompt。
  - `requirements.txt`：`vllm>=0.10`、`transformers==4.57.0`、`datasets==3.2.0`、`pyyaml>=6`。
  - `.gitignore`：`outputs/`、`__pycache__/`。

  **`openai_judge_eval`**（`git: true`）
  - `README.md`：标题 "Pairwise LLM-as-a-judge evaluation"；提到 "judge model", "rubric", "win rate"。
  - `judge.py`：`from openai import OpenAI`；读取 `prompts/judge.txt`；`client.chat.completions.create(model=args.judge_model, messages=[...])`，**不设置 temperature**；argparse `--judge-model`（默认 `gpt-4o`）、`--n-trials`（默认 1）、`--pairs`（默认 `data/pairs.jsonl`）。
  - `pyproject.toml`：`[project] name="judge-eval" version="0.1.0" requires-python=">=3.10" dependencies=["openai>=1.0", "pandas"]`。
  - `prompts/judge.txt`：一段 judge 指令。
  - `data/pairs.jsonl`：3 行 JSON（`{"prompt":..., "a":..., "b":...}`）。
  - `.env.example`：`OPENAI_API_KEY=your-key-here`。

  **`privacy_custom_params`**（`git: true`）
  - `README.md`：标题 "Privacy-preserving LLM inference"；提到 "differential privacy", "threat model: honest-but-curious server", "membership inference attack", "attack success rate (ASR)"。
  - `method.py`：`import torch, yaml`；`from transformers import AutoModelForCausalLM`；`AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B-Instruct", trust_remote_code=True)`；读取 `configs/privacy.yaml` 中 `method.alpha`, `method.delta`, `method.safe_interval`, `method.orth_loss` 并在函数中使用。
  - `attack.py`：读取 `attack.query_budget`；定义 `membership_inference(...)`。
  - `configs/privacy.yaml`：`method: {name: orthogonal_noise, alpha: 0.25, delta: 1.5, safe_interval: [0.1, 0.9], orth_loss: 0.1}`；`attack: {method: mia, query_budget: 1000}`。
  - `environment.yml`：`name: privinf`；`dependencies: [python=3.11, pytorch=2.8.0, pip, {pip: [transformers==4.57.0, pyyaml]}]`。
  - `.env`：`OPENAI_API_KEY=sk-FAKEFAKEFAKEFAKEFAKEFAKE0000`（故意存在且未忽略；值为明显伪造）。
  - `.gitignore`：`__pycache__/`（**不**含 `.env`）。

  **`not_a_git_repo`**（`git: false`）：`train.py`（`import torch`）、`requirements.txt`（`torch==2.8.0`）。

  **`dirty_tree`**（`git: true`；`post_commit`: `append configs/run.yaml "\nextra: 1\n"`；`write scratch.txt "tmp"`）：`run.py`、`configs/run.yaml`（`seed: 42`）、`requirements.txt`（`transformers==4.57.0`）。

  **`no_deps_file`**（`git: true`）：仅 `run.py`（`print("hi")`）。

- 每个 fixture 目录含 `README.md`（说明用途、故意植入的问题、以及「这些 fake secret 仅用于测试」）与 `expected/audit_L0.json`（本周只含 `code.git_repo`、`code.git_commit` 的结果）。
- `tests/fixtures/secrets/`：本周只创建目录与 `README.md`，语料在 M5。
- `tests/fixtures/hf_api/`、`tests/fixtures/nvidia_smi/`：创建目录与 README，内容在 M4/M5。

**验收标准**
- `materialize_repo` 对同一 fixture 在两次调用中得到相同 commit sha（测试断言具体值，并在 fixture README 记录该 sha）。
- 六个 fixture 的 `audit_L0.json` snapshot 测试通过。
- 全套测试在 Windows runner 上通过（`git` 存在；`materialize_repo` 需用 `GIT_CONFIG_GLOBAL` 指向空文件而非 `/dev/null`）。

---

### M1-T09 文档骨架（S）

**范围**：`docs/index.md`（一句话定位 + 状态 + 路线图链接）；`docs/adoption.md`（表格模板：月份 / PyPI 下载 / GitHub dependents / 外部 issue / 外部 PR / 已知使用仓库 / 论文；首行 2026-09）；`docs/plan/` 已由 T01 放入；README 加 badges（CI、PyPI、License）。

**验收标准**：链接无 404（`lychee` 可选，不进 CI）。

---

### M1-T10 发布 0.0.1（S，本周最后一个 PR + 人工打 tag）

**范围**：`__version__ = "0.0.1"`；CHANGELOG `## [0.0.1] - 2026-09-13`（内容："Project skeleton, schemas, doctor, first two audit rules. Not yet usable."）；PR 合并后由维护者 `git tag v0.0.1 && git push --tags`；release workflow 发布至 PyPI；在干净虚拟环境验证 `pip install reprollm==0.0.1 && reprollm --version && reprollm doctor`。

---

## 4. 本周禁区

- 不实现除 `code.git_repo`、`code.git_commit` 之外的任何规则。
- 不实现 `init` / `lock` / `run` / `diff` / `export` / `discover`（命令可以先不注册；如注册则必须输出 "not available until 0.x.0" 并退出 2）。
- 不引入 `huggingface_hub`、`GitPython`、`numpy`、`torch` 等依赖。
- 不在 `core/proc.py` 之外调用 `subprocess`。
- 不在测试中访问网络。
- 不修改 `01_specification.md` 的字段名；若发现 spec 问题，开 `spec` issue。

---

## 5. Dogfooding

本周无功能可 dogfood。唯一动作：在 Project A（HF + vLLM 评测仓库）的根目录运行 `reprollm audit .` 与 `reprollm doctor`，确认不 crash，把输出贴到 M1 收尾 issue 里。

---

## 6. Definition of Done（M1）

- [ ] H1–H9 全部完成
- [ ] T01–T10 全部 PR 合并，CI 绿
- [ ] `schemas/` 与代码一致（freshness 检查在 CI 生效）
- [ ] 六个 fixture 的 `audit_L0.json` 存在并通过
- [ ] `pip install reprollm==0.0.1` 在干净环境可用
- [ ] `docs/adoption.md` 有 2026-09 首行（数值可为 0）
- [ ] GitHub Release `v0.0.1` 存在，notes 来自 CHANGELOG

---

## 7. 发布步骤

1. 合并 T10 PR。
2. `git checkout main && git pull && git tag -a v0.0.1 -m "v0.0.1" && git push origin v0.0.1`。
3. 观察 release workflow；在 `pypi` environment 处人工批准（若配置了 reviewer）。
4. 干净环境验证；把验证命令输出贴进 Release notes 评论。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| PyPI trusted publisher 配置错误导致首发失败 | H5/H6 在 T02 前完成；失败时不要改用 API token，修正 publisher 配置后重新 push 同一 tag（先删远端 tag） |
| Windows runner 上 git 行为差异（CRLF、路径） | `.gitattributes` 设 `* text=auto eol=lf`；fixture 文件全部 LF；`materialize_repo` 设置 `core.autocrlf=false` |
| pydantic `extra="forbid"` 让 manifest 过于严格，未来加字段麻烦 | 这是有意为之（拼写错误必须报错）；新增字段走 spec 变更 |
| Agent 为了让 mypy strict 通过而滥用 `Any`/`type: ignore` | PR 模板加一条：新增 `type: ignore` 必须注明原因；review 时 grep |
