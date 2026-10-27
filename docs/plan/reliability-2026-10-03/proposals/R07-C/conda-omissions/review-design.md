# D-M-CE：独立边界与验收设计复核

状态：PROPOSED。候选策略执行 0、候选补丁应用 0；没有实施产品修改。
本复核依据当前 `_parse_environment`、`_add_conda_entry`、`Declarations`、
`LlmCriticalDepsPinnedRule` 及最近 D-M-PF 的 P-A 分界编写。
它建议局部方案 A，不代替维护者接受本次具体规范／实现补丁。

## 推荐边界

仅在既有 native Conda helper 的两处省略声明的提前返回增加内部事实：
一处为 `_CONDA_NAME_RE.fullmatch(entry.strip())` 返回 None，另一处为已提取 suffix
以 `::` 或 `/` 开头。两处使用 `declaration_read_issues.setdefault(path, "unparsed_conda")`，
为 `DeclarationReadIssue` 增加该字面量；保留旧诊断后返回，其他声明提取不变。

这表示本工具的当前有界提取省略了一项 native str，不能写成该 MatchSpec 不合法、
实际 Conda 安装失败、已知隐藏 exact pin 或完整 environment 无效。
`unparsed_requirement` 属于 Python Requirement 路径；`invalid_structure` 属于已接受的
解码后类型边界。这里使用独立内部名称更准确，不新增持久化字段或消费分支。

不存在“有 unsupported 诊断就失败”的宽规则。现有 `pytorch>=2.4` 会记录该诊断但保留
range declaration；wildcard／复杂 suffix 也会保留原 placeholder declaration。
带空白的 channel／slash、URL-looking、backslash 与 unicode suffix 等边界同样必须按
实际两处 return 判断，不能因看似复杂而扩大范围。数字 `==`、单 `=` 前缀及字面 build
继续原 exact 合同；本片不引入 MatchSpec parser、Python／Poetry 版本语法或 solver。

## 先存在的原因与遍历

`_invalid_environment_structure` 在 entry 循环前检查整个 decoded document。
因此，文本后面的 malformed sibling 可能已先记录 `invalid_structure`；本片必须通过
setdefault 保留它，不能宣称一定是物理上第一项失败获胜。
结构 precheck 后，embedded pip 的旧 `unparsed_requirement` 与新 CE 才按现有访问顺序
保留先存在的原因。每逻辑文件仍最多一个 issue，不改旧 precheck 的赋值或提前 return。

只处理既有 dependencies 列表实际交给 native helper 的 str。空串／空白串属于该访问；
embedded pip 的空串则沿用自己的旧跳过条件。未知 installer mapping、任意嵌套容器和
未访问字符串不进入本片。YAML aliases 只保留现有 decoder／循环的实际访问，不新增递归、
展开、去重或安全判断。多行 scalar 仍以既有 strip／fullmatch 为准；line 仍是原 list index，
不增加物理 YAML 行定位器。两个 environment 扩展名、同目录双文件歧义及所有候选／读取不变。

## 信用、输出及可接受成本

现有消费优先级保持：exact／qualified lock 信用，然后 D-F／D-S、D-L、D-M，再 D-G。
不添加新的 uncertain-directory barrier，不改变已有 project roots、nearest-project
关联、manager 匹配、lock membership 或 qualified origin。被省略字符串仍不创建 declaration、
in-use 包名或 lock origin；有效 sibling 和跨文件 existential exact 信用完整保留。

只要更高优先级条件成立，完整旧 finding 必须保留，不能混入较低优先级 CE 或 D-G 路径。
若原来已为 D-M SKIP，新文件的唯一变化可以是 sorted failure evidence 多一个路径。
原第一 declaration，否则第一 import evidence，及 D-M message／fix hint 均保持。
没有已采集 critical use 时仍保留 no-use applicability，不从原文合成缺 pin；现有
empty-result primary-Python veto 也不变。D-M 本身不依赖 Python coverage。

明确成本是全仓保守影响：无关子项目的非关键 native omission，也可让所有剩余当前已使用、
无信用 critical 包由 WARNING／提升 CRITICAL 改为 SKIPPED/INFO。这是维护者需要选择的策略，
不是遗漏类型本身证明了隐藏 exact。孤立退出 1 可变为 0，独立达到阈值的其他 finding 仍失败。
FAIL-only override、suppression 和 thresholds 沿用；完整 JSON 保留 SKIP，默认文本可能显示
Findings PASS 和 skipped 数，默认 export 可能不再包含原 notable warning。
SKIP 不授予信用、完整性或可复现性证明。

备选 B 是保留当前 captured-view WARNING 并将该 native omission 边界继续标记 OPEN；
这也是明确策略选择，不能称现行全仓缺 pin 警告已证明完整 absence。
既有 Poetry／Pipfile／requirements 局部接受没有自动批准本次新合同。

## 现有观察与未来验收的区别

独立准备的 32 项 literal helper oracle 先冻结，再运行当前真实 helper；32 项全部匹配。
输入和预期 tuple 没有调用产品 regex 来生成，执行没有 candidate patch 或 monkeypatch。
该观察仅覆盖当前 helper：12 项现有省略提前返回、20 项保留声明控制。
它不执行新策略、环境 full-parser、engine／CLI、manager 或正式五项目 Gate A。
源码前后 hash 与完整 current record 另存观察件，由主会话核对后决定公开表示。

[未来验收矩阵](acceptance-cases.md)的 36 组全部是 **NOT_EXECUTED**：
分别覆盖 core、rule、CLI、消费者和会话门。具体合同被接受后，先 RED，再最小实现 GREEN，
最终输入上执行一次完整质量门、fresh 五项目 Gate A 和受影响命令，记录完整差异及最终 CI。
五项目没有该 native 触发输入时，只能证明零适用性，不能替代这些合成触发回归。

本片无需改 engine／redaction／schema，因此不跨 D-41；若后来确需改动，必须另行明确审阅。
不改 scanner、依赖、版本、五项目 gold 或历史文件；无 manager／solver／资源调用或发布。
被保留的其他 Conda grammar、遗漏 use／候选／listing、README／config／framework 与充分证书
仍属于广义 R07-C OPEN 范围。本片不能据此关闭整个任务。
