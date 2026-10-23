# D-M-P：独立设计审阅

日期：2026-10-23；基线 `cc6e891c07aea9c8d585e80e2a14eff3b98b32af`。
状态：**PASS_FOR_P_A_DESIGN_REVIEW / NOT_POLICY_APPROVAL / NOT_IMPLEMENTED**。
最终审阅未发现尚未解决的设计阻断；这不代表维护者已接受 A、未来测试通过或产品门通过。
`decision.json` 仍为 `PROPOSED`、`accepted=false`。

## 审阅对象与实际检查

对照主方案、精确规范补丁、决定、38 项未来验收、兼容表、当前观察和五项目来源，
直接阅读现有 `core/deps.py`、`rules/env.py`、`cli/scan_diagnostics.py`、`export/exporter.py` 及规范相关章节。
本审阅未执行候选政策、修改产品/测试/现行规范，也未自行重放原产品观察；仅回读两次观察原件。
本审阅代理此前编制五项目来源；本页对其他代理编制的政策设计和验收边界作独立核对，
不将来源编制与本次设计审阅合称第三方产品验收。

- 最终 `git apply --check spec-proposed.patch` exit 0；补丁只指向 `docs/plan/01_specification.md`，
  `--numstat` 为 81 行新增、13 行删除，主要为新增 §12.3.9 及明确交叉引用。
  `--check` 没有应用补丁，现行规范 hash 仍为 `2eaf4f7f0f1fc9f3cbb53cf64ca320c52636fbec03227feb709d24b6110c01d5`。
- `delivery-baseline.json` 的 **521 个受保护文件全部原字节不变**，包括产品、测试、规范、
  schemas、依赖、examples、gold/验证输入边界；未借 P-A 改变现行政策。
- 决定记录的 patch hash 与最终文件相同；没有沿用此前 D-G/D-C 的批准推定本片已接受。
- 38 个未来 ID 恰为 P01–P38，连续且唯一。当前观察的 P01–P24 属另一个命名空间，
  不映射为未来验收同号条目已经通过，更不作为 38 个新测试的执行记录。

## 设计与真实控制流一致性

| 核查点 | 结论 |
|---|---|
| 新事实边界 | 只限成功 TOML 解码后，原 `project.dependencies` list 和 optional mapping 的 list 内实际到达既有 helper 的 str；不额外遍历错误结构或新字段 |
| 失败含义 | 现 helper 使用已有 broad `Exception` 捕获；设计准确写成该次既有 Requirement 调用的已捕获失败，不替换为另一种标准校验或全部 grammar 无效判断 |
| 空白成本 | 原代码确实把空/空白 PEP 621 str 原样送入 helper；将这些失败也纳入，并可能影响无关项目，是已明确展示、仍待具体接受的全仓保守成本 |
| 单文件原因保护 | D-M-S 在现有提取之前记录结构原因；拟议记录须有等价 `setdefault` 的保护，保留 unreadable/invalid_syntax/invalid_structure，不用低优先级原因覆盖它们 |
| 共享 helper | requirements 图和 embedded pip 也调用同一 helper；本片要求显式 PEP 621 context/result，仅两入口选择新事实。不是改变共享默认行为，也不从 unparsed 文本反推事实 |
| 原始提取副作用 | 成功声明、顺序、specifier/exact、原诊断、物理路径/行、读取次数/预算、manifest 资格、项目根、barrier、lock 集合及关联均应保持；失败 str 本身不成为声明 |
| 规则实际顺序 | 现 `env.py` 先 qualified credit、再 exact credit，之后 D-F/D-S、D-L、非空 declaration_read_issues、D-G、原 WARNING；两种正信用都先于任何保守分支 |
| D-M 复用 | 现代码只检查失败字典是否非空，保留首条 declaration/import use evidence，再按源路径排序附文件证据；新原因无须新增 finding 分支、文案、公开字段或 rule ID |
| 部分正面信用 | 同文件/异组/异项目 exact 和合格 lock 继续有效；失败不得撤销信用。有效 pyproject 项目根及配对仍存在，不因单个 str 失败新增 uncertain barrier |
| 未知 use 和空结果 | 不从坏片段猜名称；无已知关键包仍沿 applicability；全部包获信用时保留 Python empty-result veto，原 check 空列表不等于已执行 CLI PASS |
| 用户可见成本 | 隔离门可 exit 1→0；独立 qualifying finding 不被压制。既有 FAIL-only override、suppression、完整 JSON、默认 text skipped 计数及 export notable 合同保持 |

