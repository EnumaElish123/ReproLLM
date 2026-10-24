# 官方原始来源与独立边界

2026-10-24 读取，仅静态源审阅；未安装或运行 Pipenv/Plette，未执行 solver，候选政策运行 0。以下链接均绑定 immutable commit；stable 网页和搜索缓存只帮助定位，不用它们断言最新版本。原始第三方全文私下保留，公开只给链接、定位与哈希。

[Pipenv 官方 vendored Plette 包模型](https://raw.githubusercontent.com/pypa/pipenv/83627fdcc2a1fdce8a1daaec3983857382137cbd/pipenv/vendor/plette/models/packages.py)：PackageSpecfiers 的可选 version 字段类型为 str；另一个 Package.validate 分支兼容直接 TOML Float/Integer package 值。因此 mapping.version 的非字符串可单独识别，不能据此否定所有直接非字符串包值。
字节数 3708；SHA-256 `53df67e43c82cfc28316da89db86f6be0202ce02d26682abb1e62314d9383811`；Git blob `e5185f02d291b209ea29b0b06cda04026d04009c`。

[Pipenv 官方 vendored Plette 基础模型](https://raw.githubusercontent.com/pypa/pipenv/83627fdcc2a1fdce8a1daaec3983857382137cbd/pipenv/vendor/plette/models/base.py)：可选字段检查以键实际存在为前提，再检查其类型。缺失 version 与非字符串 version 是不同情况；这为字段存在且类型错误提供来源依据。
字节数 3506；SHA-256 `0f0b363a29333a077314a6ae6d2052d58a42ca3fdbf3b979bec64705e3b5e220`；Git blob `c3d6937f0976c4c60fcb632aba7c9d0757a1adb5`。

[Plette 上游 v2.4.0 包模型](https://raw.githubusercontent.com/sarugaku/plette/fb5bcc588f5a749076af3a8594750e4b9db2580e/src/plette/models/packages.py)：上游有相同的可选 version 字符串类型及直接数值兼容分支，与所读 Pipenv vendored 合同一致；不把 vendor 内容误称为逐字相同文件。
字节数 3683；SHA-256 `8acfb83efbc3f7ff71e57355f23eb44342a07c992a26680203bdfe1d8556009e`；Git blob `ab0adc894fe1b1058448b5f0c73e2fbc269422c0`。

[Pipenv 官方 vendored Pipfile 模型](https://raw.githubusercontent.com/pypa/pipenv/83627fdcc2a1fdce8a1daaec3983857382137cbd/pipenv/vendor/plette/pipfiles.py)：标准 packages 和 dev-packages 使用同类包集合；模型还处理自定义类别。ReproLLM 此轮仍只检查原来遍历的两节，不新增 custom-category 支持。
字节数 4817；SHA-256 `4ab42d14f6f9c1bc7c1bdf509f9b4f6266eab0eb1c2c36433eec3ea8a5ceac6f`；Git blob `9b01a374007ee21c9e2fe82938492e17a919a9b0`。

[Pipenv 官方 vendor 版本清单](https://raw.githubusercontent.com/pypa/pipenv/83627fdcc2a1fdce8a1daaec3983857382137cbd/pipenv/vendor/vendor.txt)：该 release 的 Plette 版本为 2.4.0。此处只证明所读 release 的 vendor 关系，不宣称工作区安装了此版本。
字节数 214；SHA-256 `f0f4b584dc7084c90384a95dd7d5836d515d4b95672bbb6697bc052c70b58bb8`；Git blob `3b80efdf36a9a2b690ab5ad992a77b55e8f85c93`。

[Pipenv 官方 Pipfile 文档](https://raw.githubusercontent.com/pypa/pipenv/83627fdcc2a1fdce8a1daaec3983857382137cbd/docs/pipfile.md)：说明 packages/dev-packages、扩展 version/options 语法、没有 version 的 path/file/git 来源以及自定义类别。其示例不能转成读取器未遍历位置的新保证。
字节数 22487；SHA-256 `7bcceb62417d127c0c3df4f487baf98bf9f15d926b1af21c87fb67a3b1209ffe`；Git blob `624104b8442fa7a9e55f93b2778f62cb0d82ddeb`。

[Pipenv 官方版本约束文档](https://raw.githubusercontent.com/pypa/pipenv/83627fdcc2a1fdce8a1daaec3983857382137cbd/docs/specifiers.md)：区分 exact、范围与 wildcard，并展示 transport 和类别。ReproLLM 的既有 Pipfile allow_bare=False 仍以当前规范为准，不从 manager 文档导入额外 exact 信用。
字节数 13085；SHA-256 `19e1cd3dcc585c76b429ce6a87323f2d642a51d126bca1a39cf9a118002bbf90`；Git blob `637d12f3e07143964b638ad814daaeef21741601`。

Pipenv release `v2026.10.2` 的 annotated tag object 为 `f8c4c115b07b293397110a64d5f01a7a3245c474`，指向 commit `83627fdcc2a1fdce8a1daaec3983857382137cbd`；Plette `v2.4.0` 指向 commit `fb5bcc588f5a749076af3a8594750e4b9db2580e`。精确 fetch 时间与成功响应记录见 source-fetch-record.json；失败定位过程见 retrieval-attempts.json。

这些来源支持显式字段的类型边界，不证明整个 Pipfile 安装失败、存在隐藏 exact、缺失字段不合法、或全仓 SKIP 必然成立。A 的全仓保守影响仍是待具体接受的产品选择；此前 Poetry 的批准不授权 Pipfile 扩展。
