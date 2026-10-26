# 2026-10-26：当前候选验证补全

产品候选：`6afe8f40ab8d33e191ca0e75c4e5e08a57cabc46`；最近产品任务为
R07-C D-M-PF `ba1415b6905976a38d132198e6d025c64621dbe5`，版本为未发布的 0.7.0。
本轮响应维护者“先处理已经开发完成但是尚未完成完整验证的工作”，补跑当前候选的可执行资源矩阵。
先前静态 P-B 的本地与 CI 验收保持历史身份，本轮实际执行另行绑定上述候选。

质量、五项目、H2、五组原生 GPU A/B、正式 judge A/B 和当前输入 discover 接受流程通过。
VAL-R03 继续 BLOCKED：五份原始 §8.1 metadata manifest 缺失，认证成功后的两份限定小文件仍返回 403。
维护者确认暂时没有原始文件，并要求先完成其余补验。本轮不变更产品、规范、gold 或版本，不发布 release。

## 本轮结果

完整计数、输入身份及独立证据引用见 [session-checks.json](session-checks.json)；
原始收据、比较输入与输出由 [source-index.json](source-index.json) 的 SHA-256 引用。

| 验证层 | 实际结果 | 计时边界 |
|---|---|---|
| 最终本地质量 | 24 项通过；4716 tests PASS、2 slow deselected；security 359 PASS；覆盖率 94.56008267%；redaction 59/59 statements、24/24 branches | pytest 809.20 秒；质量层墙钟 993.208620 秒 |
| 五项目基础层 | 50 命令、31 检查、10 份完整 L0/facts JSON，pin/origin/clean 正确 | 墙钟 85.648153 秒 |
| 受影响消费者 | 130 命令、111 检查；15 份完整 graph/verbose/L1 JSON、5 export、15 init 文件及诊断字节符合独立预期 | 墙钟 224.523219 秒 |
| Linux H2 supplementary | 五项目 × offline/online1/online2，639 检查；15 份完整 lock、15 report、15 stderr 通过 | 控制器墙钟 217.356010 秒；外层 223.993116 秒 |
| 原生 GPU | 10 children、5 pairs、35 个解释清楚的变化、20 export 状态及 1291 项导出比较通过 | 10 个 run wrapper 累计 718.422465 秒 |
| 原生完整审计 | 25 份完整报告、298 项 terminal 检查、84 个 run 文件；195 收据和 390 条原始流保留 | 25 次统一严格比较另有独立收据 |
| 正式 judge | 两次真实 POST，无重试；214 项 terminal 检查、154 项独立导出比较、完整 pair/self 通过 | 外层正式 stage：A 49.984104 秒；B 18.460521 秒 |
| Initialized discover | 五项目离线预览 67 命令通过；一次真实 POST、7 候选审阅、选定规则接受及 5 次严格比较通过 | 预览墙钟 124.313199 秒；provider 约 80.07 秒 |

各层计时不相加作为总会话墙钟。完整命令参数、退出码、原始 stdout/stderr、JUnit、coverage、
比较差异及失败原件保留在外部会话目录，每条命令通过收据及哈希定位。
审计的完整预期保留上游已有的 FAIL/SKIP；表中的验收通过表示结果符合独立预期。

