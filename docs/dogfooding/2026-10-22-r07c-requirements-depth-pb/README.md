# 2026-10-22 · R07-C D-G / P-B

状态：委托裁决选择A，实施及本地最终验收 **PASS**。本报告形成于推送前，精确远端HEAD的五项CI仍须在交付回复中核验。
起始main `38b4e2b8881754c85a4f4d489e8a1a51025c8009`，工作区干净。

维护者本次明确要求“裁决D-G A/B”；agent复核规范、控制流和用户影响后选择A，
并沿用此前“完成所有后续开发并提交main”的授权推进本片。
这与维护者逐字选择A的来源不同，见 [具体委托裁决](../../plan/reliability-2026-10-03/proposals/R07-C/requirements-depth/decision-accepted.json)。
本决定仅适用D-G和已列精确补丁，不自动接受其他R07-C政策。

[原P-A](../2026-10-22-r07c-requirements-depth-pa.md)、
[原规范补丁](../../plan/reliability-2026-10-03/proposals/R07-C/requirements-depth/spec-proposed.patch)、
[验收G01–G30](../../plan/reliability-2026-10-03/proposals/R07-C/requirements-depth/acceptance-cases.md)。

原22例中“later shallow root”实际浅根先展开，不能证明时间上的后补捕获。
已另立 [证据勘误与4次旧产品观察](../../plan/reliability-2026-10-03/proposals/R07-C/requirements-depth/decision-evidence/README.md)，
原23文件快照逐字节保留；新观察不冒充D-G回归、完整质量门或Gate A。
P-B先补真正先深后浅与反序的root/read轨迹断言，再实施最终图判定。

方案A接受全仓保守SKIP及孤立WARNING／CRITICAL门退出1→0的成本；
保留正面信用和D-F/D-S、D-L、D-M/D-M-S优先级，不增加读取、探测、预算、语法或信用。
产品提交 `d823f90c28229ef90a2f5740f1149c4af7ffdf76`（`fix(env): defer missing pins at final include frontier (R07-C D-G)`），
本地验收覆盖该提交的最终产品、规范与测试字节；本收尾仅补报告、导航和证据，不改这些输入。

普通政策会话资源Gate B为 **NOT_APPLICABLE**，不借历史资源PASS代替本轮结果。
VAL-R03原始metadata与受限访问、A02真实独立反馈仍待补齐；不调用付费API、不发布版本。

## 实施与先测后改

新增内部 `Declarations.unexpanded_requirement_targets` 尾字段，默认空tuple。
只在所有既有roots展开完毕后，从可读已捕获node的受支持include events求最终缺node目标，
去重排序；保留深度10、原声明、closure、诊断、读取及锁库存。
`env.llm_critical_deps_pinned` 在既有信用和D-F/D-S、D-L、D-M之后消费该事实，
按已接受的完整message／hint／evidence输出SKIPPED/INFO。原规范补丁已精确应用。

| 验收组 | 旧产品真实RED | 覆盖 |
|---|---|---|
| 核心图与parser | 最终62 failed／322 passed／1既有权限skip，pytest 5.76秒，进程6.079004秒 | G01–G13、G21–G24、G29；真实root／read顺序、无额外probe、信用／锁／closure／诊断不变 |
| 规则与CLI | 最终31 failed／21 passed，pytest 11.08秒，进程11.5727744秒 | 48新增测试及4既有控制；完整对象、优先级、无use／正信用、阈值／压制／文本／导出／恢复 |

RED前后产品字节不变；核心62处失败均为尚无新字段，消费者31处均为尚无D-G结果。
核心新文件共62例；唯一outside-alias skip来自旧 `test_deps.py`，JUnit classname及源版本已另行核对。它在普通账户因符号链接权限跳过，不能称为PASS。
RED未到达的后续断言必须在GREEN覆盖，不能由预期失败推称通过。
保留早期RED及最终RED，不覆盖。核心早期58→62仅增加边界用例；消费者最后一次RED只调整换行。
其后只读审阅发现全局 `--verbose` 应置于 `audit` 前，单独修正调用位置并记录前后hash；
这不改独立结果预期，也不冒充修正后重新取得旧产品RED。

旧 `test_env.py` 只将depth移出“仍为WARNING”的参数组，因该项政策被本片显式取代；
readable-line、directive、cycle、预算内excluded-include四项保留。
新专用测试提供更强depth断言，原核心“不凭未展开目标伪造body failure”测试保持。

## 验证范围与独立预期

