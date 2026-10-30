# ReproLLM 的 Agent Skill / MCP 扩展评估

日期：2026-10-30（Asia/Shanghai）。这是研究与产品判断记录，不是已接受的开发方案，也不表示接口已经实现。本次未验证任何宿主客户端的实际接入兼容性。协议事实取自下列官方资料；成本、用户匹配度和实施顺序属于工程判断。

## 官方接口事实

### Agent Skill

Skill 是给 Agent 使用的工作流程与领域知识包。最小形态是含 `name`、`description` 和操作指引的 `SKILL.md`，可附脚本、参考文档与模板。Agent 根据任务加载相应内容，因此可以把“先审计、解释结果、补充声明、再记录与比较”的过程封装起来。[官方概览](https://agentskills.io/home)

Skill 不自动提供 Python 环境、仓库访问能力或执行权限。规范允许声明兼容性要求；脚本支持取决于宿主，`allowed-tools` 仍是支持情况因实现而异的实验字段。应把本地 CLI、版本要求和网络需求写清楚，不能把 Markdown 指令当作安全沙箱。[格式规范](https://agentskills.io/specification)

跨客户端共享的是内容格式，安装目录、激活方式、权限处理和运行环境仍由宿主决定。官方实现指南明确区分本地、云端和沙箱 Agent：云端 Agent 不会天然看见研究者本机仓库。[客户端集成指南](https://agentskills.io/client-implementation/adding-skills-support)

### MCP

MCP 规范入口在本次查阅时重定向到正式的 **2026-07-28** 版本；本文没有将 `draft` 当作正式版本。它定义应用与工具/数据服务之间的通信协议，不能单凭“支持 MCP”推定一个客户端支持所有扩展。[正式规范](https://modelcontextprotocol.io/specification/2026-07-28)

本地 MCP 可以使用 **stdio**：客户端启动服务子进程，通过标准输入/输出交换 JSON-RPC。无需部署公网服务，但协议 stdout 不能混入普通 CLI 文本、Rich 输出或实验子进程日志；日志可走 stderr，服务应隔离实际执行过程的输出。[stdio](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)

Tools 有 `inputSchema`，可声明 `outputSchema` 并返回 `structuredContent`。协议错误与实际工具执行错误分开，后者使用 `isError`。工具注解是描述信息，不能代替输入校验、权限控制或敏感操作确认。[Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)

长训练/推理任务不能仅靠一个阻塞调用承诺可靠运行。官方 **Tasks** 扩展提供持久任务句柄、状态轮询、结果恢复和取消请求，但需要双方明确支持；取消是协作式请求，不保证底层工作立即停止。适配层仍需实现进程生命周期和资源回收。[Tasks](https://modelcontextprotocol.io/extensions/tasks/overview)

HTTP MCP 是独立服务部署问题：需处理 Origin 校验、访问认证与传输安全；官方对本机 HTTP 服务建议只绑定 localhost。HTTP 授权规范与 stdio 不同，stdio 通常从运行环境取得凭据。由此可推断：仅做本地 stdio 与做多用户远程服务，成本应分开估计。[HTTP 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)、[授权规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

### 两者可以组合

官方已发布 **Skills over MCP** 扩展：通过 MCP 发现、读取 Agent Skills 与配套文件。其存在说明 Skill 与 MCP 可以分别承担工作流程和工具连接，而非二选一。官方同时注明 SDK/宿主支持仍在推进，不能将该扩展作为所有客户端都可用的首版前提。[Skills 扩展](https://modelcontextprotocol.io/extensions/skills/overview)

## 对科研 CLI 的通用工程判断

| 形式 | 适合承担的工作 | 需要付出的额外代价 |
|---|---|---|
| CLI | SSH、终端、脚本、CI；固定命令与可追溯产物 | 用户学习命令与实验配置 |
| Skill + CLI | 自然语言引导、解释发现、组织多步本地工作流程 | 编写可靠指引、环境预检、客户端试用和防止错误推断的评测 |
| 本地 MCP + 既有引擎 | 向多个 Agent 客户端暴露类型明确、边界受控的工具 | 参数/结果包装、错误映射、输出隔离、授权范围、客户端兼容测试 |
| 远程 MCP 服务 | 研究团队平台集成、集中访问与服务管理 | 身份认证、项目/用户隔离、网络部署、任务与凭据生命周期、运维 |

以下属于判断，不是官方承诺：如果既有 CLI 已有稳定 JSON、明确退出码、非交互参数和可重用逻辑，Skill 的试用包通常最容易；本地只读 MCP 的小型验证也可较轻，但完整覆盖写操作、付费请求和 GPU 长任务将明显增加工作。不能用“包装一个命令的演示成本”代表完整产品交付成本。

面向使用本地仓库、SSH/GPU 服务器和 CI 的研究者，保留 CLI 作为可靠基础更符合现有工作环境；面向已经使用编码 Agent、主要难点是记命令和理解下一步的人，Skill 的直接收益更大；面向集成平台或需要跨宿主标准工具接口的人，MCP 的收益更大。这是按任务场景推断，尚无本项目的用户调查支持市场占比结论。

## 本仓库适配评估

源码基准：本地 `main` 的 `b7b341c469740dd44283438c43c9ef1b3b47ed7a`，开发版本 0.7.0。
本次没有拉取远端、修改产品代码或验证 MCP/Skill 原型。原有 README、站点索引及手动试用材料的未提交改动保持原状。
最新易用性方案的五项开发任务已有本地验收；外部首次使用反馈仍未观察，不能用作者回放代替真实用户研究。
依据：[计划索引](../plan/README.md)、[易用性方案](../plan/usability-2026-10-29/README.md)。

### 已有基础及可复用程度

| 源码事实 | 对扩展的意义 |
|---|---|
| `run_audit(root, ...) -> AuditReport` 与 Typer 输出分离 | MCP 可复用确定性引擎；Skill 可直接调用 JSON CLI |
| Finding 有 `rule_id/status/severity/evidence/fix_hint`；持久文档和 schema 已版本化 | 不必让 Agent 从彩色终端文本猜测结论，也不必复制规则 |
| `audit`、`diff`、`runs`、`profiles`、`rules list` 有 JSON 读取路径 | 主要检查、解释和比较场景容易接入 |
| init 可保存命令；run 无 argv 可执行保存命令；dry-run 不启动实验；diff 可选择最近成功记录 | 操作步骤与 run ID 管理已有可复用能力 |
| init 已分为 `plan_init`、`render_manifest`、`write_scaffold`；lock、diff、export 有独立业务函数 | 需要结构化接口时可以提取小范围服务层，通常无需重写核心 |
| 当前打包只有 `reprollm` CLI 入口，没有 MCP 依赖或服务入口 | 可扩展不等于已支持；需要独立交付和验证 |

源码：[audit](../../src/reprollm/cli/audit.py)、[engine](../../src/reprollm/core/engine.py)、[Finding/AuditReport](../../src/reprollm/schemas/finding.py)、[init scaffold](../../src/reprollm/core/manifest_scaffold.py)、[run](../../src/reprollm/cli/run.py)、[打包配置](../../pyproject.toml)。

### 不能靠简单包装解决的部分

1. **首次配置。** `init` 有非交互模板、profiles/task/command 参数，但没有通用的字段赋值参数或结构化问答接口。第一版 Skill 可生成模板，再依据用户提供或源码中有证据的值准备 manifest 编辑供审阅；不能猜测缺失研究参数。成熟接口宜把待填字段、类型、说明和校验结果结构化，并复用现有 writer。不能把交互终端问答直接搬进无 TTY 的 MCP 请求。
2. **下一步提示。** 当前顶部 `Next steps` 由文本 renderer 生成，JSON 没有同名字段。第一版 Skill 可以读取已有 `fix_hint`；如果要多个入口给出完全一致的行动顺序，应把既有排序/分组提取成共用逻辑。可在适配响应中附行动建议，是否更改正式 AuditReport schema 是另一项决定。
3. **运行生命周期。** 当前执行器使用同步 `child.wait()`，CLI 终端模型下的信号转发不等于持久任务服务。MCP 还要规定任务启动、状态读取、取消、断连、重试去重及进程清理；已有 `run_id` 和运行中记录是基础，但不是完成的 job API。首版检查接口可以只读已有记录，暂不启动长任务。
4. **输出与隐私。** 当前 `_tee` 原样转发终端输出，仅保存的日志经过脱敏。直接把 CLI stdout 用作 MCP stdout 会污染协议；即使收进返回字符串，也可能把原始实验输出送入模型上下文。应隔离子进程流，默认返回有界、经过既有隐私处理的结果/日志摘录，并限制源文件和完整快照的读取。Skill 也需要这层输出约束，不能只写一条“不要泄密”的指令。
5. **权限与工作目录。** 保存命令仍可执行任意用户程序；`shell=False` 不等于沙箱。适配层应限定用户授权项目，校验真实路径/输出路径，逐请求使用独立 cwd，区分只读、写产物、联网和启动实验。Skill 指令和 MCP annotations 都不构成强制安全边界。已有授权可以沿用；不应每次只读检查都重复询问。
6. **退出与错误。** audit 的退出 1 是检查完成且发现超阈值，lock check 的 1 是过期，不能统一当 MCP 调用失败；run 则透传 child exit code，必须另行解释。工具层应分别返回调用完成状态、门控结论和子进程结果，保留 SKIPPED 与扫描诊断。
7. **分发与环境。** 评估基于当前源码；不能假定用户安装的公开包具有这些新选项。需要能力/版本预检。Agent、适配器和研究程序的 Python 环境也可能不同，不能把适配器环境误报为实际训练环境。若采用 MCP SDK，建议独立适配包隔离依赖，并核对 Python 与宿主协议版本支持。

依据：[init](../../src/reprollm/cli/init.py)、[next steps](../../src/reprollm/reporters/next_steps.py)、[preflight](../../src/reprollm/run/preflight.py)、[wrapper](../../src/reprollm/run/wrapper.py)、[规范 §§1/5/16/21](../plan/01_specification.md)、[发行状态记录](../community/roadmap.md)。后者是仓库记录，本次没有重新核对公开包市场。

### 本次只读接口验证

在既有手动试用的 drift lab 中，用当前源码虚拟环境执行；stdin 为 DEVNULL，stdout/stderr 分开收集，单条设 60 秒上限。profiles 在源码根执行。下面是实际观察，非 MCP 接入验收。

| 命令 | 退出码 | 观察 |
|---|---:|---|
| `reprollm audit . --format json` | 1 | 合法 JSON 对象，21,226 字节；38 条 findings 均含 status/evidence/fix_hint；无顶层 next_steps |
| `reprollm profiles list --json` | 0 | 合法 JSON 数组，1,294 字节 |
| `reprollm runs list --json` | 0 | 合法空数组；未执行实验的试用目录符合预期 |
| `reprollm rules list --json` | 0 | 合法空数组 |
| `reprollm run --dry-run` | 0 | 943 字节文本，以 Run preflight 开头；未启动实验 |

五条命令 stderr 均为空。本次没有执行 init/lock 写入、实际 run、discover、GPU 或付费请求，也没有验证全部 CLI 的 MCP 兼容性。

## 推荐路线与成本判断

**保留 CLI 与确定性引擎作为核心；先交付 Skill，再根据接入需求提供本地 MCP。**
Skill 负责引导、取证和解释；CLI/引擎负责检查、记录与比较；MCP 负责跨客户端工具接口。Agent 不能改写规则结论，不能将未知填成“已验证”。这种本地适配符合 D-03/D-04/D-23 的原意；多用户托管服务超出现行 local-first/无 hosted component 范围，需另外立项。

以下为熟悉代码的一名工程师的粗估，包含相应测试、文档及首批宿主试用，排除 GPU 环境安装、资源等待、正式发布和未预见协议兼容问题；不是已排期承诺：

| 范围 | 粗估 | 判断 |
|---|---:|---|
| Skill 原型：审计、解释、预览、读取/比较已有记录 | 1–2 人日 | 低成本，可基本不改产品代码 |
| 可试用 Skill：环境预检、边界清楚的工作流、输出约束、失败案例与两种宿主验证 | 3–5 人日 | 当前优先；不承诺任意复杂初始化和所有长任务全自动 |
| 本地只读 MCP：audit/profiles/runs/diff/preflight，有界输出、路径检查、宿主验证 | 5–8 人日 | 可以控制在小迭代；少数短命令的演示会更快 |
| 完整本地 MCP：增加初始化写入、锁定、导出、规则变更、实验执行及发现流程 | 约 2–4 人周 | 需要长任务、授权/重试与隐私设计，不是薄包装 |
| 多用户远程 MCP | 单独估算 | 服务部署、隔离与运维会改变产品范围 |

推荐首批 Skill 工作流：

- “检查这个仓库还缺哪些复现信息”：只读审计，引用规则/字段/证据，说明 SKIPPED。
- “帮我登记已有实验命令”：准备配置，缺失研究事实再询问，展示变更，预览与执行分开。
- “解释两次结果为何不同并准备报告”：读取明确的记录对，解释已观察的漂移和证据边界；导出按用户授权执行。

成功指标应是用户能否完成这些任务、需要手敲多少命令、Agent 是否误填研究事实/误判 SKIP、是否错误重试实验，以及报告解释是否保留证据。建议先招募 3–5 名真实使用者；小样本用于发现障碍，不用于推断市场占比。

## 使用群体判断

| 群体/任务 | 推荐入口 | 理由 |
|---|---|---|
| 终端、SSH、GPU 服务器上的论文作者与复现实验者 | CLI 为基础，Skill 可选 | 能直接接入现有实验环境，不额外要求使用模型服务 |
| 已在编码 Agent 中工作、主要困难是配置和命令的研究者 | Skill + CLI | 自然语言操作和按需解释更贴近当前易用性问题 |
| CI、批处理、artifact 审核 | CLI | 固定执行路径、退出码和产物，便于离线运行与复核 |
| Agent 平台/IDE 集成维护者，多客户端工具编排 | 本地 MCP + 核心 CLI/库 | 类型明确的接口与工具发现更有价值 |
| 只使用云端聊天、无法访问实验机的使用者 | 两者均需额外连接安排 | Skill/MCP 都不会凭空提供仓库、数据和 GPU |

本仓库[采用指标](../adoption.md)明确将当前独立采用情况记为未测量。因此“Skill 优先”是基于产品定位、源码和本轮用户痛点的建议，不是已证实的用户偏好。使用云端 Agent 时，提交给模型的报告仍会离开本地；本地运行 CLI/MCP 不等于整条工作流离线。

## 本次变更与验证边界

评估完成时仅新增本评估文档；未实现 Skill/MCP，也未提交或推送。按[文稿验证例外](../plan/validation-workflow-2026-10-13.md)检查本地链接及内容一致性；完整产品质量门、五项目 Gate A/B 与真实客户端兼容验收在评估轮均 NOT_APPLICABLE，不能将上述只读观察称作这些验收通过。

后续维护者要求先制定并提交 Skill 开发方案，本评估作为[2026-10-30 方案](../plan/skill-2026-10-30/README.md)的依据一并纳入版本控制；这不改变上述评估时的验证范围。
