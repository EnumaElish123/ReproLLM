# R07-C D-M-P P-B：PEP 621 字符串失败

日期：2026-10-23。产品提交 `26a4d309380baee117cc1ae71295170c8d4ac82b`，父提交 `2a2b4aeefaa87b272c4efa9e4c281d826671ba5a`。本地最终验收已完成；精确推送 HEAD 的五项 CI 在交付时独立核验，本报告不提前声明远端通过。未发布版本。

任务依据：[当前计划](../../plan/README.md)、[具体 P-A 与保留快照](../../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/README.md)、[上下文授权记录](../../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/decision-accepted.json)、规范 §12.2、§12.3.6–§12.3.9。
用户在具体 A、原规范补丁及全仓保守成本交付后回复“继续进行下一步开发”。记录解释为这一个 D-M-P A/P-B 的上下文授权，不伪写成逐字“接受 A”，也不扩张旧 D-G/D-C 或其他政策。原 patch SHA-256：`89505a8e74cd84ad3589e0a95cc8749f671446443110fb2a35e6f4745bc6ce9f`。

`_add_requirement_line` 仅返回原 Requirement 调用是否成功；两个现有 PEP 621 列表提取点在失败时以 setdefault 记录内部 unparsed_requirement。已有 unreadable/invalid_syntax/invalid_structure 优先，部分声明、原诊断、读轨迹、信用和 D-F/D-S → D-L → D-M → D-G 次序保持。
原 P-A 清单的 20 项哈希与父提交 checksum 保持不变；新增接受 sidecar 独立保存，不改旧 PROPOSED 或原观察。
空串或无关子项目的实际失败也可能让剩余未获信用的关键包由 WARNING/CRITICAL 转为 SKIPPED/INFO，孤立退出码可由 1 变 0；这不证明存在 exact pin。默认 text 可显示 PASS 与 skipped 计数，default export 不再列该 warning，完整 JSON 保留 finding。无新增 engine/scanner/redaction/schema、依赖、版本或历史 gold 改动。

测试先于实现，新增 170 个唯一参数例（core 94、rules 44、CLI 32）；原未来 P01–P38 到最终源码行号、SHA、精确重放 selector 见 [验收映射](acceptance-mapping.json)。跨验收 ID 引用同一家族不重复计数。
Core 原 RED 为 36 failed / 56 passed / 2 权限 skip。消费者首轮 43 项政策失败与 4 项错误 verbose 调用失败分开保留；修正全局选项位置后，47 项均为预期政策 RED，29 控制通过。准备时位置预期修正及原记录亦保留。
[Core RED（私有原件 SHA 6007a30d219c…）](evidence/source-index.json)；[消费者修订 RED（私有原件 SHA 264c6f7bd691…）](evidence/source-index.json)。
首轮完整质量门在旧临时候选 978c5375 真实 FAIL：4116 passed / 2 failed / 4 skipped / 4 deselected，墙钟 617.184s；不是准备失败或可忽略 skip。两个失败为测试预期：旧扫描器保留越界别名到安全 read_text 边界，返回 unreadable；旧 exact-format 的 malformed PEP 621 需按本片变为 SKIP/INFO。产品源码未改。
[原失败质量门（私有原件 SHA 6b2ca49c6b2c…）](evidence/source-index.json)；[按原始哈希保留的轮换记录（私有原件 SHA 87550a00da08…）](evidence/source-index.json)；[旧候选 Git bundle（私有原件 SHA 022c8ab06b81…）](evidence/source-index.json)。
管理员隔离旧源码修正版 RED 为 38 failed / 108 passed / 0 skipped；当前候选定向 GREEN 为 1032 passed / 0 skipped，含两条真实符号链接用例。两处测试修正完成上述验证后，仅 amend 自己未推送的临时候选，父提交仍为 2a2b4ae；完整质量门因测试输入改变重新执行。
[管理员纠正验证（私有原件 SHA 54cd8a2bbdca…）](evidence/source-index.json)；[最终完整测试收据与四项 skip](final-test-receipt.json)。

最终主验证输入为 521 个文件、23 helpers 与 13 bindings。完整输入清单 SHA-256：`b737cd9d6e104536859b671cc9d3bd4c9eda96f180fc5cefe87d318ea312b4b8`；工具 manifest SHA-256：`b4bf440c7b55ff8dd6668cc6366b88533ba0d3e4cd34b7720f6014c4fe74b0c2`。下表每组均记录实际命令、退出码、原始流哈希和耗时，顺序执行，未以旧通过结果替代。

| 最终组 | 实际命令 | 检查 | 墙钟秒 | 命令累计秒 | 结果与证据 |
|---|---:|---|---:|---:|---|
| preflight-final | 2 | 真实管理员环境＋5 safety 用例 | 2.168 | 2.166 | [PREFLIGHT_PASS（私有原件 SHA bcbd285bce6b…）](evidence/source-index.json) |
| quality | 24 | 4118 passed / 4 skipped / 4 deselected | 736.029 | 735.772 | [PASS（私有原件 SHA 765f8c833723…）](evidence/source-index.json) |
| gate | 125 | 35 完整比较；15 初始化文件 | 222.923 | 222.596 | [PASS（私有原件 SHA 571ba76207ee…）](evidence/source-index.json) |
| affected | 20 | 15 graph／完整report／verbose 比较 | 57.930 | 57.835 | [PASS（私有原件 SHA daa0d759c092…）](evidence/source-index.json) |
| synthetic | 1 | 24 完整内部记录 | 0.426 | 0.363 | [PASS（私有原件 SHA 438951c87af8…）](evidence/source-index.json) |
| post-gates | 15 | 五原件 HEAD／origin／clean | 0.690 | 0.610 | [PASS（私有原件 SHA 095c61aa3d0f…）](evidence/source-index.json) |

