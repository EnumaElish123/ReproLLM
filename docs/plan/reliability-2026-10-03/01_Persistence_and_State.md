# Sprint 1：产物保全与有效运行参数

版本：v1.2 · 日期：2026-10-03 · 状态：PLANNED

共同合同：[00_Execution_Guide.md](00_Execution_Guide.md)。审查 SHA：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

## 1. 目标与会话

本 Sprint 修复可能破坏已有 manifest、把敏感值写入 lock，以及让 diff 丢失真实参数变化的缺陷。交付可单独审阅的回归测试、实现、文档修正和五项目验证报告。

| 会话 | 按顺序执行 | 完成后交接 |
|---|---|---|
| S1-A | R00 → R01 | 当前问题矩阵、init 保全实现、Gate A、R02 / R03 输入 |
| S1-B | R02 → R02-R → R03 | lock 拒绝写入、run 安全脱敏、State 选择合同、Gate A、S2 / S3 接口说明 |

优先级：R01 / R02 / R02-R 为 P0，R03 为紧随其后的 P1。R00 只建立必要基线，不做全仓重构。R02-R 独立提交；若安全修复或审阅占满 S1-B，将尚未开始的 R03 登记到具名接续会话，保留 R04 对它的依赖，不缩减测试。

禁区：不放宽项目名 schema；不增加 unsafe 写入开关；不实现通用多文件事务框架；不扩大 diff 漂移策略；不改一致性规则“任何 observation 与声明冲突”的现有语义。

## 2. R00：建立可继续的执行基线

### 输入与动作

1. 记录实际 SHA、工作区、Python / ReproLLM 版本、依赖安装结果。HEAD 与审查不同则先检查相关提交和复测行为。
2. 运行总则 §6 的质量门。把既有失败、环境失败和新回归分开登记；不为恢复审查基线而改版本或回退代码。
3. 依据本包每项的最小场景，给 R01–R07（含 v1.2 的 R02-R、R06-G、R04-B）填写“仍复现 / 已修复 / 环境阻塞 / 需重新界定”。可以先完成 P0 的测试，再顺序补其他复核；同时登记 R05-S 的已知规范冲突。
4. 验证 `val.md` 五个 checkout 的存在、SHA、origin、干净状态；登记缺失输入及可恢复步骤。
5. 建立任务账本和会话报告骨架。把 R08 / scope 等拟改策略列为 PROPOSED，不写成已存在缺陷的默认预期。

### 验收

- [ ] 每个任务有当前代码定位和状态；已修复项附证据。
- [ ] 本轮质量基线有真实命令与退出码。
- [ ] 五项目输入清单完整，无“跳过即通过”。
- [ ] 有明确可进入 R01 的工作区和下一步；报告无需依赖审查临时目录。

建议提交：`docs(plan): record reliability execution baseline (R00)`。仅提交可分享的摘要和证据索引，不提交绝对路径、虚拟环境或外部项目副本。

## 3. R01：init 在失败时保全已有文件

### 代码入口与已确认问题

`src/reprollm/core/manifest_scaffold.py`：`plan_init` 使用 `root.name`；`write_scaffold` 先写 manifest / 辅助文件，后 `load_manifest`，失败时删除 manifest。`src/reprollm/cli/init.py` 负责 CLI，`src/reprollm/core/yaml_io.py` 提供 YAML / model 校验。

审查复现：目录名为 `实验项目`，已有合法 `reprollm.yaml`，其中项目名为 `saved-project`；使用 `--force` 生成 inference scaffold 时，非法目录名导致校验失败并退出 2，旧 manifest 随后消失。

### 实施步骤

