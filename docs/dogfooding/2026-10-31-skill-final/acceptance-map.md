# Skill A01–A24 分层验收映射

代码 `a81aa7a3b2fb5b9a323ee09146dfeefa2cf47c29`；文稿 `a6f7e018b92465f6b530fe8029272abdde292736`。当前结论为 **LOCAL_SCOPED_ENGINEERING_AND_GPU_ACCEPTANCE_AUTHENTICATED_PAID_GATES_BLOCKED**。单元、原生/安装、资源、宿主分别记录，不按总体通过率合并成 FULL_ACCEPTED。

最终代码质量门24项/6,666 passed（2个slow deselected），五项目基础50命令/31检查/10份完整JSON通过；当前CPU40导出+40guard+5preview、公开匿名HF和七次真实Codex流程已分别验收。五组GPU A/B与限定离线judge已验收，认证API与两项付费验证为BLOCKED_NOT_AUTHORIZED；Claude Code按维护者暂缓，外部研究者反馈UNOBSERVED。

| ID | 合同/单元层 | 原生或本轮实际层 | 资源/宿主剩余边界 |
|---|---|---|---|
| A01 | 固定来源/hash/catalog正反例 | 当前真实wheel分发检查与source148身份；早期SK2A来源/篡改安装11命令仅历史机制证据 | 当前fresh在线49.08s、卸载0.52s、缓存离线新建23.87s通过，148文件/33缓存保全；异常分支仍分层记录 |
| A02 | 旧版/同版本缺能力/模块遮蔽、独立前缀与探针 | 当前安装身份148/24及Codex全新用户域安装；CPU轻量prefix/9WIP完整保护 | 末尾41分发+927环境元数据已按原始基线复核一致；非全部故障都作真实环境注入 |
| A03 | 复用、并发安装与半成品拒绝 | 当前七流程安装后复用；早期并发/单有效安装与cache语义保持原范围 | 本轮没有把两个真实并发安装作为新鲜场景重跑 |
| A04 | 失败保全/rollback/ownedlease/卸载状态 | 当前真实宿主精确卸载并保留运行/报告/操作结果；早期repair/rollback/lease实测为历史 | 中断升级、所有stale/unknownlease分支主要为contract与早期证据；当前宿主未覆盖全部分支 |
| A05 | Python/venv/权限/磁盘/认证URL/SOCKS/TLS错误与安全诊断 | 当前正常在线、缓存离线和HF匿名网络分别实测；保留正常proxy/TLS | 真实认证provider待授权；Python/SOCKS等异常为contract证据，不称真实403 |
| A06 | 零副作用about、路由/无关请求/不重复菜单 | 五项目基础与既有只读入口；当前真实about仅文档读取 | 无关lint/论文及所有后续路由不是每项都作真实宿主重放 |
| A07 | 权限沿用、缺命令/选择、数据中指令不扩大授权 | 当前宿主check不运行；已明确授权的保存/运行/导出连贯完成 | GPU已按现有授权验收；付费/凭据用途的具体授权另列 |
| A08 | audit0/1/2/3、SKIP/suppressed/缺扫描完整数据与独立门 | 当前五项目完整audit/facts；Codex完整12findings并保留audit1 | 宿主exit0不代表auditPASS；每类错误码并非都作本轮真实故障注入 |
| A09 | Unicode/空格/链接/根/明确外部路径及越界拒绝 | 当前40report/40guard范围保全；早期外部/别名路径专题保留精确范围 | 当前真实矩阵不宣称遍历所有路径/符号链接/外部授权组合 |
| A10 | 完整分页/游标绑定/输入变更、隐私与指令作为数据 | 当前raw335完整链及单页输出；早期417440字节真分片为旧候选；当前分页正反例在Q | 本轮CPU成功回复实为单页，不能称真实多页已重跑；所有原P1/P2按各修正收据闭合 |
| A11 | nativeinit问答/未知/默认值/任务选择与仅登记命令 | 早期五项目C初始化完整对照；当前host新项目保存命令、空参数、未知事实保留 | 没有把早期五项目init全部重称当前新跑；当前故障变体主要由Q覆盖 |
| A12 | 覆盖意图/CAS/旧plan/并发编辑/失败保全 | 当前40guards含缺hash、stalehash、staleinput、研究目标拒绝、已知hash覆盖 | multi-file发布不是跨文件系统事务；schema/init其他故障保全沿Q与C范围 |
| A13 | offline/check优先、身份/stale、长hash与解析失败 | 当前匿名HF40完整结果含offline-after-online与25+25fresh/stale检查；C长hash机制为早期实测 | 大型hash本轮具体运行另记，不把私有模型完整性预检当产品hash场景 |
| A14 | 原生规则全生命周期/具体接受/不可变归档/重复与变化拒绝 | 早期五项目C完整规则产物与无插桩入口；当前Q保留完整生命周期 | 真实新discover的源码证据→具体接受→缺失PASS→重复拒绝仍待新批准请求后验证 |
| A15 | 明确/最近成功/name、损坏/歧义/不足、HIGH与无漂移 | 当前真实host显式两个stdlib记录：1MEDIUM命令变化+4NONE身份/时间；旧B完整reader/diff按原scope | 无runtime binding时未伪造temperature HIGH；五项目GPU十份完整A/B比较已验证各自HIGH漂移 |
| A16 | 历史优先/当前审计分开/四模板/schema10/目标保护 | 当前40export+40guard全部完整字节；schema10当前Q与早期C真实入口证据 | CPU明确不证明实验消费、科学复现或GPU；schema未声称本轮五项目全部重新调用 |
| A17 | 原native客户端403/missing-key/verify-api/doctor与proxy错误 | 当前公开匿名HF完整40结果、199raw、6doctor pairs、58native GET observations | DeepSeek认证GET/模型列表权限未授权；模拟403不等于真实gated访问，弃用Llama2不再要求权限 |
| A18 | 原collector dryrun/show-content、秘密/排除/缺配置/零Client | 当前五项目预览全role/content/source/report/diagnostic重算；DP canonical0fc一致 | 合成秘密与失败输入属于contract；真实provider请求仍为独立场景 |
| A19 | 原客户端JSONmode降级/校验重试、逐send预算与输入变化拒绝 | 仅本轮公开输入预览已验收，未发送付费请求 | 当前候选/固定输入/端点/模型/新预算授权后才允许真实POST及候选全链路 |
| A20 | 未知费用/超时/撤销/恢复、不外层重试、不自动accept | 未知费用保留与操作恢复在mock及contract中通过；没有当前真实收费超时 | 不得制造付费超时或用历史预算/模拟结果声称当前付费门PASS |
| A21 | argv/cwd/env/nullfd/独立Python/child7及native绑定 | 当前Codex两次实际stdlib0与一次取消-15；记录器3.12.14、child产物自报3.9.13 | 另有20次规范GPU native/Skill运行；记录器与3.11/3.10重型child分开，native child包/消费仍unverified |
| A22 | 改写/删除/新建/configbinding/capture快照与敏感流 | 当前host无capture长任务不产生stdout/stderr；Q的原native/合成stream合同 | 五GPU快照/日志与两次offline judge的Python/JSONL已实测；正式付费judge仍BLOCKED，未声称穷尽全部组合 |
| A23 | 重复start/UNKNOWN/恢复/PIDfd/generation/取消/privacylogs | 当前真实新Codex宿主重连同操作、一次TERM、记录-15且lease释放；早期force9仅机制历史 | Linux限定；unknown_descendants不升级为全清理；当前host未实测所有force/PIDreuse/崩溃分支 |
| A24 | 50Linux/48nonLinux适用选项测试与静态25/85/33；不能冒充宿主 | 当前安装身份、CPU/HF/五GPU、限定offline judge、原native源与文稿bridge | 双宿主门DEFERRED；external3–5研究者UNOBSERVED；其他平台实测/最终pushCI另记 |

