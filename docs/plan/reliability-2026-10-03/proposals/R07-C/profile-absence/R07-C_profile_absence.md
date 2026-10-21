# R07-C 接续：已声明 profile 的缺证据结论

日期：2026-10-21。源码 / 规范基线：`bb98e67c6e108822c62842d738f42af2eda871e4`。
状态：**P-A，PROPOSED；规则、规范及测试补丁尚未应用**。
本材料承接已交付的局部 A，不重新打开其决定，也不将它扩成广义 B 的授权。

## 1. 当前进度与本批范围

S1–S4-B 工程任务和 R06-B、R08-A、R08-B A4 已交付。R07-C 的
[既有具体接受](../decision-accepted.json)只覆盖两个规则在 check=[] 时的 synthetic-PASS veto；
原记录明确保留非空 absence findings、listing/deps/framework 和充分证书为 OPEN。
本批只处理 `exec.profile_detection_mismatch` 的 **declared-but-undetected** 分支。
其他规则及该规则正向高置信度分支保留。没有新增任务 ID。

当前规则先逐项检查声明的非 core profile：未出现在 detection 列表就产生 INFO FAIL；
随后检查 high / shipped 且未包含在 effective declarations 中的 profile，产生有具体检测证据的 FAIL。
引擎原样接收非空列表，既有 empty-result hook 因此不能消除前一种缺证据结论。
同一输入将唯一 vllm import 从 cap 外纳入扫描后，原 absence FAIL 可变为 PASS；
“找到了违规见证”和“没有找到支持声明的信号”需要不同处理。

## 2. 推荐的局部方案 P

只在原 first-direction 分支已经确定 `profile not in detected` 后，复用现有 typed
`ctx.pyscan.coverage().pass_skip_reason()` 的 None / 非 None 判断。
只读取其完整性判定，不解析 warning，也不复制其“no rule-wide PASS”文案。
未观察、计数不一致或 parsed<candidate 时，对该 profile 显式输出一条 SKIPPED/INFO；
有效完整视图仍保留原 INFO FAIL、message、evidence。core 仍隐式排除。

新 finding 的完整合同：

- ID `exec.profile_detection_mismatch`、aliases、category、ctx.level 和当前 fix_hint 保持。
- status `skipped`，severity `INFO`，severity_origin `default`；其余 origin / suppression 字段使用既有默认值。
- message 模板：

```text
declared profile {profile!r} has no detection evidence in the analysed inputs; Python candidate analysis is incomplete or unavailable, so absence is not established
```

- evidence 只有一个既有 field item：kind=`field`、field=`experiment.profiles`、note=`{profile} declared; detection absence unverified`；其余字段保持模型默认值。
- known gap 与 unavailable 使用同一模板，不新增持久化 counts、状态、schema 字段或版本。

每个声明仍按原顺序排序处理，之后继续运行正向 high / shipped 检测分支；
不得因为一个 absence SKIP 返回整个规则。混合列表可同时包含 SKIPPED 和真实 FAIL。
引擎最终 severity/category/ID 排序、空结果 veto、applies=false、规则选择、fail-on 阈值定义均不改。
已有 dependency / README / 自定义检测见证使 profile 出现在 detected 时，不会生成该 absence finding。

这是有意保守的**规则内政策**。它也会覆盖当前 loaded detect 不依赖 Python、甚至空 detect 的
未检出 profile；本轮不建立逐 profile 输入充分证书，不硬编码 shipped profile 的信号集合。
parsed=candidate 只表示既有 eligible primary-Python 视图完整，不证明其他读取域完整，
也不证明声明的实验实际执行或整个仓库不存在某能力。完整视图仍保留旧有有界 absence 合同。

## 3. 退出码、覆盖和抑制代价

既有 engine 只向 FAIL 应用 profile severity override。新 SKIPPED 因而始终 INFO/default；
若用户原来把本规则提升为 WARNING / CRITICAL，且没有其他触发项，缺证据场景可能从 exit 1 变为 0。
这属于提案明确改变的行为，不能用默认 INFO 不触发默认 critical 门掩盖它。
真实 high/shipped 未声明分支仍是 FAIL，继续接受相同 override，混合场景仍可 exit 1。

既有 ignore/suppression 对所有 status 继续生效：匹配的 FAIL/SKIPPED 都成为 SUPPRESSED/INFO，
保留原因、追加原 ignore evidence。summary 从 info failure 减少、skipped 增加；如原 finding 被提升，
对应 warning/critical failure 减少。suppression 的 message / field evidence 仍反映各自原结果。
规则 ID、默认 severity、CLI 默认阈值和 schema 不变；读者可继续使用现有严格模型读取新结果。
历史报告字节不改，新候选使用新政策解释新运行的审计输出。

## 4. 选择与限制

| 方案 | 行为 / 代价 |
|---|---|
| **P（推荐）** | 只对这个 nonempty absence 分支保守 SKIP；保留正向违规。改动小、无 engine/schema 变化，但会放宽部分用户提升后的门，且不提供输入充分证书 |
| K：保持现状 | 继续报告有界 INFO FAIL；用户提升 severity 后仍可能因未分析的信号误触门，需依靠原诊断解释 |
| C：逐 profile 充分证书 | 可在确实不受遗漏 Python 影响时保留结论；需要覆盖实际 loaded overrides、特殊 Trainer/framework 信号及非 Python 域，留待独立设计 |

