# 未发送的 spec issue 草稿

建议标签：spec。状态：LOCAL_DRAFT_NOT_SUBMITTED。

标题：R07-C D-I：为已到达却被候选检查拒绝的 requirements include 决定缺 pin 结论。

当前 §12.3.8 的 D-G 明确排除预算内已建节点的 candidate 拒绝；D-M仅含实际正文读取失败。
因此 `requirements.txt` 中声明 torch>=2.5.1 并引用 build/pins.txt 时，即使原候选检查拒绝
该目标且没有正文读取，仍可产生捕获视图 WARNING。需要具体选择是否保守跳过这类absence。

推荐A：私有拒绝set与可读parent规范化include最终求交，输出独立内部tuple，放在D-G之后。
接受其全仓影响、目标可能不存在、孤立WARNING/提升CRITICAL门1→0及默认显示成本。
备选B：保持现行行为。实现/规范两个确切patch、before/after哈希和未来验收在本目录。
未改scanner/engine/schema/读取范围/严重度/gold，不提交外部issue或发布版本。