1. 在 `tests/unit/cli/test_init.py` 增加复现，用已有合法 fixture 为起点；保存旧文件字节，而非只断言旧文件存在。
2. 分开“生成 / 校验”和“提交写入”。在任何目标写入前，对最终 YAML 文本按与 `load_manifest` 相同的规则做内存校验；不能只校验建模前的字典而漏掉 YAML 字符串类型问题。
3. 在目标同目录准备临时 manifest，再用原子 replace 提交；参考 lock writer 的现有模式。manifest 的最终替换放在必要辅助文件准备成功后。
4. 记录本次新建的辅助文件与目录；正常异常路径只清理本次新建内容。已有 `.reprollm/config.yaml` 和 `project-rules.yaml` 不覆盖、不删除。新目录只有为空且由本次创建时才清理。
5. 明确项目名处理：合法目录名保持字符串语义；本轮推荐对非法目录名使用固定 fallback `experiment`，并显示可编辑 `project.name` 的安全提示。若当前维护者已选定其他合法命名合同，按该具体决定执行并更新测试。显式 `--name` 是可单独审议的 UX 选项，不作为 P0 修复前提；不得以放宽 schema 处理。
6. 错误提示只描述安全的位置和原因，不能借底层 YAML / OS 错误回显敏感内容或机器绝对路径。

故障边界是正常异常、校验失败和替换失败下的保全；不宣称实现断电条件下跨多个文件的全局事务。已存在产物的字节与权限保全策略须在测试中明确。

### 必须建立的回归矩阵

| 用例 | 独立预期 |
|---|---|
| 中文、空格、超过 64 字符的目录名 | 按本轮命名合同生成字符串 `experiment`，显示修改提示；manifest 可 load |
| `123`、`true` 等易被 YAML 解析为非字符串的目录名 | 输出 load 后 name 仍为合法字符串 |
| 强制覆盖已有合法 manifest，生成校验失败 | 旧字节完全不变；已有辅助文件不变 |
| 无旧 manifest，生成校验失败 | 不留下半成品 manifest / 辅助文件 |
| 模拟辅助文件创建失败、临时写入失败、replace 失败 | 旧 manifest 保留；仅清理由本次创建的临时产物 |
| 正常首建和正常 `--force` | manifest 可立即 load；辅助文件语义与现有合同一致 |
| 已存在 manifest，未使用 `--force` | 原有拒绝行为；没有写入 |
| owned 输出位置或辅助目录为 symlink | 采用可说明的安全拒绝 / 受控路径策略，不写到项目外；不扩大成任意用户文件重写 |

命名矩阵是验收设计；不是宣称每个名称在审查时都已单独复现。故障用 monkeypatch 模拟，不要求改真实目录权限制造不稳定测试。

### 测试入口与完成条件

```bash
uv run pytest -q tests/unit/cli/test_init.py tests/unit/cli/test_init_selection.py
```

- [ ] 原缺陷的失败测试先出现，再因修复通过。
- [ ] 输出 YAML 与 model 的校验规则一致；没有 schema 放宽。
- [ ] 所有失败路径保全原文件；所有成功路径可 load。
- [ ] 全质量门及五项目 init → L1 audit Gate A 完成。
- [ ] CHANGELOG 解释数据保全修复和必要命名变化。

建议提交：`fix(init): preserve existing scaffold on validation failure (R01)`。

## 4. R02：lock 的持久化安全检查

### 代码入口与已确认问题

`src/reprollm/integrations/_resolution.py::resolve_inference`、`src/reprollm/lock/resolver.py` 的自由参数复制路径；`src/reprollm/lock/writer.py::build_lock / write_lock`；`src/reprollm/cli/lock.py`；`src/reprollm/run/privacy.py` 和 `src/reprollm/core/redaction.py` 的既有策略。

审查在 `backend: other` 的 `inference.params` 放入合成 API key 和绝对 cache 路径，生成 lock 成功并保留值。另以 `api_key: syntheticPlainCanaryABC` 验证：只判断 `RunPrivacy.value(obj)` 是否改变，会漏掉需要键值上下文的 secret 检测。

writer 已实现临时文件、flush / fsync、replace 和异常清理；已有 `test_atomic_write_preserves_existing_lock_when_replace_fails`。本任务复用这些能力，不再重建原子写入机制。

### 实施步骤

