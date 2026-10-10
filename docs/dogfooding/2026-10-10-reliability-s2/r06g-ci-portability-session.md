# S2 R06-G：Windows 验证夹具修正

首次最终提交 `a3d6948354841b0fbf4403ef2afb71abe75a3991` 的
[实际CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/38040056703)
中三个Linux job与macOS通过，Windows Test失败。
[原始CI状态](r06g-ci-portability-initial-failed-ci.json)与
[全部实际annotations](r06g-ci-portability-annotations.json)保持原失败事实。

两条失败均发生在R06-G外部哨兵创建：`write_text`在Windows转换成CRLF，
末尾rb字节比较按固定LF预期。把创建改为`write_bytes(text.encode("utf-8"))`，
保留完整静态消费者、Git事实、外部零读取与逐字节未修改断言。产品代码、schemas、
依赖和所有gold均未改。独立审查与精确一行diff见
[r06g-ci-portability-independent-review.json](r06g-ci-portability-independent-review.json)、
[r06g-ci-portability-exact-diff.json](r06g-ci-portability-exact-diff.json)。

本地显式pytest plugin仅对外部fixture的文本写入模拟Windows CRLF：
原测试2 FAIL（pytest报告1.22秒）→修复后2 PASS（4.90秒）。
这份受控模拟与上方实际Windows CI分别记录；没有宣称本地Linux执行是真实Windows。
[完整TDD ledger](r06g-ci-portability-tdd.json)同时保留原始/净化日志SHA。

[完整质量门](r06g-ci-portability-quality.json)：14/14 PASS，pytest 2391 PASS（321.05秒），
security 160 PASS（14.137秒），总体覆盖93.56%，redaction100%，10份schema完整字节一致；
ruff/mypy及四项generated docs freshness均通过。保留既有2项slow排除和1项marker warning。

[后续完整Gate A](r06g-ci-portability-gate-summary.json)：质量门后执行五个原始固定仓库，
5条实际只读`audit . --format json --fail-on never`命令；同进程额外读取5份静态hints，
完整L0/profiles/hints/diagnostics/source比较100/100 PASS。明确`--fail-on never`，
exit0×5用于收集完整输出，验收依据为独立完整gold而非退出码。
实际child耗时55.975987秒，stage墙钟58.438519秒，unknown/reuse/wrapper均0。
5pins SHA/origin/clean与149产品文件前后相同，产品库存仍`c1c1173f15991a33ebf89067d1376c70b4f435aeec789b67653689be1e3f8115`。
无非资源命令行为变化，因此未重复init/export；S2逐项fresh验证继续由原始证据绑定。
[17份portable artifacts完整索引](r06g-ci-portability-gate-evidence-index.json)与20份原始输出索引保留。

首次CI失败不改写为通过。修正后main提交的精确HEAD五job结果与URL在最终交付消息中记录。
R06-B仍PENDING；YAML physical-source-index仍UNASSIGNED；历史VAL-R01–03仍BLOCKED。

[补充文档与证据检查](r06g-ci-portability-final-document-check.json)已核对全部索引、schema/portable JSON、来源SHA与112条历史/本次TDD日志。
