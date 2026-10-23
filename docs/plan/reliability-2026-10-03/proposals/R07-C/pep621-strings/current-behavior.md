# D-M-P：当前源码的有界观察

2026-10-23，基线 `cc6e891c07aea9c8d585e80e2a14eff3b98b32af`。
本页及 JSON 保存**尚未实施 D-M-P 的当前行为**；拟议 `unparsed_requirement`
事实和未来规则结果均未执行。24 组独立预写投影在两次当前源码观察中各 24/24 通过；第二次仅因证据版本元数据修正重核。

## 先确定预期，再观察

[cases.json](cases.json)先写输入、独立依据及 `expected_current_projection`；
预期来自规范 §12.2、§§12.3.3–12.3.8、既有源码控制流和 PEP 621 的字符串合同，
没有从本次观察输出复制预期。每组输入只包含有限、相对路径下的合成文件。
前置技术审计另做过 8 组函数级内存微探，用于选择本轮有界缺口；
它们不是本次 24 组的冻结观察、正式验收或盲测证据。本轮不声称在所有探索性观察前冻结预期。

首次冻结于 `2026-10-23T02:58:27.3852593Z`；下列为首次原始输入 SHA：

- cases SHA256：`71f2bda8afd68de625d4efbc15ec42b001aacf9eeeb64a83ae59eb2ff80abc5c`
- observer SHA256：`0c4e8bd9b7a00760997b2544c3674945e63f8c9d2376d1f486145656f67c3fdb`

冻结收据及原命令收据的 SHA 在 [observation-replay.json](observation-replay.json)。
执行后两项 SHA 与冻结值一致，记录的 8 项源码／规范文件执行前后未变化。
首次输入、观察器及原输出均按原字节归档，未覆盖。独立审阅发现字符串版号不符 D-39 后，
只修正证据版号并添加 producer version，未改输入文件、独立预期或产品调用；重新冻结后执行第二次观察。
[元数据修复账本](metadata-repair.json)列出旧／新摘要、确切修改及比较豁免；两次全部业务观察相等。
两次均 24/24，无失败观察；第二次不是候选政策或挑选更好结果。

## 实际调用与边界

[观察器文稿](current-observer.py.txt)是 `.py.txt` 文稿，不是正式产品代码、测试或 tools。
它在新的可丢弃目录写出每组真实输入，然后调用：

1. 真实 `RepoScanner` 的记录子类，使用 `GitInfo(is_repo=False)` 进行原 fallback 遍历；
2. 原 `scan_dependencies`，记录每次正文读取的路径和大小上限；
3. 原 `AuditContext`、真实 `scan_python` 及 `LlmCriticalDepsPinnedRule` 的
   `applies`、`skip_reason`、`pass_skip_reason` 和 `check`。

唯一固定的环境采集接缝是把 `reprollm.rules.env.installed_versions` 返回值设为 `{}`，
使版本建议不依赖本机安装包。没有替换声明解析、Python 扫描、规则或候选政策。
因此本观察不验证已安装版本采集和 Git listing。

[current-observations.json](current-observations.json)完整保存每组输入及各输入 SHA、
`Declarations` 的全部当前字段（包括内部 project roots、barriers、失败字典和未扩展目标）、
诊断、正文读取、Python 扫描和原始 rule findings。公开文件与第二次私有 raw 原件字节完全相同，未对输出重写或强制类型转换。
仅 `checked_projection_keys` 列出的预写字段计为通过；其他实际字段供复核，
不得事后将它们当作已独立批准的 gold。P19 特意不对 TOML 解码器错误 prose 作断言；
其他 23 组对 `unparsed` 列表均作完整相等断言。

没有执行 CLI、engine、profile detection、init 或 export。
原 `check()` 返回空列表只代表没有逐包 finding，**不等于已验证 CLI PASS 或 engine 合成 PASS**。
没有执行完整质量门、五项目 Gate A 或资源 Gate B，本观察不冒充它们。

网络审计 hook 禁止 socket connect/connect_ex/bind/sendto；导入 hook 禁止
torch、transformers、vllm、huggingface_hub 和 numpy。`gethostname` 没有被禁止，
避免将普通本机查询误作网络；观察器未采集或保存 hostname。未联网解析依赖或 URL。

## 24 组当前结果

“FAIL/WARNING”与“SKIPPED/INFO”均指原规则的 raw finding，不代表命令退出状态。

