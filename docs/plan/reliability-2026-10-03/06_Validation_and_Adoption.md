# 专项方案：可重放证据、独立试用与申请材料

版本：v1.2 · 初始日期：2026-10-03 · 状态：按活动分层交付（2026-10-26 更新）

共同合同：[00_Execution_Guide.md](00_Execution_Guide.md)。审查 SHA：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

## 1. 目标与推进方式

把项目的可靠性改进变成他人能够检查的输入、命令和结果，并据真实使用与维护事实准备申请材料。

| 活动 | 何时开始 | 交付 |
|---|---|---|
| A01-A：输入与资源准备 | R00 同期 | 可获取输入、哈希清单、formal / supplementary 归类、阻塞表 |
| A01-B：修复后回放 | D01 / D02 可用后 | 干净环境回放、run / diff / export、安全的证据包 |
| A02：独立研究者试用 | recipe 达到可分享状态后 | 试用任务、反馈模板、问题闭环；真实反馈另计 |
| A03：采用与申请材料 | 随已有事实滚动整理 | 事实表、申请草稿、证据索引、尚缺内容 |

不把外部用户回应、资源供应或申请结果算成可由编码 Agent 保证完成的开发 Sprint 任务。材料完成、实际执行、独立采用分别登记。

2026-10-19 接续状态：

