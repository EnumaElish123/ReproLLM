# D-M-CE 具体 A/B

状态：PROPOSED。依据现规范 §12.2、§12.3.6–12.3.12 及当前 `_parse_environment` /
`_add_conda_entry`；本轮不把现行一致行为描述为规范违背。

## 当前问题

`environment.yml/.yaml` 的已解码 `dependencies` list 中，native str 进入同一个
helper。它可能完全不产生声明：name-pattern 无匹配，或匹配后 rest 以 `::` / `/`
开头。这包括当前提取器不支持的 channel/subdir 形式，也包括空白、前导 wildcard
及某些多行字符串。省略不意味着 Conda 语法非法；官方语言大于本工具的有限子集。

当前两分支仅添加固定 unsupported 诊断，未写入声明失败事实。若已有 `import torch`，
省略 `conda-forge::requests` 后仍可能按已采集视图报告 torch 缺少 exact。
单条缺 pin finding 不能同时证明所有依赖正文都被完整提取。

## A（推荐，明确接受具体范围和代价后实施）

内部 `DeclarationReadIssue` Literal 新增 `unparsed_conda`。仅在 helper 的两个原
提前返回点，以原逻辑 source path 执行：

```python
result.declaration_read_issues.setdefault(path, "unparsed_conda")
```

触发谓词严格等于原 `_CONDA_NAME_RE.fullmatch(entry.strip()) is None`，或匹配成功
后的 `rest.startswith(("::", "/"))`。仍执行原诊断和 return；不提取 channel 中
的包名、不恢复 exact、不执行 Conda、不校验整个 MatchSpec。

新增专用 code 表达“现有提取器省略了实际访问的 native 字符串”，不复用代表实际
Python Requirement 失败的 `unparsed_requirement`。两者均是内部事实，不增加持久化字段。

保留所有到达原 append 的路径：裸包名、数字 single-equals 前缀、double-equals、
字面 build、数字范围和其他 suffix。**同样出现 unsupported 诊断的数字范围不能
触发新原因**；URL-looking `https://...`、separator/slash 前有内空白等当前保留 head
的形式也不触发。unknown installer/selector mapping 和未遍历内容不扩展。

## 原因顺序与不变量

原整段结构 precheck 先于循环，已有 invalid_structure 即使来自物理位置靠后的条目
也优先。原 entry 调用次序中，先 pip failure 则保留 unparsed_requirement，先 CE
则保留 unparsed_conda；每 source 一个原因。原解析器其他赋值与读取时序不改。

不增加 uncertain-directory barrier、候选、读取、重试、include edge、包使用证据
或 lock origin。保留所有有效兄弟、其他声明、原外层依赖序号、line fallback、
project roots、锁集合和配对。不能从被省略原文为未被采集的关键包合成 finding。

规则直接复用现有顺序：exact/qualified credit → D-F/D-S → D-L → D-M → D-G。
较高优先级 finding 全文保留。若此前已由其他 D-M source SKIP，可能只增加新的
distinct sorted file evidence；需比较完整 finding，不能只看状态总数。
沿用 D-M 原 message、fix_hint 和首 declaration／否则首 import evidence。

## 具体兼容成本

现行 exact 信用是全仓 existential 汇总，D-M 也已采用全仓保守影响。接受 A 后，
无关子项目、非关键包或空白省略，都可能令所有剩余已使用、未获 exact/qualified
信用的关键包从 FAIL/WARNING 变为 SKIPPED/INFO。这并非从 Conda 有效性推导的
必然事实，空白字符串也不可能证明藏有有效 pin；它是本片独立产品取舍。

例如 `import torch` 加一个被省略的 channel-qualified requests 条目：当前 torch
为 WARNING，A 下为 SKIPPED/INFO。若另有 torch exact 或合格锁则仍优先获信用。
no-known-use 的原 applies=false 保持，SKIP 不授予信用或完整性证明。

孤立 WARNING 或用户提升后的 CRITICAL 门可从 exit 1→0。独立达阈值 finding
仍失败；FAIL-only override 不提升 SKIP，suppression 和阈值计算不变。
默认文本可能 PASS+skipped；默认 export 会少原 notable warning；完整 JSON 保留 SKIP。

## B（保持现状）

不增加 code、不应用规范补丁，继续当前 captured-view 的缺 pin WARNING。
避免本片新增全仓放宽，Conda 字符串省略的不完整性继续 OPEN。
保留诊断及“不宣称已完整采集”的限制；B 是可接受的政策选择。

## 实施与禁区

P-A 只交付提案、当前观察、精确未应用补丁和导航。接受后 P-B 先写 core/rules/CLI
验收回归并证明 RED，再最小实施、应用规范 §12.3.13、补 CHANGELOG 和报告。
计划产品仅 `src/reprollm/core/deps.py`，无 engine/redaction/schema 默认改动。
一次最终完整质量门、fresh 五项目 Gate A 与受影响消费者完成后推送 main，核对 CI。

Conda 保留声明的 grammar、其他 manager 值、solver、workspace scope、遗漏 use、
listing/framework 及广义充分性证书仍 OPEN。本片不授权发布、GPU 或付费请求，
不对外提交 issue 或申请。裁决对象是本目录两份精确 patch 及上述兼容成本。
