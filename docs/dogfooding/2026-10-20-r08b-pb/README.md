# 2026-10-20 · R08-B A4 / P-B

状态：**本地最终验收 PASS**，产品任务提交 `69d3a9de66201cc66a7799c65a5ca5110627256b`；
起点 `30dc9cae41b2fbcc1657357eff34b3e5a7f26322`，纯 P-A 快照提交
`dfefce06513a0ce0f32a8a54c10fac8e5f6cdde5`。
报告收尾只补充证据与导航，保持已验证的产品、测试、配置及工具字节。
最终交付另行核对实际推送 main HEAD 的五项 CI，不使用旧提交结果替代。
本轮不发布 release、tag 或 PyPI。

维护者已[具体接受 A4、规范和前瞻补丁](../../plan/reliability-2026-10-03/proposals/R08-B/decision-accepted.json)。
产品仅在默认表逐条加入四个 HIGH：
`privacy.mechanism.params.target_epsilon`、`privacy.mechanism.params.target_delta`、
`privacy.mechanism.params.max_grad_norm` 和 `training.params.num_train_epochs`。
等级描述已记录配置变化的比较风险，不证明参数已消费、隐私保证成立或结果因果。
用户 LOW/NONE、profile 继承、first-match、单层 wildcard 和其余字段保持。
不改 schema、State、matcher、profiles、依赖或版本。

原 P-A packet / PROPOSED 决定及历史 native / judge 报告原字节保留；另立 ACCEPTED 决定。
前瞻 `val.md §8.3.1` 只规定新候选 diff 的 epsilon HIGH，不重写旧 MEDIUM 结果。
原始 metadata 缺失与 HF 403 仍是独立外部缺口；本次普通静态政策任务不启动新的资源里程碑。

## 验收与范围

[RED→GREEN 原始证据](tdd/summary.json)：新增 86 项参数化验收先在旧默认运行，
25 failed / 61 passed / 218 deselected，失败均为四条新默认缺失或 MEDIUM→HIGH 预期差异。
应用接受补丁后，两个完整受影响模块 **304 passed**；Ruff check / format 均通过。
验收覆盖四字段 changed / added / removed、实际 Manifest→State、用户 LOW/NONE、
profile 继承、broad / exact first-match、深层与别名控制、完整 CLI JSON、过滤 / 阈值、
全量 summary、无额外 HIGH 掩盖、重复确定性、自 diff、只读及 schema。
[独立实现复核](final/qualification/implementation-review.json)无未解决问题：五份接受补丁
在内存逐 hunk 应用到纯 P-A 提交后，六个实施文件与候选和 Git blob 完全一致。

| 改动 / 保留合同 | 受影响验证 | 独立预期 |
|---|---|---|
| 四条精确默认 HIGH | 定向矩阵、完整质量门、五项目 isolated diff | 每条单独变化触发 HIGH；没有 config hash 或其他 HIGH 掩盖 |
| LOW/NONE、继承、first-match、过滤、阈值 | 公共接口 / CLI；DP 一次性副本追加覆盖 | 现行覆盖优先序、完整 summary 和退出码不变 |
| L0 扫描及所有规则 | 五项目 fresh Gate A | 完整 findings / detection / hints / deps / 路径 / diagnostics 零差异 |
| 五组旧 native A/B 记录 | 当前候选 fresh CLI full / repeat / HIGH / filter / self | 仅 DP epsilon 新计算 MEDIUM→HIGH；其他四份完整报告不变 |
| init / lock / run / export | NOT_APPLICABLE 于本轮受影响扩展 | 仅默认 diff YAML 改动，不机械重跑未受影响命令 |
| GPU / provider / Hub | NOT_APPLICABLE 于本轮普通静态政策任务 | 不触发新里程碑 / release；历史成功与阻塞保持原候选归属 |

## 最终共享结果

