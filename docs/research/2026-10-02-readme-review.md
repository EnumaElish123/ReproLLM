# README 调研与改版记录（2026-10-02）

对应任务：[README-T01 / M8-T02–T08](../plan/README_2026-10-02.md)。

## 选择了哪些项目

选择与实验追踪、可复现工作流或 LLM 评测相邻，且 GitHub 页面显示超过
一万星的五个项目。以下为 2026-10-02 查看官方仓库时的**四舍五入约数**，
不是精确整数或全领域排名。Star 用于筛选参考对象，不证明 README 导致了增长。

| 项目与官方来源 | Stars（约） | 定位关联 | README 中值得学习的做法 |
|---|---:|---|---|
| [MLflow](https://github.com/mlflow/mlflow) · [README](https://raw.githubusercontent.com/mlflow/mlflow/master/README.md) | 28.2k | 实验追踪与 AI 工程 | 品牌首屏、文档／Demo 导航；三步上手后展示分场景能力和截图 |
| [Promptfoo](https://github.com/promptfoo/promptfoo) · [README](https://raw.githubusercontent.com/promptfoo/promptfoo/main/README.md) | 25.6k | LLM 测试、CLI 和 CI | 安装到查看结果的短路径；用任务动词组织能力，配终端和结果矩阵 |
| [DeepEval](https://github.com/confident-ai/deepeval) · [README](https://raw.githubusercontent.com/confident-ai/deepeval/main/README.md) | 18.6k | LLM 评测 | 清楚的类比与用例、首屏演示；用一个案例贯穿代码与结果，折叠较长能力列表 |
| [DVC](https://github.com/treeverse/dvc) · [README](https://raw.githubusercontent.com/treeverse/dvc/main/README.rst) | 15.9k | 本地可复现 ML 工作流 | Banner 与导航；按用户任务解释价值，用“任务→命令”表呈现工作流 |
| [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) · [README](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/README.md) | 14.1k | 研究评测工具 | 用可核验的研究与生态资料建立信任；复杂配置通过文档导航、后端分组和引用入口展开 |

DVC 的旧地址 `iterative/dvc` 当前重定向到 `treeverse/dvc`，本记录使用后者。
另浏览了 [Aim](https://github.com/aimhubio/aim)（约 6.3k），其界面演示与折叠
高级说明有启发，但未放入以上高星主样本。所有观察来自项目自己的 README；
未复用他人的图片、Logo、宣传文案或采用率声明。

## 总结：丰富不等于把手册搬到首页

1. **首屏给定位、结果和入口。** 读者应先明白工具服务谁、解决什么问题、
   下一步点哪里。徽章用于验证版本、质量和许可，不堆砌无依据的数字。
2. **先展示产品证据。** 对 CLI 工具，真实的 finding、修复提示和 diff
   比抽象架构描述更能帮助判断价值。ReproLLM 没有 dashboard，不制作虚构界面。
3. **第一次成功要小。** 安装后先在已有仓库执行 audit；需要 manifest、
   网络、模型或运行资源的流程放到进阶部分。
4. **按用户问题组织能力。** 用“共享前检查／结果变了／准备论文／自定义方法”
   承接需求，再说明相关状态、命令和产物。
5. **让复杂性逐步展开。** README 负责概览与选择；字段、规则、全部选项和
   完整教程链接到专门文档，开发安装和文件布局采用折叠块。
6. **信任来自可核验事实。** 展示实际 CI、已存在的例子、软件引用和验证记录；
   不把维护者的测试仓库写成第三方用户，不把历史或待资源验证写成新通过。

这些是基于样本结构作出的编辑建议；没有点击率、转化率或用户实验能够证明
它们一定增加 Stars。后续可通过真实冷启动试用和 issue 反馈判断效果。

## 对 ReproLLM 的具体调整

| 原有问题 | 本次调整 |
|---|---|
| 首屏几乎全是文字，缺少视觉层次 | 原创桌面／窄屏 SVG；品牌、manifest→lock→run 的证据路径与直接导航 |
| 重复出现 Quick start 和 30-second demo | 合并为真实输出展示与三步首个 audit 路径 |
| 大段命令掩盖使用场景 | 增加研究问题、五类 LLM 状态、步骤→命令→产物表 |
| “真实输出”没有给清楚来源，profile 提示也已过时 | 从当前 quickstart 同源 fixture 实际取样，注明摘录、省略与退出状态 |
| `FAIL` 文本容易被误认为进程失败 | 明确 finding 状态与 `--fail-on` 阈值不同，保留真实 CLI 行为 |
| 一行 Action 用法省略必要上下文 | 给 checkout、Python 和 Action 的完整最小 workflow；解释 lock 检查开关 |
| 示例、论文导出、框架和贡献入口分散 | 增加示例选择表、conference 导出命令、框架指南、文档导航、引用入口 |
| 首页路线图仍停留在旧里程碑 | 链接现有 backlog 和待审提案，区分 main 与发布包 |
| 链接的 docs/index.md 仍称 0.1.1／export 未实现 | 同步更新文档入口和命令可用性，保留已发布／未发布边界 |

保留架构 §2 的产品定位原文、§2.1 的五类状态和核心原则。没有改变 CLI、
规则、profile、schema、依赖、发布版本或未获批准的规范提案。

## 示例与版本证据

- README 的 warning 来自 `scripts/gen_quickstart.py` 的 `prepare` 创建的
  初始化前副本；实际命令为 `reprollm --no-color audit .`。仓库干净、无
  manifest/lock/run，3 WARNING、2 INFO、6 PASS、1 SKIP，退出 0。
  完整文本 SHA-256：`f1f4f9dbe84dd08447c2b4df5ba00de137941784696654a8bfd96ebc0e4fc8e2`。
  README 只摘录 vLLM 依赖 finding 及其路径和 fix，不伪造整份成功报告。
- Diff 摘录来自 [CI 再生成的 quickstart](../quickstart.md#explain-the-drift)：
  标准库探针的 `generation.max_tokens` 从 32 改为 48，HIGH；未把它称为模型推理。
- 公开 [PyPI 元数据](https://pypi.org/pypi/reprollm/json) 核实最新版本为 0.6.1，
  Python 要求为 `>=3.10`，wheel 于 2026-10-01 08:07:30 UTC 上传。
  当前 main 的完整 Discover 预览、候选显示、Action 和导出修复属于 Unreleased。
- 图片为本次原创静态 SVG。主图用于宽屏，紧凑图用于窄屏；均含 title、desc，
  README 提供 alt。图片 URL 指向自有仓库，方便包描述引用；它们不是运行截图。

## 验证记录

基于 `0ee49493bedf0c204ff3b202d5c67ccda02d5771` 加本次文档修改验证。
此次只改文档，不激活真实模型、付费 API 或 GPU Gate B。

| 检查 | 结果 |
|---|---|
| 本地文件与标题锚点 | 88 个链接／锚点通过；架构定位原文和真实 warning 摘录逐字匹配 |
| 图片 | 两个 SVG 均通过 XML 检查，含 title/desc，无脚本或外部资源引用 |
| 视觉 | 浏览器检查宽屏、390px 窄屏和深色背景；主图／紧凑图、正文、导航正常显示 |
| PyPI Markdown | `readme_renderer[md]` 渲染成功、无警告，保留 picture、图片和 details；仅临时验证环境补齐渲染组件 |
| 包描述与构建 | `python -m build --no-isolation --wheel --sdist` 成功；两个产物 `twine check` 通过；未发布新包 |
| 全套测试 | `pytest -q --cov=reprollm --cov-branch`：1518 passed、3 skipped、2 deselected，81.65 秒；既有 slow marker 警告 1 条 |
| 安全边界 | redaction 59 条语句、24 个分支，均为 100% 覆盖；未修改脱敏代码 |
| 静态检查 | `ruff check .`、`ruff format --check .`、`mypy src/` 通过；115 个源文件类型检查通过 |
| 生成内容 | 9 份导出 schema 无差异；rules、profiles、CLI、quickstart 四项 freshness 通过 |

图片渲染检查使用隔离的本地预览，图片来自与待提交文件相同的 SVG。
最终 GitHub CI 以本次提交对应的 [workflow run](https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml)
为准；发布前仍需单独执行已有资源门。本次没有 fixture、schema 或 gold answer 变更。
### 五项目 Level 0 Gate A

完整本地质量门通过后，执行既有 `run_l0_gate.py --quality-gate-confirmed`
入口；对 val.md 的五个原始 checkout 先后核验固定 SHA、origin 和干净状态。
实际产品命令为 `reprollm -v audit <pinned-checkout> --level 0 --format json --fail-on never`。
五份完整 JSON 仅忽略 `generated_at` 后均与已审核的 0.6.1 基线相同，完整 stderr
也逐字相同；规则状态、全部依赖集合、profile 置信度、检测 hints、源码行号和
扫描截断诊断另按 val.md §§3–6 的独立预期复核通过。没有修改 checkout 或金标准。

| 仓库 | 固定 SHA | 预期／实际退出 | audit 秒数 | Critical/Warning/Info/Pass/Suppressed/Skipped | 完整差异数 |
|---|---|---:|---:|---|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 0 | 7.114 | 0/14/1/8/0/1 | 0 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 0 | 0.686 | 0/16/1/8/0/1 | 0 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 0 | 0.864 | 1/15/1/7/0/1 | 0 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 0 | 0.699 | 0/7/1/7/0/1 | 0 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 0 | 0.392 | 0/7/1/7/0/1 | 0 |

退出 0 来自显式 `--fail-on never`，不表示 findings 全部通过；LlamaFactory
的已知 CRITICAL 和 lm-eval 的 500/816 扫描截断均保留。5 次产品 audit、26 条
带命令／目标 SHA／退出码／耗时／输出哈希的记录，共 10.169 秒子进程时间。
[紧凑 Gate A 证据](2026-10-02-readme-evidence/gate-a-complete.json)保留每个目标的
完整报告／诊断哈希与比较结果。完整原始 JSON、stderr、命令记录、源码快照和
独立预期核对结果保留于本次本地验证证据。产品源码仍为
`0ee49493bedf0c204ff3b202d5c67ccda02d5771`，执行时包含此次未提交文档改动；
源码快照记录了该工作区差异哈希，不冒称最终提交已被测试。本次文档任务没有
新增命令行为，不激活 Gate B，也未使用网络、凭据、模型或 GPU。
