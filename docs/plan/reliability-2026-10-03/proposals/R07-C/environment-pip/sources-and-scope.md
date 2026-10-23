# 官方格式事实与本项目政策边界

查阅日期：2026-10-23。以下为原始官方文档的简要释义；项目级 SKIP 是本次待决选择。

| 原始来源 | 核对的事实 | 不从它推出的结论 |
|---|---|---|
| [packaging Requirement API](https://packaging.pypa.io/en/stable/requirements.html) | Requirement 解析 dependency-specifier，无法解析时会报告异常；URL 成功解析不验证在线有效性 | 不认证完整 pip 文件语法，不决定审计 SKIP |
| [Conda CEP 24 dependencies](https://conda.org/learn/ceps/cep-0024/#dependencies) | pip subsection 是 str 列表，其处理交给具体实现，常见做法调用 pip；环境格式文件名也可不同 | 本项目现有 source basename 集合不自动扩张，不执行安装器 |
| [pip requirements 文件格式](https://pip.pypa.io/en/stable/reference/requirements-file-format/) | pip 文件接受选项、include、注释等，完整语法与 pip 实现相关 | 不将现有 Requirement 失败自动称为 pip 无效，不把 D-C 回退扩展到环境子项 |

本项目当前代码和固定版本依赖决定“实际走到哪个调用、调用得到什么结果”；官方格式事实不能取代这些观察。
因此推荐 A 只记录现有提取失败，保留 strip／空白过滤与所有当前 grammar；不修复文本、不猜名称、不跟随 -r。
全仓保守 SKIP、无关文件影响、既有 D-M 文案和 exit 1→0 是需要具体接受的产品成本，不是上述标准强制要求。
