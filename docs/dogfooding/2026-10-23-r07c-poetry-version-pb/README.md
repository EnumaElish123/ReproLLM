# R07-C D-M-V / P-B：Poetry 显式 version 字段

日期：2026-10-23。状态：**已接受A及精确补丁；产品实现与全部适用本地门PASS**。产品提交`b18ed198882c88e9824ea9eb94d2f797730f94c2`。
报告/导航另作收尾提交，精确推送main HEAD五项CI交付时另核。不发布版本。

## 范围与接受

干净基线ae173ad33f4b6e4f9b79837169302dfc54c00981；7897进程级代理git pull --ff-only，exit0 / Already up to date。
维护者回复“接受推荐，继续执行下一步”，承接上轮具体A、精确补丁及全仓成本；[接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/decision-accepted.json)单独新增。
原[P-A31文件](../../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/README.md)、PROPOSED决定、35当前观察及SHA256SUMS保持原字节，不冒充本轮候选结果。

产品仅在原Poetry循环加6行：dict value显式含raw version且值非str时，setdefault既有invalid_structure。
保留helper、具名声明、PEP621先因、line/fallback、诊断、reads、root/barrier及锁关联和信用；不扩提前预检。
缺失、所有str（含空白/非exact/不支持语法）、整体非dict、多约束数组、groups和Pipfile保持原行为。
transport+非str只表示显式字段类型边界，不宣称Poetry完整验证/安装失败或隐藏exact存在。

信用→D-F/S→D-L→D-M→D-G保持，复用原D-M完整message/hint/evidence。已接受全仓成本：无关非关键包也可使剩余已用未获信用包WARNING→SKIPPED/INFO，孤立exit1→0；text可PASS+skips、default export移去旧notable warning，完整JSON留SKIP。
独立warning、FAIL-only overrides、suppression和threshold保持；SKIP不授予pin或完整分析证书。
现行规范原字节精确等于批准目标SHA1ab7e083e6a73e45632019792499c14bae6b22a332ee166670c7f9bbefa03d75，CHANGELOG记录成本。
无engine/scanner/redaction/schema/依赖/规则ID/版本/gold/历史记录变更，没有新的D-41范围。

## 先测试与更正

171新增：112core、29rules、30CLI；[48项文件级映射](acceptance-map.json)区别未来设计行数与实际执行数。
完整Finding/JSON/text/verbose、阈值/独立warning、init/hints/export和历史字节均有预写合同预期。

| 阶段 | 真实结果 |
|---|---|
| 旧结构14参数 | RED1FAIL/13控制PASS → GREEN14PASS；仅Poetry false-version新原因，Pipfile等保持 |
| core RED01 | 38FAIL/72PASS/2权限SKIP；graph原调用顺序预期有误 |
| core RED02 | 37政策FAIL+1旧graph complete预期错误/72PASS/2权限SKIP |
| core最终GREEN | 110PASS/2权限SKIP，正式门补两条alias PASS |
| rules RED→GREEN | 27FAIL/2控制PASS →29PASS |
| CLI RED→GREEN | 22FAIL/8控制PASS →30PASS，测试字节不变 |
| 最终171例隔离旧源码RED | 87FAIL/82控制PASS/2权限SKIP，无errors；38core+27rules+22CLI均政策有关 |

两处core纠正仅为同一graph既有合同：先root普通行再include/comment回退与canonical解析；closure.complete表示读取/展开完整，不是全exact。
原RED01/02、两修订和GREEN整件保留。最终RED从ae173ad只读提取完整src，强断言全部reprollm模块origin来自隔离旧源码，未回退共享工作区。
定向Ruff/format与128源mypy通过；任务提交经以下最终门才成立本地验收。

## 最终质量与五项目

527最终输入、22helpers/16bindings冻结；工具24项正反例通过。原生管理员预检：`5 passed in 1.39s`。

| 正式组 | 命令 | 墙钟秒 | 命令累计秒 | 结果 |
|---|---:|---:|---:|---|
| preflight-final | 2 | 2.066 | 2.064 | PREFLIGHT_PASS |
| quality | 24 | 802.618 | 802.365 | PASS |
| gate | 125 | 223.508 | 223.182 | PASS |
| affected | 20 | 55.614 | 55.525 | PASS |
| synthetic | 1 | 0.454 | 0.385 | PASS |
| post-gates | 15 | 0.695 | 0.618 | PASS |

pytest：`4443 passed, 4 skipped, 4 deselected in 704.84s (0:11:44)`；覆盖率94.49202599%，redaction分支100%；安全：`352 passed, 2 skipped, 4097 deselected in 17.31s`。
171新增均正式PASS，两条真实alias均PASS。四项平台skip：

