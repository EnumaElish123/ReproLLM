# D-G：五项目独立影响预期

状态：SOURCE_EVIDENCE_ONLY / PREDICTED_NOT_EXECUTED。
日期2026-10-22；[来源记录](portfolio-source-evidence.json)有40条真实只读Git命令、退出码、耗时、hash。
固定HEAD/origin、前后tracked/untracked clean；5份requirements与Gitblob及旧R06-B source hash完全一致。

| 项目及pin | 文件/实际来源 | depth-frontier预期 |
|---|---|---|
| lm-eval b954108c9baaaa934b4ad842033b31a97ee30816 | `lm_eval/tasks/japanese_leaderboard/requirements.txt`，4普通行 | 无include，零新增 |
| FastChat 587d5cfa1609a43d192cedb8441cac3c17db105d | 无requirements文件，pyproject原样 | 零新增 |
| LlamaFactory 673048c6a543cbbeaed5b8444b8223dc4e23c721 | `docs/requirements.txt`，3普通行 | 无include，零新增 |
| HarmBench 8e1604d1171fe8a48d8febecd22f600e462bdcdd | root 21行、alignment-handbook 26行；root18/19为inline comment | 无include，零新增；保留nested exact信用 |
| llm-dp 7f8b5dff4b92aae90ceccce3ec959b48307bed9e | root6行；第4行VCS，5/6注释 | 无include，零新增；不因VCS扩张exact |

总60行：55 plain requirement、2整行comment、2 inline-comment、1 bare VCS；0 include、0 directive。
新事实只来源于typed supported include event；这些输入不产生任何此类边，故不能产生depth frontier。
pyproject/Pipfile/Conda不受本片调整；整个仓库的其他findings、profiles、hints、paths、diagnostics、init文件、L1和defaultexport预期原样。
不能以此替代合成depth边界；五项目没有这种输入，不证明新逻辑正确。

完整原始源行、公开固定URL、SHA256都在JSON。没有运行新产品、未来政策或Gate A。
正式P-A应在D-M-S交付HEAD重新核对产品身份；P-B还须验证旧oracle适配条件并fresh运行完整比对。
如出现任何非metadata delta，先停下来解释，不把当前输出复制成gold。

范围之外真实语法的区别依据：[pip requirements格式](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
包含inline comments、续行、选项与rich来源；[constraints说明](https://pip.pypa.io/en/latest/user_guide/#constraints-files)
区分约束版本与引入包。2026-10-22只读核验，无pip运行。
这些事实只支持区分“产品不支持”与“外部格式非法”，不授权新增本项目信用或skip规则。
