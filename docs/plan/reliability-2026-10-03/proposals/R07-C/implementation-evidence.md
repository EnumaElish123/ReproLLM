# R07-C：当前实现的公共审计观察

来源 `055c5fb880f4e374555a1d229b79d0d612c80350`；**当前程序观察，不是未来R07-C验收或新gold**。通过public run_audit完成11例、13项预写检查；active Python limit=1/2、proc gateway非Git返回、固定合成host/user和不可读文件边界均为观察夹具控制。未调用私有规则/parser helpers；没有真实网络/子进程/重依赖/模型/资源请求，未读凭据，前后source hash相同。

[完整机器记录](implementation-evidence.json)、[原始总观察](observations/original-observations.json)、[来源索引](observations/source-index.json)和[69规则清单](rule-evidence.md)。附件只包含完整JSON audit reports，没有脚本、物理.env文件或可执行合成源码。

| Case | 当前profile mismatch | 当前critical pin | 全量当前JSON |
|---|---|---|---|
| cap-before-positive | fail | fail | [report](observations/01-cap-before-positive.json) |
| cap-after-hidden-positive | pass | skipped | [report](observations/02-cap-after-hidden-positive.json) |
| complete-absent | pass | skipped | [report](observations/03-complete-absent.json) |
| selected-unreadable | pass | skipped | [report](observations/04-selected-unreadable.json) |
| hidden-positive-complete | fail | fail | [report](observations/05-hidden-positive-complete.json) |
| declared-hidden-profile | fail | skipped | [report](observations/06-declared-hidden-profile.json) |
| declared-profile-complete | pass | fail | [report](observations/07-declared-profile-complete.json) |
| one-covered-package-hidden-other | pass | pass | [report](observations/08-one-covered-package-hidden-other.json) |
| other-package-complete | fail | fail | [report](observations/09-other-package-complete.json) |
| known-use-unread-exact | pass | fail | [report](observations/10-known-use-unread-exact.json) |
| known-use-exact-readable | pass | pass | [report](observations/11-known-use-exact-readable.json) |

观察对照：cap前已检测到的未声明high-profile FAIL保留；同signal位于cap后时当前会合成PASS，放宽到完整两文件后变FAIL。单个不可读文件在count以内也可能合成PASS，R07-B现合同不为这种输入增加默认count摘要。声明profile但无检测的当前FAIL，在完整扫描后可变PASS。

critical规则在已知torch exact、未知vllm import被省略时当前合成整rule PASS；完整扫描后产生vllm WARNING。已知torch loose且nested exact不可读时当前WARNING，而读取exact后变PASS。每个case的禁止文件finding仍存在；禁止文件名称与合成值不是实际凭据。

这些现象支撑有界的两规则empty-result hook，不要求一次重做所有mixed scopes。A应保留现有非空finding但明确absence性质；不得把其全部叙述成单调正证据。具体未来状态、message、fail-on/ignore、五项目条件delta须在接受后才实施及验证。

[首次观察器setup资格](observations/observer-setup-note.json)：过宽guard把本地gethostname元数据也拦下，首例提前停止；固定合成API后使用新cases-final-1目录完成上述11例。初次无raw stream保存，不伪造日志/hash或产品失败；初始夹具仍在scratch，未覆盖。
