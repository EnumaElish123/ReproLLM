# D-G 裁决时证据勘误与补充（2026-10-22）

本目录补充 [委托裁决记录](../decision-accepted.json)，不改原 P-A 的23文件快照、22例输入、观察或原决定。
本次由维护者明确委托 agent 裁决 D-G A/B，agent 选择 A；不是维护者逐字回复“接受 A”的记录。

## 原观察的准确边界

原 `depth-later-shallow-root` 与 `depth-later-shallow-root-loose` 的实际 roots 是
`requirements-z.txt`、`requirements.txt`；`-` 排在 `.` 前，浅根实际先展开。
它们证明最终目标已捕获时仍可保留深根的不完整 closure／depth 诊断，不能证明“后来浅根补捕获”的时间顺序。
原主文、议题草稿和兼容说明中的该时间顺序表述不应作为已验证事实。原始文件与hash全部保留。

此勘误不改变最终图谓词或所接受规范补丁。成功完成的当前遍历中，active／visited 早退已有node；
预算内排除或实际读取失败也会建立node。受支持边的最终目标缺node才表示未越过深度预算展开。
不得用旧诊断或 `closure.complete=False` 代替该谓词。

## 实施前新增的当前行为观察

[四个字面输入](inputs.json)、[完整观察](observations.json)、[观察器原件](observe_current_order.py.txt)
在旧产品 `38b4e2b` 上取得：exact／loose × 真实先深后浅／反序，共4次，0.2148106秒。
深根命名 `requirements-a.txt`，浅根 `requirements-z.txt`；反序案例交换角色。

真实先深后浅时，第一根结束尚无 `deps/10.txt`，第二根才读取该目标；目标只读一次。
反序也得到完整捕获。exact保持信用，loose保持旧WARNING；两种顺序的深根closure仍不完整。
正常 `scan_dependencies` 与逐root观察图的实际读取轨迹相同，源码前后hash相同。
控制为Git非仓库、installed_versions为空；audit hook拒绝socket、subprocess和重依赖import。
这些是当前parser／graph／rule观察，未来D-G执行为0，不是CLI、完整质量门、Gate A或CI通过。

P-B 的 G07/G08 必须断言实际root及读取顺序，保留本补充和原22例，不能用案例名字代替时序证明。
本目录的 [SHA256SUMS](SHA256SUMS) 覆盖补充正文和三份原始文件；原观察中的文件名指向私有原件，
公开观察器只追加 `.txt` 后缀，内容和hash相同。
