# 2026-10-21 · R07-C D-M / P-B

本地验收 **PASS**。D-M 已按维护者具体接受的规范和实现落地；完整质量门、五项目 Gate A 和受影响命令均在相同任务提交上首次通过。
本报告提交时尚未推送最终文档提交，**最终 HEAD CI 为待执行**；推送后的精确提交和五项 CI 在交付消息及外部回执单独确认，不把旧运行当作本轮结果。

基线 `aee6488078c3435dcc33b20a68cca8bda0d0ec57`；P-A 快照 `34eaea23fc98aceab88681a82e4750e0f907b3bb`；
产品任务提交 `69712c0585045261c6c5a691a6f23224639f8717`（`fix(audit): defer missing pins after declaration body failures (R07-C)`）。
后续收尾提交仅增加本报告和验证材料，不改变已验收产品输入。

[具体接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/decision-accepted.json)、
[原提案及补丁](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/R07-C_declaration_body_failures.md)、
[P-A 报告](../2026-10-21-r07c-declaration-read-pa/README.md)。原 449 文件 PROPOSED 快照逐字节保持，接受记录另立。

## 实现与兼容边界

按规范 §12.2、§12.3.1–§12.3.6，仅在现有采集中记录声明正文已知读取／TOML、YAML 解码失败；requirements 仅记录实际正文读取返回 None。
保留 exact／合格 lock 的正面信用及 D-F/D-S、D-L 既有优先级，然后把剩余缺 pin 项逐包改为 SKIPPED/INFO。
规则证据保留既有首条来源，再按路径排序追加失败来源；不增加精确声明或使用事实。

现行全仓 existential exact 政策决定了保守成本：另一子项目的失败也可能影响剩余包；孤立 WARNING 或提升的 CRITICAL 门可能 1→0。
默认文本可能显示 PASS 和 skip 计数，默认 export 隐藏 SKIP，完整 JSON 保留。
engine、scanner、redaction、schema、依赖、presence、五项目 gold 和历史资源结论均保持。

**整个 R07-C 仍 OPEN**：可读但未支持的结构／条目语法、requirements 指令和一般 include 图、未知 use／遗漏候选、listing／framework 和充分性证书不属于本批。

## 测试先行与实际更正

新增 105 项验收，按 D-M 修订 11 个旧结果。真实 RED 为 **116 failed / 19 passed**，pytest 6.93 秒，命令 7.866499 秒；产品仍为旧字节，无收集错误。
首轮七模块 GREEN 实际为 **2 failed / 529 passed**，pytest 40.45 秒、命令 41.380809 秒；原始失败完整保留。
两处测试路径预期错误分别是：恢复 loose pyproject 后按既有采集顺序优先于 requirements，以及 ignore 证据原本指向配置文件。
只改这两处断言，原接受补丁、产品和规范未变；[最小修正及来源](final/qualification/oracle-correction/test-oracle-correction.patch)另立。
最终七完整模块 GREEN 为 **531 passed**，pytest 42.14 秒、命令 43.146334 秒；没有重新执行 corrected RED。
六个受影响文件 Ruff／format、两个产品源 Mypy 通过；更正后两测试另作 Ruff／format 通过。

[三个真实阶段及静态检查](final/tdd/green-2/summary.json)、[完整来源索引](final/source-index.json)保留命令、原始退出、时长和原始／分享版哈希。

## 同一任务提交的最终验证

