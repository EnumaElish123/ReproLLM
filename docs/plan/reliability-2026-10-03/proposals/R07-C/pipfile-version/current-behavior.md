# 当前行为与可重放边界

观察基线 `d7bc16b3a4f855ccd35546966ee6424dcd47cc96`；真实 producer 0.7.0、Python 3.12.9。
38例，每次最终326项 literal assertions。原38例v1在首次观察前冻结；首次执行完成但三处预期字段错误，v2按源码更正：PF29 raw lock membership 不等于 qualified origin credit；PF36 depth 失败含10层祖先传播共11诊断；PF38 requirements exact 保留 specifier `==2.4.0`。
原输入、首次失败和更正理由保留，不把它们删成一次全绿。更正不改产品、observer 或 synthetic 输入。

随后同一v2在两个新目录重放，完整255218字节输出一致，SHA-256 `e4590883201993c2bcc9d6c2ccb181c8d06006105c2c05d10e2a9d394641968d`。
两次各61输入文件实例原字节核对；128源码文件前后相同，53个已导入产品模块核hash。真实非Git scanner，禁network/subprocess/heavy import，installed_versions空；PF30明确构造coverage gap。
包含完整 Declarations 内部字段、锁/根/屏障/graph、Python记录、read/candidate/helper/Requirement traces及三项raw env规则finding。日期时间以预声明typed ISO编码保存，strict JSON不允许NaN。

当前观察：26例 raw warning、5例 positive-credit raw空、6例 raw skipped、1例 no-use。它们不是 engine/CLI整体结果。
未记录结构错误的 mapping非str version 仍留下同名声明；当前缺pin的26例继续warning。候选政策执行0，manager/solver/CLI/audit/init/Gate A执行0。
两次最终观察累计命令1.039172400秒，含首次失败的三次观察1.591331300秒；没有把命令时长当整会话墙钟。

[冻结v1](cases-frozen-v1.json)、[更正v2](cases-frozen-v2.json)、[首次失败整件](replay-01-observations.json)、[最终完整记录](replay-02-observations.json)、[所有观察收据及准备错误](replay-summary.json)、[回读摘要](behavior-summary.json)。
第二个成功整件与第一个逐字节相同，只公开一次正文；原件留本机，摘要绑定两者哈希。
六个原始stdout/stderr为Windows原字节，在[无损base64封套](raw-command-streams.json)保存，解码后的bytes/SHA必须吻合，未归一化换行。
[复制映射](publication-copy-map.json)披露此表示方式；原命令含绝对路径，仅公开哈希引用。准备脚本/quoting/隐私误报与首次复制LF假设错误均保留或明确披露，不冒充产品失败或从未失败。

## 本地重放

使用单独的基线 checkout，HEAD必须等于上面d7bc完整SHA，src来自该提交且环境依赖与0.7.0兼容；不要在用户输入或正式五项目运行。
把 [observer文本](current-observer-v1.py.txt) 原字节复制为临时 `.py`，给出repo、cases、全新root和output：

```text
python -X utf8 current-observer-v1.py --repo <baseline-checkout> --cases <packet>/cases-frozen-v2.json --root <new-empty-directory> --output <new-output.json>
```

本轮已执行的真实命令、退出和耗时绑定在收据中。重放会校验基线HEAD、producer、源码/输入与326项预期；它不安装Pipenv、不调用网络、不应用候选。
公开输入、observer和完整业务记录支持此当前行为重放；私有Git原始流、HTTP原文与完整命令正文仅凭哈希不能独立复验。
