# 第一次使用：保存命令，然后直接运行

先用仓库自带的一个小项目熟悉流程：保存命令、查看缺口、预览、记录一次运行。准备好目录后，主流程只有 **4 条 ReproLLM 命令**，不需要手工编写整份 YAML，也不需要记住 run ID。

素材来自 [GSM8K 示例](../../examples/lm_eval_replay/README.md)的 `probe.py` 和 `validation/eval.yaml`。这次实际运行的是 Python 标准库配置读取程序：读取配置，并写出 `outputs/current/consumed.json`。配置里的 Qwen、GSM8K 和 vLLM 描述上游研究示例的计划；本练习**不加载模型、不执行评测、不需要 GPU 或 API 凭据**。运行成功表示记录流程完成，不表示论文结果得到复现。

## 一次性准备

本教程使用当前源码中的易用性功能。已在 ReproLLM 源码目录配置好环境的用户，只需激活该环境；其他用户先按[安装说明](../distribution.md)准备当前源码或候选 wheel。已发布版本的范围见[交付状态](../community/roadmap.md)。

在 ReproLLM 源码根目录，Linux/macOS 可使用：

```bash
uv sync --locked
source .venv/bin/activate
```

Windows PowerShell 的激活命令是 `.venv\Scripts\Activate.ps1`；后面的 ReproLLM 命令相同。

用文件管理器在 **ReproLLM 仓库外**新建一个空目录 `reprollm-first-run`，只复制以下两个文件：

| 原文件 | 新目录中的文件名 |
|---|---|
| [examples/lm_eval_replay/probe.py](../../examples/lm_eval_replay/probe.py) | `probe.py` |
| [examples/lm_eval_replay/validation/eval.yaml](../../examples/lm_eval_replay/validation/eval.yaml) | `eval.yaml` |

然后在该新目录打开终端，保留刚激活的 Python 环境。也可以从 ReproLLM 根目录执行这四条准备命令；如果目标目录已存在，请换一个新名字：

```bash
mkdir ../reprollm-first-run
cp examples/lm_eval_replay/probe.py ../reprollm-first-run/
cp examples/lm_eval_replay/validation/eval.yaml ../reprollm-first-run/eval.yaml
cd ../reprollm-first-run
```

## 1. 保存实验命令并按提示填写

```bash
reprollm init --interactive --profiles evaluation --command "python probe.py --config eval.yaml"
```

这是唯一一次输入完整实验命令。初始化只保存声明，不执行它。

按提示填写下表；字段说明会显示在终端。这里的值来自示例配置及其[数据任务定义](../../examples/lm_eval_replay/upstream/gsm8k.yaml)，无需猜测。

| 提示 | 本练习输入 |
|---|---|
| `Profiles for this experiment` | 按 Enter，保留 `evaluation` |
| `models.primary.id` | `Qwen/Qwen2.5-0.5B-Instruct` |
| `inference.backend` | `vllm` |
| `generation.temperature` | `0` |
| `generation.max_tokens` | `32` |
| `datasets.eval.id` | `openai/gsm8k` |

想体验错误恢复，可以在 `generation.max_tokens` 先输入 `abc`，看到提示后在同一位置输入 `32`，前面的回答会保留。Enter 会保留已有默认值；没有默认值时表示暂时未知。不要为消除提醒而填写猜测值。

`evaluation.metrics` 需要手工描述实际指标，本练习暂时留空。工具会报告 **1 个必填声明尚待补充**。这个数字只统计所选 profiles 的必填字段，不是审计发现的总数，也不代表其余研究细节已经齐全。

此时会生成 `reprollm.yaml` 和 `.reprollm/`。已有配置的真实项目直接使用后续命令；不要为了重复运行而再次初始化或加 `--force`。

## 2. 先读报告顶部的下一步

```bash
reprollm audit .
```

先看 `Next steps` 中最多三项行动，再看详细发现及 `fix:` 提示。本练习预期仍有缺口：这个临时目录没有 Git 历史和依赖声明，指标也尚未填写；seed、top_p 等研究字段还没有从配置同步到声明。审计通常以 **退出码 1** 结束，表示发现达到阈值，不是程序崩溃。

后续完善真实项目时，按提示的字段路径编辑 `reprollm.yaml`，从实际代码和配置中取值。例如本素材的 seed 为 `42`、top_p 为 `1.0`；指标名称和实现路径则要核对真正运行的评测代码，不能把任务名 `gsm8k_validation` 直接当作指标。依赖锁文件也不能由 `reprollm.lock` 代替。

`SKIPPED` 表示检查条件或证据不足。使用 `reprollm audit . --show-skipped` 查看原因，不能把跳过当作通过。本练习可以继续检查运行记录功能，研究信息的缺口仍保留在报告里。

## 3. 预览保存的命令

```bash
reprollm run --dry-run
```

确认工作目录和输入文件提示。预览不会启动实验、联网或创建运行记录；缺少 lock 等提醒会保留。这里没有手工配置参数绑定，因此配置文件会被采集，但配置里的每个数值不会自动成为“已验证的运行参数”。

## 4. 直接运行

```bash
reprollm run
```

本示例应以退出码 `0` 完成，产生：

- `outputs/current/consumed.json`：**示例程序**写出的配置读取结果。
- `.reprollm/runs/…/run.json`：**ReproLLM**写出的运行记录，包含命令、退出码和输入文件证据。

这一步不要求先把审计报告变成全 PASS。判断研究是否可复现时，仍须处理报告中的缺口，并核对实际模型与数据的运行证据。

## 查看、重复与分享

无需复制长串 run ID，先查看最近记录，再导出最近一次运行的报告：

```bash
reprollm runs list
reprollm export .
```

打开当前目录下的 `REPRODUCIBILITY.md`。报告保留已知限制；分享前核对其中的声明和缺失项。

下次运行同一命令只需 `reprollm run`。已有两次成功记录后，可以直接比较：

```bash
reprollm run
reprollm diff --latest-successful
```

这对未修改的示例输入应没有实质实验参数漂移。两次程序成功、或比较没有漂移，都不证明模型评测已经运行；本练习始终只执行配置读取程序。

## 换成自己的项目

进入自己的已有 Git 仓库，把初始化中的 `python probe.py --config eval.yaml` 换成一条已经能正常运行的实验命令，选择实际适用的 profiles，按提示保存研究声明。以后继续使用上面的 `audit`、`run --dry-run` 和 `run` 即可。

命令需要管道、重定向或多个 shell 步骤时，先放进你自己的脚本，再保存运行该脚本的命令。模型环境、数据和计算资源仍由项目准备；ReproLLM 不会自动配置模型环境、下载数据或调度计算资源。`run` 会启动你保存的命令，该命令可能运行模型或使用付费服务。

需要在线锁定模型、配置参数绑定、真实模型 A/B 或发现项目规则时，再查阅[完整入门示例](../quickstart.md)、[GSM8K 原生运行说明](../../examples/lm_eval_replay/README.md)和[CLI 参考](../cli.md)。这些进阶步骤不属于本次四步主流程。
