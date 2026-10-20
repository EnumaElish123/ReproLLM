# R07-C：五项目独立预期与边界

状态：**DESIGN_EXPECTATION_NOT_EXECUTED**。这里只读分析已有完整报告、facts、诊断和固定源码；没有执行未来实现，也没有改写 `val.md`、fixtures 或历史 gold。

来源是 `docs/dogfooding/2026-10-20-r06b/final/`，产品候选 `5d5e104bfc1cc187a00c50448c4a5ca5fa910937`。本次重新核验五个正式 checkout 的 SHA、公开 origin 和 tracked/untracked clean；26 份引用材料逐一与原 `file-manifest.json` 的完整字节 SHA/大小一致。原 engine、pyscan、env 和 exec 实现仍与该产品提交逐字节相同，R07-C patch 尚未应用。

完整资料见 [portfolio-evidence.json](portfolio-evidence.json)、[五项目身份](pinned-identities.json)和 [69 条内建规则逐项比较](all-69-rule-comparisons.json)。后者包含五项目各 L0/L1，共 690 条规则比较；未选择或高于当前 level 的规则明确记为未执行，不擅自补 SKIP。

## 实际覆盖与诊断

| 固定项目 | Python candidates | selected | parsed | count limit | 已知缺口 | 默认 L0 stderr |
|---|---:|---:|---:|---:|---|---|
| lm-evaluation-harness | 816 | 500 | 500 | 500 | count cap 漏 316 | R07-B coverage 摘要 |
| FastChat | 148 | 148 | 148 | 500 | 未见 primary AST 缺口 | 空 |
| LlamaFactory | 311 | 311 | 311 | 500 | 未见 primary AST 缺口 | 空 |
| HarmBench | 123 | 123 | 121 | 500 | 两个已选文件 syntax skip | 空 |
| llm-dp-finetune | 46 | 46 | 46 | 500 | 未见 primary AST 缺口 | 空 |

`parsed` 并非历史 facts 中新增的结构字段。上表由完整 candidate/selected 路径及明确的每文件 AST skip 诊断，按原 `scan_python` 逻辑推得；没有靠模糊 read failure 猜原因。Python 文本读取上限是 512 KiB，既有列表过滤上限是 2 MiB，另有环境/生成目录排除。这里的“完整”仅指这份 eligible primary Python candidate view，不能扩张成整个文件系统、依赖 parser 或 framework 扫描完整。

HarmBench 两个实际 skip 是：

- `baselines/artprompt/jailbreak/baseline.py:9: syntax error; skipped`
- `baselines/artprompt/jailbreak/safe_eval.py:3: syntax error; skipped`

其默认 stderr 为空符合现行 R07-B：只有 candidate 超 count limit 时才显示默认 coverage 摘要；parse-only 缺口仍保留在 facts/verbose。R07-C A 不顺带改变这条诊断合同。

其他域的原诊断也完整保留：HarmBench requirements 的两条不支持项、DP 的 git requirements 项。它们不被偷换成 AST count 缺口，A 也不声称已解决相应依赖解析范围。

## 推荐 A 的精确、有意保守范围

A 只允许 `env.llm_critical_deps_pinned` 和 `exec.profile_detection_mismatch` opt in。在 `applies=true` 且 `check=[]` 时，如果 captured primary Python 结果未观察，或 `parsed<candidate`，原本由 engine 合成的 PASS 改成一条 SKIPPED/INFO。所有非空 finding、原 applicability skip、其他 67 条内建规则和 generated project rules 保持原流程。

已观察但不完整时的固定 message：

```text
Python candidate analysis incomplete: parsed {parsed} of {candidate} candidate files; selected {selected} (limit {limit}); no rule-wide PASS is established.
```

evidence 保持空列表；ID、alias、category、level、fix hint、profile/severity origin 和后续 suppression 流程不改。未观察的内部结果有独立固定 reason；这五个真实项目没有该 Unknown 情况。

A 是**规则级保守 veto**。它不等于证明这些输入只能 SKIP。lm/Harm 当前实际加载的 shipped 检测定义中，AST 可产生 high 的 profile 都已被 effective/resolved profiles 覆盖，且全部声明已有正检测证据。更精细的 B 可以据完整有限义务证书保留这些 PASS，但该通用设计尚未实施；不能硬编码默认三种 profile 并忽略用户 overrides。

## 五项目完整 finding delta

| 项目 | 原 L0（FAIL/PASS/SKIP） | A 的 L0 delta | 原 L1（FAIL/PASS/SKIP） | A 的 L1 delta |
|---|---|---|---|---|
| lm-evaluation-harness | 15 / 8 / 1 | 无 | 35 / 9 / 16 | 仅 profile mismatch：PASS→SKIPPED；PASS 9→8、SKIP 16→17 |
| FastChat | 17 / 8 / 1 | 无 | 39 / 13 / 17 | 无 |
| LlamaFactory | 17 / 7 / 1 | 无 | 36 / 9 / 16 | 无 |
| HarmBench | 8 / 7 / 1 | 无 | 30 / 8 / 16 | 仅 profile mismatch：PASS→SKIPPED；PASS 8→7、SKIP 16→17 |
| llm-dp-finetune | 8 / 7 / 1 | 无 | 23 / 8 / 7 | 无 |

