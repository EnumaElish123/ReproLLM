# Agent Skill 扩展开发方案 v2

日期：2026-10-30。修订起点：`da0e8345f5742824fb12e2a8f602e38e507d3325`。
维护者要求：加入自动安装、能力介绍和按用户需求调用完整功能，明确分批任务与验收。
**执行更新：SK2-A、SK2-B 及其跨平台测试修正已验收；SK2-C 在 `981d263` 本地验收通过，待交付提交 CI。**
原 SK2-A Windows 失败保留；修正后的 `429b3ed` 五项 CI 已全部通过
（[运行记录](https://github.com/EnumaElish123/ReproLLM/actions/runs/41035875585)）。
见 [SK2-A 报告](../../dogfooding/2026-10-30-skill-sk2a/README.md)和
[前置修复报告](../../dogfooding/2026-10-30-skill-privacy-prerequisite/README.md)。
[SK2-B 报告](../../dogfooding/2026-10-30-skill-sk2b/README.md)记录 `e07963d` 的 24 项完整质量门、
5,911 测试、新鲜原生五项目门、86 项已安装检查 / 250 次调用及独立隐私复核全部通过。
原报告 `916c883` 正式 CI 四平台通过、Windows 测试构造失败；
[修正 `af62013`](../../dogfooding/2026-10-30-skill-sk2b/windows-ci-correction.md)保留完整 payload/断言，
新完整 24 项本地质量门通过；修正交付 `8f2130c` 的[五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/41073192655)及 Ubuntu 3.12 十二步骤已通过。
[SK2-C 报告](../../dogfooding/2026-10-31-skill-sk2c/README.md)记录 24 质量检查、6,189 测试、fresh 五项目、80 完整受控案例、56 无插桩入口及初始化专项通过。
SK14–SK15 为 LOCAL_ACCEPTED_CI_PENDING；SK16–SK19 在独立工作树实施和验证，尚未完成资源/最终会话门，SK20–SK21 仍待交付。
原方案修订轮仅交付文稿。

本版替代 [v1](v1.md) 的“不自动安装”“只预览不运行”和“不支持联网/规则写入”等限制。
v1 的 SK01–SK05 未实施，现为 SUPERSEDED，不能计为完成；使用新编号避免混淆。
依据：[冻结决策](../00_architecture_and_decisions.md)、[规范](../01_specification.md)、
[易用性实现](../usability-2026-10-29/README.md)、[扩展评估](../../research/2026-10-30-agent-interfaces-assessment.md)。
本文件与[验收矩阵](acceptance.md)共同定义开发范围，不代替规范，也不表示功能已实现。

维护者于本轮执行中明确“暂时无需在意claude code的适配”。本轮 SK20 先完成 Codex 真实宿主验收，
Claude Code 适配及其登录前置记为 `DEFERRED_BY_MAINTAINER`，不再阻塞其余开发。
原双宿主目标保留为后续事项，不能将单宿主结果计作双宿主 PASS；其他工程、资源和隐私验收不变。

## 1. 用户目标

用户安装 Skill 后，用自然语言提出需求。Agent 在首次需要工具时检查并按需安装 ReproLLM，
介绍能力、选择功能、连续完成已经授权的操作，再解释结果和下一步。
用户无需自行拼 ReproLLM 命令、找 run ID 或预先建立工具专用环境。

- “这个工具能做什么？”：直接介绍和举例，不为回答这个问题安装软件或扫描项目。
- “检查这个项目能否复现”：如缺工具，自动准备独立环境，然后审计并说明证据缺口。
- “登记这条命令，运行并生成报告”：补齐必要选择，初始化、预览、实际运行、检查记录和导出。
- “比较这两次实验”：选择实际记录，解释漂移及其来源，不推断未经验证的因果关系。
- “固定远端版本”或“发现项目规则”：执行相应联网流程，候选发现与规则接受分开。

“完整功能”指覆盖当前受支持 CLI 的命令族及有效选项，不等于任意修改源码、重建训练环境
或保证论文结果复现。`discover --paper` 等当前不支持的行为继续明确拒绝。
宿主必须能读取 Skill、访问项目和执行程序；安装/在线操作还需要网络及对应权限。
一般在首次调用时准备工具，不承诺复制 Skill 文件本身就触发安装钩子。

## 2. 全功能清单

| 需求 | 产品命令及覆盖范围 | 主要边界 | 任务 |
|---|---|---|---|
| 了解能力 | 静态介绍、版本、各命令帮助 | 介绍不安装、不扫描、不联网 | SK12 |
| 诊断环境 | doctor JSON、本地和显式网络检查 | 工具环境不等于实验环境 | SK13、SK16 |
| 选择实验类型 | profiles list/show、init list-tasks | 多候选不能擅自合并为一个实验 | SK13 |
| 建立声明 | init 非交互/交互等效填写、command/task/profiles、明确请求的 force | 沿用写前校验和产物所有权 | SK14 |
| 审计 | audit 的 level/profiles/fail-on/输出模式和文件 | 规则、完整证据、SKIP、诊断不变 | SK13 |
| 固定身份 | lock offline/check、在线/verify-api/hash-large-files | 未解析不冒充 resolved，支持长时 hash | SK15–16 |
| 执行实验 | run 保存命令/显式 argv、cwd/name/capture/env/snapshot/dry-run | 按实际环境启动用户命令，保留 child exit | SK18–19 |
| 读取记录 | runs list/show 及过滤 | 历史记录重新校验、展示脱敏 | SK13、SK19 |
| 比较记录 | diff 明确 A/B、最近成功/name、阈值/显示过滤 | 显示实际来源，支持明确授权的外部输入 | SK13 |
| 输出报告/格式 | export 指定 run、四模板/output；schema export | 目标/覆盖意图明确，历史快照语义不变 | SK14 |
| 发现参数 | discover opt-in、dry-run/show-content、max-chars、正式请求 | 外发同意、凭据、预算和重试总量 | SK17 |
| 管理规则 | rules list/show/candidates、add/accept/ignore/remove/restore 及其有效选项 | 接受具体候选；归档不可变，重复/冲突不掩盖 | SK15、SK17 |

从实施候选的规范和 `--help` 建立逐命令/逐选项覆盖清单。不能只覆盖命令名而遗漏显式 argv、
绑定参数、历史导出或规则恢复。每个选项有类型校验及测试；未知选项拒绝，无任意 shell 透传入口。
原 CLI 的文本、JSON、GitHub 格式继续支持，Agent 展示另做隐私和长度处理。

## 3. 架构与交付布局

用户 → Agent/Skill → 安装引导或类型化适配器 → 现有 CLI/共用业务函数 → 既有产物。
Agent 解释在规则引擎之外；不在 audit 中调用模型，不替代 discover 的生产客户端。
优先复用 CLI；为交互输入、运行状态和输出隔离提取共用服务函数时保持原语义，
不直接把 Typer 终端全局状态当并发接口，不复制规则、解析器或 next-steps 排序。

目标布局（本轮不创建实现占位）：

```text
skills/reprollm/
  SKILL.md
  references/capabilities.md
  references/workflows.md
  scripts/bootstrap.py
  scripts/reprollm_skill.py
  assets/install-catalog.json
docs/agent-skill.md
tests/unit/skills/
tests/fixtures/skills/
```

详细安装/运行指引按需拆到 references；宿主专用元数据仅在实际接入需要时增加。
Skill 可从固定仓库提交安装；不硬编码本机路径、凭据位置、GPU 环境或临时素材。
依据 [Agent Skills 规范](https://agentskills.io/specification)及
[Python 虚拟环境安装指南](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)。
源码提交不等于发布 PyPI、技能市场包或托管服务。

## 4. 自动安装与能力介绍

### 4.1 安装生命周期

1. 首次具体使用检查可信 Python 和已有工具，复用能力兼容的安装。仅问介绍不安装。
   用户已授权安装/使用工具时，不重复询问同一动作；仍遵守宿主实际执行权限。
2. 缺失或不兼容时，在用户作用域的 Skill 专属目录建立独立环境。bootstrap 不能依赖
   尚未安装的 ReproLLM；不修改系统 Python、项目/训练 venv、全局 PATH、shell 文件，不使用 sudo。
3. catalog 固定可信来源、精确版本/完整源码 commit、wheel hash 和平台依赖/构建清单。
   优先已验证 wheel；不用 latest/main，不从目标仓库执行同名工具或导入同名模块。
4. 公开包可能缺少 main 功能。没有兼容发行 wheel 时，可从 catalog 指定的官方仓库完整 commit
   获取并验证源码，在隔离构建环境构建 wheel、记录 hash 后安装。此通道必须独立实测，
   不以相同版本字符串替代来源证明，不暗中降级。现有 wheel 验证入口见[分发验证](../../distribution.md)。
5. 离线使用已校验缓存/wheelhouse；并发安装有锁和临时目录，成功后原子切换。
   安装/升级失败保留原可用环境，重复调用不重复安装，运行中的 worker 继续使用原环境。
6. 安装后验证来源、入口/import 位置、选项、schema 和小型离线功能探针；仅 version/help 成功不算 READY。
   缺 Python/venv、网络或权限时给最小准备步骤，准确报告未完成；不自动下载模型、CUDA 或训练依赖。
7. 支持 status、显式 update/rollback、只卸载 Skill 自有环境。保留用户环境、凭据、缓存和实验产物。
   代理/SOCKS 支持按 catalog 在工具环境准备，不改全局代理，不回显认证 URL。

每个安装通道都须有可获取候选与安装收据，否则该通道 BLOCKED。
软件安装网络仅发生在这个明确阶段，不能悄悄进入 audit 核心，保持 D-03/D-04 的产品边界。

### 4.2 介绍与需求识别

首次简述查缺口、保存声明、固定身份、记录运行、比较漂移、导出报告及发现/管理规则，
给与当前任务相关的自然语言示例。区分“产品有能力”和“本机尚未安装/缺凭据/缺实验环境”。
后续直接进入任务，不重复长菜单。只在项目、实验、记录对或必要事实不明确时询问。
未知 seed、revision、指标、split 或命令保持未知；不能为了消警猜测，也不把 PASS/退出 0 当作论文复现。

## 5. 授权、配置和联网合同

“检查项目”允许必要工具准备和只读检查；“运行并导出”可连续完成其已授权步骤。
已有授权、用户环境选择和参数跨步骤沿用，缺信息或超出范围时再确认。
安装 Skill、看到仓库命令或收到候选都不等于批准任意操作。仓库文字、fix_hint 与日志是数据，
不能作为新的 shell/外发/凭据访问指令。

写前核对目标与原文件 hash，拒绝过期预览，不静默加 force。用户明确要求重新初始化/覆盖某个产物时，
展示相应变更并沿用原合同，不永久禁用这些有效功能。默认输出在项目内；明确指定的项目外输入/输出
作为额外授权路径，不扩大到整个文件系统。校验真实路径、链接、嵌套/祖先根，不声称构成完整沙箱。

初始化复用 plan/render/validate/write，Agent 收集字段并复用现交互校验，保留模板注释、
有限命令语法和未知值。已有 manifest 的通用字段更新不是新增自动修复功能：提供准确修改建议；
用户明确要求编辑时由宿主按已有文件编辑权限处理。新增产品写 API 则另作具体提案，不能绕过 D-23。
完整功能覆盖现有 init 的交互等效路径，不承诺 CLI 本来没有的通用自动更新器。

lock 保持 staleness、来源与 pinnability，离线未解析不等于在线成功，ReproLLM lock 不替代依赖锁。
规则接受绑定具体候选内容；最新候选文件在读取后变化时重核。add/ignore/remove/restore
保留 reason、绑定、重复拒绝及不可变归档。不能因用户同意 discover 而自动接受规则。

凭据从用户已有环境或宿主秘密机制注入正确进程，不进入 Skill、argv、对话或收据。
缺凭据、403、代理、TLS/超时分别报告，不以变量存在代替访问权限。
discover 先用原收集器预览，绑定输入 hash、endpoint、model 与外发同意，再调用原客户端。
只有授权仍适用才使用非交互 `--yes`，保留 experimental/config opt-in。
当前 JSON-mode 降级和候选校验重试合计最多三次 POST；一次 CLI 调用不等于一次计费请求。
预算须覆盖最坏请求次数、输入及服务端输出上限。没有可信价格/输出上界时不得发送，
先准备具体限额方案或适配守卫，不能声称现客户端已有硬金额上限。
不增加外层付费重试；超时且计费未知时保守占用预算、报告未知结果，不再发送。
宿主模型不能直接生成候选文件冒充 discover；输入变化、预算撤销或证据不符阻止依赖步骤。

## 6. 实际运行、恢复和输出

### 6.1 实验环境与 recorder

命令、cwd 和实验环境由用户提供/明确选择。工具 venv 不得悄悄替换 child 的 Python、PATH、CUDA、
代理或凭据；记录工具环境与实验环境的区别。没有可用实验环境时如实报告，安装工具不代表模型已就绪。
保留 shell=False 和保存命令语法；复杂流程使用用户明确指定的脚本或 shell argv，不擅加 shell=True。
dry-run 仍零子实验、网络和产物；预览不是消耗证明，实际运行继续采集启动前输入。

执行复用 recorder、run v2、bindings、输入前后变化、环境证据与 child exit 合同。
不添加人为 GPU 配额；使用用户提供且实际可用的资源，不干扰其他任务。
明确“运行并导出”后可连续执行；未授权费用、不明确命令或缺实验环境则先处理该缺口。

### 6.2 本地运行控制

提供 start/status/logs/cancel/result，绑定 operation_id、run_id、请求指纹和所有权。
仅管理本次用户命令的 worker，不实现集群调度器或远程服务。
启动前记录操作身份，同一操作重投不能产生第二个实验；有意“再跑一次”必须是新操作。
启动与状态落盘之间无法判定的中断记 UNKNOWN，核对记录/进程后处理，不能宣称任意崩溃下严格 exactly-once。

取消 v1 对所有操作统一 120 秒的限制：短查询可限时；长实验返回句柄，Agent 周期查询与报告进度。
支持持久 worker 的宿主可断开后恢复查询；不支持时明确限制，不把失联当完成或自动重启。
取消只针对本操作核对过身份的进程/组；先正常结束，必要强制结束限定同一操作，并核对实际终态。
PID 或进程名不能单独构成终止权限。child exit 7、信号中断、wrapper 错误、捕获告警、未知状态分别表达。
未实现平台回收行为前不能宣称该平台支持后台运行；失败默认报告原结果，不自动再跑训练/计费脚本。

### 6.3 隐私与完整结果

原 run 终端输出未脱敏，不能直接给 Agent。worker 原始流隔离且默认不落盘；要看日志时使用
既有脱敏 capture 产物，展示时再做隐私处理。capture 关闭则说明无日志。测试长行、分块秘密、
控制字符和异常；不能把半行先输出后补脱敏，也不能因展示上限阻塞 child 的流排空。

助手返回带 schema_version 的信封，分开表达调用状态、门控/child 结果、完整数据范围和诊断。
模型单次结果默认最多 256 KiB，完整结果可用受限筛选/分页继续获取；分页绑定快照/hash，
变化使游标失效。summary 标明全量/当前页，SKIP 与诊断不可静默消失，不以截断结果声明全部通过。
不再沿用 v1 超过固定 8 MiB 就把完整流程交还手工的策略；短查询仍可有明确 incomplete 边界。

安装/操作/缓存状态只写 Skill 自有用户目录，不增加任意项目文件；均有 schema_version、
原子写入、权限、保留和清理策略。不保存秘密、原始 argv、绝对机器路径或身份。
恢复时重新提供项目根并核对哈希身份；辅助状态不替代原十种产品 schema 或 run.json。
具体状态字段在对应任务编码前设计并测试。云端 Agent 收到的内容可能离开实验机，
本地执行不等于全流程离线，用户仍可使用纯 CLI。

## 7. 分批任务与实施顺序

三个阶段各两会话；每任务一个 Conventional Commit，每会话共享最终质量证据。

| 会话 | 任务 | 交付与主要验收 | 前置 | 状态 |
|---|---|---|---|---|
| SK2-A | SK10 | 安装 catalog、候选身份/兼容矩阵；固定来源/hash，真实 wheel/源码通道、拒绝模块遮蔽 | 本包 | ACCEPTED |
| SK2-A | SK11 | 自动安装/复用/更新/回滚/卸载；空环境、并发、离线、失败保全、不污染研究环境 | SK10 | ACCEPTED |
| SK2-B | SK12 | Skill 入口、介绍、需求路由及适配基础；介绍零副作用，已授权任务连续执行 | SK11 | ACCEPTED |
| SK2-B | SK13 | audit/doctor/profiles/tasks/runs/diff/preview；完整结果、诊断、分页、退出码一致 | SK12 | ACCEPTED |
| SK2-C | SK14 | init 交互等效填写、命令登记、export/schema；原校验、历史快照、有效覆盖意图及保全 | SK13 | LOCAL_ACCEPTED_CI_PENDING |
| SK2-C | SK15 | 离线 lock/check/大文件处理、rules 全生命周期；staleness、具体接受、归档和冲突正确 | SK14 | LOCAL_ACCEPTED_CI_PENDING |
| SK2-D | SK16 | 在线 lock/verify-api/doctor、凭据/代理；真实元数据解析与权限失败区分 | SK15 | WORKTREE_VALIDATION_IN_PROGRESS |
| SK2-D | SK17 | discover 预览→外发/预算→正式请求→审阅→接受→audit；重试总量/输入变化/失败不重发 | SK16 | WORKTREE_VALIDATION_IN_PROGRESS |
| SK2-E | SK18 | 保存/显式命令实际运行、环境和日志隔离；准确 argv、run v2、child exit、输入证据 | SK17 | WORKTREE_VALIDATION_IN_PROGRESS |
| SK2-E | SK19 | 长任务查询/取消/恢复/防重复；短等待不杀长实验，断连/未知终态不重跑、不误杀 | SK18 | WORKTREE_VALIDATION_IN_PROGRESS |
| SK2-F | SK20 | 空工具环境到完整流程的集成验收、宿主/平台矩阵；全部命令选项有覆盖证据；本轮按维护者更新先验 Codex | SK19 | WORKTREE_VALIDATION_IN_PROGRESS |
| SK2-F | SK21 | 安装使用文档、介绍实例、卸载恢复与首次使用观察；工程/外部反馈分别记载 | SK20 | NOT_STARTED |

每项先把 [A01–A24](acceptance.md)落实为独立预期及行为测试，再实现；不能只匹配 SKILL.md 句子。
catalog 随候选更新，未验收能力标 unavailable，SK2-A 完成不代表完整功能已完成。
SK14 交互解耦和 SK19 状态/进程协议先给具体设计及失败路径，再按授权实施。
若需更改冻结决策、engine、redaction.py 或正式 schema，走原有具体补丁审阅流程；
不能把本方案当成对未来未知补丁的提前接受，也不因此停止不依赖该修改的工作。

## 8. 交付门与完成定义

详细断言、阶段出口和资源矩阵见[验收矩阵](acceptance.md)。安装器、适配器、运行控制均是用户功能，
即使位于 skills/scripts 也执行产品完整质量门及五项目 Gate A；每会话只在最终输入跑一次完整门。
自动测试无真实网络；安装、在线解析、GPU 和付费 discover 另做有资源条件的集成验证。
本轮仅文稿，不执行这些未来门，不消费 GPU/API 预算、不发布产物。

推送前本地适用门通过，推送后检查同一提交五项 CI。工程、资源、宿主、公开分发和外部反馈分别列状态。
mock/标准库 child 不替代真实 API/GPU；单宿主不等于跨宿主。缺资源记 BLOCKED，可交付已验收部分，
但矩阵未齐不能标完整功能完成。三类基础流程不要求用户手输 ReproLLM 命令，
实际运行仍需用户给出实验命令/环境及不可推断的真实信息。

## 9. 禁区、工期与下一步

保留确定性规则、证据优先级、隐私、opt-in 和版本政策。不修改科学 gold，不任意自动修源码/配置，
不实现 MCP，不安装重型实验依赖，不侵占他人任务，不发布 release/技能市场、不自动联系外部试用者。
“完整功能”不取消必要授权，但已有授权不能每步重复索取。

本版替代 v1 的 3–5 人日估算：熟悉代码的一名工程师粗估 3–5 人周，
SK2-A/B 约 4–6 人日；其余按进程/宿主边界复杂度重估，资源等待、招募和发布另计，不是排期承诺。
当前核对 SK2-C 报告提交的 CI，并完成 **SK2-D：SK16 → SK17** 的适用联网/发现验收；后续按依赖顺序执行。
本轮记录见 [v2 方案修订报告](../../dogfooding/2026-10-30-skill-plan-v2.md)。
