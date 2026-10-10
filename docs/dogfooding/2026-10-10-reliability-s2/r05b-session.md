# S2-B / R05-B Conda 格式专属 pin 语义

日期：2026-10-10。前置 main：`d1b76ccfd06e8249211c40af57a36fa42cab3158`。
按 R06-P → R05-B 顺序；规范 §12.2、§13、§22。
[R05-S A/P+C](../../plan/reliability-2026-10-03/proposals/R05-S/decision.json)
已明确接受；没有再次请求批准。

C-only规范delta随本任务应用，[composition proof](r05b-spec-composition-proof.json)
证明已先应用的A/P+C完整规范SHA为
`13db16f6f89971b5e971b03578de356aba6c5e5bf2f5087fc08e2f3545ba25a7`，
与最初接受的完整patch逐字节一致。官方MatchSpec/package-spec在2026-10-10
重新核对，见[primary source record](r05b-development/primary-source-check.json)。

只改Conda三个bounded regex及 `_add_conda_entry`：数字 `N(.N)*` 的
`name==version`，或single/double equality +非空ASCII literal build才exact；
single equality无build为prefix。受支持原operator/version/build保留existing
specifier字段，exact_version仅numeric version；不加build schema。
channel/subdir/bracket/regex/range/glob/复杂输入保守，fixed诊断不回显raw未知内容。
未知specifier使用固定安全描述，仅已知bounded numeric simple range保留legacy
证据；这不扩exact支持。environment文件本身仍不是lock；嵌套pip走Pythonhelper。
[独立审查](r05b-independent-review.json)绑定a3d248...冻结源码：54公开probe
（50literal + Pythonprefix + 3安全）及9真实console CLI全部PASS，4.971968秒。
30旧defs及其余148正式产品文件同前置提交逐字节一致；源码前后SHA不变。
[完整review包](r05b-review-evidence-index.json)保留12原schema1文件与digest，
原relative refs从r05b-review目录解析。

[18条owner命令](r05b-tdd.json)记录真实argv/退出/wall/rawSHA与前后source：
最小3项真实RED（prefix/double及build raw证据）→3GREEN；57新例+3旧controls
完整RED46FAIL/14PASS→60GREEN。随后公开audit实际发现unknown absolute build/
URL参数可进入evidence，新2安全RED→GREEN，完整矩阵62PASS。
旧privacy consumer错把prefix认exact，定向1FAIL/355PASS→356PASS（wall19.130659，
pytest18.68秒）；保持原fixture输入，改为assert torch WARNING。已有exactcontrols保留。
最终59新验收tests，ruff/format/mypy122全通过。两次lint import失败及最后仅空行
整理记录原log/AST等价证明，不删历史错误；未把预计369误当实际执行数。

[fixture oracle proposal](r05b-fixture-oracle-proposal.json)在修改前独立保存并经
source-backed review：privacy tree第4物理行pytorch=2.8.0、legacyentry2非exact，
仅torch PASS→WARNING，warning+1/pass-1及既有severity/category/rule_id排序。
手改5expected snapshot和gaps literalfailure set；不使用snapshot更新开关。
[实际兼容回归](r05b-fixture-compatibility-tdd.json)：6FAIL/4PASS（10.283017秒）
→10PASS（11.678505秒），completeoverlay精确lock control与其他fixture保持。
原stdout/stderr及harness摘要保留，portable pytest路径呈现修正独立记录。

[不可变owner package](r05b-development-evidence-index.json)保存25indexed原file
及原index（SHA875f47...），原internal refs/hash不改；root TDD view仅给log引用
加package prefix。冻结时候选摘要仍留root gates pending历史状态；以最后quality/
Gate/此报告/Gitbinding判定。

