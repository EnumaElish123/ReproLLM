# 独立依据和范围选择

查阅日期：2026-10-23。以下是格式事实；文件级原因、全仓影响和 SKIP 是另行待决的项目政策。

| 官方来源 | 使用的事实 | 不从它推出的结论 |
|---|---|---|
| [PyPA pyproject](https://packaging.python.org/en/latest/specifications/pyproject-toml/#dependencies) | dependencies 及 optional groups 的字符串应符合 dependency-specifier 格式 | 不要求 ReproLLM 全面验证元数据或规定审计 SKIP |
| [packaging Requirement API](https://packaging.pypa.io/en/stable/requirements.html) | 现有解析器提供字符串结构结果与失败；URL 解析不是在线有效性验证 | 不认证完整标准、不运行安装或网络解析 |
| [Poetry](https://python-poetry.org/docs/dependency-specification/#multiple-constraints-dependencies) | 多条件数组与 source enrichment 有合法形式 | 不把非字符串/无 version 值一律判错 |
| [Pipenv Pipfile](https://pipenv.pypa.io/en/latest/pipfile.html#packages-section) | git/path/file 映射可以没有 version | 不与 PEP 621 字符串混同 |
| [Conda CEP 24](https://conda.org/learn/ceps/cep-0024/#dependencies) | embedded pip 列表交给具体安装实现处理，可调用 pip 等工具 | 不据此将 pip 文件指令按 PEP 621 简单分类；embedded pip 暂留 OPEN |

因此只从 D-M-S 的 OPEN 集合选择 PEP 621 两处现有失败现场。
A 的事实只说明“此字符串未提取”；文件级保守 SKIP、空白也纳入、全仓作用与 D-M 消息沿用
都是本项目建议，必须和补丁一起接受。本片不恢复名称、不扩展 comment grammar 或 manager 校验。
