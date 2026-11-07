# 单病例多模态智能体应用的完整证据链

本教程把 ReproLLM 应用到一个**真实形态的研究应用**上：一个多阶段、多模态的
中医舌苔问诊智能体（图像分类 → 视觉语言模型 → 多轮信息收集 → RAG 检索 →
任务规划 → 多角色协作 → 网络搜索 → 报告生成），并记录一条可审计的证据链。

与 [第一次使用](first-experiment.md)（保存一条命令并重放）和
[并发本地模型隔离](concurrent-local-experiments.md)（工作区隔离）不同，本教程
的重点是：**当应用有图像输入、多个模型角色、外部检索/搜索状态和辅助权重文件
时，如何让每个环节的"实际消费"都留下可校验的证据**。

应用仓库：[LingshuSmartLink](https://github.com/LiangRichard13/LingshuSmartLink)，
本教程验证时的试用分支为 `codex/single-case-replay`（HEAD `8407c86`，改动提案
见 [PR #2](https://github.com/LiangRichard13/LingshuSmartLink/pull/2)），试用记录
见该分支内 `docs/reprollm-single-case-trial.md`。请以届时的 README/文档为准。

**边界先行**：教程作者以三种模式完整跑通了该应用的单病例链路。运行成功表示
记录与一致性证据成立，不表示诊断内容正确，更不构成任何医疗或模型效果证明。

## 三种模式：证据只能声称到各自的实际来源

| 模式 | 分类/embedding/RAG | LLM/搜索 | 可以声称的证据 |
|---|---|---|---|
| fixture | 注入的固定结果，不加载真实权重 | 人工构造的确定响应（标记 `synthetic`） | 编排真实执行、配置真实消费、产物与回执可复现 |
| local | 真实 ResNet18 / GTE / Chroma | 仍为注入响应 | 真实本地组件与检索行为进入回执 |
| live | 真实本地组件 | 真实 provider API 与真实搜索 | 单病例完整在线运行，记录实际模型与响应 |

fixture 不叫"历史录制"——它是脚本化的确定响应。只有 live 的输出才携带
provider 真实返回；把 fixture 的成功说成"模型效果好"是本教程明确反对的。

## 准备

```bash
git clone https://github.com/LiangRichard13/LingshuSmartLink.git
cd LingshuSmartLink
git switch codex/single-case-replay   # 或届时合入后的默认分支
```

两套 Python 环境（隔离是刻意的，recorder 与被记录的 child 不共享依赖）：

```bash
# recorder 环境：ReproLLM 自己的锁定依赖（轻量，无 torch/langchain）
uv venv --python 3.12 .venv-trial
uv pip install --python .venv-trial/Scripts/python.exe \
  "reprollm @ <固定来源的 wheel 或 PyPI 包>" "pytest==8.3.5"

# child 环境：应用原始依赖（torch/CPU 版本单独记录，见试用文档）
uv venv --python 3.12 .venv-live
uv pip install --python .venv-live/Scripts/python.exe -r backend/requirements.txt
```

Windows 下解释器在 `.venv*/Scripts/`，POSIX 在 `.venv*/bin/`。`reprollm run`
记录的是 child 的事实；**不要把 recorder 环境的包清单当作 child 环境的证明**，
应用环境用 `python tools/trial_tools.py env --output trial/environment.json`
单独采集（importlib.metadata 生成，无解释器绝对路径）。

fixture 模式只需要上面第一套环境——这是刻意设计：编排逻辑的验收不应被
torch/CUDA 等重依赖绑架。

## 合成病例与输入

试用分支已自带这些合成输入（合入后克隆即可直接使用）；只有当 `trial/`
目录为空时才需要从零生成：

```bash
python tools/trial_tools.py seed        # 仅 trial/ 为空时需要
python tools/trial_tools.py prepare --mode fixture --variant baseline
```

`seed` 生成合成病例（`trial/cases/case-001.json`，`synthetic: true`）、有效
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
核对与运行即可：

```bash
reprollm lock . --check
reprollm run --dry-run -- python backend/replay_case.py --mode fixture   --case trial/cases/case-001.json --image trial/cases/case-001.png   --config trial/configs/current.yaml --cassette trial/fixtures/external.json   --output-dir trial/outputs/current
reprollm run --name my-first-fixture-run --capture-output -- python backend/replay_case.py --mode fixture   --case trial/cases/case-001.json --image trial/cases/case-001.png   --config trial/configs/current.yaml --cassette trial/fixtures/external.json   --output-dir trial/outputs/current
```

若你要为自己的应用从零搭建同样结构（而非复用分支声明），顺序是：

```bash
reprollm init . --profiles inference      # 只生成初稿
# ... 准备 trial 输入与环境清单 ...
python tools/trial_tools.py env --output trial/environment.json
reprollm rules add --id project.chat_turn_limit --field custom.workflow.chat_turn_limit   --severity CRITICAL --reason "Bound the actor and instructor iteration budget."   --config trial/configs/current.yaml:workflow.chat_turn_limit
# 另有 corpus_manifest 与 rag_k 两条，同格式；详见试用文档
reprollm lock . --offline && reprollm lock . --check
```

`init` 只生成初稿；`prepare`（试用工具）填写 manifest 时同步 `config_files`、
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

- **`.pth` 目录权重**：`lock` 对仅含 `.pth` 文件的目录当前不计入权重清单
  （`weights` 为空集合摘要），显式文件声明则正常哈希。现状行为、四组 CLI
  对照与讨论见 [#15](https://github.com/EnumaElish123/ReproLLM/issues/15)。
  本教程不依赖目录声明规避该边界。
- fixture 的 `trace.jsonl` 时间来自注入时钟（保证字节可复现）；live 的
  trace 为真实时间。`result.json` 的耗时字段单独存放，不参与字节复现声明。
- 应用原始依赖与 ReproLLM 依赖建议分环境安装；混装时旧版本 pins 可能与
  recorder 冲突（试用中有真实案例，见试用文档"recorder/child 环境分离"）。

## 验证声明

教程作者在 `codex/single-case-replay`（HEAD `8407c86`）上按本教程顺序完整
执行并验证了 fixture、local、live 三层；命令回执、期望/实际对照、审计
finding 全集与失败归档见该分支 `docs/reprollm-single-case-trial.md` 及其
引用的私有证据目录结构。复现时以届时分支与文档为准。