总覆盖率 94.475628%；redaction 分支覆盖 100%；安全测试 343 passed。Ruff、format、mypy、生成文档、examples 与自审计均包含于 24 项最终质量门。Windows schema 仅使用已声明 CRLF 差异归一；Linux 3.12 的精确 freshness、generated docs 和 examples 仍须在最终 HEAD CI 核验。
普通准备预检为 PREPARED_ADMIN_REQUIRED，符号链接权限失败没有被冒记为通过；正式入口使用真实管理员 token，5 项既有安全用例通过。工具准备的 python3 定位失败、启动/证据读取权限记录均保留，未改全局安全设置或降低测试门槛。

五项目仍使用 val.md 的原始固定 SHA。预先核对旧 D-C 产品字节、调用参数、包环境及完整原始输出后，显式绑定其已接受 actual 输出作为兼容基准；没有用新候选输出生成 expected，也没有退回 D-C 之前的 HarmBench gold。47 份完整基准和 20 份 graph/verbose 预期均独立绑定，旧历史原件保留。
P36 的 source-only 准备包含 33 命令、12 源文件及 163 个成功 PEP 621 字符串的逐项原文/位置/hash 核对；不以总数替代清单。[逐项位置证据（私有原件 SHA 76d647c53cfb…）](evidence/source-index.json)；[旧证据复用绑定（私有原件 SHA 5fee767fa7da…）](evidence/source-index.json)。
P37 为完整零差异：五 fresh L0/facts/profiles/hints，五 disposable init → L1/default export，及完整 graph/verbose 均比较；15 初始化文件包含隐藏的 config/project-rules。HarmBench 保留 D-C 后 47 declarations、2 Python diagnostics，root closure.complete=true、is_exact=false；不是本片再次新增 art/tenacity 或删除诊断。原五 checkout 最终身份保持。

| 项目 | 固定提交 |
|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` |

本片 synthetic 使用实现前冻结的 24 输入与完整旧产品兼容记录加独立字面 delta：13 内部 cause 变化、7 WARNING→SKIP、P19 原 D-M evidence 扩展。它验证真实依赖/scanner/rule 内部记录，固定 installed_versions={}，没有执行公共 CLI/engine/profile/init/export；那些边界由独立消费者测试与五项目命令覆盖。[synthetic 冻结计划（私有原件 SHA 0db9c01e6d72…）](evidence/source-index.json)。

公开证据共 3 文件（含 checksum）；来源 968 项。verbatim-copy=0、verbatim-envelope=0、projected-metadata=0、private-reference=968。归档 writer/独立 reader 的 61 项工具正反例通过；工具自测不是产品验收。
[来源与保留规则](evidence/source-index.json)、[完整校验和](evidence/SHA256SUMS)、[归档执行收据](archive-run-summary.json)、[独立回读](archive-readback.json)。本次公开包严格为 hash-references-only：所有原始正文、命令元数据、helper、JUnit 与 coverage 均整件留在本机，只公开相对逻辑名、长度、SHA 和逐项核对的终结摘要；不复制、封装、投影或删改任何原始业务字段。独立 reader 核验本地原件并拒绝公开包夹带正文。
这是公开证据索引与复验入口，完整原始证据包保留本地；独立外部读者不能仅凭哈希确认私有正文，也不能仅凭此目录一键回读全部流程。映射给出精确 pytest selectors；五项目按固定 pin、val.md 命令及独立基准复验，需提供明确环境和临时副本。

原 759 文件／约 5.8 MB 原文归档写入在执行前被自动审批拒绝：未确认该批私有来源适合公开及具体 payload 授权。安全替代缩减为三个公开元数据文件、零原始正文，并新增 19 项正反例（8 正／11 拒绝）验证强制引用政策。原始流与失败记录完整保留本地，主产品验证结果和工具未变。
本轮普通政策 P-B 不完成新里程碑、不准备 release，资源 Gate B 为 NOT_APPLICABLE。VAL-R03 原 metadata 缺失/HF403 等仍 BLOCKED；VAL-R01/VAL-R02 分别保留 948d164／75d1b0 的历史接受身份，本轮未重跑 GPU、付费 API、正式 judge 或资源实验。独立试用反馈和申请授权仍分别待外部输入。
后续可准备 environment 嵌入 pip 字符串失败的独立 P-A：先核既有非空过滤/strip、真实失败、原原因与信用，再写兼容性和五项目预期；本次 D-M-P 授权不自动扩展过去。更广 R07-C、未采集来源、通用语法/充分证书仍 OPEN。
交付前另核精确最终 main HEAD 的五项 push CI、五项 Verify candidate checkout，以及 Ubuntu 3.12 的 schema/generated-docs/examples；本地 PASS 不替代远端结果。暂不发布版本。

文稿生成的路径护栏曾将两条合成 HTTPS 测试选择器误认成盘符，在任何报告写入前停止；仅修正匹配边界后生成，真实绝对路径仍被拒绝。见[文稿更正收据](documentation-notes.json)。
