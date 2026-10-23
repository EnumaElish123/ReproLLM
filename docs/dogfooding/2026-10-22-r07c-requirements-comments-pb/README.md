# R07-C D-C P-B 会话报告

启动日期：2026-10-22；收尾记录日期：2026-10-23。状态：**产品实施、完整本地质量门、五项目与受影响验证、证据归档均 PASS；推送前验收快照，精确提交 CI 在交付时另核**。
本地验收完成于 2026-10-23；最终推送提交及其五项 CI 在交付回复中记录。本轮不发布版本。

## 授权、候选与范围

维护者已明确接受 D-C 方案 A 及具体规范补丁；授权来源为
`docs/plan/reliability-2026-10-03/proposals/R07-C/requirements-comments/decision-accepted.json`。
基线／提案提交为 `9186605af958c5693e4fc616484e72f93f54a225`，
具体补丁 SHA-256 为 `e7202a79fdbe8a99a4cd0343688f4499e8d674af5429dd9f03d3f12a4f2a7a79`。
产品任务提交是 `0f8c4dfaf5822f4784c1b9bb9033509b9e8097dd`；完整质量门开始时工作区干净。
产品与证据按本轮验收提交交付；精确最终 head 的推送及 CI 仍单独核验，不能借用历史 CI。
原 P-A 17 份文件、PROPOSED 提案和历史输出保持原样；它们的状态不被改写为本轮执行结果。

本轮只让已捕获 requirements 图的 ordinary 行获得有界尾注释回退：原 route 分类先执行，
完整原行解析成功时直接保留；只有原行失败、且该文件任意物理行均未命中尾反斜线 veto，
才尝试第一个 ASCII SPACE/TAB 后 `#` 的前缀。前缀须经既有 Requirement 成功解析且没有 URL。
失败保留原完整行诊断。保留物理行、exact 判据、图遍历、读取范围和既有规则优先级。
新增 exact 可带来正信用、requirements lock 或消除告警；新增 loose use 也可新增告警、profile 和初始化字段。
隔离阈值下退出码可双向变化，独立 finding 不被隐藏。

只读产品审阅确认 `src/reprollm/core/deps.py` 是相对 RED 的唯一产品改动，SHA-256 为
`4f6593b18c1fd24f672aa32e8b985ed9f3082c4e22530ea9d46be1f28f76d45d`。
其他 manager parser、rule、engine、detect、scaffold 与 renderer 保持原字节。
本片不扩展续行、include、URL/VCS、constraints、环境展开或 manager 执行。

## 测试先行与全部真实结果

下表是两组聚焦测试，**不是最终全量质量门**。两组共有 9 个不同模块、775 个 case；
141 个新 case = 核心 85 + 消费者 56，最终全部通过。参数化展开后的 case 只计算一次，
35 条验收项可引用同一测试，不能把映射行数叠加为测试数。

| 阶段 | 失败 | 通过 | 跳过 | pytest 秒 | 实际进程秒 | 原始收据 |
|---|---:|---:|---:|---:|---:|---|
| 核心旧产品 RED | 42 | 457 | 5 | 6.64 | 6.998357 | [原件 hash 引用：development/core/red-01.receipt.json](evidence/source-index.json) |
| 消费者旧产品 RED | 53 | 217 | 1 | 39.43 | 39.929497 | [development/consumer/03-red-receipt.json](evidence/development/consumer/03-red-receipt.json) |
| 核心实施后 GREEN | 0 | 499 | 5 | 6.25 | 6.578000 | [原件 hash 引用：development/core/green-01.receipt.json](evidence/source-index.json) |
| 消费者首次 GREEN | 1 | 269 | 1 | 48.37 | 48.869114 | [development/consumer/06-green-receipt.json](evidence/development/consumer/06-green-receipt.json) |
| 唯一断言修正最小复验 | 0 | 1 | 0 | 3.16 | 3.633239 | [development/consumer/08-probe-receipt.json](evidence/development/consumer/08-probe-receipt.json) |
| 消费者最终四模块 GREEN | 0 | 270 | 1 | 48.36 | 48.869737 | [development/consumer/09-green-receipt.json](evidence/development/consumer/09-green-receipt.json) |