## SK16–SK21 测试先行与独立复核

| 任务/提交 | 原失败 | 修正后证据 | 独立来源ID |
|---|---|---|---|
| SK16 `8a41841956d7efbf589a1452d267e841d69f1788` | 28 tests:23 expected failures5passes before implementation | 59task-focused pass;754 earlier regression;currentQ covers integrated source | SK16_17_STANDARD, FINAL_STANDARD |
| SK17 `3de9bebde87be8255e3b3fa1266370ad80e7fb34` | Missingadapter RED;4operation failures;budget/credential/source-role counterexamples retained | 115task-final focused;original0/1/3POST mock controls and source-privacy repairs;currentQ6666 | SK17_SPEC, SK17_GUARD_REVIEW, SK17_SOURCE_REVIEW, FINAL_STANDARD |
| SK18 `2cd86945147832335385eaf015655c6eab724536` | 31expected RED beforeadapter;original folder/cwd/private-preflight repros RED | Task181focused and3original fixesGREEN;currentQ andactualCodexstdlib;五GPU矩阵PASS；live judge BLOCKED | SK18_REVIEW, FINAL_STANDARD |
| SK19 `4cb8659b223837c89ae6a38551a353f4b293dddc` | Status/context/delivery/compact RED;independentPEM/PIDuncertainty/statusP1/P2 retained | Final85targeted;7context+4status RED→GREEN;currentQ;currenthostreconnectTERM | SK19_SPEC, SK19_STANDARD, FINAL_STANDARD |
| SK20 `0c51cda` | NOT_APPLICABLE_TEST_ONLY_TASK_NO_BUSINESS_RED_RECEIPT_FOUND | 50Linux portable optioncases;48nonLinux applicable;currentQ;7freshCodexjourneys | FINAL_STANDARD, HOST |
| SK21 `ce7bc79` | Real a81host appendedprivate identity togeneratedreport;originalFAILEDpreserved | Only3MD guidance repair;fresha6sevenjourneysPASS;native reportbody keptunchanged | SK21_DOC_REVIEW, FINAL_STANDARD, HOST |

