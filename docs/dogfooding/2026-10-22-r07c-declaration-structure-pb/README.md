# 2026-10-22 · R07-C D-M-S / P-B

状态：IMPLEMENTED，最终验收 IN_PROGRESS。维护者已接受方案 A 及具体规范补丁。

基线 `bd80e78fdad1b80d150375cfea2fe68a6a2e1565`，分支 main，起始工作区干净。
本次只实施规范 §12.3.7 的有限结构表，保留部分提取、既有信用和优先级。

[接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/decision-accepted.json)、
[P-A 报告](../2026-10-22-r07c-declaration-structure-pa.md)、
[独立验收预期](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-structure/acceptance-cases.md)。

先记录新增回归 RED，再最小实施 GREEN。核心 RED 为 106 failed / 216 passed / 1 skipped，
全部 106 项失败均是旧实现缺少 `invalid_structure`；核心 GREEN 为 322 passed / 1 skipped。
规则／CLI 新回归 RED 为 45 failed / 10 passed，既有 scope 预期修订 RED 为 6 failed / 4 passed；
最终 8 个受影响规则／CLI 模块 GREEN 为 401 passed / 4 skipped（145.53 秒）。
跳过是既有平台前提；完整质量门使用管理员测试上下文核验适用符号链接安全测试。

产品只修改 `core/deps.py`，复用原 D-M 规则消费。独立审阅与静态保护检查通过：
18 个原 P-A 文件及 177 个受保护产品／工具／schema 文件保持字节，规范恰为已接受补丁。
没有 fixture／gold 更新。原始临时目录权限失败、仓库内临时目录的父 Git 干扰及一次无效测试目录
选择分别保留为环境／准备记录，不计入有效 RED 或 GREEN。

最终完整质量门之后运行全五项目 Gate A、全部 init/L1/default export 与结构专项。
本机无付费 API 调用，无版本发布。

资源 Gate B 对普通政策会话 NOT_APPLICABLE。既有 VAL-R03 的原始 metadata 缺失及 HF
授权阻塞仍单列保留；本地产品验证不解除它们，也不重写历史资源验收。
