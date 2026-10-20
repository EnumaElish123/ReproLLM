# 独立验收设计：当前观察与未来 A 分开

状态：PROPOSED_TEST_DESIGN_NOT_EXECUTED。源码基线 `055c5fb`。
[原实现完整观察](observations/original-observations.json)是已执行的 11 个公共 `run_audit` 输入；
下面的 A 列是源码/语义独立推导，不是已经运行 proposed patch。
每例均有最小 manifest、无凭据的合成 `.env`；非 Git 接口、installed versions 和主机标识固定。
Git 走受控 proc gateway；读取失败在文件接口注入，不依赖 root 权限下 chmod 的效果。
生产源码不变。上限 1 / 2 只是进程内夹具，实际产品默认仍 500。

## 必需的四格与完整对照

| 观察 case | 输入与实际 primary Python 视图 | 当前 profile mismatch | A 独立预期 |
|---|---|---|---|
| `cap-before-positive` | `a.py: import vllm`，`z.py: value=1`，limit=1；parsed=selected=1/candidate=2 | FAIL INFO，已观察 inference 未声明 | 原完整 finding 保留，不增加 SKIP |
| `cap-after-hidden-positive` | 将唯一 import 放入 `z.py`，limit=1；1/1/2 | PASS | 单条 SKIPPED INFO、固定 1/2/1/1 counts message、空 evidence |
| `complete-absent` | 只有 `a.py: value=1`，limit=1；1/1/1 | PASS | 原完整 PASS 保留 |
| `selected-unreadable` | `a.py: import vllm` 候选存在，但内容读取失败；limit=1；0/1/1 | PASS；无默认 R07-B count summary | 单条 SKIPPED INFO、固定 0/1/1/1 message；仍不伪造 count-cap stderr |
| `hidden-positive-complete` | 与 cap-after 相同来源，limit=2；2/2/2 | FAIL INFO，inference 未声明 | 与当前完整 finding 一致，证明信号确实位于此前遗漏文件 |

每例的 `env.secret_files_ignored` 仍为原先同一完整 FAIL；这个安全结论不依赖 Python coverage。
合成非 Git 场景原有其他 CRITICAL 可掩盖 exit，所以这些原观察不用于宣称阈值变化。
未来阈值测试应在受控干净 Git / 无其他 CRITICAL 或 WARNING 的输入里独立验证。

## 防止把 absence finding 误作正向证明

| case / 对照 | 当前观察 | A 的预期和未解决范围 |
|---|---|---|
| `declared-hidden-profile` / `declared-profile-complete` | 声明 inference，cap 内缺证据产生 INFO FAIL；同源完整解析后 PASS | A 保留前者 FAIL 和后者 PASS；此 absence 分支保持 OPEN，不当作全域证明 |
| `one-covered-package-hidden-other` / `other-package-complete` | torch 有 exact，cap 外唯一 vllm；前者 critical-deps PASS，完整后 vllm WARNING | A 使前者 critical-deps SKIP；后者完整 WARNING 不变 |
| `known-use-unread-exact` / `known-use-exact-readable` | root loose torch、nested exact 不可读时 WARNING，恢复读取后 PASS | A 不解决 dependency scope：两个结果按旧合同保持，不能把保留 WARNING 称作已验证不存在 exact |

以上四格 + 七个对照共 11 例、13 条当前程序条件，全部 findings 快照和原哈希随材料保存。
不自动将 A 推导结果写成 fixture gold。首次夹具曾把合法主机名元数据调用也拦截而提前停止；
最终观察显式固定合成主机/用户后重新建独立目录运行。前一次未完成观察不计入 11 例或成功证据。

## P-B 必须先写的测试

1. 通过 `scan_python` 和公共 audit 入口验证 cap 前/后、确无信号、不可读、512 KiB/binary/decode/syntax 跳过；
   包括未超数量上限的 parse gap，保留 R07-B 原默认可见性。相同已知 witness 不被 SKIP。
2. 零候选的真实扫描 observed=true；默认 `PyScanResult()` observed=false。
   冻结 coverage 对 invalid counts 返回 unavailable，而不是当 exhausted；合法零 budget 是合法 gap，不用 limit=0 当 unknown sentinel。
3. 不变量：`0 <= parsed <= selected <= candidate`、`0 <= limit`、`selected <= limit`。
   派生 gap/unknown 只从这些 typed facts 和 marker 判断，不匹配 warning 文本；中文或任意 warning 变化不改变结果。
4. 两个 opt-in ID 之外 67 个 built-in 和 generated/project rules 不受 primary coverage gate；
   manifest/lock/State/Git/安全检查、显式 per-field PASS、applies=false 的理由不变。
   非空 mixed PASS/FAIL/SKIPPED 和 profile overrides 原样处理；hook 仅空结果调用，不能启动无关扫描。
5. 完整观测视图逐完整 findings/summary/order 与旧程序一致；gap 的变化严格限定为既定 PASS→SKIP。
   有既存 failure 时不附第二条 coverage finding。正向 high mismatch/缺声明和 independent Git/security 的原 evidence 保留。
6. `--fail-on critical/warning/never`、suppression、默认 JSON 单文档、重复结果确定性和 text 输出均验收。
   SKIPPED/INFO 不算 FAIL INFO，不因 message 或 severity 变化引入新失败退出。
7. `audit` 和默认 `export` 内嵌 audit 用同一候选包；`init` 的 manifest/profile 选择不变。
   十个既有 schema 新旧读取无新字段；schema freshness 必须保持，通过不等于对新 schema 的批准。
8. 五个固定仓 fresh Gate A + 受影响初始化 L1/export，完整 rule/profile/hint/path/diagnostic 对比；
   使用 [portfolio 的预写差异](portfolio/portfolio-evidence.md)，不从当前输出自动更新 gold。
9. 先 RED 后 GREEN，最终一次完整 quality gate 和精确推送提交 CI，按 validation workflow 记录。
   本任务没有受影响的 GPU/paid/Hub 场景，既有资源证明保持原候选。

未证明的 listing/2 MiB 丢项/deps/framework/配置读取/alias 竞态不伪装为 PASS；
它们是 A 的明确范围外待办。完整 R07-C 后续决定仍需其自身的可裁决材料。
