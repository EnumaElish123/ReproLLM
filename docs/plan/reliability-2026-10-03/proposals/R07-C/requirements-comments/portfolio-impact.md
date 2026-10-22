# D-C：五项目独立来源与预写影响

状态：**SOURCE_EVIDENCE_ONLY / PREDICTED_NOT_EXECUTED**。本页为 requirements-comments P-A，
不应用规范补丁，不运行未来 normalizer、产品 audit、init 或 Gate A。未来政策执行次数为0。

[机器可读来源](portfolio-source-evidence.json)绑定当前 `e52e0a24f28fa3ef56cc8e49821962eb1c73869c`
及21份产品/规范/profile来源哈希。五个原仓库均重新核对精确 HEAD、origin、tracked/untracked clean，
在读取前后保持一致。44条正式来源采集命令保留原始流与哈希；另21条只读命令补充当前产品来源身份，
记录独立采集时点，不冒充更早的执行元数据。最初采集 helper 的字段名冲突及未执行的文稿组装语法错误
保留为准备故障，不是产品失败，也没有被写成未来政策结果。

通过 `git ls-tree` / `git show`取得全部候选源字节。JSON的 `source_utf8` 编码回 UTF-8 后与Git blob
及工作副本完全相同，并逐份记录字节数、SHA-256、原物理行、固定源码URL。共5份 requirements、60行，
另3份 pyproject；没有其他候选 manager/格式锁文件。候选核验依据当前scanner的父目录排除、virtualenv
marker、regular-file/内部路径、读取大小及UTF-8边界，不调用产品collector。未发现被排除的依赖候选。
原始stdout/stderr和工具留在私有准备目录；JSON中的命令流路径是逻辑相对名，不声称这些流已公开复制。

## 每项目输入与独立预期

| 项目 / 固定提交 | 完整 requirements 来源 | 其他 manager 来源 | 候选A预期 |
|---|---|---|---|
| lm-evaluation-harness `b954108c9baaaa934b4ad842033b31a97ee30816` | `lm_eval/tasks/japanese_leaderboard/requirements.txt`，4行 | 根 `pyproject.toml` | 无行内注释、无变化 |
| FastChat `587d5cfa1609a43d192cedb8441cac3c17db105d` | 无 | 根 `pyproject.toml` | 没有 requirements root、无变化 |
| LlamaFactory `673048c6a543cbbeaed5b8444b8223dc4e23c721` | `docs/requirements.txt`，3行 | 根 `pyproject.toml` | 无行内注释、无变化 |
| HarmBench `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 根21行；`adversarial_training/alignment-handbook/requirements.txt` 26行 | 无 | 根18/19新增声明并移除诊断，closure变完整；下述非零差异 |
| llm-dp-finetune `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 根6行 | 无 | 第5/6行是整行注释，继续忽略；第4行bare VCS继续未解析，其他不变 |

完整原行的当前 `packaging 26.3 Requirement` 语法检查结果为55行成功、3行失败、2行整行注释未解析。
这只是已捕获原文的当前语法观察，不执行产品扫描或候选A；也不判断pip安装语法有效性。
三个失败原行为HarmBench的两条尾注释和llm-dp的bare VCS。

## HarmBench不能写成零事实差异

根 `requirements.txt` SHA-256为
`a342b21c680e1d3102953f7937c97db58f095791f311953465148a87f25f5e9d`。

| 物理行 | 原始完整行 | 独立新增声明 |
|---|---|---|
| 18 | `art  # for ArtPrompt` | name/display_name=`art`，specifier/exact_version=`null`，source_file=`requirements.txt`，line=18 |
| 19 | `tenacity  # for ArtPrompt` | name/display_name=`tenacity`，specifier/exact_version=`null`，source_file=`requirements.txt`，line=19 |

两个完整原行均不能由当前 Requirement解析。字面前缀 `art`、`tenacity` 的单独当前语法检查均成功，
`url is None`，没有specifier；这些预写字面前缀没有经过未来normalizer求值。
两条声明按现有物理行顺序进入根节点；合并声明总数从45变47，原有45条声明内容与顺序保持。
从 `Declarations.unparsed` 和 engine合并diagnostics中精确移除：

