# 2026-10-22 · R07-C D-M-S / P-A

状态：具体提案与规范补丁已准备；**PROPOSED，未批准、未应用、未执行未来政策**。
会话从干净 main `88a26ee270c92c939140fe347b71f2909f8c7d97` 开始，接续 D-M 的
[已交付 P-B](2026-10-21-r07c-declaration-read-pb/README.md)。起点五项 CI 已确认
[通过](https://github.com/EnumaElish123/ReproLLM/actions/runs/39581530995)；这不是本轮最终提交的 CI。
提交主题拟为 `docs(spec): propose decoded declaration structure policy (R07-C)`。
本报告随任务提交，不虚构自身提交 hash；实际交付 HEAD 和 CI 在推送后的交付消息确认。

## 本轮产物与决策边界

- [具体方案及兼容性](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/R07-C_declaration_structure.md)：封闭结构表、保留部分有效声明、现有信用与 D-F/D-S→D-L→D-M 优先级。
- [未应用规范补丁](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/spec-proposed.patch)：同步跨引用并提议 §12.3.7；正式 §12.3.6 和其他规范原字节不改。
- [32 组独立验收要求](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/acceptance-cases.md)：未来 P-B 用例，不是已运行的测试数。
- [PROPOSED 决定](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/decision.json)、[spec issue 草稿](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/issue-draft.md)及独立审阅；没有向外发 issue 或消息。
- 计划入口、包索引、05 政策导航与 CHANGELOG 只登记提案状态，不改写前序决定或报告。

推荐 A 仅扩展内部 `invalid_structure`，复用 D-M 消费；不检查 Poetry/Pipfile 单包值或 requirements grammar/include。
所有正面 exact／qualified-lock 证据保留，坏兄弟项不能撤销；未知结构不得变成新 pin。
falsey 错误类型不能与 missing 混淆；顶层 YAML None 保留旧兼容，但显式 dependencies/pip null 触发。
无关项目失败可保守影响全仓剩余关键包，孤立 warning/critical 门可能 1→0；这些成本属于具体待接受内容。
整个 R07-C 继续 OPEN。拟议实现只涉及 deps 的有限事实；无新增 engine/redaction/schema 改动。

## 实际执行与预期的区别

| 材料／检查 | 本次事实 | 边界 |
|---|---|---|
| [旧政策观察](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/observations/README.md) | 64 个预写小例首次全部匹配；133 输入文件、2744 字节、133 次已有 reader 调用；11 份 source/spec 与基线 Git blob 相同 | 真实 parser/AST/rule；Git 非仓库、installed_versions 空为明确控制；无完整 CLI/engine/renderer 或未来政策执行 |
| [五项目来源](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/portfolio/source-evidence.md) | 最终 43 条只读 Git 命令 exit 0；五 pin/origin/前后 clean；8 声明文件逐字节核对 | 三 pyproject 共 39 依赖数组／163 字符串均符合表；五 requirements 排除；无 Pipfile/Conda 实际候选 |
| 完整五项目影响 | 独立来源预期 findings/profiles/hints/paths/diagnostics/facts/init 无差异；10 份历史 audit/facts oracle 与原索引哈希匹配 | PREDICTED_NOT_EXECUTED，不是新鲜 Gate A，不复制当前输出更新 gold |
| 规范草案与文稿 | 应用检查、相对链接、结构一致性、JSON 唯一键、输入／源码哈希及公开隐私检查 | [文稿检查回执](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/document-checks.json)记录最终结果；补丁保持未应用 |

当前观察只比对预先固定的完整 critical-rule findings 和声明／issue／barrier／project／lock／presence 投影；
其他原始诊断、调用轨迹、scanner/AST 与 presence-rule 输出保留，但不虚称独立全输出 gold。
39 个输入被人工映射为拟议结构触发；映射不是未来执行。观察得到 58 个 WARNING、3 个既有 SKIP，
另 3 个 case 无 critical finding（两项信用控制、一项无已知 use）；不把空结果自行合成 PASS。
产品观察体 0.368127 秒，observer 总墙钟 1.079540 秒，外层命令 1.5139764 秒，退出 0。
另从公开 JSON 提取同哈希观察器，在新私有目录重放；64 项预期再次匹配，两次全部 actual 对象逐字段相同。
重放只验证证据包可重现，未来政策执行次数仍为 0；首轮记录没有被第二次覆盖。
另有[独立证据回读](../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/observations/review.json)：
全部 64 个预期／投影及两次完整 actual 以保留布尔／数字类型的 canonical JSON 比较一致，
全部输入哈希和 39/25 设计分类核对通过；源逻辑审阅范围和原观察器 Python equality 的限制明确保留。
作者会话内的独立 Agent 审阅不计外部采用、维护者批准或产品全量验收。
五项目最终来源采集墙钟 1.578709 秒、Git 累计 1.464317 秒，前置预读单独记录。
这些阶段耗时不能相加充作整个会话耗时。

## 验证流程分类

本批只有方案文稿／证据／未应用 patch；没有修改产品、正式测试、验证工具、CI、依赖或生成器输入。
私有一次性观察脚本的可重放源码封存在 JSON 中，未安装为仓库工具；没有用条件实现代替正式产品。
依据 [validation workflow §3](../plan/validation-workflow-2026-10-13.md)，本地完整产品质量门、fresh Gate A
均为 **NOT_APPLICABLE**；生成文档 freshness 因输入／输出未变亦不适用。
普通 P-A 不激活里程碑或发布 Gate B；资源门 **NOT_APPLICABLE**，不是 PASS。
适用的文稿检查、真实旧政策观察和独立来源核查分别记录；最终推送 HEAD 的五项 CI 单独确认。

公开新文件以逻辑相对路径、合成输入和源码哈希标识；私有操作路径不进入证据。
没有新增持久化 schema；证据 JSON 均有 schema_version。旧 P-A/P-B、source、spec、val、gold 原件保持。

## 阻塞与下一会话

政策阻塞仅是具体 D-M-S 决定未作出；当前产品继续按已接受 D-M 工作。
具体接受 A/规范补丁后，P-B 才按验收矩阵先 RED，再最小实现 GREEN，完成定向／静态检查，
最后一次完整质量门、全五项目 Gate A 与 init/L1/default export 及结构专项；之后推送并检查准确 HEAD CI。
本提案没有提交未经展示的实现补丁供自动批准，实际实现需符合已审阅合同及未来测试。

资源台账维持：VAL-R01 PASS 绑定 `948d164`；VAL-R02 PASS 绑定 `75d1b0`；VAL-R03 仍因上次 HF 小文件 403
和 Project C 原 metadata 缺口 BLOCKED，全部五份原始 metadata 尚缺。本轮没有新的 Hub／原生／GPU／judge 请求。
见 [资源台账](pending-resource-validation.md)；不把历史资源结果改绑本提交，不声称 release-ready。
不调用付费 API，不创建 tag，不发布版本。
