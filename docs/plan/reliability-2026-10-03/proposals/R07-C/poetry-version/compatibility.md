# 兼容性与保守成本

| 情况 | 当前 | A 的未来预期（未执行） |
|---|---|---|
| 已遍历 Poetry dict 显式 nonstr version，无先因 | 保留 named declaration，无新 issue | 保留同样声明，新增原 path 的 invalid_structure |
| 同文件已有 PEP621 parse failure | unparsed_requirement | setdefault 保留原原因，不能预检抢先 |
| 先有 container/read/decoder failure | 原原因／原控制流 | 原原因／原控制流不变 |
| dict 缺version／任意str／非dict／数组／未遍历groups／Pipfile | 原捕获行为 | 原捕获行为，无新原因 |
| exact/qualified credit | 先信用 | 仍先信用，不撤销或新增 |
| D-F/S 或 D-L 优先 | 原完整 finding | 原完整 finding |
| D-M 或 D-G 共存 | 原既有 finding | D-M可增加 distinct path／先于 D-G；不混合低优先证据 |
| unrelated 包／嵌套项目触发 | 剩余缺pin包原WARNING | 全仓保守SKIPPED，不套局部lock ownership |
| JSON/text/export 与门 | 原FAIL/WARNING | 原D-M message/hint/evidence；孤立exit1可0、text可PASS+skips、export可移除notable |

无持久化字段或 schema version 变化：旧 writer→当前 reader、新 reader→旧文档均保留原 schema 解析合同，
不自动重算历史 finding；新 finding 的现有 SKIPPED/INFO 字段也不需要新 reader。语法可读不代表结果语义未变化。
run/export/历史快照均原字节保留，无迁移重写；只对未来新 audit 采用被接受政策。

声明次序、姓名、specifier/exact、既有line值（包括原索引fallback）、read traces、roots/barriers、锁内容/关联、profile/hints/init inventory保持。
存在新 issue 不改变 format lock qualification；部分同包 exact 继续获信用。未受影响finding、suppression、fail-on和排序保持。
全仓SKIP不是对隐藏pin存在的证据；接受A必须同时接受保守成本。

不借字段类型扩大字符串/多约束/transport语法支持，不运行Poetry，不新增网络、依赖、schema或D-41受保护接口。
