# R07-C D-M-P / P-A：PEP 621 字符串解析失败提案

日期：2026-10-23。任务：R07-C 的下一局部 P-A，标识 D-M-P。
状态：**提案准备完成，PROPOSED；政策未接受、未实施，规范补丁未应用**。
本报告是推送前快照；提交身份和该精确 HEAD 的五项 CI 结论在交付回复另行记录，
不能用基线 CI 或预期结果冒充本次最终提交成功。

## 基线与下一任务选择

会话从干净 main `cc6e891c07aea9c8d585e80e2a14eff3b98b32af` 开始；
通过既有本机代理执行 `git pull --ff-only`，exit 0，Already up to date。
D-C 产品提交 `0f8c4df` 及前项验收保持，基线 closure 的
[五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/39886920211)是历史已确认结果。

按[当前计划](../plan/README.md)、[执行总则](../plan/reliability-2026-10-03/00_Execution_Guide.md)、
[政策任务](../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md)及
[前项 P-B](2026-10-22-r07c-requirements-comments-pb/README.md)选择下一片：
D-M-S 已明确保留成功解码后的字符串内容缺口。D-C 后没有本片已经批准的 P-B。
普通“继续”及此前 D-G/D-C 裁决不选择尚未准备的 D-M-P 政策。

本片只准备 PEP 621 两处既有 `Requirement` 失败现场，不扩张到其他 manager 包值、
pip grammar、候选遗漏、listing/framework 或充分证书。不触碰产品、测试、正式工具、
CI、现行规范、schemas、依赖、版本、gold 或旧证据；[521 项基线](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/delivery-baseline.json)原字节保持。

## 交付与具体选择

[提案入口](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/README.md)集中保存：

- [具体 A/B](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/R07-C_pep621_strings.md)、
  [兼容性](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/compatibility.md)和
  [38 项未来验收](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/acceptance-cases.md)。
- [未应用规范补丁](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/spec-proposed.patch)、
  [PROPOSED 决定](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/decision.json)和
  [未发布 issue 草稿](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/spec-issue-draft.md)。
- [当前观察](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/current-behavior.md)、
  [原始结果](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/current-observations.json)、
  [重放收据](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/observation-replay.json)、
  [元数据修复账本](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/metadata-repair.json)。
- [五项目影响](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/portfolio-impact.md)、
  [独立源字节证据](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/portfolio-source-evidence.json)和
  [官方来源与排除边界](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/sources-and-scope.md)。
- [独立设计审阅](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/review-design.md)、
  [文稿检查](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/document-checks.json)及
  [SHA256SUMS](../plan/reliability-2026-10-03/proposals/R07-C/pep621-strings/SHA256SUMS)。

推荐 A：只在原 `project.dependencies` / `project.optional-dependencies` 的真实解析失败，
新增内部 `unparsed_requirement`，同源旧原因优先，部分有效声明、信用和诊断保持。
复用 D-M，把剩余当前已知使用、未获信用的关键包保守置为 SKIPPED/INFO；
不从坏字符串猜名称，不复解析、不加读取或新规则分支。

具体成本是全仓作用：无关子项目或空白失败字符串也可能使 WARNING→SKIPPED，
孤立门可 exit 1→0。exact/qualified lock 信用、高优先级原因、独立 warning、
suppression、阈值及完整 JSON 合同保持。B 则维持现行为，本缺口继续 OPEN。

精确补丁 SHA256：
`89505a8e74cd84ad3589e0a95cc8749f671446443110fb2a35e6f4745bc6ce9f`。
仅拟新增 §12.3.9 并修既有前向引用；`git apply --check` 只检查，不应用。
独立设计审阅不是维护者政策批准。

## 实际本地证据及更正

24 组当前输入在产品调用前预写指定投影；前置另有 8 组内存技术微探，
不把后者当作正式冻结观察或声称全部探索前盲测。
两次当前源码观察均 **24/24、exit 0**，候选政策执行数为 **0**。
两次全部业务字段完全相等；只在比较时排除明确列出的执行时间、输入/observer hash、
schema 和 producer version 元数据，不忽略 findings、输入、诊断、读取或来源差异。

首次 `observation-attempt-01` 的证据 `schema_version` 为字符串，违反冻结 D-39／规范 §0。
保留首次 cases、observer、raw、freeze、command 和旧公开文稿原字节；
只修正证据版号为整数并补 producer version 0.7.0，不改独立预期、文件输入或产品调用。
在 `2026-10-23T03:13:39.662737+00:00` 重新冻结后执行 `observation-attempt-02`：
observer 0.238529 秒，命令 0.434740 秒；公开 raw 与第二次私有原件字节完全相同。
这次重核明确归因于版本元数据修正，不抹去首次缺陷，也不称只有一次运行。
首次观察器／命令分别为 0.226432／0.358752 秒。失败观察数 0。

