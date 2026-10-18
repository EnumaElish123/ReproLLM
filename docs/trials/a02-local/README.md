# A02 本地试用材料

整理日期：2026-10-18；核对基线：`0d893b26666e74baa105ca87ba8ac2f02af39989`。

材料状态：**READY_FOR_REVIEW**。实际独立试用：**PENDING**。
邀请尚未发送；没有独立用户反馈、问题闭环或持续采用结论。

依据：[A02 任务与验收](../../plan/reliability-2026-10-03/06_Validation_and_Adoption.md#5-a02试用材料与反馈闭环)。
本材料面向有真实实验或运行记录的研究者。只进行本地检查、比较和标准库演示，
不要求执行推理、训练、模型下载或 API 请求。预计操作时间请由试用者实际记录。

## 版本与安装入口

需要 Python 3.10+ 和 Git。**0.7.0 是未发布候选版本**，不能用
`pip install reprollm==0.7.0` 获取本材料所测候选。
[发布状态](../../community/roadmap.md)和 main 的文档可能不同，先确认实际安装版本。

选择一种安装方式，并在[反馈表](feedback.md)记录来源：

1. **本地已核验 wheel，优先采用。** 使用维护者提供的候选文件和对应构建清单，
   按 [D02 安装验证说明](../../distribution.md)核对文件名、版本、SHA-256 和源码关联。
   [A01 候选身份](../../dogfooding/2026-10-18-a01-local/candidate-wheel.json)所指文件为
   `reprollm-0.7.0-py3-none-any.whl`，SHA-256 为
   `0be12d1d44a07e1ab29459c161cf67fcdc48a0934d1e57d593cc5887ac6049ff`，
   原构建源码为 `a4d895d4f30f6f74421d7f1cd96606f9b0baba15`。
   wheel 和依赖 wheelhouse 未随文档分发；无法取得时记录阻塞，不用同名文件替代。
2. **已审阅源码副本。** 使用维护者明确指定、记录完整 commit SHA 的一次性源码副本。
   在该副本执行 `uv sync --locked --dev`、`uv run reprollm --version`，随后激活其
   `.venv` 再执行任务卡。记录为源码安装，不能据此声称验证了上面的 wheel。
   依赖准备可能需要普通软件包索引；这不需要模型库、模型权重或付费凭据。

wheel 安装示例中，尖括号内容均需替换；环境目录应新建在现有项目之外：

```console
python -m venv <trial-env>
```

激活该环境：PowerShell 使用 `<trial-env>\Scripts\Activate.ps1`；
Linux/macOS 使用 `source <trial-env>/bin/activate`。然后：

```console
python -m pip install <verified-local-wheel.whl>
reprollm --version
```

若已有兼容的依赖 wheelhouse，安装可改用 D02 已支持的
`python -m pip install --no-index --find-links <wheelhouse> <verified-local-wheel.whl>`。
版本字符串相同不代表 wheel 字节或源码身份相同。其他候选需要自己的清单与证据。

## 任务卡一：现有实验的 audit / init

**目的：** 判断发现项、字段路径和修复提示是否能帮助补齐实验声明。
只读 audit 可以在你有权检查的既有项目执行：

```console
reprollm audit <project-path> --format json --fail-on never
```

预期：得到完整报告；记录一个有用、错误或难理解的发现项。`--fail-on never`
让发现项不触发退出 1，退出 0 不表示没有问题或实验可复现。扫描预算诊断也需保留。

**以下写入步骤只在一次性项目副本执行。** 副本放在原项目之外；保留所需相对路径，
移除凭据、缓存和无关大文件。不要在原项目覆盖文件。进入副本后：

```console
reprollm init .
reprollm audit . --format json --fail-on never
```

若已有 `reprollm.yaml`，跳过 init，直接检查它；本任务不用 `--force`。
若没有 manifest，init 应创建 scaffold，并指出仍需填写的字段。
只从实际实验信息填写副本，不把 TODO 或猜测值当作已验证事实。
记录首个阻塞步骤、实际退出码，以及你能否理解下一步该做什么。

## 任务卡二：已有 run 的单字段变化、diff / export

**目的：** 判断报告是否能解释一项已知实验变化。先在本地写下目标字段、旧值、新值
和预期等级，再看 diff。使用包含 manifest、lock、`.reprollm/runs/` 及其快照的一次性
项目副本。选择两个已有、可读取且记录了一项已知参数变化的 run；本任务不重跑原框架。

在副本内执行，替换两个 run ID；两个导出文件名须尚不存在：

```console
reprollm runs list --json
reprollm diff <run-a> <run-b> --format json --fail-on HIGH
reprollm diff <run-a> <run-a> --format json
reprollm export . --run <run-a> --output trial-export-a.md
reprollm export . --run <run-b> --output trial-export-b.md
```

预期：目标字段的值和等级与事先记录一致；解释完整的其他差异，包括输入 hash、
代码 commit 和时间字段。自 diff 应为空；导出应对应明确选定的 run。
`diff --fail-on HIGH` 在存在 HIGH 差异时退出 **1**，这不是崩溃。
保留声明、观察和未验证消费之间的区别；导出成功不证明模型实际执行或结果正确。

**没有两个可用 run 时：** 使用 [A01 可分享标准库回放指南](../../dogfooding/2026-10-18-a01-local/replay-guide.md)，
按其原命令在新的外部工作目录、空输出目录和新环境中运行已核验 wheel。
该指南提供安装前提、确切脚本参数和独立预期，无需框架或 API。
先阅读其中 32 → 48、完整三条非 NONE 差异、自 diff、选定导出及消费后改写为 96 的预期。
不要把共享的 `run.json` 直接当作 `export --run` 的 ID，也不要用未知项目的训练命令补 run。

此标准库路径只建立所声明的 L2 证据。作者自测不计独立采用；独立试用者实际运行
并反馈后可登记一次试用，仍不等于持续采用或原生模型验证。

## 反馈与问题处理

填写[空反馈模板及净化说明](feedback.md)，允许只提供最小合成复现。
无需上传整个项目、私有 prompt、数据集、模型权重或密钥。
维护者按 bug / 文档 / 工作流需求 / 超出范围分类，关联有边界的任务；
只有记录“复现 → 处理 → 试用者回访验证”后才标记问题闭环。

## 筛选标准与邀请草稿

优先选择拥有或获准使用真实 LLM 实验、愿意本地安装与报告阻塞的独立研究者；
不要求 GPU、付费账户或公开私有项目。采用小批量试用，并记录作者/维护者与独立用户的区别。
无需以星标、下载量或正面评价作为筛选条件。未获明确发送授权前，只保留草稿。

> 想邀请你试用 ReproLLM 的本地 audit 和运行差异报告。材料包含两张任务卡，
> 可使用你有权检查的项目，也可选择无需模型或 API 的标准库案例。
> 当前测试版本是未发布候选，需要本地已核验 wheel 或指定源码副本。
> 我们希望了解首个阻塞点、报告是否可理解，以及是否有值得解释的差异；
> 不预设正面评价。你可以只反馈最小合成案例，不必上传私有内容。

## 状态边界

| 项目 | 当前状态 |
|---|---|
| 说明、两张任务卡、反馈与处理模板 | READY_FOR_REVIEW |
| 邀请发送、真实独立试用与反馈 | PENDING |
| 真实问题闭环、重复使用、独立集成 | PENDING；尚无本材料收集的证据 |
| 作者已有回放 | 见 [A01 证据包](../../dogfooding/2026-10-18-a01-local/README.md)，不作为独立用户反馈 |
| 原生框架、认证访问、付费 API 与正式资源验收 | 保留[原有阻塞](../../dogfooding/pending-resource-validation.md) |
