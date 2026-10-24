# 兼容性与保守成本（条件设计，未执行）

| Writer → reader / 表面 | 接受 A 后预期 | 当前 P-A 证据边界 |
|---|---|---|
| 旧 audit/run/export → 新 reader | 原字节、schema 和已保存 finding 原义保持；不重算历史 | 未来 P-B 加载/历史字节回归 |
| 新 audit → 现有 reader | schema 不变；已有 skipped/info 枚举可读，finding 语义会变化 | 语法可读不等于语义不变 |
| 新完整 JSON → export | 完整记录含 SKIP；默认 notable 列表会失去原 warning/critical | 需未来 JSON/text/export 联合断言 |
| 内部手工/legacy Declarations | 失败字典仍默认空；不加持久化字段 | 需未来构造/序列化回归 |
| 旧 exact 或 qualified-lock 信用 | 仍优先；触发不授予/撤销信用，无 per-package PASS | 未来核完整 record/finding |
| profiles/hints/init | 原 captured inventory 不变，独立输入下无预期差异 | 不能由 summary 数量代替完整比较 |

影响全仓，不能按局部 format-lock owner 限制 D-M。`nested/Pipfile` 的非关键 requests.version=0 可以影响根 torch，甚至所有剩余 used/uncredited critical packages。
这一类型缺口不能证明合法 pin 被隐藏；恢复字段后可能仍没有 pin。全仓保守 SKIP 是 A 要接受的取舍。
保留当前 in-use set 和无关键包 applicability；不从锁包名单创造 use。信用优先后按 D-F/S、D-L、D-M、D-G，不能把 D-G paths 追加给 D-M。

同一文件先因保留，section 错形仍走原 precheck/barrier；新 entry 检查只 setdefault，不扩大 barrier。
多个文件可扩大 D-M 证据，即使状态此前已 SKIP。全部业务字段须比较，不能只看 warning/skipped 计数。
FAIL-only severity override 不提升 SKIP；suppression/threshold 和独立 qualifying warning 维持原合同。
孤立 warning 或 promoted critical 可能 exit1→0，默认 text 的 PASS 不表示复现成功；default export 的 notable 内容会减少。

Pipfile `"2.5.1"` 仍无 exact；`"==2.5.1"` 保持现有 exact 合同。Poetry 的 bare exact 不移植。
transport/source/options、任意字符串、whole 非dict package、custom category 不新增检查或支持；这些控制不是有效性或完整性证明。
行号维持现有 index/fallback，不能顺带修复跨 section 的索引行为。依赖图、诊断、读取、候选、预算、根资格、锁关联不变。

五项目若新鲜源盘点均无 Pipfile，仅可给出条件零影响预期；它们不覆盖新触发分支。P-B 仍须 fresh Gate A 与独立 synthetic regressions。
本片无 schema/version bump 或迁移重写；不调整 gold。若实现需要不同范围，先更新提案再裁决。