首次公开复制前另有两次路径 regex 误报，均保留原收据：
将 JSON 转义换行及 HTTPS 内的 `s:/` 误识别为盘符。
修正为检查已解码字符串及 token 边界，增加正反例；不是产品失败或重写业务结果。
早期未完成的补丁生成计数断言／私有临时目录创建失败均在正式产品调用前停止，
没有产品修改或遗失原件；补丁交叉引用／export 措辞草稿另存私有历史。
独立审阅将“省略 SKIP/notable warnings”澄清为“仅列 WARNING/CRITICAL；变成 SKIP 的旧条目不再列出”，
明确不删除无关 notable finding；精确补丁及决定摘要已同步。
这些准备修订不被计为通过的产品验收。

真实 `RepoScanner` fallback、依赖提取、Python 扫描、上下文和规则被调用；
`installed_versions` 唯一环境接缝固定为 `{}`，GitInfo 为非仓库输入。
只断言预写字段；其他完整观察不能事后升格为 gold。
未执行 CLI、engine、profile detection、init/export 或未来政策。
`check()=[]` 不是已验证 CLI PASS。网络及重依赖导入由观察器 hook 阻止。

五项目执行 59 条只读 Git 命令，均 exit 0／stderr 空；读取前后 pins/origin/clean 核验通过。
12 个来源逐项绑定 pin blob 与工作字节，其中 8 个受支持声明文件，4 个 setup 边界文件。
独立定位、TOML 解码并解析 **163 条** PEP 621 字符串：
lm-eval 98、LlamaFactory 31、FastChat 34、其余两项目 0，全部成功。
因此五项目完整输出预期零差异是 **PREDICTED_NOT_EXECUTED**，
不是本轮 Gate A PASS；未来仍须 synthetic 坏值分支和 fresh 五项目验收。
来源命令原始流只在内存检查，公开归档其长度/hash，不虚构另有原日志。

## 按验证流程收尾

本次类别为 **DOCUMENTATION_ONLY**，依据
[验证流程 §3–5](../plan/validation-workflow-2026-10-13.md)及 [val.md](../../val.md)。
`.py.txt` 是当前观察证据文稿，不是正式运行工具／测试扩展；
元数据修正也不改变产品或新增可执行工具。

文稿最终检查覆盖：本包与报告／三处导航的链接及锚点、严格 JSON、
整数 schema／producer version、观察器语法、冻结输入与原 raw SHA、
两次业务相等、独立来源计数及 hash 绑定、规范补丁检查、
521 个受保护文件、隐私正反例与已知本机标识排除、
包内 SHA256SUMS／Git 暂存字节完整性。
具体范围及最终输入 hash 见 document-checks；清单不包含自身摘要，避免自引用。
统一 diff 文稿内合法的空白 context 行被默认暂存 whitespace 检查识别为尾空白；
保留补丁原字节，不删除必要 context 标记。其他文稿使用默认严格检查，
仅补丁文件关闭 blank-at-eol／blank-at-eof 项，并独立通过 `git apply --check`；
这项格式处理不改变规范补丁或已审阅政策。

| 门 | 本轮状态 | 依据 |
|---|---|---|
| 文稿一致性／证据检查 | PASS，收据见本包 | 实际文件核查；不表示候选政策通过 |
| 本地完整产品质量门 | NOT_APPLICABLE | 纯提案，产品／测试／工具／规范未改 |
| fresh 五项目 Gate A | NOT_APPLICABLE | 只读来源审计不能代替产品验收 |
| 资源 Gate B | NOT_APPLICABLE | 普通 P-A，未完成里程碑、未准备发布 |
| 精确推送 HEAD 五项 CI | 交付时另核 | 不能用历史 cc6e891 CI 或计划预期替代 |

报告、导航和收据是本片文稿；无受影响生成产品文档，不触发 schema/quickstart 重新生成。
未来 38 项验收是设计，不是测试执行数，也不与当前 P01–P24 同号映射。

## 资源阻塞与下一步

[资源账本](pending-resource-validation.md)状态不改：
VAL-R01 `948d164`、VAL-R02 `75d1b0` 是各自候选的历史结果，未重新绑定；
VAL-R03 五份原始 metadata manifest 缺失、账本最近 authenticated HF 小文件预检 403，
本轮不重试受限服务、不把本地成功充作资源通过。
A02 真实独立反馈 PENDING；A03 身份、角色、组织及提交授权仍待提供。
未使用 GPU、付费 API，不对外发帖／提交申请，不发布版本。

具体接受 **D-M-P A 及上述精确规范补丁和全仓保守成本** 后，才进入 P-B：
先补回归 RED → 最小实现／GREEN → 受影响 lint/type →
一次最终完整质量门 → 五项目 fresh Gate A、init/L1/default export 与受影响验证 →
提交推送 main 并确认精确 HEAD 五项 CI。
其余 R07-C 范围继续 OPEN，不将本片准备记为整项完成。
