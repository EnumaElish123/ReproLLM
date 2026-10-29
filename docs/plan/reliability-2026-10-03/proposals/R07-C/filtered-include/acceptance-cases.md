# D-I 的未来 P-B 验收设计

状态：DESIGN_ONLY。以下不是本次已执行的新政策测试。
接口沿已约定公开 audit、init（含 list-tasks）及 export；不 spy 自有 scanner/graph/engine，
不把 CLI 规范化输出说成内部节点计数。source 分支依据与公开行为证据分开记录。

| ID | 输入/边界 | 独立预期 |
|---|---|---|
| I01 | torch>=2.5.1 + supported include build/pins.txt，正常深度 | 现 WARNING 的 tracer 先RED；A后逐包 D-I SKIP/INFO，原use evidence后附目标路径 |
| I02 | 同目标正文为 exact / nonexact / empty / malformed | 都不读正文推断；只按实际 candidate False，Finding 相同 |
| I03 | build/pins.txt 不存在 | 仍可触发；不宣称存在或含 pin |
| I04 | dist、.venv、硬跳过 runs 前缀 | 原 candidate False 才触发，不改读取边界 |
| I05 | 自定义目录 pyvenv.cfg marker | 实际拒绝触发；marker检查失败只可作为原False，不细分原因 |
| I06 | 内部 symlink 指向排除路径；安全的物理源别名 | 前者原False触发，后者保持原正常读取/信用 |
| I07 | Git和非Git；相同root/include语义 | 门合同相同；完整其他Git finding按各自事实保持 |
| I08 | 任意扩展名 target，例如 pins.data | 可作为 supported include target；不把root命名规则错误套给target |
| I09 | shared/duplicate/normalized target 与多目标 | 只附distinct sorted逻辑路径；不新增读取/边或诊断 |
| I10 | 可读target，包含 exact/nonexact/empty | 不触发D-I；原信用、WARNING、空闭包合同保留 |
| I11 | candidate=True而 read=None：缺失/binary/超上限/越界 alias | 只保留D-M，不能把unreadable反推为candidate过滤 |
| I12 | malformed/unsupported/absolute/escaping/remote include，没有normalized target | 不触发D-I，不增加探测或语法 |
| I13 | 深度10边界；depth11目标未检查 | 未达目标只归D-G，不能新探测其filter；预算不变 |
| I14 | 同时D-G和D-I；或后来的浅root捕获旧frontier | D-G优先且原finding全字段保留；最终图及D-I各按自身事实 |
| I15 | exact/requirements完整lock/合格格式lock与D-I并存 | 正信用先赢；无额外每包PASS/SKIP |
| I16 | D-F/S、D-L、D-M与D-I并存 | 每一旧优先分支message/hint/evidence全保留，不追加低优先路径 |
| I17 | 无关子项目被拒绝；多个已知未获信用包 | 全仓逐包SKIP；不得按关联或文件名猜包名 |
| I18 | 无已知critical use；全部获信用；Python完整/gap | applicability与空结果veto保持，不创建use/新证书 |
| I19 | WARNING与promoted CRITICAL孤立门；独立warning | 原门1→新0可复现，独立违规仍1；never仍0 |
| I20 | ignore/suppression、FAIL-only override、alias、排序 | 沿既有engine合同，SKIP为INFO，原suppress证据保持 |
| I21 | 默认text/show-skipped/JSON/verbose/default export | JSON保留D-I；默认text可PASS+skip，export少notable；原诊断不改 |
| I22 | init/list-tasks与完整profile/hints/manifest；全部五pins | 现捕获库存不变；零差异须与独立gold完整比较，不只比summary |
| I23 | legacy/manual newtuple默认空；内部图缓存 | 原构造兼容；图已有节点不新增候选/正文调用，缓存不被重读 |
| I24 | root被拒绝但没有受支持可读parent入边 | 不凭root或私有set非空合成D-I target；一般遗漏root仍OPEN |

P-B用例应逐条映射到既有优先级和具体补丁，先公开CLI tracer再纵向扩展。
新tuple在五pins为空的预期来自独立源码盘点，P-B须单独断言；既有facts collector若只输出旧投影，
不能据其“完整比较”声称验证了新field。marker检查故障及symlink案例必须记录实际前提，
公开CLI输出不证明内部probe次数；不为了这些验收增加产品探测或持久化字段。

同一最终源码/测试输入只跑一次最终完整质量门；产品会话 Gate A 覆盖全部五pins，
含freshL0、完整facts/profiles/hints/诊断、disposable init→L1/default export和完整任务清单。
Gate B不因普通政策切片自动激活；资源/里程碑/发布仍按val.md独立边界。
