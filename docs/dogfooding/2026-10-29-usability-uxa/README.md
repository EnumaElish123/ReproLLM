# UX-A：首次保存命令、直接运行与下一步报告

日期：2026-10-29。基线 `0a28406`；最终产品与测试候选 `ce24ebbceebd423082ee921fcd1801d1b66ee5eb`。
本轮三个任务的实现、完整本地质量门与五项目验收均通过。最终交付提交的五项 CI 在本报告提交、推送后单独核验；本报告保留推送前快照，不以本地 Linux 结果替代跨平台结果。

## 范围与提交

依据维护者的易用性改进请求及[执行方案](../../plan/usability-2026-10-29/README.md)，先交付 UX-A。

| 任务 | 提交 | 行为 |
|---|---|---|
| 计划 | `6992934` | 确定 UX-A/UX-B 范围、验收与禁区 |
| UXR01 | `d26f00a` | `init --command STRING` 写入前验证，精确保存一次实验命令 |
| UXR02 | `49e3566` | 无显式 argv 的 `run`/`run --dry-run` 读取保存命令；显式 argv 优先 |
| UXR03 | `2175d06` | 文本审计先列最多三项下一步，保留完整发现及跳过说明 |
| UXR01 边界修复 | `d9270fd` | 隐私检查达到解析限制时返回私密的输入错误 |
| UXR02 边界修复 | `ce24ebb` | 非法保存 cwd 在运行与预览中返回输入错误，不创建产物 |

首次配置示例（把示例替换为项目已有的实验命令）：
~~~console
reprollm init --command "python eval.py --config configs/eval.yaml"
reprollm audit .
reprollm run --dry-run
reprollm run
~~~
保存命令不会启动实验；研究字段的缺口仍须由用户补充。后续运行不必重复输入整串实验参数。

## 行为与兼容边界

- 未给 `--command` 时，默认 manifest 字节、原交互提示顺序及旧自定义 profile 的 command 渲染保持。
  新选项保存准确字符串，拒绝无效语法、秘密及机器路径/身份；失败保持既有文件字节和模式。
- 保存串采用跨平台一致的有限 POSIX 引用语法，保留空格、空参数与引用字面量，不隐式执行 shell 运算符或展开。
  复杂流程使用用户自己的脚本。默认从 manifest 根及 `execution.cwd` 运行，显式 `--cwd` 覆盖；嵌套项目归属不能悄悄切换。
  显式 `run -- CMD...` 的既有行为、输出捕获默认值、child 退出码、run v2 和隐私规则保持。
- 新文本按 CRITICAL → 缺 manifest 初始化 → WARNING → INFO 排序、分组。SKIPPED 带覆盖缺口说明；依赖锁提示与 `reprollm.lock` 区分。
  JSON/GitHub、规则结果、severity、fail-on、持久化 schema、扫描覆盖合同和完整详细发现保持。

规范 §3.2、§5.2/§5.2.1、§21、生成 CLI 参考及 CHANGELOG 同步。未修改 engine、redaction.py、依赖或版本；没有 release/PyPI 发布。

## 开发与定向验证

首批 118 个新增参数化案例：UXR01 36、UXR02 63、UXR03 19；交付复核另补 6 个边界案例，本轮合计 124 个新增案例。
UXR01 的有效实施前 RED 为 7F/28P，两个最终定向集合为 120P 和 55P，去重后 139 项；
UXR02 为 47F/4P，另有展开及格式字符两组 2F→GREEN，最终相关回归 509P；
UXR03 为 17F/2P，原定向回归 149P。不同集合有交集，不能相加作为独立测试总数。
三项代码经过交叉只读复核；后续独立交付复核及修复见下文。最终受影响 lint、格式与类型检查通过。

早期测试素材/解释器选择及预览文件存在性期望的修正保留原记录，见 source-index 中任务收据。
六份 `audit_L0.txt` fixture 仅加入 Next steps，旧内容逐字节保留；没有更新 JSON gold。
首轮完整门在 `a5b6c52` 得到 5365P/48F：六份历史 CLI 精确文本矩阵遗漏了新块。
仅补充七处字面预期，保留原完整文本、stderr、JSON 和退出码断言；移除这些新增字面块后测试 AST 与原件一致，独立复核通过。
这组六文件与新 reporter 回归共 243P。当时只变更测试预期，产品源码、schema、配置、工具及依赖不变；第二轮 `2175d06` 完整门和五项目验收通过。
独立交付复核随后发现两处 P2：深层引用 JSON 参数触发隐私解析限制，以及 manifest 的 cwd 含 NUL，均可能误报内部 exit 3。
6 个真实 CLI 案例在修复前全部失败；局部调用边界修复后 105 项相关回归通过，检查 exit 2、私密提示、无新产物及 --force 保全。
独立复核确认两项已关闭；没有改 redaction.py、schema 或既有显式 argv 行为。
当前 `ce24ebb` 重新执行完整质量门及全部五项目，早期失败和第二轮成功原件保留且不代替当前验收。