- `tests.unit.cli.test_audit_normalization::test_symlinked_invocation_normalizes`：creating symlinks needs privileges on Windows
- `tests.unit.cli.test_scan_diagnostics::test_untrusted_warning_prefix_cannot_become_default_coverage[syntax]`：POSIX filename includes colon/control character
- `tests.unit.cli.test_scan_diagnostics::test_untrusted_warning_prefix_cannot_become_default_coverage[external-read]`：POSIX filename includes colon/control character
- `tests.unit.core.test_manifest_scaffold::test_force_success_preserves_existing_file_modes`：POSIX permission bits are unavailable on Windows

Ruff/format/mypy、schema、生成文档、examples和自审计通过。Windows schema按已声明CRLF-only归一；最终Linux3.12精确schema/docs/examples另由CI核验。
完整质量门仅正式跑一次；随后纯报告/导航未改冻结产品输入，不机械重复。

五原checkout前后pin/origin/clean保持。fresh Gate A125命令、35完整比较、15初始化文件；affected20命令/15完整graph/report/verbose比较，全部零差异。
完整findings/profiles/hints/paths/diagnostics、init→L1/default export与独立已接受兼容gold比对，不只比摘要。
新盘点17724tracked/17675候选，三份pyproject等于HEAD blob，Poetry/Pipfile条目0；不声称五项目执行坏version分支。
47完整oracle和20affected预期的原字节/来源/环境/参数适配已核，未用候选输出填gold。HarmBench既有47声明和两条Python诊断保留，不重计旧delta。

35例从不可变P-A完整记录加产品改动前冻结的literal delta建立：20新增原因路径、15WARNING→SKIP、Q33 D-G→D-M；原先因和正信用保持。
246断言及35完整内部records比较通过，完整覆盖声明/诊断/graph/Python/read/helper/锁与三条raw规则。
旧完整记录是兼容依据，不是每字段独立人工gold；Q34为显式coverage seam，installed_versions固定空。CLI/engine/init/export由消费者和五项目另验。

## 环境、归档与后续

默认沙箱临时子目录WinError5发生于业务前；改明确real Temp，无ACL变更。
普通preflight的MSYS clone因NtCreateDirectoryObject权限停止；原件保留，require_escalated普通用户新clone/长路径/HEADblob6命令通过，最长233。
早期symlink权限skip由正式nativeAdmin门补PASS。首次工具provenance缺历史manifest在候选前停止，补核原件后24项通过；内联报告生成器首稿因嵌套引号SyntaxError在写文件前停止，改直接保存脚本后语法检查通过；两者只有原会话工具错误，未伪造raw收据。
独立私有spec重建首轮受默认Git CRLF影响；显式process-only LF后原字节精确相等，首次原件保留。
首次归档plan因affected-expected同时被完整tree和命令前缀重复选中而停止，未写公开目录；保留失败原件，明确排除已由完整tree覆盖的命令组根并补归档回归，未改产品或正式验证工具。
核心测试作者另审产品和消费者预期，验证准备者另核来源及35例oracle；不把核心作者自己的测试冒充另一作者审查。

[公开证据三文件](evidence/publication-summary.json)严格hash-references-only，共871来源，全部private-reference，正文/envelope/projected发布0。
工具81项正反例（32正/49反）通过；具体preview经根与另一审阅者核对后才公开，三文件与preview逐字节相同。
[归档执行](archive-run-summary.json)、[独立原件回读](archive-readback.json)绑定终结结果。完整命令/exit/耗时/stdout/stderr/JUnit/coverage/失败/更正/工具整件留本机，包括最终RED ZIP和module-origin检查。
公开哈希不能独立验证私有正文，不承诺仅凭公开目录一键复验。公开新增回归可运行：

```text
uv run pytest -q tests/unit/core/test_poetry_version_field_failures.py tests/unit/rules/test_poetry_version_uncertainty.py tests/unit/cli/test_poetry_version_uncertainty.py
```

普通政策P-B未完成新milestone或准备release，资源GateB为NOT_APPLICABLE。VAL-R03五份原metadata缺失/最近authenticated HF403仍为历史BLOCKED，本轮未新请求；VAL-R01/02保留948d164/75d1b0历史身份。
A02独立反馈和A03身份/角色/组织/提交授权仍待输入；未调用付费API、未启动GPU作业、未提交外部issue/申请、未发布版本。
更广R07-C仍OPEN。下一步可独立P-A调查Pipfile显式version：官方来源、packages/dev-packages两节、allow_bare=False、真实输入及兼容成本；本次Poetry接受不批准该政策。

最终main推送后五项CI、五项Verify candidate checkout及Ubuntu3.12精确schema/docs/examples交付另核，复核远端main等于本地且工作区干净。
