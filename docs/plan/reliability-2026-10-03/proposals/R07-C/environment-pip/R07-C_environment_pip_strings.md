# R07-C D-M-E：environment 嵌入 pip 字符串的有界提取失败

状态：PROPOSED。任务依据为当前计划、D-M-P P-B 交接、现行规范 §12.2、§12.3.6–§12.3.9。
本片只准备下一项独立决定；普通继续开发与旧 D-M-P 批准不自动实施新政策。

## 当前行为与问题

`core/deps.py::_parse_environment` 已发现 environment.yml / environment.yaml，安全读取并 YAML 解码后，
先做整个文档的有界结构检查，再逐个遍历 dependencies。只有一个 mapping 成员的 pip 值是 list，
且某成员是 str、strip 后非空时，才把 strip 后文本交给 `_add_requirement_line`。
helper 已有布尔返回值；其失败只追加原诊断，environment 调用点目前忽略 False。

因此同一文档中的成功声明、Conda 信用与资格均可保留，而该失败字符串未贡献 declaration，
也没有新增 declaration_read_issues。这是当前明确排除于 §12.3.9 的提取缺口，不是实现违反已批准合同。
没有宣称工具应执行完整 pip grammar。pip 的注释／-r／options 等可被安装器接受却不能由此解析器提取。

示意输入是 `dependencies: [{pip: ["torch>=2", "not a requirement"]}]`。
当前 torch 无信用时为 FAIL/WARNING；推荐 A 在这一个原调用失败后记录文件级原因，沿既有 D-M 输出
SKIPPED/INFO。实际当前观察与独立未来预期分别保存，尚未运行这个候选结果。

## 推荐 A：只消费既有失败结果

1. 保留原字符串判断、空白跳过、strip 字节和单次 Requirement 调用；只在现有 helper 返回 False 时，
   `declaration_read_issues.setdefault(path, "unparsed_requirement")`。
2. 同源 unreadable／invalid_syntax／invalid_structure 优先。结构检查在整文档遍历前执行，
   后面的结构错误也已先记录，不能被前面失败字符串覆盖。不从诊断文本解析原因。
3. 有效兄弟、声明顺序、Conda canonical/exact、manifest 资格、项目根、barrier、锁集合与关联保持。
   不新加原因词汇、公开字段、规则分支、解析、读取或安装器执行。
4. 保留现有行值：外层 dependencies 的一基序号，同一 pip 列表所有子项共享；不是 YAML 物理行。
   原诊断仍使用 strip 后失败文本，不增加逐子项 evidence，不借本片修复位置精度。
5. 只复用 D-M：qualified／exact → D-F/D-S → D-L → D-M → D-G → 原 WARNING；
   每个包保留已赢的信用或分支，不能整条规则提前返回。

候选 B 完全保留当前调用者不记录原因的合同；本缺口继续 OPEN，后续仍可另行提案。
不建议第三种“实现全部 pip grammar／执行 solver”的扩大方案；它不是本片的边界。

## 必须具体接受的成本

D-M 的影响保持全仓，失败源不必与 use 同目录。无关 environment 中一条未提取字符串，即便安装器
可以接受它，也可能使所有剩余未获信用关键包 WARNING→SKIPPED。此举只承认提取不完整，
不证明隐藏 exact pin 存在、不授予 lock/declaration 信用、不宣称复现通过。
孤立 warning 或 FAIL-only CRITICAL override 可 exit 1→0；独立 warning／critical 仍按原阈值失败。
完整 JSON 保留 skipped；默认 text 可显示 PASS 和 skipped 计数；default export 不再列旧 notable warning。

## 精确文件和禁止区

[规范补丁](spec-proposed.patch)拟新增 §12.3.10 并修正 forward refs，明确 §12.3.9 的 PEP 621 与本片分别 opt-in。
若获接受，产品原则上只需变更 `src/reprollm/core/deps.py` 的现有 environment 调用点，
先新增 core/rule/CLI 回归；现有 helper 的 bool 和内部原因词汇已存在，无需改它们。
实施仍须 CHANGELOG、独立任务提交、最终质量门、五项目 Gate A 与受影响验证、精确 HEAD CI。

本提案不请求更改 D-41 的 engine/redaction/schema；若后续扩大到这些文件，需另行具体审阅。
不扩展 Conda MatchSpec、其他 manager 包值、pip directives/includes/comments、读取候选、预算、
未捕获 use、listing/framework 或充分证书，不更改历史 gold／资源结果／版本，不发布。
