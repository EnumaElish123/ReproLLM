# 可靠性方案入库与 Agent 导航：PLAN-IMPORT

日期：2026-10-03。任务：PLAN-IMPORT。

## 范围与交付

维护者明确要求将本轮方案和开发 Agent 提示词纳入仓库并 push。本次交付：

- [七份 v1.1 方案及目录入口](../plan/reliability-2026-10-03/README.md)，方案字节与交付版本完全一致。
- [独立 Agent 提示词](../plan/reliability-2026-10-03/AGENT_PROMPTS.md)，包含首个 S1-A、后续会话、策略审议和 A01-A 输入准备。
- [稳定的当前计划索引](../plan/README.md)，以及 AGENTS、贡献指南、文档首页和 roadmap 的入口链接。
- CHANGELOG 的 PLAN-IMPORT 文档条目与本次验证记录。

本次尚未开始 R00/R01 等实现任务；不把方案入库当作修复完成。七份计划中的待决策略、schema 审阅和资源边界保持原样。

基线提交：`590ee1739484bd21e21594e294e7ddf14bfd093f`。交付提交是包含本报告的文档提交，可在文件历史中定位。产品源码、测试、依赖、工作流、examples、导出 schemas、架构决策、规范和 val.md 与基线相同；仅更新文档及计划导航。

## 文档核验

七份方案逐字节比对通过；新增计划/提示词及入口的本地文件链接和标题锚点均经过检查。未添加仅为文档复制而复述实现的单元测试；执行既有质量门和五项目 gate。首个实现入口仍是 S1-A：R00、R01。

## 本地质量门

环境：Linux / Python 3.12.14。

- 全量 pytest：**1,930 passed，2 deselected，1 warning**；总覆盖率 **93.27%**。
- redaction：**100%**，59 条语句和 24 个分支均覆盖。
- security：**29 passed**；现有未注册 `slow` marker 警告仍记录，未在文档任务中顺带修改配置。
- Ruff check / format、Mypy、十份 JSON Schema freshness、四项生成文档、三个 examples 的 L1 audit / lock freshness 均通过。
- self-audit 在本次文档工作区以 `--fail-on never` 正常执行；这不表示其所有 findings 都是 PASS。

以下为本次实际运行命令，所有退出码为 0。schema 的临时输出位置以逻辑占位符表示；原始日志和临时产物在仓库外保存，证据清单保留结果摘要及日志摘要哈希。

| 检查 | 命令 | 退出码 | 耗时（秒） |
|---|---|---:|---:|
| `locked_dependencies` | `uv sync --locked --dev` | 0 | 0.051 |
| `pytest` | `uv run pytest -q --cov=reprollm --cov-report=term --cov-fail-under=85` | 0 | 115.925 |
| `redaction_coverage` | `uv run coverage report --fail-under=100 --include=src/reprollm/core/redaction.py` | 0 | 0.116 |
| `ruff` | `uv run ruff check .` | 0 | 0.027 |
| `format` | `uv run ruff format --check .` | 0 | 0.024 |
| `mypy` | `uv run mypy src/` | 0 | 0.199 |
| `security` | `uv run pytest -q -m security` | 0 | 2.385 |
| `rules_doc` | `uv run python scripts/gen_rules_doc.py --check` | 0 | 0.258 |
| `profiles_doc` | `uv run python scripts/gen_profiles_doc.py --check` | 0 | 0.271 |
| `cli_doc` | `uv run python scripts/gen_cli_doc.py --check` | 0 | 7.853 |
| `quickstart_doc` | `uv run python scripts/gen_quickstart.py --check` | 0 | 4.315 |
| `schema_export` | `uv run reprollm schema export --out <temporary-schema-directory>` | 0 | 0.382 |
| `schema_freshness` | `compare ten exported JSON schemas byte-for-byte` | 0 | — |
| `hf_vllm_eval_audit` | `uv run reprollm audit examples/hf_vllm_eval --level 1 --fail-on never --format json` | 0 | 0.378 |
| `hf_vllm_eval_lock` | `uv run reprollm lock --check examples/hf_vllm_eval` | 0 | 0.381 |
| `openai_judge_eval_audit` | `uv run reprollm audit examples/openai_judge_eval --level 1 --fail-on never --format json` | 0 | 0.377 |
| `openai_judge_eval_lock` | `uv run reprollm lock --check examples/openai_judge_eval` | 0 | 0.423 |
| `privacy_custom_params_audit` | `uv run reprollm audit examples/privacy_custom_params --level 1 --fail-on never --format json` | 0 | 0.366 |
| `privacy_custom_params_lock` | `uv run reprollm lock --check examples/privacy_custom_params` | 0 | 0.311 |
| `self_audit` | `uv run reprollm audit . --format github --fail-on never` | 0 | 3.439 |

