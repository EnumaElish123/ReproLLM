# R07-C D-M-E P-B：environment 嵌入 pip 提取失败

日期：2026-10-23。产品提交 `a221e9d5feadd55724bfe92ddccebe586e66d854`，父提交 `a57c6462d2189792caf606410add2f9e1a7f983a`。最终本地质量、五项目 Gate A、受影响验证、27 例完整记录与原件复核均 PASS。精确最终推送 HEAD 的五项 CI 在交付时单独核验，本报告不提前声明远端通过。暂不发布版本。

依据：[当前计划](../../plan/README.md)、[P-A 固定材料](../../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/README.md)、[具体接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/decision-accepted.json)、规范 §12.2、§12.3.6–§12.3.10。维护者明确回复“继续执行下一步开发计划，接受推荐”，接受本片推荐 A、精确补丁及全仓保守成本；不扩张为其他政策批准。

原补丁 SHA 为 `2ccb8860b2e7333f721e4dda4d8b5300a39d4e070226a26179080878f81f6d17`；应用后的规范完整字节 SHA 为 `eea9b4e7b9899dba99af4aba81317f695fc40e4ec9bef1610a7136137b2b4f4f`，精确匹配提案目标。原 P-A 的25项及 SHA256SUMS 保持父提交字节，批准 sidecar 单独新增。

最小实现只改 `_parse_environment` 的原 embedded-pip 调用点：保留 str／非空 strip 短路和原单次 stripped 参数，实际失败时 setdefault 记录既有 unparsed_requirement。同源结构等原因优先，部分声明、顺序、外层 dependencies 一基序号、原诊断、Conda exact、项目/锁关联和信用保持。空白仍跳过；不扩展 pip/Conda/includes/comments、不猜包名、不增加读取。引擎、扫描器、脱敏、schema、依赖、版本、gold 和历史结果未改。

原 exact/qualified 信用 → D-F/D-S → D-L → D-M → D-G 的逐包次序保持。接受的成本包括无关子项目失败可令全仓剩余未获信用关键包 WARNING／升级 CRITICAL 转为 SKIPPED/INFO，孤立 exit 1→0；不授予 exact 信用。独立 warning、阈值、suppression/alias 保持。完整 JSON 保留 finding，默认 text 可显示 PASS 与 skipped 数，默认 export 移除原 notable warning；init/profile/hints 的成功库存及生成文件保持。

## 测试先行与完整更正记录

新增154个唯一参数例：core85、rules39、CLI30，共39函数；三处旧函数中的四个参数实例按批准的新原因合同修订（P14两例、结构一例、C21 environment一例），不算新增。不更新 fixture/snapshot 或 gold。[精确验收映射与所有原件索引](evidence/source-index.json)中的 `review/acceptance-mapping-draft.json` 绑定 A01–A38、selector、行号、源码/函数 hash；该原草稿的待最终验证状态保留，本节和最终门给出终结结果。

| 阶段 | 实际结果与边界 |
|---|---|
| core 首轮 RED | 37失败／49通过／2权限skip：其中2项漏写原 Conda range 诊断；按旧源码补回，不改政策预期，原件保留 |
| core 修正 RED | 36政策失败／50控制通过／2权限skip，源码未改 |
| core red-03 | 实际已是候选 GREEN：86通过／2权限skip；此轮加入物理打开轨迹，目录名不改，绝不冒充基线 RED |
| core 最终 GREEN | 86通过／2权限skip；随后正式门的两条真实 alias 均无skip通过 |
| 消费者首轮 | 默认临时目录 WinError5，69 setup errors；不算业务 RED |
| 消费者最终 RED | 54失败／15控制通过；实现前把正信用 Conda fixture 从前缀 pytorch=2 修正为 exact pytorch==2，预期输出未变；两轮原件均保留 |
| 消费者 GREEN | 同一最终69项全部通过，完整 Finding/JSON、阈值、text/verbose、init/export与历史哈希保持 |
| 集中回归首轮 | 970通过／1失败／7权限skip；C21旧 environment cause 断言直接被本片取代，语法/诊断不变 |
| 最终隔离旧源码 RED | 完整最终核心输入加四项旧参数断言：37失败／50控制通过／2权限skip，不回退共享工作区 |
| 最终集中 GREEN | 1123通过／9权限skip，52.028秒含 Ruff/format/mypy；两条新增真实alias后由正式门补通过 |

最初产品嵌套 if 触发 SIM102，改为等价短路单 if 后定向检查通过，未改变 strip／解析次数。最初 Windows PowerShell 把 UTF-8 中文路径误读，正式预检前退出；普通诊断 exit1 与原 stderr 保留。改用现有 PowerShell7 后真实管理员预检通过；只读回读管理员原件，未改 ACL 或全局设置。初始 synthetic 预期冻结工具的 first-evidence note 护栏过窄，在写出案例前停止；接受既有 declared-as 文案后冻结成功，无产品执行、无业务预期更改。

初始内联 SIM102／预期冻结护栏诊断保留于本机会话工具记录，未伪造独立 raw 收据。正式门、RED/GREEN、隔离旧源码及已记录准备失败的完整原件通过下述索引保留。

## 最终共享质量门与五项目

最终524输入清单 SHA `bda91a925e7480614d8c91f3aa47ef19f7b068c98fdbaf5d8aaaf18830133f78`；工具 manifest SHA `39dcfb172b1cda1eeab82f8bfaba7dcf6211b7ba9a37e0673c14d4f4c9b7fdff`。工具准备27项正反例通过，manifest绑定19 helpers/11 bindings，正式质量门另冻结全部实际工具输入。下表引用[完整原件索引](evidence/source-index.json)，保留真实命令、退出、耗时及原始流 hash；墙钟和命令累计时间分列，不重复相加。