```text
requirements.txt:18: art  # for ArtPrompt
requirements.txt:19: tenacity  # for ArtPrompt
```

本根无include，以上是仅有两个grammar error，因此其 `closure.complete` 从false变true，
package set增加art、tenacity，source set仍只有根 `requirements.txt`。
已有range/unversioned条目仍在，故 `is_exact` 保持false，不新增requirements-as-lock。
嵌套alignment-handbook root仍complete=true、is_exact=false；其既有逐包exact信用全部保留。

其他requirements roots的完整性/is_exact也已逐项预写：lm-eval和LlamaFactory均true/false保持；
llm-dp因bare VCS仍false/false；FastChat没有requirements closure。全部五份文件无include，
D-G final-node frontier、depth、读边界和来源集合不产生新变化。

## 边界如何约束本批来源

- 候选A的文件veto是：任一捕获物理行 `rstrip()` 后以反斜线结束，整文件禁用新增comment fallback。
  五份原文连任意反斜线字符都没有，因此没有命中veto的行；这不是只检查18/19行，也没有缩窄正式veto。
- 原route先处理include/directive和字面 ` @ `；本批requirements没有这样的原始行。
  不将可能位于注释后缀的 ` @ ` 先删除后改走ordinary。
- 先解析完整原行；只有完整行失败才能尝试新前缀。HarmBench恰两行满足这一先决条件，
  其他成功原行不重解释；llm-dp bare VCS既无适用分隔符也继续原行为。
- 新前缀必须满足 `req.url is None`；本批两个字面前缀均满足。不能据此推广到URL/tab-`@`变体。
- 只有requirements图ordinary分支在本提案范围。三份pyproject保持原TOML/PEP621/Poetry合同；
  不修改共享 `_add_requirement_line`，不把相同fallback应用到其他manager或embedded pip。

## 消费者与未来验收范围

| 消费者 | 本批独立预期与源码理由 |
|---|---|
| 完整 dependency facts / graph | HarmBench有上述非零声明、unparsed、package set、complete差异；不能仅比较summary。其余四项不变 |
| `env.dependency_manifest_present` / `env.lockfile_present` | 原manifest存在性不变；所有requirements roots仍非exact，没有新增格式锁或requirements-as-lock |
| `env.llm_critical_deps_pinned` | art/tenacity不在 `core/envinfo.py` 的critical集合；既有critical use、exact/qualified信用、D-F/D-S→D-L→D-M→D-G优先级及证据不变 |
| profiles / hints / evidence | `profiles/detect.py`仅按声明名匹配dependency signals；全部shipped profile源码中无art/tenacity，五项目无自定义profile来源；原import、README/config及其他检测源未改 |
| L0 / L1完整AuditReport与退出码 | findings/summary/既有evidence预期不变；diagnostics不是AuditReport字段，不能因JSON相同忽略它 |
| 默认audit文本 / verbose | `engine.py`合并unparsed；`cli/scan_diagnostics.py`仅verbose展示这些旧诊断。默认文本不变；HarmBench verbose精确少两行 `scan: ` 加上述原诊断 |
| init / 默认export | init的profile/hints/scaffold及Python覆盖诊断来源不变；export消费audit findings，默认diagnostic呈现不显示这两条unparsed。生成文件、L1、默认export预期不变 |

完整事实比对器若保留declarations/unparsed或graph字段，HarmBench必须显式接受这组差异，不能复用D-G的
“所有facts零差异”结论。后续P-B仍须五项目fresh L0+facts/diagnostics，并按受影响消费者执行
一次性副本init→L1、默认export及HarmBench verbose断言；既有gold原字节保留，补充只依据独立来源及具体接受。

本P-A的完整产品质量门、Gate A、Gate B均 **NOT_APPLICABLE**；这里没有任何产品Gate PASS。
普通提案不激活里程碑资源门，原metadata/HF403及其他资源状态沿原报告，不由本页解除。
没有网络、付费API、GPU、安装、外部提交或版本发布。
