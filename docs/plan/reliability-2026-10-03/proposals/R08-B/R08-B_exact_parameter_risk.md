# R08-B：四个有实际来源的自由参数精确路径

状态：**PROPOSED，尚未接受或应用**。日期：2026-10-20；基线 `30dc9cae41b2fbcc1657357eff34b3e5a7f26322`。
本批为 [05 §7](../../05_Policy_and_Compatibility.md#7-r08-bprivacy--training-自由参数风险分级) 的 P-A。
当前产品遵循现行规范，并非实现违反规范；P-B 须先取得对具体政策、规范和前瞻 gold 的决定。
[决定记录](decision.json)不将概括的“继续开发”视作默认表的新批准。
R07-C 更广范围、发行、付费 API 和重新执行原生训练均不在本提案中。

## 1. 当前事实与有界清单

[privacy 清单](inventory/privacy/README.md)覆盖 16 个实际 privacy/custom 路径、6 类排除项和 41 个来源。
[training 清单](inventory/training/README.md)核对 20 份实际 manifest（4 examples、6 fixture、10 个五项目 A/B 快照）及 42 个来源。
这是有界语料清单，不声称覆盖任意自由字典中的所有可能字段；schema 接受任意键不等于它们都有共同实验含义。
源文件均有固定提交、相对路径、SHA-256、物理行号和原 Git blob 字节校验。

当前 `*` 只匹配一个点分 segment，first-match 生效，未命中为 MEDIUM。
`training.*` 与 `privacy.*` 不覆盖深层 params；实际内置 privacy/finetuning profile 没有覆盖它们。
这里的四个精确叶子均为 MEDIUM，不因 config 文件的独立 HIGH 哈希变化而成为 HIGH。

| 精确 manifest / State 路径 | 实际声明与调用来源 | 当前 | 推荐 A4 |
|---|---|---|---|
| `privacy.mechanism.params.target_epsilon` | DP manifest:33 的 8→4；config binding:43；`PrivacyArgs.target_epsilon` → 原生 engine 参数 | MEDIUM | HIGH |
| `privacy.mechanism.params.target_delta` | 同 manifest:33 的 0.001；归档 entry 映射；原生 `language_model.py:449` | MEDIUM | HIGH |
| `privacy.mechanism.params.max_grad_norm` | 同 manifest:33 的 1.0；entry 将其传给 `PrivacyArgs.max_grad_norm_dp`，再传 engine `max_grad_norm`（:446） | MEDIUM | HIGH |
| `training.params.num_train_epochs` | 同 manifest:28 的 0.125；entry 显式赋值；engine `epochs=train_args.num_train_epochs`（:445） | MEDIUM | HIGH |

实际来源为 [DP manifest](../../../../dogfooding/2026-10-20-validation-followup/native/runtime/llm-dp-finetune/a/run/manifest.yaml)、
[原生固定调用](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/models/language_model.py#L441)、
[固定 PrivacyArgs](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/arguments/privacy_args.py#L7)。
机器清单进一步绑定归档 entry 的内容地址、源行及实际值，不把未声明的 binding 凭空补上。

推荐按四条精确路径分类的理由是：epsilon / delta 指定隐私意图，clipping norm 指定裁剪尺度，
epoch horizon 在本例参与噪声校准，均有真实记录和活跃代码来源。HIGH 表示重新比较时应注意这些记录值的变化，
**不计算 DP 保证，不证明值已被 child 消费，也不承诺任意改值都改变输出**：

- 显式非空 `noise_multiplier` 可以绕过 epsilon 校准；相关分支可见[固定 fastDP 实现](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/privacy_engine.py)。A4 不增加条件求解。
- `max_steps` 可限制实际训练步数；本例的 epochs 仍传给 PrivacyEngine 校准。不能用未被 scheduler 使用的 `t_total` 计算证明实际步数变化。
- `training.epochs` 当前 schema 为 int，概览草图写 number；既有案例用合法自由字段表达 0.125。本批不修类型、不建立 alias、不迁移值。
- 历史独立消费 receipt 直接记录 epsilon、target_delta、epochs；max_grad_norm 的证据是配置、entry 映射、活跃调用及 clipping 执行，不能写成直接记录了 constructor 中该值。

## 2. 推荐与备选

**A4（推荐）：只新增以上四条默认 HIGH 精确行。** 不改 matcher、State、profiles、继承、schema、audit 或 run 捕获。
[默认表补丁](default-proposed.patch)在相应较宽行之前逐条加入，不引入任何新 wildcard。
值类型、空值、字典展开和 list 原子语义沿用 State：只对实际产生的精确叶子分类；深层同名前缀不是新匹配。

**B：只增加 target_epsilon 一条 HIGH。** 其余三条维持 MEDIUM，可分别延期。此选项需在 P-B 前生成与该决定一致的完整补丁和验收材料，不混用 A4 的四行补丁。

**C：四条都保持 MEDIUM。** 清单仍可交付；不产生本轮默认行为变化。

以下均保持原合同：`privacy.mechanism.params.delta`（orthogonal_noise 示例的 1.5 是隐藏状态偏移，不是 DP δ）、
`alpha` / `safe_interval` / `orth_loss`、`custom.*` 的深层字段、其他 training 自由键、日志/资源/输出位置。
`noise_multiplier`、`max_grad_norm_dp`、`per_sample_max_grad_norm` 等实际源码键不自动成为 manifest alias。
后者仅出现在已注释的旧实现中；源码有一个键不等于本工具有对应路径。
已接受的 judge 直接参数 HIGH、typed training 字段和其他现有默认不变。

## 3. 输出和兼容性

对只有一个目标叶子变化的比较：changed / added / removed 的 severity 从 MEDIUM 变为 HIGH，完整 summary、
文本分组及过滤相应变化。记录的 a / b 值、状态、来源说明不变。未传 `--fail-on` 仍 exit 0；
显式 `--fail-on HIGH` 从 0 变 1。effective LOW / NONE override 后仍遵循现有 first-match 行为。
HIGH 过滤可以隐藏 LOW，但完整 summary / fail-on 不能被显示过滤掩盖；self-diff 仍为空。

用户在选中的 `.reprollm/profiles/<name>.yaml` 中为完整路径设置 `drift_overrides` 即可保持 LOW 或 NONE，
并保留原 profile 内容。继承中同键 child 可替换 parent；不同 pattern 仍按 first-match，
不能承诺“更具体的 pattern 一定优先”。不在 built-in 父 profile 增加宽泛 override。

| 输入 / reader | A4 实施后的边界 |
|---|---|
| 支持旧 manifest1 / lock1 / run1或2 的新程序 | 原输入和来源不改；新计算的四条精确叶子按新默认 |
| 旧程序重新计算它本来支持的输入 | 仍使用其旧默认；不赋予旧 reader 新 run schema 支持 |
| 新旧程序读取已保存的 diff_report1 | 既有字段和 HIGH 枚举不变；历史报告字节不重写 |
| 已选中 profile 的 effective LOW / NONE | 按当前合并 / 匹配顺序继续优先于默认表 |

没有 schema 或持久化枚举变更，无数据迁移或版本 bump 提案。新旧比较须记录产品 commit 和政策，
不能要求同版本号的未发布不同 commit 得到相同 severity。CHANGELOG 必须说明新的显式 HIGH 退出影响。

## 4. 可直接审阅的改动

| 未应用草稿 | 目标文件 |
|---|---|
| [default-proposed.patch](default-proposed.patch) | `src/reprollm/diff/drift_severity.yaml`，四条精确默认行 |
| [spec-proposed.patch](spec-proposed.patch) | `docs/plan/01_specification.md` §18.1 / 18.2，逐路径及语义边界 |
| [tests-proposed.patch](tests-proposed.patch) | `tests/unit/diff/test_severity.py`、`tests/unit/cli/test_diff.py`，独立验收草稿 |
| [changelog-proposed.patch](changelog-proposed.patch) | `CHANGELOG.md`，新默认与显式 HIGH gate 的兼容影响 |
| [gold-amendment-proposed.patch](gold-amendment-proposed.patch) | `val.md` 新增前瞻 §8.3.1；历史正文不改 |

不涉及 D-41 的 engine/redaction/schema 文件，不申请这些模块的新改动。当前这些补丁均未应用。最终根测试补丁补齐独立规则注册与仓库 Ruff 配置资格，见[更正记录](test-draft-qualification/correction-receipt.json)；原 experiments 测试草稿和原审阅保留为准备时记录，不作为最终草稿。
未来若验收发现需要扩大模块/语义范围，先另立具体方案。外部 spec issue 只准备[草稿](spec-issue-draft.md)，未发送。
[Issue #9](https://github.com/EnumaElish123/ReproLLM/issues/9)是 judge 的窄范围议题，不当作 R08-B 批准。

## 5. 独立预期、五项目和 Gate B

先独立冻结四路径 × changed/added/removed 以及邻近/别名/custom/typed/judge controls，再观察当前默认和
公开 SeverityTable 注入的条件 A4。当前 CLI 用标准 run2 合成输入验证读取、过滤、阈值和 profile；
它不是原生训练、child capture 或 P-B 已实现证明。未来 HIGH 默认测试在批准后先取得真实 RED。
完整实验、输入来源和工具准备失败资格见[会话报告](../../../../dogfooding/2026-10-20-r08b-pa/README.md)。

| 固定项目 | 新鲜 Gate A / init 等预期 | 既有 native pair 在 A4 下的完整差异预期 |
|---|---|---|
| lm-evaluation-harness | 全部 findings/profiles/hints/路径/诊断不变 | 无四目标变化，完整 diff 不变 |
| FastChat | 同上 | native generation cap 仍 HIGH；judge 政策保持，完整 diff 不变 |
| LlamaFactory | 同上 | typed learning_rate 仍 HIGH，完整 diff 不变 |
| HarmBench | 同上，保留嵌套 exact gold | generation cap 仍 HIGH，完整 diff 不变 |
| llm-dp-finetune | 同上 | 仅 target_epsilon MEDIUM→HIGH、counts −1/+1 及既定排序；其他三目标 A/B 同值，不新增 drift |

本 P-A 已对保留的五组旧 run 重新投影为 State：current 与条件 A4 各五份完整报告，严格对比预先从不可变
历史报告派生的预期，无字段豁免。**这是当前政策/条件政策对旧记录的 CPU 比较，不是新 GPU 回放**。
历史 epsilon8→4 MEDIUM、config SHA HIGH 和其余原生证据均原字节保留。
前瞻 gold 只在具体接受并实施后生效；未来 native replay 仍须保留所有输入、pin、原生裁剪/噪声/accountant 验收。

批准后的普通 P-B：先验收测试 RED→默认/规范补丁→GREEN；按验证流程一次完整最终质量门，全部五项目
新鲜 Gate A 与受影响 diff 扩展，比较完整报告、HIGH 隔离 / LOW-NONE / 过滤 / self-diff / 确定性。
本策略不改变静态审计/init/export消费者的业务路径；扩展选择依据需在报告明确。
没有新里程碑或 release 时，不为政策-only 工作重跑无关 GPU/付费矩阵；旧资源成功和外部 metadata/HF 阻塞继续绑定原候选。

## 6. 待裁决的问题

是否接受 **A4 四条精确默认 HIGH**、对应 §18 规范补丁及 `val.md` 前瞻补充，按上述边界实施 P-B？
具体接受必须记入决定记录，并与原 PROPOSED 材料分开保留。B/C 也可独立选择，不视为产品失败。
本次提案、源码清单和条件实验本身不把任何默认策略改为 HIGH。
