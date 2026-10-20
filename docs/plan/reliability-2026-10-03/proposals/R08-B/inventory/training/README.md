# R08-B P-A：training 参数与来源清单

状态：**PROPOSED；仅清单和方案证据，未修改产品、规范、默认表或历史结果。** 基线 `30dc9cae41b2fbcc1657357eff34b3e5a7f26322`。

`inventory.json` 逐项记录完整来源 SHA、相对路径、文件 SHA-256、行号、当前 first-match 结果和建议。所有来源工作区文件均逐字节与其固定提交的 Git blob 核对；不复制宿主路径或源文件中的个人目录。没有运行产品测试、模型、网络、GPU 或凭据检查。

## 实际映射与推荐边界

本清单完整检查了 20 份受限语料中的 manifest：全部 4 个可运行 example manifest、6 个 golden fixture manifest，以及最近五项目 A/B 的 10 份 runtime manifest 快照。历史重复归档不重复计作独立案例。**只有 DP A/B 两份实际声明了 `training.params.num_train_epochs: 0.125`**；其余实际训练配置使用 typed training 字段，或 training 缺失 / 为空。单测的 `training.params.x` 仅是人工预检控制，不提供共同实验语义。

| 实际 manifest 字段 | 当前等级 | 来源与意义 | 本清单建议 |
|---|---|---|---|
| `training.params.num_train_epochs` | MEDIUM，未匹配默认表 | DP supplementary manifest 第 28 行；归档 entry 第 85 行固定传 `TrainerArgs(num_train_epochs=0.125)`，第 92 行调用原生 DP 训练方法；固定上游 `language_model.py` 第 445 行向 `PrivacyEngine` 传入 `epochs` | 仅对此精确路径提议 HIGH；等待具体政策决定 |
| `training.method`、`learning_rate`、`optimizer`、`scheduler`、`batch_size`、`gradient_accumulation`、`epochs`、`max_steps`、`precision`、`seed` | HIGH，匹配 `training.*` | 当前正式训练 manifest 和 typed schema | 保持 |
| `training.deepspeed.config` | MEDIUM，未匹配默认表 | 相对配置路径；文件内容另有 `files.<path>.sha256` 的 HIGH 差异 | 保持；不以路径本身推断内容或直接提级 |
| `training.params.x` | MEDIUM | 单测人工任意键，未定义实验意义 | 保持 |

`training.epochs` 的当前 schema 类型是 `int`；规范的概览草图写 `number`。本次补充案例为适配 fractional `0.125` 使用了合法自由字段 `training.params.num_train_epochs`。它们是**两个不同路径**；本清单不建立别名、不迁移现有值、不修 schema、不修改导出格式，也不把外部框架的 `num_train_epochs` 自动转换为 built-in 字段。

该自由字段没有声明运行 binding。其证据是 manifest 声明、内容地址绑定的 entry 源码快照、固定原生函数调用链；不能描述成 `bindings_observed` 或 child 内部验证结果。A/B 值均为 `0.125`，历史 paired diff 没有该字段的变化，不应重写历史结果。即便 `max_steps` 决定实际停止步数，DP `PrivacyEngine` 仍使用此 `epochs` 参数校准噪声；已注释 scheduler 旁的 `t_total` 计算本身不足以证明实际步数变化。

## 配置源码键不等于 manifest 路径

固定五项目的源码证据单独列在 `upstream_source_keys_without_new_manifest_mapping`，其 `manifest_field_path` 均为 null。它们提供风险分类的上下文，不是新默认路径清单：

