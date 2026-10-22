# 2026-10-22 · R07-C D-M-S / P-B

本地验收 **PASS**。已实施维护者接受的方案 A 和具体规范补丁，保留部分有效声明、既有信用和优先级。
本报告收尾提交时，**最终推送 HEAD CI 待执行**；交付时另核对精确提交的全部五项 CI，不借用旧运行。

起始基线 `bd80e78fdad1b80d150375cfea2fe68a6a2e1565`，main，起始工作区干净；同步确认远程没有更新。
产品任务提交 `9bfa895a53478868c0e2cffa5978665f66556015`
（`fix(audit): defer missing pins after decoded declaration gaps (R07-C)`）。
本报告和证据收尾不改变该提交的产品、测试、规范、依赖或验证工具字节。

[具体接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/decision-accepted.json)、
[原 P-A 提案](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/R07-C_declaration_structure.md)、
[独立验收预期](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/acceptance-cases.md)、
[P-A 报告](../2026-10-22-r07c-declaration-structure-pa.md)。
原 18 文件 P-A 快照逐字节保持，原 PROPOSED 记录不改写，具体接受另立。

## 实现与兼容边界

按规范 §12.3.7，仅在管理器声明成功解码后检查明确列出的容器和成员类型，记录
`invalid_structure`。保留有效部分的包名、顺序、来源、行号、specifier、exact 和读取次数；
缺省字段、合法空容器、environment 顶层 None 的既有例外及未知映射键均按接受表处理。
不扩张单包值或字符串语法，也不将 requirements 一般图不完整当作本片结构错误。

产品只修改 `core/deps.py`；复用既有 D-M 消费。
exact／qualified-lock 信用优先，然后 D-F/D-S、D-L、D-M；没有新增每包 PASS 或撤销正面信用。
剩余已知使用且无信用的关键包在已知结构缺口时成为 SKIPPED/INFO。
全仓 existential 合同意味着另一个子项目的缺口也可影响它；孤立 WARNING 或提升为 CRITICAL 的门可能退出1→0。
默认文本可显示 PASS 和 skip 计数，默认 export 隐藏 SKIP，完整 JSON 保留；独立 qualifying finding 仍可失败。

engine、scanner、redaction、持久化 schema、依赖、版本、presence、五项目 gold 和历史记录均未改。
规范变化恰为接受补丁，SHA-256 `c1459c7e72094c4081499b501ad51895e7d075f23047645aa5037c841e1ca33c`。
独立审阅及静态保护检查通过：177 个受保护产品／工具／schema 文件保持字节；没有 fixture／gold 更新。
整个 R07-C 仍 OPEN：requirements 图与行语法、manager 单包值、遗漏候选／use、listing／framework 和充分性证书不属本片。

## 测试先行与环境记录

| 阶段 | 实际结果 |
| --- | --- |
| 核心 RED | 106 failed / 216 passed / 1 skipped；6.49秒；全部106失败都是旧实现缺少 `invalid_structure` |
| 核心 GREEN | 322 passed / 1 skipped；5.62秒，命令6.071秒 |
| 规则／CLI 新回归 RED | 45 failed / 10 passed；22.43秒 |
| 既有 scope 预期修订 RED | 6 failed / 4 passed；0.70秒 |
| 最终8个受影响规则／CLI完整模块 GREEN | 401 passed / 4 skipped；145.53秒，命令146.0243秒 |

新增核心模块136项；106项核心 RED 由98项新失败和8项旧预期修订构成。
跳过来自既有平台前提，未新增 skip；管理员测试上下文核验了适用符号链接安全测试。
定向 Ruff／format／严格 Mypy 与两个独立源代码审阅通过。
原始临时目录权限失败、仓库内临时目录的父 Git 干扰，以及一次无效测试目录选择分别保留为准备记录，
不计作有效语义 RED 或 GREEN。新测试文件的 CRLF→LF 规范化另记，内容与任务提交 Git blob 相同。

