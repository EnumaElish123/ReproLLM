# 当前源码观察与候选边界

状态：当前源码观察完成，候选政策执行数 0。基线为 72bf2fc，实际 producer 为 reprollm.__version__ 0.7.0。

27 个 E01–E27 合成案例记录完整 Declarations、关联内部字段、scanner 候选/读/list 调用、原 Requirement 参数、
实际 Python 采集及三条 raw env rule 的完整 Finding。字面断言只检查预写指定投影，完整记录的存在不等于所有字段
已被独立预期逐项验证；两次重放对全部记录逐字节比较，不能把投影 PASS 写成全量 gold 已审定。
E20/E22 显式设置 Python coverage 元数据缺口，保留真实 import；安装版本 seam 固定为空。
原生 symlink、公共 CLI/engine、init/export 或整体退出码未在这些观察中执行，不能冒记 PASS。

| 当前事实 | 观察与后续保留要求 |
|---|---|
| 空白 pip str | 不调用 Requirement、无新诊断；A 保持跳过 |
| 非空失败 str | 先 strip、原诊断保留；当前 environment caller 忽略 False |
| 位置 | 一基外层 dependencies ordinal，共享于同一个 pip list；不等于 YAML 物理行 |
| 结构原因 | 全文 precheck 先于提取；即使坏成员在后，也保留 invalid_structure 优先 |
| 部分声明/信用 | valid pip、Conda pytorch exact、独立 requirements exact、合格 lock 原样保留 |
| 双 environment basename | 原同目录 conda-lock 配对歧义不变 |
| 较高原因 | 当前 D-F/S、D-L 先于 D-M；未来新 cause 不追加较低优先级 evidence |
| 新源/原 D-G | 未来可能只扩大 D-M evidence，或以 D-M 接替 D-G；不是零差异 |
| pip directive/comment | E27 的 -r extras/pins.in 不新增读取；该目标有 exact 文本也不从此获得信用 |
| 独立 requirements root | E09 的独立发现仍可提供信用，不是 embedded include 扩展 |

最初案例先写再执行；但首轮 162 个字面断言中有 1 个 E21 旧 D-G 诊断预期错误：深度上限为 10，
实际先在 chain9 记 depth-limit，再向各 parent 记 incomplete。依据现有 _closure 和既有 depth 回归修正该诊断字面值；
产品、pip 输入、原因/信用预期和候选 A 选择均未改。修前 cases/raw/patch/收据完整留本地，见[来源索引](source-refs.json)。
E27 的非根文件命名在首次执行前已按真实发现规则修正。两次更早修正后观察仍保留，后来指定的 03/04 两次重放
各 162/162、exit 0，在不同空根产生完全相同的 174347 字节业务记录。总共 5 次 observer 调用，不是两次总执行。
最终案例中 E21 预期是在首次观察后修正，不能宣称全部最终预期都是第一次观察前盲写。

[未执行的 A 分类](recommended-impact.json)预写：19 案例可新增 20 个按案例计的逻辑文件原因；
10 个 raw critical WARNING 可变为 SKIPPED，E21 可由 depth 改用 declaration，E23 可扩大既有 D-M evidence。
这些不是已运行候选结果，也不是 CLI 退出码／五项目 delta。其余信用、no-use、更高原因和无新原因控制逐项列出。

复验需提供基线 72bf2fc 的独立 checkout 及其 locked 开发环境，在全新 root 执行：

```text
<BASELINE_PYTHON> -X utf8 current-observer.py.txt --repo <BASELINE_CHECKOUT> --cases cases.json --root <NEW_EMPTY_ROOT> --output <NEW_OUTPUT>.json
```

observer 验证基线提交与 0.7.0，记录 128 个源文件前后 hash 和 53 个已加载产品模块来源/hash；
真实 non-Git scanner 运行，初始身份核对后禁止子进程、网络及重库导入。新重放生成新收据，不覆盖本次原件。
历史 replay03/04 精确命令/退出/耗时/原始流 hash 见[重放摘要](observation-replay.json)。
