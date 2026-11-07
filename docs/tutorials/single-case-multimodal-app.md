# 单病例多模态智能体应用的完整证据链

本教程把 ReproLLM 应用到一个**真实形态的研究应用**上：一个多阶段、多模态的
中医舌苔问诊智能体（图像分类 → 视觉语言模型 → 多轮信息收集 → RAG 检索 →
任务规划 → 多角色协作 → 网络搜索 → 报告生成），并记录一条可审计的证据链。

与 [第一次使用](first-experiment.md)（保存一条命令并重放）和
[并发本地模型隔离](concurrent-local-experiments.md)（工作区隔离）不同，本教程
的重点是：**当应用有图像输入、多个模型角色、外部检索/搜索状态和辅助权重文件
时，如何让每个环节的"实际消费"都留下可校验的证据**。

应用仓库：[LingshuSmartLink](https://github.com/LiangRichard13/LingshuSmartLink)，
本文固定应用试用提交 `b09becc18b1b9cd0e4d6ac04ed61a7dcbb63554b`；改动提案
见 [PR #2](https://github.com/LiangRichard13/LingshuSmartLink/pull/2)，截至核对时尚未合入
应用默认分支。[固定试用报告](https://github.com/LiangRichard13/LingshuSmartLink/blob/b09becc18b1b9cd0e4d6ac04ed61a7dcbb63554b/docs/reprollm-single-case-trial.md)
包含原始试用与后续更新；[维护者证据分级](../adoption/lingshu-2026-11-07.md)区分公开材料与贡献者报告。

**边界先行**：贡献者报告完成了三种模式的单病例链路；原始 local/live 回执与真实资产
主要保留在其私有证据目录。维护者只复核本文的离线 fixture 路径。成功运行本身不能证明
任意输入被正确消费，仍须检查独立见证；也不表示诊断正确或任何医疗、模型效果成立。

## 三种模式：证据只能声称到各自的实际来源

| 模式 | 分类/embedding/RAG | LLM/搜索 | 可以声称的证据 |
|---|---|---|---|
| fixture | 注入的固定结果，不加载真实权重 | 人工构造的确定响应（标记 `synthetic`） | 编排真实执行、配置真实消费、产物与回执可复现 |
| local | 真实 ResNet18 / GTE / Chroma | 仍为注入响应 | 真实本地组件与检索行为进入回执 |
| live | 真实本地组件 | 真实 provider API 与真实搜索 | 单病例完整在线运行，记录实际模型与响应 |

fixture 不叫"历史录制"——它是脚本化的确定响应。只有 live 的输出才携带
provider 真实返回；把 fixture 的成功说成"模型效果好"是本教程明确反对的。

## 准备

下列可执行示例使用 **Windows PowerShell**，并只运行 fixture。首次安装需要网络；
之后的 fixture 命令不需要网络、GPU、付费 API 或应用重依赖。

```powershell
git clone https://github.com/LiangRichard13/LingshuSmartLink.git
cd LingshuSmartLink
git checkout --detach b09becc18b1b9cd0e4d6ac04ed61a7dcbb63554b
uv venv --python 3.12 .venv-trial
uv pip install --python .venv-trial/Scripts/python.exe `
  "reprollm @ git+https://github.com/EnumaElish123/ReproLLM.git@d73f45f2b5334cd05e382b86b137e37d9aabda12" `
  "pytest==8.3.5"
$Python = (Resolve-Path .venv-trial/Scripts/python.exe).Path
$Repro = (Resolve-Path .venv-trial/Scripts/reprollm.exe).Path
$env:PYTHONUTF8 = "1"
```

这里安装的是固定提交的 **未发布 0.7.0 源码**，包含 `.pth` 目录扩展；当前正式
PyPI 0.6.1 不含该扩展。此处固定源码不代表其全部依赖也已锁定；请保留实际安装清单。
POSIX 用户需将解释器改为 `.venv-trial/bin/python`、入口改为 `.venv-trial/bin/reprollm`，
并转换 PowerShell 的变量、调用和续行语法。

fixture 的 recorder 与 child 可共用这套轻量环境。local/live 则须另建应用 child 环境，
按原应用的平台兼容说明准备 CPU 依赖及真实资产，不能直接把原 Linux/CUDA requirements
照搬到 Windows。使用该 child 解释器执行 `tools/trial_tools.py env --output trial/environment.json`，
再把 run 命令的 child 换成它；**不要把 recorder 的包清单当作另一个 child 环境的证明**。

## 合成病例与输入

试用分支已自带这些合成输入（合入后克隆即可直接使用）；只有当 `trial/`
目录为空时才需要从零生成：

```powershell
& $Python tools/trial_tools.py prepare --mode fixture --variant baseline
& $Python tools/trial_tools.py env --output trial/environment.json
```

固定提交已经带有种子，不执行 `seed`。从零构建时，`seed` 生成合成病例
（`trial/cases/case-001.json`，`synthetic: true`）、有效
PNG、小语料、脚本化 LLM/搜索 cassette 和全部提示词文件（模板从原代码逐字
迁移到 `trial/prompts/*.txt`，成为运行时单一来源）。**已存在的文件会被拒绝
覆盖**——这是刻意的：分支自带的种子资产与 lock 记录一一对应，重新生成会
破坏 hash 链。

关键点：**图像走显式 argv**（`--image trial/cases/case-001.png`），而不是像
应用原交互入口那样从 stdin 读取。`reprollm run` 记录 child 的 argv——stdin
传入的图片路径不会出现在运行记录里，只有 manifest 的"声明"，无法构成 child
实际收到该图片的观察证据。

## ReproLLM 接入：声明、规则与锁定

试用分支**已经随仓库提交**了 `reprollm.yaml`、`reprollm.lock`、
`.reprollm/project-rules.yaml` 与用户 profile（`trial_policy`）——克隆后直接
核对；`prepare` 与本机环境采集后要重新生成离线 lock，不能假定分支自带的 lock
对本机更新后的声明仍 fresh。所有写入均在上述独立克隆中完成：

```powershell
& $Repro lock . --offline
& $Repro lock . --check
$Replay = @("backend/replay_case.py", "--mode", "fixture",
  "--case", "trial/cases/case-001.json", "--image", "trial/cases/case-001.png",
  "--config", "trial/configs/current.yaml", "--cassette", "trial/fixtures/external.json",
  "--output-dir", "trial/outputs/current")
& $Repro run --dry-run -- $Python @Replay
& $Repro run --name my-first-fixture-run --capture-output -- $Python @Replay
```

从输出读取实际 RUN_ID（后续示例的 `RUN_A`/`RUN_B` 都是需要替换的标识），核对并归档：

```powershell
& $Python tools/trial_tools.py verify --run RUN_A --scenario baseline
& $Python tools/trial_tools.py archive --run RUN_A --label fixture-a --dest trial/archives
& $Repro run --name my-repeat-fixture-run --capture-output -- $Python @Replay
& $Python tools/trial_tools.py verify --run RUN_B --scenario baseline
& $Repro diff RUN_A RUN_B --fail-on HIGH
```

`archive` 校验复制结果后清空 `trial/outputs/current`；直接重复 run 会因非空输出目录失败。
独立副本中可用 `& $Python -m pytest -q tests/replay -m "not local and not live"`
检查应用自带的 20 项离线验收；它们不属于 ReproLLM 产品测试集。

为其他应用从零接入时，先 `init --profiles inference` 生成初稿，再声明真实输入与项目规则，
而不是复制这些应用专用规则。`prepare`（试用工具）填写 manifest 时同步 `config_files`、
bindings 与 artifacts，**填写后必须人工检查**。三条项目规则把协作轮数、语料
清单、检索 k 钉成 CRITICAL，并通过 bindings 让 lock 观察到配置里的实际值。

每次运行产出四个文件：`report.md` / `trace.jsonl` / `consumed.json` /
`result.json`。其中 `consumed.json` 是**配置消费见证**：记录代码实际读取的
配置、每个角色真正发出的 model 与参数、每阶段的调用计数、输入文件摘要。验证
配置消费要看的是"真正传给模型的值"，而不是"同一函数生成的配置副本"。

fixture 基线的 L2 审计有 2 条 CRITICAL（`model.revision_pinned`——人工构造
的模型 ID 没有 provider revision，如实保留，不用假 revision 消除）。完整
默认 finding 集合不做抑制。

## 正常、失败与漂移实例

正常：同输入重复运行，`report.md` 逐字节相同（fixture 固定时钟），
`reprollm diff RUN_A RUN_REPEAT --fail-on HIGH` 仅剩可解释的元数据差异。

失败（全部真实发生过，保留归档）：

- 病例消息耗尽而模型未给出结束标记 → `informer_exhausted`，child 非零退出，
  失败 run 被保留；
- 预算上限内**先检查后请求**：`model_call_limit=3` 时第 4 次请求不会发出，
  trace 记录 `budget_exceeded`；
- 第三方搜索服务失效（百科镜像 DNS 不可达）→ `search_failed`，已完成的
  前序阶段保留，不生成成功 result。

漂移（改一个输入，看它真实流到下游）：

| 变体 | 改什么 | diff 观察到的 HIGH |
|---|---|---|
| rounds-3 | 协作轮数 5→3 | `custom.workflow.chat_turn_limit` |
| prompt-v2 | Actor 模板加标记 | `prompts.actor.sha256` |
| image-v2 | 同路径换 PNG 字节 | `files.<图片>.sha256` |
| retrieval-reordered | 检索结果换序 | 已声明检索夹具 hash |
| search-v2 | 搜索返回换一项 | 已声明外部夹具 hash |

变更的真实消费证据用独立的录制客户端核对：轮数变更是 Instructor 真实调用
次数的变化（4 任务 ×5/×3），模板变更是 Actor 请求摘要的变化，图片变更是
消费摘要的变化，检索换序是下游上下文顺序的变化。

## 真实组件与在线模式

local/live 需要真实资产：分类 checkpoint（torchvision ResNet18 + 6 类输出头
的 state_dict，CPU 严格加载与一次前向通过后才可用）、GTE 本地目录、按
200/20 与 400/20 分块重建的 Chroma 索引（构建脚本带确定性 CLI 与构建清单）。
资产来源、交付者与下载记录（floating 下载的 revision 边界）在试用文档与
`asset-sources.json` 中单独保存。

`prepare --mode local/live` 会核验资产存在性，缺什么就明确 BLOCKED，不用
合成权重顶替。live 的凭据经环境变量注入，不写入配置、manifest 或命令行。

真实模型与脚本响应的差别会立刻显现：问诊轮数需求、任务分割格式漂移、提前
给出完成标记、第三方服务的可用性——这些边界在试用中全部真实发生并被记录，
教程作者的处置（派生收束对话、显式搜索降级、有界重试）与理由见试用文档，
照搬前请先理解自己的应用是否相同。

## 已知边界

- **`.pth` 目录权重**：`lock` 现已把目录内的 `.pth`（大小写不敏感）计入
  权重清单——目录字节变化会改变 `weights.sha256`，固定 config 时
  `config_sha256` 保持独立稳定，流式哈希、不做 checkpoint 反序列化。该
  支持由 [#15](https://github.com/EnumaElish123/ReproLLM/issues/15) 提出并
  在 [b4d6c71](https://github.com/EnumaElish123/ReproLLM/commit/b4d6c713fe9cf16c1d97364fa07dda5f4ef24a60)
  中实现，尚未正式发行。贡献者报告在 fixed main `d73f45f` 重建 wheel 后复测探针，
  目录由空集合变为计入 4,216 字节；固定 config 独立稳定、显式文件行为不变。
  公开报告没有附 fixed wheel hash 或私有原始探针回执，不将其写成全应用修复后重跑。
- fixture 的 `trace.jsonl` 时间来自注入时钟（保证字节可复现）；live 的
  trace 为真实时间。`result.json` 的耗时字段单独存放，不参与字节复现声明。
- 应用原始依赖与 ReproLLM 依赖建议分环境安装；混装时旧版本 pins 可能与
  recorder 冲突（试用中有真实案例，见试用文档"recorder/child 环境分离"）。

## 验证声明

贡献者的历史 fixture/local/live 结果来自上述固定报告，最初 recorder 为
`dfb72eda57abb47cc0fc972982e770c6199c5bd2`，与本页固定安装的修复后源码不同。
维护者只在一次性副本复核离线 fixture、重复与轮数漂移；具体环境、命令状态和
失败准备记录见 [owner 会话报告](../dogfooding/2026-11-07-owner-followup/README.md)。
两者均不能代替私有真实资产的独立重现、长期部署或医疗效果验证。