该设计不增加 LLM、网络、依赖、scanner/engine/redaction/schema 改动或用户文件写入，
未见与冻结 D-04、D-19、D-30、D-41 冲突。若 P-B 实际需要超出最小范围，仍须另行具体审阅；
本页不能批准一份尚未编写的扩大实现。

## 边界、验收与证据解释

D-C 的 ordinary requirements 注释回退仍仅在图内；PEP 621 失败字符串不能借本片剥注释、
重新解析、修复或新增 use。Poetry/Pipfile 值、environment.pip、Conda、setup.py/setup.cfg、
dynamic/build/groups、遗漏候选、listing/framework 和充分证书均未被纳入。
既有成功的 URL、marker、extras、任意相等、范围、通配符和 unversioned 解析不被重新判错，
exact 的旧合同独立保留。

P01–P17 覆盖原入口、空白、类型隔离、部分提取、既有原因和读边界；P18–P28 覆盖逐包信用、
高优先级原因、全仓成本、no-use 和 Python veto；P29–P35 将隔离退出码、独立 warning、
suppression、展示、init/export 和历史记录分开；P36–P38 要求来源核验、新鲜五项目与最终门。
它们是未来设计，参数化数量和真正 RED/GREEN 必须等 P-B 实测，不能从 38 条映射推导测试数。

最终 cases/observer SHA 与第二次执行前冻结及其观察记录一致；24 组输入 SHA 均可回核，
两次当前观察各 24/24，公开第二次结果中 24 个 `expected_projection_passed` 均为 true、mismatch 列表均为空。
只把预先列出的投影当当前行为断言；Git listing、安装版本采集、CLI/engine/profile/init/export
未被这次观察验证。未重放观察、未执行未来 `unparsed_requirement` 路径。

五项目的 163 个 scoped string 全部独立解析成功，来源位置/值/token hash 已回读核对。
98+31+34+0+0 与兼容表及 P36 一致；五 pins 不包含新坏分支，因此完整输出零差异只是
**PREDICTED_NOT_EXECUTED**，不能替代 synthetic 或标为 Gate A PASS。
HarmBench 的 45→47 及原诊断/closure 变化属于已交付 D-C 基线，本片不重复计算。
初始化文件按原始字节比较；T-02 只在其明确允许的报告 metadata 上豁免，不泛化到 YAML 文件。

## 审阅中已澄清的表述

最终补丁已补齐 D-L、D-F/D-S 和 D-G 对 §12.3.9 的前向引用；它仍复用 D-M，
没有增加一个排在 D-G 后的新规则分支。D-M-S 的“not validated here”是该局部结构表的边界，
无需借本片将其改写为包值 grammar 检查。

P32 已明确保留旧可见性：普通 dependency unparsed 诊断只在 `-v` 显示，
默认显示的固定 Python coverage/run warning 特例不扩展。本轮没有修改 renderer。
最终补丁对照 `exporter.py:406–409` 澄清：默认 export 继续只列 WARNING/CRITICAL notable findings；
旧 warning 转为 SKIP/INFO 后不再列出，不删除任何无关 notable finding。
这些澄清已经进入最终审阅 hash。下述证据元数据缺陷及新冻结另行明确记录，
不能沿用“始终只有一次执行、公开 cases/observer 从未修订”的旧表述。

### D-39 证据元数据缺陷与关闭依据

审阅发现首次 cases/current-observations/replay 的 `schema_version` 为字符串 `"1"`，
replay 的嵌套 freeze 也有该类型。冻结架构 D-39（第 236 行）明确要求整数，规范 §0
（第 16 行）另要求整数版号和 producer version；AGENTS 的简写不能用作类型例外。
这是证据辅助元数据缺陷，不是 24 组当前行为失败，也不是新增候选政策。

采用的修复保留全部首次原件、冻结与命令收据，不静默转换其已记录输出。
公开 cases 只修正版号并补 producer version；observer 的精确 diff 仅将输出版号改为整数，
并从 cases 读取 `reprollm_version`。产品调用代码、每组真实文件和独立预期完全不变。
`2026-10-23T03:13:39.662737+00:00` 新冻结先于 attempt-02 开始，再运行一次原产品观察。
两次均 24/24、exit 0，不合计成 48 个不同验收，也不声称首次之前没有技术探索。

本审阅独立回读并确认：

