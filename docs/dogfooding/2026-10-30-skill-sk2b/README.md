# SK2-B：能力介绍与完整只读检查

日期：2026-10-30。范围：[Skill v2](../../plan/skill-2026-10-30/README.md) 的 SK12 → SK13。
SK12 提交 `08a758392882dfdc827272238e4dcbbfd5971de5`；SK13 最终候选
`e07963d47cb9e0d64a5f0404d5516bf9248b08fc`。本批为 **LOCAL_ACCEPTED_CI_PENDING**；
最终报告交付提交的五项官方 CI 在推送后另行核对。SK14 正在独立复核与修正，SK15–SK21 尚未验收。

## 用户可用行为

SK12 提供静态能力介绍、自然语言需求路由和有类型的请求/结果协议。仅询问能力不安装、扫描、联网或
访问工具目录；具体检查在用户授权范围内自动准备隔离工具，已有选择与授权跨步骤沿用。
缺失实验事实保持未知，不因仓库文字、日志或 fix hint 扩大执行/外发权限。

SK13 覆盖 audit、本地 doctor、profiles list/show、任务列表、runs list/show、diff 和运行预览。
完整结果保留 findings、profiles、hints、SKIP、suppressed、stderr 和退出结果；调用完成与门控失败分开。
默认单条信封连同换行不超过 256 KiB，集合分页及大文本片段可完整重组；游标绑定输入、项目、请求、
全部 helper 字节与安装身份，变化时拒绝旧游标。明确边界超限返回 incomplete，不把片段当全量 PASS。
项目外输入/报告仅接受具体路径授权；报告发布还核对原 hash，过期或链接重定向时保留原字节。

历史 run 的 typed 来源、命令 flag 和 secret env 上下文在展示前按现有原生隐私政策处理；
JSON、文本、diff、audit 及明确请求的报告文件均受保护。公开科学值、来源、缺省字段与显式 null
保持原义；原始 diff 比较、规则结论、severity、summary、fail-on 与历史 redaction 计数不因展示替换改变。
未修改 engine、核心 redaction、规则、正式 schema 或原生产品合同。

## 最终候选验证

| 范围 | 最终结果 | 证据 |
|---|---|---|
| 共享完整质量门 | 24 项及来源守护全部通过；5,911 测试、2 个 slow deselected，零失败/错误/跳过 | [验收](acceptance.json)、[逐命令](quality-command-index.json) |
| 覆盖率及安全 | 总体 93.407%；redaction 24/24 branches、59/59 lines；security、lint、格式、类型、十份 schema/生成文档 freshness、分发检查通过 | [验收](acceptance.json) |
| 新鲜原生五项目 Gate A | 50 命令、31 检查、10 份完整 L0/facts JSON；来源/pin/干净状态、stderr 及全部字段通过，无未解释 gold 差异 | [逐命令](native-command-index.json) |
| 最终候选安装后适配 | 86 检查、250 次调用全部通过；reader、audit/diff/cache 和五项目重新执行 | [完整摘要](installed-acceptance.json)、[reader](installed-reader.json)、[routes](installed-routes.json)、[five](installed-five.json) |
| 独立安全复核 | 56 项 direct/native、6 个已安装前门、4 个 audit 输出、2 个 helper 身份案例及零副作用 about 通过；无剩余已证实 P1/P2 | [收据索引](receipt-index.json) |

质量门墙钟 1,258.677 秒；原生 Gate A 墙钟 87.279 秒、命令累计 85.832 秒。
安装适配 250 次调用包含 80 次原生 CLI、91 次最终 helper、20 次官方完整 JSON 比较、7 次原生隐私
policy oracle、2 次旧 head 游标必要正对照和 50 次 Git 来源守护，不能把总数解释为 250 次用户操作。
适配请求中位约 18.2 秒、最大约 84 秒，包含每次安装身份/完整性/probe；大型任务列表首响应最慢。
这记录了当前成本，没有宣称即时响应。各组命令有并行，累计耗时不能相加成会话墙钟。

