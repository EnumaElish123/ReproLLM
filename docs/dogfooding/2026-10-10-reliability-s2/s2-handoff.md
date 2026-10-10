# S2 交接与范围外事项

日期：2026-10-10。以下不标记为已批准的新产品合同。

## R06-B：PENDING_SCOPE_DECISION

`dependency_file_paths`返回全部同basename候选，根目录优先，其余按路径确定排序。
资格判断独立进行，不因工具-only文件或后出现文件丢失根声明。
每scan私有requirements graph保存归一化source/边；每requirements根使用实际
`_RequirementsClosure`决定完整性、所有声明exact与非空package集合。重复边、shared node、
active-stack cycle、有限深度各有独立事实；lock packages不借未引用sibling。
这些是确定事实接口，不是workspace schema、子项目筛除或“任意lock覆盖全仓”的决定。
独立requirements根仍按现有仓库级聚合合同消费；将来scope方案须明确兼容性与gold。
HarmBench九个nested精确pin及独立61-row provenance保持，勿改为root-only。

## YAML-physical-source-index：UNASSIGNED_BACKLOG

现有environment parser的`DependencyDeclaration.line`是dependency entry index。
R05-B独立矩阵另外记录实际物理source行，保留legacy字段合同；没有新增YAML lexer，
也没有宣称修复这一来源精度问题。后续任务需单独定义nested pip与YAML的来源映射。

## 支持子集与限制

Python使用已支持单一非wildcard合法`==`，Poetry另支持裸精确版本；不执行或求解
URL/VCS/path来源。Requirements仅支持空白分隔`-r target`/`--requirement target`，
相对包含文件alias目录规范化；quote/attached/expansion/URL保守，depth最大子层10。
不同合法alias保留各自provenance及相对include基准，不承诺按inode去重。
Conda支持有限数字`N(.N)*`及ASCII literal build；channel/subdir/bracket/regex/
compound/range/glob等复杂MatchSpec保守诊断，不安装Conda、不引入solver。
version/build exact不证明platform/channel/artifact/hash相同。

公共内容边界在首次内容读取前验证解析目标并重新验证cache目标；仍可能在验证后
由并发写入替换文件/路径组件。现有保证不等于无竞态descriptor sandbox。

## 资源与下一会话

历史VAL-R01–R03仍BLOCKED，资源需明确provision后按val.md恢复；本次离线Gate A
不证明GPU、外部provider、paid API或真实judge路径通过。
下一工程S3-A为R07-A → R07-B；读取本报告及当前HEAD继续，不回退历史review SHA。
R07-C、R04-S、R08-A/B与发布/采用任务保持各自待决状态；S2不替代它们。
