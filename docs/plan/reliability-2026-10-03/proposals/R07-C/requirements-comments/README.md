# R07-C D-C: requirements 普通行内注释

状态：**PROPOSED / REVIEW_READY**；推荐 A，尚未批准，尚未实施。
基线为 `e52e0a24f28fa3ef56cc8e49821962eb1c73869c`，其中 D-G 产品为 `d823f90`。
本轮只准备下一项 P-A；“裁决 D-G A/B”的委托不延伸至 D-C。

- [具体 A/B 方案](R07-C_requirements_comments.md)与[本地 spec issue 草稿](spec-issue-draft.md)
- [精确规范补丁](spec-proposed.patch)：仅 `git apply --check`，未应用
- [兼容性](compatibility.md)与[独立未来验收](acceptance-cases.md)
- [预写当前输入及投影预期](cases.json)、[当前产品完整观察](current-observations.json)、[观察器原文](current-observer.py.txt)
- [五项目源码影响](portfolio-impact.md)与[源码证据](portfolio-source-evidence.json)
- [决定记录](decision.json)、[交付基线](delivery-baseline.json)、[文稿检查](document-checks.json)、[字节清单](SHA256SUMS)
- [本轮报告](../../../../../dogfooding/2026-10-22-r07c-requirements-comments-pa.md)

当前行为观察只比较预写投影；保存的其他实际字段没有被宣称为独立 gold。
当前输入 C01–C32 与未来验收 C01–C35 属于各自文件的独立编号，不是一一映射。
未来政策执行次数为 **0**。产品完整质量门、五项目 Gate A、Gate B 在本轮文稿类别中均为
**NOT_APPLICABLE**，不能写成 PASS。后续 P-B 必须取得具体批准、先补回归测试，
再实施、执行一次最终质量门、五项目 Gate A 和受影响消费者验证。

本轮不修改旧提案、历史 gold、正式输入、产品代码、测试或现行规范；不调用付费 API，不发布版本。

重放当前观察时，在新的 disposable clone 中保留本包输入，把 `current-observer.py.txt` 按原字节复制到
新私有目录并命名为 `current-observer.py`，从 clone 根运行 Python UTF-8 模式。
先核对 delivery-baseline 和 cases 的原字节 hash；输出只写 clone 中的新证据副本和该私有目录，
不得覆盖本历史包。该步骤不会运行候选 A。32 条投影预期保存在输入中，其他完整字段只留作观察。