| 验收 | 实际结果 | 时长与完整记录 |
| --- | --- | --- |
| 完整质量门 | 24/24 命令及 24 次来源守卫通过；3524 passed、2 deselected；覆盖率 94.38745168%；redaction 100%，24/24 branches；security 345 passed | wall 685.930389 秒；命令合计 680.390053 秒；[summary](final/quality/summary.json)、[commands](final/quality/commands.json)、[JUnit](final/quality/pytest-report.xml) |
| 五项目 Gate A | 5/5 固定版本／origin／前后干净；完整 L0 和事实共 10 份 JSON 对比通过；规则、profile、hint、路径及诊断无 gold 差异 | 51 命令／32 检查；wall 88.665239 秒；[summary](final/gate-a/summary.json)、[commands](final/gate-a/commands.json) |
| 受影响命令及专项 | 5 份完整 L1、5 份完整默认 export、全部 15 初始化文件（含 10 隐藏配置）通过；4 个预写 D-M 完整 JSON、额外 export 的预写 summary/notable 语义通过 | 197 命令／154 检查；wall 193.348924 秒；[summary](final/affected/summary.json)、[commands](final/affected/commands.json) |

额外 synthetic export 保存完整输出，但只按事先写定的 summary/notable 验收，**不是独立整份 Markdown gold**。
专项包含管理器正文解码失败、安全 include 正文失败、排除／深度控制和全仓正面信用优先；排除控制 audit 预期 exit 1，其余专项预期 exit 0，实际全部符合。
所有命令退出和逐项预期／实际在完整 commands、comparison 记录中；不能从零退出计数推导验收。

| 固定项目 | 目标 SHA | L0／facts／init／L1／export |
| --- | --- | --- |
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | PASS |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | PASS |

三个最终门均绑定任务 `69712c0`，输入清单前后字节相同；原始固定 checkout 只读，生成命令仅操作一次性副本。
质量 summary 原哈希 `9ba64605b1e3d3a46120927950b58ef37258355987830123d4ed584d15f2baa3`；
BASE `f5b7c5b6b7d1276a32e19e6bc5ef8ee609e4231d1dd37fa145a65360bd01cf6f`；
affected `53246b3216747d83866385aa01a8af03b9d34ce74aac8e3ed45636f547908452`。

## 材料、限制与交付

[完整本地证据](final/README.md)、[归档清单](final/file-manifest.json)保存原始来源哈希和明确的隐私投影。
JSON／JSONL 保留业务结构；XML 解析后投影并正确转义；文本除固定隐私路径／身份投影外保持原空白与 EOF。
大清单、轮子、辅助代码和内联命令代码以原始哈希引用，不把执行材料或源码副本混入产品。
归档首轮因 JUnit 安全测试名称中的合成绝对路径／Windows 标签／合成 token 参数被隐私检查阻止，写入前停止、零输出文件。
随后只为 52 个已按原始 class/name 哈希绑定的测试名称建立不同合成标记；函数名和原始整份 JUnit 哈希保留，状态、计数、时间、文本及业务 JSON／export 均不变。
第二次归档又在写入前发现归档脚本局部变量遮蔽错误，同样零输出文件；只重命名 XML 循环的局部变量并保留实际停止记录。
归档准备还修正 coverage.json 的重复选择、安装包一次性目录的显式映射和离线轮子目录别名的规范来源；相关实际停止均在写入前，原始记录完整保留。
最终第 7 次归档成功，828 文件、1516 条原始来源索引；前 6 次均在写入前停止且零输出文件。
工具准备／修正／失败流保存为外部原始哈希引用，并另立安全摘要；正式产品验收记录保留完整数据。
独立回读结果见交付回执；不重跑产品质量门。
真实 RED、首轮失败 GREEN、最终 GREEN，以及准备／读取桥／静态修正历史分别保留，不把准备停止写成产品失败或通过。

本轮是普通规则政策会话，按 validation workflow 和 val.md 不激活原生／Hub／GPU／付费 Gate B，记 **NOT_APPLICABLE**；无新 gold、tag、release 或 PyPI 发布。
本地完整质量门只在最终产品输入运行一次，文档／证据收尾不重复产品全量测试。
主工作区既有 README、docs/index 和额外 gold 草稿属于维护者修改，交付前后单独核对，未加入本批提交。

独立归档与报告回读 PASS，回执原哈希 `7625c8c5133e003cc1a20b5bb1cbc0daf177083de6884f9c8dca530738b86adc`；核对 828 文件、1516 来源、19 完整比较及 17 本报告链接。
