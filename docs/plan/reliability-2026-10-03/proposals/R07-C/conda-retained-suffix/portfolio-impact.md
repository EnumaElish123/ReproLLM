# D-M-CS 五项目来源盘点及条件影响

状态：SOURCE_ONLY，非fresh Gate A。日期：2026-10-27，产品源身份`22e3dbc`。
五项目及pin唯一来自[val.md](../../../../../../val.md#2-pinned-portfolio)。

本轮重新执行40条只读Git命令，保留80份stdout/stderr原件，逐份核对大小/哈希和退出码。
五个项目的前后HEAD、origin及完整tracked/untracked状态均符合固定输入；没有修改任何checkout。
扫描完整GitTree路径清单，精确选择basename `environment.yml`和`environment.yaml`。

| 项目 | GitTree tracked路径数 | supported环境文件 | native/新placeholder观察 |
|---|---:|---:|---:|
| lm-evaluation-harness | 16413 | 0 | 0 |
| FastChat | 219 | 0 | 0 |
| LlamaFactory | 597 | 0 | 0 |
| HarmBench | 429 | 0 | 0 |
| llm-dp-finetune | 66 | 0 | 0 |

完整SHAs、源路径清单哈希及输入身份见[portfolio-source-evidence.json](portfolio-source-evidence.json)。
因为没有匹配文件，没有解码YAML正文或观察依赖member类型；不虚构decoder/shape成功。

若将来仅接受本片现placeholder赋值点的有限新原因，五项目完整gold delta独立预期为空。
该推断来自源发生数0，不是复制产品当前输出，也不授予任何Conda-valid或完整扫描证明。
没有运行audit/init/export或候选政策，没有改pins/gold；summary无差异不能替代正式验证。
P-B仍须在最终质量后重新执行全部五项目Gate A和受影响扩展，即使源适用数仍为0。

正式盘点命令累计0.481148秒、盘点层墙钟0.609843秒；不作为整个会话耗时。
原始参数/cwd/流保存在私有会话，公开索引仅记录相对逻辑位置及哈希。
资源Gate B按本次文稿类别不激活；没有GPU、Hub或付费请求。
