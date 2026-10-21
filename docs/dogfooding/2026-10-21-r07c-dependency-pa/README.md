# 2026-10-21 · R07-C dependency format-lock / P-A

状态：**下一批选定局部 D-L，具体方案及补丁 PROPOSED；P-B 尚未实施**。
起点 `9cabdc80ecab7728b1ee08c79fc408dd202a6e28`；此前 profile-P 的本地与
[五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/39532772125)已完成，不借用其成功充当本轮验证。
本轮先 fetch 并确认 main/origin 同 SHA；原三项 WIP 在 main 保留，准备发生在独立 worktree。

## 下一步范围

按 [05 §5](../../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md)接续非空依赖缺证据分支。
[具体 D-L 提案](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/R07-C_dependency_lock_credit.md)
仅在既有 in-use 包缺少 exact/qualified 信用，且 primary-Python incomplete/unavailable、包名又存在于已采集格式 lock 中时，逐包 SKIPPED/INFO。
这针对遗漏 import 可以新增 R06-B lock 归属信用的真实反例；依赖声明解析独立，未声称 Python cap 隐藏 exact 声明。
其他包、完整视图、已获信用、requirements 闭包与空结果 veto 保持现行合同。

统一将有缺口时所有 WARNING 改 SKIP 会改变 lm-eval 13 条、HarmBench 5 条 gold；本批不采用该方案。
D-L 相对于固定依赖视图使用格式包名上界，五项目无格式 lock，预期完整结果零差异。
未配对 / 错误 owner / uncertain barrier 等成员也会保守 SKIP，不赋予 lock 信用。
读失败或错误 lock 未捕获包名时仍是原有界 WARNING，独立依赖/parser/read/listing 完整性继续 OPEN。

## 已执行检查

| 项目 | 实际证据与界限 |
|---|---|
| 隔离方案观察 | 15 API、2 明确内部 coverage、3 CLI 输入各 baseline/conditional，共 40 worker；20 份完整 JSON 对照首轮通过，仅 T-02 根 metadata 豁免，schema/version另验 |
| 独立预期 | 完整 expected 由旧 baseline 与先冻结的逐包变换派生，在对应 conditional 前写入；条件输出不提供业务预期值，实际时间戳保留 |
| 门与混合 | CRITICAL 1→0；保留另一包 WARNING 的混合场景 1→1；suppression/never 0→0；未用其他失败遮蔽单一缺证据门 |
| 范围与来源 | 四种格式/规范化、隐藏 import 与完整来源控制、无成员/exact/requirements、unpaired 上界、read/parse及独立 dependency-read 未解决控制；40worker仅替换进程内单一 check，源码/HEAD/index/输入原字节保全 |
| 实际耗时 | 观察墙钟 43.336549 秒，全部编排命令累计 41.261222 秒；两者不相加。没有执行失败或重跑 |
| 观察归档 | 170 文件、390 原来源，20 组输入可完整重建；280 次产品 Git 查询受明确只读白名单限制；大原始输入清单/500 文件实例外部哈希绑定，无网络或训练/推理调用 |
| 五项目设计 | 43 次只读 Git 查询，210 原来源与完整 Git blob 校验；所有精确 pin/origin/完整 status 干净不变；完整 Git 与既有 analysis 路径均无四种格式 lock；不是 fresh Gate A |
| 验收测试草稿 | 31 参数化案例/11 新函数，两个既有模块，旧函数 AST 不变；AST 3.10、Ruff/format、apply-check 通过，未运行 pytest 或声称 RED/GREEN |
| 独立复核 | 源码/规范、31 项测试、对照预期与实际、五项目来源综合复核单列；不以作者自检替代 |
| full quality / fresh Gate A / Gate B | NOT_APPLICABLE：P-A 仅新文稿、未应用补丁与条件证据，无正式源码/测试/工具落地；P-B 具体接受后执行完整适用门 |
| 最终 CI | 仅对实际本轮推送 HEAD 单独确认；起点9cab的CI仍只归9cab |

[40 次对照原件与完整差异](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/observations/README.md)、
[观察读回](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/observations-readback.json)、
[五项目完整预写与来源](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/portfolio/README.md)
不重复嵌入完整 JSON。API read/parse 案例实际 candidate=selected=1、parsed=0、limit=1，无文件数 cap；
另在未执行 CLI 测试草稿加入预算内 parse gap 与空默认 stderr 的明确断言。
预运行只纠正观察 helper 的 Ruff 静态格式，未运行失败产品；报告打包预检曾将 10 份外部 Git 原始路径流一并复制，
在生成 packet 清单前已剔除，原件及哈希未变，最终只保留便携来源索引和重建配方。

## 兼容代价与具体决定

新 SKIP 保持 INFO/default，不接受 FAIL-only overrides；孤立 WARNING 或提升为 CRITICAL 的缺证据门可能从1变0。
默认文本沿用现规则，可显示 `Findings: PASS` 并列 skipped 数；默认 export 不展示 SKIP 数或原 notable 警告，
完整 JSON 仍保存未验证 finding。renderer 本身不变，未把这些现象包装成完整依赖验证。

[具体规则/规范/测试补丁及待决记录](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/decision.json)
尚未应用。现规范 §12.3.1 保留非空 WARNING，且原 A/P 接受排除此分支；执行总则 §5.9 要求先接受具体规范修订。
本轮不触及 engine/redaction/schema，因此不额外请求 D-41 模块审阅。
[完整 spec issue 草稿](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/spec-issue-draft.md)保留本地，未向外发送。

接受后依次：先 RED→GREEN 与定向 lint/type；最终完整质量门；五项目 fresh L0 与 init→L1/default export，
另用真实默认 500/501 合成场景核对 D-L 分支；归档、提交、推送 main，确认最终五项 CI。
P-A 原提案、PROPOSED 决定与条件证据原字节保留，接受记录另立。
不改 val gold、pins、历史报告，不发布版本或使用付费/GPU资源。
更广 dependency/parser/read/listing/framework/README/config 完整性与充分证书仍 OPEN，不因此关闭整个 R07-C。
