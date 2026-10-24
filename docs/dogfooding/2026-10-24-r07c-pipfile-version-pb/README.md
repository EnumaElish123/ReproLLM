# R07-C D-M-PF：Pipfile 显式 version P-B

日期：2026-10-24；状态：本地适用门完成，精确最终推送HEAD的CI在交付时独立核验。
基线 `f62958b10a96543718b6c853a0c78a9de690c9c0`；产品任务提交 `ba1415b6905976a38d132198e6d025c64621dbe5`。
维护者[明确接受A、精确补丁与全仓成本](../../plan/reliability-2026-10-03/proposals/R07-C/pipfile-version/decision-accepted.json)。
原[P-A报告](../2026-10-24-r07c-pipfile-version-pa.md)、PROPOSED决定及原34文件保持历史字节，接受记录独立新增。

## 交付范围

只在原 `_parse_pipfile` 的 packages/dev-packages entry循环新增6行：dict、显式version、非str时setdefault既有invalid_structure，仍走原helper和append。
保留 `allow_bare=False`、所有声明/顺序/partial兄弟、先因、line/index fallback、barriers、锁inventory/关联与exact/qualified credit。
缺失version、任意字符串、whole非dict、transport/source控制和custom categories保留；不扩预检、遍历、读取或grammar。
复用D-M：信用→D-F/S→D-L→D-M→D-G；保留原完整message/hint及first declaration/import、distinct sorted file evidence。
已接受的全仓保守成本：无关非关键条目也可使剩余已用未获信用包WARNING→SKIPPED/INFO，孤立exit1→0；text可PASS+skipped、default export notable减少，完整JSON保留SKIP。独立warning、overrides/suppression/threshold保持。
SKIP不授予信用、不证明完整分析或复现成功。engine/scanner/redaction/schema/依赖/规则ID/版本/gold和历史记录保持。
规范字节精确等于批准目标 `b4274dadf6bdd7a23bd6e281dfaf32432d12d913f893f97462a14fcfe788eb0c`；CHANGELOG记录用户行为成本。

## 测试先行与独立审阅

新增267例：161core、58rules、48CLI。另同步四份既有测试中8例Pipfile旧政策预期，不改历史报告/fixtures/snapshots。
[45组验收映射](acceptance-map.json)区分新增参数用例、既有回归、38合成记录和正式门；映射本身不是单独的PASS证书。

| 阶段 | 真实结果 |
|---|---|
| core RED01→RED02 | 61FAIL/97PASS/2权限SKIP → 61FAIL/98PASS/2权限SKIP；只格式化和增加1filtered-source控制，无oracle更正 |
| rules初始54例 | 有效RED36FAIL/18控制PASS → GREEN54PASS |
| CLI初始48例 | 有效RED28FAIL/20控制PASS → GREEN48PASS |
| 初始3例旧预期适配 | RED3FAIL → GREEN3PASS |
| 首轮完整门发现的另5旧预期 | 隔离旧src RED5FAIL/13控制PASS → 当前18PASS，保留全部声明/graph/read/credit断言 |
| export原字节增强 | 3处expected read_text改read_bytes，受影响4例GREEN；旧源/差异保留，最终48由正式门覆盖 |
| A23补充4例 | wrong-manager/missing-member/unpaired-directory/nearer-project，隔离旧src RED4FAIL → GREEN4PASS |
| 最终263版隔离RED | 125FAIL/136控制PASS/2权限SKIP，原件保留 |
| 最终267版隔离RED | 129FAIL/136控制PASS/2权限SKIP，无ERROR，全部124导入产品模块核为隔离f629源码 |
| core定向GREEN | 159PASS/2权限SKIP；正式native门补两条真实alias PASS |

规则/CLI首次运行在tmp_path setup出现54/48 ERROR，未进入产品断言，不能算政策RED；改显式real Temp/basetemp后才得到上表有效结果，原失败保留。
后续export字节精度与A23负例来自独立审阅，均在最终质量门前补齐；旧263测试/旧CLI/旧rules和所有RED/GREEN/JUnit/receipt保留。
定向ruff/format/mypy通过。267正式新增用例全部PASS，以最终JUnit为准；不把早期权限skip当PASS。

## 一次最终质量门和五项目

530最终输入、23正式helpers/19bindings冻结；工具24项正反例通过，native预检5项真实symlink/no-leak均PASS。

| 正式组 | 命令 | 墙钟秒 | 命令累计秒 | 结果 |
|---|---:|---:|---:|---|
| preflight-final | 2 | 2.488 | 2.484 | PREFLIGHT_PASS |
| quality | 24 | 1109.495 | 1109.058 | PASS |
| gate | 125 | 324.225 | 323.730 | PASS |
| affected | 20 | 79.984 | 79.846 | PASS |
| synthetic | 1 | 0.571 | 0.485 | PASS |
| post-gates | 15 | 0.868 | 0.771 | PASS |