本批不处理 `env.llm_critical_deps_pinned` 的 used-but-unpinned absence、格式 lock 新来源信用、
listing/stat/2 MiB 过滤、dependency/parser/framework/README/config 完整性、signal-aware 证书或新全局 hook。
本批完成也不能勾选整个 R07-C 为关闭，不触发 release、paid API 或新 native/GPU 验收。

## 5. 具体改动与兼容性

[规则 patch](implementation-proposed.patch)只改 `src/reprollm/rules/exec_.py` 的 import 和原 first-direction 分支；
[规范 patch](spec-proposed.patch)修改 §12.3 / §12.3.1 并新增 §12.3.2；
[CHANGELOG patch](changelog-proposed.patch)记录新政策及门的可见变化。
测试草稿单独保存，不在 P-A 应用到正式 tests。

engine、registry、pyscan、redaction、schemas、profiles、依赖及版本不改，故不新增 D-41 敏感文件补丁。
若实施时需要改变这些范围，重新评估其具体审阅要求。既有 D-41 接受不作为新引擎改动许可。

| 写入 / 读取 | 解释 |
|---|---|
| 旧 AuditReport → 当前 / 新读者 | 既有 schema 和原字段可读，不重写旧结论 |
| 新结果 → 当前 schema 读者 | 仍是已有 FindingStatus.SKIPPED、INFO 和 field evidence，无额外字段 |
| 新审计 → 默认 export | 使用同一规则结果；在受影响合成案例检查 summary 变化，五项目常规预期不变 |
| 新审计 → CI / 用户 override | 阈值常量不改；新 SKIP 不再作为可提升的 FAIL，正向 FAIL 仍可触发 |

## 6. 验收与执行分界

P-A 完成源码核对、独立预期、当前 / 条件观察、静态补丁资格、五项目预写影响与独立复核。
条件运行仅在进程内替换单个规则类，候选源码与规范保持未变；它不是已实施 P-B、fresh Gate A 或资源验收。

P-B 具体接受后，先在旧实现运行接受测试证明 RED，再应用接受补丁，定向 GREEN；
最终候选只运行一次完整 quality，随后五项目 fresh L0 Gate A、一次性 init→L1 与受影响 default export。
完整 findings/profiles/hints/路径/诊断/manifest/export 逐份比较，不用 summary 相同代替完整结果。
缺证据与正证据混合、不可读 / 解析跳过、zero candidates、unknown/invalid counts、用户 loaded signals、
多个 profile 排序、WARNING/CRITICAL 提升门、suppression、重复 JSON / 默认诊断 / schema / 只读均须覆盖。
最后提交推送 main，并确认实际最终 HEAD 的五项 CI。既有资源成功和阻塞保持原候选归属。

## 7. 待具体决定

问题：是否接受 **P 的 declared-profile absence 局部政策、具体规则 patch 和规范 patch**，并按此实施 P-B？

需要这一决定的依据是[执行总则 §5.9](../../../00_Execution_Guide.md)对规范冲突的明确要求：
现行 §12.3.1 仍保留 nonempty absence FAIL；原[接受记录](../decision-accepted.json)也明确不授权 broader B。
本次不是重复请求既有空结果政策的许可，也不要求新的 engine D-41 审阅。
具体材料、观察与最终哈希由本目录决定记录和会话报告索引绑定；其他任务不因该子项待决而改写状态。

## 8. 已完成的 P-A 材料

- [40 次条件观察与完整比较](observations/results.md)、[原始结果汇总](observations/summary.json)和[完整读回](observations-readback.json)：32 API＋8 CLI 真实观察、20 份 strict 完整 JSON，无字段豁免；另保留 1 次进入 CLI 前的 launcher 失败。
- [五项目零差异设计及完整来源](portfolio/README.md)：71 份仓库来源、36 份固定上游来源、105 个检测见证逐一核验；143 个产品文件中仅先前接受的 diff 默认表与旧执行候选不同，审计 / 检测 / init / export 字节相同。
- [18 项测试草稿](tests-proposed.patch)及[静态资格](tests-draft-qualification.json)：Python 3.10 AST、Ruff/format、apply-check；未运行拟议 RED/GREEN。
- [独立最终复核](review-profile-absence-final.json)、[条件观察独立读回](review-profile-absence-observation-readback.json)：无未解决问题。
- [具体待决记录](decision.json)绑定四份最终补丁哈希；[可转 issue 草稿](spec-issue-draft.md)未对外发布。

API 的精确 expected JSON 在两个 worker 后落盘，但只读取 baseline 并执行观察前冻结的政策差分映射，
不使用 conditional 输出生成预期；CLI 补段则在 conditional 前落盘。两者的实际时点在证据中明确区分。
40 次产品 worker 的退出码与单次耗时均保留；20 次纯比较器调用的耗时未采集，不推算为已知。
