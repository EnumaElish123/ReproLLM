# 正式 metadata 公共模型替换 M4-META-PUBLIC-20261027

日期：2026-10-27。范围：A01-A 正式输入维护及新输入的真实 metadata 验证。
维护者明确指令：“无法获取llama2权限，请更换一个模型”。
[val.md §8.1.2](../../../val.md#812-public-model-replacement-2026-10-27) 据此替换
Project C 模型，并撤销后续验证对 Llama-2 成功授权的强制依赖。

## 新输入

选用 [distilbert/distilgpt2](https://huggingface.co/distilbert/distilgpt2)，官方模型卡
标注为 Apache-2.0 的 GPT-2 系列文本生成模型。现行 §8.3/§8.5 的原生 DP 验证
已经使用 DistilGPT2；此次只调整 metadata 输入，不重新定义其训练场景。

| 项目 | 当前输入 |
|---|---|
| Project C manifest | [reprollm.yaml](reprollm.yaml) |
| 新的 metadata intent | [metadata-dp-public.yaml](metadata-dp-public.yaml) → 副本内 `validation/metadata-dp-public.yaml` |
| 五项目完整输入索引、旧新哈希和独立预期 | [baseline.json](baseline.json) |
| 执行及验收记录 | [checks.json](checks.json) |

其余四项目仍引用[上一正式配置包](../metadata-formal-2026-10-27/README.md)中的
精确 YAML 字节；所有 upstream pins 不变。旧 Project C YAML 与旧哈希留存，
不把文件替换写成找回历史原件。

新 manifest 保留 `[finetuning, privacy]`、ECHR metadata、原有 DeepSpeed、数据
loader、隐私参数和模型实现的哈希输入。原 Llama-2 DP8 YAML 不再列入本案例的
`execution.config_files`，以免把 Llama-2 的模型声明混入新选择。新增 intent
明确 `architecture: distilbert/distilgpt2`、full fine-tuning 意图（peft=none）、
ECHR 与 epsilon=8。它仅用于元信息验证，不是可执行训练配置，也不补写 seed。
原始 checkout 不修改；只在验证副本中添加本包拥有的输入文件。

## 独立预期与执行

在运行 ReproLLM 前，通过无 Authorization 的官方 HTTP 请求读取模型信息、固定
revision 的 `config.json` / `tokenizer_config.json` 及 ECHR repo metadata。
均为 200；模型 `gated=false`、`private=false`。

- 模型/tokenizer：`2290a62682d06624634c1f46a6ad5be0f47f38aa`。
- config 原始 762 字节，SHA-256 为 `4ec5947c1d59fee6212cdf3b0ec1a53eac02092554c5ff0a733488cbd2c64f3a`。
- tokenizer_config 原始 26 字节，SHA-256 为 `5e04eb606e3a1583530a42e36c2a6b6615c86f34fe77e44d9ddeb43ff940931f`。
- 模型没有 chat template，预期 `absent` 与 exact `hf_api` 证据。
- ECHR revision 仍为 `1351ba4211ed9bc44692e6a1e2f237c4e3775b41`，不下载数据内容。

所有响应限制 2 MiB，无模型权重、token、付费请求或 GPU 执行。HF revision
继续不写入 manifest，以验证解析行为；独立 catalog 固定预期 revision，main
变化须报告差异，不能自动刷新 gold。

五项目每个在干净一次性副本执行以下三个阶段；每阶段保留 raw lock/JSON/stdout/
stderr、退出码及耗时。manifest、额外 intent 与 lock 在副本内提交后才执行 audit。

```console
reprollm lock <CASE> --offline
reprollm lock <CASE> --check
reprollm audit <CASE> --format json --fail-on never
reprollm lock <CASE>
reprollm lock <CASE> --check
reprollm audit <CASE> --format json --fail-on never
reprollm lock <CASE>
reprollm lock <CASE> --check
reprollm audit <CASE> --format json --fail-on never
```

完整预期在首个新产品命令前冻结：依据已审核的 10-26 H2 全量记录、官方 HTTP
原始字节以及本次人编 intent，仅变更 Project C 的 model/tokenizer ID、固定 SHA、
config provenance、chat-template absence、一个本地文件及 manifest 哈希。
全部 finding 仍保留其独立预期，不能把 metadata case 的缺 seed/训练声明等
真实缺口改成 PASS。比较用 `scripts/compare_gold.py`，仅豁免审计根时间/版本与
lock schema 所有的时间字段；报告 lock digest 从本次实际 lock 字节独立计算。
每项目两次 online lock 还须完整一致；stderr 按既有诊断逐字节核对。

## 验收边界

本次结果为 **PASS**，产品候选为 `00c239283c18899daa944746acbbc15b323e34e5`
（与 `6afe8f4` 产品源码一致）。五项目共 51 次真实产品命令全部 exit 0，
包含 15 阶段的 lock/check/audit、五次 doctor 及一次 gpt2 metadata 网络探针。
15 份完整 lock、15 份完整 audit 与15份 stderr 比对通过；五组重复 online lock
相符。18 个来源/人编文件哈希、30 份冻结预期及260份原始命令输出流哈希均复核。
五项目原始 checkout 与本仓库已有用户修改保持原样。

五项目回放墙钟 270.515497 秒；产品命令累计 253.987231 秒，另一个网络探针
2.282608 秒。累计命令时间不与回放墙钟重复相加。doctor 如实保留 Git 2.25.1
的版本建议警告；gpt2 网络探针为 OK。

原 VAL-R03 “Llama-2 授权后成功读文件”记为 **SUPERSEDED_NOT_PASSED**。
新当前门为“公共模型小文件成功解析与持久化”，不宣称匿名读取验证了 gated
授权路径。历史 401/403 和模拟拒绝回归仍保留为独立覆盖。
当前 VAL-R03 公共模型门已通过；不再把 Llama-2 权限列为开发阻塞。

本轮为文稿及人编验证输入维护，产品源码、schema、测试、依赖、CI 与工具均未改。
按[验证频率合同](../../plan/validation-workflow-2026-10-13.md)，产品完整质量门和
Gate A 记 NOT_APPLICABLE；本次真实 metadata 回放另行记录，不视为新产品发布验收。
上一轮质量、GPU、付费 judge/discover 成功仍绑定原候选；本次没有重新调用付费 API。

本包两份 YAML 按本仓库 Apache-2.0 保存。上游配置及模型/数据不随包分发，
只保留公开来源和哈希；raw 响应、lock 和报告保存在外部证据目录。
