# D-M-P：五项目 PEP 621 字符串来源与预写影响

日期：2026-10-23；P-A 基线 `cc6e891c07aea9c8d585e80e2a14eff3b98b32af`。
状态：**SOURCE_EVIDENCE_ONLY / PREDICTED_NOT_EXECUTED**。
本轮只核查 `project.dependencies`、`project.optional-dependencies` 内已有
`Requirement` 调用所接收的字符串，不执行 ReproLLM 或未来政策。

[机器可读证据](portfolio-source-evidence.json)记录五个固定 pin、公开 origin、
读取前后 tracked/untracked clean 状态，以及 59 条只读 Git 命令的退出值、耗时和原始流 hash。
五原始 checkout 的 HEAD/origin 均符合固定输入，前后身份相同、状态为空。
命令原始流仅在内存读取；公开文件保存字节数和 SHA-256，不声称另有已归档原日志。

## 来源与独立核验

从每个 pin 的 `git ls-tree` 枚举相关文件，逐一读取 `git show <pin>:<path>`，
核对 Git blob object ID、blob SHA-256、工作文件 SHA-256 及原始字节相等。
共 12 个相关来源：**8 个既有受支持声明文件（3 个 pyproject、5 个 requirements）**，
另 4 个 setup.py/setup.cfg 仅作为排除边界。没有 Pipfile、environment 或 Poetry dependency table。
JSON 保存各文件 hash、物理行数和固定源码链接，不复制任何完整目标仓库文件。

三份 pyproject 用标准库 `tomllib` 独立解码；独立的单行 TOML 字符串词法定位逐组核对
全部字面量解码序列等于 `tomllib` 数组，再逐项调用 `packaging 26.3 Requirement`。
未导入产品模块或复用产品位置索引。每个成员保留精确键路径、数组下标、物理行和列、
公开依赖字符串、原 token/value hash，以及独立解析结果；列号从 1 开始且末列包含在内，数组下标从 0 开始。

| 项目 / 固定 pin | 受支持来源与实际类型 | D-M-P 独立来源结论 |
|---|---|---|
| lm-evaluation-harness `b954108c9baaaa934b4ad842033b31a97ee30816` | [pyproject:20–35](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L20)：14 个 dependency str；[optional:52–106](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L52)：31 组、84 个 str；另有 Japanese leaderboard requirements 4 行 | 98 个 scoped string 全部成功解析；0 个新触发 |
| HarmBench `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 根 requirements 21 行及 alignment-handbook requirements 26 行；没有 pyproject | 不存在 scoped string；0 个新触发 |
| LlamaFactory `673048c6a543cbbeaed5b8444b8223dc4e23c721` | [pyproject:38–76](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L38)：31 个 dependency str；optional-dependencies 缺失；另有 docs requirements 3 行 | 31 个 scoped string 全部成功解析；缺失 optional 不是失败；0 个新触发 |
| FastChat `587d5cfa1609a43d192cedb8441cac3c17db105d` | [pyproject:15–19](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L15)：15 个 dependency str；[optional:21–26](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L21)：5 组、19 个 str | 34 个 scoped string 全部成功解析；0 个新触发 |
| llm-dp-finetune `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 根 requirements 6 行；没有 pyproject | 不存在 scoped string；0 个新触发 |

合计 **163 个 str，163 个独立解析成功、0 个失败**，包含各字段内的重复声明，不是唯一包数。
这只证明固定源文本可被当前既有 Requirement parser 接受；不证明可安装、环境相容、解析器完整或所有包已锁定。

三份 scoped 文件的 blob/worktree SHA-256 分别为：

- lm-evaluation-harness：`88b654cba602d6d1bd2ed8cd164f960ebfe325344430345d83e7be0c4a1e72e1`。
- LlamaFactory：`d2d044de25f84d319338de30299437ee882650e2a998af50f617bfbb5964becf`。
- FastChat：`413be30fdc6b5c94746acc86197c447c5ce75d240013e08d9aa57c1766196cbe`。

## 排除边界与既有 D-C 基线

