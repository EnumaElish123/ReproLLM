# R07-C D-G 私有 P-A 材料

**未写入仓库；未接受；规范补丁未应用；没有未来产品执行。**
准备发生在当前D-M-S最终验证期间，不影响该会话冻结输入。

- [具体方案与裁决项](R07-C_requirements_depth_frontier.md)
- [精确规范补丁](spec-proposed.patch)及[新增节预览](proposed-section.md)
- [PROPOSED决定与hash](decision.json)、[准备身份和apply-check](preparation-identity.json)
- [30组未来验收](acceptance-cases.md)、[完整未来finding示例](future-finding-example.json)、[兼容性](compatibility.md)
- [22个字面当前输入及预写预期](cases.json)、[当前实际观察](current-observations.json)、[观察器源码](current-observer.py.txt)
- [五项目来源](portfolio-source-evidence.json)、[独立影响预期](portfolio-impact.md)
- [本地 spec issue 草稿与具体决定问题](spec-issue-draft.md)，尚未发送。

当前观察不是新政策通过。observer控制Git非仓库、installed_versions空、无fixture Python imports，
使用真实parser/graph/rule；安全hook禁止子进程、socket及heavy imports。
所有22项简明当前预期符合；完整实际对象保留，但没有伪称每个raw字段都已有独立gold。
观察原字节/源码hash均保留；附加preparation source身份单独标注采集时点。

本包预备的首个patch因私有生成器裁掉尾部context空白而apply-check失败；未触及仓库。
生成器改为保留diff原始尾部后，正式patch检查成功。旧失败patch保留于私有工具目录，
不是本提案的被审patch，也不是产品失败。

下一步由主代理在D-M-S实际交付后冻结新基线、独立审阅最终scope和字面输出、完成文稿检查后，
才能复制为仓库正式P-A。需要具体维护者决定才可P-B；其他已授权文稿/事实核验可继续。
不调用付费API，不发外部消息，不提交申请，不创建tag或发布版本。