| 改动 | 本轮命令／变体 | 预写独立预期 |
|---|---|---|
| 依赖最终图事实与L0／L1规则 | 五固定原件L0、完整facts；一次性副本init→L1→默认export | 绑定历史Git字节的47份oracle；五份requirements无include，预计完整业务零delta |
| D-G消费者 | 六个专用案例，18份完整AuditReport；基线→未展开→重复／verbose／压制→删边恢复 | exact隐藏、loose隐藏、不存在、深度前未检查的excluded目标、多目标去重排序、独立warning；分别比较完整报告及退出码 |
| 呈现兼容性 | 默认text、show-skipped、default export、完整JSON、重复字节 | text的PASS／skipped数及export不列SKIP沿用现行合同；导出仅预写摘要与列出内容断言，完整文件保留，不冒充完整独立export gold |

正式工具与证据均放在仓库外的短临时目录。普通账户缺少符号链接权限；
经审阅的隐藏管理员入口先验证环境、三项符号链接安全测试与两项泄漏测试：5 passed（1.32秒）。
初次准备预检12条命令均达预期退出，但整体FAIL：过早的输入冻结遇到并行测试新增；
原FAIL和输入差异保留，不能写成最终门PASS。只去除准备阶段的过早冻结，最终门仍严格冻结全部产品／测试／工具。
冻结前另独立审阅并修正synthetic全局verbose位置及重复normalized边的诊断行预期；
原草稿与diff保留，18份完整报告预期逐字节不变，未用产品输出回填。

定向GREEN：核心384 passed／1既有权限skip（5.21秒，进程5.552795秒）；
扫描边界62 passed／19既有符号链接权限skip（3.93秒，进程4.289130秒）。
消费者11完整模块最终454 passed／4 skipped（161.48秒，进程161.995506秒）；
其中2项符号链接权限skip须由管理员最终门覆盖，2项POSIX文件名skip须由Linux CI覆盖。
本轮共110新增例（核心62＋消费者48），移除1项被批准政策取代的旧depth参数例，净增109。

消费者首轮完整回归8 failed／446 passed／4 skipped（161.67秒，进程162.211526秒）：
8项均为旧导出测试的Windows默认GBK解码UTF-8文件错误。仅设置子进程 `PYTHONUTF8=1`，
不改产品或测试，先最小8项重验通过（5.45秒，进程5.950964秒），再完成同11模块最终GREEN。
所有失败原件保留，最终门显式使用UTF-8。
受影响Ruff、format及Mypy（完整src 128文件）通过；产品、测试及规范在相应收据前后hash一致。
独立审阅确认最终图谓词、无新增探测、完整消息及信用／优先级符合精确批准补丁。

## 最终质量门

一次最终门 **24/24命令PASS**，命令合计633.747784秒／墙钟633.985359秒。
**3807 passed／4 skipped／4 deselected**；pytest 539.30秒，进程540.092756秒。
覆盖率 **94.4485566247%**，redaction全部分支 **100%**；security **343 passed／2 skipped／3470 deselected**（16.92秒，进程17.371744秒）。
Ruff、format、Mypy、quickstart、三份生成文档、schema导出、全部示例audit／lock-check及仓库自审均exit0。
CLI精确 `reprollm 0.7.0` 在本门内独立验证，没有沿用前轮遗漏后的补验。

[质量摘要](evidence/validation/quality/summary.json)、[逐命令记录](evidence/validation/quality/commands.json)、
[原stdout计数提取](evidence/validation/quality/test-counts.json)、[冻结输入](evidence/validation/quality/inputs.json)。
质量summary SHA256 `95e8215f391d067ca49d83b5c89ffd2c1637a219d340e3389b22995e33106092`；
inputs SHA256 `a550845bc4443121aa112641554583c18c248f92d4b8a8aedc7bf6b435306e1e`。
516项产品／测试／规范等输入、21份工具、47份历史oracle与18份专项预期门后均保持原hash。

四个skip分别是Windows下的调用符号链接归一化、两个POSIX冒号／控制字符文件名、POSIX权限位；
前者为现有显式Windows装饰器跳过，即使管理员也保持该平台条件。
普通账户定向回归中跳过的其他symlink例已在管理员全套执行，不把原skip重标为PASS。
这四项平台例及security内两项平台skip仍须由Linux CI覆盖。

[本机schema比较](evidence/validation/quality/schema-comparison.json)的原始字节不同，差异仅CRLF／LF，归一后完全相同。
沿用既有Windows边界，**不声称本机精确字节freshness PASS**；精确推送HEAD的Ubuntu Python3.12 CI仍须通过schema freshness。
本轮完整最终质量门无失败或重跑；前文定向环境失败与准备工具失败保持独立记录。

## 五项目与专项验收

