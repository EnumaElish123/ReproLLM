# Poetry 显式 version 边界：五项目来源核验

本次只读来源审计，不是新产品 Gate A。48 条 Git 命令均退出 0；五项目固定 SHA、origin 与 tracked/untracked clean 前后不变。17724 个 tracked 路径、17675 个当前 scanner 候选完整清单保留私有，未跑 dependency parser、audit、init 或候选政策。

| 项目 | 完整候选数 | 已遍历 pyproject | Poetry 条目 | Pipfile | 影响预期 |
|---|---:|---|---:|---:|---|
| lm-evaluation-harness | 16413 | pyproject.toml | 0 | 0 | source-only zero-applicability；条件零差异，未执行 |
| HarmBench | 381 | 无 | 0 | 0 | source-only zero-applicability；条件零差异，未执行 |
| LlamaFactory | 597 | pyproject.toml | 0 | 0 | source-only zero-applicability；条件零差异，未执行 |
| FastChat | 218 | pyproject.toml | 0 | 0 | source-only zero-applicability；条件零差异，未执行 |
| llm-dp-finetune | 66 | 无 | 0 | 0 | source-only zero-applicability；条件零差异，未执行 |

三个 pyproject 均 read-admitted、tomllib 解码成功，原始 `tool` 中没有 `poetry` 键。原始文件字节与 HEAD blob 完全相等：

- lm-evaluation-harness/pyproject.toml：5948 bytes，SHA-256 `88b654cba602d6d1bd2ed8cd164f960ebfe325344430345d83e7be0c4a1e72e1`。
- LlamaFactory/pyproject.toml：3382 bytes，SHA-256 `d2d044de25f84d319338de30299437ee882650e2a998af50f617bfbb5964becf`。
- FastChat/pyproject.toml：1342 bytes，SHA-256 `413be30fdc6b5c94746acc86197c447c5ce75d240013e08d9aa57c1766196cbe`。

无 Poetry 依赖条目，因此逐条 name/raw type/version key/type/value/transport/physical line 清单均为空，完整源文件与所有 section 物理行已核对，未以汇总数替代非空条目。Pipfile 独立盘点为零，不自动并入政策。PEP 621 依赖及 lm-eval 的 dependency-groups 属其他来源，不从其数量推导 Poetry 输入。

对于限定到已遍历 Poetry 显式 version 字段的未来方案，五项目没有真正触发输入，预期其现有声明、诊断、锁关联、规则、profile/hint、init/export 与退出行为不变；这只是独立源预期，不是候选执行或 gold 更新。需要合成用例和将来 P-B 新鲜完整 Gate A 验证真实触发及消费者影响。
