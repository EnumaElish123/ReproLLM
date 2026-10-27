# D-M-CE 当前行为、观察范围及重放

观察源为 `38b59cc41f8870b63f00321b8278cfc88b14a86b`、ReproLLM 0.7.0。
本页只描述现有源码；候选政策执行次数为 0。

## 两层独立当前观察

1. 独立作者先冻结 32 份 direct-helper literal 预期，再调用原 `_add_conda_entry`，
   32/32 匹配：12 份提前返回省略、20 份保留声明控制。原件保存在外部，
   [source-index.json](source-index.json) 绑定输入、观察器和结果哈希。
2. [冻结的 36 份集成输入](integrated-cases-frozen.json) 在首次执行前写好当前 literal
   预期；每份 6 项，共216项。真实非 Git scanner、原依赖解析和三个原始 env rule
   的观察全部匹配。三个全新目录的完整 JSON 逐字节相同，SHA-256 为
   `38099eca4de0db37064148a10f7d30a65b631ee01361804b3c889847de89f2e4`。

36 份记录保留完整 Declarations、project roots/barriers、锁 inventory/credit、
Python 捕获结果、scanner read/list/candidate 轨迹、Requirement/版本 helper 轨迹，
以及三个 raw rule 的 applies、skip reason 和全部 Finding 字段。
Declarations 不含完整 RequirementsGraph.nodes/closures；本观察没有额外截获该图，
不能把此文件叫作完整 requirements graph 验证。

128 份产品 Python 源文件在观察前后相同，53 个已导入产品模块核对源码哈希。
禁止 network/subprocess/heavy import；installed_versions 固定为空，不代表真实安装环境。
CE34 的 Python coverage gap 是显式构造的 seam，不是真实扫描预算截断。
helper 轨迹包装只转调原实现；没有加载或执行 prepared patch。

独立复核者未执行观察器或候选产品，通过源码和冻结字面预期重建核对全部216项、
108个完整 raw rule 对象、输入和导入模块身份，见
[current-observation-review.json](current-observation-review.json)。

## 纸面候选影响，未执行

若未来接受 A，按两处原返回谓词有23个集成案例触发新原因；其中12例现有
WARNING 将变为 SKIPPED。其余案例保留信用/较高优先级/no-use/已有D-M结果，
有的仅改变内部 first cause 或增加新 source evidence。

- CE24：whole-document invalid_structure precheck 保留，即使结构问题在后面。
- CE25：先失败的 pip 保留 unparsed_requirement。
- CE26：先 Conda 后失败 pip，未来内部原因应为 unparsed_conda；现有 D-M Finding 全文不变。
- CE34：D-L finding 完整优先。
- CE35/36：原 D-M Finding 未来只增加有序的新 environment source evidence。

这是对精确补丁的纸面推演，不是候选对照、测试 GREEN、CLI exit 或 renderer 实测。
未执行 engine、audit/init/export 命令、阈值、override/suppression、五项目 Gate A、
GPU、付费或发布验收。未来测试合同在 acceptance-cases.md，全部 NOT_EXECUTED。

## 复现

使用固定基线 checkout 和已安装的兼容轻量依赖。将
[观察器文本](current-observer.py.txt) 原字节复制到临时 `.py`，使用新目录：

```text
python current-observer.py --repo <baseline-checkout> --cases <packet>/integrated-cases-frozen.json --root <new-empty-directory> --output <new-output.json>
```

观察器拒绝错误 HEAD、已存在的 root/output；记录 source/import/input 哈希并验证
literal 预期。保留 real scanner 与明确环境控制，不安装或执行 Conda/solver。
公开 integrated 输入和 observer 支持当前行为重放；仅凭外部文件哈希不能复验
未公开的 helper 原件、Git 原始命令或完整来源清单。

第一次集成观察成功，但未单独持久化耗时。随后两次带收据观察分别
0.433496秒、0.445853秒，exit均0；不将累计时长写作整会话墙钟。
[replay-receipts.json](replay-receipts.json) 保留该计时边界。
