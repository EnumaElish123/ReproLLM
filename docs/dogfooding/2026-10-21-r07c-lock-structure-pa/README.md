# 2026-10-21 · R07-C D-S / P-A

状态：**具体下一步方案与条件验证已完成，D-S 仍 PROPOSED；正式产品与测试补丁未应用**。
本批只准备已关联格式锁的有限结构提取失败，不关闭整个 R07-C。

## 基线与当前进度

源码/规范起点 `603883fd8b7c7be2eac42d335a182ff654f93918`。
上一批 D-F 产品 `14560ca91b858c1e2bba6bc01dbd48d45bbb9875` 已交付；
其最终 main `603883f` [CI 五项全部成功](https://github.com/EnumaElish123/ReproLLM/actions/runs/39552891340)。
本轮远端只读核对仍为该 HEAD，没有发现上一批遗留补验。
main 三处原 WIP 保持，不纳入提案提交；方案在独立 worktree 准备。

范围依据 [05 §5](../../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md#5-r07-c扫描不完整时哪些结论仍成立)
和上一批报告保留的 OPEN 分支。新[完整提案](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/R07-C_associated_lock_structure.md)
附完整规范、实现、测试及 CHANGELOG 补丁，未应用到正式目标。
提案文稿按单独 Conventional Commit 归档；实际提交号由交付 Git 历史定位。

## 具体合同与边界

仅在 deps 增加内部 `invalid_structure`，检查四种格式锁的有限根容器、包集合、list 条目的非空字符串 name。
保留缺失/空容器和 Conda 顶层 None 的明确例外；存在的 null/其他假值错误类型不能当作缺失。
保留不透明 Pipfile 包值、name 拼写/版本等既有行为，不声称完整格式验证。
已有部分包名信用、任一 exact 或其他合格锁信用优先，再经既有 R06-B 来源关联使用 D-F 原 SKIPPED/INFO 输出。
不改 env/engine/scanner/redaction/schema、锁存在性、历史结果或 gold。

## 实际证据

| 检查 | 实际结果 | 边界 |
|---|---|---|
| 实现静态资格及独立规范审阅 | Ruff、format、严格 Mypy、apply-check；有限五个 AST 节点及一处说明 docstring，其他执行逻辑保持 | 草稿，非已应用实现 |
| 验收草稿 | 109 个新参数例 / 15 函数；明确修订旧 7 个结构例；其余 100 个旧函数 AST/全文不变；三模块静态编译、Ruff/format 和 apply-check 通过 | 未执行 pytest/collection/RED/GREEN |
| [条件观察](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/observations/summary.json) | 29 API + 3 CLI，共 64 workers；32 份完整 expected/conditional JSON 比较；224 命令，448 次只读产品 Git 查询；全部退出码和 stderr 如预期 | 正式补丁未应用，精确 deps 草稿只在独立内存模块执行；注册规则及 check 未替换 |
| [独立实际数据回读](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/review-actual-observations.json) | 32 份完整 expected 从 baseline 与预写字面合同重新独立构建；全部 raw stream/metadata/hash/fixture 与 10,533 tracked 来源核对通过 | 不重跑产品或观察器；严格类型/键/列表/值比较，仅根 T-02 豁免 |
| [五项目来源](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/portfolio/verification.json) | 五个 exact/clean pins；43 只读 Git 命令、10 完整路径捕获、210 来源；独立回读另 22 只读查询通过 | 不执行新鲜产品；预期 zero delta 因完整路径集合没有四格式锁 |

条件观察墙钟 **64.027921 秒**，命令累计 **61.955559 秒**，二者不相加。
实际时间戳保留；无原始结果重写、无失败产品观察或重试。
每个完整 expected 在对应 conditional 前，按 baseline 加预写指定包名/路径/原 D-F 字面转换建立。
只有 typed issue 和未验证关联 map 发生约定变化；旧包集合、声明、unparsed、imports、coverage、诊断及 Git 查询保持。
孤立 CRITICAL 门 1→0、混合 WARNING 1→1、suppressed never 0→0 分别核验。
部分锁中的 torch 继续获合格信用，缺失的关联 openai 才 SKIP；D-F/D-L 与边界控制均保留。

五项目为 lm-evaluation-harness、FastChat、LlamaFactory、HarmBench、llm-dp-finetune。
原完整 L0/facts、五份 L1、15 个 init 文件及五份完整默认 export oracle 的 SHA、原来源提交和完整比较回执已核对。
它们是原版本不可变预期，不是本轮 Gate A。五项目 gold 未更新。

## 适用门、准备停止和待决事项

这是方案文稿会话。按 validation-workflow §3，P-A 完整产品质量门与新鲜 Gate A 为 **NOT_APPLICABLE**；
正式 TDD 与 P-B 产品验收尚未执行（**NOT_RUN**）。不能用上述条件观察冒充通过；接受后的产品 P-B 必须执行全部适用门。
生成规范文档的正式输入未变，受影响生成文档 freshness 为 NOT_APPLICABLE。
本轮无新里程碑或 release，GPU/Hub/provider/付费/原生 Gate B 为 NOT_APPLICABLE。

准备停止如实保留：实现外部文件名令 Ruff 对原未变 imports 错判分类，按实际逻辑文件名检查同一字节后通过；
测试草稿一条 101 列字面量静态失败，拆相邻字面量后通过；观察器最初格式/行长提示，经格式化后冻结，再首次正式执行；归档器静态行长提示修正后复核，未运行产品。
root 首次 AST 核对器未容许已记录的说明 docstring，修正核对范围后通过，没有改产品。
root 五项目 helper 文案替换引入 SORMAT 显示拼写；原 helper/运行结果保留，单独[勘误](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/portfolio/wording-correction.json)
标明正确展示值。四 basename、路径集合与语义检查未改变，无来源门重跑。
上述仅为准备阶段停止，部分诊断是明确标识的人类转录，不能说成保存了原始 subprocess 字节。

**D-S 需要具体接受。** 执行总则 §5.9 和现规范 §12.3.4 明确把本分支留在 D-F 外；
总体继续授权不是这个新合同的批准。已完成可审阅的全部补丁、复现、独立预期和影响清单，
具体决定到达后直接执行 P-B，不重复索要同一权限。无需新 D-41 模块审阅，因为未触碰受保护模块。

## 接续

接受 D-S 与具体补丁后：先测试 RED、再应用已接受补丁 GREEN，完成完整受影响模块和静态检查；
在最终相同输入上一次完整质量门 → 全部五项目 Gate A → 五份 init/L1/default export 及结构/部分信用专项扩展；
记录独立任务提交、最终证据，推送 main 并核对精确最终 HEAD 五项 CI。
原 PROPOSED 快照保留；具体接受另立 sidecar。

其他格式 grammar/包值/版本、一般 manifest/requirements、遗漏候选/import、listing、README/config/framework
及广义充分证书仍 OPEN。既有资源结果只归原候选；不宣称 release-ready，不发布 tag/PyPI。
