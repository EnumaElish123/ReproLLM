# D-M-S：独立验收预期（尚未执行未来政策）

基线 `88a26ee`；规则合同来自现行 §12.2／§12.3.6 与本轮拟议 §12.3.7。
下表是接受后 P-B 的测试要求，不是实际测试通过清单。
除明确说明外，fixture 有 `z.py: import torch`、完整 Python 采集、无 lock／exact／其他失败。
W = 当前使用但无 pin 的 FAIL/WARNING；S = 提案下沿 D-M 的 SKIPPED/INFO。
“保留”要求完整声明／lock／诊断／barrier／读取轨迹相等，不只是计数相等。

| ID | 输入维度（分别参数化） | 独立预期 |
|---|---|---|
| A01 | project/tool/有效tool内poetry：false、0、空串、空列表、非空错误类型 | 新 invalid_structure；W→S；不凭 raw falsey 当 absent；旧 qualification/barrier 保留 |
| A02 | project/tool/poetry 缺失、正确空映射、tool.ruff 配置 | 不新增 issue；结果保持；build-system/group 配置不扩展 |
| A03 | project.dependencies：错误容器（含空映射/false/0/空串） | 新 issue，W→S；不新增任何 declaration |
| A04 | project.dependencies：缺失或 [] | 无新 issue；W 保持；没有内容不是失败 |
| A05 | deps = ["numpy==1.26.4", 7, "torch>=2"] | 保留两条及顺序、numpy exact；只对无信用的 torch S |
| A06 | deps = ["torch==2.5.1", 7] | 保留 torch exact；不产生其 missing-pin finding；不伪造 per-package PASS |
| A07 | deps 非str成员：bool、整数、列表、映射 | 均触发；合法str与坏成员混排时继续捕获合法兄弟 |
| A08 | optional-dependencies：错误外层、错误组值、组中非str | 分层独立触发；其他合法组和成员保留 |
| A09 | optional 缺失、{}、group=[] | 不新增 issue；group名语法不检查 |
| A10 | poetry.dependencies：非映射（含空list/false/0/空str） | 新 issue；旧提取/manifest/项目根保持 |
| A11 | Poetry 单包数组、transport/source-only dict、非str version | 不因这些值新增结构issue；记录当前结果，不声称完整支持或有效 |
| A12 | Pipfile packages/dev-packages分别非mapping，另一个section有效 | 新 issue；保留有效section与exact；任一坏section足够触发 |
| A13 | Pipfile absent/{}、单包来源dict和其他value、custom category | 无新增issue；不能把无version视为缺结构 |
| A14 | environment root：[]、false、0、字符串 | 新 issue，W→S；保持旧presence与barrier |
| A15 | environment 空文件、显式root null、{} | 无新增issue，旧行为；明确是兼容例外，不是完整格式证书 |
| A16 | dependencies存在但null/false/0/空str/{} | 新 issue；raw存在和缺失分开；不得被or[]吞掉 |
| A17 | dependencies 缺失或 [] | 无新增issue，旧行为；不加缺字段验证 |
| A18 | dependencies 列表含非str非dict，如null/bool/数字/list | 新 issue；有效Conda字符串/嵌入pip保留 |
| A19 | pip存在但非list（含null/false/空dict/空str） | 新 issue；其他有效成员保持 |
| A20 | pip list部分非str、部分有效exact/loose/空str | 非str触发；有效exact保留；空str属grammar排除，无新类型错误 |
| A21 | unknown installer/selector/空dict，或pip+unknown键混合 | 未指定键不检查；pip字段仍按表检查；不声称unknown mapping被理解 |
| A22 | 有结构缺口；合格格式lock包含torch | credit优先；保留qualified结果，不新发missing-pin |
| A23 | 无关子项目结构缺口＋另一项目exact | 全仓exact优先；失败位置不能撤销其他源的pin |
| A24 | 结构缺口＋关联坏lock；或D-L已满足 | 分别保留D-F/D-S、D-L原消息和证据；不追加较低优先级结构路径 |
| A25 | 正文失败源 a 与结构失败源 z 共存 | 沿D-M S；首条use证据后按路径合并；新路径导致证据delta，即使状态没变 |
| A26 | 无关失败源＋torch和numpy当前均无信用 | 两包均可能S；影响范围全仓，不套用lock关联边界 |
| A27 | 无已知关键包；全已获信用；Python coverage未知 | 不创造use；原applicability/空结果/primary-Python veto保持 |
| A28 | 修复坏成员为torch exact、或删除错误结构 | 前者恢复信用；后者按剩余真实输入恢复W；不保留过期issue |
| A29 | 只有缺pin规则的CLI gate：warning／override critical | 预写完整JSON及退出1→0；无其他规则遮蔽；FAIL-only override不作用S |
| A30 | 独立规则warning、ignore/suppression、默认文本/export | 退出/展示沿现合同；完整JSON保留；文本/export须预写明确断言 |
| A31 | 同包冲突exact、requirements宽松行/坏grammar/include | 现有exact/requirements合同保持；不扩展本切片 |
| A32 | 两次相同输入、既有历史JSON、遗留手工Declarations对象 | 字节确定性/默认空字典/旧读者兼容；不重写旧记录 |

## P-B 检查映射

- `tests/unit/core/test_deps.py`：类型表所有边界、partial extraction、读取次数、原diagnostic／barrier原样、默认字段及恢复。
- `tests/unit/rules/test_env.py` 与 `test_dependency_lock_scope.py`：credit、D-F/D-S→D-L→D-M、全仓影响、no-use/empty结果、完整evidence。
- CLI audit / scan diagnostics / export：新增SKIP的完整JSON、隔离warning/critical门、suppression与可见性；不以别的FAIL掩盖门差异。
- 五项目：完整L0/facts、init生成的全部文件、L1/default export比较；历史独立oracle只在身份与输入兼容时复用。

本轮没有 pytest 收集、RED/GREEN 或未来产品执行；当前行为观察另列实际case ID。
上述测试名仅指定现有模块，不提供虚假的已运行测试数。
