# 2026-10-20 · R07-C 局部 A / P-B

状态：IMPLEMENTATION_CANDIDATE，完整最终质量门与五项目验收待本会话收尾填入；不是已验收或已推送声明。
基线：`1ce5d18ec49b1b8ed4110586de1e24fd2fdb2cc4`。

维护者已明确[接受局部 A、规范和 D-41 引擎补丁](../../plan/reliability-2026-10-03/proposals/R07-C/decision-accepted.json)。
实现只改变两条 opt-in rule 的空结果路径；保留所有非空 findings、其他 67 条内置规则、generated rules、
显式 role PASS、severity overrides / suppression / fail-on 及 R07-B 默认 stderr 合同。
更广的 R07-C mixed evidence、listing/deps/framework 和充分证书工作仍 OPEN。

先测试验收从公共 run_audit 和 scan_python 开始；同一 tiny-cap 输入两条 PASS 的 RED
在批准补丁应用后变为固定计数 SKIPPED 的 GREEN。新增 public CLI、核心 counts/invariants、
四格、所有 69 规则及 generated/mixed-role 比较的原始证据将在最终报告归档。
产品 schema、profiles、依赖、版本和历史 gold 不变；没有触发 GPU/paid/Hub 路径。

原 P-A packet、PROPOSED 决定和条件 expected-A 保留原字节。
历史 portfolio JSON 的早期 unknown message 元数据不作为规范；实际 unknown/invalid 使用已接受 patch 的固定 unavailable 文本。
代码采用已审阅 engine hunk。PyScan 的非负 budget 写法仅从 `0 <= limit` 等价改为 `limit >= 0` 以满足 SIM300；政策及数值不变量不变。

最终 task commit、本地完整质量门、fresh 五项目 Gate A 和 init/L1/export 完整比较、
前瞻性唯一两处 finding delta、精确推送 HEAD CI 以及未改用户文件的核验在报告收尾提交填入。
旧资源记录仍各自绑定 `948d164` / `75d1b0`，本次不重跑或重新归属；原始 metadata 缺失与 HF 403 仍是独立外部缺口。
