# S4-B / D03：修正后的最终五项目新鲜 Gate A

2026-10-18，在 uv 构建 marker 修正后的最终完整质量门结束后重新执行。原 gate-a 的采集结果和原始输出另行保留，本目录为新的 50 条实际命令。**五项目全部 PASS；10 份完整 JSON 比较共 0 个差异，完整默认 stderr 比较全部相等。** 产品源码、schema、依赖及比对器的字节库存前后不变；没有修改 gold 或项目 pin。

本批 D03 修改 CI 和验证工具。按维护者要求额外执行五项目新鲜基础层，不把工具例外写作产品验证通过，也不将该基础层当作发布资源矩阵。

| 固定项目 | SHA | 新鲜产品命令 | 完整比较 |
|---|---|---:|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | L0 audit + facts | 2 PASS，0 差异 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | L0 audit + facts | 2 PASS，0 差异 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | L0 audit + facts | 2 PASS，0 差异 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | L0 audit + facts | 2 PASS，0 差异 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | L0 audit + facts | 2 PASS，0 差异 |

每个新建临时 checkout 的执行前后 SHA、公开 origin、tracked/untracked 干净状态均通过。另逐一核对全部 17,724 个 tracked 输入与固定 Git blob；Python 文件数为 816 / 148 / 311 / 123 / 46。

10 条产品命令、10 条完整 JSON 比对命令、30 条前后 Git 身份命令全部 exit 0。三路并行的墙钟为 **60.774684 秒**，产品命令累计 **70.857644 秒**，全部命令累计 **73.370015 秒**；累计时长不当作墙钟。

独立预期沿用已提交 S4-A 的审阅 oracle，并逐文件核对其不可变索引哈希。audit 使用 `compare_gold --audit-metadata`，只豁免规范 T-02 允许的根时间和包版本；完整 facts 中的 hints、profiles、路径、imports、declarations、frameworks 和 diagnostics 均严格比较。stderr 仅规范 CRLF 为 LF 后比较完整文本，原始物理字节及哈希保留。Linux / Python 3.12.14 的预期在本次 Windows / Python 3.12.9 上全部相符，没有按当前输出补写 expected。

PASS 表示符合完整 gold；LlamaFactory 的 tracked `.env.local` CRITICAL、未固定依赖 warning，以及 lm-eval 的 500/816 扫描限制仍然可见。guarded CLI 和 facts collector 禁止网络连接及重型框架导入。

准备期间 lm-eval 首次长路径 checkout 遗漏 16 个文件；未在该无效输入上运行产品命令。仅在本任务副本启用 Git 长路径并移至较短临时目录后，全树字节与干净状态复核通过。LlamaFactory 唯一 Git 软链接 `CLAUDE.md` 在 Windows 默认 checkout 中表示为目标文本文件；该平台事实已记录，完整输出预期不变且比较通过。

入口与证据：

- [summary.json](summary.json)：完整目标状态、比较语义、时长及范围。
- [commands.json](commands.json)：50 条精确逻辑命令、退出码、耗时、原始 stdout/stderr 哈希与长度。
- [comparisons](comparisons/)：10 份完整 JSON 差异报告，均无差异。
- [oracle-provenance.json](oracle-provenance.json)：独立来源、审阅索引及采集器哈希。
- [input-verification.json](input-verification.json) 与 [preparation.json](preparation.json)：最终输入与准备失败原貌分开记录。
- [product-inventory.json](product-inventory.json)、[harness](harness/) 和 [evidence-index.json](evidence-index.json)：产品字节约束、惰性归档采集器及证据完整性。

全部 100 份原始 stdout/stderr 和完整逐文件输入库存留在任务临时目录，以逻辑标识及哈希引用。未运行 GPU、模型、付费 API 或受限 provider 场景；此结果不关闭 VAL-R01/R02/R03 或发布 Gate B。

归档文本仅将物理 CRLF 规范为 LF，并验证 JSON 数据相等；原始采集哈希和预期 source 哈希不变。转换回执见 [archive-conversion.json](archive-conversion.json)，LF 文件索引与 Git clean-filter 实际归档字节另行核对。