## 最终完整质量门

24 项检查及 24 次来源守卫通过，受跟踪输入前后字节一致。
**5419 passed、0 failed/error/skipped；普通门另排除 2 个 slow。总覆盖率 94.7627541919372%，redaction 语句与分支 100%。**
含 security、ruff/format/mypy、10 份 schema 字节比较、生成文档、示例、自审计、wheel 全载荷和隔离安装。
命令累计 1143.1775 秒，质量层墙钟 1149.615778 秒；两者不相加。
独立环境实际完成 `uv sync --locked --dev --offline`，安装 41 包；通用旧 runner 的 `environment_synced=false` 仅为继承元数据，本轮版本/导入源守卫另证实际环境。
Git 2.25.1 使用已复核兼容包装器，SHA-256 `87a9309323f9e82d8721b7bd58cac0c1a8f08e44a4348fbf6d476854aa19b298`；quickstart freshness 先于全量 pytest 通过。

## 五项目：预期与实际

普通产品会话适用 Gate A 基础层及受影响扩展。预期在执行前固定：旧 JSON/manifest/export 保持；新文本只插入引导；新命令流程对照明确的标准库 probe 参数与结果。
全部 pinned checkout 的 SHA、origin、tracked/untracked 干净状态在前后核对；写操作仅发生在一次性副本。

| 项目 | 固定 SHA |
|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` |

| 层 | 命令记录 / 检查 | 完整验收 |
|---|---|---|
| 基础 | 50 / 31 | fresh L0、完整 facts/hints/路径/诊断，10 份完整 JSON 比较 |
| 受影响 | 130 / 111 | graph、verbose、init→L1、默认 export，15 份完整 JSON、15 份 init 文件、5 份完整 export |
| 新 UX | 75 / 56 | 五项目旧/新文本完整对照，保存→预览→实际 child→run v2 回读 |

合计 **255 条外层命令记录、198 项检查、25 份完整 JSON 比较**；JSON 中只有规范允许的根时间/版本字段豁免。
文本两端一致采用 `--fail-on never`，否则 LlamaFactory 已有 CRITICAL 的 exit 1 不能当作异常；移除新增引导块后，全部旧文本和 stderr 逐字节一致。
五份新 manifest 保存串准确；child 收到带空格值、空参数、字面分号值；工作目录为项目根，每个副本只有一个 completed/exit 0 的 run v2。
预览比较证明非 Git 文件字节集合不变、没有输出/run 产物，且不回显原 argv；零子进程/网络/写入另外由定向测试验证，不把文件字节比较夸大为完整副作用证明。
三层墙钟分别 85.735189、224.41332、179.721582 秒；无未解释 gold 差异。

继承的 57 份 oracle 以原来源与逐文件哈希复用，没有用候选输出生成新预期。旧 oracle 记录中的 `3157ae7` 是历史来源；本轮执行另绑定 `ce24ebb`、完整输入清单和最终质量收据。

## 完成边界与下一批

GPU 计算、真实 Hub 解析、付费 judge/discover：**NOT_APPLICABLE**，本轮是普通 UX 迭代，不完成旧 M1–M8 里程碑或准备 release。
标准库 child 的成功不代表研究实验、模型或论文结论已获验证，也不回填历史资源验收。
原主工作区三项 WIP 与未提交的手动试用素材保持，未纳入本轮提交。

UX-B 的 UXR04（字段说明、类型错误原位重试、剩余项计数）和 UXR05（单项目短教程及真实首次使用观察）仍为 PLANNED。
本轮不把作者自测登记为外部用户采用。最终 main 提交及五项 CI 在报告推送后确认。

[session-checks.json](session-checks.json)记录安全摘要；[source-index.json](source-index.json)记录选定原件的相对位置、字节数和哈希。
原始命令、退出码、耗时、完整比较与输出流保留在本次会话证据中；哈希不能恢复未公开正文。