| 门 | 实际结果 | 命令合计／墙钟 |
|---|---|---|
| 五项目Gate A与受影响扩展 | PASS；125命令、35检查；完整L0／facts／L1／默认export各5，init文件15，零差异 | 223.905072／224.222820秒；[摘要](evidence/validation/gate/summary.json)、[命令](evidence/validation/gate/commands.json)、[完整检查](evidence/validation/gate/checks.json) |
| D-G六案例 | PASS；105命令、35检查，18份完整独立预期及36次状态报告匹配 | 35.721217／36.047912秒；[摘要](evidence/validation/synthetic/summary.json)、[命令](evidence/validation/synthetic/commands.json)、[检查](evidence/validation/synthetic/checks.json) |
| 门后五原项目身份 | PASS；15命令，全部固定SHA／origin／clean一致 | 0.550494／0.621091秒；[摘要](evidence/validation/post-gates/summary.json)、[命令](evidence/validation/post-gates/commands.json) |

| 固定项目 | 固定SHA | L0／facts／init／L1／default export |
|---|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | PASS |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | PASS |

G01–G13／G21–G24／G29由核心新例和既有parser边界控制覆盖，G14–G20由规则信用／优先级／coverage控制覆盖；
G25–G28由CLI新例和六专项完整消费者覆盖，G30由上述五项目新鲜完整比较覆盖。
六案例包括隐藏exact、隐藏loose、不存在、深度前未检查的excluded目标、去重排序多目标及独立warning。
孤立WARNING／promoted CRITICAL基线exit1→D-G SKIP exit0→删除失配边恢复exit1；独立warning案例始终exit1。
完整JSON／verbose诊断、只豁免timestamp的重复原始字节、suppression及默认text／export可见性均按预写预期通过。
专项导出只作预写摘要／列出内容断言；五项目导出才作完整独立gold字节比较。
JSON比较仅豁免规范允许的根 `generated_at`／`reprollm_version`，不豁免业务字段、嵌套同名字段、类型、列表顺序或缺失项。

## 证据、偏差与交付

[证据索引](evidence/README.md)、[来源逐件绑定](evidence/source-index.json)、[SHA256SUMS](evidence/SHA256SUMS)
共626个清单内文件，另有SHA256SUMS本身，共627个文件；621份原件投影、53份发生已知机器根替换。
188份JSON严格核对类型、键及顺序，原始CR／LF／EOF全部保留；不删除业务字段，不改timestamp。
JUnit、coverage正文、详细测试及失败正文、含私密测试字符串的工具补丁整件保留私有，324件给出原始hash／大小／理由。
完整Gate／专项业务报告、诊断和15个初始化文件公开一次；47份已提交历史oracle以不可变来源路径及hash引用，不重复抄录。

[独立回读结果](archive-verification.json)为PASS：重新核原件／公开字节、全部清单、18份专项预期原hash与identity索引、隐私及行尾；
归档＋独立回读共2命令、墙钟1.989995秒，属于证据检查，不计作产品重跑。
公开目录自身 `.gitattributes` 禁用文本转换；已显式加入10个被忽略的 `.reprollm` 初始化文件，
627个证据文件的index原始字节与清单及工作区全部一致。独立回读结果另以精确原字节保存并禁用文本转换。

准备时另保留一次投影预检FAIL：两份工具补丁包含尚未列出的已知Git运行目录及OS临时父目录，严格拒绝后才补充这两个精确映射。
最终投影预检覆盖66份JSON／补丁，4份含测试canary的补丁仅私有hash引用；原FAIL见
[准备勘误](evidence/validation/preparation-revisions/projection-dryprobe-patches-fail.json)。
中文JSON转义、18份预期二次绑定及独立隐私检查在冻结前补齐，正反例自测通过；没有据当前产品输出调整独立预期。
独立核心review曾误写管理员预检尚待执行，已另立时点勘误，原review保持；核心测试计数也按JUnit classname和历史源位置单独澄清。

推送前报告／导航232个本地链接及内容一致性检查通过，原23份P-A文件和全部冻结输入再次核验不变；
生成文档输入没有变化，不因纯报告补充重跑产品门。
推送后须核对最终main的精确HEAD、五项CI成功、全部candidate checkout步骤及Ubuntu Python3.12 schema／docs／examples步骤，
并复核remote main、工作区clean和冻结输入。此段明确记录报告写入时点，不借历史CI冒充本次交付。

本轮仅关闭D-G有界切片；requirements语法、其他图不确定性、遗漏候选／use、manager值语法、listing／README／config／framework完整性等仍OPEN。
VAL-R03仍BLOCKED：五份原始metadata manifest缺失，最近台账的受限HF小文件预检403；本轮没有重新访问授权资源。
VAL-R01／R02历史资源PASS仍绑定原候选字节，不移记为本轮资源验收。
普通政策会话Gate B为NOT_APPLICABLE；A02真实独立反馈仍PENDING，A03只保留已准备的事实与申请文稿，不联系或提交申请。
未调用付费API、未运行GPU资源验证、未改版本、未创建发布tag或发布版本。
