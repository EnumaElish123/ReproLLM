# 2026-10-20 · R08-B P-A：实际自由参数与四条精确默认提案

状态：**P-A 材料完成，A4 仍 PROPOSED；产品默认未修改。**
起点 main `30dc9cae41b2fbcc1657357eff34b3e5a7f26322`，与 origin/main 一致。
前批 R07-C 局部 A 已交付；其 [五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/39377406310)
绑定该起点，不当作本次提交的 CI。本批从 [05 §7](../../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md#7-r08-bprivacy--training-自由参数风险分级)
选取 R08-B P-A；没有扩大已接受 R07-C，或重新宣称历史资源完成。

## 交付

[具体提案](../../plan/reliability-2026-10-03/proposals/R08-B/R08-B_exact_parameter_risk.md)准备四条精确路径：
`privacy.mechanism.params.target_epsilon`、`target_delta`、`max_grad_norm`，以及
`training.params.num_train_epochs`。四者来自真实 DP manifest / 配置 / 原生调用，不是将全部 params 提级。
当前等级均 MEDIUM；A4 建议未来新计算 diff 的相应叶子为 HIGH。备选为仅 epsilon 或保留现状。
规范、默认表、测试、CHANGELOG 及前瞻 val 补丁都可审阅，均未应用。
决定仍 [PROPOSED](../../plan/reliability-2026-10-03/proposals/R08-B/decision.json)，不从“继续开发”推导具体新政策批准。

清单的限定语料为 20 份实际 manifest、五个固定上游代码来源和真实 DP 记录。
privacy 清单有 16 条实际路径、6 类排除组、41 个来源；training 清单有 42 个来源，
在其语料中只发现 DP A/B 的 `training.params.num_train_epochs=0.125` 是实际 training 自由键。
两个清单来源重叠，不相加成 83 个唯一来源。原始文件逐 Git blob / SHA256 / 行号校验，
保留实际 manifest 路径、源码键、声明和消费证据的区别。

关键限制：显式噪声可绕过 epsilon 校准；max_steps 和 epochs 的作用层次不同；
max_grad_norm 经 `_dp` 参数名映射，但不是自动 alias。例中 `delta=1.5` 是隐藏状态偏移，
不能当作 DP δ。typed `training.epochs` 当前 int 与概览草图 number 的差异仅登记，未修 schema。
HIGH 是记录值的默认可比性分类，不是 DP 保证、因果证明或 child 消费验证。

## 当前行为与条件实验

[条件实验](../../plan/reliability-2026-10-03/proposals/R08-B/experiments/README.md)先冻结独立输入和预期，再执行当前 State / resolver 与条件 A4 的公开 SeverityTable 注入。
**359 项检查 PASS**：30 组 Manifest→State 用例（4×changed/added/removed 加18邻近控制），
LOW/NONE、真实继承与 first-match、self-diff，以及32条当前 CLI 调用。
CLI 输入是标准 run2 合成记录；没有 child 执行，metadata / argv / 快照一致，单条绑定叶子隔离，
无 config SHA 或 dirty HIGH 掩盖。没有公开 CLI 表注入入口，所以条件 A4 CLI 未执行，
不能把它写成未来默认 HIGH 已验证。草稿 HIGH 测试也尚未作为 P-B 运行。
最终条件观察墙钟29.050435秒，CLI累计14.865207秒。

另将五组原生历史 run2 快照重新投影为 State，current / 条件 A4 各五份完整 diff。
[十份 strict 比较](../../plan/reliability-2026-10-03/proposals/R08-B/portfolio/observation/strict-comparison-summary.json)全部 PASS，
**没有字段豁免**；预期先从不可变历史报告独立派生，未从当前结果复制 gold。
只有 DP epsilon 从 MEDIUM 变 HIGH、对应 counts −1/+1 和原定排序，其他四项目完整报告不变。
另外三条目标在这组 A/B 同值，覆盖来自定向实验，不能冒充已有原生变化对。
[独立复核](../../plan/reliability-2026-10-03/proposals/R08-B/portfolio/independent-review.json)
复算所有完整报告、固定来源、原记录文件指纹和外部完整后置 guard，未运行产品或改写历史。

这些是当前政策 / 条件政策对保留旧输入的 CPU 分析，**不是新原生/GPU执行或新资源验收**。
原生结果继续绑定历史 `948d164`，正式 judge 继续绑定 `75d1b0`。
旧 epsilon8→4 MEDIUM、config SHA HIGH 等全部原字节保留；前瞻补充只在具体接受且实施后生效。

## 检查分类与资格

这是纯 P-A 文稿、数据和未应用补丁会话，没有修改产品源码、实际测试、profiles、schema、
依赖、打包或 CI；保留的 helper 为 inert text。按权威[验证流程](../../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义)：

| 检查 | 本批状态 |
|---|---|
| 文稿链接、JSON/来源/隐私/补丁适用性及独立审阅 | [文档检查 PASS](document-checks.json)：554文件、403份JSON、149本地链接、541原件与11外部源哈希，五补丁合并适用检查通过 |
| 完整本地产品质量门 | NOT_APPLICABLE：不是产品或可执行工具变更，不将历史质量门改作本次 PASS |
| 五项目新鲜 Gate A | NOT_APPLICABLE：无产品字节变化；五份旧 pair 的条件比较单独登记 |
| GPU / provider / Hub / release Gate B | NOT_APPLICABLE：没有触发新里程碑/发布或资源执行 |
| 具体政策 / 前瞻 gold | PROPOSED，尚未实施 |
| 精确推送 HEAD CI | 交付时单独核对，不由前批 CI 推断 |

环境以 locked/offline dev 安装，观察器验证当前模块 origin 和源哈希。main三份用户 WIP 仅保留哈希，
未复制其内容；工作在隔离 worktree。全部正式 checkout 的输入只读，没有凭据或私有数据读取。

准备失败全部限定为工具接线：条件实验首次缺规则注册，随后使用不支持的 `python -m reprollm` launcher，
均进入0条产品 CLI；原件/安全投影/哈希与日志缺口如实保存。另一个五pair观察器也先因未注册catalog停止，
未生成当前实际结果；补启动后使用新目录。其首 traceback 仅在工具响应中，没有虚构原始 stderr 文件哈希。
外部后置检查进一步验证完整7562文件集合、字节 inventory、HEAD 和 clean，补齐 denial hook 内的受限 guard。

初版 future 测试草稿有两个静态问题：focused 继承测试未明确启动规则包、scratch Ruff 没有绑定仓库配置。
最终根补丁补齐公开 bootstrap 并使用仓库配置核验；初实验草稿及原审阅原字节保留，最终补丁和收尾资格记录明确其替代关系。
没有把改格式/启动条件写成产品 bug 修复或未来 HIGH 的测试成功。完整旧测试文件中的既有合成绝对路径 canary 不重复归档；保留最终 diff、固定 base 和完整目标哈希，可重建目标，见最终草稿的 retention 资格。

## 接续

下一步为对四条路径、具体 §18 规范及前瞻 gold 的逐项裁决。A4 接受后：
先将验收测试补成真实 RED，再只应用接受范围，获得 GREEN，运行一次完整最终质量门，
五项目新鲜 Gate A 和受影响 diff 扩展，提交推送 main 并核对精确 HEAD 五项 CI。
获准的 LOW/NONE 与现有匹配/继承保持；不新增 alias、递归匹配、自动消费证明或 schema。
没有授权发布、付费请求或对外发送 issue/邀请。原五份 metadata 缺口及 HF403 仍是独立阻塞，
不因本批准备完成改为 PASS。广义 R07-C 继续 OPEN。
