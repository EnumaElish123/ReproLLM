# R07-C：已关联格式锁的有限结构提取失败（局部 D-S）

状态：**PROPOSED / P-A**。基线 `603883fd8b7c7be2eac42d335a182ff654f93918`。
正式源码、规范和验收测试补丁均未应用；本材料不代表 P-B 验收或政策接受。

## 问题与具体下一步

R07-C 局部 A、profile-absence P、D-L 和 D-F 已交付。D-F 产品提交
`14560ca91b858c1e2bba6bc01dbd48d45bbb9875`，最终 main `603883f` 的
[五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/39552891340)全部成功。
原三处用户修改保留，不纳入本轮。

现[规范 §12.3.4](../../../../01_specification.md#1234-known-associated-format-lock-body-failures-r07-c-d-f)
明确把错误结构、部分包名提取列为 OPEN。当前解析器可以成功解码，随后忽略错误容器或条目，
只保留部分名字并记 `read_issue=None`。例如同目录 `[project]` 声明 `torch>=1`，
`uv.lock` 的 `package = false`，或有一个无 name 的条目，当前结果仍为未锁定 WARNING。
修复该锁的结构可能给出 torch 的现有合格信用，所以“已证明缺少 pin 证据”并不成立。

下一批建议只处理四个已捕获格式锁的**有限容器和条目结构**，不扩成完整格式验证，
不进入一般 manifest/requirements、listing 或框架覆盖。具体源码位置与指纹见
[源码边界](source-boundary.json)，完整[实现补丁](implementation-proposed.patch)仅修改 `core/deps.py`。

## 推荐 D-S 合同

内部 `LockReadIssue` 增加固定 `invalid_structure`。旧 safe-read 的 `unreadable`
及原捕获 decoder 异常的 `invalid_syntax` 优先，拒绝后的内容不重读。

| 格式 | 保留的空/缺失行为 | 新的已知结构失败 |
|---|---|---|
| uv.lock、poetry.lock | 缺少 package 或 package=[] | 存在的 package 不是 list；任一列表项不是 mapping 或没有非空字符串 name |
| Pipfile.lock | 根 mapping；缺少 default/develop 或空 section mapping | 根不是 mapping；存在的 default/develop 不是 mapping |
| conda-lock.yml | 解码顶层 None（空 YAML/显式 null）；根 mapping 中缺少 package 或 package=[] | 其他顶层不是 mapping；存在的 package 不是 list；列表项同 TOML 合同 |

显式 `package:null` 和 Pipfile section null 是错误结构，不能等同缺失；
false、0、空字符串、空 mapping 也不能因是假值被当成 package 空列表。
Conda 顶层 None 的旧空值例外保留，不据此声称管理器接受该文件。

列表 name 只要求原字符串不等于空串，不校验拼写、版本、build、hash 或完整管理器 metadata。
非空空白字符串和其他不支持的名字继续原捕获/规范化；Pipfile section 中的名字键和值保持不透明，
包括空键及错误包值也不在本批扩展验证。没有把 `read_issue=None` 升格为完整格式证书。

保留所有原已提取名字，包含混合异常条目时的部分名字。保留全部旧 `unparsed` 文本和顺序，
不新增诊断，不解析 warning 文字推断 typed 状态。None 仍为旧手工/internal 构造默认值。

对固定已采集 in-use 包，现有任一 exact 声明或 qualified-lock 信用仍优先。
包括坏锁已提取的合格成员，不因旁边异常条目撤销已获得的名字信用。
仅对**仍待警告**且有既有 R06-B 合格声明/import 关联的包，借用 D-F 原分支逐包 SKIPPED/INFO。
Python coverage 不影响此分支；D-S 与 D-F 均先于 D-L，后两者原范围保留。
无关联、错误 manager、被近项目或 uncertain barrier 阻断的锁保留原结论。

## 具体 finding 与兼容影响

复用 D-F 原输出，**不改 env 规则源码或 renderer**：

```text
{display} is used; an associated format lock could not be read or parsed, so missing pin evidence is not established
```

```text
Review {display} declarations and associated format-lock files; restore readable, valid lock contents before deciding that exact pin evidence is absent.
```

evidence 先保留原首个声明/否则首个 import，再追加排序去重的合格失败锁逻辑路径，
note 仍为 `{display} associated; lock package contents unverified`。
不新增汇总 finding 或单包 PASS，不授予新锁信用。

| 场景 | 当前 → 推荐 D-S |
|---|---|
| 已关联结构异常锁、待警告包 | WARNING/FAIL → INFO/SKIPPED |
| 同锁已采集成员有合格来源 | 原信用保持；缺失的其他待警告成员才 SKIP |
| 任一 exact/其他合格锁已有信用 | 原结果保持 |
| 无合格关联、合法非成员/空锁 | 原 WARNING 保持 |
| 原 D-F、D-L、Python 空结果 veto | 保持原合同 |
| 孤立 WARNING 或提升为 CRITICAL 的旧 FAIL | 对应门可能从 1→0；其他违规仍计算 |
| severity override / suppression | override 仍仅作用 FAIL；SKIP 保持 INFO，ignore 仍作用所有状态 |
| 默认文本 / export / 完整 JSON | 原可见性保持；文本可能 Findings: PASS 并列 SKIP，export 不列 SKIP 数，JSON 保留未验证项 |

不改变默认 fail-on 值、其他 finding、规则 ID/严重度、锁存在性、使用集合、关联边界或排序。
历史 audit/run/report 字节不改；新读者仍读旧产物，旧读者也能读同 schema 的新 audit，
但状态语义增加本处 SKIP。无持久化 schema 字段/版本、依赖或产品版本变化，无迁移重写。

## 文件、审阅及验收

- [规范补丁](spec-proposed.patch)：§12.2/§12.3 的关联引用、§12.3.4 边界和新 §12.3.5。
- [实现补丁](implementation-proposed.patch)：仅 deps 的 typed reason、有限三解析器和共享名字提取 helper；
  既有 `Declarations` 执行逻辑和 env check 不变。
- [验收草稿](tests-proposed.patch)：先明确变更旧的“错误结构保持 None”测试，其余旧测试保留。
- [CHANGELOG 补丁](changelog-proposed.patch)：Unreleased，记录新范围及保持部分信用。

不修改 engine、registry、scanner/pyscan、redaction、schemas、profiles、默认配置或依赖。
因此不请求新的 D-41 受保护模块批准；若实施需要改变这个边界，须先重新评估。
既有 D-41 审阅不作为新 engine 改动授权。

独立预期与当前观察严格分开。P-A 条件观察仅在独立内存模块执行精确草稿 deps，
注册规则及其 check 不变；每个条件结果的完整 expected 在其执行前由 baseline 和冻结的
包名/路径/原 D-F 字面合同建立，再严格比较完整 JSON，仅豁免根 T-02 metadata。
完整输入、stderr、退出码、真实时间和 source/fixture guard 均保留。
这不是正式补丁应用、测试 RED/GREEN、完整质量门或新鲜 Gate A。

[五项目来源与预期](portfolio/design-expectations.json)逐一核对固定 SHA、origin、干净状态及完整路径集合。
五个固定项目没有四种格式锁，本批新条件均不成立；预期完整 L0/facts、init/L1 和默认 export
与原独立 oracle 相同，gold 不改。原 LlamaFactory 禁止文件、lm-eval 截断诊断、HarmBench 嵌套 exact 信用保留。
源文件缺少锁的事实是影响判断依据，不能把旧结果写成本轮新鲜 Gate A 通过。

接受后 P-B：先应用验收草稿在旧实现上 RED，再应用三份产品/规范/CHANGELOG 补丁 GREEN；
完成受影响 lint/type、安全/fixture 回归；同一最终输入执行一次完整质量门，
然后全部五项目 Gate A，五份 init→L1 和默认 export，并加入结构异常、部分信用、
边界控制与 CLI 阈值的受影响验收。确认最终 main 五项 CI 后交付。
普通政策任务不激活新 GPU/Hub/provider/付费或原生 Gate B；不发布 release/tag/PyPI。

## 已执行的 P-A 观察与独立回读

[条件观察](observations/summary.json)首轮 32 组（29 API、3 CLI），64 workers、224 命令，
32 份完整 JSON 比较全部通过；448 次只读产品 Git 查询与完整来源/夹具 guard 核对。
墙钟 64.027921 秒，命令合计 61.955559 秒。仅独立内存 deps 执行草稿，规则及 check 对象保持。
[实际独立回读](review-actual-observations.json)重新构建全部 32 份预期并严格检查原始结果，未重跑产品。
[portable 独立回读](review-portable-readback.json)验证 379 文件、633 来源映射及全部投影；原始字节和隐私边界明确。
[静态测试矩阵](acceptance-matrix.md)含 109 新例与明确修订的旧 7 例，未执行 RED/GREEN。
[会话报告](../../../../../dogfooding/2026-10-21-r07c-lock-structure-pa/README.md)区分准备停止、P-A 证据及 P-B 待执行门。

## 备选、决定和剩余工作

推荐 D-S。备选是保持当前 bounded WARNING 并明确其证据局限；成本是已知错误结构继续没有 typed 结论。
不推荐将整个坏锁所有成员信用撤销，或所有锁失败都无条件全局 SKIP：前者否定既有正向证据，后者超出来源边界。

具体待决问题：**是否接受此 D-S 范围、完整规范与实现/测试补丁，并继续 P-B？**
见 [PROPOSED 决定](decision.json) 和[本地 issue 草稿](issue-draft.md)。
依据[执行总则 §5.9](../../../00_Execution_Guide.md#5-统一实现与兼容性要求)要求
“不要把本包中‘建议的新行为’当成已经修订的规范”；现 §12.3.4 明确把此分支排除在 D-F 之外。
本轮总体继续开发授权覆盖具体方案准备，不替代这个新合同的接受。

更广依赖/requirements 失败、其他 grammar、遗漏候选/import、listing、README/config/framework
和充分证书继续 OPEN。D-S 交付不能关闭整个 R07-C。