核心 RED 的 42 个失败分为 40 个新 comment 捕获预期和 2 个窄范围旧预期调整；45 个新控制通过。
旧调整是 `tests/unit/core/test_requirements_graph.py::test_safe_legacy_noninclude_bytes` 和
`tests/unit/core/test_requirements_depth_frontier.py::test_g23_readable_unsupported_grammar_does_not_create_frontier`
中的 `torch>=2 # comment` 参数；仅承认批准的声明／closure 变化，不更新历史 gold。
消费者 RED 的 53 个失败全部来自尚未实现的捕获/use/credit/profile/first-evidence 变化；
3 个新控制通过，12 个阈值用例在去掉 veto 前的旧行为完整 JSON 都通过。
两组均无 collection/setup/fixture 错误；原日志、命令、退出值、JUnit、计时和输入 hash 均保留。

5 个核心 skip 是当前普通 Windows 进程无法创建 symlink 的既有用例；消费者 1 个 skip 是 POSIX mode 位。
它们不构成安全验证 PASS。另行管理员安全预检和完整本地质量门现已通过；正式门仍保留 4 项 Windows/POSIX 限制 skip，不能视为全平台验收。
核心测试从 RED 到 GREEN 原字节不变；消费者最终 147 个产品／测试输入在执行前后与冻结核验时一致。
两组相应 ruff check/format check 通过；消费者首次 lint 的 2 条 E501 换行修正及原输出也已保留。

## 唯一测试预期修正

消费者首次 GREEN 的唯一失败并非产品语义问题：测试在 raw Markdown 中搜索 `<version>`，
而既有 `src/reprollm/export/exporter.py:495` 使用 `html.escape(..., quote=False)`，
模板 `src/reprollm/export/templates/REPRODUCIBILITY.md.j2:196` 输出 notable message。
独立 raw export 字面量应为 `&lt;version&gt;`；完整 AuditReport 与 CLI text 预期不变，产品不改。

修正前后 SHA、精确 diff 和来源依据保存在
[development/consumer/07-export-expectation-correction.json](evidence/development/consumer/07-export-expectation-correction.json) 与
[development/consumer/07b-export-correction-followup.json](evidence/development/consumer/07b-export-correction-followup.json)。
旧产品 RED 在 FAIL 状态的退出码断言已失败，尚未到达该 export 断言；
修正后没有回退产品重跑 RED，不能宣称取得了修正后全部字节的新 RED。
1 个最小复验通过后，原四完整模块重新取得 270 PASS / 1 既有 skip。
最终消费者 CLI 测试 SHA 是 `d1d33b7f1228b846e85158f43311bf3a221fc29a2f73049fc78fd356514f5979`。

## 35 项验收映射与边界

详见同目录 `acceptance-mapping.json`：含 C01–C35 全部条目、26 个测试 family 的精确路径／函数／行号、
每个 family 的真实参数化数量、141 个新 case 的唯一计数、既有控制和待执行门。
C01–C34 的聚焦断言、完整质量门和相应专项均通过；C35 的新鲜五项目／受影响／最终身份检查也通过。
全部条目保留精确最终 head CI 的单独待验状态；C35 不以单元测试代替。

C31 的新增回归直接覆盖独立 WARNING 和自身 promoted CRITICAL 的阈值矩阵。
无关 CRITICAL 的聚合仍由既有 `tests/unit/core/test_engine.py::test_level0_not_a_git_repo` 与
`tests/unit/cli/test_audit.py::test_audit_text_fail_result_line` 支持；它们已在完整质量门中逐项确认通过，
不声称新增了 comment 专属的独立 CRITICAL fixture。
C34 的双路径新测试比较完整 dependency facts/graph/read traces；CLI 新测试比较重复完整 JSON、
完整导出字节及历史 stdout。最终 synthetic 还完成不同路径的完整报告与导出重放，公开归档已独立回读通过。

## 准备阶段的环境与工具失败：不计作正式产品门

所有原件均保留，正式质量门未因这些准备记录被宣称执行或通过。

