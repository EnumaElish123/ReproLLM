# 验证流程优化：VOPT-01–03 会话报告

日期：2026-10-13。范围：维护者同意按耗时诊断建议开始优化，并确认以命令行退出码、
报告内容、完整 gold 差异及真实 pytest 筛选作为回归边界。

## 交付与范围

| 任务 | 提交 | 结果 |
|---|---|---|
| VOPT-01 | `ae9adbe` | Windows 普通 CI 使用 `not slow and not linux_only`；登记 slow；nightly 性能预算不变；4 项真实收集回归 |
| VOPT-02 | `874acfd` | 每任务定向回归、最终会话一次完整门；五项目基础层 + 受影响扩展层；环境预检、复用边界及文稿/工具例外统一到权威流程 |
| VOPT-03 | `91aa196` | 只读 JSON 完整比对脚本及 18 项命令行回归；不生成 gold、不执行资源任务 |

规则依据：[验证流程](../plan/validation-workflow-2026-10-13.md)、spec §22 T-02/T-08/T-09、
[val.md](../../val.md)。writing-for-agents 指导本轮将频率集中到单一文档，
AGENTS、执行总则、启动提示词和贡献指南引用它，避免重复要求继续累积。

本轮开始时基线为 `fd8fe12`。共享工作区中的扫描器性能修复由原有工作提交为
`110087b`，其交接记录为 `c3f843b`；本轮未修改或认领该实现。
`docs/plan/README.md` 的工作流入口与其交接更新同时进入 `c3f843b`。
以 `c3f843b` 为边界检查，本轮 `src/`、`schemas/`、`uv.lock` 无差异；
`pyproject.toml` 仅登记测试 marker，没有改产品依赖或打包行为。
README、docs/index 和新增研究案例文档原有未提交改动保持原样，未混入本批提交。

## 本地验证

环境：Linux、Python 3.12.14、ReproLLM 0.6.1；`uv sync --locked --dev --offline`
成功，刷新本项目 editable 安装元数据，没有升级锁定依赖。
下表命令均在仓库根运行；`uv run --no-sync` 使用这一锁定环境。
时间未单独测量的项目标为“未计时”，不虚构耗时。

| 检查 | 命令/输入 | 退出码 | 实际结果/耗时 |
|---|---|---:|---|
| CI 红灯复现 | `pytest -q tests/unit/test_ci_selection.py`，修复前 | 1 | Windows 误选 `test_slow`；其余 3 项通过；4.20 秒 |
| 定向最终回归 | `pytest -q tests/unit/test_ci_selection.py tests/unit/test_compare_gold.py` | 0 | 22 passed；4.70 秒 |
| 最终完整质量测试 | `pytest -q --cov=reprollm --cov-report=term --cov-fail-under=85` | 0 | 2527 passed、2 deselected；覆盖率 93.64%；pytest 370.28 秒，shell 墙钟 370.981 秒 |
| redaction 门 | `coverage report --fail-under=100 --include='src/reprollm/core/redaction.py'` | 0 | 100%，24 个分支全部覆盖；在 security 重跑前读取 |
| security | `pytest -q -m security` | 0 | 174 passed、2355 deselected；pytest 9.05 秒，墙钟 9.656 秒 |
| lint/格式 | `ruff check .`；`ruff format --check .` | 均 0 | 413 个文件格式正确；未计时 |
| 类型 | `mypy src/ scripts/compare_gold.py` | 0 | 124 个源文件通过；未计时 |
| 生成文档 | `python scripts/gen_{rules_doc,profiles_doc,cli_doc,quickstart}.py --check`（逐项执行） | 均 0 | 四项 freshness 通过；quickstart 成功重跑 11.729 秒 |
| schema | `reprollm schema export --out <独立临时目录>`，随后 `diff -r schemas <该目录>` | 均 0 | 10 个文件集合及字节一致；未覆盖 tracked schemas |
| 文档/补丁 | 修改文档的本地相对链接检查；`git diff --check` | 均 0 | 71 个本地链接目标存在；无 whitespace 错误 |

定向负例覆盖完整嵌套差异、相同 summary 下的语义变化、数组顺序与长度、类型
差异（含 bool/int）、缺失字段、重复键、非有限/溢出数字、高精度小数、无效 schema、
缺失文件、敏感键值和原始输入不变。`--audit-metadata` 显式开启后只忽略审计
文档根 `generated_at` / `reprollm_version`；不借助模型 dump 填默认值或改别名。

首次全量因本机 Git 2.25.1 不支持 `init -b`，出现 3 项 quickstart 相关失败，
另有 2524 passed、2 deselected，耗时 243.865 秒；首次独立 quickstart 也因此失败。
本轮起初未沿用历史环境前提，造成了这次可避免的重跑，不是新代码回归。
经读取内容并核对历史哈希后，复用 S1-A 已审阅的临时 Git 兼容包装器，仅改变验证
进程 PATH，不改系统 Git、仓库源码或测试。包装器 SHA-256：
`87a9309323f9e82d8721b7bd58cac0c1a8f08e44a4348fbf6d476854aa19b298`。
先确认 quickstart freshness，再得到上表最终全量成功。流程已补环境预检。
另一次计时命令启动因本机没有独立 `time` 程序退出 127，未启动测试；改用 shell 内建计时。

## 五项目与资源门的适用性

本轮是 CI/验证工具/流程改动，按流程 §3：产品 Gate A 为 **NOT_APPLICABLE**，
不是 PASS。未修改 pins、规则、profiles、hints 或正式 gold。Gate B 未激活；
没有下载权重、真实训练/推理或 API 费用。

额外使用已审阅历史文件
`2026-10-13-reliability-s3a/r07b-gate-baseline-comparisons.json`
中的五组 `label=L0-default-full` expected/actual，验证新比对器的接线。
来源文件 SHA-256：`b565c6f9a01be00b11048cbeb33005edc129f96f77d9077a11bef916440478ce`。
对五项目分别用 `jq` 只读提取两侧对象，通过管道文件交给
`python scripts/compare_gold.py <expected> <actual>`（严格模式），均退出 0、零差异。
这是对历史完整报告的工具检查，不是本轮产品重跑、独立 gold 复审或重新生成 expected。

比对器首版不采集 checkout、不执行完整五项目矩阵，也不比较 JSON 之外的 stderr、
文本、生成文件或缺失于 JSON 的 hints；这些义务仍由 Gate A 执行者完成。
原始文件只保存一次，比较报告通过字节哈希和全部差异位置引用，不复制整个 payload。

## 效果与后续

已经消除 Windows marker 覆盖错误，并把重复全量质量门从“每任务一次”改为
“最终会话一次”。以本轮约 6.2 分钟的完整测试为参考，每少一次无必要全量就能避免
这一级别的重复工作；这是频率估算，不是端到端加速实测。Gate A 矩阵缩减的实际
耗时应在下一次产品会话按相同输入记录，当前不宣称已节省某个百分比。

完整自动采集 runner、扫描器进一步提速和新增研究案例转正式门不在本批完成范围。
后续 S3-B 仍按 R04-A → R04-B 执行，并采用本轮新频率。
记录时本地门已通过；新提交远程 CI 尚未运行，不以 Linux 结果替代跨平台验收。
推送后按对应 commit 的 Actions 结果确认；GitHub CLI 当前未登录，公开只读 API 可用。