| 组 | 独立输入／控制点 | 当前完整投影结果 |
|---|---|---|
| P01 | main dependencies：宽松 torch 加失败字符串 | 有效 sibling 保留，失败项仅进诊断，失败字典空；FAIL/WARNING |
| P02 | exact torch 加失败字符串 | exact 2.5.1 保留；原 check 空列表 |
| P03 | 失败字符串加真实 torch import | 只有 import 建立使用；FAIL/WARNING 的来源为 main.py |
| P04 | 失败 `torch==broken`，没有 import | 不猜包名或未知 use；规则不适用 |
| P05 | 有效 torch 加空字符串和空白字符串 | 有效条目保留；两条既有诊断；失败字典空 |
| P06 | optional group 有效 transformers 加失败 torch | 仅 transformers 声明被提取；FAIL/WARNING |
| P07 | 多行重复失败，含 optional group | 原物理行 4、5、9 及顺序完整保留 |
| P08 | 合法非 exact range | 正常提取；不建立解析失败；FAIL/WARNING |
| P09 | 合法 exact | exact 信用；原 check 空列表 |
| P10 | exact 加本机可能不满足的 marker | 保持原静态提取；不求值 marker；exact 信用 |
| P11 | 合法 URL 字符串 | 正常提取为非 exact；不建立失败；FAIL/WARNING |
| P12 | PEP 621 字符串内的 `# note` | D-C 不传播至此；诊断失败，真实 import 建立使用 |
| P13 | 非字符串成员加失败字符串 | D-M-S 已有 invalid_structure；有效 sibling 保留；SKIPPED/INFO |
| P14 | 错误 tool 容器加有效 project 和失败字符串 | 已有 invalid_structure 保留；不多加 falsey 诊断；SKIPPED/INFO |
| P15 | 无关子项目中的失败字符串 | 当前只有诊断；根 torch 仍 FAIL/WARNING |
| P16 | 另一文件含同包 exact | 既有全仓 existential exact 信用；原 check 空列表 |
| P17 | qualifying project 同目录 uv.lock 含 torch | qualified lock 信用；原 check 空列表 |
| P18 | associated uv.lock package 成员结构错误 | D-S 优先；SKIPPED/INFO 的证据仍为声明和 lock |
| P19 | 另一个 Pipfile 有 TOML 解码失败 | 既有 D-M invalid_syntax 与其文件证据；SKIPPED/INFO |
| P20 | requirements 普通行失败对照 | 原失败诊断；不属于拟议 PEP 621 两入口 |
| P21 | embedded pip 的 `-r` 和空字符串对照 | `-r` 保留诊断，空字符串沿旧行为跳过；未增加 issue |
| P22 | Poetry 多条件数组对照 | 原无 pin 声明保留；未增加 issue |
| P23 | Pipfile `{version=false}` 对照 | 原无 pin 声明保留；未增加 issue |
| P24 | dynamic 字段和空 optional group | 不执行动态依赖；零实际 Requirement 调用；规则不适用 |

以上说明：成功解码、容器合法并不意味着每个 PEP 621 声明字符串被成功提取。
P01、P05、P06、P15 的失败项当前不会建立 D-M 不确定性；
P02、P16、P17 同时说明未来政策不能撤销已取得的 exact／qualified-lock 信用。
这些是当前行为与拟议边界的依据，**不是未来 A 方案已运行通过的证据**。

## 运行收据与复制检查

私有 attempt 为 `observation-attempt-01` 和 `observation-attempt-02`；共执行两次，
两次各 24/24、exit 0、失败观察次数 0。公开收据与 raw 绑定第二次，首次缺陷及原件 SHA 保留。
Python 3.12.9、packaging 26.3、Windows `os.name=nt`。
首次观察器 elapsed 为 0.226432 秒、命令 0.358752 秒；第二次分别为 0.238529 秒、0.43474 秒。

可重放命令模板（`<attempt>` 必须是不存在的新目录）：

```text
PYTHONUTF8=1 .venv/Scripts/python.exe -X utf8 <proposal>/current-observer.py.txt --repo <repo> --cases <proposal>/cases.json --attempt <attempt>
```

命令模板不包含真实本机绝对路径。重放器检查基线 HEAD，拒绝覆盖旧 attempt，
并保留真实输入和 `raw-observations.json`。本轮私有原件的逻辑文件名、摘要、
exit、elapsed、环境及源 SHA 均在 replay 中；公开 artifact 不含本机绝对路径、
hostname、用户名或已知秘密 token 格式。

公开复制前有两次隐私检查误报，均在写出公开 observation 前停止，原件已保留：
第一次对原始 JSON 转义文本检查，将 `dependencies:\n` 片段误作 drive path；
第二次改查已解码字符串后，宽泛 regex 又将 `https://` 中的 `s:/` 误作 drive path。
最终仅修正发布检查为对解码后字符串做带 token 边界的路径检查，全部检查通过，
当时原观察数据未改写、cases 与观察器未改、未重跑产品。
随后 D-39 元数据审阅触发第二次观察，经过明确的新冻结；账本保留这两件不同的事。
这两次是发布检查的误报，不是 24 组原产品观察失败；replay 保留首次三项发布检查、其后 D-39 重核的区分及原件 SHA。

独立标准事实参见 [PyPA pyproject dependency strings](https://packaging.python.org/en/latest/specifications/pyproject-toml/#dependencies)。
它约束声明字符串格式；本项目拟议的文件级不确定性、全仓影响和既有信用优先级是另需批准的政策选择。