- **FastChat**：原生训练文档与 `train_lora.py` 有 epochs、batch、gradient accumulation、learning rate、warmup、sequence limit、precision 及 LoRA 构造参数。LoRA rank/alpha/dropout/target_modules 已有 typed model adapter 对应槽位，但仍须显式声明或 binding，不能增加重复 `training.params` 别名。正式最新 FastChat 验证是生成 / 评价，并非这些训练源码的执行证据。
- **LlamaFactory**：示例 `qwen3_lora_sft.yaml` 把 method、token cutoff、sampling、optimizer schedule 与 output/logging 混在一个顶层配置中。正式训练 manifest 已使用 typed training/model/dataset 字段；不能按 YAML 层级直接发明 `training.params.<key>`。
- **HarmBench**：alignment-handbook 的 SFT recipe 有训练控制和 logging/output 控制；正式最新 HarmBench 验证是评估，不建立这些配置键的 manifest 路径。
- **llm-dp-finetune**：原始 YAML 是 `trainer_args.*`，不是 manifest 的 `training.*`。`dry_run` 虽然名字像便捷工具开关，却会把 max_steps 改成 2；`output_dir` 在该 subclass 的 help 写为 unused。必须逐字段读实现，不能按类别统一 HIGH 或 LOW。
- **lm-evaluation-harness**：在本清单受限正式 manifest 语料中没有 training 自由字段。项目总览说明其评价用途；本结论不宣称整个仓库不存在所有训练相关脚本。

日志、worker 数、输出目录、checkpoint 保留、reporting、timeout 等只列为已存在的 **source-only keys**。它们有时可能影响资源、恢复或结果选择，现有证据不足以授予统一新等级；本提案不新增相应路径，也不更改其现合同。

## 现有匹配和用户覆盖

`*` 严格匹配一个点分段；`training.*` 不匹配 `training.params.num_train_epochs`，`custom.*` 同样不递归。默认按表内 first-match 决定，未命中为 MEDIUM。State 递归展开 dict，list 保持原子值，因此 schema 里的 `evaluation.metrics[].params` 不意味着存在 `evaluation.metrics.0.params.*` binding / diff 路径。`artifacts.metadata` 虽是合法自由容器，却不在 experimental State 的投影 section 集合内。

用户可选中一个继承 finetuning 的本地 profile，并按精确路径覆盖：

```yaml
schema_version: 1
name: training_policy
description: Project training drift policy
extends: [finetuning]
drift_overrides:
  training.params.num_train_epochs: LOW
```

文件位置是 `.reprollm/profiles/training_policy.yaml`；manifest 的 `experiment.profiles` 需要选中 `training_policy`。`NONE` 同样合法，可替换 LOW。profile 覆盖项被放在默认表前面，同键继承由 child 替换 parent；不同模式间仍按 first-match，**不承诺更具体模式自动优先**。不修改 profile 继承或 resolver。

## 对四条 exact HIGH 方案的独立复核

将 `privacy.mechanism.params.{target_epsilon,target_delta,max_grad_norm}` 与 `training.params.num_train_epochs` 四条逐项列为 HIGH，有具体 case 和源码调用链支持；没有发现阻止准备提案的反证。仍应明确以下局限：

1. 这是 declared / captured experimental values 的默认可比性风险等级，不证明某次参数变化一定改变结果，不验证隐私保证。
2. 原生 `PrivacyArgs.noise_multiplier` 文档明确：若直接固定噪声，`target_epsilon` 会被忽略。HIGH 不代表忽略上下文后作因果保证。
3. manifest `max_grad_norm` 经 entry 显式传给 `PrivacyArgs.max_grad_norm_dp`，再进入 `PrivacyEngine.max_grad_norm`，不能把源字段名误记成 manifest 路径。
4. `num_train_epochs` 的 fractional 适配、无 binding、max_steps 与 DP epochs 的作用层次按上文保留。四条均不扩展为 `training.params.*`、`privacy.mechanism.params.*` 或递归 wildcard。
5. 当前历史 epsilon 8→4 的 MEDIUM 记录保留。新默认须另立前瞻性 gold，用户 LOW/NONE 覆盖继续按原规则生效。

因此最窄 training 方案是**一个精确路径**；维护者也可以先延期 training 子集。不能因为源码存在很多训练参数而扩大本次默认表，也不能声称没有真实 training 自由字段。
