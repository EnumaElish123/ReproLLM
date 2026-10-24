# Pipfile 显式 version 边界：五项目来源核验

本轮只读来源审计完成：48 条 Git 命令均退出 0，96 个原始 stdout/stderr 完整重算哈希。五项目固定 SHA、公开 origin 及 tracked/untracked clean 在采集前后相同。17724 个 tracked 路径与 HEAD 的完整递归 tree 一致，17675 个当前 scanner 候选完整盘点。未执行依赖解析、规则、audit、init、候选政策或新鲜 Gate A。

| 项目 | tracked 路径 | scanner 候选 | 当前声明 manifest 路径 | Pipfile |
|---|---:|---:|---|---:|
| FastChat | 219 | 218 | `pyproject.toml` | 0 |
| HarmBench | 429 | 381 | `adversarial_training/alignment-handbook/requirements.txt`, `requirements.txt` | 0 |
| LlamaFactory | 597 | 597 | `docs/requirements.txt`, `pyproject.toml` | 0 |
| llm-dp-finetune | 66 | 66 | `requirements.txt` | 0 |
| lm-evaluation-harness | 16413 | 16413 | `lm_eval/tasks/japanese_leaderboard/requirements.txt`, `pyproject.toml` | 0 |

五项目 tracked 和当前 scanner 候选中均没有 `Pipfile`；连大小写不一致的同名文件也不存在。因此 `packages`、`dev-packages`、逐条 name/raw type/version key/type/value/transport/physical line 清单均为空，未略过任何已存在条目。三个 `pyproject.toml` 只用于其他来源对照，原始字节均可读、独立 TOML 解码成功，并与 HEAD blob 完全相同：

- `FastChat/pyproject.toml`：1342 bytes；SHA-256 `413be30fdc6b5c94746acc86197c447c5ce75d240013e08d9aa57c1766196cbe`。
- `LlamaFactory/pyproject.toml`：3382 bytes；SHA-256 `d2d044de25f84d319338de30299437ee882650e2a998af50f617bfbb5964becf`。
- `lm-evaluation-harness/pyproject.toml`：5948 bytes；SHA-256 `88b654cba602d6d1bd2ed8cd164f960ebfe325344430345d83e7be0c4a1e72e1`。

若未来方案严格限制在已有 Pipfile 两 section 已遍历 mapping 条目的显式 `version` 字段，这五个固定输入没有触发来源，条件预期为零差异；该预期未执行，也不是政策批准。来源缺席不能证明畸形输入、规则消费者、CLI 退出或完整管理器语法正确。将来实施 P-B 仍须新增有触发输入的回归与新鲜完整五项目 Gate A。

完整路径清单、原始 source/Git 流保留私有；公开安全摘要只含公开项目身份、相对路径、计数、哈希和边界，不声称仅凭哈希即可重放私有正文。
