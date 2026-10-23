# D-M-E 兼容性与全仓成本

状态：PROPOSED / NOT_IMPLEMENTED。A 复用既有 `unparsed_requirement`，不新增内部词汇或 persisted schema。

| 输入或消费者 | 当前合同 | 推荐 A 的独立未来预期 |
|---|---|---|
| 非空 pip str，strip 后现有解析真实失败，有已捕获未获信用关键包 | 原 WARNING，或按原更早原因 SKIP | 增加文件级原因；只在原先尚无更早分支时沿 D-M SKIP/INFO |
| 空串、Unicode 空白、tab、换行空白 | 不调用 Requirement | 保持跳过，无新原因；不同于 PEP 621 的空白触发 |
| 成功 loose／exact／extras／marker／direct URL | 原声明与 exact 判据 | 全字段不变；不重新解释 URL 或 marker |
| pip 支持的 -r、comment 或 option 未被当前解析器提取 | 原诊断，未提取 | 记录提取不完整，不判定 pip/environment 无效；不执行／跟随 |
| 原同文件有结构原因，另有失败 str | invalid_structure，保留部分声明 | 原原因优先；诊断不删改 |
| 同包 Conda／pip／其他来源 exact | 原 existential 信用 | 保留；不新增 conflict 或 per-package PASS |
| 合格 conda-lock 或其他已合格锁 | 原信用 | 保留；不撤销项目资格／锁关联，不新建 barrier |
| 双 environment basename | 原同目录配对歧义 | 保持歧义；不借新原因放宽关联 |
| D-F/S 或 D-L 原分支胜出 | 原 SKIP finding | message／hint／evidence 全部不变 |
| 已有 D-M，新增不同失败源 | 原 D-M SKIP | 可扩大排序后的路径 evidence；status 相同不等于零差异 |
| 原 D-G 胜出，新增本片失败源 | 原 D-G SKIP | 更早 D-M 的 message／hint／evidence 接替，需完整比较 |
| 未捕获任何关键包 use | 既有 applicability SKIP | 不从坏文本猜包，不新增 aggregate finding |
| 全部关键包有信用 | 原空结果处理 | 保留 Python empty-result veto；不能一律承诺 PASS |
| 无关 environment 失败而其他项目有多个 use | 各包原 WARNING | 全仓保守 SKIP，明确成本；无 ownership 限制 |
| 默认／promoted 孤立门 | exit 1 | 可 exit 0；FAIL-only override 不提升 SKIPPED |
| 独立 warning／critical 达到门槛 | 退出失败 | 独立 finding 保持，不能用相同退出码掩盖 pin finding 改变 |
| suppression／alias／阈值 | 原机制 | suppression 保留原 evidence 和 reason，按现行合同追加配置 evidence |
| init／profile／hints | 原捕获依赖决定 | 捕获库存未变，生成文件逐字节不变；随后 L1／export 可变 |
| 旧 audit／run／export／snapshot | 原历史含义 | 不重写、不重新标成新政策通过；新 audit 是新结果 |

保持声明逻辑路径和外层 dependency ordinal，不转换物理行号；原诊断用 strip 后文本。
不把 pip 内 -r 变成 requirements 图。若一个文件另被当前 requirements 根发现规则捕获，仍可独立读取并提供信用；
该现有发现不是 embedded pip include 扩展。无这种独立发现的目标仍不读取。
新采集修复、删除或替换失败 str 后按真实当前输入重新计算，不能残留旧原因。

无公开状态／severity／字段形状变更，旧读者继续读取既有 Finding/AuditReport；无 schema_version 迁移。
只记录内部事实，不扩张扫描范围，不增加机密内容回显。五项目原固定输入上的本片触发为零，
这并不验证真实 malformed／unsupported pip 场景，也不改变发布或资源准备状态。
