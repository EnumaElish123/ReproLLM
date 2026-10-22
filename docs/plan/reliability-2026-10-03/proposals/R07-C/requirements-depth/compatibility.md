# D-G：兼容性、风险与不变项

状态：提案；没有实际新政策产物。

| 表面 | 约定 |
|---|---|
| 内部Declarations | 末尾新增tuple字段，默认空，保留旧位置参数顺序；无persisted schema |
| 旧writer→新reader | 旧JSON没有变化；不重写历史finding或schema_version |
| 新writer→旧reader | 使用现有SKIPPED/INFO及Evidence字段，结构仍可读；旧工具不自动理解新policy原因 |
| rule/threshold | 只新增有界missing-pin SKIP理由；exact/qualified、DF/DS→DL→DM优先级保持 |
| 命令退出 | isolated warning/critical门可1→0；独立qualifying findings仍可1 |
| suppression | existing每status suppression合同保持，包括追加ignore证据和reason |
| text/export | 维持当前显示，text可PASS带skipped，defaultexport隐去SKIP；不改renderer |
| source与采集 | 无新增read/candidate/probe/网络，原reader安全边界不动 |
| graph/lock | 不改depthlimit10/roots/edges/closure资格/requirements-as-lock；新事实不授予credit |
| schema/dependencies/version | 全部保持；不触及engine/redaction/scanner |
| 历史与gold | 原字节保留；五项目预期零变化并需fresh完整比对 |

最主要风险是全仓保守影响：已使用但无信用包可以因无关图的未展开target被SKIP。
目标并不一定存在或含pin；一个未被执行的candidate过滤/物理路径检查也不能凭空当作已知结果。
例如 depth11的`.venv/pins.txt`保守触发，与预算内已到达且排除的同路径不同。
这一差异来自实际捕获证据与预算顺序，必须连同具体方案接受，不能藏在实现细节中。

若不接受这一成本，备选B维持现WARNING与默认diagnostics；不应临时增设额外文件探测来绕开审议。
更精细的candidate-aware frontier会改变采集/查询行为，需要另一份具体设计，而不是本片隐含实现要求。

不使用 `unparsed` 或 `complete=False` 的统一替代：全局index option、fully captured cycle和非exact闭包不证明还有未捕获pin。
相反，literal22cases中的depth-unseen-exact给出真实可能性，later-shallow-root反例说明为什么要最终图。
这一推理只在固定capture view和当前受支持include合同成立，不声称pip完整解析或实验可复现。
