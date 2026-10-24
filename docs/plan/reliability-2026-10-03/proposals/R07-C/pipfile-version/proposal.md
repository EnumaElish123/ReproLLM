# D-M-PF：Pipfile 显式 version 字段的独立 A / B

状态：PROPOSED，推荐 A，尚未接受、未实施。D-M-PF 是 R07-C 局部标签，不是架构 D-nn。

当前规范 §12.2、§12.3.7 和 §12.3.11 明确区分 Pipfile/Poetry 的 exact 合同，并排除这里的个别 Pipfile 字段类型检查。当前实现符合现行规范；本轮准备政策扩展，不宣称修复规范违背。Poetry D-M-V 的接受不涵盖 Pipfile。

## A（推荐，须接受本片具体范围及成本）

只在现有 `_parse_pipfile` 遍历 `packages`、`dev-packages` 映射的原 entry 循环内检查原 value：

```python
isinstance(value, dict) and "version" in value and not isinstance(value["version"], str)
```

触发时 `declaration_read_issues.setdefault(path, "invalid_structure")`，随后仍执行原 helper 和 append。
一个 helper 调用点遍历两节；`allow_bare=False` 保留。false、0、浮点、错误空容器、日期时间均触发，TOML 没有 null。
transport+非str version 仅按该字段触发，不推断安装拒绝、transport 优先级或隐藏 exact。
不扩原 section 预检，不增 uncertain-directory barrier，不改行号索引或共享 helper。

缺失 version、任意字符串（空/空白/范围/通配/看似错误字符串）、whole 非dict值、数组、source-only/transport-only、未遍历 custom categories 均保持旧行为。
特别是官方 Plette 对直接数值 package 值另有兼容，不能由字段类型合同推断整个 Pipfile 的合法性。
helper `(None,None)` 或 `exact is None` 都不是失败标志。

复用 D-M：现有信用 → D-F/S → D-L → D-M → D-G。声明顺序、名字、specifier/exact、source 和当前 line/fallback、有效兄弟、两节、原先原因和全部信用不变。
现有共享 `pipfile.packages` 行号索引可能给 dev-packages 回退值；本片不把它改成物理 version 行，也不宣称其已有精确物理位置。

例如 `import torch` 与 `requests={version=0}`：当前 torch 缺 pin 为 FAIL/WARNING；A 下可变为 SKIPPED/INFO。requests 的具名声明仍在。
若另处有 torch exact 或合格 lock 信用则信用优先；较高 D-F/S、D-L finding 全量不变。D-M 已 SKIP 时可能新增 distinct sorted source evidence，不能只比状态计数。

字段类型并不能证明藏有合法 exact。选择 A 的理由是有界记录已知提取缺口，并与既有 D-M 保守政策一致；全仓放宽是独立产品选择。
无关非关键包、另一个子项目也可能使所有剩余已使用且未获信用的关键包 WARNING→SKIPPED。
孤立 WARNING／提升后 CRITICAL 可 exit 1→0；默认文本可显示 PASS+skipped，默认 export 不再含原 notable warning，完整 JSON 保留 SKIP。
独立 qualifying finding 仍可失败；FAIL-only override 不提升 SKIP；suppression、threshold、applicability 不变。

## B（保留现状）

不添加 typed cause，不应用规范补丁，继续按 captured view 提醒缺 exact；它不证明完整仓库不存在 pin。
避免新增 repository-wide 放宽，但个别 Pipfile version 提取缺口继续 OPEN。B 同样是可接受的明确政策选择。

## 文件与执行顺序

本 P-A 仅提案、报告和三处当前导航。现行规范、产品、测试、CI、工具、依赖、schema、gold、历史报告和版本均不改。
接受 A 后 P-B 先补 core/rules/CLI RED 回归，再仅改 `src/reprollm/core/deps.py` 原 Pipfile 循环，应用精确规范补丁并写 CHANGELOG/报告。
预计不触及 D-41 的 engine/redaction/schema；若实际需要则停止该越界部分，另备具体审阅。
按验证流程一次最终质量门、fresh 五项目 Gate A 和受影响扩展；资源门逐项适用，缺资源不能 PASS。main 推送后核精确 HEAD 五项 CI。
无 release、付费 API、GPU、外部 issue/申请写入。具体裁决对象为 [未应用补丁](spec-proposed.patch) 和 [兼容成本](compatibility.md)。