- 5 份首次归档文稿/原件、replay 列出的全部私有原件 SHA 和 4 份新公开文件 SHA 均相符。
- 第二次公开 raw 与 `observation-attempt-02/raw-observations.json` **逐字节相同**，
  没有输出归一化；其 observer/命令 elapsed 分别为 0.238529/0.434740 秒。
- 两版 cases 除版本元数据外完全相同；两次 raw 除账本明确列出的 6 项顶层执行/版本/hash
  元数据外，全部业务字段完全相同，包含完整 findings、输入、诊断、读取和源 hash。
- 当前全部公开 JSON 的版号（含嵌套 freeze/command）均严格为整数 1，producer version 为 0.7.0；
  521 个受保护产品/测试/规范等文件仍原字节不变。

详见 [metadata-repair.json](metadata-repair.json)。首次缺陷、两次路径隐私检查误报、
首次三项发布检查及其后 D-39 重核分别保留，未通过声明格式例外绕过冻结决定。
该问题已关闭，不需重写历史产品记录，也不构成 D-M-P 政策接受。

资源结果继续绑定各自候选：VAL-R01 为 `948d164`、VAL-R02 为 `75d1b0` 的历史结果；
VAL-R03 的原 metadata/HF403、A02 独立反馈、A03 申请信息/授权仍独立待解。
本 P-A 的完整产品门、fresh Gate A 和资源 Gate B 为 NOT_APPLICABLE，不是 PASS；
没有 GPU、付费 API、外部提交或版本发布。最终推送 HEAD CI 也仍由交付时单独核验。

## 已核 SHA-256

以下为本次最终审阅输入；后续实质变更须重新审阅相应部分。

| 文件 | SHA-256 |
|---|---|
| R07-C_pep621_strings.md | `7f907ccb171beee302d667d5419b9862d38eaa7d46328626c532f66439c10bf6` |
| spec-proposed.patch | `89505a8e74cd84ad3589e0a95cc8749f671446443110fb2a35e6f4745bc6ce9f` |
| decision.json | `144dc6ae76b9f01dcc7c6ab2dec2103ad243fbf0897ee88d6a05dfadbf0916a3` |
| acceptance-cases.md | `9ef975d3c482e3f65a794726ca720ada8806cfc8102f5a9b81911c563c97b4ac` |
| compatibility.md | `1f1fcf144ce632c7b79b6630aec375a63c9cd93361260e7e8b6488d19ed2ca1b` |
| portfolio-impact.md | `c1f97c6bfcd6dbbe0bce223210e68048b87896eb8c9333a8bde10de191d37d90` |
| portfolio-source-evidence.json | `58be193e7de548eff44a3a86f0da8f14d34284765e70ac6c4cd9cf1a6b203a66` |
| current-behavior.md | `ceac22e87830f92e133a24aa6c7b3e94633a7dbc62be7f97be749b4bb6a02747` |
| cases.json | `439193e8b549e3ab8b90f00fbe263a57c62828b9a02285a12a9537010c958e13` |
| current-observer.py.txt | `d6508146a983493e04a1da145d3144a2216df13b07d46a0344aec2bf8874f630` |
| current-observations.json | `7c0f0c69741ea91231eddd981639901d8e5e19e09bf4dedfbc4bd026cf7907ae` |
| observation-replay.json | `ae841ecccbc579846cf626a5aa1a6f403340345a60a5a84e5c4d678a1a832ffa` |
| metadata-repair.json | `ca5cbf8a20b514a44a559afac5c2ac673d2595e5a5f272e76e8a4d97a4cc07d6` |
| README.md | `29d72b39854426883279df12cc15b0363bc978c73598eea4ee4aab6de53fb733` |
| delivery-baseline.json | `6b935a4e27833e66c1b68076d4d1f900cba704c4883f9d4059535a0311857003` |
| src/reprollm/core/deps.py | `4f6593b18c1fd24f672aa32e8b985ed9f3082c4e22530ea9d46be1f28f76d45d` |
| src/reprollm/rules/env.py | `14212913b79f3d53862173e4e316fa3d0177a8609354208de9a6b3834c97d995` |
| src/reprollm/cli/scan_diagnostics.py | `ddc6785fe2007fd219e4d1f9380ef4637053c12e83268678c96bbc08754cb0f1` |
| src/reprollm/export/exporter.py | `06d81f00ccaada06aa64579e7471fa53950057114c1ed0707a2cbacac24fcbdf` |