[最终完整质量门](r05b-quality.json)14项全部GREEN：2391PASS、2既有slow
excluded、1既有marker warning，精确总覆盖93.56%（term TOTAL四舍五入94%），redaction statement/branch
100%、security160；pytestwall331.945秒。Ruff/format、strict mypy122、四项生成
文档检查与10 exported schema完整集合/字节全部通过。
[冻结证明](r05b-frozen-files.json)26全局file仍同固定baseline，fixture input tree/
overlays/manifests不变，严格只允许独立提案的5expected snapshot差异。
系统Git/依赖不改，保留临时Git init -b shim；不增网络测试。

[五项目主验证](r05b-gate-execution-accounting.json)85条fresh leaf全部exit0，
667比较全部PASS（180 baseline + 487 affected）；leaf207.956604秒，
baseline177.603873、affected30.352731、wrapper191.083935秒单列。
每pin完整L0/init/L1、离线discover、18独立literal public consumer与6真实audit CLI。
冻结product149 inventory为
`c1c1173f15991a33ebf89067d1376c70b4f435aeec789b67653689be1e3f8115`，
前后实际bytes及五个原始pin的SHA/origin/clean均相同，gold无delta。

补充纯证据比较使用受支持raw版本/build、保守unknown specifier、完整诊断/
evidence/来源及30真实CLI的两个rule状态literal oracle。先验helper误将dataclass
字段写为raw_name，实际/历史source均为display_name。初helper在flush前assert；
保留原helper/准备表/初错记录，并以同原helper、同保全raw做零产品纯重放重建420
观察（335PASS、85字段错误无效）。重建与首次记录的区别明确disclose，不将重放
冒充首次原始完整log。仅据独立source修正
字段标签，值/语义不变；对原raw零产品重跑得420/420PASS。这420合格check仅计一次，
原420及其重建另列，不把无效check计入qualified结果或当作产品FAIL。

[最终合计](r05b-gate-session-total-execution-accounting.json)95 actual=qualified
leaf、1179 qualified完整checks（667主 + 420纯比较 + 92 export），exit0×95、
unknown/reused0、273.465225秒（wrapper排除）。最终结论以主/纯observer/export
各自index及独立review/disclosure为准，不覆写历史harness错误。

[完整export验证](r05b-export-gate-execution-accounting.json)：每pin同一canonical
baseline disposable clone执行冻结R06-G参考及当前export，10fresh leaf全部exit0，
92 checks PASS；15项完整stdout/stderr/Markdown rawbytes逐项相同，65.508621秒。
无timestamp/version归一化；只在portable呈现中约束Wrote对应owned输出路径。
[runner独立根审查](r05b-export-runner-root-review.json)和
[历史manifest独立模型ID oracle](r05b-export-predicate-provenance.json)绑定future
helperbbf9...；相对旧R06-A执行helper只改一个has_identities predicate。
本次仍检查null roles/unlocked/no-run等诚实说明，不把空role对象当真实model。
五项目各完整export/source bytes保存，无网络/provider/GPU运行。
[主证据索引](r05b-gate-evidence-index.json)与
[export索引](r05b-export-gate-evidence-index.json)保存各原rawSHA及portable artifact。
保全15 baseline生成artifact、5 export及所有raw后，仅清理本项5个clone；
原始pins和证据均保留；cleanup wall2.292139秒。

精确version/build不证明channel、平台、文件哈希或位级复现。本项不导入Conda、
不执行依赖声明或求解环境；复杂MatchSpec保守处理，不扩语法或持久化schema。
Python exact、R06-A路径候选/类型保护及R06-P完整include闭包保持字节。
Conda嵌套pip继续使用Python parser；现有YAML declaration.line仍为entry index，
独立矩阵另留physical_source_line，不声称修复具名YAML-physical-source-index backlog。
五个原始pin/gold、fixture input tree/overlays、依赖/schema/engine/redaction保持不变；
privacy夹具5个expected快照按独立literal oracle仅调整torch warning、计数与排序，
既有gaps failure set同步，详见实际RED/GREEN与独立review，不从程序输出生成gold。
资源Gate B本批未激活；历史VAL-R01–R03为BLOCKED，本次offline验证不代替它们。
Git product tree提交后与完整inventory精确绑定，CI在最终main推送后核对exact HEAD。