本片不改变 requirements 图或共享 requirement-string parser 的其他调用者。
HarmBench `requirements.txt:18–19` 的 `art`、`tenacity` 已由接受并交付的 D-C 捕获；
45→47 条声明、两条旧诊断消除和 root closure 修复已经属于当前基线。
**D-M-P 不再次产生这组 delta**；应保留现有 47 条及其顺序、图和诊断结果。
llm-dp `requirements.txt:4` 的 bare VCS 仍维持原合同，不能由本片改成支持或新增 manager 字符串失败。

- lm-evaluation-harness `pyproject.toml:108–114` 的 dependency-groups 含 include-group mapping；
  它不在本片，也不能作为 PEP 621 两字段的坏成员。
- HarmBench `adversarial_training/alignment-handbook/setup.py:129/131` 的
  `extras_require`、`install_requires` 均为 AST `Name`，不是字面量参数。
  本轮仅静态读取其形状，没有执行 setup.py 或求值变量。
- llm-dp `setup.py:4` 仅调用 `setup()`；实际包装声明在 `setup.cfg:14–27`。
  setup.py/setup.cfg 不因本片成为受支持依赖来源，其中的 exact/URL 不能新增信用或失败。
- environment 的 embedded pip、Poetry/Pipfile 单包值、其他 manager、build/dynamic/groups、
  包名/版本的进一步校验、遗漏候选和广义完整性继续沿各自现行边界，不由本页裁决。

## 完整输出的预写验收

在 D-M-P 仅记录上述两个 PEP 621 位置的**既有 Requirement 调用失败**、不改变已有成功提取的前提下，
五项目均未触发新增事实。相对 `cc6e891`，以下完整结果逐项预期 **ZERO DELTA**：

| 比较面 | 五项目预期 |
|---|---|
| declarations、顺序、exact/qualified lock 信用、project/barrier、requirements graph 与 lock inventory | 完整保持 |
| unparsed、扫描 diagnostics、已有失败证据及优先级 | 完整保持；不把 D-C 历史差异再次应用 |
| L0/L1 完整 findings、profiles、hints、evidence、路径、summary | 完整保持；不只比数量 |
| 默认/verbose audit 文本、完整 JSON 与退出码 | 完整保持 |
| init 的全部生成文件和默认 export | init/export 逐字节保持；只有 AuditReport 根时间/版本字段适用 T-02，其他业务结构不使用该豁免 |

这是 **PREDICTED_NOT_EXECUTED**，不是五项目 Gate A 通过，不使用当前产品输出决定 gold。
五项目没有新失败分支，不能替代独立 synthetic：未来接受后的 P-B 须先覆盖坏/空/空白字符串、
有效兄弟部分提取、已有 exact/qualified 信用、各失败优先级、恢复、独立阈值及文本/export 可见性，
再在最终产品输入上执行适用完整质量门、fresh 五项目 Gate A 和受影响验证。历史 gold 保持原字节。

## 资源与当前会话分类

- VAL-R01 的 H2/native/capture/diff/export PASS 绑定历史候选 `948d16423023027fff77322b8a872acaba306691`。
- VAL-R02 的正式付费 judge pair PASS 绑定历史候选 `75d1b065e9f0e3eeafa8e480e195a2a2ddbe95b5`。
  二者均不转写为当前 P-A 或未来候选的新鲜通过。
- VAL-R03 仍 BLOCKED：最新账本保留五个原始 metadata manifest 缺口和认证后 restricted 小文件 403。
  本轮未发起新 HF 请求，不能把旧拒绝访问处理当成功访问。
- A02 真实独立试用/反馈仍 PENDING；A03 草稿不等于提交或获批，申请身份、角色、组织信息和提交授权仍待申请人确认。

当前为文稿/计划 P-A：完整本地产品质量门、fresh 五项目 Gate A、资源 Gate B 均
**NOT_APPLICABLE**，不是 PASS。资源完整矩阵和广义 R07-C 不因本页关闭。
本轮没有 GPU 执行、付费 API、上游脚本执行、外部申请提交或版本发布。