候选构建的 wheel SHA-256 为
`c5b9b56228eff0ab298294440550f0e4acde762d1ca9e6424186486f0cc5cf1d`。
它在 modern Python 3.11.12 与 DP Python 3.10.20 两个已提供环境中安装，
全部 143 个包文件逐字节匹配；其余分别 274、82 个已安装 distribution 保持。
五个原 checkout 均保持 [val.md §2](../../../val.md#2-pinned-portfolio) 的 pin、origin 和干净状态。
45 个模型缓存文件共 48,925,943,574 字节已逐一对照独立完整性清单验证；收尾只核 stat，未重复读取约 49 GB。

## 原生 A/B 与当前政策

| 项目 | 固定 A/B 变化 | 实际验收 |
|---|---|---|
| lm-evaluation-harness | cap 32 → 48，HIGH | 每次 100 GSM8K 文档，实际 vLLM 消费、输出与捕获 |
| LlamaFactory | learning rate 0.0001 → 0.0002，HIGH | 每次两次实际 LoRA 更新、有限 loss 与非零 adapter |
| llm-dp-finetune | epsilon 8 → 4，HIGH | 每次两次 DP 更新、clipping/noise/accountant/权重及 B 更大 noise multiplier |
| HarmBench | target cap 16 → 24，HIGH | 原 target/classifier 顺序、实际参数及分类结果 |
| FastChat | cap 32 → 48，HIGH | 原固定两轮问题、实际本地生成、完整捕获与消费 |

DP 的目标叶独立按 [val.md §8.3.1](../../../val.md#831-prospective-r08-b-exact-parameter-policy-supplement)
验为 HIGH；历史 MEDIUM 记录保持。每组恰好七个已解释变化，self-diff 为空，阈值和完整 findings/profiles 均核对。
20 个导出状态为五个 manifest-only、五个 lock-only 和十个 selected-run。

首次启动前 GPU1 空闲容量已不足，依维护者持续有效的实际容量指示改绑 GPU0；
全部十次实际启动与 HarmBench 四个阶段边界均记录 GPU0，原显存比例、串行与设备锁保持。
没有干预其他任务；收尾设备锁已释放。生成的 HarmBench 文本保留私有，不发布。

## 真实付费路径

正式 judge 原 A 四输入逐一匹配 §8.4；只使用公开 MT-Bench 问题、rubric 和固定合成答案。
本轮新批准上限为人民币 3 元，A 完整捕获及独立导出通过后才执行 B，最多两次请求且无重试。
两次评分观测为 7、8，finish 均为 stop；分数本身不作为 gold。
输入、Python 快照及完整八行 JSONL rubric 保真通过。
完整 pair 为 direct cap HIGH、config hash HIGH、clean commit MEDIUM 和四个 NONE，self-diff 为空，HIGH 门退出 1。
按当日官方峰值价格估算合计人民币 0.002740 元，属于用量估算而非账户发票。

Discover 使用本轮新批准的 4 元预算，保留生产客户端的四个请求字段，只发送一次且无重试。
案例 `DISCOVER-INIT-6AFE-20261026` 的四输入和完整消息逐字节等于 10-20 已接受的 current-input 案例；
较早 §8.6 的三项历史哈希仍不同，本轮不覆盖历史 gold。
公开用户消息为 31,337 字符；一次 HTTP 200、finish stop，usage 为 prompt 8762 / completion 14684 / total 23446。
reasoning 只保留 token 计数。峰值估算为人民币 0.134996 元，未进行第二次发送。

七个候选及其 ID 均独立核对，选入 `c-05faa5` 的 `custom.privacy.target_epsilon`。
实际发送的固定 README 第 99 行明确 ε=8.0；建议绑定对应的固定 YAML 第 40 行为 8，
后者由响应后的源码复核建立，未宣称该 YAML 内容发送给模型。
只在一次性接受副本中显式写入验证意图 8.0，保留候选原 ID、证据、binding 和 CRITICAL 等级。
该规则从缺值 CRITICAL FAIL 变为 PASS；其他 38 条完整 findings 保持，另五条 CRITICAL 使整体阈值仍为 1→1。
重复接受退出 2 且规则文件字节不变；完整重复审计仅根 generated_at 不同。此声明不证明运行消费。
最终精确扫描覆盖 347 个文件，两个实际配置的秘密值均出现零次；81 份产品/审阅文件的规范隐私检查通过。
其余 266 份辅助文件按私有原件保留，其中本机路径/身份不冒充无泄漏的产品产物；最终收据本身另作补充扫描。

## 观察器更正与证据边界

原始失败及更正前代码均保留。Native 首次在 B-before 比对时仍引用历史 A run ID；
只从历史与本轮 typed A RunRecord 导出有限完整路径映射，对同一原报告重比，再从尚未启动的 B run 续跑。
原 native helpers/session 不改，派生观察器另有哈希绑定；全部原生 child 均只执行一次。
Judge 的外部后置守卫误要求 B 后仍只有一条预算记录，修正为阶段对应的一条或两条后只继续只读验收。

Discover 的跨环境预期首次未绑定安装版本；初诊按 rule_id 建 dict 又折叠了同规则的五条发现。
复核恢复完整 38 条有序 findings，仅将五个包的 message/fix_hint 占位由预存及当前安装元数据独立渲染，共十字段。
后续同环境比较无此豁免。原成功 accept/missing 前缀不重跑，剩五命令续跑；
前缀两个单独耗时未在断言前持久化，明确为 null，保留原外层 1.667767 秒，续跑墙钟 4.344357 秒。
25 份 native 报告及 discover 五份比较均使用现行 `scripts/compare_gold.py` 默认严格模式；
actual 比较投影只移除根 generated_at；native expected 另以各 variant 不可变 documents 中的锁字节
独立绑定输入 hash，并按既定八个 typed A 字段绑定运行引用。版本与其余业务字段保持严格。

公开包仅包含本报告、检查摘要与哈希引用索引。完整原件、私有路径、凭据、权重和生成文本均不复制到仓库；
公开哈希不能单独复验未发布的私有正文。最终分享文件另作链接、JSON、内容一致性及隐私检查。
既有 README、docs/index 与 additional-cases-gold 三份用户改动保持原字节，不加入本次提交。

## 尚缺条件与交付

VAL-R01、VAL-R02 的本轮通过均绑定 `6afe8f4`，历史候选及旧失败不改绑。
匿名 H2 只覆盖 supplementary metadata，不能替代五份原始 manifest 或 gated 成功分支。
本轮 HF identity 请求为 200，两份固定 Llama-2 小文件为 403；VAL-R03 仍需原始输入和模型作者访问授权。
独立试用反馈、申请身份/提交及更广 R07-C 后续工作仍分别登记，不据本轮资源成功闭合。

候选的 [五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40108044547)
与 [nightly](https://github.com/EnumaElish123/ReproLLM/actions/runs/40176956921) 已核对精确 SHA、全部 job 成功，
Ubuntu 3.12 schema/examples/generated docs 及 nightly performance 步骤成功。
本次纯报告提交不复跑未改变的产品输入；推送 main 后的精确最终 HEAD 五项 CI 在交付时独立核对。