[核心RED](evidence/development/core-red-receipt.json)、[核心GREEN](evidence/development/core-green-receipt.json)、
[消费端RED](evidence/development/consumer-red-receipt.json)、[消费端GREEN](evidence/development/consumer-green-receipt.json)、
[独立保护检查](evidence/development/acceptance-checks.json)保留来源、命令、退出、时长和原始日志哈希。

## 最终质量门及真实失败修复

最终完整质量门为 **21/21命令 PASS**（Windows schema仅CRLF等价，精确字节门待Linux CI），墙钟597.979956秒、命令合计597.764802秒：
**3698 passed / 4 skipped / 4 deselected**；pytest506.10秒，命令506.872855秒；覆盖率94.40864993%。
最终pytest采用 `-m "not slow and not linux_only"`；四项既有skip分别是Windows下的调用符号链接归一化、
两个依赖POSIX文件名的扫描诊断案例、一个POSIX权限位案例；四项deselected按既定marker排除。
redaction 59/59行、24/24分支100%；security **343 passed / 2 skipped / 3361 deselected**，16.07秒。
锁定离线同步、环境核验、quickstart、Ruff／format、严格 Mypy、生成文档、schema、四个示例的七条audit／lock命令和自审均通过适用断言。
完整门遗漏的 CLI `--version` 随后在 Gate A 前单独补验，输出精确 `reprollm 0.7.0`，退出0，命令0.360938秒、墙钟0.409685秒。
前后513份最终产品／测试／配置／schema输入及冻结验证辅助字节一致。

[最终质量摘要](evidence/validation/quality/summary.json)、[完整命令](evidence/validation/quality/commands.json)、
[真实测试计数](evidence/validation/quality/test-counts.json)、[版本补验](evidence/validation/quality-supplement/summary.json)。

首轮完整质量门实际为 **51 failed / 3647 passed / 4 skipped / 4 deselected**，pytest507.10秒，墙钟515.751907秒。
深层临时目录触发 Windows 路径长度限制，导致快照／Git／scaffold失败；没有以产品改动或测试放宽消除它们。
在独立短临时目录逐一重跑原51个失败节点，**51 passed**，命令16.241510秒，probe墙钟16.723758秒；
随后重新执行完整最终门得到上述 PASS。原始 FAIL、日志／JUnit哈希、移动来源、修复probe均保留，不重标成功。

本机 schema 的原始字节比较不同，差异仅为 CRLF→LF；规范化后完全相同，沿用既有 Windows 验证边界。
这不宣称本机字节级 freshness PASS；最终精确推送提交的 Ubuntu Python3.12 CI 必须另通过 schema freshness。

## 五项目及受影响验证

| 验收 | 实际结果 | 命令合计／墙钟及完整记录 |
| --- | --- | --- |
| 五项目 Gate A 与受影响扩展 | PASS；125命令、35检查；L0／facts／init／L1／export无delta | 222.880730／223.189871秒；[summary](evidence/validation/gate/summary.json)、[commands](evidence/validation/gate/commands.json)、[checks](evidence/validation/gate/checks.json) |
| 六个结构专项 | PASS；81命令、23检查；完整JSON、恢复、压制、重复、退出门和可见性 | 25.760440／25.985838秒；[summary](evidence/validation/synthetic/summary.json)、[commands](evidence/validation/synthetic/commands.json)、[checks](evidence/validation/synthetic/checks.json) |
| 最终五原项目身份 | PASS；15命令，SHA／origin／clean均一致 | 0.498485／0.564235秒；[summary](evidence/validation/post-gates/summary.json)、[commands](evidence/validation/post-gates/commands.json) |

| 固定项目 | 固定 SHA | L0／facts／init／L1／default export |
| --- | --- | --- |
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | PASS |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | PASS |

基线完整 L0／facts共10份JSON，受影响完整 L1五份、默认export五份，以及全部15个初始化文件逐项核对。
独立预期来源为已审阅历史 oracle，47个文件的来源与hash绑定；不从当前输出生成预期。
JSON只豁免规范允许的根 `generated_at`／`reprollm_version`；完整finding、profile、hint、路径、诊断、类型及顺序均严格比较。
stdout／stderr明确允许 CRLF跨平台换行等价；生成的 init／export 文件按完整字节核对。

