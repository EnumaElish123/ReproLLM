# 可靠性方案代码审查修订：PLAN-REVISE

日期：2026-10-03。基线：`781366e89362a54d9036d3aed070fad169ba8204`。

## 范围与交付

维护者要求按代码审查建议优化开发方案并上传。当前执行包更新为
[v1.2](../plan/reliability-2026-10-03/README.md)，保留四个工程 Sprint，各两次会话：

- 新增 P0 的 R02-R，覆盖 run 结构化值和文本快照的密钥脱敏，放入 S1-B。
- 新增 R06-G，在 S2-A 首先建立所有静态内容读取的项目根边界；R06-P 继续处理 include 图。
- 新增 R04-B，处理输入基线、运行中改写和结束后采集，成为 D01 / A01-B 验收前置。
- 新增 R05-S，明确已经存在的 Conda 规范冲突，作为 R05-B 实施合入的决定前置。
- 同步七份分册、总索引、README、Agent 提示词、roadmap 和 CHANGELOG。

这是一个文档任务，不实施上述产品修复，不修改规范、架构决策、gold、schema、工作流或依赖。
Issue #9 与必要 D-41 审阅保留各自范围；计划纳入不替代具体策略/代码决定。
保留原有未跟踪的用户目录和 v1.0 草稿。

## 代码审查证据

同轮前序审查在基线代码上、临时目录中使用合成输入复现：

| 场景 | 实际观察 | 对应任务 |
|---|---|---|
| 无效 manifest 强制覆盖 | 原合法文件未保留 | R01 |
| 普通键值密钥 | 合成值进入 lock，以及真实包装运行的 run.json / 配置快照 | R02 / R02-R |
| 两组顺序相反的重复 temperature 参数 | effective State 均选 0.1 | R03 |
| 通配 Python 版本、同名 pyproject | 通配版本判 exact；根依赖被工具-only 文件覆盖 | R05-A / R06-A |
| include 越界、普通 requirements / Python 外部软链接 | 读入根外合成内容 | R06-P / R06-G |
| Git 模式下 501 个 venv 源文件 | 业务 Python 未进入预算；fallback 可进入 | R07-A |
| child 读取 0.1 后改写 config 为 0.9 | exit 0；独立消费值 0.1，bindings 记录 0.9 | R04-B |
| Conda 声明 | `python=3.11` 判 exact，`torch==2.5.1` 未识别 | R05-B / R05-S |

这些是既有缺陷的复核，不是修复后的 PASS。具体重建输入、代码入口及未来验收矩阵见各任务卡。
没有使用真实密钥或发送模型请求。官方版本语义来源与日期记录在 R05-S；本次不修改 normative spec。

## 本次验证

环境：macOS / Python 3.12.14 / ReproLLM 0.6.1。锁定依赖安装成功后执行既有质量门：

- 全量 pytest：**1,927 passed、3 skipped、2 deselected、1 warning**；总覆盖率 **93.25%**。
- redaction：**100%**，59 条语句和 24 个分支均覆盖；security：**29 passed**。
- Ruff check、限定本次提交范围的格式检查、Mypy、十份 schema freshness、四项生成文档检查均通过。
- 三个 examples 的 L1 audit / lock freshness 均通过；self-audit 使用 `--fail-on never` 正常完成，不表示所有 findings 都为 PASS。
- 新计划任务的索引、会话顺序和提示词一致，本地文件链接与标题锚点通过检查。

完整命令、退出码、耗时、日志摘要及文档哈希保存在
[verification.json](reliability-plan-v1.2-2026-10-03/verification.json)。pytest 用时 102.738 秒，security 用时 3.593 秒；其余单项均低于 4 秒。验证驱动使用锁定环境中的工具，不修改产品测试。

本次如实记录以下环境差异：

- 初次离线安装因缺少构建缓存失败；联网安装锁定依赖后，离线复核通过。`uv.lock` 未变。
- `ruff format --check .` 首次因原有未跟踪 v1.0 草稿中的代码块失败。保留该用户文件原样，以 `--exclude plan/ReproLLM_Agent_Development_Plan_2026-10-03_v1.0.md.md` 重新检查通过；该草稿不在本次提交或远端 CI checkout 中。
- 现有未注册 `slow` marker 警告保留；未为文档任务修改测试配置。与上次 Linux 报告相比，本次在 macOS 有 3 项 skip，未将它们计入 passed。

## 五项目 Gate A 与基线差异

在质量门之后，对五个固定 checkout 分别执行：

```bash
<reprollm> audit . --format json --fail-on never
<reprollm> -v audit . --format json --fail-on never
```

另在同一环境采集 `AuditContext(root, level=0).detection.hints.model_dump(mode="json")`。
每项在运行前后核对 SHA、origin 和完整 clean 状态；所有命令退出码均为 0。

| 项目 | 固定 SHA | 两次 CLI 总耗时（秒） | 完整比较数 | 结果 |
|---|---|---:|---:|---|
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 1.094 | 5 | PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 1.120 | 5 | PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 1.547 | 5 | PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 0.586 | 5 | PASS |
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 13.297 | 5 | PASS |

比较覆盖默认/verbose 两份完整 L0 JSON、两份 stderr 和完整 hints，仅从 JSON 排除规范允许的 `generated_at` 并另验其格式。保留完整规则、profiles、依赖集合、路径、行号及证据；预期来自此前独立审阅的 [UX3 完整基线](ux3-2026-10-03/README.md)，基线文件哈希与 PLAN-IMPORT 记录一致，固定输入和 Python 文件数符合 `val.md`。

**10 次 CLI、25 项完整比较通过；相对上次基线无差异。** LlamaFactory 的 tracked `.env.local` CRITICAL、既有未精确固定依赖 finding，以及 lm-eval 的 816/500 截断诊断均保持原状；PASS 表示符合基线，不表示这些项目不存在风险。普通文档任务未改变产品命令，因此没有额外激活五项目 init/L1 等变化矩阵。

原始日志和完整比较保存在仓库外；仓库内证据只使用相对路径或逻辑占位符。没有更改 gold、schema、规范、产品代码或依赖。交付提交为包含本报告的 PLAN-REVISE 文档提交，可从文件历史定位；该提交的远端验证由 [GitHub Actions](https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml?query=branch%3Amain) 记录，本地结果不替代远端结果。

## 后续

实现仍从 S1-A：R00 → R01 开始，依照实际 HEAD 复核，不能回退到审查 SHA。
本次普通文档会话不激活里程碑或发布 Gate B；VAL-R01/R02/R03 仍按既有资源阻塞登记。
后续代码任务须重新建立失败回归、执行全质量门及适用 Gate A/B，不能将本报告当作修复验收。
