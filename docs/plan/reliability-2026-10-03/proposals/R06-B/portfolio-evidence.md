# R06-B：五项目依赖来源与 lock 范围证据

状态：**提案准备的只读源码证据；未批准、未实现、未更新 gold。** 本文支持
[P-A / R06-B](../../05_Policy_and_Compatibility.md)，
不把源码盘点写成当前产品验收。机器清单见 [portfolio-evidence.json](portfolio-evidence.json)。

## 1. 结论与核验边界

五份固定源码的 SHA、公开 origin 和 tracked/untracked clean 状态在最终采集前后均匹配
[val.md §2](../../../../../val.md#2-pinned-portfolio)。共 30 项身份检查通过。
完整 Git 树中有 12 份候选文件，其中当前支持的依赖 manifest 是 8 份：3 份 PEP 621
pyproject、5 份 requirements。格式 lock 为 0，requirements include 边为 0，合格完整
exact requirements closure 为 0。**九个嵌套 exact 声明有据；根实验已锁定没有证据。**

依照 [spec §12.2](../../../01_specification.md#122-env-l0-m2) 保留支持格式、L0 仓库聚合与
确定性扫描边界时，推荐 A 的五项目 `env.llm_critical_deps_pinned` **预期新增 0、移除 0**；
`env.lockfile_present` 仍为五项 WARNING。主提案 §2.1 已定义拟议 owner 规则，§5 将完整
facts/message 不变列为验收目标；若新增外部 provenance 展示，须先补精确输出设计并独立
审阅 gold。这个零差异目标没有在本轮执行，不能代替未来产品的完整 JSON 比较。
这里没有格式 lock，不能用五项目的零 package delta 证明一般 owner 规则已正确。

最终采集从 ReproLLM `af8adea8ec37fb5db57373432f4ced58cec9fb9e` 开始，仅运行 40 条只读
Git 子命令，最终采集墙钟 **4.028138 秒**；这不是整个文稿会话的耗时，也不包含早期阅读探针。
未运行产品命令、pytest、训练、推理、网络或 API；未执行 upstream setup.py。
按[验证流程 §3](../../../validation-workflow-2026-10-13.md#3-执行频率唯一权威定义)，
产品质量门 / Gate A 为 **NOT_APPLICABLE（仅文稿证据）**，没有新产品 PASS。

## 2. 固定输入与来源数量

| 项目 | 固定 SHA | 支持的 manifest / 声明行数 | 其余候选与边界 |
|---|---|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | `pyproject.toml` 98（14 core + 84 optional）；`lm_eval/tasks/japanese_leaderboard/requirements.txt` 4 | 2 manifest；build-system 1 与 dependency-groups 4 条字符串另计，不是当前 runtime/optional 契约 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | `pyproject.toml` 34（15 core + 19 optional） | 1 manifest；dev 的 2 个 exact pin 均不是 LLM-critical 包 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | `pyproject.toml` 31；`docs/requirements.txt` 3 | 2 manifest；docs 的工具依赖不证明训练环境覆盖 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | root requirements 21 条可读声明、nested requirements 26；已审阅 facts 是 19 + 26 = 45 行 | 2 manifest；nested setup.py 是补充 computed packaging 来源；setup.cfg 仅工具配置 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | root requirements 3 条具名声明 + 1 条未具名 VCS 行 | 1 manifest；setup.cfg 13 条 packaging 声明尚不在支持格式内；setup.py 仅 setup() shim |

“声明行数”按依赖条目计，同行可有多个条目，同包多处声明分别计数；不是唯一包数量。
JSON 同时保存独立源码计数与历史 facts 计数。HarmBench root 行 18–19 的
`art # for ArtPrompt`、`tenacity # for ArtPrompt` 可独立读为 pip 声明，但现有已审阅静态
facts 将二者保留为诊断，故 47 与 45 的差异不等于获准增加两行产品输出。

全五 `uv.lock`、`poetry.lock`、`Pipfile.lock`、`conda-lock.yml` 均为 0；额外核查的
`conda-lock.yaml`、`pdm.lock` 亦为 0。不将未支持格式或普通同名工具配置推定为 lock。
五个 requirements root 每个只可达自身；每个都有 non-exact 或不支持声明，均不能成为
完整 exact closure。没有观察到实际 requirements include、tool-only pyproject、独立
子项目格式 lock 或相互冲突的 critical exact pins；这些 owner 正反例仍需要固定 fixture。

各文件的完整 Git blob SHA-256、Git object ID、字节数、行数、固定 SHA 和公开源码 URL
均在 JSON 的 `source_files` 中；hash 对象是**原始 Git blob 字节**，不假称 Windows
工作区 CRLF 字节与其相同。50 份源文件记录涵盖 12 个候选文件与关键 import 的代表来源。

## 3. HarmBench 九个 pin 与 include 关系

以下行号来自固定 SHA 的
[nested requirements](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt)
和 [setup.py](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/setup.py)。

| 包 | exact 声明 | requirements 行 | setup.py `_deps` 行 | 当前 L0 声明证据 |
|---|---|---:|---:|---|
| accelerate | `==0.23.0` | 1 | 44 | covered |
| bitsandbytes | `==0.41.2.post2` | 2 | 45 | covered |
| datasets | `==2.14.6` | 4 | 47 | covered |
| deepspeed | `==0.12.2` | 5 | 48 | covered |
| evaluate | `==0.4.0` | 7 | 50 | covered |
| peft | `==0.6.1` | 16 | 59 | covered |
| torch | `==2.1.0` | 22 | 65 | covered |
| transformers | `==4.35.0` | 23 | 66 | covered |
| trl | `==0.7.4` | 24 | 67 | covered |

这里的 covered 仅指当前 L0 仓库聚合能找到 exact declaration；九包的 lock coverage
与根实验环境 coverage **均为 unproven**。nested requirements 共 26 条声明，只有
10 个 exact（含 black），其余有范围或无版本；root requirements 21 条只有 spacy 与
confection 两个 exact。部分包 exact 不等于整个 requirements 是 lock。

完整读取 [root requirements 行 1–21](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/requirements.txt)
与 nested 行 1–26 后，二者均无 `-r` / `--requirement`，也没有 constraints include。
**root → nested 的 include 边不存在；nested → root 同样不存在。** root 的 transformers
行 4、accelerate 行 15 无版本；当前 L0 用嵌套 exact 声明免除同名包警告，不表示 root
安装命令会消费这些 pin。

setup.py 行 43–70 的 `_deps` 列表重复这些版本，行 78 的名称映射、81–82 的 deps_list
为 Python 内部的声明引用；并没有读取 requirements 文件。行 93–113 构造 19 个核心
install_requires，行 131 交给 setup。torch 位于行 87 的 optional extra，不能写成核心
install_requires 已包含 torch。setup.cfg 仅 isort/flake8/pytest 配置，不是额外依赖来源。
setup.py 的 python_requires 行 130 亦不等于现有 L0 已支持该 Python 版本来源。

原始 Git blob SHA-256：

| 文件 | SHA-256 |
|---|---|
| root `requirements.txt` | `a342b21c680e1d3102953f7937c97db58f095791f311953465148a87f25f5e9d` |
| nested `requirements.txt` | `592459a407b2956d95a7bdc4da80f9af08f9e388be14827ded210d3d45cff5b7` |
| nested `setup.py` | `e476e773c9ad148156d7fbd7d07462681f8fa365fb82aef790d07e829e400b77` |
| nested `setup.cfg` | `ae51d9a03f4bf7b0029fa4b74fde69a3ec83814e992ef99fb64e75d63a15b90e` |

## 4. 全五独立 expected 包集合与推荐 A 的 delta

先从固定 Git blobs 独立读取支持格式声明、解析限定范围内的 absolute imports，按
spec 的 exact/L0 合同推导集合，再与 [val.md §4](../../../../../val.md#4-unpinned-llm-critical-dependency-gold)
和历史已审阅 oracle 比较。未运行当前 ReproLLM 输出作为 expected。
JSON 对每个 critical 包保留 expected source、代表 import 的路径/行/原行/hash、
支持格式声明、exact covered/unproven、lock 与实验 coverage 以及 cross-scope 风险。

| 项目 | 独立预期 WARNING 包集合 | 数量 | 推荐 A 的 package-set delta |
|---|---|---:|---|
| lm-evaluation-harness | `accelerate, anthropic, datasets, evaluate, lm_eval, numpy, openai, peft, sentencepiece, sglang, torch, transformers, vllm` | 13 | added 0 / removed 0 |
| FastChat | `accelerate, anthropic, datasets, deepspeed, flash_attn, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, vllm, xformers` | 15 | added 0 / removed 0 |
| LlamaFactory | `accelerate, bitsandbytes, datasets, deepspeed, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, trl, vllm` | 14 | added 0 / removed 0 |
| HarmBench | `anthropic, numpy, openai, safetensors, vllm` | 5 | added 0 / removed 0；九个 exact 包不加入 |
| llm-dp-finetune | `datasets, numpy, peft, torch, transformers` | 5 | added 0 / removed 0 |

共 52 项包级 WARNING 预期；它们都没有已证实的 lock coverage。除 HarmBench 九包外，
本表涉及的关键包也没有支持格式 exact 声明覆盖。局部 exact 声明仍不能证明跨平台安装、
传递依赖、artifact hash 或实际运行消耗的环境一致。

lm-eval 的源码有 816 个 Python 文件，确定性 first-500 范围独立核对一致，遗漏 316 个；
不把范围外的 tokenizers 加入集合，也不称整仓库 imports 完整。其他四项目各有
148 / 311 / 123 / 46 个 Python 文件，没有数量截断；HarmBench 另有两个 SyntaxError
文件（具体路径/行在 JSON），不把未成功解析的文件计为已验证 imports。
lm-eval 的 optional self references 仍是当前 L0 声明；不借本提案自动移除 lm_eval warning。

## 5. 补充 packaging 证据与 owner 验收边界

[DP setup.cfg](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/setup.cfg)
行 14–27 有 13 个 install_requires 条目，包括行 16 transformers==4.29.0、
18 deepspeed==0.8.3、19 tokenizers==0.13.3；pydantic 与 scipy 也 exact。
这是独立可见的 packaging 事实，但 setup.cfg 不在当前 §12.2 的支持扫描来源中。
因此不能据此移除现有 transformers warning，或新增 deepspeed/tokenizers warning；
支持新格式需要单独决定。行 20 flair 与 25 fastDP 为无 immutable ref 的 VCS 声明，
root requirements 行 4 同样是未固定的 unnamed VCS，均不是 exact lock。行 5–6
是注释，不计为生效依赖。setup.py 行 1–4 只有 setup() 委托，没有 literal install_requires。

主提案已经定义、未来实施仍须验证的边界：

1. 格式 lock 与声明 owner 的关联及 uncertain barrier 按主提案 §2.1 的拟议规则；
   这五份源码没有格式 lock 正例，不能从不存在 lock 推导这些规则已实现或验收。
2. 同目录 lock、无关兄弟子项目 lock、真实 requirements include、tool-only pyproject、
   多个互相冲突 exact 版本的固定预期，须由 fixture 补齐，不改真实五项目来造案例。
3. 当前 exact declaration、reachable exact closure 与选定实验环境完整性分别解释；
   如未来增加 experiment scope，先走兼容性/规格决策，不臆造 schema1 字段。
4. 新增 provenance 文本/结构可能改变完整 facts/evidence/messages；应先冻结输出契约，
   再独立审阅基线变化并在产品实现最终质量门之后新鲜执行 Gate A；主提案当前目标仍为
   既有完整输出不变。

## 6. 历史 oracle 与本轮文档检查

引用 [S4-A reviewed base](../../../../dogfooding/2026-10-15-reliability-s4a/validation/expected/base/index.json)
作为历史独立审阅参考，**不是本轮新鲜产品运行**。其 index SHA-256 为
`06d04134b580257b5c63fc297a50f4635fba874e24f5176737b0b7655bc9cf80`；
本轮逐字节复核了选定的 13 份文件（5 audit、5 facts、oracle-plan、independent-review、
oracle-and-environment-provenance），均与原 index hash/size 相符。没有宣称复核整个历史
质量门或 index 的其余全部成员。JSON 保存每个被核验文件的相对路径、原 hash 与字节数。

最终采集的 40 条只读 Git 命令包含 30 项前后身份检查，以及每项目一条 ls-tree 和
一条批量 cat-file；退出码全部 0。后续文稿自查另用 20 条只读 Git 命令（5 次批量 blob
复核与 15 项最终身份检查），再次核对 50 份 blob 的 hash/size 与 156 处原文行引用，
五份源码仍 clean；另检查了 7 个本地链接及适用 anchor、JSON 唯一键与版本、隐私模式、
LF 和行尾空白。其命令数不混入上述 40 条采集命令，耗时亦不冒充完整会话耗时。
独立只读同伴审阅通过，无 must-fix；同步澄清 owner 规则已在主提案定义，实施验收仍待执行。
JSON 为 schema_version 1，生成文本使用 UTF-8/LF；
公开清单不包含本机绝对路径、私有主机、凭据或源码仓库副本。仅交付这两份文稿文件，
未修改原 checkout、产品、测试、验证工具、val 或历史 gold。
