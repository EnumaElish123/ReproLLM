# D-M-S：五项目声明结构的独立源码核对

日期：2026-10-22；提案基线 `88a26ee270c92c939140fe347b71f2909f8c7d97`。
状态：**SOURCE_EVIDENCE_ONLY / 未执行新产品或条件产品**。
机器可读来源、实际只读命令退出／耗时和哈希见 [source-evidence.json](source-evidence.json)。

本轮直接核对五个固定 checkout 的 HEAD、公开 origin 和 tracked/untracked clean 状态，
前后 30 项身份检查全部符合既有固定输入。使用 Git blob 和标准库 TOML 解码检查实际结构，
没有调用 ReproLLM、pytest、上游 setup、包管理器、网络或模型。
整个 Git 树中仍只有 **8 个受支持声明文件：3 个 pyproject、5 个 requirements**。
8 个工作文件均与固定 Git blob 原始字节相同，也与历史 R06-B 来源包的对应 blob 哈希相同。

## 实际结构与有限边界

三份 pyproject 的根、`project`、`tool` 均为 table，均没有 `tool.poetry`。
`project.dependencies` 均为 array，所有成员都是字符串。
存在的 `project.optional-dependencies` 均为 table，所有组值都是字符串 array；
LlamaFactory 没有该字段，按拟议合同保持 missing，不制造失败。

| 项目 / 固定 SHA | 独立源码位置及类型 | 本轮结构触发项 |
|---|---|---|
| lm-evaluation-harness / `b954108c9baaaa934b4ad842033b31a97ee30816` | [pyproject 第 20 行](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L20)：14 个 core 字符串；第 52 行 optional table 有 31 组、84 个字符串 | 0 |
| FastChat / `587d5cfa1609a43d192cedb8441cac3c17db105d` | [pyproject 第 15 行](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L15)：15 个 core 字符串；第 21 行 optional table 有 5 组、19 个字符串 | 0 |
| LlamaFactory / `673048c6a543cbbeaed5b8444b8223dc4e23c721` | [pyproject 第 38 行](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L38)：31 个 core 字符串；optional table 缺省 | 0 |
| HarmBench / `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 根及 alignment-handbook 两份 requirements；本切片不检查 requirements 语法或 include 图 | 不适用；0 新触发 |
| llm-dp-finetune / `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 根 requirements；本切片不检查 requirements 语法或 include 图 | 不适用；0 新触发 |

合计 **163 个 pyproject 依赖字符串**，包含各位置的重复声明；它不是唯一包数。
JSON 保存每个 array 的精确键路径、起始键行号、全部解码字符串、数量和类型断言。
lm-eval 另外一份 Japanese leaderboard requirements、LlamaFactory 的 docs requirements
也计入五份 requirements，但不进入新结构判定。

固定树中没有 Pipfile 或 environment.yml/yaml 声明，无法用五项目证明其新增边界正确；
这部分需由预写 synthetic 正反例验证。三份 pyproject 都没有 Poetry 声明，
不得从这里推断 Poetry dependency value 的完整 grammar；合法多约束列表等值不在本切片判错。
lm-eval 的 `dependency-groups`、所有 build-system/tooling 配置及 setup.cfg/setup.py
包装信息不作为新增依赖声明结构证据。特别是 DP 的 setup.cfg 精确版本、HarmBench
嵌套 setup.py 不会因为本提案变成受支持声明来源。

本来源核对采用的有限表是：pyproject 的 project/tool/poetry 容器与已有 PEP 621
依赖 array 成员类型、Poetry dependencies table；Pipfile 的 packages/dev-packages table；
Conda 的非 null 根 mapping、dependencies list 及其中已存在 pip 的字符串 list。
missing／正确 empty 不触发；Conda null 根保持 legacy；Poetry/Pipfile 包值、requirements
全部 grammar/include、其他 Conda mapping/selector 和遗漏候选均排除。
这不是原生包管理器 schema 校验，也不证明依赖字符串有效、可安装或完整锁定。

## 五项目完整输出的预期

相对基线 `88a26ee`，拟议 D-M-S 对五项目的**完整规则 findings、profiles、hints、路径、
diagnostics、依赖 facts 和生成 manifest 预期均不变**，不是只要求警告总数相同。
原因是没有已解码的受支持字段触发新失败记录，且本提案不增加公共输出字段或改变有效输入提取。
新增／移除 WARNING 或 SKIP 均预期为 0；既有 Python gap、D-M 以及其他已接受政策保持。

这是独立来源支持的 **PREDICTED_NOT_EXECUTED** 验收预期，本轮没有执行条件实现或产品。
不以五个不含新结构失败的实际项目替代 synthetic 边界，也不修改 gold。
若具体批准进入 P-B，仍需最终质量门后新鲜执行五项目 Gate A，并完整比较受影响
init/L1/default export；任何新增内部字段向外输出的变化都必须在实施前说明。

## 历史 oracle 和本轮只读收据

复核 [S4-A reviewed base index](../../../../../../dogfooding/2026-10-15-reliability-s4a/validation/expected/base/index.json)
原始 SHA-256：`06d04134b580257b5c63fc297a50f4635fba874e24f5176737b0b7655bc9cf80`。
从中选定的 **5 份 complete audit + 5 份 complete facts** 均逐字节符合原 index，
完整哈希／大小保存在 JSON。这里只检查这些十个成员及 index，没有重新执行旧验收、
推断全部 index 成员通过，或将历史 gold 改成当前产品输出。

最终采集共 **43 条只读 Git 命令**：30 次前后身份、5 次完整树清单、8 次 blob 读取；
退出码全部 0。墙钟 **1.578709 秒**，Git 命令耗时合计 **1.464317 秒**，
两者不是整个文稿会话耗时。先前另一次 43 命令成功预读仅用于准备，零公开文件写入，
在 JSON 单独登记，不混入最终计数。所有公共位置为逻辑项目名、仓库相对路径或固定公开 URL；
本机路径只用于私有定位，没有写入分享文件。

本文件的五项目证据只作 P-A 输入依据。产品质量门／Gate A 的适用与执行由整个会话
按实际改动类别决定；这份独立来源核对本身不是产品通过记录。
