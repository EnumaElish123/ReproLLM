# 2026-10-22 · R07-C D-C / P-A

状态：**REVIEW_READY / PROPOSED**。推荐有界 requirements 行内注释方案 A；尚未批准/实施。
本片继续当前执行计划，完成具体方案、未应用规范补丁、兼容成本、独立验收和当前产品观察。

## 基线及实际进度

本次 `main` 先以 fast-forward-only 同步，结果 already up to date；登记前 HEAD 为
`e52e0a24f28fa3ef56cc8e49821962eb1c73869c`。其中 D-G 产品提交为
`d823f90c28229ef90a2f5740f1149c4af7ffdf76`，此前 D-G 最终质量门、五项目 Gate A 和受影响验证已完成，
详见其[P-B 报告](2026-10-22-r07c-requirements-depth-pb/README.md)。
基线 `e52e0a2` 的[五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/39711763878)
属于该提交，不能替代本片新提交的 CI。

S1–S4-B 工程已交付；R07-C 更广范围仍 OPEN。没有另一个已具体批准、可直接实施的本地政策片。
按执行总则继续 P-A：普通 requirements 行内注释有真实源依据，比扩大到全部 grammar 或统一 SKIP 更容易准确验收。
旧提案、D-G 裁决与原始证据全部保留，D-G A/B 的委托不等于本片授权。

## 本轮交付与观察

见[提案包入口](../plan/reliability-2026-10-03/proposals/R07-C/requirements-comments/README.md)：
具体 A/B、精确 §12.2 补丁、兼容矩阵、35 组独立未来验收、本地 spec issue 草稿、32 组当前输入和完整观察。

A 仅在原 ordinary route 完整行解析失败后，为无任一结束反斜杠物理行的 captured file 尝试首个 ASCII
SPACE/TAB + `#` 的合法非 URL 前缀。原分类、原成功解析、其他格式、读取和预算保持。
它可能新增 exact/requirements lock 信用，也可能新增 loose use、medium profile 和 init scaffold，
所以隔离 warning 门可能 1→0 或 0→1。所有具体限制和成本都列入待决问题。

32/32 原预写当前投影匹配，完整观察耗时 `0.2602855000004638` 秒；
投影范围仅有序 name/exact 对、原始关键规则 statuses、body issues 和 D-G frontier。
完整 graph/closures/read traces/findings 同时归档，没有把未独立预写的字段算成 gold。
最终成功的 32 组观察没有运行 engine/CLI、profile/provider detection 或候选 comment parser。
观察器第一次开发调用被其 socket guard 拦住 `socket.gethostname`，没有网络请求；
移除可选 profile/provider 观察后在新隔离目录重跑成功，输入/预期未修改，见[重放记录](../plan/reliability-2026-10-03/proposals/R07-C/requirements-comments/observation-replay.json)。

五项目进行了固定 pins/origins/clean 和实际源码字节核对，详见[影响分析](../plan/reliability-2026-10-03/proposals/R07-C/requirements-comments/portfolio-impact.md)。
HarmBench 第18/19行会新增 art/tenacity 两条非关键声明，移除两条诊断，并使 root grammar closure
complete false→true；仍有非 exact 成员，因此 is_exact 仍 false，不新增 root lock。
其他四项目无新增候选；完整 findings/profiles/hints/init/L1/export 的不变预期及理由也逐项记录，
不是零 facts 差异声明，也不是新 Gate A PASS。未来政策执行次数为 **0**。

## 检查与交付身份

本片类别 **DOCUMENTATION_ONLY**。未修改 src/tests/schema/CI/正式工具、依赖、版本或现行规范。
472 个受保护文件的原字节基线和复核见[交付基线](../plan/reliability-2026-10-03/proposals/R07-C/requirements-comments/delivery-baseline.json)。
临时观察器只在独立私有目录执行，作为 `.py.txt` 留存，不加入正式产品或验证工具。

本地完整产品质量门、五项目 Gate A、Gate B 均为 **NOT_APPLICABLE**：
依据[验证流程文稿类别](../plan/validation-workflow-2026-10-13.md)和 val.md 的适用门，
本轮不改产品、不完成里程碑、不准备发布。无受影响生成文档。
文稿链接、JSON 唯一键/schema_version、相对路径隐私、原字节哈希和 `git apply --check` 的实测结果，
见[文稿检查](../plan/reliability-2026-10-03/proposals/R07-C/requirements-comments/document-checks.json)。
本包 `.gitattributes` 保留证据原字节，SHA256SUMS 不包含自身。
首次默认 staged 空白检查把原 CRLF 证据及 unified patch 的 context 空行报为尾空白；
保留字节，按单次 `cr-at-eol` 设置检查其他文件，精确 patch 单独以 `git apply --check` 验证。

本片 Conventional Commit 为 `docs(spec): propose bounded requirements comments (R07-C D-C)`。
本稿不自填未来提交 hash；提交/推送后核对精确新 HEAD 的 push workflow、全部五个 jobs、
五个 candidate-checkout 步骤及 Ubuntu3.12 schema/docs/examples。交付前 CI 状态为
**PENDING_NEW_COMMIT_AND_PUSH**，最终实际 SHA/CI 链接在交付答复记录，旧 CI 不替代新提交。

## 后续和资源边界

下一步需对[具体 A、规范补丁及兼容成本](../plan/reliability-2026-10-03/proposals/R07-C/requirements-comments/spec-issue-draft.md#可直接裁决的问题)
作具体选择。接受后进入本片 P-B：先 RED，再最小实现，最终质量门、五项目 Gate A 和受影响消费者；
选择 B 则本缺口继续 OPEN。本地 spec issue 草稿符合执行总则 §5.9，未对外发帖。

五份原始 metadata 和已记录 HF403 仍阻塞 VAL-R03；未重新发起资源探测。
VAL-R01/R02 的历史 PASS 沿原候选保留，不能称为新 HEAD 的资源验收。
A02 真实反馈、A03 申请人信息/提交授权仍待实际来源；其他 package-value/string grammar、
续行/约束、未知 use、listing/framework 和充分证据继续 OPEN。
没有调用 GPU、推理/训练、付费 API、discover、外部邀请或版本发布。
