# 易用性改进执行方案

日期：2026-10-29。起点：0a28406。维护者本轮明确要求制定并实施首次配置、已保存命令运行和下一步报告改进。
本包承接已完成的可靠性方案；历史验证与开发完成记录保持其原有范围。

## 用户目标

用户已有一条能运行实验的命令。首次只需把它保存一次：
~~~console
reprollm init --command "python eval.py --config configs/eval.yaml"
reprollm audit .
reprollm run --dry-run
reprollm run
reprollm diff --latest-successful
reprollm export .
~~~
初始化不会自动执行实验。需要补充的研究声明如实保留缺口。
日常运行不要求重复输入 argv、run ID 或手工整理报告路径。

## 任务与顺序

| 会话 | 编号 | 交付 | 状态 |
|---|---|---|---|
| UX-A | UXR01 | init --command 保存一次实验命令，沿用已有交互填写与写前保全 | IN_PROGRESS |
| UX-A | UXR02 | run 无 argv 执行已保存命令，dry-run 共用选择，明确 cwd/覆盖语义 | IN_PROGRESS |
| UX-A | UXR03 | audit 文本首先展示最多三项确定性的下一步，保留完整发现与门控 | IN_PROGRESS |
| UX-B | UXR04 | 引导填写研究字段：说明、类型错误原位重试、剩余字段准确计数；具体接口在 UX-A 实际反馈后细化 | PLANNED |
| UX-B | UXR05 | 单项目短教程与首次使用观察：记录完成首次 capture 的命令数、人工编辑点、阻塞；进阶手册保留为参考 | PLANNED |

按 UXR01→02→03 形成单任务提交，共享 UX-A 最终质量与五项目验收。模块不重叠的开发可并行，提交按依赖串行。
本轮执行 UX-A；UX-B 读取本轮报告后继续。不把用户尚未完成的试用登记为可用性成功。

## UXR01 保存首次命令

新增可选 init --command STRING；非交互无新增提示，交互已有字段顺序不变，显式命令不重复提问。
仅保存用户明确提供的 execution.command；不从 README 猜测可执行命令，不推断模型/数据/参数消费。
未给选项时，manifest 输出保持原字节。给定时通过共用命令解析及现有隐私检查，完整字符串按 YAML 字符串引用保存。
空白、控制字符、无效引用、有限非 shell 语法以 exit 2 在写入前拒绝；不回显不安全值。
--list-tasks 不得与 --command 组合。已有文件、--force 失败保全和任务选择合同保持。
验收先覆盖：带空格/引用/冒号/井号值精确保存；默认兼容；交互不重复问；冲突/非法/秘密不写入；旧文件保全。
隐私复用原机制，不修改 redaction.py。

## UXR02 运行已保存命令

显式 -- 后 argv 优先且保持原有行为，包括无 manifest 的 capture；不读取保存命令来覆盖显式 argv。
无 argv 时从选定位置最近的 manifest 读取 execution.command，使用与 init 相同的有限 POSIX 引用语法解析成 argv，仍 shell=False。
默认 cwd 为 manifest 根加 execution.cwd；显式 --cwd 优先，必须有效且在该 manifest 根内；遇到嵌套项目不能悄悄切换记录归属。
保存字符串中的 shell 操作符、展开、重定向、管道、赋值前缀与换行不自动解释，给出固定修复提示；复杂工作流可以显式使用用户自己的脚本。
Windows 同样使用这套字符串语法，路径使用 / 或适当引用；不把平台 shell 命令行语法误称为受支持。
读取沿用 preflight 有界/包含于根/普通文件政策。缺少命令指向 execution.command 和显式 argv 方式；不创建 run、不启动 child。
--dry-run 使用相同选择结果，继续零子进程、零网络、零写入，也不回显完整 argv。
实际执行复用原 recorder、脱敏、信号转发、child 退出码和 run v2，不自动 lock、不安装依赖、不默认启用输出捕获。
验收先覆盖：真实 child 收到准确 argv/空参数/空格；子进程退出 7；显式覆盖；根/cwd；错误无副作用；预览零执行；引用、转义、Windows 路径合同。

## UXR03 下一步报告

只增强人类阅读的文本报告，最多三项行动，放在详细发现之前。
从现有未抑制 FAIL 与 fix_hint 确定优先级，CRITICAL → 缺 manifest 初始化 → WARNING → INFO，稳定分组去重。
缺 manifest 的提示使用 reprollm init；依赖锁缺失绝不能错写成 reprollm lock 即可解决。
每项保留规则身份及安全字段/位置，未知发现沿用原 fix_hint。缺口/跳过保留说明；不把 SKIPPED 当作已修复。
无待处理失败时可提示现有工作流的下一条可用命令，但不声称研究结论已验证。
不修改 Finding/AuditReport schema、JSON、GitHub 输出、规则、severity、fail-on、engine、export。
用户可控文本经现有脱敏/转义路径，不能产生可执行注入式建议。
验收先覆盖：混合严重度、重复依赖、缺 manifest/依赖锁区别、全 PASS、全 SKIP、suppressed、无hint、敏感canary、稳定排序及原JSON/退出码。

## 规范与禁区

本轮新增行为来源于维护者明确的产品要求，实施时同步规范 §1、§3.2、§5.2/新增保存命令段、§21 与 CHANGELOG。
保留 D-11/D-13/D-18/D-24/D-39/D-40/D-41：不添加 shell=True、自动发现请求、自动执行初始化、自动修用户源码、不变持久 schema。
禁止更改 audit 规则结论、扫描覆盖合同、原有 runtime 证据含义、模型依赖、发布版本、历史 gold。
对保存字符串的保守拒绝只影响新路径；不能限制已有显式 argv。
UX-B 的新交互写入/恢复合同先做具体设计，不从本包推导无限范围自动配置能力。

## 验证与交付

依据 validation-workflow-2026-10-13.md：任务定向 RED/GREEN；最终候选一次完整 pytest/coverage/security/lint/type/schema/文档/示例质量门。
新文本导致生成 quickstart 变化须审阅并再生；JSON gold 不更新。Git 2.25.1 的既有兼容措施先核对再用。
五个固定项目全部 fresh L0 + init/L1，完整 JSON、profiles/hints/path/diagnostics/manifest 与原件比较；
新 --command 流程在五个一次性副本各演示用户明确提供的标准库 child，预览→保存→运行→回读。
文本变体检查新增行动的顺序/安全性和原 findings 不丢失；默认生成 manifest 不变。
本包是普通产品易用性迭代，不是旧 M1–M8 里程碑或 release；GPU/付费 API 门本轮 NOT_APPLICABLE。
推送 main 前本地门通过；推送后确认最终提交的五项 CI，报告实际结果与未完成的 UX-B。
原三份用户 WIP 及未提交的手动试用材料不纳入本轮提交。