1. 基于 `tests/unit/lock/` 的合法最小 manifest，分别在 inference、training、privacy 等实际复制到 lock 的自由参数中插入 canary，验证当前泄漏。
2. 建立持久化对象的统一检查入口，遍历 dict 键 / 值、嵌套 list 与嵌套对象；同时使用结构化 secret-key 语义和既有值模式。不要把 `RunPrivacy.value` 当完整验证器。
3. 在任何含敏感值的临时文件落盘前，检查将被持久化的最终数据；序列化后对完整待写字节执行必要的最终检查，覆盖 provenance / notes / 自由字段的遗漏。
4. 默认拒绝不安全写入，返回 `UserError` / exit 2；旧 lock 完全保留。不得静默替换可执行参数成 `<REDACTED>` 后生成一个看似有效的 lock。
5. 对普通密钥字段，给出“移出 manifest，由被包装程序从环境或其安全机制读取”的提示；当前 YAML 不支持 `${OPENAI_API_KEY}` 插值，不教用户使用不存在的替换能力。
6. 对项目内路径，提示使用可验证的相对路径。值匹配必须保留合法 HF ID、URL、相对路径和控制 token，不能用“出现斜杠即拒绝”的规则。
7. 若确需修改 redaction 模块，补充正反例 corpus、100% 分支覆盖与 D-41 审阅材料；修改范围只覆盖明确支持的检测合同。

只检查将持久化的值。例如原始 prompt 若仅参与哈希，不因其正文含 secret-shaped 文本而拒绝安全的哈希产物；若正文会进入 notes / snapshot，则按实际持久化规则处理。不要宣称检测任意未知密钥格式。

### 必须建立的回归矩阵

| 输入 / 场景 | 独立预期 |
|---|---|
| `api_key: syntheticPlainCanaryABC` | 即使值不匹配服务商前缀，仍因键值语义拒绝 |
| `sk-proj-ReprollmReviewCanary0000000000`、JWT 等 corpus 值 | 按现有受支持模式拒绝，输出不回显 canary |
| `/home/review-user/private-cache`、Windows 绝对路径、用户名 / 主机名测试模式 | 按持久化隐私合同拒绝或安全转换；不得泄漏原始值 |
| dict key、list 内对象、provenance notes 含 canary | 同一安全入口覆盖；不只检查顶层 params |
| 合法模型 ID、HTTPS URL、`cache/models`、glob、`</s>`、`max_tokens` | 正常写入，不能把普通标识误判为路径或秘密 |
| 安全 prompt 只存哈希，正文含用于研究的 secret-shaped 文本 | 不因未持久化正文误报 |
| 不安全输入 + 已有 lock | exit 2；旧 lock 字节不变；无含 canary 的临时文件或日志 |
| 安全输入 + replace 异常 | 保持既有原子写入测试通过 |

检测不得扫描真实用户目录寻找密钥。所有断言都基于合成输入，涵盖 stdout、stderr、错误文本、最终文件和本次临时文件。

### 测试入口与完成条件

```bash
uv run pytest -q tests/unit/lock/test_writer.py tests/unit/lock/test_resolver.py tests/unit/cli/test_lock.py
uv run pytest -q tests/unit/run/test_privacy.py tests/unit/run/test_privacy_fidelity.py
uv run pytest -q -m security
```

- [ ] 结构化键值检测与最终写入边界都有失败回归和负例。
- [ ] 原子 writer 保留；安全产物的语义未被静默删改。
- [ ] 清楚说明这是新写入保护；不声称旧 lock 已自动清理。
- [ ] 不悄悄扩展 `lock --check` 的 freshness 合同；如需旧产物扫描另建明确任务。
- [ ] 全质量门、适用五项目 Gate A 及必要的 D-41 审阅完成。

建议提交：`fix(lock): reject unsafe persisted values before writing (R02)`。

## 4.1 R02-R：run 结构化值与文本快照的密钥脱敏

### 当前证据与范围

补充审查 SHA：`781366e89362a54d9036d3aed070fad169ba8204`。真实 stdlib 包装运行读取 `config.json` 的 `settings` 对象，经 `custom.settings` 的 config binding 捕获。对象内的合成值 `{"api_key": "syntheticPlainCanaryABC123"}` 同时原样进入 `run.json` 和 `files/` 配置快照。只为 lock 增加检查不能修复这两条路径。

