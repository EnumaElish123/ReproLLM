# R07-C：格式 lock 中出现的包与 Python 扫描缺口（局部 D-L）

状态：**PROPOSED / P-A**。起点 `9cabdc80ecab7728b1ee08c79fc408dd202a6e28`。
本提案接续已交付的空结果局部 A 与 profile absence 局部 P，不改写其接受记录或历史验收。
本次准备不代表具体政策已接受，正式产品、测试和规范补丁尚未应用。

## 具体问题与下一步范围

[规范 §12.3.1](../../../../01_specification.md#1231-known-primary-python-gaps-bounded-synthetic-pass-policy-r07-c-a)
明确保留非空 used-but-unpinned WARNING，将其进一步分类留作 OPEN。
依赖声明独立于 Python AST 扫描读取，不能声称 Python 的文件上限直接隐藏了 exact 声明。
真实可变的是 R06-B 的 import-origin lock 信用：根目录声明 `torch` 未固定，嵌套项目的格式 lock 含 `torch`，
该项目唯一的 `import torch` 被文件预算排除。当前不合格的 lock 在补读该 import 后可以取得信用，
而现规则使用“全仓至少一处 exact/合格 lock”汇总，根目录包的 WARNING 随之消失。

下一批只处理 `env.llm_critical_deps_pinned` 中这种可能受 Python 缺口影响的非空缺证据结论。
它不是依赖解析覆盖率工程，也不改变 R06-B 的关联或 L0 汇总合同。

## 备选与推荐

| 方案 | 行为和代价 | 判断 |
|---|---|---|
| 维持现行 WARNING | 非空结果保持旧合同；已复现的缺失 import 信用反例继续存在 | 可保留为拒绝新政策时的行为 |
| D：缺口下所有待警告包 SKIP | 实现简单，但无格式 lock 的稳定警告也被压低；lm-eval 13 条、HarmBench 5 条现有 gold WARNING 会改变 | 本批不选；需要额外前瞻 gold 审议 |
| **D-L：只对已捕获格式 lock 中出现的待警告包 SKIP** | 先保留 exact/合格信用；用包名集合形成可能信用的保守上界。其他包继续旧 WARNING | **推荐**；规则内有界变更，五项目预期零差异 |
| 精确检查每条未解析路径能否新增关联 | 可进一步减少保守 SKIP，但需要逐路径覆盖、潜在 owner / barrier 与资格证书设计 | 后续独立方案，不混入本批 |

D-L 只在原规则已选中的 in-use canonical 包中处理，lock 条目本身不会创建“使用了该包”的结论。
原 qualified-lock 或任一 exact declaration 先获信用并继续原路径；剩余包同时满足以下条件才逐项 SKIPPED/INFO：

1. 既有 typed primary-Python coverage 为 incomplete 或 unavailable（包括未观察/不一致计数）。
2. 包名在已采集的 `uv.lock`、`poetry.lock`、`Pipfile.lock`、`conda-lock.yml` 至少一个包集合中。

其他包和完整视图均保留原结果。requirements 闭包 lock 不参与新条件；它的信用和 exact 声明独立于 imports。
新结论的完整 message、fix hint、使用证据和去重排序的 lock 路径证据均冻结在
[规则补丁](implementation-proposed.patch)与[规范补丁](spec-proposed.patch)，不是泛化接口提案。

## 有界证明与保守代价

`Declarations.qualified_lock_packages` 的 requirements 信用和配对 manifest 声明信用固定；
imports 唯一能新增的格式信用，必须满足包名属于某个被配对 lock 的 `packages`。
因此，在**固定已捕获依赖视图**下，新增 imports 能增加的信用是已捕获格式 lock 包名并集的子集。
原本缺 exact/合格信用且不在该并集中的包，不会单靠补读 Python imports 获得信用，继续原有界 WARNING。
这不证明所有依赖文件、包使用或格式包名都已被完整读取。

新条件使用的是宽上界：即使 lock 没有有效配对、属于另一 manager、被较近项目或 uncertain barrier 阻断，
只要已捕获包名仍可能保守 SKIP。它没有获得信用；也没有建立它实际可用于该 import 的证明。
新 message 只陈述扫描缺口、已捕获 membership 与本政策不建立缺 pin 结论，避免错误宣称所有条目都能取得信用。
完整视图保留这些情形原有 WARNING。

读失败/格式错误的 lock 若没有采集到该包名，仍保留原有界 WARNING；这个明确限制不以 Python coverage 掩盖。
独立依赖解析、listing、framework、README/config 完整性与更广充分证书保持 OPEN。

## 兼容性与禁区

- Rule ID、class 默认 WARNING、CLI fail-on 常量和所有 schema 版本不变；只增加已有状态的逐包 SKIPPED/INFO。
- 新 SKIP 不接受 FAIL-only severity override；孤立 WARNING 或被提升的 CRITICAL 门可能从 exit 1 变 0。
  同列表其他包的 WARNING/CRITICAL 保留；suppression 继续适用于全部状态。
  孤立警告变 SKIP 后，默认文本可能显示 `Findings: PASS`，同时显示 skipped 计数并提示 `--show-skipped`；
  默认 export 会移除该 notable WARNING 并显示 0 warning / 0 passed，但不显示 SKIP 计数。
  完整 JSON 保留未验证条目。这沿用现有显示合同，本批不改 renderer。
- 空结果 veto、无 critical 包的 applicability skip、profile P、Git/安全等规则不变。
- 不改 engine、registry、deps、scanner/pyscan、redaction、schema、profile 默认表、依赖或版本，不扩大内容读取或扫描预算。
- 不修改上游输入、历史报告、`val.md` gold 或原政策快照；不发布 tag/release/PyPI。
- 不激活 GPU、Hub 或付费 API。本轮不是新里程碑或发布；历史资源结果继续绑定原候选。

## 验收与批准后执行

P-A 先冻结输入/语义预期，比较旧实现与只在进程中替换该 check 方法的条件观察。
保留真实时间戳和原流，完整 JSON 只按 T-02 处理根 metadata，不把条件输出复制成 gold。
五项目影响预写基于固定源路径、完整既有报告/生成文件和格式 lock 缺失证据，不能冒充 fresh Gate A。
测试补丁只做 AST 3.10、Ruff/format、apply-check；没有运行拟议测试或宣称 RED/GREEN。

接受本具体 D-L、规范及规则补丁后执行 P-B：

1. 应用测试先取得预期 RED，再应用已接受的规则、规范及 CHANGELOG 补丁取得 GREEN。
2. 定向回归及 lint/type 检查；最终输入执行一次完整质量门，保留失败再诊断的实际记录。
3. 五项目 fresh L0、受影响 L1/init/default export 及真实 500/501 隔离反例，比较完整 findings、证据、诊断和生成文件。
4. 同候选三门通过后归档、提交、保护 main 原三项 WIP，推送并确认实际最终 main HEAD 的五项 CI。
5. 原 P-A 决定保持 PROPOSED 快照，具体接受另立 sidecar；不会因此关闭整个 R07-C。

## 实际准备证据

- [隔离对照](observations/README.md)：40 次 worker、20 份完整 JSON 比较首轮通过；15 API、2 明确标记的内部 coverage、3 CLI 输入各运行 baseline/conditional。
  实际时间戳保留，仅豁免 T-02 根字段；完整 expected 在对应 conditional 之前，由 baseline 与预先冻结的逐包变换派生。
  conditional 不提供 expected 业务值。CRITICAL 门 1→0、混合 WARNING 门 1→1、suppression/never 0→0。
- [观察读回](observations-readback.json)：170 文件、390 原来源，完整输入重建与 280 次只读 Git 查询核验；未修改产品或执行测试。
  API read/parse 缺口实际为 candidate=selected=1、parsed=0、limit=1，没有文件数 cap；另将预算内 parse gap / 空默认 stderr 补入未执行 CLI 测试草稿。
- [五项目来源与预写影响](portfolio/README.md)：完整 Git 路径与既有 analysis facts 均无四种格式 lock；210 份来源、完整 L0/L1/facts、15 初始化文件与五份导出绑定。
  五项目零差异是独立预写设计结论，不是本轮 fresh Gate A。
- [31 项验收测试草稿](tests-proposed.patch)及[静态资格](tests-static-qualification.json)：11 个新函数、两个现有模块，旧函数 AST 不变。
  AST 3.10、Ruff/format、apply-check 通过；未运行拟议 pytest，未宣称 RED/GREEN。
- [初步源码/规范复核](review-source-spec-initial.json)保留最初身份；最终综合复核另列，不以静态观察替代 P-B 完整质量门。

## 决定依据

执行总则 §5.9 明确要求“不要把本包中‘建议的新行为’当成已经修订的规范”。
现 §12.3.1 与原 A/P 接受记录均明确保留/排除本分支，因此需要接受本具体修订。
本批没有触及 D-41 的 engine/redaction/schema，不额外请求该受保护模块批准。
