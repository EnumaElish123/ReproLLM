# 2026-10-22 · R07-C D-G / P-B

状态：委托裁决选择A，实施与最终验收 **IN_PROGRESS**。起始main `38b4e2b8881754c85a4f4d489e8a1a51025c8009`，工作区干净。

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
最终质量、五项目Gate A、受影响命令、分享证据、提交与精确推送CI均须实际完成后另记。

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

最终质量门、Gate A、专项验证、证据核验和提交／CI结果待实际执行后补充。