入口：`core/bindings.py::_safe_value`、`run/privacy.py::RunPrivacy.value / text`、`run/wrapper.py::_write_record / _snapshot_document`、`run/capture.py::hash_and_snapshot`；对照 `export/exporter.py::_redact_keyed_values` 已保留键上下文的做法。结构化键和值目前分别处理，普通值缺少密钥前缀时无法单独识别；JSON 带引号的键也不匹配当前 generic_kv 文本模式。

### 实施与安全边界

1. 先建立真正经过 `execute` 的失败回归：manifest 绑定 `custom.settings` 到 `config.json:settings`，stdlib child 读取配置；检查整个 run 目录，不只调用脱敏 helper。
2. 对嵌套 mapping、list 内对象及绑定标量保留可验证的键 / 字段上下文，复用现有受支持的秘密分类。对原始 JSON/YAML 等文本快照覆盖带引号的键，不靠在序列化后搜索几个已知 canary 值。
3. 在临时及最终产物落盘之前完成脱敏；范围包括 `run.json`、manifest/lock 快照、声明文件快照、patch 和保存的 stdout/stderr。既有 child 原始终端输出合同保持；ReproLLM 自身诊断不得回显秘密。
4. R02 的 lock 默认拒绝不安全参数，R02-R 的 run 保存安全脱敏的观察。不能将 lock 的拒绝策略直接移到 child 已完成后的路径，造成退出码变化或丢失运行记录。脱敏失败时保留安全最小记录及捕获失败说明，不回退到保存原文。
5. 原始文件哈希、脱敏后快照和 `redacted` 标记按现有合同区分；不将替换后的参数宣称为原始可执行配置。旧产物不自动改写；文档明确新写入保护的边界。
6. 若调整 generic_kv 的规范模式，先准备 §16.2 的具体补充、正反例和影响范围。触及 `core/redaction.py` 时遵循 D-41：补 corpus、保持 100% 分支覆盖并取得明确代码审阅。此次计划修订不代替该审阅。

### 必须建立的验收矩阵

| 场景 | 独立预期 |
|---|---|
| 普通合成 `api_key`，没有服务商前缀 | run.json 与配置快照均无原值；记录安全替代及脱敏事实 |
| JSON 双引号键、YAML 普通/带引号键、嵌套对象、list 内对象 | 键上下文保留，所有持久化副本均受保护 |
| 被绑定的叶子自身是秘密字段 | 不因离开父对象而丢失秘密上下文；不回显原值 |
| `max_tokens`、`TOKENIZERS_PARALLELISM`、模型 ID、相对路径、glob、`</s>` | 保留实验值，不扩大成所有含 token/key 字样的值都删除 |
| snapshot 开/关、capture-output 开/关 | 相应产物检查一致；关闭某条路径不能掩盖其他路径泄漏 |
| child exit 7、捕获/脱敏故障、原子替换失败 | 遵守已完成 child 退出码合同；没有含秘密的临时或最终文件 |
| 两个不同的秘密值与已有 diff/export 消费路径 | 安全处理及无法比较的边界明确，不虚称已恢复被脱敏值的差异 |

定向入口：`tests/unit/run/test_wrapper.py`、`test_privacy.py`、`test_privacy_fidelity.py`、`tests/unit/core/test_bindings.py` 及 security corpus。

- [ ] 真正包装运行、快照字节和整个 run 目录的正反例通过。
- [ ] 不改变正常实验值、哈希语义和子进程退出码。
- [ ] 全质量门、五项目受影响的无资源 run/diff/export Gate A、必要规范决定和 D-41 审阅完成。
- [ ] R02 与 R02-R 分别记录结果；不得用 lock 测试代替 run 安全验收。

建议提交：`fix(run): redact keyed secrets before persisting captures (R02-R)`。

## 5. R03：repeated CLI 的 last-wins 与 State 合并

### 代码入口与已确认问题

`src/reprollm/core/bindings.py::observe` 已保留 argv 顺序；`src/reprollm/diff/state.py::observed_state / _choose / _evidence / merge` 按 rank、detail 和序列化 value 排序后取首值。之后 merge 会展开 alternatives 再排序，可能再次覆盖第一轮的修复。