| 准备记录 | 实际结果与归因 | 后续核验 |
|---|---|---|
| [原件 hash 引用：validation/preparation-attempt-01.json](evidence/source-index.json) | synthetic helper 在准备时出现 bytes literal 的非 ASCII 字符 SyntaxError，exit 1；product executions=0、尚无预期文件 | 清理误入的字符后完成预期准备；修前脚本与 SHA 保留 |
| [tools/preflight/summary.json](evidence/validation/preflight/summary.json) | 9 条命令中 `long-path-clone` expected 0 / exit 128；原 stderr 为 Git/MSYS `NtCreateDirectoryObject` 对象创建被沙箱拒绝，status FAIL | 后续主机长路径预检单独记录，不把失败抹成 PASS |
| 同一 preflight 的 `outside-repository` | exit 128 且 expected_exit=128，证实隔离目录不在父 Git 仓库内 | 这是通过的环境控制，不是第二个 clone 失败 |
| [tools/host-path-preflight/summary.json](evidence/validation/host-path-preflight/summary.json) | 5 条命令；clone、checkout 成功，真正 FAIL 是 `expected-blob` exit 128 / Filename too long | [tools/host-path-preflight-retry/summary.json](evidence/validation/host-path-preflight-retry/summary.json) 的 6 命令全部通过；仅 disposable clone 启用 longpaths，最长正式 clone 路径 232 字符、Python 字节等于 Git blob |
| [tools/preparation-revisions/admin-preflight-readback-attempt-01.json](evidence/validation/preparation-revisions/admin-preflight-readback-attempt-01.json) | 只读核查误用 `administrator` 而实际环境字段为 `admin`，产生 KeyError；已核四条 raw hash、没有重跑产品 | 后续 `admin-preflight-readback.json` 为 PREFLIGHT_RAW_READBACK_PASS，原 5 个安全测试通过结果保持 |

管理员证据读取 ACL 的范围受限处理及原始身份／SDDL 收据保留在私有根，公开材料只保留原始 hash 引用；
不把普通沙箱看不见管理员进程的观察当成产品退出。[tools/preflight-final/summary.json](evidence/validation/preflight-final/summary.json) 再次记载
2 条命令 PREFLIGHT_PASS。这些预检不替代完整质量门。

## 正式验证与五项目结果

管理员安全预检已通过且本报告可读取原始收据：[tools/preflight-admin/summary.json](evidence/validation/preflight-admin/summary.json) 为
PREFLIGHT_PASS，2 条命令 exit 0；独立安全测试流 [原件 hash 引用：validation/preflight-admin/raw/001-symlinks-and-no-leaks.stdout](evidence/source-index.json)
记载 5 passed，pytest 1.29 秒。管理员证据读取前提已核验。
最终输入与投影准备冻结后，唯一完整质量门已在产品提交 `0f8c4df` 上通过。
正式 [tools/quality/summary.json](evidence/validation/quality/summary.json) SHA-256 为 `b4c96e4c7a39a39d8d3b56933bc9be1dcf354c6484a8c3c4b2401a5662070552`，
24 条命令总计 670.692762 秒、整门实际 670.954901 秒；48 条 raw 流 hash 已独立回核。
完整 pytest 为 **3948 passed / 4 skipped / 4 deselected**；总覆盖率 **94.4579915761472%**，redaction 行与分支均 **100%**。
安全子集为 343 passed / 2 skipped / 3611 deselected。518 个产品／测试等输入与 39 项验证工具绑定未变；
inputs SHA-256 为 `d563d8f762fc01d3d33cb656c5a55ba30e05ddcbeba6d4dd3ffb8de828e12db5`。
141 个新 case 已逐一匹配正式 JUnit，全部通过。4 个 skip 分别为既有 Windows symlink invocation 一例、
POSIX colon/control 文件名两例、POSIX mode 位一例；管理员 5 个安全用例 PASS 不表示所有 Windows 标记用例均运行。
10 份 schema 在本机原字节均不相同、仅 CRLF→LF 后相等；Linux 精确 schema CI 在最终推送后单独核验。
[tools/execution-plan.json](evidence/validation/execution-plan.json) 保留准备快照，其 NOT_RUN 字段不冒充当前状态；以下由每个终结摘要分别更新。