SK20为新增验收测试与覆盖映射，现有记录没有需要补造的业务RED。其50个Linux用例包含明确的recorder替身，不能用来替代子环境、模型或宿主实测。SK21保留原a81宿主报告追加隐私失败，修订三份Markdown后才重新执行并独立核对a6的七流程。

## 静态清单和文稿缺口

25个命令/组、85个参数和33个typed actions为静态声明范围；192项action-option出现次数不等于192次用户操作。当前链接测试均解析到实际函数。完整机器清单见 [cli-option-inventory.json](evidence/cli-option-inventory.json)，分层证据与逐项状态见 [acceptance-map.json](evidence/acceptance-map.json)。

原 command-coverage.md 的“See the JSON”没有仓库内目标；本次已链接本轮分层映射与静态清单。原私有 f0 准备材料仅保留来源，未当最终行为收据。安装通道增量见[专项收据](evidence/installation-channels.json)，没有新增产品行为。

## 证据哈希索引

| ID | SHA256 |
|---|---|
| plan_acceptance | `bc8ac7e8aa40069538d3e669e6e7fe0726c6f6f7b98adfe03b1d3d320dba4917` |
| SK2A | `ad23f3a5f1a2882bfedc186f6f5cfcc19d53bff2fd6b05bd2914484dbcefc75f` |
| SK2B | `84f5b3d531a3337e5fd96db5298d76cb584810a57df81a5db7b69f76f88ff663` |
| SK2C | `3bdcae602665e3d05221363ea51c4b0a9f5baae0ee3b9eccf54427bc2b94ee55` |
| SK2A_install | `0c44fc7d6d23e340cc6533d74ca45e4678070fc436debaea81cdda399561d1d8` |
| Q | `70165798e4660d7bae1e12513fd4fcea46d711f5b9621cdb24f180e9c94e0a90` |
| BASE | `d8767be27487a6548b80789290532d3f44feafb052e25323a977cbce18fa22a1` |
| INSTALL | `fd17e6aeaf602e71aab5df64202b0246558084efa9e1209c8e2270ef0bc00a8a` |
| CPU | `e8d0234e2905aa625c930ca630db67fc4b915b8d343e2863365a1efd17496bb6` |
| CPU_REVIEW | `ea004849bd40120a4534b062b6793044a556c4dae38edb96fe6e65f213b6e622` |
| HF | `d4c32c3fb179a13188ac4b7667045051b5102f2f05b08cb0265fc50f6fc5ee87` |
| GPU_ROOT | `287e85983829d74f890fa3212128f4abfaf30f2ab0557f8319f63f9fa5e7d829` |
| OFFLINE_JUDGE_ROOT | `5b3780e2aa553f7f35b6253c82af0686fa91a54d0f91474f2a95a30fe54743d3` |
| HOST | `aaf9372aa48d591aaf999502dbd45622bf754dea51446e7cd3ee000ab8e7790e` |
| DOC_BRIDGE | `bd70a96b1e731c6fc7b41760cb52a4c702ce9b9c7ac86170b9fba2a9c784dbf5` |
| FINAL_STANDARD | `ad2b5812eaa8e00c252287c8604541be54733c31978190a2f48cf646159f8a55` |
| SK16_RED | `3b55c6d4a1545ba911763ec7439568bbf8cb635dacd24cad3cba0c7081bd82f7` |
| SK16_GREEN | `677992ab4fd1ddc2cef197b364e4a8ad2f82179087d5fd133726597c19f7297d` |
| SK16_17_STANDARD | `81606eeffde45895a07f6a87328097fe7c7d93e7c31507682e3fa68691bbffc5` |
| SK17_SPEC | `361a43b8517b9d1ff67a17b5cb345a14a54656aa98019e28643342276f62e1f5` |
| SK17_GUARD_REVIEW | `e34fb60579614b7e893742ad26fc0f75741181161be2410d5e2aa85052532b49` |
| SK17_RED | `c7b5cf9b4cb14d7b566148e8592a05bf1b2b5d2ae140953b86b90e19a62e8631` |
| SK17_OPS_RED | `2c13a3948a129bca46f3be983426492e914f555da96acf372040b245c0b8a9a5` |
| SK17_GREEN | `a4379e3fa592373d1c42cdd4bb9689d4ff0279b535782bfa70b9e487155bbe41` |
| SK17_SOURCE_REVIEW | `7c4329ba6b0fd2b8bf181e9ae1235dfeedc2b0edb1d01cec27ebb42a19eb1094` |
| SK18_RED | `c29e9863d0d5bdd58c7ba4da24c29e390cf256285e6f96b66beba4114b46f5c5` |
| SK18_GREEN | `c7d3828b14a2a9e16c646f033c739bb20eb33155f51a16f75e6bae416090f7c7` |
| SK18_REVIEW | `7a1613adad4b17f537ad612c1953af49863e1946772082c1c13f33c2433f2f87` |
| SK19_RED | `3529042a7b2edc1f9c03aa4a627c4e115189d59d7c4ab8fae507a05d08078437` |
| SK19_STATUS_RED | `abb2fc0953d2dcc5fcb1f54c5775e39f4486ecc438fe62b55dc66c843d9abe71` |
| SK19_GREEN | `48cebaec8ea70e7dfb8097cff435649f45b20f9da69471760816cf91b951288a` |
| SK19_SPEC | `de3f310a4761b9891d233c7eed821d51e40d6917cc6967af582de2a0adaa8f29` |
| SK19_STANDARD | `5ec92e9e3ee4946c20873e8ea5c72d12836f11a61b8608ac15a59d2c0f7ecf16` |
| SK21_HOST_RED | `836cf74647bd20ad343b46b2d1a96ff3e5c6566d8b84ba56e5974a35e58aa3a4` |
| SK21_DOC_REVIEW | `fad752048f6734aa4dcebbbb2b38990251224268f84d25c5a0ff805aec911fa8` |
| CLI_PRIVATE_PREPARATION | `15c0a2ca5a191ec07e467cee383b089b8f38b61674a3debf102370265fa78130` |
| CLI_DOC | `19eca836bc78c4953b6dcbbcc0bf3e8ba3dd17ee8753ce3437ed94a776ee8e17` |

已提交的SK2A/B/C报告保留各自候选与插桩/真实边界；本映射没有把历史安装、资源或先前候选重标为本轮新鲜PASS。当前安装双通道复核已由独立安装清单闭合。源代码a81到文稿a6只有三份Markdown差异，旧产品门仍绑定a81，受影响宿主流程为新鲜a6实测。

本映射按已执行并接受的收据维护文稿；整理本身没有重新运行产品、安装、网络、凭据、模型或 GPU。最终文稿更新不改产品源码或原始证据。
五GPU完整边界见[gpu-resources.md](gpu-resources.md)，离线judge另见[限定说明](offline-judge.md)，末尾保护见[收据](evidence/protected-inputs.json)。
