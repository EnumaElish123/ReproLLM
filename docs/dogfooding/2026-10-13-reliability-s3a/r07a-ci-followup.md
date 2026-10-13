# S3-A CI 收尾：恢复原 slow/nightly 测试选择

日期：2026-10-13。R07-A/R07-B 与性能跟进的产品提交、质量门及五项目结果保留。
`c3f843b3e5967452daf991ac95a5084dc65c1a2b` 的四个 CI 作业通过，Windows
再次仅在原 `test_large_repo_audit_budget` 失败：覆盖率条件下 17.1 秒，超过 10 秒。
[实际失败记录](r07a-ci-followup/windows-second-failure.json)保留这次观察。

## 原合同与配置错误

M8-T04 要求两个 `slow` 性能预算由 nightly 执行，每 PR 的普通质量门使用
项目默认 `-m 'not slow'`。原 nightly 使用 Ubuntu/Python 3.12，运行
`pytest -q tests/perf -m slow`，没有覆盖率插桩，10/15 秒预算保持原样。
原 spec §22 T-09 同时要求 Windows 排除 `linux_only`。

Windows 作业追加的 `-m "not linux_only"` 覆盖了 pytest 配置的 marker 条件，
意外把两个 slow 测试带进覆盖率质量门。[只读合同复核](r07a-ci-followup/normative-readonly-review.json)
绑定实际 Git 对象；它不把两次 Windows 超时改判为性能通过。

并行的 VOPT-01 已以 `ae9adbe` 修正为 `not slow and not linux_only`，并登记
现有 slow marker。S3-A 没有重复提交该配置或认领 VOPT 的工作。
其测试与最终完整质量门见[独立 VOPT 报告](../2026-10-13-validation-workflow-optimization.md)。

## 实际收集与性能核对

在 c3f843b 的独立副本，以实际 pytest CLI 收集并保留完整输出：

| 条件 | 退出码 | 实际选择 |
|---|---:|---|
| 原 Windows marker | pytest 0；验收断言 1 | 2,505 项，其中错误包含两个 slow 测试；真实 RED |
| 修正后的 Windows marker | 0 | 2,503 项，等于默认普通集减去两个 linux_only；GREEN |
| 普通默认配置 | 0 | 2,505 项，两个 slow 均排除 |
| 原 nightly 条件 | 0 | 恰好两个原性能测试 |
| linux_only 参考集 | 0 | 恰好两个平台测试 |
| 原 nightly 性能测试，无 coverage | 0 | 两项均通过，pytest 整组 14.47 秒，命令 14.862352 秒 |

最后一项的 audit call 8.96 秒包含造文件与 Git 设置；它不是审计内部墙钟值。
原测试内部的 10/15 秒断言均通过。以上是 Linux 观察；未取得独立的
Windows 无覆盖率性能 PASS，普通 CI 通过也不会证明该额外性能结论。

初始两次收集 harness 因便携输出检查拒绝任务目录路径而退出，尚未运行产品测试；
修正为先保留原始流、再替换精确路径后，重新收集得到上述真实 RED/GREEN。
参数化安全案例中的三个绝对测试路径也作一致映射，完整私有原流与双 SHA 保留，
12 个输出流的逆向恢复通过。[准备说明](r07a-ci-followup/preparation-notes.json)、
[完整证据索引](r07a-ci-followup/index.json)、[实际选择断言](r07a-ci-followup/summary.json)。

## 输入与交接

相对 c3f843b，并行工作到 `63ecdc5` 的 `src/`、schemas 和 uv.lock 字节不变，
150 文件产品清单仅 pyproject.toml 的 marker 登记发生变化，产品依赖未改。
R07-B 获批 §13 内容逐字节不变；整体规范另由 VOPT 澄清 §22 T-09。
[来源绑定](r07a-ci-followup/source-binding.json)保留这些实际差异。

S3-A 产品最新验证仍为 2,505 tests、174 security tests、14/14 质量门通过，
五项目 126 条全新命令、987 项完整比较及独立 30 项核对通过。
VOPT 的追加测试由其报告记录为 2,527 tests / 174 security tests；这是独立
工具会话的完整质量门。CI/文稿收尾没有新增产品行为，不冒称重新运行 Gate A。

最终 main 五项 CI 在最后推送的实际 HEAD 核对，结果见会话最终回复与本地
final-ci.json。下一工程会话仍为 S3-B：R04-A → R04-B；R07-C、D01 和历史
VAL-R01–R03 的待决/BLOCKED 状态不变。