五项目当前 L0/L1 均无 SUPPRESSED。所有原 FAIL 的 severity/message/hint/evidence、其他 PASS、原 SKIP 均完整保留。L0 唯一原 skip 是 `code.submodules_initialized` 的 no `.gitmodules`，与 Python cap 无关。Git 五项 PASS 和 secret-file finding 不受 A 改动；LlamaFactory 原 tracked `.env.local` CRITICAL 尤其保持。

L0 的 critical package finding 全是既有非空 WARNING。A 不额外追加 partial-failure SKIP。对这些固定输入，inventory 没有格式 lock，遗漏 Python import 本身不能创造 exact 声明或 lock artifact，因而已有 known-package warning 不变。**不能泛化为任何已找到 FAIL 都是单调真违规**：一般 R06-B 情形中，未分析 import 可能补足 qualified lock 的 origin 关系，从而推翻原 WARN。该 mixed-scope 问题仍 OPEN。

L1 五项目 `model.adapter_declared`、`model.trust_remote_code_declared` 当前都有已观察信号和非空 WARNING，不在 A 两条目标 rule 内，也不会被本提案压掉。

两条确切新 message：

- lm：`Python candidate analysis incomplete: parsed 500 of 816 candidate files; selected 500 (limit 500); no rule-wide PASS is established.`
- Harm：`Python candidate analysis incomplete: parsed 121 of 123 candidate files; selected 123 (limit 500); no rule-wide PASS is established.`

[expected-A/](expected-A/) 保存全部十份完整 AuditReport 设计预期，未增加任何 schema 字段；除上述两条 finding、对应 PASS/SKIP summary 和既有排序产生的位置变化外，其余全部字段按历史来源保留。`generated_at` 仍是原 baseline 值，用于绑定独立设计输入，不冒充未来执行时间。B 和保持现合同的 C，对这十份报告的预期 delta 均为零。

## 语义、退出码与未来验证

这两处变化不增加 FAIL：critical/warning/info failure counts 全不变，SKIPPED 的 INFO 不计作 INFO failure。因此 `audit --fail-on critical|warning|never` 的退出行为不变。L0 LlamaFactory 仍因原 CRITICAL 退出 1，其余 L0 默认 critical 仍 0；初始化 L1 五项目原本已有 critical failures，默认 critical 仍 1。原 harness 的 `--fail-on never` 仍 0。

默认 renderer 使用现有 SKIPPED/INFO 表示和计数，排序沿用 engine severity/category/ID。R07-B stderr 原文不变。未来 P-B 仍须独立 RED/GREEN、D-41 审阅、最终完整质量门、fresh 五项目 Gate A 和受影响消费者；这份 P-A 阅读不是那些门的 PASS，也未查询新的 CI。历史 gold 不重写；若 A 被接受，未来验证应把上述独立设计预期作为经审阅的新政策解释，并保留旧报告原字节。

## 不能据此关闭的工作

A 不修复非空的 declared-but-undetected profile INFO、used-but-unpinned package WARNING 的 absence 推理，不调整 applies=false 的过强无证据措辞，不保证 dependency/listing/framework/config readers 完整，也不重设计 suppression 或 generated rule 信任。其他 67 条规则“未改”是有界交付范围，不是宣称它们已有全域覆盖保证。

真实 portfolio 缺少 unread/oversize、零可解析文件、Unknown、suppressed scan-dependent rules、omitted import 补足 qualified origin 等输入。它们须用独立 synthetic cases 守护，不能从这五个现有报告臆造通过。内部 coverage observation marker、hook、固定 message 和 engine 分支仍只是未应用的具体提案；本材料不宣布 R07-C 全关闭或实验完整可复现。


## 完整原报告与设计预期路径

下面的原报告均位于现有已提交 R06-B 包；只引用并核验 hash，不复制或重写。

| 项目 | L0 原报告 | L0 A 设计预期 | L1 原报告 | L1 A 设计预期 |
|---|---|---|---|---|
| lm-evaluation-harness | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/gate-a/actual-audit/lm-evaluation-harness.json) | [DESIGN_EXPECTATION](expected-A/lm-evaluation-harness-L0.json) | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/extensions/candidate/artifacts/lm-evaluation-harness/audit-level1.json) | [DESIGN_EXPECTATION](expected-A/lm-evaluation-harness-L1.json) |
| FastChat | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/gate-a/actual-audit/FastChat.json) | [DESIGN_EXPECTATION](expected-A/FastChat-L0.json) | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/extensions/candidate/artifacts/FastChat/audit-level1.json) | [DESIGN_EXPECTATION](expected-A/FastChat-L1.json) |
| LlamaFactory | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/gate-a/actual-audit/LlamaFactory.json) | [DESIGN_EXPECTATION](expected-A/LlamaFactory-L0.json) | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/extensions/candidate/artifacts/LlamaFactory/audit-level1.json) | [DESIGN_EXPECTATION](expected-A/LlamaFactory-L1.json) |
| HarmBench | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/gate-a/actual-audit/HarmBench.json) | [DESIGN_EXPECTATION](expected-A/HarmBench-L0.json) | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/extensions/candidate/artifacts/HarmBench/audit-level1.json) | [DESIGN_EXPECTATION](expected-A/HarmBench-L1.json) |
| llm-dp-finetune | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/gate-a/actual-audit/llm-dp-finetune.json) | [DESIGN_EXPECTATION](expected-A/llm-dp-finetune-L0.json) | [原报告](../../../../../dogfooding/2026-10-20-r06b/final/extensions/candidate/artifacts/llm-dp-finetune/audit-level1.json) | [DESIGN_EXPECTATION](expected-A/llm-dp-finetune-L1.json) |
