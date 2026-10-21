# R07-C：已采集依赖声明正文的已知读取／解码失败（局部 D-M）

状态：**PROPOSED，正式规范、产品和测试补丁未应用**。基线 `aee6488078c3435dcc33b20a68cca8bda0d0ec57`。
上一批 D-S 已实现并通过完整本地质量、五项目及最终 HEAD 五项 CI；本提案接续其明确保留的一般声明失败分支。

## 当前合同与证据

规范 §12.2 保留仓库级 existential exact：任何一处实际采集的 exact 声明都可给同名关键包信用。
D-F/D-S 仅处理四格式锁的已关联失败；D-L 仅处理 Python 缺口与已采集锁成员。
§§12.3.1、12.3.4–12.3.5 将一般声明／requirements 的其他非空 WARNING 留在原合同。
因此现有 WARNING 符合当前 bounded 合同，但不能从正文读取失败推出全仓没有精确声明。

`core/deps.py` 三类 manager 解析入口已经捕获 `read_text` 返回 None 与文档解码错误，
requirements 实际图节点也已知道正文不可读；这些事实目前没有传给关键依赖规则。
例：`z.py` 导入 torch，而 `aux/pyproject.toml` 无法读取或解码。当前没有捕获 torch pin，规则输出 WARNING；
恢复该文件可能发现 `torch==2.5.1`，按现有 §12.2 足以改变结论。
失败源在其他子项目仍可能有这种作用，不能套用 format-lock 的局部来源边界来缩小该声明不确定性。

[五项目独立来源证据](portfolio/source-evidence.md)核对全部固定版本、公开 origin 和前后干净状态。
当前八个依赖候选正文可读，三份 TOML 可解码，五个 requirements 根均无 supported include。
各项目新增 body-failure 清单预期均为空；完整 gold delta 预期为空，不更改 gold。
这属于源码核查，不是新鲜 Gate A 或产品质量门。

## 推荐 D-M 合同

新增内部 `DeclarationReadIssue = Literal["unreadable", "invalid_syntax"]` 和默认空字典
`Declarations.declaration_read_issues`，只记录现有采集事实，不新增持久化字段：

| 来源 | 新增事实 | 明确排除 |
|---|---|---|
| 已发现的 pyproject.toml、Pipfile、environment.yml/.yaml | 现有安全读取返回 None；现有捕获的 TOMLDecodeError／YAMLError | 成功解码后的错误结构、条目 grammar、工具表是否真实声明依赖 |
| 现有 requirements 图已构造且通过候选检查的根／实际 include 节点 | **实际现有 read_text(source) 返回 None**，只记 unreadable | 没有读取的候选排除／未展开节点、错误 include 语法、cycle、depth、可读但不支持的行／指令 |

复用原安全读取及预算，禁止重试、读取被拒内容、增加 include 边或从诊断 prose 反推 typed 状态。
路径为既有逻辑相对路径。保留全部已捕获声明、精确版本、锁包集合、presence、barrier、诊断和读取次数。
requirements 缓存命中不重读；不存在的 supported include 目标只有在原图实际尝试读取并返回 None 时才入表。
None／空字典都不是完整格式或扫描证书。

仅处理当前已经使用的关键包，按顺序保留：

1. 已有 qualified-lock 或任一 exact 声明信用。
2. D-F/D-S 原 SKIP，及 D-L 原 SKIP（保留各自消息、证据和优先级）。
3. 仅剩余本应输出 used-but-unpinned WARNING 的包，在正文失败字典非空时改为逐包 SKIPPED/INFO。

第三步独立于 Python coverage，不创造新使用包、每包 PASS 或额外汇总 finding。
no-use applicability、全已获信用时的空结果和原 Python veto 均保持。

消息：

```text
{display} is used; a dependency declaration body could not be read or parsed, so missing pin evidence is not established
```

fix_hint：

```text
Review {display} declarations and failed dependency source files; restore readable, valid declaration bodies before deciding that exact pin evidence is absent.
```

证据先保留当前首个声明／import，再按路径字典序附全部去重的失败声明源，
`kind: file`、`path: 原逻辑路径`、`note: "{display} possible exact declaration unverified"`；其他字段默认不变。
规则 ID、别名、category、level、canonical 包顺序与 engine 最终排序不变。

## 兼容成本与边界