完整pytest：`4710 passed, 4 skipped, 4 deselected in 978.63s (0:16:18)`。覆盖率94.49365220%，redaction分支100%；security：`357 passed, 2 skipped, 4359 deselected in 21.12s`。
267新增均正式PASS，两项真实alias均PASS。平台skip完整原因见[会话检查](session-checks.json)，未抹除或改测试规避。
本机Git/venv/python3/locked offline环境和quickstart在重门前核过；Windows schema仅按已声明CRLF-only策略比较，Linux3.12精确schema/docs/examples由最终CI另核。
首轮完整质量门在a913325发现5处更早测试的Pipfile旧预期，4705PASS/5FAIL/4SKIP；267新增及两alias均PASS，链在pytest后停止。原目录20+6原件迁至quality-failed-01/preflight-final-attempt-01并逐hash核回，另保存原.coverage与未推送提交patch。仅同步三份既有测试的5处预期，产品6行不变；修正后的新最终输入执行完整门。后续文稿不改变冻结530输入。

五个正式checkout在fresh Gate A及post检查前后保持固定pin/origin/clean。125命令比较完整L0/facts/L1/export，以及15个生成文件字节和完整stdout/stderr/diagnostics；不只比summary。
Gate A共有35个完整checks：20个报告/facts/export比较与15个初始化文件字节；不能称35个JSON compare。
受影响20命令比较15个完整graph/report/verbose结果。旧47oracle和20affected预期的来源/字节/参数/环境适配已核，不从候选结果更新gold。
本次来源盘点17724tracked/17675候选、3pyproject等于HEAD blob、Pipfile0；五项目不覆盖新坏version触发，触发由新增回归和38合成记录补。

38例以不可变P-A完整记录加实现前冻结的literal delta为兼容预期：25触发案例、24新增source issue、14WARNING→SKIP、PF36 D-G→D-M；先因、较高优先级和信用保持。
364断言与38完整business record匹配；覆盖Declarations/PyScan/read/list/candidate/helper/Requirement traces和三raw规则finding。
原record不含RequirementsGraph.nodes/closures；完整graph由core及affected collect_graph另外覆盖，不夸大synthetic捕获范围。
预期并非每字段独立人工gold；独立作者以stdlib TOML和规范重建38记录/326投影，未导入候选或读取候选输出。PF30为明确coverage seam，installed_versions固定空。

## 证据和剩余边界

[公开证据三文件](evidence/publication-summary.json)严格hash-references-only，1046个来源，正文/envelope/projected发布0。
归档工具89项正反例通过；[执行](archive-run-summary.json)、[独立回读](archive-readback.json)绑定原件和最终结果，root与独立作者审具体preview后才公开，三文件与已审preview字节一致。
完整命令/exit/耗时/stdout/stderr/JUnit/coverage/失败/更正/工具和旧srcZIP留本机。公开hash不能独立复验私有正文，不承诺只凭该目录一键复验。
新增公开回归可运行：

```text
uv run pytest -q tests/unit/core/test_pipfile_version_field_failures.py tests/unit/rules/test_pipfile_version_uncertainty.py tests/unit/cli/test_pipfile_version_uncertainty.py
```

本轮验证准备的字段名/self-check与归档layout遗漏、fixture准备错误，以及selector/publish guard修正和有效RED/GREEN均保留；未改正式产品/530输入以掩盖问题。
普通token Win1314由native正式门补验；Admin原件经固定只读桥接回读，保留原hash，未改ACL。
普通政策P-B未完成新milestone或准备release，Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE。
VAL-R03五份原metadata缺失及最近authenticated HF403仍是历史BLOCKED，本轮未新请求；VAL-R01/R02保留948d164/75d1b0历史绑定。
A02需要独立实际试用反馈；A03需身份/角色/组织事实和明确提交授权。取得输入后先核候选身份和独立预期，再执行适用门或提交步骤。
未调用付费API、未启动GPU作业、未提交外部issue/申请、未发布版本。更广R07-C和真实资源/采用工作仍OPEN，本片不闭合全部R07-C。

文稿检查核相对链接、strict JSON/schema_version、隐私、LF、P-A原件及3文件证据；530冻结输入保持，原14991文件除10个授权变更外其余14981原字节不变。文稿收尾不复跑未受影响的产品门。

任务提交ba1415b经以上适用本地门验收；最终报告/导航提交与推送main后，另核精确HEAD五项CI、五项candidate checkout及Ubuntu3.12 schema/docs/examples，并确认remote main等于本地且工作区干净。
