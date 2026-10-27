# D-M-CS：保留名称的 Conda specifier 边界与官方来源

状态：**PROPOSED，未接受、未实施**。2026-10-27 本轮重新通过网络阅读官方规范、
文档及源码；未安装、导入或执行 Conda，未运行 solver、候选补丁或产品验收。
D-M-CS 是本地 R07-C 标签，不是冻结的架构决定 D-nn。

## 本轮来源身份

| 官方来源 | 本轮页面显示的身份 | 使用范围 |
|---|---|---|
| [CEP 24：environment.yml](https://conda.org/learn/ceps/cep-0024/) | Approved；Updated 2025-04-09 | 原生 dependencies 字符串使用 MatchSpec；installer mapping、其中的 pip 内容另行处理。 |
| [CEP 29：MatchSpec](https://conda.org/learn/ceps/cep-0029/) | Accepted；Updated 2026-03-04 | 版本约束、位置参数、brackets、匹配与规范化表示。 |
| [CEP 33：版本字面量](https://conda.org/learn/ceps/cep-0033/) | Accepted；Updated 2026-03-04 | 非纯数字版本、epoch/local 与归一化排序。 |
| [stable MatchSpec API](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/models/match_spec/) | 页面标题为 Conda **26.9.3** | 官方示例、独立的 version/build 字段、完整产物身份边界。 |
| [stable package specification](https://docs.conda.io/projects/conda/en/stable/user-guide/concepts/pkg-specs.html) | 页面标题为 Conda **26.9.4** | range、OR、版本/build wildcard 的用户文档与历史表述。 |
| [官方 match_spec.py，26.9.3 tag](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/match_spec.py) | 本轮读取该 tag URL 的源码 | 定位 `_parse_version_plus_build`、`_sanitize_version_str`、`_parse_spec_str` 及 dispatcher。 |
| [官方 version.py，26.9.3 tag](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/version.py) | 本轮读取该 tag URL 的源码 | 定位 `VersionOrder`、`VersionSpec.get_matcher`、关系运算符与错误分支。 |

`stable` 各页面本轮显示的版本不同，不能将它们合称为同一份已安装客户端。
网页及 tag 引用可变；此处没有声称绑定 immutable commit、完整 HTTP 原文哈希或
工作区安装版本。CEP 的 Accepted/Approved 也不是所有历史客户端一致实现的证明。
来源身份以各自链接本轮显示内容为限。

## 不能从 placeholder 推出的结论

当前 ReproLLM 在已经保留 head、rest 非空，而且既有 VERSION、RANGE 都未匹配时，
将 specifier 存成固定 placeholder；这个内部事实不携带 Conda 的解析结果。
原生字符串与 embedded-pip 的语法入口本来不同，不能用 Python Requirement 失败、
PEP 440 版本检查或任意同文案 diagnostic 代替这个分支事实。
参见[当前 helper](../../../../../../src/reprollm/core/deps.py)及
[CEP 24 dependencies](https://conda.org/learn/ceps/cep-0024/#dependencies)。

以下是按官方规则阅读的**代表性语法例子**，用于说明范围而非本轮执行结果。
它们不保证相应 torch 版本或 build 在任何 channel 存在，不保证可安装，也不证明
所有命中 placeholder 的任意字符串合法。某些历史前端的接受边界可以不同。

| 命中该分支的代表形态 | 官方来源支持的区别 | 对本提案的意义 |
|---|---|---|
| `torch==2.8.0rc1`、`torch==2.8.0.dev1`、`torch==2.8.0.post1` | `VersionOrder` 明确包含 pre/dev/post；`VersionSpec` 的有效 `==` 使用归一化版本比较。不是只有纯数字 release 才能表达版本精确相等。见[官方 version.py](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/version.py)。 | placeholder 可以遮住版本精确表达，不能一律解释成 range 或非法版本。 |
| `torch==1!2.8.0`、`torch==2.8.0+cu121` | epoch 和 local 是版本字面量的组成部分；不是 build 字段。见[CEP 33](https://conda.org/learn/ceps/cep-0033/#version-literals)。 | 不能因为当前数字 regex 不覆盖这些字符就断言上游无精确版本。 |
| `torch 2.8.0`、`torch 2.8.0 py_0` | 文档保留空格分隔的旧形式；位置、等号和 build 是否存在会影响版本解释。见[CEP 29 version expression parsing](https://conda.org/learn/ceps/cep-0029/#version-expression-parsing)及[API 示例](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/models/match_spec/)。 | 内部空白不等于语法非法；本提案仍不新增这种解析。 |
| `torch==2.8.0=*cuda*` | version 可以精确而 build 使用 glob；version 精确不等于单一 build/产物。见[API 的独立匹配字段和完整 spec 条件](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/models/match_spec/)及[CEP 29 的位置形式示例](https://conda.org/learn/ceps/cep-0029/#version-expression-parsing)。 | build wildcard 本身不能证明 version 非精确，也不能赋予完整产物身份。 |
| `torch>=2,<3`、`torch>=3\|<2` | 前者是 AND range，后者包含 OR；这些具体例子允许多个版本。见[官方 package specification](https://docs.conda.io/projects/conda/en/stable/user-guide/concepts/pkg-specs.html#canonical-match-specifications)。 | 合法、明确非精确的约束也会命中；新的源文件不确定性不能被说成发现隐藏 exact。 |
| `torch=2.8.*`、`torch[version='2.8.*']` | 末尾版本 wildcard 是 fuzzy matching。见[官方 package specification](https://docs.conda.io/projects/conda/en/stable/user-guide/concepts/pkg-specs.html#canonical-match-specifications)。 | 一律把 placeholder 解释为可能丢失 exact，会保守覆盖本来就非精确的输入。 |
| `torch[version='==2.8.0']`；`torch==2.8.0[version='>=2,<3']` | bracket 中的字段可以覆盖同名位置字段；name 有独立例外。见[官方 match_spec.py 的 bracket/component 合并](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/match_spec.py)。 | 只看外侧 `==` 或保留的 head 也不足以判定完整约束；不在本片实现 override。 |
| URL-looking head，例如 `https://example.invalid/pkg` | 官方另有 package-extension/URL 处理；CEP 还给出 `.conda` artifact URL 的身份分解。任意 `https` head 不等于真实包名或合法 artifact URL。见[官方 URL 路径](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/match_spec.py)及[CEP 29 fully specified expressions](https://conda.org/learn/ceps/cep-0029/#appendix-c-fully-specified-expressions)。 | 不新增 URL 读取、包名推断、存在性或可安装性判断；这类 head 也可能保守影响无关包。 |
| 缺失版本、陌生运算符或其他随意 suffix | 官方源码存在缺失/非法 operator、非法版本字符等拒绝路径，但 placeholder 没有执行这些检查。见[VersionSpec/VersionOrder](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/version.py)和[MatchSpec sanitizer](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/match_spec.py)。 | 不能反过来把所有命中者都认证为合法，也不能从同一个 placeholder 推出全部非法。 |

逗号或 OR 的存在也不是所有可能表达式“必定非精确”的证明：AND 可包含单一 exact
约束；源码对复合 matcher 的 `is_exact` 标记与求解后只有一个可选记录是不同层次。
这里不执行约束求解或合并化简。[CEP 29 version matching](https://conda.org/learn/ceps/cep-0029/#version-matching)、
[VersionSpec 复合 matcher](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/version.py)。

## 文档和实现的边界差异

不能从用户指南的历史段落单独导出一般 whitespace 拒绝规则：该页部分旧文字排除
operator 内空格，而 CEP 29 的当前规则要求处理此类空格；所读源码的版本/build
拆分也移除版本部分空格。此处只确认存在不同表述，不执行客户端一致性测试，
更不把自己的字符串修复逻辑加进 ReproLLM。
[package specification](https://docs.conda.io/projects/conda/en/stable/user-guide/concepts/pkg-specs.html#canonical-match-specifications)、
[CEP 29](https://conda.org/learn/ceps/cep-0029/#version-matching)、
[官方 `_parse_version_plus_build`](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/match_spec.py)。

六种既有 numeric RANGE 前缀是 ReproLLM 的兼容控制，不是本研究对每个组合的
Conda 有效性认证。尤其 `~=` 在 CEP 29 中有定义但标为 deprecated；不能据此宣称
所有历史客户端或任意数字组合都有效。保留该现有分支不需要改变其语法结论。
[CEP 29 version matching](https://conda.org/learn/ceps/cep-0029/#version-matching)、
[官方运算符实现](https://raw.githubusercontent.com/conda/conda/26.9.3/conda/models/version.py)。

## 与建议 A 的关系：独立产品决定，仍为 PROPOSED

建议 A 若获接受，只在当前 placeholder 赋值点，用独立内部
`unparsed_conda_specifier` 记录该次有限提取器没有保留 rest 的事实，并复用既有 D-M。
它不是 Conda 解析错误码，不是 Python `unparsed_requirement`，也不扩大已接受
D-M-CE 的“两处省略返回”定义。原 native declaration、固定 diagnostic、specifier
placeholder、名称、序号和 exact/lock 信用均保持；现有 numeric RANGE 路径不触发，
既有 read/shape/pip/CE first cause 不能被覆盖。
这些是本项目待审方案，依据是[现行规范 §12.3.13](../../../../01_specification.md#12313-bounded-omitted-conda-string-entries-r07-c-d-m-ce)
明确留下的 retained-name 范围，不是官方 Conda 规范已经要求的改动。

保守成本必须单独接受：即使是已知非精确 range、wildcard 或无关非关键包的
未保留 suffix，也可能让全仓其余已使用且无信用的关键包 WARNING→SKIPPED/INFO。
孤立 WARNING 或提升的 CRITICAL 门可由 1→0；默认 text 可显示 PASS 和 skipped 数，
默认 export 可少一个 notable 条目，完整 JSON 保留 SKIP。exact/qualified 信用和
更高优先级 D-F/D-S、D-L 继续优先；不合成新包用途或逐包 PASS。
官方语法支持得更广，并不逻辑上要求这种全仓 SKIP；同一个分支还包含无隐藏 exact
的合法非精确输入及未经认证的文本。支持 A 的理由只能是明确接受的保守提取政策，
不能写成上游已证实 pin 存在、Conda-invalid、安装失败或复现成功。

本研究未授权改写 VERSION/RANGE regex、运行 Conda、增加依赖、解析 bracket/URL、
授予新 exact 信用或改变引擎/schema/历史 gold。P-B、真实产品门和资源验证均未执行。
