# 正式 metadata 验证配置 M4-META-20261027

日期：2026-10-27。任务：A01-A，正式输入基线维护。

维护者指令：“直接制定一份新的正式验证配置，替代旧文件”。本包据此成为
[val.md §8.1.1](../../../val.md#811-current-formal-metadata-inputs-2026-10-27)
指定的后续 M4 正式输入，替代五份无法取得的 2026-09-19 manifest。
这是已授权的基线替换，不再等待第二次批准。旧文件仍记为 MISSING；旧报告及其
输入哈希保持历史身份。新基线的五份输入全部随仓库保存，不再依赖临时目录。

## 五份配置

| 项目 | 正式文件 | 选择的元信息 |
|---|---|---|
| lm-evaluation-harness | [manifest](manifests/lm-evaluation-harness.yaml) | Qwen2.5-0.5B-Instruct、GSM8K main/test、任务 YAML、vLLM |
| FastChat | [manifest](manifests/FastChat.yaml) | Vicuna-7B-v1.5、GPT-4o dated snapshot、MT-Bench question/reference/rubric、三个执行源码文件 |
| LlamaFactory | [manifest](manifests/LlamaFactory.yaml) | Qwen3-4B-Instruct-2507、identity/alpaca demos、qwen3 LoRA YAML、dataset_info |
| HarmBench | [manifest](manifests/HarmBench.yaml) | Vicuna-7B-v1.5、行为 CSV、模型配置 |
| llm-dp-finetune | [manifest](manifests/llm-dp-finetune.yaml) | Llama-2-7B、ECHR、DP8 YAML、DeepSpeed 配置及数据/隐私/模型源码 |

[baseline.json](baseline.json) 固定每个新 case ID、五个 upstream commit、旧/新
manifest SHA-256、文件大小、18 个本地源文件哈希、六个 HF repository revision
及小文件哈希。manifest 本身使用现行 schema 1，复制到目标 checkout 后文件名为
`reprollm.yaml`。路径均相对于目标项目根目录，而非本包目录。

## 选择依据和覆盖边界

选用已存在的 §8.2 H2 配置的精确字节，将其作为本次新正式基线。
`*-linux-metadata` 名称保留，避免无意义的输入变化。新哈希与五份丢失的原始文件
均不同，但与 H2 输入相同。正式身份自本次决定起生效；10-26 的 H2 执行仍按当时的
supplementary 身份记录，不能写成今天新执行了一次正式资源门。

独立预期来自已审核的 val.md §8.1、固定 upstream 源文件和原始 HF 响应哈希，
不是根据当前 ReproLLM 输出生成。此次重新读取 Git 固定对象并计算 18 份文件哈希，
核对五项目 SHA、origin 和干净状态；模型和数据选择逐项复核：

- lm-eval 的 `gsm8k.yaml` 明确 dataset/subset/split、prompt 和 five-shot 任务设置。
  Qwen 0.5B、bf16、无量化、trust=false 与 vLLM 是验证案例的显式选择，
  不宣称是框架唯一默认值。新 metadata manifest 不填采样数/生成参数。
- FastChat 的本地 question/reference/rubric 文件和三个 Python 文件均来自固定源码。
  Vicuna/GPT-4o snapshot、judge temperature=0、cap=2048、repetitions=1 是本案例
  的声明；本门只验证身份、pinnability 和哈希，不发送 GPT-4o 请求。
- LlamaFactory 的 qwen3 LoRA YAML 指定模型、identity/alpaca 数据与训练方法；
  本配置只选元信息，不补写未纳入本案例的训练参数或 seed。
- HarmBench 的模型表明确包含 Vicuna-7B-v1.5，行为 CSV 为选定评估数据。
- DP8 YAML 明确 Llama-2、ECHR、epsilon=8 和 full fine-tuning（peft=none）；
  数据 loader 与隐私/模型实现一并哈希。配置无显式 seed，不虚构训练 seed。

新五份配置均是有界 metadata 案例，并非完整训练/评估 recipe。相对于旧 M3 A/B
描述，lm-eval 的 100 样本/生成设置、FastChat 的一次真实生成加打分不在本包中；
其执行覆盖由现行 §8.3 原生运行及 §8.4–8.5 正式 judge 场景继续承担。
缺失的原始 YAML 无法逐字段还原，因此不声称与其语义完全等价，也不继续使用
旧 M3“零缺失 CRITICAL”的结果作为这五份有限配置的预期。
不完整 presence findings 必须保留；模型身份/数据/文件哈希、freshness 和完整报告
仍按各自合同核验，不能用总数相同或强制全 PASS 代替。

## 执行和预期

1. 按 val.md §2 核验五个原始 checkout 的 pin、origin、clean；创建一次性副本。
2. 从本包复制对应 YAML 到副本根目录的 `reprollm.yaml`，对照 baseline.json
   核验字节哈希；重新独立核验表中的全部本地文件哈希。
3. 按 §8.1 执行 offline lock/check/audit、两次 online lock/check/audit，并保留
   每个阶段的完整 lock、audit、stdout/stderr、退出码及耗时。每次 audit 前在副本内
   提交 manifest/lock，使 Git 检查面对干净输入。生成产物保存在仓库外。
4. HF 输入没有声明 revision，保留“解析 revision”的被测路径。offline 应为
   unresolved/offline；online 必须解析到 baseline.json 的固定 revision。
   main tip 改变必须报告差异，不能自动更新预期。检查全部 config/tokenizer/template
   哈希、local hashes、manifest/lock freshness、文件一致性及完整 findings。
5. 两次 online lock 仅允许 schema 所有的时间戳差异；不得任意忽略 params 中同名字段。
   完整 JSON 比较使用 `scripts/compare_gold.py`；仅在合法审计元数据位置使用豁免。
   §8.1 的 doctor 和网络探针仍适用；每次重放按实际环境记录工具缺失或网络失败。

资源边界沿用 §8.1：仅 metadata 和每份不超过 2 MiB 的小文件；不下载权重或数据集
内容，不运行 GPU，不调用付费模型，不使用 `--verify-api`。凭据只提供给 metadata
进程。Mirror 如被采用必须单独记录，不能证明官方 endpoint 可访问。

Llama-2 repo metadata 可解析并不代表小文件授权成功。匿名拒绝与认证后成功是分开
的验收分支。现有两份小文件 403 的历史事实保留；**VAL-R03 仍 BLOCKED**，
解除条件是模型作者授权后，通过真实小文件解析及独立 revision/hash/provenance
比对。新基线已解除“必须找回原五份 manifest”的后续输入阻塞。

## 本次检查与历史证据

本次为验证文稿及人编输入基线维护，不修改产品、默认配置、测试、工具或 CI。
按[验证频率合同](../../plan/validation-workflow-2026-10-13.md)，产品完整质量门、
Gate A 及新在线 Gate B 本次记 NOT_APPLICABLE，不冒充新产品验收或发布就绪。
本包的 schema、全部输入/源文件哈希、来源、相对路径、文档链接以及五项目离线
lock/check/audit 验收记录见 [checks.json](checks.json)。

本次结果：5/5 manifest schema 通过；18/18 源文件哈希相符；五项目共 15 次
离线产品命令全部 exit 0。五份完整 lock 与五份完整审计、stderr 均符合已审核的
H2 预期；仅排除 schema 规定的时间字段，并独立计算新 lock 的报告引用哈希。
160 个本地文档链接有效，五个原始 checkout 与已有用户修改保持原样。

此前 [10-26 资源报告](../2026-10-26-validation-completion/README.md) 在 `6afe8f4`
已用相同 H2 输入通过 639 条断言和 15 组完整 lock/audit/诊断比较。
baseline.json 引用原证据哈希；本次只核对证据及输入身份，不把旧执行改绑到新提交。
后续产品候选/发布仍按现行频率执行适用矩阵，配置替换不免除重放。

本包的 YAML 为 ReproLLM 验证案例文本，按本仓库 Apache-2.0 许可保存；
upstream 文件仅保存引用和哈希，内容及许可仍归相应 upstream，本包不分发模型或数据。