| 门 | 当前状态 | 计划与验收依据 |
|---|---|---|
| 最终完整质量门 | PASS | [tools/quality/summary.json](evidence/validation/quality/summary.json)、`commands.json`；24 命令，完整 pytest／安全子集／coverage／lint／format／mypy／生成文档／schema／CLI／examples／self-audit 均完成；没有 build 步骤 |
| 五项目 Gate A | PASS | [tools/gate/summary.json](evidence/validation/gate/summary.json)；125 命令／35 检查，五份 fresh L0/facts/L1/default export 全量比对，15 份初始化文件逐字节通过 |
| graph/verbose 受影响验证 | PASS | [tools/affected/summary.json](evidence/validation/affected/summary.json)；20 命令／15 检查，五项目完整 graph／verbose AuditReport／stderr 全部通过，20 份预写来源预期 |
| D-C 公共 CLI synthetic | PASS | [tools/synthetic/summary.json](evidence/validation/synthetic/summary.json)；7 场景、21 完整独立预写报告、136 命令／43 检查 |
| 原始五项目最终身份／clean | PASS | [tools/post-gates/summary.json](evidence/validation/post-gates/summary.json)；15 命令确认五原件 HEAD／origin／clean 与固定输入一致 |
| 公开证据归档与独立回读 | PASS | [归档执行](archive-run-summary.json)与[独立回读](archive-readback.json)；793 文件另加 SHA256SUMS，完整保留原始 hash 与路径投影依据 |
| main 推送与精确提交五项 CI | REQUIRED_AT_DELIVERY | 本报告为推送前快照；最终 head 的实测 SHA、CI URL 和结果记录于交付回复，不借用历史 CI |
| 本片资源 Gate B | NOT_APPLICABLE | 普通有界政策会话，不完成里程碑／不准备版本；资源账本中的 BLOCKED 不因此关闭 |

新鲜 Gate A 已独立取得 PASS：实际 230.871222 秒，命令合计 230.544427 秒，
summary SHA-256 为 `0aeafddae025ce55333f475d7dda99079d4e7e47f93b2299ce16e4af8998297b`。
每项目均完成 L0／facts／三份 init 文件／L1／default export 七项完整比较，250 条 raw 流 hash 已回核。
固定输入如下；所有门结束后的最终 origin／HEAD／clean 核查也已通过。

| 项目 | 固定提交 | Gate A |
|---|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 7 项完整比较 PASS |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 7 项完整比较 PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 7 项完整比较 PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 7 项完整比较 PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 7 项完整比较 PASS |

HarmBench 的独立来源预期为新增 root `requirements.txt` 第18/19行 art、tenacity 两个 unversioned 声明，
完整声明总数 45→47；只删两条对应 requirements 诊断，保留原有两条 Python syntax 诊断，
合并诊断 4→2。root closure complete false→true，但 is_exact 仍 false，不新增 root requirements lock。
其他 facts 字段、完整 L0/L1、profiles/hints、init/default export 预期不变；其他四项目预期完整不变。
这些预期在冻结前独立来源推导；本轮 Gate A 的完整 facts 已按这些精确差异比较通过，graph／verbose 专项也已按相同独立来源完整比较通过。历史 47 份 oracle 保持，
当前预期按来源补充并独立绑定，禁止复制候选输出反填 gold。

graph／verbose 专项实际 55.854853 秒、命令合计 55.764155 秒，summary SHA-256 为
`94b89d506fde760567469cd0b934da40a5ce0eb314bebd216c0efa297e6eba70`。
五项目各自完整 graph、verbose AuditReport 与 stderr 均一致，40 条 raw 流 hash 已回核；
HarmBench root complete false→true、is_exact 仍 false，未发现额外差异。

公共 CLI 专项实际 48.937761 秒、命令合计 48.537243 秒，summary SHA-256 为
`ab93392fe1531b2a9428a54f913d05f2485ba265b4b6abb07e8fc051fe2f64d9`。
7 场景／21 完整独立报告／136 命令／43 检查覆盖双向 WARNING／CRITICAL 阈值、独立 warning、
suppression、veto 与恢复、完整 verbose、默认 text／export 重复和不同路径重放；272 条 raw 流 hash 已回核。
最终原件身份检查为 15 命令，实际 0.684607 秒、命令合计 0.608143 秒，summary SHA-256 为
`8019286563d84c2a6c36d20991a220602bf48de5f13d5b0f372aa38a4f8c3e7b`；五份原始 checkout 保持固定 HEAD／origin 且 clean。
正式各门均一次通过，无正式门失败或重跑；准备失败保留在前述独立记录。验证执行方对含 final preflight 的
322 命令／644 原始流完成全量 hash／字节／预期退出值回读。