- [A01 本地层](../../dogfooding/2026-10-18-a01-local/README.md)保留 10-18 环境的 12/50 恢复及无资源回放结果；后续 [资源实跑](../../dogfooding/2026-10-19-resource-completion/README.md)在已提供的 Linux 节点恢复 **45/50** 个精确 slot，5 个原始 metadata manifest 仍缺失。此节点的恢复不代表本机已取得文件。
- **VAL-R01 PASS，绑定 `750270b`**：Linux H2、五项目原生 GPU A/B、完整捕获/消费/diff 与 20 个默认 export 状态。**VAL-R02 PASS，绑定 `75d1b0`**：[R02-R 修复后的新 formal judge A/B](../../dogfooding/2026-10-19-judge-snapshot-fix/README.md)通过真实 provider、完整捕获与语义验收；旧 `750270b` A FAIL / B NOT_RUN 继续保留。
- [Windows 测试 ID 修正](../../dogfooding/2026-10-19-judge-snapshot-fix/windows-ci/README.md)的 `409a1a7` 仅改测试元数据，产品和正式 wheel 不变。前一进度核对确认 [`af8adea` 的五项 CI 成功](https://github.com/EnumaElish123/ReproLLM/actions/runs/39209260394)；本次及后续提交需另核对 CI，不覆盖旧 receipt。
- **VAL-R03 BLOCKED**：HF 认证成功但限定小文件仍 403，原始 metadata 输入仍有缺口。`75d1b0` 的 CPU/judge 跟进没有重跑 GPU/H2；完整同候选发布矩阵未完成，未授权发布。详见[资源账本](../../dogfooding/pending-resource-validation.md)。
- [A02 材料](../../trials/a02-local/README.md)可审阅，独立试用 PENDING；[A03 本地事实与叙述](../../adoption/a03-2026-10-18.md)已整理，当前官方表单核验尚未执行。R06-B 方案 A 已于 2026-10-20 [具体批准](proposals/R06-B/decision.json)，后续 P-B 的独立验证见[接续报告](../../dogfooding/2026-10-20-r06b/README.md)。

2026-10-20 接续：[先行补验](../../dogfooding/2026-10-20-validation-followup/README.md)在 `948d164` 完成质量、Gate A、H2、五原生 GPU pairs 和20 exports。新输入 discover 案例亦完成一次 provider 和候选接受；其三个变化 hash 经维护者单独接受，历史 gold 不变。VAL-R02 继续绑定 `75d1b0`，没有新 judge 请求；原始五 metadata 与 gated HF 403 仍阻塞。后续 R06-B 的静态 policy 验证单独绑定，不声称新 GPU/付费/HF 成功。

2026-10-26 接续：[当前候选补验](../../dogfooding/2026-10-26-validation-completion/README.md)
在 `6afe8f4` 完成质量、fresh 五项目基础/受影响层、匿名 supplementary H2、十个原生 child、
五配对和20 export；DP epsilon 叶按已接受 R08-B 验为 HIGH。
新批准的 3 元 judge 预算覆盖两次原输入正式请求，完整捕获/导出/七变化配对通过，direct cap 为 HIGH。
新批准的 4 元 discover 预算覆盖一次 current-input 请求及源码审阅后的规则接受；历史输入/gold 保持。
VAL-R01/R02 新通过共同绑定本候选。原始五 manifest 仍缺，当前 HF 认证 200、两小文件 403，VAL-R03 继续 BLOCKED。
本轮不推进产品任务、不发布版本，不以资源成功替代 A02 独立反馈或 A03 身份/提交授权。

2026-10-27 接续：维护者直接要求制定新正式配置替代旧文件。
[M4-META-20261027](../../dogfooding/metadata-formal-2026-10-27/README.md) 按 `val.md §8.1.1`
正式接替五份缺失 metadata manifest，五份新输入已纳入版本控制。历史恢复清单仍为
45/50，不伪造找回；当前五份正式输入为 5/5 AVAILABLE。VAL-R03 的输入阻塞解除，
受限小文件成功访问仍 BLOCKED。历史资源回放不重新绑定，不改变 GPU/付费场景。

同日后续：维护者明确无法获取 Llama-2 权限并要求更换模型。
[公共 DistilGPT2 配置](../../dogfooding/metadata-public-model-2026-10-27/README.md)
按 `val.md §8.1.2` 接替 Project C，其他四份 manifest 及五项目 pin 保持。
旧 gated 成功门撤为 SUPERSEDED_NOT_PASSED，当前 VAL-R03 改验公开小文件成功解析、
哈希/provenance 和持久化；真实回放结果见新包的 checks.json，不要求继续申请 Llama-2。
新案例在 `00c2392` 产品字节通过五项目15阶段 metadata 回放、51次产品命令及
完整比较，当前 VAL-R03 为 PASS；原 gated 成功门保持 SUPERSEDED_NOT_PASSED。

下文完成条件是任务合同；已有结果保留候选、机器和日期，不以材料准备替代真实反馈或正式验证。

## 2. A01-A：先恢复输入，再安排资源回放

### 仓库入口

`val.md`、`docs/dogfooding/pending-resource-validation.md`、`docs/dogfooding/m5-m6-runtime-gold.md`、`docs/dogfooding/m4-m6-linux-validation.md`、`docs/dogfooding/deepseek-api-validation.md`。

### 实施步骤

1. 从 `val.md` 逐行提取适用场景、固定仓库 SHA、输入文件、已知 hash、命令、独立 gold、资源约束和历史状态。
2. 为每个输入记录实际可获取位置、许可 / 分享边界、大小和 SHA-256；先验证字节，再运行产品。仅存在 hash 不能恢复原文件。
3. 将缺失的原始 manifest、entry、transport、config、fixed answer 单独列出；不从报告猜写同名文件后宣称原输入已恢复。
4. 可公开的轻量输入优先进入现有 examples / dogfooding 组织；权重、checkpoint、凭据、缓存和大文件保持外部存放，以引用和校验和定位。
5. 需要新替代案例时，使用新 case ID、全新输入哈希和独立预期，标 supplementary。只有维护者明确更改 formal baseline 后才改变其地位。
6. 不假定以前的凭据、路径、预算或 GPU 仍可用；核对本轮实际提供的资源和仍有效授权。已授权且仍在相同边界内的操作不用重复请求。

### 当前资源状态与后续恢复动作

| 项目 | 已有验收 / 当前缺口 | 后续验收边界 |
|---|---|---|
| VAL-R01 | `6afe8f4` 新通过匿名 supplementary H2、五项目真实 A/B/完整捕获/消费/25审计及20 export；原始 §8.1 metadata 身份仍独立 | 为后续候选或发布执行适用同候选矩阵时，重新核对输入身份与实际可用资源；旧结果不自动改绑 |
| VAL-R02 | `6afe8f4` 新通过原始 formal 输入的两次 provider、完整捕获/导出与 HIGH direct-cap 配对 | 后续付费回放仍核对输入、当轮 provider/凭据和有效预算；保留旧失败，不复用历史成功冒充新执行 |
| VAL-R03 | 公开 DistilGPT2 新案例在 `00c2392` PASS（§8.1.2）；旧 Llama-2 授权成功门为 SUPERSEDED_NOT_PASSED | 后续适用候选按新正式输入重放匿名小文件解析、固定 revision/hash/provenance、两次锁一致及安全持久化；不要求 Llama-2 权限 |

Linux 节点的历史 45/50 输入清单仍有五个 §8.1 原始 manifest 缺口；它与无资源本地层、历史 H2 supplementary 输入和其他历史输入的身份分别保留。2026-10-27 新正式配置已替代后续执行对旧 manifest 的依赖；不再把找回旧文件列为当前输入前置条件。各次结果以[资源账本](../../dogfooding/pending-resource-validation.md)与对应输入清单为准。

历史 formal FastChat 输入的四个关键文件为 `reprollm.yaml`、`validation/judge.yaml`、`validation/judge_entry.py`、`validation/judge_transport.py`，精确 hash 在 `val.md §8.4`。恢复时逐个比对，不复制一份不完整报告当输入包。

### 可维护的输入清单模板

```markdown
| Case ID | Formal / Supplementary | Upstream SHA | 输入相对路径 | SHA-256 | 可获取位置 | 状态 | 缺失项 |
|---|---|---|---|---|---|---|---|
```

不得将私有路径 / 签名 URL / 凭据写入可分享清单。下载位置可以是公开固定 revision URL，或只在本机解析的逻辑位置名称。

### 完成条件

- [ ] 每个 formal 输入标记 AVAILABLE / MISSING / ACCESS_BLOCKED / HASH_MISMATCH。
- [ ] 可恢复项已经恢复并校验；其他项有具体缺失文件和恢复动作。
- [ ] 新案例与历史 formal 输入没有身份混淆。
- [ ] D01 可以拿到可用输入或清楚的替代案例边界；不必等全部资源到齐才修代码。

建议提交：`docs(validation): inventory replay inputs and resource blockers (A01-A)`。

## 3. 正式 Gate B 的执行清单

执行时重新完整读取 `val.md` 的适用章节，以下仅指明必须覆盖的关系，不能代替其具体哈希和资源合同。

| 类别 | 需要覆盖 | 核心断言 |
|---|---|---|
| M4 metadata | 五项目 offline / 两次 online / freshness；提供凭据时相应认证分支 | 独立 revision / 文件 hash、允许时间字段归一化后的确定性、拒绝访问的安全 provenance |
| M5 runtime | lm-eval、FastChat answer、LlamaFactory、HarmBench、formal DistilGPT2 DP；另有 formal DeepSeek judge | 真实有限执行、输入身份、消费参数、hash、相对路径、隐私 |
| M6 paired diff | 每个已激活 runtime 的 A / B | 目标语义路径和等级正确，解释全部其他差异 |
| M7 export / discover | 可用 State 全部 export；五项目离线 discover 收集；已提供资源的 opt-in 请求 | 实际 payload 文件与脱敏、返回使用、状态和导出证据一致 |
| 每次 release | 所有适用 Gate A / B 的本轮矩阵 | 候选 SHA 一致，无未解释差异或被隐藏的 BLOCKED |

资源守则来自已有 formal 合同：

- GPU 只在当前已提供环境、授权设备和限额内执行；先核对资源，不影响已有进程。`val.md` 后续维护者补充可修订旧 guard，按最新明确决定执行，不挑选最宽松片段。
- 正式 DeepSeek judge 的历史合同为总额 CNY 3、最多两次 completion attempt、禁止隐式重试、有限 payload 和 deadline。执行前重新确认官方模型 / 价格、当前预算和输入兼容性；不能把旧价格当作未来成本保证。
- gated 模型场景只取已限定的小型 metadata / config 文件，按 `val.md` 的单文件 2 MiB 边界；本任务不授权下载受限权重或绕过作者访问限制。
- discover / 付费调用在发送前核对确切 payload、文件清单和隐私；网络 mock 能证明本地行为，不能证明真实服务成功。

历史成功继续保留，但本轮没有执行的行保持 NOT_RUN / BLOCKED。资源不足时完成所有其他可执行检查，并将缺口交给 D03 的 release readiness 报告。

## 4. A01-B：构建可重放的证据包

### 输入

D01 最终 recipe、D02 的候选 wheel / hash、A01-A 的已验证输入、R02-R 的产物脱敏、R03 的有效值合同、R04-A 的环境来源、R04-B 的输入时点/变化合同、R08 的实际生效策略。

### 实施步骤

1. 在干净临时项目 / 外部一次性 clone 和新环境中安装已验证 wheel；实际导入来自 wheel，不依赖维护者开发 checkout。
2. 校验输入和上游 SHA，记录 case ID / ReproLLM SHA / version / wheel hash / Python 与平台的安全摘要。
3. 用确定命令完成 audit、lock、run A / B、diff、export；资源不足则停在对应层次，保留已完成部分。
4. 对输入文件直接计算独立 SHA-256，与对应采集阶段的 lock / run 记录核对；记录运行期间是否改写、删除或新建。对运行参数以实际 child parser / request / config 消费证据核对。不能只自比两个 ReproLLM 输出，也不能将 post-run 配置或未改写的启动前基线单独视为消费证明。
5. 解释完整 drift 集合；目标字段、config hash、clean commit、argv 分别标明，避免一个无关 HIGH 掩盖目标丢失。
6. 检查整个证据包中的凭据、机器身份、绝对路径和敏感内容，覆盖结构化 run 值和 JSON/YAML 快照，不只检查 lock；使用 R02-R 的合成正反例验证检测边界。对可执行参数不能静默修改后声称仍是原始精确重放；确需净化的份额单独说明。
7. 从已分享的包再做一次独立路径重放，验证相对路径和输入可获取性；这是对“可重放”主张的必要检查，不要求重复跑所有昂贵资源场景。

### 证据包内容

建议放在现有 `docs/dogfooding/` 配套目录或 `examples/` 的小型子目录。路径以下均为拟定交付名：

| 文件 | 必需内容 |
|---|---|
| `README.md` | 环境、安装、输入获取、完整命令、资源限制、验证层次、已知限制 |
| `inputs/` | 可公开且轻量的 manifest / config / prompt / entry；保留许可与来源 |
| `SHA256SUMS` | 输入和可分享输出的校验和，路径相对包根 |
| `expected.md` | 执行前确定的独立规则 / drift / consumption 预期及来源 |
| `results.md` | 实际退出码、耗时、预期与实际、PASS / FAIL / BLOCKED |
| `evidence/` | 安全的 run / lock / diff / export 与必要片段；无权重 / secret |

不要为了包完整而生成不存在的训练结果或选择性删除失败记录。模型输出变化和吞吐变化按观测记录，不预填“完全一致”。

### 完成条件

- [ ] 接收者只用包和公开 / 已授权输入即可重建已声明通过的验证层次。
- [ ] 每项成功有实际命令和证据；input hash 与 expected 来源独立。
- [ ] 源环境与 child 未验证项按 R04 合同准确表述。
- [ ] formal 与 supplementary、历史与本轮、offline 与 live 状态清晰。
- [ ] 把当前候选的实际结果交给 D03；未完成资源检查继续 BLOCKED。

建议提交：`docs(evidence): publish a reproducible validation bundle (A01-B)`。这里的 publish 指准备或提交仓库内文档；向外部平台公开分享按实际授权执行。

## 5. A02：试用材料与反馈闭环

### 先完成 Agent 能控制的工作

1. 从 D01 / D02 提炼一个新研究者能独立执行的安装与首个运行路径，说明实际版本和资源前提。
2. 准备两种任务卡：已有 LLM 实验的本地 audit / init；已有 run 的单字段变化 / diff / export。提供预期观察，不提供应被用户照抄的“好评”。
3. 制作简短反馈模板，收集失败命令、实际版本、阻塞步骤、结果是否可理解、是否发现有价值差异、下一次是否还会用。
4. 给出日志净化说明，允许用户只提交最小合成复现；不要求上传 private prompt、dataset、模型权重或密钥。
5. 准备邀请草稿与候选人筛选标准。可以建议小批量、有真实需求的独立研究者试用；没有明确消息发送授权，不主动联系任何人。

### 反馈记录字段

| 字段 | 记录要求 |
|---|---|
| Trial ID / 日期 / 版本 | 匿名或获准公开的身份标识；被测版本清楚 |
| 环境和项目类型 | 足够定位问题；不收集无关私人信息 |
| 首个阻塞点 | 用户实际到达的步骤和退出码 |
| 复现材料 | 安全的最小案例与命令，缺失项明确 |
| 工程分类 | bug / 文档 / 工作流需求 / 超出范围 |
| 处理 | 关联任务或 issue、修复版本、是否重新验证 |
| 采用证据 | 单次试用、再次使用、独立集成分别记录 |

### 三种完成状态

- **材料完成**：新用户可使用的说明、任务卡、反馈表和问题处理流程已经交付。
- **试用完成**：有真实独立使用者运行和实际反馈；没有回应就记录等待，不能假定成功。
- **采用成立**：有重复使用、独立项目集成或其他可核实持续使用证据；一次作者自测不属于这一层。

### 验收

- [ ] 材料不依赖维护者个人机器路径 / 私有资源。
- [ ] 收到的问题可以转成最小复现和有边界的后续任务。
- [ ] 未收到反馈的行为空或 PENDING；不补写虚构用户名、引用或指标。
- [ ] 真实问题至少完成“复现 → 处理 → 回访验证”的记录才称闭环；外部等待不阻塞核心修复收尾。

建议提交：`docs(trial): prepare independent-user validation materials (A02)`。

## 6. A03：采用事实表与 Codex for Open Source 申请草稿

2026-10-22 带日期补充：[官方表单匹配与申请草稿](../../adoption/a03-2026-10-22.md)
已只读核对公开字段、三个 500 字符上限和条款，[长度记录](../../adoption/a03-2026-10-22-lengths.json)
保留精确草稿与计数。准备时事实和 P-B 交付时验收分别记录；申请仍为 DRAFT / NOT_SUBMITTED /
NOT_APPROVED，个人信息、角色、组织标识与提交授权仍由申请人确认。10-18 历史事实表保持原样。

### 实施步骤

1. 建立事实表，每个数值或项目状态包含来源、采集日期、口径和限制；信息不足就写未知。
2. 区分自身 ReproLLM 仓库 / 自身 Action、测试过的上游项目、真实独立采用。跑过 FastChat / HarmBench 不等于上游使用或推荐 ReproLLM。
3. 从 A01-B 提取可审阅的可靠性证据：修复的问题、真实回归、运行数据完整性、可安装 wheel、可重放案例及仍未完成的资源验证。
4. 从 A02 提取获准引用的真实使用反馈与独立集成；星标 / 下载数字如有使用则标明时间与口径，不把它们当效果保证。
5. 描述 Codex 将用于哪些具体维护工作：回归测试、兼容性验证、文档 / recipe 同步、issue 最小复现、受约束的代码实现。人工审阅边界与已有 D-41 机制对齐。
6. API 研究推理开销与 Codex 编码维护用途分别说明，不混写为同一种资源需求。
7. 提交前核对官方项目说明、表单字段、当前字数 / 字符限制和资格条款。只有表单实际要求 500 字符时才按该限制压缩，不从历史截图推测当前要求。
8. 准备完整申请草稿和证据链接；申请提交按明确授权另行执行。

### 事实表模板

```markdown
| Claim ID | 拟使用的陈述 | 数值 / 状态 | 来源 URL / 证据相对路径 | 截至日期 | 口径与限制 | 可公开 |
|---|---|---|---|---|---|---|
```

### 草稿结构

- 项目解决的具体研究复现问题及目标用户。
- 已提供的工作流与开源许可 / 仓库身份。
- 可被第三方查看的案例、质量和真实采用证据。
- 维护负担与未来几份开发方案中的具体工作。
- Codex 的计划用途、维护者审阅和资源约束。
- 当前限制与尚缺证据，保持事实准确。

不要编造最低 star 门槛、通过概率、OpenAI 认可或用户数量。申请的叙述重点是可核实价值与维护计划，不能通过文案消除资源验证或外部采用的事实缺口。

### 完成条件

- [ ] 每个可核查事实有来源与日期，截图 / 链接与版本对应。
- [ ] 本轮修复结果、历史验证和未来计划没有混用时态。
- [ ] draft 与当前真实表单字段匹配，长度已检查。
- [ ] 维护用途具体，API / Codex 需求区分清楚。
- [ ] 草稿与证据索引已准备好；没有把“准备申请”写成“已提交 / 已获批”。

建议提交：`docs(application): prepare evidence-backed OSS application draft (A03)`。

## 7. 最终交付检查

| 成果 | Agent 能直接完成的部分 | 可能依赖外部的部分 |
|---|---|---|
| 输入包 | 清单、可取得文件、hash、独立预期、缺失定位 | 缺失的原始远程输入、私有访问权限 |
| 回放报告 | 无资源路径、已提供资源的实测、所有阻塞说明 | GPU、当前凭据、预算、服务可用性 |
| 试用 | 指南、任务卡、反馈结构、收到问题的工程处理 | 用户实际运行和回复、持续采用 |
| 申请 | 事实表、草稿、链接与长度检查 | 明确提交授权、申请方评审结果 |

所有外部缺口写明“需要什么、谁能提供、拿到之后先做什么”，不转成笼统的“待完善”。

初始审查依据（历史快照）：[val.md](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/val.md)、[待执行资源验证](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/docs/dogfooding/pending-resource-validation.md)。当前执行以仓库中的 [val.md](../../../val.md) 和[资源账本](../../dogfooding/pending-resource-validation.md)为准，按最新维护者资源指导，不恢复旧人工阈值。[Codex for OSS 官方说明](https://developers.openai.com/community/codex-for-oss)、[申请表](https://openai.com/form/codex-for-oss/)、[项目条款](https://learn.chatgpt.com/docs/codex-for-oss-terms)。官方申请信息与服务价格在实际提交 / 调用前重新核验。
