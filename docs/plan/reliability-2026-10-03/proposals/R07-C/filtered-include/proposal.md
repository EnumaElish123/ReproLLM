# R07-C D-I：被静态候选检查拒绝的 requirements include

日期：2026-10-28。基线 `e3aa653`。状态 **PROPOSED**；两份补丁仅为文本，候选政策执行0。
上一批配置深度修复及精确交付 HEAD 的五项 CI 已完成，本批不重开那些验证。

## 现状与下一步

现有 `-r build/pins.txt` 等合法引用可以在深度预算内到达目标，但现有 candidate
检查返回 False。图保留 unreadable 节点和原 include-unreadable 诊断，没有正文读取；
它既不满足 D-M 的实际正文读取失败，也不满足 D-G 的最终图缺节点，剩余包仍 WARNING。
规范 §12.3.8 明确将这个分支留在已接受范围外，因此这次先做独立 P-A。
当前规则没有证书语义；这里解决的是捕获视图下仍待决定的 absence 结论。

## 推荐 A 与备选 B

A 只增加独立内部 `excluded_requirement_targets`。在原 `_node` candidate=False 分支
记录私有 set；全部现有 roots 扩展后，从可读父节点的规范化 include 目标与该 set 求交，
排序去重。不改 scanner，不增加候选检查、正文读取、存在性探测、根/边、重试或预算。
默认空 tuple 保留 legacy/manual 构造。这个字段不持久化，也不是 D-M 的读取失败原因。

顺序是 **qualified/exact → D-F/S → D-L → D-M → D-G → D-I → 原 WARNING**。
保留所有旧优先分支完整 finding；只有原本会缺 pin 警告的逐包结果变为 SKIPPED/INFO。
消息、hint、证据顺序和目标 note 均在[具体规范节](proposed-section.md)逐字给出。
B 则不应用补丁，保持现有捕获视图 WARNING。两种选择都不扩大读取范围。

## 准确边界

- 目标必须来自已捕获可读父节点的受支持、非空规范化 include；目标扩展名不受限。
- 只按原 `is_analysis_candidate` 的实际 False 记录，不从诊断、不可读节点或 incomplete closure 推断。
- skipped directory 下不存在的目标也可能被拒绝；不声称文件存在、含 pin 或原因必为 venv。
- lexical exclusions、pyvenv marker、解析后指向排除目录的内部 alias，以及原 marker 检查失败可能触发。
- 普通缺失/二进制/超读取上限/越界 alias 若 candidate=True、实际 read=None，保持 D-M。
- 超出深度预算而未实际检查的目标保持 D-G；两事实并存时 D-G 先赢，旧 message/evidence 不改。
- 仅 listing 未列出不等于被拒绝；显式 include 仍可能触达候选。无入边的拒绝 root 不单独触发。
- 不支持的 include、被省略的 roots/use、一般 listing/framework 充分性仍不纳入本片。

## 必须明确接受的兼容成本

| 情况 | 当前 | A |
|---|---|---|
| 已知 torch 使用、无信用，目标因 candidate=False 被拒绝 | FAIL/WARNING | SKIPPED/INFO |
| 被拒绝目标不存在、为空、内容明确非精确，或位于无关子项目 | 同上 | 同样全仓保守 SKIP，不读取正文猜内容 |
| 任一 exact 或合格 lock 信用已赢 | 原结果 | 完整保留 |
| 旧 D-F/S、D-L、D-M、D-G 已赢 | 原 SKIP 及证据 | 完整保留，不追加 D-I 路径 |
| 无已知关键包使用，或全部已获信用 | 原 applicability/空结果合同 | 保留；不创造 use 或额外 PASS |
| 孤立 WARNING 或用户提升为 CRITICAL 的门 | 可退出1 | 可退出0；独立违规仍可退出1 |
| 默认 text / default export | 原警告 | 可显示 PASS+skips / 少一条 notable；完整 JSON 仍保留 SKIP |

全仓影响沿现行 existential exact 合同，不按目录配对这项不确定性。它不是安装成功、隐藏
精确版本或完整复现的证明。无关/缺失路径也可能使其他子项目的门停止失败，这是明确代价。

## 具体补丁与验收

[实现补丁](implementation-proposed.patch)只涉及 `core/deps.py` 和 `rules/env.py`；
[规范补丁](spec-proposed.patch)只增加 §12.3.15 及准确交叉引用。
[字节绑定](patch-binding.json)给出每个文件 before/after 与两份 patch SHA。
不改 engine、scanner、redaction、持久化 schema、规则 ID/默认严重度、依赖、版本或 gold。

[未来验收](acceptance-cases.md)是待批准的设计，不能写作已通过。
本批只运行冻结现行源码的有限公开 CLI 观察；每条原始命令与输入前后字节记录另存。
五项目源码盘点无受支持 include 边，只能支持条件零 delta 预期，不能验证新触发分支。
接受 A 和具体补丁后才做 P-B：公开 CLI tracer 先 RED→GREEN，再有限兼容回归、一次最终完整
质量门及 fresh 五项目基础/受影响命令与任务清单；最终提交推送 main 后核精确 HEAD 五项 CI。

更广 R07-C 保持 OPEN；本片不授权资源调用、外部 issue 提交或发布。