| 检查 | 结果 |
|---|---|
| 完整质量门 | 24/24 PASS；3,187 tests、2 slow deselected；345 security tests；coverage 94.205719419%；redaction 59/59 行、24/24 分支 |
| 质量门耗时 / 输入 | 623.259989 秒墙钟；pytest 473.39 秒；全部候选输入前后逐字一致，24 次 origin guard |
| 五项目 Gate A | 51 commands / 32 checks / 10 份完整 JSON 比较；零 gold delta；89.067542 秒墙钟 |
| 受影响 diff | 36 次 fresh 产品 CLI / 36 份完整 strict JSON 比较 / 135 checks；含 Git、环境及比较器共 148 commands；39.613386 秒墙钟 |
| diff 输入 / 只读 | 64 份旧 run/snapshot 原件完整核对固定 Git blob；全部历史 / synthetic / profile 输入前后逐字相同 |
| 构建 / 隔离安装 | 新 wheel SHA256 `0f8bd1df0ba83db9f8f1a6faccbf1efcc5fa379e2acb310d8f2a959f7ac6b801`；offline distribution PASS |

[完整本地证据](final/README.md)保留完整审计 / facts、严格比较、diff 实际输出 / 独立预期、
全部 stderr、命令 / 退出码 / 耗时、候选来源及输入哈希。质量门只运行一次最终产品输入；
锁定环境提前离线同步，quickstart 在完整 pytest 前通过，经核验的 Git 兼容器适配本机 Git 2.25.1。
通用 runner 的历史任务标签原样保留；本轮 invocation binding、完整候选提交、输入 inventory、
模块 / 安装版本 origin guards 和新输出目录绑定实际 R08-B 执行。

五项目基础层与当前质量门均是新执行，独立旧 oracle 只用于预期，未复用旧 PASS。
扩展层在五个一次性固定副本中分别执行五种 native-record diff（共 25 次）和单一字段案例
（5 次），DP 再追加 LOW/NONE、过滤与 broad/exact 顺序（6 次）。
每份 JSON 使用既有 compare_gold 严格比较全部字段，没有元数据豁免；预期在当前产品执行前固定。
旧记录按原 run ID 放回完整快照树，以保留 refs；新 synthetic 输入使用相同 run 元数据隔离唯一配置变化。
原始五个 checkout 及副本的 HEAD、origin、tracked/untracked 干净状态均前后通过。

只有 DP epsilon 叶子的新计算等级从 MEDIUM 升为 HIGH，完整 counts 相应 MEDIUM−1 / HIGH+1 并按现行顺序排序；
原 config SHA HIGH 和其他字段保持。其余三条 A4 参数在旧 pair 中相等，不凭新默认合成 drift。
四条独立 HIGH 场景由额外 CPU 输入验证，不能将其解释成新的训练、隐私记账或 child 消费验证。
本轮没有新 native child、GPU、provider、Hub 或付费请求；旧资源证据仍分别绑定 `948d164` / `75d1b0`。

## 验证工具纠正与交付边界

首个 diff 扩展尝试的辅助 audit hook 禁止了产品正常的只读 `git rev-parse --show-toplevel`，
首条命令 exit 3、0 份比较；原始失败、helper、输入及源哈希均保留。
纠正仅允许精确 Git argv 且 cwd 为当前一次性 clone，仍拒绝 socket、heavy import 和其他子进程。
新旧准备材料的 72 份非 inventory 文件逐字相同；全部 36 条计划、28 份独立预期及 64 份旧输入引用未变。
嵌入日志代码的转义问题在 AST 预检即发现，未进入产品；前稿与修正资格另行保留。
修正后的完整 36 项在新目录执行，逐条记录唯一合法只读查询，共 36 次。
[独立工具修正复核](final/affected-diff/qualification/independent-correction-review.json)确认白名单和输入边界；
辅助工具修正不改变产品、测试、schema 或 gold，不作无依据的完整质量门重跑。

原始 unified patch 的空白上下文行按已接受哈希保留；Git 将其识别为 trailing whitespace，
这是不可改写的补丁语法，不报告为全文件无例外 PASS。原始输出的 EOF 空行按哈希保留；
源文件及手写文档另行检查。归档后核对完整 Git 文件集与每个 blob，包含受 ignore 影响的文件。
main 原有 README、docs index 修改及额外案例草稿保持原字节，不纳入本轮提交。
当前本地 PASS 不代表同候选完整发布矩阵已完成；最终 CI 以实际推送 main HEAD 五项成功为交付条件。

[归档独立读回](package-independent-readback.json)核对 471 个文件、1,020 个原始来源及完整哈希 / 隐私边界；
[Git 暂存核验](staged-archive-verification.json)及[收尾文档检查](closure-documentation-checks.json)记录实际提交集合。
