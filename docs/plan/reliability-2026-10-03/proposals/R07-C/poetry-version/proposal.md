# D-M-V 的具体 A / B

当前规范 §12.3.7 明确排除个别 Poetry/Pipfile version 字段类型。当前实现与它一致；本轮不是修复已确认的规范违背。
当前 Poetry helper 对 {version=0} 返回 (None,None)，caller 仍追加具名声明；没有失败标志，不能仿照 D-M-E 把 None 当解析失败。
{source="private-source"}、空白 version、合法非 exact 和 transport 字符串也可能缺少 exact 信用；它们不能被统称非法。

## A（推荐，待具体接受）

只在已成功解码且当前 _parse_pyproject 已遍历的 tool.poetry.dependencies mapping 中，对每个原 value 检查：

```python
isinstance(value, dict) and "version" in value and not isinstance(value["version"], str)
```

触发时在原循环 setdefault(path, "invalid_structure")；仍调用原 helper 并追加原声明，不改共享 helper。
不把个别值检查提前到 _invalid_pyproject_structure：否则同文件 PEP621 的 unparsed_requirement 可能被抢先，违背先因保持。
false/0/浮点/错误空容器/TOML 日期时间触发；TOML 没有 null。transport+非str 触发的只是显式字段类型边界，
不宣称 Poetry 安装拒绝、transport 优先级或隐藏 exact。transport+str、缺失 version、空白 str、caret/range/wildcard、
看似错误的 str、非 dict 整体值、multi-constraint 数组及未遍历 group 均不触发。Pipfile 不 opt in。

复用现有 D-M：信用 → D-F/S → D-L → D-M → D-G；仅原本缺 pin 的当前已使用包受影响，不改 use/applicability。
一条 unrelated/noncritical 包的失败也会全仓使其余关键包 WARNING→SKIPPED/INFO；这延续 D-M 保守政策，
字段非str 不能证明隐藏合法 exact，选择 A 的理由是有界且与既有结构缺口政策一致，不是逻辑必然。

典型例：import torch + requests={version=0}，当前 torch FAIL/WARNING；A 下 torch SKIPPED/INFO。
requests 具名声明、行号和 specifier/exact 仍保持；torch 若另有 exact 或合格 lock 信用则继续优先通过信用路径。
使用 D-M 原 message/hint、原 first declaration/import 加 distinct sorted source files 的 file evidence；不新增诊断。

必须接受的展示成本：孤立 warning/promoted critical 可 exit1→0；独立 warning 仍可失败。
FAIL-only override 不提升 SKIP；suppression/threshold不变。默认 text 可 PASS 并显示 skipped 计数，默认 export 失去原 notable warning，完整 JSON 留存 SKIP。
既有 D-F/S、D-L完整finding优先；D-M可多一个源路径但不附 D-G paths。SKIP 不授予信用，不证明完整分析或复现成功。

## B（保留现状）

不增 typed cause，按当前 captured-view 有界 WARNING 提醒缺 exact 信用。它不是对完整仓库不存在 pin 的证明。
version 字段提取缺口继续 OPEN；缺少全仓保守放宽，但与既有其他结构缺口政策暂不一致。选 B 不实施补丁。

## 文件、范围和后续

本 P-A 只改计划/提案/报告。接受 A 后预计产品仅 src/reprollm/core/deps.py 的现有 Poetry caller；
先补 core/rules/CLI 回归，再最小实现；同步现行规范、CHANGELOG 和最终报告。若无 schema 变化则不导出新 schema。
不改 engine/redaction/schema、scanner、Pipfile helper、规则ID、依赖、gold、历史记录或发行版本；不申请 D-41 越界许可。
验收见 [未来表](acceptance-cases.md)，规范内容以 [精确未应用 patch](spec-proposed.patch) 为裁决对象。
