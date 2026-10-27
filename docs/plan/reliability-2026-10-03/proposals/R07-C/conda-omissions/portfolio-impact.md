# D-M-CE 五项目独立源码适用性

读取所有五个 `val.md §2` 固定提交的完整 Git tracked-path 列表，独立复核 SHA、
origin 与前后干净状态。无产品 parser/audit/init/lock 执行；非 fresh Gate A。
全部 source-list 命令、计数、字节和哈希见
[portfolio-source-evidence.json](portfolio-source-evidence.json)。原始路径列表留外部。

| 固定项目 | tracked environment.yml/.yaml | 实际 native member | 条件预期 delta |
|---|---:|---:|---|
| lm-evaluation-harness | 0 | 0 | 空 |
| FastChat | 0 | 0 | 空 |
| LlamaFactory | 0 | 0 | 空 |
| HarmBench | 0 | 0 | 空 |
| llm-dp-finetune | 0 | 0 | 空 |

完整 tracked 路径中都不存在目标 basename，因此无需猜测其中的包语义或安装器
行为，也不存在先过滤后遗漏此触发的假零。原来源 pin、依赖 warning 集、profiles、
hints、相对路径／行号、诊断、init 生成文件的独立预测全部保持。
不从当前产品输出复制新 gold；五项目 gold 不变。

这只证明本片对固定五项目零适用性，不能证明新触发/全仓保守代价正确。
未来 P-B 必须合成回归先 RED，再验证最小实现、一次最终完整质量门、fresh
五项目 Gate A 和受影响解析／规则／CLI消费者；P-A 不冒充这些门已经通过。
旧资源通过与本轮 source-only 盘点保持各自身份，公共模型 VAL-R03 不重新打开。
