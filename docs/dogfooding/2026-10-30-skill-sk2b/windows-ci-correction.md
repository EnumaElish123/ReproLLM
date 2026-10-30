# SK2-B Windows 测试构造修正

日期：2026-10-30。产品实现仍为 `e07963d47cb9e0d64a5f0404d5516bf9248b08fc`；
测试修正候选为 `af62013f3829e127c462869e8c0c26fe4ed63094`，没有改动产品或 Skill helper。
本次按[验证工作流](../../plan/validation-workflow-2026-10-13.md)的测试工具类执行完整最终质量门；
Gate A 为 **NOT_APPLICABLE_TEST_ONLY_CORRECTION**，不冒充新鲜产品运行。

## 原始正式 CI

原交付 `916c88391e8055e93237f6466968d8b4ef0514ef` 的
[正式 push CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/41063987624)为失败：
Ubuntu Python 3.10/3.11/3.12 与 macOS 成功，Windows 的 Test 失败。
Ubuntu 3.12 的十二个必需步骤全部 success，不能据此把 4/5 算作完整通过。
Windows Test 用时 29 分 15 秒；旧 `429b3ed` 的成功 Windows Test 用时 21 分 34 秒。
没有取消、重跑或改工作流，原始 failure 收据与原文注解保留。

公开注解确认一个历史 run Unicode fixture 构造失败，以及同一超长参数案例的两条错误。
后两条注解被 262,192 字符的 test name 占满而截断，未直接观察到其被截断的异常文字。
日志下载 API 返回 403，未要求用户提供凭据或日志。

## 根因与最小修正

1. `test_skill_run_display.py::record` 用系统默认编码写入含 70,000 个中文字的 JSON。
   Windows 该执行的 `charmap` 编码无法表示它们，公开注解明确报告 UnicodeEncodeError，
   位置 336–70335。fixture 的写入及原件断言读取现在显式 UTF-8，Unicode 内容与断言不减少。
2. `test_entry_exit_matches_the_serialized_reply` 的 256 KiB 字符串被 pytest 自动用作参数 ID，
   继而进入 `PYTEST_CURRENT_TEST`。Windows 的环境变量长度检查会拒绝该值；这是从冻结
   test nodeid、实际 pytest 更新路径与平台边界得出的原因，并非从被截断注解补造异常。
   原测试在进程内调用 `entry.main([])`，没有超长 `python -c`/CreateProcess argv。
   现在只给两个案例短的显式 ID，256 KiB 数据、无效对象及原退出/完整 JSON 断言保持。
   平台限制由 [CPython 3.12 源码](https://raw.githubusercontent.com/python/cpython/v3.12.12/Modules/posixmodule.c)
   及 [pytest 的同类原始问题](https://github.com/pytest-dev/pytest/issues/6881)支持。

在原冻结测试上加入独立的 cp1252 默认文本 I/O 与 32,767 字符环境边界模型，确定重现
同一 UnicodeEncodeError 和同一超长节点的 setup/teardown 两个 ValueError。
修正后相同三案例全部通过；两个文件原生 105 项与相同边界模型下 105 项均通过。
还比较参数 payload 表达式与原测试 body AST，确认未改变；lint/格式检查通过。
这是 Linux 上的可审阅边界模型，不能声称 Windows 修正已验收。

## 最终验证与边界

修正候选 af620 的完整 24 项质量门与 24 次来源守护全部通过：5,911 测试、2 个 slow deselected，
零失败/错误/跳过；总体覆盖率 93.407%，redaction 分支 100%。
security、lint、格式、类型、十份 schema 与生成文档 freshness、自审计、wheel 及隔离分发均通过。
墙钟 1243.274 秒，命令累计 1236.880 秒；
全部 tracked 输入在门内前后相同。摘要见[修正验收](windows-ci-correction.json)，
逐命令退出码、耗时与原输出 hash 见[索引](windows-correction-quality-command-index.json)。
通用 runner 的旧 A01 label 与 next_step 原样保留；本次 invocation binding 和测试工具类适用矩阵
定义实际范围，不能把通用文字当成已执行 Gate A。

本次 `src/reprollm`、整个 `skills/reprollm`、依赖声明/锁、十份 schema、架构与规范
Git objects 均与已接受的 e079 相同（含 tracked 文件集合、字节和模式）。
旧 e079 的五项目与安装适配证据保持原归属；本次没有重新运行 Gate A、重新安装、
访问 provider、使用 GPU/付费资源、运行第二宿主或发布任何发行产物。
最终修正报告交付提交的五项官方 CI 推送后核对，旧失败不能被本地成功覆盖。
