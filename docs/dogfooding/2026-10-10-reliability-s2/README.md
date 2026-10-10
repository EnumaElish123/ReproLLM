# S2 依赖准确性验证与交付

日期：2026-10-10。按最新方案完成全部五项，维护者明确接受R05-S A/P+C。
[S2-A](s2a-session.md) 与 [S2-B](s2b-session.md) 是完整会话报告；具体边界、
真实RED/GREEN、独立预期、全质量门、五项目差异、失败observer修正及限制见逐项报告。

| 任务 | 提交 | pytest | security | quality | 验证 |
|---|---|---|---|---|---|
| R06G | `a80a84eb61dfc2ad381e67228050f5ecf1995b04` | 2121 | 124 | 14/14 | [报告](r06g-session.md) |
| R05A | `f679570b657a1341778120e80a4cf895ed5281f0` | 2253 | 124 | 14/14 | [报告](r05a-session.md) |
| R06A | `57b1384f748f09ae2af674e31f80ec868eea1972` | 2298 | 124 | 14/14 | [报告](r06a-session.md) |
| R06P | `d1b76ccfd06e8249211c40af57a36fa42cab3158` | 2332 | 158 | 14/14 | [报告](r06p-session.md) |
| R05B | `cb2b98b2377b0618ba523ad00f38b9b8be8f1bb8` | 2391 | 160 | 14/14 | [报告](r05b-session.md) |

每项的 `*-quality.json`、`*-tdd.json`、`*-independent-review.json`、
`*-gate-evidence-index.json`、`*-gate-execution-accounting.json`、
`*-gate-commit-binding.json` 分别保存完整质量、真实开发过程、独立审查、
portable artifact摘要、实际命令/比较统计与提交产品字节绑定。
R06-P与R06-A/R05-B的supplement/export另有自己的index、accounting与binding。
[最终文档与证据检查](s2-final-document-check.json)核对全部索引SHA、文档链接和110条TDD日志；
R06-G的32条原始日志从已保留的验证环境核对，其余归档日志从仓库核对。
原始完整stdout/stderr/harness留在验证环境；repository只保存净化后的schema1
证据及原始字节SHA，不持久化机器绝对路径或身份。时间戳字段只按规范明确例外比较，
不按当前输出改gold。

五个固定仓库均实际验证，原pin/origin/clean状态不变，逐项完整gold无变化。
26个全局冻结文件、fixture input tree/overlays、schemas、pyproject与uv.lock保持字节一致。
R05-B依已接受Conda语义和独立source oracle手改privacy夹具5个expected快照，
仅torch PASS→WARNING及对应计数/排序，详见独立提案、review与真实RED/GREEN；
其余expected及五项目gold不变。
任务产品149文件与验证库存精确绑定；后续仅文档提交不改变该产品库存。

[R05-S接受记录](../../plan/reliability-2026-10-03/proposals/R05-S/decision.json)、
[规范完整composition proof](r05b-spec-composition-proof.json)、
[后续scope/语法/来源交接](s2-handoff.md)。
历史资源VAL-R01–R03仍BLOCKED，S2未执行GPU/paid API/weights/judge Gate B。
下一工程会话为S3-A（R07-A → R07-B）；它尚未执行。

CI字段保留各候选测试时NOT_RUN的历史事实。最终main推送后核对其精确HEAD的
Linux Python3.10/3.11/3.12、macOS Python3.12、Windows Python3.12共五job；
最终CI结果/run URL在交付消息中记录，避免文档commit自引用。

后续Windows CI修正：首次最终HEAD `a3d6948` 的四个job通过，Windows有两条
外部sentinel测试因fixture文本写入转换为CRLF而失败。改用固定UTF-8字节构建，
保留全部原断言；完整质量门再次14/14通过，五项目再执行5条只读命令/100完整比较通过。
[失败事实、真实CRLF模拟RED/GREEN、修正与后续验证](r06g-ci-portability-session.md)
保留原始证据。产品字节与所有gold不变；后续精确main HEAD五job在交付消息记录。