| 正式组 | 命令 | 墙钟秒 | 命令累计秒 | 完整结果 |
|---|---:|---:|---:|---|
| preflight-final | 2 | 2.149 | 2.146 | 真实管理员环境与5 safety用例通过 |
| quality | 24 | 788.428 | 788.167 | 4272 PASS / 4 SKIP / 4 deselected；全部24项质量检查成功 |
| gate | 125 | 227.017 | 226.690 | 35完整比较、15初始化文件；五L0/facts、init→L1、default export零差异 |
| affected | 20 | 56.752 | 56.662 | 15完整graph/report/verbose比较，零差异 |
| synthetic | 1 | 0.503 | 0.434 | 27完整内部记录相等，189检查通过 |
| post-gates | 15 | 0.834 | 0.754 | 五原件SHA/origin/clean保持；冻结输入不变 |

实际总覆盖率 94.475628%；redaction 分支100%；安全单独347 PASS／2个平台skip。Ruff、format、mypy、生成文档、examples、自审计均通过。Windows schema仅使用已声明CRLF归一，最终HEAD的Linux3.12精确schema/docs/examples另由CI核验。四项全量skip原因为：

- `tests.unit.cli.test_audit_normalization::test_symlinked_invocation_normalizes`：creating symlinks needs privileges on Windows。
- `tests.unit.cli.test_scan_diagnostics::test_untrusted_warning_prefix_cannot_become_default_coverage[syntax]`：POSIX filename includes colon/control character。
- `tests.unit.cli.test_scan_diagnostics::test_untrusted_warning_prefix_cannot_become_default_coverage[external-read]`：POSIX filename includes colon/control character。
- `tests.unit.core.test_manifest_scaffold::test_force_success_preserves_existing_file_modes`：POSIX permission bits are unavailable on Windows。

新增 A17 两条真实 symlink（内部逻辑身份／外部内容拒绝）在正式 JUnit 中均 PASS，不以早期权限skip替代。

五项目仍是 val.md 固定pins：lm-eval `b954108c9baaaa934b4ad842033b31a97ee30816`、FastChat `587d5cfa1609a43d192cedb8441cac3c17db105d`、LlamaFactory `673048c6a543cbbeaed5b8444b8223dc4e23c721`、HarmBench `8e1604d1171fe8a48d8febecd22f600e462bdcdd`、llm-dp `7f8b5dff4b92aae90ceccce3ec959b48307bed9e`。

独立来源再次核验17724 tracked paths；精确 environment/conda-lock源为0，不能声称五项目实测了该失败分支。旧产品、包环境、命令参数及原始hash适配核验后，显式绑定47份已接受完整兼容基准与20份graph/verbose预期；没有复制新候选输出为gold。新鲜命令比较全部零差异，保留D-C后HarmBench47声明和两条原Python诊断，不将旧delta重计为本片。原五checkout最终仍干净且pin/origin一致。

27例来自不可变P-A完整兼容记录加独立字面delta，改源码前冻结；独立重建复核一致。实际19案例新增20个逻辑文件原因、10 raw WARNING→SKIP、E21 D-G→D-M、E23原D-M evidence扩展均符合预期。六投影加一个完整record比较共189项；声明、诊断、graph、Python、scanner/read/Requirement轨迹、锁关联和三条raw规则全量比较。不把完整旧兼容记录误称每字段独立gold，也不把内部raw规则当CLI退出实验。observer固定 installed_versions={}，E20/E22为显式Python coverage seam；公共CLI/engine/profile/init/export由69消费者和五项目命令另测。

本片154项新增回归可直接重放；Windows 的真实 symlink 用例需具备对应权限，权限 skip 不能记作通过：

```text
uv run pytest -q tests/unit/core/test_environment_pip_requirement_failures.py tests/unit/rules/test_environment_pip_uncertainty.py tests/unit/cli/test_environment_pip_uncertainty.py
```

## 归档、资源与交接

[公开三文件证据包](evidence/publication-summary.json)为严格hash-references-only，共 792 个来源，全部 private-reference，verbatim-copy/envelope/projected-metadata均0。完整原始正文、命令、工具、JUnit、coverage、所有失败及更正原件整件保留本机；公开仅相对逻辑名、长度、SHA及核对的终结摘要。[归档执行](archive-run-summary.json)、[独立回读](archive-readback.json)，归档工具76项正反例（30正／46反）通过。公开hash本身不能让外部读者验证私有正文，不承诺仅凭公开目录一键重放；本机完整包和精确selectors可供复验。

普通政策P-B不完成新milestone、不准备release，资源GateB为NOT_APPLICABLE。VAL-R03的五份原metadata缺失及最近HF403仍BLOCKED，本轮无新请求；VAL-R01/02分别保留948d164／75d1b0历史身份。A02独立反馈与A03身份/角色/组织/提交授权仍待外部输入。未调用付费API、未用GPU、未发布版本。

下一步可准备独立P-A：核对Poetry已遍历依赖条目中显式version字段的提取边界，先调查mapping中present-but-non-string值，Pipfile单列对照。现有(None,None)或exact=None混合缺失/空白/非字符串及合法非精确/transport情况，不能直接当失败信号。先建立实际输入来源、独立行为、精确补丁与完整消费者/五项目预期，再裁决是否需要新政策；不创建自动批准开关，更广R07-C仍OPEN。

产品提交后的本轮报告/导航只补充证据；最终推送HEAD的五项CI、五项Verify candidate checkout和Ubuntu3.12精确schema/docs/examples在交付时另核，并复核远端main等于本地、工作区干净。