归档及独立 reader 共 2 条命令，实际 3.1272995 秒；公开文件 **793 份，加 SHA256SUMS 共 794 份**，
对应 788 copied sources、60 路径投影、262 次严格 JSON 类型／键／顺序核验和 387 份未重复复制源的 hash 引用（含私有原件及已入库历史 oracle）。
20 affected 与 21 synthetic 独立预期原始 hash、隐私、换行和 EOF 保留检查全部通过。
[校验和清单](evidence/SHA256SUMS) SHA-256 为
`b89869032ab3c16f7c9b345cfdc29d612c6512a8b0a6c5e8196681cb30778543`；详见[来源索引](evidence/source-index.json)
和[独立回读结果](archive-readback.json)。包含 canary、身份信息的测试原始流和 helper 不做字段删减，整件保留私有并记录 hash。

## 可重放范围与入口

使用产品提交 `0f8c4dfaf5822f4784c1b9bb9033509b9e8097dd` 与其 `uv.lock`，
按 `uv sync --locked --dev` 恢复开发环境。141 个新 case 可由[验收映射](acceptance-mapping.json)
中每项 `path::function` 精确选择器重跑；同一 family 的参数化 case 只选一次。重跑结果属于新执行，不能替换本轮原始收据。

五项目先核对 `val.md` 固定 pin／origin／clean；规范 L0 命令形态为：

```text
uv run --locked reprollm audit <PIN_CHECKOUT> --level 0 --format json --fail-on never
```

`init → L1 audit → default export` 只在 disposable clone 中执行；各目标精确 argv、cwd 的逻辑投影、退出值、
计时、完整初始化文件与导出产物由[证据索引](evidence/source-index.json)指向。
JSON 全量比对使用 `scripts/compare_gold.py EXPECTED ACTUAL`；只有 AuditReport 使用 `--audit-metadata`，
facts／graph 等业务结构不使用此豁免，YAML／Markdown／stdout 按各原定完整字节合同比较。

独立预期来源见[oracle 绑定](evidence/validation/oracle-binding.json)。没有重复复制的历史 body，
按其 `source_commit`、`source_path` 和 SHA-256 从 Git 读取并核验；HarmBench 的批准差异另按本轮独立来源补充，
不得用候选实际输出生成预期。临时冻结 helper 本体含机器路径或安全测试 canary，仅保留私有原件与公开 hash 引用；
公开包提供完整证据及复验入口，不声称自带一键运行器，也不使未提供资源的验证变为可执行或通过。

## 资源和后续范围

`docs/dogfooding/pending-resource-validation.md` 中 VAL-R03 继续 **BLOCKED**：
台账最近一次 authenticated HF 小文件预检返回 403，五份原始 metadata manifest 仍缺失。
本轮没有新访问预检，没有恢复或验证这些远程文件。
VAL-R01/R02 历史结果保留其原候选归属，不能改绑到 `0f8c4df`；本轮不使用 GPU，不调用付费 API，
不跑新的 paid judge，不发布版本。

更广 R07-C 仍 OPEN：其他 requirements/include/续行/URL/constraints/manager 单包 grammar、
listing/framework 覆盖和充分证据政策仍须独立具体 P-A 与适用批准。
A02 真实独立试用／反馈仍 PENDING；A03 申请草稿不等于提交／获批，身份、角色、组织信息及提交授权另行确认。
本报告不据局部完成自动裁决后续政策，也不编造真实采用指标。

## 提交与 CI 边界

本地结果绑定产品提交 `0f8c4dfaf5822f4784c1b9bb9033509b9e8097dd`。文档、导航和证据的收尾提交随后记录；
本报告是推送前快照；最终推送 head 的五项 CI 与 Linux 精确 schema 校验在交付时独立核验，确切 SHA、run URL 和结果记录于交付回复。
未取得这些结果前不把会话标记为全部完成。本轮不调用付费 API、不使用 GPU、不发布版本。