## 五项目 Gate A

全部项目在运行前后均核对固定 SHA、origin 和完整 clean 状态。每个执行：

```bash
<reprollm> audit . --format json --fail-on never
<reprollm> -v audit . --format json --fail-on never
```

`<reprollm>` 是本轮安装环境中的 CLI，cwd 是各固定 checkout。另用该环境的 `AuditContext(root).detection.hints.model_dump(mode="json")` 检查完整检测线索。

每个项目做五项完整比较：默认 L0 JSON、默认 stderr、verbose L0 JSON、verbose stderr、完整 hints。两份 L0 报告仅排除 `generated_at`，并单独验证时间格式；保留所有规则、状态、依赖集合、profiles、路径、物理行号和证据。预期来自已有独立审阅的 [UX3 完整基线](ux3-2026-10-03/README.md)，并按 val.md 核对固定源码与 Python 文件总数。

| 项目 | 固定 SHA | CLI 命令数 | 完整比较数 | CLI 耗时（秒） | Gate 结果 |
|---|---|---:|---:|---:|---|
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 2 | 5 | 1.738 | PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 2 | 5 | 1.833 | PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 2 | 5 | 2.587 | PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 2 | 5 | 0.795 | PASS |
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 2 | 5 | 22.523 | PASS |

合计 **10 次 CLI 命令、25 项完整比较全部通过，未出现未解释差异**。这里 PASS 表示与既有 gold 一致：LlamaFactory tracked `.env.local` 的 CRITICAL、各项目未精确固定依赖等 finding 均保留。lm-eval 816 个 Python 文件的 500 截断在 verbose 中披露；默认诊断行为仍按当前基线记录，R07-B 的拟议修复未实施。

本次无产品命令行为变更，所以没有额外激活 init/L1 的五项目变化矩阵。质量门中的 examples 验证按现有 CI 要求执行。

## 证据与兼容性

[verification.json](reliability-plan-import-2026-10-03/verification.json) 保存：七份方案的 SHA-256、质量检查命令/退出码/耗时、每个固定输入的身份、完整比较的 expected/actual 摘要、已有 gold 文件的路径与哈希。原始 audit/hints/diagnostics 和外部项目副本保存在仓库外；不向仓库提交机器路径、虚拟环境或外部 checkout。

没有修改 gold、schema、drift 默认策略或 release 工作流。AGENTS 的改动仅把当前计划定位到新的索引，保留原质量门、五项目验证和 D-41 审阅要求。

## 资源与后续会话

本次是普通文档入库，不激活里程碑/发布 Gate B；没有模型调用、付费 API 或 GPU 任务。VAL-R01/R02/R03 的既有资源阻塞状态保持不变。

下一次实现读取 [S1-A 提示词](../plan/reliability-2026-10-03/AGENT_PROMPTS.md#1-第一次实现s1-ar00r01) 和 [Sprint 1](../plan/reliability-2026-10-03/01_Persistence_and_State.md)，以当前 HEAD 复核 R00/R01。推送提交的远端 CI 由该提交的 [GitHub Actions](https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml?query=branch%3Amain) 记录；本报告中的本地验证不替代远端平台结果。
