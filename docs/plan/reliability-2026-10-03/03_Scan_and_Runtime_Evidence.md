# Sprint 3：扫描范围与运行环境证据

版本：v1.1 · 日期：2026-10-03 · 状态：PLANNED

共同合同：[00_Execution_Guide.md](00_Execution_Guide.md)。审查 SHA：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

## 1. 目标与会话

让静态分析预算用于实际项目文件，并准确说明扫描覆盖；让运行报告区分 recorder、宿主环境和未经验证的 child 环境，避免采集值被误读成被包装实验的已验证事实。

| 会话 | 按顺序执行 | 主要产物 |
|---|---|---|
| S3-A | R07-A → R07-B | 一致的候选集、默认诊断、消费者清单、Gate A |
| S3-B | R04-A | 来源 / 时点合同、State / audit / export 消费修正、Gate A |

R04-A 接续 R03 的 State 合并合同。R07-C 的规则覆盖率政策、R04-S 的条件 schema 工作见 [05](05_Policy_and_Compatibility.md)，只在相应任务需要时激活。

禁区：不以统一过滤隐藏安全文件事实；不取消所有扫描限制；不把整个 run.environment 设为 null；不自动执行任意解释器探测环境；不借本任务建设通用远程 / 容器观测系统。

## 2. R07-A：扫描候选过滤先于预算

### 代码入口与已确认问题

`src/reprollm/core/scanner.py` 的 `RepoScanner.files` 在 Git 与 fallback 两种枚举方式下过滤不同。Git 路径可能将虚拟环境或缓存文件计入静态扫描，Python 分析预算为前 500 文件。伪造的 501 个 venv 文件曾挤掉真实业务 AST，并污染 framework / profile 信号。

消费者包括 `core/pyscan.py`、`profiles/detect.py`、`integrations/_static.py`、`integrations/lm_eval.py`、`integrations/lighteval.py`、`integrations/inspect_ai.py`、`discover/collector.py` 及依赖扫描。实际文件名执行前用 rg 核对。

安全消费者也使用文件事实，例如 `env.secret_files_ignored`；Git 事实还用于 `code.no_untracked`。它们不能因为静态分析排除目录而失去证据。

### 实施步骤

1. 列出所有 `scanner.files()` / README / 文件名 / 目录名信号消费者；注明它需要完整文件事实、安全候选还是静态分析候选。
2. 建立明确的静态候选视图或等价接口，Git / fallback 对虚拟环境、缓存、node_modules 等已有明确排除对象采用一致规则；保留现有合理 hard filters，不把任意 vendor / third_party 名称自动扩张为新的排除范围。
3. 过滤发生在 500 文件预算和任何 AST / framework / dependency / task hint 计数之前；排序只作用于过滤后的确定集合。
4. 依据实际路径段、已知目录和 `pyvenv.cfg` 等标记判断环境，不以“所有子目录都是 vendor”排除研究子项目。
5. 保留 Git tracked / untracked / secret 文件事实的独立访问。LlamaFactory tracked `.env.local` 仍须产生现行 CRITICAL。
6. 文档说明分析候选排除及预算；不加入用户不需要的内部枚举细节。

### 回归矩阵

| 场景 | 必须保持 / 变化 |
|---|---|
| 业务项目 + 501 个 `.venv` 中的合成 framework 文件 | 业务 profiles、hints、依赖与无 venv 时一致；不被 venv 挤出预算 |
| Git 枚举与无 Git fallback 的同等内容 | 静态候选和分析结果一致；Git 规则差异另行解释 |
| 带 `pyvenv.cfg` 的非标准环境目录 | 环境内容按合同排除；目录命名不作为唯一依据 |
| README / 配置 / 文件或目录名含伪 framework 信号 | 若处于排除目录，不污染 detector；不能只修 AST 消费端 |
| 真实嵌套研究项目 | 仍作为候选；不因修复被整体隐藏 |
| tracked `.env.local` 或其他禁止文件 | 安全规则仍发现；完整文件事实没有被抹去 |
| 新增未忽略 venv 文件导致 Git dirty / untracked | 业务分析稳定；Git 状态允许真实变化，不能要求整份 audit 字节不变 |
| symlink、不可读文件、大小阈值边界 | 现有安全与资源限制继续有效，诊断可解释 |

### 验证入口

