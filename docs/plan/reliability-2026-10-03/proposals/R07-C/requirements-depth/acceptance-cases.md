# D-G：独立未来验收矩阵

状态：FUTURE_EXPECTATIONS_NOT_EXECUTED。W=现行缺pin FAIL/WARNING；G=拟议D-G SKIPPED/INFO。
默认有真实 captured `torch>=2`、无其他信用/不确定性。完整比较所有声明/lock/诊断/reads及findings，不能只比摘要。

| ID | 输入及边界 | 独立预期 |
|---|---|---|
| G01 | root深度0，最终条目在深度9/10 | 正常捕获；新tuple空；现exact/W保持 |
| G02 | 受支持edge在深度10指向depth11 exact正文 | 不增加read；目标进入tuple；W→G；不授予隐藏exact |
| G03 | 同G02，但目标正文实际上loose/空/不存在 | 都不探测，tuple相同；G不声称目标有pin或存在 |
| G04 | 同G02，未到达目标路径将被`.venv`/环境filter排除 | 不新增candidate检查；仍是depth未展开，保守G成本明确 |
| G05 | 在预算内到达被排除的target，已有node(readable=False) | 新tuple空；不伪造body failure，原W保持 |
| G06 | 在预算内实际读取缺失/binary/oversize/权限目标 | 现D-M为unreadable；D-G不重复；旧完整message/evidence保持 |
| G07 | 深度target稍后由独立shallow root捕获exact | 最终tuple无该目标，信用保持，即使首closure仍false |
| G08 | 同G07，但浅层目标为loose/空 | 不因旧深度诊断G；根据其他事实保持W |
| G09 | 深度target本身名为requirements-extra.txt且是独立root | 按最终节点排除，无root排序误判 |
| G10 | 捕获到原target，但其自己的子edge最终仍无node | 仅真实最终child frontier加入tuple |
| G11 | 多来源边指向同target；normalized内部..别名 | 去重为单逻辑target，顺序稳定；不重复reader |
| G12 | 多个不同target，源/target插入顺序变化 | tuple及evidence lexical排序，完整JSON确定性 |
| G13 | self-cycle、多节点cycle、diamond共享child | 新tuple空；closure资格原样，不用cycle伪装未读 |
| G14 | root exact/无关源exact/同包冲突exact＋depth gap | exact保留；无新每包PASS；不撤销positive |
| G15 | qualified format-lock credit＋depth gap | credit保留；锁库存/association不变 |
| G16 | D-F或D-S关联lock failure＋depth gap | 先前消息、hint、evidence完全相同，无D-G paths |
| G17 | D-L成立＋depth gap | D-L先触发，完整证据原样；coverage条件不扩大 |
| G18 | D-M unreadable/syntax/D-M-S structure＋depth gap | D-M先触发，旧证据原样；不将depth target混入body词汇 |
| G19 | 未获信用torch和numpy＋无关subproject depth gap | 两个当前包可G；不限定本地format-lock ownership |
| G20 | 无critical use、全获信用、Python coverage未知 | 不造use/每包PASS；既有applicability与empty-result veto保持 |
| G21 | 把graph改浅、删除失配边、目标后续变exact | 新fresh scan重算tuple；真实信用或W恢复，不留陈旧状态 |
| G22 | malformed/quoted/attached/remote/absolute/escape include target=None | 新tuple空；不增加读取或联网，旧diagnostic不变 |
| G23 | invalid plain line、inline comments、continuations、index option、constraints/VCS/editable | 不由该文本/closurefalse触发D-G；单独grammar范围保持 |
| G24 | root未枚举/大文件listing丢弃/未知use | 不创建虚假target；listing仍OPEN |
| G25 | isolated W规则audit，warning阈值 | 完整JSON仅批准delta；退出1→0，完整G对象如示例 |
| G26 | 同G25，FAIL-only override CRITICAL | G仍INFO/default；critical门1→0 |
| G27 | 独立rule WARNING＋G | warning门仍1；不被SKIP掩盖 |
| G28 | ignore/suppression、defaulttext、default export | 已有SUPPRESSED/INFO及reason；text skips可见，export不列SKIP，JSON保留 |
| G29 | 旧/manual Declarations positional构造；旧auditJSON | 新字段默认空，旧字段位置不动，旧读者schema兼容；无历史改写 |
| G30 | 全部五项目固定输入，L0/facts/init/L1/default export | 完整零delta；target pins、origin、前后clean及原字节oracle可追溯 |

P-B必需先RED后GREEN，完整受影响回归/静态检查，再一次最终质量门、五项目Gate A及受影响扩展。
普通政策开发不激活资源Gate B；记NOT_APPLICABLE并单列既有资源BLOCKED，不是PASS。

现存当前行为保护须逐项解释变更，尤其 `test_unexpanded_or_uncaptured_requirements_nodes_do_not_invent_body_read_failures`
仍保持body_issue空，只增加独立depth字段；rule层depth项会改变，但readable-line/directive/cycle/excluded-include控制继续W。
不为了通过批量更新gold或快照，不修改受支持exact/closure合同。
