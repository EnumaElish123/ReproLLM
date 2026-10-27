# D-M-CS：未来 P-B 验收组（未执行）

状态：PROPOSED，38组设计，候选政策执行数0。当前观察不是这些组的 P-B 通过。
接受对象包括 public `scan_dependencies`、真实 `LlmCriticalDepsPinnedRule` 和 CLI 三个接口。
以 literal 输入及独立完整预期写测试，不使用候选输出或候选 regex 生成 expected。

| 组 | 独立验收合同 |
|---|---|
| CS-A01 | 两个原早退都未发生，非空rest、VERSION和RANGE均不匹配时才记录新原因；只记录现placeholder赋值分支 |
| CS-A02 | pre/post/dev/local/epoch等不在有限数字子集的suffix保留原声明、占位、None exact和诊断；不恢复信用 |
| CS-A03 | wildcard版本/build等可含合法非精确或版本精确形式；新事实不作Conda-valid或hidden-pin判断，全仓成本明确 |
| CS-A04 | 逗号/或/多重条件等既有placeholder路径按literal边界处理；不新增组合求值 |
| CS-A05 | bracket约束、hash/channel/platform字段保持占位和原head；不解析bracket取回exact |
| CS-A06 | 内空白只按原raw rest；separator/slash前空白与CE早退分别按原路径，禁止归一化改变触发 |
| CS-A07 | URL-looking head、arbitrary suffix可能触发且保留原名；不推断URL内部包，不回显丢弃原文 |
| CS-A08 | 合成secret和机器路径suffix只形成固定诊断/占位；完整持久化JSON和export中无原文泄漏 |
| CS-A09 | 六种原数字RANGE形状（含~=）虽有相同unsupported诊断但不得新增CS原因；不据此声称Conda-valid |
| CS-A10 | bare、单=数字prefix、==数字、=或==加literal build保持exact/specifier和信用；不以exactNone触发 |
| CS-A11 | CE原两早退保持unparsed_conda，不改为CS；无name匹配、channel/subdir省略和blank保持旧合同 |
| CS-A12 | outer strip、Unicode、decoded multiline/trailing-newline保持原fullname匹配路径；不连接物理行 |
| CS-A13 | YAML alias、重复对象和未遍历/循环容器保持有限访问；不因新事实扩大递归或读取 |
| CS-A14 | unknown installer/selector和空/缺字段兼容；列明wrong-shape由原invalid_structure负责，非CS |
| CS-A15 | 实际CS/CE/pip调用首因：CS先、CE先、pip先三种顺序逐项完整比较，setdefault不覆盖已有原因 |
| CS-A16 | 整段structure precheck在循环前；即使错误member物理位置更后也保留invalid_structure |
| CS-A17 | 原read None/decoder exception先于entry；保持原body原因、诊断和barrier，不访问未知正文 |
| CS-A18 | root/nested同basename、内部alias、过滤/排除/体积/预算控制；逻辑relative路径及原ordinal保持 |
| CS-A19 | 重复触发同source只一原因；多source distinct sorted证据，首包声明/否则首import保持 |
| CS-A20 | 同文件部分exact兄弟、不同项目exact、其他格式exact优先，不能因新字典撤销信用 |
| CS-A21 | R06-B合格lock优先；仅存在、不含包、未配对lock仍按现范围；不扩展关联 |
| CS-A22 | 叠加D-F/D-S时高优先级完整Finding保持，不添加D-M路径到它们的证据 |
| CS-A23 | 叠加D-L时Python gap和捕获lock的原Finding优先；完整视图与gap视图分别测试 |
| CS-A24 | 已D-M SKIP可只增source；D-G在D-M后；混合路径逐字典/完整Finding比较 |
| CS-A25 | 原name保留意味着使用集保持；无known critical use时不造包、不新增该规则缺pin结果 |
| CS-A26 | same-package placeholder declaration和import两种首证据；Python complete/partial/unobserved不决定CS事实 |
| CS-A27 | 无关项目/非关键条目/明确非exact触发对其他已用包的全仓成本，多个剩余包逐项预写SKIP |
| CS-A28 | 所有critical已获信用或无使用时，原empty-result Python veto/applies skip保持，不授予新PASS证书 |
| CS-A29 | 完整Finding：ID/aliases/category/level/message/hint/default fields、INFO SKIP、profile override、suppression保持 |
| CS-A30 | 隔离WARNING门1→0；提升CRITICAL门1→0；never0→0；独立达阈值Finding仍1→1，禁止其他WARNING掩盖目标 |
| CS-A31 | audit完整JSON通过schema及全部字段比较；重复/不同根输出确定，root元数据豁免严格限定 |
| CS-A32 | 默认text/details/show-skipped/verbose完整预期；原unsupported诊断字节保持，不能只核摘要 |
| CS-A33 | GitHub格式只按原renderer转换结果，目标warning注解可能消失；无关finding注解保持 |
| CS-A34 | 默认export完整bytes/旧notable条目移除；manifest/lock/run来源和其他模板/内容保持 |
| CS-A35 | init实际三文件、profiles/hints/声明路径保持；随后L1只出现接受的Finding变化，历史文件字节不改 |
| CS-A36 | 有限真实helper/Requirement调用和非空requirements图探针，冻结输入及唯一issue差异；不冒充全部38组图状态运行 |
| CS-A37 | LF/CRLF真实写入字节前后快照、读取/候选轨迹、历史artifact和故意改写负例；不要重复上批的LF假设错误 |
| CS-A38 | 一次最终质量、完整五项目基础+受影响扩展、pin/origin/clean/gold差异、精确HEAD五CI；Gate B按类别明确适用性 |

P-B 每组应给具体测试引用和证据，允许一项测试覆盖多组，不能把组数当测试数。
不得机械把所有非exact或unsupported诊断改成SKIP；保留本片排除路径及更高优先级具体证据。
没有执行的场景记 NOT_RUN；资源门仅在计划激活时执行，缺少必要资源记 BLOCKED。