```bash
uv run pytest -q tests/unit/core/test_scanner.py tests/unit/profiles/test_detect.py
uv run pytest -q tests/unit/integrations/test_static_frameworks.py tests/unit/rules/test_env.py
uv run pytest -q tests/unit/discover
```

- [ ] 每个静态消费者都列入检查，没有绕过过滤的独立文件遍历。
- [ ] 安全 / Git 规则仍使用合适事实视图。
- [ ] 全质量门、五项目 L0 + 受影响 init / L1 Gate A 完成。

建议提交：`fix(scan): filter analysis candidates before applying budgets (R07-A)`。

## 3. R07-B：默认可见的扫描截断诊断

### 规格差异

当前普通输出可能不显示截断，`-v` 才显示；规格 §13 也把相应 warning 放在 verbose 说明中。需要同步修改 UX 合同，不能写成“纯内部修复、无行为变化”。

### 实施步骤

1. 在受影响命令上定义一个短且稳定的默认诊断：哪些分析受限、处理数量 / 候选数量、如何理解未发现结果。只提升与结论有关的诊断，不把所有调试输出搬到默认模式。
2. `--format json` 的 stdout 保持单一可解析 JSON；诊断使用 stderr 或已有正式结构，不能向 JSON 前后混入文字。
3. 以真实业务 Python 文件超过 500 的案例测试；不能只使用会被 R07-A 排除的 venv 文件触发截断。
4. 同步规格 §13、CLI / quickstart 生成输出和用户文档。若需要新持久化字段，进入 R07-C / schema 审议，不擅加 extra 字段。

### 验收

- [ ] 499 / 500 / 501 个有效业务文件的边界行为明确，数量稳定；执行时沿用实际 cap 配置。
- [ ] 默认文本、默认 JSON、verbose 三种输出都解释完整性边界。
- [ ] stderr 中无绝对路径、敏感值或重复刷屏。
- [ ] 固定 lm-eval 816 Python 文件的分析必须披露 500 截断；不虚称完整扫描。
- [ ] 默认 fail-on 不变；因诊断新增引起的 gold 展示差异附规格依据。
- [ ] 全质量门及 S3-A Gate A 完成；有必要的规格决定记录。

建议提交：`fix(cli): disclose incomplete analysis in default output (R07-B)`。

本项提供用户可见覆盖说明。哪些规则可以 PASS、应如何表述“未发现”的系统政策在 R07-C 单独决定，不在此统一改所有规则为 FAIL / SKIP。

## 4. R04-A：运行环境的来源和采集时点

### 代码入口与已确认问题

- `src/reprollm/run/wrapper.py::execute / _collect`：`env = dict(os.environ)` 在 child 启动前取得；`_collect` 在 child 完成后执行。
- `src/reprollm/core/envinfo.py`：Python 和 installed packages 来自 recorder 解释器。
- `src/reprollm/lock/resolver.py::_resolve_environment` 与 `integrations/_resolution.py::installed_version`：lock 也有 recorder 侧的环境来源。
- `src/reprollm/diff/state.py`、`rules/consistency.py`、`export/exporter.py` 与 export 模板：消费环境事实。
- `src/reprollm/schemas/run_record.py::RunEnvironment`：现有 os / platform / python / hostname hash / packages / env / env_capture。

审查用另一个 child venv，仅创建 `torch-0.0.123.dist-info` 模拟安装元数据。child 读到 0.0.123，run.environment.packages 却为 recorder 的空集合，warnings 为空。这证明采集对象不同；不证明 child 没装 torch，也不需要安装真实 torch 来复现。

### 必须写入规格 / 文档的来源矩阵

| 事实 | 当前可证明的主体 | 当前采集时点 | 不可直接推出 |
|---|---|---|---|
| run.environment.python / packages | ReproLLM recorder 解释器 | child 结束后的 `_collect` | child venv / 容器 / 远程环境相同 |
| run.environment.env | 启动前复制的 recorder 环境，child 继承基础 | child 启动前 | child 内部后续修改 / launcher 二次改写 |
| OS / platform、hardware | recorder 所在宿主与采集可见硬件 | 实际 collector 运行时 | 容器 / 调度后远程任务使用的同一环境 |
| lock.environment | lock 命令解析时 recorder 环境 | lock 创建期间 | 未来实验运行的已验证安装集合 |

这张表必须落实到消费端可理解的合同，而非只新增一条模糊 warning。

### 实施步骤

