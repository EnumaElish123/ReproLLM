# S2-A / R05-A Python 精确版本

日期：2026-10-10。前置 main：`a80a84eb61dfc2ad381e67228050f5ecf1995b04`。
按 S2 任务卡顺序执行；规范 §12.2、§13、§22。

使用已有 packaging 验证单一非通配 `==`，Poetry 另支持合法 bare version。
requirements、PEP 621（含 optional）、Poetry、Pipfile、嵌套 pip 共用
版本判定；local/pre/post/dev/epoch 保留。重复相同 clause 去重；不同多约束、
arbitrary equality、URL/VCS/path、unsupported types 保守 nonexact。
声明、requirements-as-lock 与 critical findings 的版本判断保持一致。
精确版本不承诺相同 build、平台或文件哈希。

R05-S 的具体 A/P+C 已明确接受，[决定](../../plan/reliability-2026-10-03/proposals/R05-S/decision.json)
保存用户原回复与固定提案、完整 patch 及独立来源摘要。A/P 规范本项同步；
Conda 规范与实现待 R05-B。本项尚未实现 include 闭包，按顺序交给 R06-P，
没有新增 scope 政策。

132 个新测试和 225 项 focused consumers 通过。独立审查先后实证并推动
VCS 表混合 version、转义 marker 字符串来源行、comment/description 抢行号
及重复相同条件的回归。TOML 来源索引仅在已支持 dependency value 数组
定位并解码单行 quoted token，未实现完整 TOML lexer。
实际 RED/GREEN、脚本预期修正与 SHA 分开保留，未把非零退出改写为通过。

[完整质量门](r05a-quality.json) 14 项全通过：2253 tests、2 既有 slow excluded、
1 既有 marker warning、总覆盖 93%、redaction statement/branch 100%、
security 124 tests。pytest wall 325.568 秒；Ruff、strict mypy、
四项生成文档及十项 exported schema 完整集合/字节全部通过。
沿用 S1-A 已验证的临时 Git init -b shim，不改系统 Git 或依赖。
[TDD ledger](r05a-tdd.json) 保存 18 次开发命令及其原有非零退出、分类、时长、
前后 source/test SHA 和全部 retained logs 摘要；[独立审查](r05a-independent-review.json) PASS。
[candidate summary](r05a-candidate-summary.json) 为冻结时快照，最终状态以 quality、Gate 和 commit binding 为准。

[五项目 Gate A](r05a-gate-evidence-index.json) 完整 PASS：actual=qualified 95 leaf
（fresh baseline45 + affected50），2077 项比较/检查全部相等（180+1897），
退出0共95次；没有失败、重试、复用 leaf 或 unknown。leaf 时长213.670885秒
（基础175.516884 + affected38.154001），wrapper189.700560秒独立列出，
不重复相加。每项目58个独立字面格式 case，加真实 audit JSON/default
consumer及完整 offline discover；来源路径与物理行、critical finding、exact
和 requirements lock 同时核对。R06-G 已合格安全边界仅在全部60 retained
SHA、精确提交archive和保护源字节校验通过后复用；本阶段基础与 affected
命令全新执行。完整 raw 与生成artifact保存后，仅清理本阶段 disposable clones。

72 个 retained schema1 文档的可移植字节及 raw 来源摘要均验证一致。
149 product files 的验证前后 inventory SHA 为
`9cff34aa063bb5cd828e914282ee772c62ceedf6b31003bdd6ce1740e2b9edf3`。
提交后绑定见 [commit binding](r05a-gate-commit-binding.json)。

五个原始固定 pin、gold、golden snapshots、依赖文件与 D-41 冻结文件不变。
提交后完整 Git product tree 与验证 inventory 再绑定。
下一项 R06-A 保留同名文件路径身份；历史资源 VAL-R01–R03 仍 BLOCKED，
本批 offline Gate A 不代替 GPU/API/weights/judge 验证。