审查以 argparse 包装运行：A 为 `--temperature 0.1 --temperature 0.9`，实际打印 0.9；B 反序，实际打印 0.1。bindings_observed 顺序正确，但两侧 effective State 都选 0.1，diff 丢失 temperature 变化，HIGH gate 返回 0。规格 §15.1 已要求同 CLI 参数 last-wins。

### 实施步骤

1. 先以 stdlib argparse 程序建立两个真正包装运行的测试；用 child 输出作为独立有效值依据。不要只拼两个 State 再测试排序。
2. 在最早可确定 argv 顺序的位置选出有效 CLI observation；保留全部观察与出处。维持 CLI > config > env > lock > manifest 的既有优先级。
3. 规定同来源证据的“已选择值 + alternatives”如何在再次 merge 中保持语义。新增选择不应被 `_evidence` 展开和排序冲掉。
4. 同一字段的不同 CLI alias 若均能映射，按照实际 argv 出现顺序处理；config / env 多来源冲突维持各自既定合同，不一律倒序。
5. 对旧 v1 run，利用已有有序 observations 恢复；优先不增加 ordinal 持久化字段。若不可避免，提交有界兼容方案，不静默改 schema。
6. 核查 CLI diff、audit 的 State 构建、export 是否使用一致的 effective value；只做本任务必要调整。

### 必须成立的不变量

| 用例 | 独立预期 |
|---|---|
| A：0.1 后 0.9；B：0.9 后 0.1 | effective 分别为 0.9、0.1；temperature 语义差异存在 |
| 单值、相同值重复、重复数值字符串 | 与包装程序的实际解析一致；重复证据保留 |
| CLI 与 config / env 同时存在 | CLI 胜出；其他证据仍可追踪 |
| `from_run` → 再 merge 一次、两次 | effective 值、来源及必要证据不被重排改变 |
| State 序列化 → 重新加载 → merge | 选择仍相同；证据不会无界重复膨胀 |
| 旧 v1 run fixture | 能读；按照已记录的 CLI 次序选值 |
| 相同输入重复执行 / self-diff | 输出确定；self-diff 不产生无关变化 |
| manifest 为 0.9，而 CLI 为 0.1 后 0.9 | effective 为 0.9；现行 consistency 仍可因早先冲突 observation 报告问题 |

最后一行保护现有一致性规则：本任务纠正实际生效值，不把“任一 observation 是否与声明冲突”偷换成“仅最终值是否冲突”。有意更改该策略必须另提方案。

### 测试入口与完成条件

```bash
uv run pytest -q tests/unit/core/test_bindings.py tests/unit/diff/test_state.py
uv run pytest -q tests/unit/cli/test_diff.py tests/unit/rules/test_runtime_consistency.py
```

- [ ] 两个真实包装运行 + 独立 child 输出的复现通过。
- [ ] merge / round-trip 不变量全部通过；证据仍完整。
- [ ] 确定性的定义保留 argv 顺序，不要求不同语义顺序得到相同结果。
- [ ] 不改变默认 drift 等级 / fail-on；相关 diff gate 按现有 generation 策略出现正确结果。
- [ ] 全质量门、适用五项目 Gate A、CHANGELOG 与消费端说明完成。

建议提交：`fix(state): preserve CLI last-wins across merges (R03)`。

## 6. Sprint 收尾

- [ ] S1-A 和 S1-B 各有自己的五项目 Gate A 报告；不能用第二次报告替代第一次。
- [ ] R01 / R02 的失败保全有文件字节证据；R02-R 有整个 run 目录的脱敏证据；R03 的有效值有真实 child 证据。
- [ ] 把安全检查复用点交给后续 recipe / 证据包工作；把 State 选择合同交给 R04-A。
- [ ] 尚未获得必要审阅的部分标记 REVIEW_READY；其余任务照常推进。

源码依据：[manifest_scaffold.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/core/manifest_scaffold.py)、[lock/writer.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/lock/writer.py)、[diff/state.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/diff/state.py)。