1. 加入两个轻量解释器环境的失败回归；只用 stdlib venv 与 dist-info 元数据，不导入 heavy package。
2. 保留可证实的 recorder / host / inherited-env 信息；child 的 Python / packages 未验证时标为 unknown，而不是解释为空集合或版本匹配。
3. 优先使用明确的内部 source / phase 类型与已有 State provenance 能力表达。标签集中定义，消费者读取结构语义；不能通过搜索自然语言 warnings 判断来源。
4. 逐个审查 State、diff、`consistency.env_vs_lock`、export。recorder 与 recorder 的版本比较可以作为该来源的事实，但不能给用户展示成 child 环境已经匹配；来源不兼容或未知时不得产生这种成功结论。
5. 记录本轮选择的具体规则行为：哪些 recorder 比较保留、何时出现信息不足、哪些 finding wording / status 改变。涉及规范判断时先形成可审阅的规格补充，附 before / after 用例。
6. 旧 run 的来源按可确认的 producer 版本合同解释；无法确认者保守 unknown。读取时不改写旧文件、不创造不存在的 child 观测。
7. 若现有字段确实无法让持久化记录和下游保持准确来源，准备 R04-S 的最小字段方案；此时 R04-A 报告到 REVIEW_READY，不以只加 warning 冒充完成。

不要用解释器 basename、`sys.version` 相等、realpath 或 inode 相同推断 child venv 与 recorder 环境等价；venv 可共享二进制但 site-packages 不同。不要为“验证”而自动执行 argv 中未知解释器，也不扫描其他用户环境。

### 必须建立的回归矩阵

| 场景 | 预期 |
|---|---|
| recorder A 包集合为空，child B 元数据含 torch 0.0.123 | recorder 事实保留；不声称 child 无 torch / 与 lock 匹配 |
| 同一解释器启动普通 Python 脚本 | 只能陈述已观测及继承合同；不从命令名承诺 child 未修改环境 |
| uv / conda / shell launcher、容器或远程命令 | 不自动猜中 child 环境；标明未验证 |
| child 运行期间安装 / 改动 recorder 可见包 | after-child 时点明确，不误写为运行开始时快照 |
| 启动前 env 与 child 内部改写 | env 仍说明是启动前继承基线；不记录不可见改写 |
| lock / run 来源相同、不同、未知 | comparison 结果和措辞符合本轮来源合同；未知不 PASS 为 child verified |
| 环境采集失败，child exit 7 | 包装命令仍返回 child 的既有退出码；记录采集失败 |
| 旧 run / State round-trip / 多次 merge | 兼容，source 语义不丢；保留 R03 的 last-wins 不变量 |
| 导出到 neurips / 其他现有模板 | 报告区分声明、解析值、recorder 观测、child 未验证，不遗漏有用宿主事实 |

### 测试入口与完成条件

```bash
uv run pytest -q tests/unit/run/test_wrapper.py tests/unit/core/test_envinfo.py
uv run pytest -q tests/unit/diff/test_state.py tests/unit/rules/test_consistency.py tests/unit/rules/test_runtime_consistency.py
uv run pytest -q tests/unit/cli/test_export.py tests/unit/cli/test_export_templates.py
```

- [ ] 来源 / 时点合同有机器内部表达与面向用户的文档。
- [ ] `consistency.env_vs_lock` 不再混淆 recorder 比较与 child 验证。
- [ ] run.environment 保留有效宿主和 recorder 信息；未知的 child 事实明确未知。
- [ ] 旧记录与退出码兼容；任何 schema 决定均有 D-39 / D-41 处理。
- [ ] 全质量门、S3-B Gate A 与 export / diff 受影响命令回放完成。

建议提交：`fix(run): qualify environment evidence by source and capture phase (R04-A)`。

## 5. Sprint 收尾与后续接口

- [ ] 向 R07-C 交付各规则依赖的事实 / 扫描来源清单，不先全局调整 PASS。
- [ ] 向 D01 / A01-B 交付能准确导出的环境来源说明，用于真实 recipe 的证据分层。
- [ ] 若 R04-S 必须执行，记录最小阻塞字段及已完成补丁；其他 Sprint 正常推进。
- [ ] S3-A / S3-B 各自保留全部五项目 Gate A 记录。

依据：[core/scanner.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/core/scanner.py)、[run/wrapper.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/run/wrapper.py)、[rules/consistency.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/rules/consistency.py)。
