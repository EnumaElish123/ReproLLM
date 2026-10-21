# R07-C dependency-absence D-L：五项目预写影响

状态：**P-A 来源资格核对通过；D-L 尚未接受或实施，未执行新产品或 Gate A**。
设计源码为 `9cabdc80ecab7728b1ee08c79fc408dd202a6e28`，完整历史执行来自任务候选
`2b0a10ad156b512cf5d53a49467e5b0c5ddf59ee`；来源均保留原候选，不作为本轮运行。

[核验收据](verification.json)、[完整预写预期](design-expectations.json)、
[产品来源一致性](product-source-identity.json)、[来源索引](source-index.json)、
[只读 Git 命令与单次耗时](commands.json)分别记录实际做过的只读核对和未来必须执行的验收。
`repository_relative` 定位仓库中已有且被 Git blob 与 SHA-256 双重绑定的原件，不是本目录新复制的产物。
原始全量 Git 路径捕获保留在外部 `external-raw`，其哈希已绑定；不建议将这 10 份原始 NUL 路径流随提案再复制入库。

## 独立事实与 D-L 条件

现行 `val.md` §§2–4 的 pins、上游和完整包集合来自独立 gold；§3 已明确五项目均无四种格式 lock。
本次额外逐项目读取精确 HEAD、公开 origin、完整 tracked/untracked status，以及完整 `git ls-tree -r --name-only -z HEAD`。
前后两次身份和全路径集合一致，五项目全部干净；没有读取任何禁止 secret 文件内容，也没有修改正式 checkout。

| 项目 | Git 完整路径数 | 已采集分析路径数 | 四种格式 lock 路径 | 原完整 WARNING 包集合 |
|---|---:|---:|---:|---|
| lm-evaluation-harness | 16413 | 16413 | 0 | accelerate, anthropic, datasets, evaluate, lm_eval, numpy, openai, peft, sentencepiece, sglang, torch, transformers, vllm |
| FastChat | 219 | 218 | 0 | accelerate, anthropic, datasets, deepspeed, flash_attn, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, vllm, xformers |
| LlamaFactory | 597 | 597 | 0 | accelerate, bitsandbytes, datasets, deepspeed, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, trl, vllm |
| HarmBench | 429 | 381 | 0 | anthropic, numpy, openai, safetensors, vllm |
| llm-dp-finetune | 66 | 66 | 0 | datasets, numpy, peft, torch, transformers |

格式范围严格为 `uv.lock`、`poetry.lock`、`Pipfile.lock`、`conda-lock.yml` 的完整逻辑 basename；
不能仅凭 `env.lockfile_present` 的 summary 推断它们不存在。本次 Git 完整路径集合和已采集完整 analysis facts 均逐项检查。
Git 路径与 analysis 路径数不同符合既有过滤；本批不修改过滤，也不以 raw Git 数量替代 Python coverage。

D-L 只可能改变“现已使用但未获得 exact/qualified 信用”且“属于已采集格式 lock 包集合并集”的包。
五项目连格式 lock 路径都没有，后者集合严格为空，故此条件对每个包都为假。
这项零差异推导独立于 primary-Python coverage 是否有缺口，不需要声称 Python 视图完整。
它不会统一压低 lm-eval 和 HarmBench 的现有 WARNING，也不会改变 HarmBench 九个 nested exact 声明的信用。

## 逐份完整预期

五项目各自预写：完整 fresh L0、完整 detection/hints/dependency/path/framework/diagnostic facts、
完整 L1、三个初始化文件（包含两个 hidden 文件）及完整普通默认 export 均零语义或字节差异。
每份既有完整原件及其来源、Git blob、大小、SHA-256 都在 `design-expectations.json` / `source-index.json` 中索引，
没有只用 summary 或包数量充当完整比较，也没有复制拟议实现的当前输出生成 gold。
15 份既有完整 JSON 比较收据实际重读确认 PASS、空差异、正确 actual 原件哈希及准确的排除范围。

未来 audit 完整比较只按规范 T-02 豁免根 `generated_at` / `reprollm_version`，facts 不排除字段。
初始化文件和默认 Markdown 导出比较完整字节；stdout 仅沿用原明确的 portable 路径投影。
原源码 143 文件及 `pyproject.toml` / `uv.lock` 的 Git 对象在 `2b0a10a` 与 `9cabdc8` 完全相同，
当前工作文件还逐份核对了对应 Git blob 与 SHA-256。旧 oracle 只因这些输入与零触发证明获得静态复用资格。
本次未执行解释器/installed metadata 探针；真正运行前仍须核对 locked 环境、来源和相应版本建议输入，
不得默默忽略环境差异或将其写成新 gold。

## 执行与未完成边界

本次实际为 43 次只读 Git 查询、210 份仓库来源读取与校验；未调用产品、测试、网络、GPU、provider、包管理器或凭据。
没有发出新 audit/init/export，也没有实施任何 conditional D-L worker；旧质量、Gate A 和 consumer 收据仍归原候选。
D-L 具体接受后仍须测试先失败后通过，最终完整质量门，再运行五项目 fresh L0 及受影响 L1/export，
并用独立合成场景验证格式 lock 可能因隐藏 import 获得信用的分支。

无 pins 或 gold 修订；不把格式 lock 包名当作真实项目归属/安装/版本证明。
listing、dependency/parser/read、framework/README/config 完整性及更广充分证书继续 OPEN。
这批普通规则政策不激活新资源 Gate B，也不重写历史 GPU、judge、discover 或外部阻塞结果。