| 场景 | 当前 → 推荐 |
|---|---|
| 已知未获信用的包＋实际声明正文失败 | WARNING → SKIPPED/INFO |
| unrelated 子项目的坏声明候选，甚至可能仅是工具配置 | 也可能使所有剩余关键包保守 SKIP；不代表该源真的包含 pin |
| 其他位置存在 exact 声明／已有合格锁 | 原信用优先，保持 |
| 关联格式锁失败／D-L 已触发 | 保持旧分支消息和证据 |
| 不支持的可读声明／结构／include 图，未发生正文失败 | 原结果保持，继续 OPEN |
| 没有已知关键包／全已获信用 | 原 applicability／空结果政策保持 |
| WARNING 或 FAIL-only override 为 CRITICAL 的孤立门 | 可由退出 1 → 0；阈值和计数状态不变 |
| 同时有其他规则 WARNING | 仍可退出 1；不能误称 global D-M 留下某个未获信用包的 WARNING |
| ignore／suppression | 原 SUPPRESSED/INFO 合同保持 |
| 默认文本／默认 export／完整 JSON | 文本可显示 Findings: PASS 和 skipped 数；默认 export 隐去 skipped 数及旧 notable warning；JSON 保留新 finding |

字典影响范围必须是全仓：R06-B 保留的 exact 汇总不要求同项目／manager。
SKIP 不赋予声明或锁信用；原锁来源限定完全不变。此方案不能声称所有依赖解析失败已闭合。
旧 JSON 读者沿用现有 status/severity/evidence schema，默认程序门行为改变；无新 schema/version 或历史迁移。
原历史结果和资源验收仍绑定各自候选，不重写为新政策。

## 精确改动与验收

产品仅 `src/reprollm/core/deps.py`、`src/reprollm/rules/env.py`；规范和 CHANGELOG 补丁随附。
测试草稿在 core deps、env、依赖锁 scope 和 CLI audit 四文件新增 105 参数例／21 函数，明确修订 7 个旧函数的 11 个结果，其余 137 个旧定义 AST／原文不变；修订的 barrier 用例继续断言没有获得祖先锁信用。
不触碰 engine、scanner、redaction、schema、profiles、依赖版本、默认配置或五项目 gold；无需新增 D-41 受保护模块审阅。

[实现补丁](implementation-proposed.patch)、[规范补丁](spec-proposed.patch)、
[测试补丁](tests-proposed.patch)、[CHANGELOG 补丁](changelog-proposed.patch)均为待应用材料。
条件观察只在隔离进程加载精确外部源码，不作为正式 TDD／产品验收。
正式 P-B 在具体接受后执行：测试先 RED → 应用接受源码 GREEN → 完整受影响模块和静态检查；
最终同一输入一次完整质量门 → 五项目新鲜 Gate A → 全部五份 init/L1/default export 及专项比较。
完整 JSON 仅豁免规范根 T-02 metadata，不忽略嵌套值、类型、顺序或业务字段。
普通政策会话不激活里程碑／release；GPU、Hub、付费 API、原生 Gate B 为 NOT_APPLICABLE，不发布 tag/PyPI。

## 备选与具体决定

推荐本方案：manager 正文失败和实际 requirements 正文失败具有同一有限证据边界。
备选一是仅纳入 manager，把已明确尝试的 requirements 正文失败延后；代价是保留同型缺口。
备选二是保留所有现行 WARNING；代价是恢复声明可能推翻这些缺失 pin 结论，需继续明确其 bounded 范围。
不推荐因任何 unparsed 文本全局 SKIP，或按锁的同目录限制缩小本分支：前者范围不明确，后者与仓库级 exact 信用不一致。

具体待决问题：**是否接受 D-M 的这项正文失败合同及完整规范／实现／测试补丁，继续 P-B？**
[PROPOSED 决定](decision.json)与[spec issue 草稿](issue-draft.md)单独保留。
执行总则 §5.9 要求“不要把本包中‘建议的新行为’当成已经修订的规范”，
现规范又明确将一般声明失败留在既有接受范围外；本轮继续授权覆盖方案准备，不能代替这项新合同的具体接受。

其余 decoded 结构／entry grammar、一般 include 图、遗漏候选和包使用、listing、README/config/framework
以及广义充分证书继续 OPEN。D-M 交付不关闭整个 R07-C。
