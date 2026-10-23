# D-M-E 五项目影响：独立来源核对

本轮只做源文件/身份核验，没有运行新政策、audit、init 或 scan_dependencies；不是 fresh Gate A。
val.md 的五个固定 pin 在前后核验中 HEAD、origin 和 tracked/untracked clean 完全一致。
独立完整 Git ls-files、ls-tree 与当前 RepoScanner 清单绑定共 17,724 tracked paths、17,675 static candidates。
其中 exact environment.yml、environment.yaml、conda-lock.yml 均为 0；没有可列出的 pip 字符串或 Conda companion，
因此 YAML loader 和 Requirement 实际调用均为 0。没有条目不能写成已解析成功或坏字符串测试通过。

| 项目 | 固定 SHA | environment/conda-lock 数 | A 的独立预期 |
|---|---|---:|---|
| lm-evaluation-harness | b954108c9baaaa934b4ad842033b31a97ee30816 | 0 / 0 | 全部原报告/诊断/graph/生成文件零差异 |
| HarmBench | 8e1604d1171fe8a48d8febecd22f600e462bdcdd | 0 / 0 | 全部原报告/诊断/graph/生成文件零差异 |
| LlamaFactory | 673048c6a543cbbeaed5b8444b8223dc4e23c721 | 0 / 0 | 全部原报告/诊断/graph/生成文件零差异 |
| FastChat | 587d5cfa1609a43d192cedb8441cac3c17db105d | 0 / 0 | 全部原报告/诊断/graph/生成文件零差异 |
| llm-dp-finetune | 7f8b5dff4b92aae90ceccce3ec959b48307bed9e | 0 / 0 | 全部原报告/诊断/graph/生成文件零差异 |

[逐项目来源绑定](portfolio-source-evidence.json)与[独立复核](portfolio-review.json)保留每个完整清单的 hash、数量、前后身份和空条目集合。
42 个显式 Git 命令的原始流与约 8 MB 完整清单整件留本地，由[源索引](source-refs.json)引用，不重复公开复制。
复验使用公开 upstream 的相同 pin，执行 git ls-files -z / git ls-tree -r --name-only -z HEAD 并与当前候选清单核对。

零触发仅支持这些固定输入的兼容预期；不证明所有 Conda 环境均无问题，也不验证 malformed/unsupported pip 业务分支。
其他名为 env.yml 等非本项目既有候选的环境文件不因 CEP24 允许该名字而被新纳入。
P-B 若获批准，仍须新鲜五项目 L0/facts、profiles/hints、disposable init→L1/export 与受影响 verbose/graph，
按完整独立 oracle 比较零差异；不得用本轮 source-only 结果替代产品门，亦不得重新计入 D-C 的 HarmBench 历史变化。
资源 Gate B 本轮 NOT_APPLICABLE，历史 R01/R02 和 R03 阻塞保持候选身份。
