# A01-A：本机精确输入恢复清单

2026-10-18。**50 个带既有独立 SHA-256 的必需输入 slot 中，12 个已恢复，5 个 MISSING，33 个 ACCESS_BLOCKED，0 个 HASH_MISMATCH。** 这些 slot 对应 42 种独立字节，当前已恢复 8 种。状态与逐文件原路径、来源、大小、哈希和恢复位置见 [input-inventory.json](input-inventory.json)。

| 输入组 | 必需 slot | 精确恢复 | 尚缺内容 |
|---|---:|---:|---|
| val §8.1 原始 M3/M4 metadata | 5 | 0 | 五份原始 manifest；其中 Project C 对应 llm-dp-finetune。不得用 §8.2 输入冒充 |
| val §8.2 Linux H2 supplementary | 5 | 0 | 五份补充 metadata manifest；与原始五份各自保留身份 |
| lm-eval native A/B | 6 | 6 | 轻量配置齐全；框架、权重、数据缓存与资源执行另计 |
| FastChat native A/B | 6 | 2 | 仅原始 answer driver 齐全；两份 manifest、两份 config 未恢复 |
| LlamaFactory native A/B | 6 | 0 | 两份 manifest、两份训练 config 及相同原始 driver 未恢复 |
| HarmBench native A/B | 6 | 2 | 仅原始 pipeline driver 齐全；两份 manifest、两份 config 未恢复 |
| DistilGPT2 DP native A/B | 8 | 2 | 仅原始训练 driver 齐全；两份 manifest、config 和相同 16 条合成 texts 未恢复 |
| formal DeepSeek judge A/B | 8 | 0 | 四关键文件的 A/B 字节未恢复；固定 synthetic answer 必须从确切 config 恢复 |

恢复范围包含当前仓库的公开轻量文件、既有证据 JSON 中的完整字符串，以及本项目全部可达、大小不超过 64 KiB 的历史 Git blobs。共检查 543 份轻量文件、1,632 份证据 JSON、3,533 个轻量 Git blobs；历史对象未额外恢复缺失输入。已知本机 S4-B 暂存目录只有固定上游源码和 wrapper 验证，没有新的 formal overlays。没有扫描无关用户目录。

现有 SSH 连接在 TCP 建连阶段超时，尚未认证；这与模型作者访问许可无关。仅尝试明确的两个轻量 archive，未请求模型或 API。清单保留 `<resource-root>/evidence/runtime-inputs-a.tar.gz`、`<resource-root>/evidence/deepseek-validation-inputs-20260927.tar.gz`、历史 A/B Git commit 和缺失成员的逻辑定位；实际资源根由本机连接配置或维护者提供，不写入公开文档。原始 §8.1 manifest 曾在历史 Linux 会话前缺失，故另记 MISSING，不能仅因远端连接故障假定它们仍存在。

原始 runtime tar 包含早期 A 配置。lm-eval 已审阅的最终 A config 是 `a7bc8316…`，必须按清单的完整哈希及最终 Git 对象核对；不能取同名早期文件替代。DeepSeek A config 和 B config 也不能互换。

除 12 份精确 case 输入，另保留公开依赖与许可共 8 份文件。已从固定上游 pin 核对 MT-Bench 整体 question/rubric、LoRA identity 和 HarmBench behavior 的既有文件哈希；选出的 question 81/82、`single-v1` 和 `profane_insult_generation` 以 schema 1 派生选择文档保存。选择文档的哈希只是本次观察，**不声称存在单条记录的历史独立哈希，也不替代原上游完整文件**。LoRA identity 的原始 JSON 数组则按精确字节保存为 `.json.txt`。DP 16 条 texts 和 judge fixed answer 的缺口在 required dependencies 中单独列明。

FastChat、LlamaFactory 的上游 Apache 2.0 许可和 HarmBench 的 MIT 许可按固定 Git blob 核对并随依赖保留。自有 validation driver 遵循 ReproLLM 的 Apache 2.0；恢复少量 driver 不等于 vendor、安装或执行整个框架。

Python driver 保存为 inert `.py.txt`，索引映射原始 `validation/*.py` 名称。恢复到新的一次性固定 checkout 时，按 `stored_relative_path` 复制到 `original_relative_path`，然后重新计算完整 SHA-256；不要执行归档文件或复制历史 lock、run、输出和 bytecode。YAML 原字节不变；缺失文件不生成占位正文。

当前仅 lm-eval 的 A/B 轻量输入完整。其他 native、H2、原始 metadata 和 formal judge 仍不可完整重放。两份 manifest 通过当前导出 schema，六份 YAML 安全解析、六份 driver 仅 AST 解析，全部恢复文件与独立哈希一致；未导入重型框架、调用模型/付费 API、下载权重或运行训练/推理。这份 A01-A 清单不代表 A01-B、Gate B 或发布验收完成。