首轮 Gate 的10项基础比较实际通过，但第一个 extended-path Git clone 返回128 Invalid argument，整个首轮为 FAIL。
原始收据、命令和成功基础输出的hash保留；五个原固定 checkout 事后身份／干净状态通过。
随后只在独立私有运行适配器中将一次性 clone 目的地改为短路径，并导入原冻结 common；
适配差异反向恢复后等于原 gate.py，原工具、产品、oracle均未改。
真实 clone／checkout／读取最长源文件 probe 与 Git blob 字节相等，实测probe路径216字符；
正式目的地的最长分析源文件路径预计算为231字符。
授权后重新运行完整 Gate，而非拼接首轮结果。纯私有路径修复不使已通过产品质量门失效。

六个预写结构专项覆盖 malformed／restored／suppressed，保留18份独立完整预期报告与24次实际JSON调用（含重复确定性）。
同时核对 isolated WARNING／CRITICAL 的0与恢复后1、独立warning仍1、ignore、默认文本／show-skipped及export。
额外 synthetic export保存完整正文，但只按预写summary／notable语义断言，**不是独立整份Markdown gold**。
所有退出、预期／实际、耗时与完整差异在证据命令和检查记录中；摘要数字不能替代它们。
生成命令只在一次性副本执行，五个原 checkout只读；最终再核对全部原项目SHA／origin／tracked与untracked干净。

## 证据、资源与下一步

[证据包说明](evidence/README.md)、[逐项原始／分享哈希](evidence/source-index.json)、
[校验和](evidence/SHA256SUMS)、[明确投影策略](evidence/projection-map.json)可供回读。
首次实际归档及独立回读PASS：613个文件纳入SHA256SUMS，含清单共614个文件、3,216,564字节；
608个复制来源中36个文件只替换明确机器根路径；151份JSON严格核对类型／键序／数组序，222个未复制原始来源按hash复验。
业务字段、时间戳、空白、换行与EOF不改；不将未知路径以宽泛正则擦除。
完整业务报告与生成文件公开一次；质量JUnit／coverage正文、详细测试日志和初始失败正文留私有并给出原始hash／大小。
原始FAIL摘要、命令、检查、修复probe、短路径适配精确差异及其hash另立，未隐去失败或把它们标为PASS。
文稿的空白检查通过；完整证据的同类检查会报告原始CRLF、行尾空白／末尾空行，全部位于已校验的原始证据范围。
按证据保真合同保留这些字节，不trim原始输出或把该检查写为全局PASS。
提交前另发现通用`.gitignore`会略过10份隐藏初始化配置；已逐个纳入证据提交，614份暂存blob与已校验工作字节完全相同。

SHA256SUMS原hash为 `a356ba227304be00caab2e7d886803b81e35d1dd4fd9166f62cdd9591c9fc380`；
source-index原hash为 `55eaf0bcb7d2efd66de865a5c9c02e457a1bb294dc76d8dae788a275ac8fa5ac`；
独立回读回执原hash为 `6333628e521f0270f6d612c0856320b7284c024d0bef074bbc6b09a6ff945e60`。

按验证流程，本片是普通政策产品会话，资源 Gate B **NOT_APPLICABLE**，不是PASS。
VAL-R01在 `948d164`、VAL-R02在 `75d1b0` 的历史接受仍绑定原候选；本轮无GPU或付费回放。
VAL-R03仍 **BLOCKED**：五份原始metadata manifest缺失，最近台账中的HF小文件访问403；本轮没有重新作授权访问预检。
需提供原始输入及相应作者许可后先核对身份／hash／访问范围，再执行适用资源门。
A02独立试用反馈仍PENDING，A03可继续更新带来源事实与申请文稿；不主动联系或提交申请。

已批准代码没有剩余实施项。下一轮先提出 requirements 深度预算后未捕获目标的具体 P-A，
列明规范、兼容成本、独立预期和五项目影响；未经具体裁决不实施该新政策，也不关闭整个R07-C。
未调用付费API，未创建tag、release或发布版本。
