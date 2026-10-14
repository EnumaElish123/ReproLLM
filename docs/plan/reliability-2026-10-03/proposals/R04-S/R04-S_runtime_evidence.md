# R04-S：S3-B 环境来源与输入基线的具体决定

日期：2026-10-14。状态：**APPROVED / IN_PROGRESS**。维护者于 2026-10-14 明确接受「具体修订与 schema patch，执行完整 S3-B」；保留原提案、实测与 patch 作为审阅依据。
基准：`52ecc504b3795c46220f68ef24728e0666638df0`。
执行范围：[S3-B：R04-A → R04-B](../../03_Scan_and_Runtime_Evidence.md#4-r04-a运行环境的来源和采集时点)。

## 需要决定的内容

建议接受以下一组具体修订，随后完成完整 S3-B：

1. R04-A 的环境主体/时点使用集中定义、经源码确认的 producer 合同解释。
   Python/packages 是 recorder 在 child 结束后采集的事实，OS/platform/hardware
   是采集时可见的 host，env/scheduler 是启动前的继承基线。
   lock.environment 是 lock recorder 在解析时的事实。未确认 producer 保持 unknown；
   即使命令使用相同解释器也不宣称 child 环境已验证。环境不新增持久化 run 字段。
2. 已确认的 recorder package 比较保留现有严重度：不匹配 WARNING，单侧缺项 INFO；
   匹配 PASS 明确限定为两份 recorder 元数据，并说明 child 未验证。
   已知可比较时点是 run 的 post_child 与 lock 的 lock_resolution，不能要求字面相同。
   来源/时点未知或不兼容则 SKIP；空 recorder packages 不代表 child 无包。
   不推断两次 recorder 实际使用同一 venv。
3. R04-B 将 manifest、lock、声明输入及启动前已存在的 argv 文件作为启动前基线，
   原有引用/哈希/快照/config bindings 全部与这一阶段一致；结束后复查固定候选。
   声明文件可以记录 missing→present 的 created；启动前不构成文件事实的普通 argv
   文本不因 child 结束后恰好出现同名文件而被重新解释成输入。输出仍在结束后采集。
   开始/结束都未改变只证明记录到的字节未变，消费状态始终 unverified。
4. 仅 run 产物新增 schema 2 的必需 `input_capture`。现有 manifest/lock 及其他
   外部 schema 仍为 1。新增 State `Leaf.context` 是内部 typed provenance，
   不新增 semantic drift leaf、不改变 severity、规则 ID、fail-on 或 R03 的 last-wins。
5. 两阶段版本：R04-A 提供 0.6.2 读取桥，仍只读写 run v1，统一明确拒绝更新版本；
   R04-B 在 0.7.0 引入 run v2，新读者支持 v1/v2、拒绝 future v3。
   冻存本地 0.6.2 制品，实际验证新产物→旧受支持读者的升级提示。
   本方案不创建 release/tag 或发布 PyPI。已发布 0.6.1 的实际限制如实记录。
6. config binding 解析上限明确为原始 UTF-8 字节 2 MiB，与 preflight 检查界限一致；
   不受 `--no-snapshot` 或 1 MiB 文件副本界限影响。超限不观察值，但仍流式计算可读文件
   的完整 hash。超过 200 文件仍保留全部 hashes，仅关闭文件副本。

## 可审阅的具体差异

- [规范 §§0、4、5、12、15–19、23 patch](spec-5-12-15-17-18-19-proposed.patch)。
- [run schema 定义 patch](run-schema-proposed.patch)：一个新顶层对象及三个小模型。
- [State context 定义 patch](state-context-proposed.patch)：三个闭合枚举字段和一个可选 context。
- [已执行案例的实际旧 run](input-before-actual.json)。
- [同一案例的新格式预期](input-after-proposed.json)：**提案示例，不是产品已写出的产物**。
- [实际失败回归依据](red-evidence.json)。
- [环境合同与来源证据](environment-source.md)。
- [旧读者实测与兼容步骤](compatibility.md)。
- [验收与五项目矩阵](validation-plan.md)。
- [提案模型的十项实测检查](proposal-model-check.json)：验证实际旧样例、新格式预期、
  非法版本/字段/指纹拒绝及 typed context 往返；这是提案检查，不是产品通过。
- [新 run JSON Schema 预期](run-record-schema-proposed.json)。

新输入结构示例：

```json
{
  "schema_version": 2,
  "input_capture": {
    "baseline_phase": "pre_child",
    "check_phase": "post_child",
    "consumption": "unverified",
    "checks": [{
      "path": "config.json",
      "origin": "declared",
      "before": {"availability": "present", "sha256": "sha256:<原始0.1字节的hash>", "size_bytes": 21},
      "after": {"availability": "present", "sha256": "sha256:<改写0.9字节的hash>", "size_bytes": 21},
      "change": "changed"
    }]
  }
}
```

`availability`：present / missing / unavailable；missing 表示确认不存在，
unavailable 表示未检查成功、不可读或路径不安全。
present 必须有完整原始字节 hash 与 size；另两种不能携带伪造 hash。
`change`：unchanged / changed / removed / created / unknown。
任一阶段 unavailable 必须 unknown；其他状态依据可用性和完整指纹确定。
不保存新的解释器绝对路径或机器身份。checks 按相对 path 排序，去重后保存。

`Leaf.context`：subject 是 recorder / host / inherited_environment / input_file / unknown；
phase 是 pre_child / post_child / lock_resolution / unknown；verification 仅 unverified。
输入基线与 post 状态留在各自证据中，不能让 post 的 0.9 覆盖 config 基线的 0.1。
context 经过 State JSON 往返和 merge 保留；binding location 仍使用原 detail。
未知或缺失 context 不能升级为验证事实，不通过分析 warnings 的自然语言恢复语义。

## 实際 before / after 行为

真实 stdlib child 读取 config 中的 0.1，写独立 consumed.json，再把 config 改为 0.9。
child exit 0，独立 witness 为 0.1，当前 binding 为 0.9；公开回归在该值断言处失败。
拟议行为保存 pre-child binding/snapshot/hash 的 0.1，另存 changed 及 after hash。
State 和四个 export 模板展示基线 0.1 与变化事实，仍说明产品未验证消费。

独立 child venv 只创建 torch-0.0.123.dist-info、没有实际 torch 模块，metadata 返回
0.0.123；recorder 包集合为空。拟议报告保留 recorder 空集合及来源，在 context/文本
中说明 child packages 未验证。不会运行未知解释器探针或安装重依赖。

旧 v1 config 的值保留原记录，phase 为 unknown，不能猜造消费或启动前基线。
旧 v1 CLI/env 顺序和 effective value 不变；generation/model/custom 规则仍比较全部
记录观测，消息明确它们是 baseline/unknown-phase 证据。
文件一致性仍比较 lock、当前工作树及原运行输入记录；新 v2 run hash 指启动前基线，
post 检查单独展示。环境与输入 phase 注解不会生成额外 drift 或改变阈值。

## 审阅及当前进度

R04-A / R04-B 的公开失败回归已执行；这是 red 证据，不是任务通过。
规范、schema 和新格式写入尚未启用。最终质量门、Gate A、兼容桥及 CI 尚未执行。
当前状态 REVIEW_READY；接受此提案后按顺序完成产品、定向回归、一次最终质量门及
新鲜五项目受影响 Gate A，再按仓库流程提交并推送 main。

审阅依据：[执行总则 §5.8–5.10](../../00_Execution_Guide.md#5-统一实现与兼容性要求)
明确要求「先准备具体 patch / 提案、对照测试和影响清单，等待该部分审阅」。
[R04-S §6](../../05_Policy_and_Compatibility.md#6-r04-s环境来源与输入时点的条件-schema-方案)
明确要求「有触发条件时，D-41 审阅和版本策略在写新格式前明确」。
[D-39 / D-41](../../../00_architecture_and_decisions.md#6-decisions-log)
分别约束 breaking 的 minor 版本与 schema 维护者审阅。
本提案只请求上述具体规范、字段和兼容策略决定，S3-B 的总体执行授权不替代该决定。

当前 GitHub 工具没有已验证的 issue 写入身份，gh 也未认证；已准备
[spec issue 草稿](spec-issue-draft.md)，不会虚称已经创建远端 issue。
原有 RunPrivacy 快照保真缺陷继续按 VAL-R01 记录，不纳入本次 S3-B 修复。