原生基础门与安装五项目流程均在最终质量门通过后执行。同一固定 pin 的全量规则、profile、hint、路径、
诊断、文本与产物对照使用既有独立 oracle；只豁免 audit 根部允许的 metadata，不以 summary 计数替代。
lm-eval 的 417,440 字节任务文本已完整分片重建。原始五项目不写入，变更操作仅在一次性副本执行。

## 来源、复用与保全

工具源码固定于已发布桥接提交 `2faa3096fa9056ba0a4e08a8b83ffd17f4ffb4e0`，归档 SHA-256
`9f1013ab05bcb80103a462677d601bad45bd50eea6860ebfe9176986abadc78a`。
最终 e079 的整个产品包树、依赖声明/锁、架构及规范 Git objects 与该工具一致，
见 [本轮重新核验的来源绑定](product-source-binding.json)。相同 0.7.0 字符串不替代来源身份；
旧 catalog 候选仍保留，默认候选追加必要 contextual word scan 能力。

原九条实际自动安装/复用/旧包升级证据仅按[逐条复用审阅](installation-reuse.json)复用未改变的软件准备
组件：bootstrap、catalog、入口/协议、产品包及安装前分支字节/AST 一致。
旧三条 post-install audit 输出仍属于旧候选；最终 e079 的 audit 由本轮新执行证据绑定。
未声称重跑九条安装命令、重新测量首次安装耗时或已完成 SK20 新用户全流程。
未改变的只读组件有明确 AST/readset 审阅；受影响 audit/diff/readers/cache 均新执行，
共同动作也在最终全五项目中重新运行，没有自动沿用旧候选 PASS。

[保全守护](preservation.json)确认九个 helper 与最终 Git blobs 一致，安装环境 2,132 个文件及 active
identity 不变、原九份用户未提交文件 hash 不变、五项目原 checkout 仍同 pin/clean；两组合成专题初始
输入及九份历史 raw run 原件保持。全部产品/测试输入在最终质量门前后相同。
原始 stdout/stderr、命令、退出码、耗时和输入/输出 hash 保留在逐条原始收据中；
[索引](receipt-index.json)绑定其 SHA-256，提交摘要使用路径代号，不复制机器身份和原始敏感值。
历史通用质量 runner 的 A01 task label 保留，候选 SHA 与 SK2-B invocation binding 确定本次范围。

## 保留失败与完成边界

早期 `8e93c61` 虽曾通过质量门与安装矩阵，随后发现 source.path 缺省被增补 null，以及 opaque/argv、
env、diff 与 audit 上下文泄漏，不能作为最终验收。`6a52de0` 的质量运行在确认 P1 后中止；
原始失败、中止状态、复现及修正均保留，最终 e079 重新完整验收。提前启动的五项目尝试仍标
NOT_ACCEPTED_PRE_QUALITY，不与后续结果拼成合格门。独立复核首轮两个 env oracle 错误发生于
helper 调用前，纠正为原生 name policy 后同一冻结候选重验；没有删除首轮证据。

本批只覆盖 Linux 上的介绍/只读/安装适配；不代表完整 Skill。没有执行 metadata 解析、真实
provider/discover、GPU、judge 或第二真实编码宿主，也未发布 release、PyPI 或技能市场产物。
跨平台单元 CI、真实平台安装/运行控制、真实宿主、资源与外部研究者反馈仍分别验收。
后续按 SK2-C（SK14 → SK15）推进；实际写入、联网、实验执行与长任务不能由本批只读结果推定通过。

本次仅补充验收报告和计划导航，链接、JSON schema_version、内容一致性、机器身份检查及
`git diff --check` 通过；没有改动已验收产品/测试输入或生成器。按验证工作流，报告提交不重复执行
完整产品质量门及 Gate A；它引用上述同一最终代码的证据，跨平台 CI 仍核对最终报告提交。
