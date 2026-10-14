# R04-S localized version/reader preflight

实际HEAD `52ecc504b3795c46220f68ef24728e0666638df0`，CLI与installed metadata均0.6.1。本轮许可的17条只读产品CLI总7.388841s；schema2/3夹具各只改变版本，未加入未批准新字段。全部输入文件前后byte inventory相同，未创建MD，0GPU/API。以下是现状观察，不是新格式验收或正式Gate。

| 当前命令 | run2 exit | run3 exit |
|---|---:|---:|
| runs-list | 0 | 0 |
| runs-show-json | 2 | 2 |
| runs-show-text | 2 | 2 |
| export-selected | 3 | 3 |
| export-latest | 3 | 3 |
| diff-direct-json | 2 | 2 |
| diff-run-id | 2 | 2 |
| diff-latest-successful | 2 | 2 |

`runs list` 返回[]并warning；show/ID diff仅泛型cannot read ValidationError；direct JSON diff提示schema_version1；latest shortcut提示0可用run。`export` selected/latest是unexpected ValidationError的内部错误3，显示Input shouldbe1，不是UserError2/upgrade。完整实际stdout/stderr和SHA见commands.json及独立rawlogs，无隐瞒或自动重跑。

主代理提出的rollout应收敛为：R04-A先形成**本地0.6.2 bridge**，仍读写run1，只统一future2/3升级拒绝并修正export内部错误；冻存源tree/wheel/bin及哈希供R04-B使用。R04-B再形成**0.7.0候选**，写run2、读run1/2，future3明确拒绝。0.6.2尚未实施/构建，不能写PASS。新v2→受支持旧0.6.2应实际验证『安全拒绝并升级提示』，不是说旧读者可读新字段。已发布0.6.1的真实局限列明，不能承诺retrofix。以上需要具体R04-S/D41决定，不授权tag/PyPI发布。

D-39（architecture:236）要求breaking只在minor bump，引入整数schema版本及CHANGELOG迁移。`pyproject.toml`使用dynamic version，`[tool.hatch.version] path=src/reprollm/__init__.py`是版本唯一源，现为0.6.1。console main、run writer、lock writer、audit/diff/discover报告、export footer、doctor均取__version__。uv.lock本地editable根包没有version值，不应借minor bump升级依赖。安装元数据应由根包refresh核对；release.yml仅在真正release时核对tag与__version__，此处不执行。

run version必须localized：共享manifest.SchemaVersion当前Literal1被其余九格式复用，不能扩大。run专用Literal1|2与版本约束防止v1接受新v2metadata，writer显式2；所有读者统一版本检查。State只是内部typed JSON，不在十个schema exports里。预期只run_record.schema.json变化，其余九个完整schema bytes不变，最终freshness必须实际核对。

规范§0『每个persisteddoc schema1』要改为run2例外；§5 run示例、§15来源、§17 State context、§19展示和§23 schema集合声明同步。CHANGELOG保留旧reader真实3和迁移建议。v1历史fixture不批量重写；新v2样本独立加入。compare_gold.py只接受root schema1，比较run2可包在schema1 comparison envelope中保留完整内层版本，或另审工具支持，不能删除schema字段凑通过。

精确入口/验收/文档影响清单见schema-reader-summary-and-version-impact.json。原用户README/docsindex/gold并行修改和既有资源证据未变。
