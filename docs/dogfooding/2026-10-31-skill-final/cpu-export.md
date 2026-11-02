# Skill CPU A16 完整验收记录

结果：**PASS_CPU_A16_AFFECTED_MATRIX**。代码候选 `a81aa7a3b2fb5b9a323ee09146dfeefa2cf47c29`；文稿候选 `a6f7e018b92465f6b530fe8029272abdde292736`。维护者已接受原始 CPU 完整矩阵，正式收据 SHA256 为 `e8d0234e2905aa625c930ca630db67fc4b915b8d343e2863365a1efd17496bb6`。

本轮逐项核对 **40 个导出、40 个 guard、5 个离线 discover 预览和335组捕获调用**。完整 Markdown、对应 JSON payload、诊断、发布计划、CAS哈希与历史快照均已比较；摘要数量只是矩阵索引。原始记录和独立审阅保持不变，本文配套 JSON 保存全部逐项结果与证据哈希。

## 验收范围

- 每个项目验证 current/historical 两种作用域，各使用 default、NeurIPS、ACL、ACM 四模板。完整 native CLI、Skill preview/apply 与实际发布文本逐字节相同，包括所有附录。
- 每个项目验证六个拒绝分支和两个成功分支。拒绝诊断及完整 before/after 输入清单一致；成功覆盖已知旧哈希替换和 fresh-clone Git index SHA/mtime 保持。
- 五个 discover 预览均与独立源码重建、原生产 CLI 和冻结消息的完整 role/content、report、source/tree、预算及诊断一致。没有发送模型请求。
- historical binding17、current declaration29和批准的两个空参数边界保持分明。自定义值没有被假定为一定渲染在文本中。
- 实际成功回复均为完整单页；检查了全部原始分页引用、complete与终止cursor。这一结果没有宣称已运行多页场景。

## T-02 与保护边界

本 CPU 矩阵没有泛化删除时间或版本字段。冻结 run/manifest/lock 的内容完整保留；进程标识、耗时及控制测量保留在各自证据中，不当成语义相等字段。原生文本到结构化payload只转换协议载体，不丢失诊断、字段类型、键或有序列表，不扩大规范T-02的例外。

五个原仓库的完整 before/after/readback 文件内容和模式相同，45次原始 pin/origin/clean 检查闭合。轻量工具prefix的2,370项清单（2,133个普通文件）完整一致，实际delta为空；CPU收尾时leases为空。9份原WIP文件未变。148份native源文件、18份helper及catalog已核对；末两项目另核14个项目/原生oracle位置的全部科学源文件、模式、无原仓库硬链接及受控新增路径。

会话另有**41项研究环境分发的原始基线**，其SHA256为 `31ab1d761698268075feda2560cf63edde667a76106d80d9433945b337ca9923`。CPU验收没有对它作完整后验；会话最终41项分发与927个sentinel的独立复核仍属后续边界，不写为CPU已通过。

代码候选到文稿候选的桥只变更 `CHANGELOG.md`、`skills/reprollm/SKILL.md`、`skills/reprollm/references/workflows.md`；15,292项Git清单中15,289项逐项相同。新文稿没有被表示为新的产品、资源或宿主实测。

## 40个导出

| 项目 | 作用域 | 模板 | 完整文本SHA256 | 结果 |
|---|---|---|---|---|
| FastChat | current | acl | `d9ac68ff960eb1304321a254e6efca20f2d38d55287c14f86a95e2df096df2f3` | PASS |
| FastChat | current | acm | `23b095cfce02f1d83bb7d65bd61ba18ff5b8f38db5f16e4e5a3f22457350afeb` | PASS |
| FastChat | current | default | `e1611ea15ea78cc0b9cde7fac437d08ffa89ffb2431871c55b2fc0c97d8a4a0c` | PASS |
| FastChat | current | neurips | `731183053a41423ae0e1c2c3c472cb2efcbad22a11a6d0e029c7e774395736bc` | PASS |
| FastChat | historical | acl | `d9a7aebcb5c4b1d66e0081735239020a0d4025a909fd55c2ecd18860de2a15b4` | PASS |
| FastChat | historical | acm | `7e35151f99d57d96d0460931ed33af0a1ee9f4a77595aeca7fe0fc7070615b55` | PASS |
| FastChat | historical | default | `03161daa1c40f0a8da324d7521fa1ef1d46b70c3b3ee7365409979b016a367ec` | PASS |
| FastChat | historical | neurips | `289927a942b74a15c8caa299b9d87d436f824c90eeda313354c66fd4ec5fbb12` | PASS |
| HarmBench | current | acl | `d86a4f31a4aed8d780b67c920154c3831a984845a382b7041a9c701bc03207c9` | PASS |
| HarmBench | current | acm | `931b62ebb3a8aadb3da41b33020b310be8089be54ba0839f5c0ae5bd9f6d5ae5` | PASS |
| HarmBench | current | default | `aa39f4a16ed83af24000587e5562a080109b42565f6d6f0bb7b1a5bae52bd4e4` | PASS |
| HarmBench | current | neurips | `b4da88d852cdad70f4d9aa3c50f7074eb3c2acfa2d958b67f0bb4b57c73ad5af` | PASS |
| HarmBench | historical | acl | `aeb11b097803dcd405d076aa7ee0c375ca4540430ab898ca531ebb826476812b` | PASS |
| HarmBench | historical | acm | `58d5665c9493a05bd0625454764f8eeec1a3f1da36bff025a60858f98fc9dbc5` | PASS |
| HarmBench | historical | default | `49bbe3bf118b68013c304f5df50bc19ed2655532c7a9b7aa20f4f814ce72ef93` | PASS |
| HarmBench | historical | neurips | `cff8b59a6280352664b2f289187105c70327196764136e59fbd185271c664780` | PASS |
| LlamaFactory | current | acl | `4512f7bb053c3195d0dc7cd47b783df984bba42d3488fb6c917116e55bd97729` | PASS |
| LlamaFactory | current | acm | `ed33a347d41ebbe8da2ec8bd05ec30facc9d043b9a0b9b0e6347525b074debd8` | PASS |
| LlamaFactory | current | default | `274614dc0c03d5f01960764466bc2b63a26cb27599ca33321a156818e11a0bd9` | PASS |
| LlamaFactory | current | neurips | `84f780463686cb9497b2329634efdf90f7e6c6eda06264f1556f9196629dd944` | PASS |
| LlamaFactory | historical | acl | `0d258d17f98bab9029dbb11027e0c409c0a0310f974f1af5fe15461094491a32` | PASS |
| LlamaFactory | historical | acm | `7cbb219cab3bcbcdf6a11eb793cb43ebf5da85caefb82ab2e3b5df3eb01bbfd8` | PASS |
| LlamaFactory | historical | default | `64d98f428fe7fa5187b20a78642d42cbef7d2b46198d3b88f0b68b9f65dbe13c` | PASS |
| LlamaFactory | historical | neurips | `6cb472c662cf3bb5ebf364668a86e609cfae4edb57d81a530b6c90ec00248e32` | PASS |
| llm-dp-finetune | current | acl | `ea858b459642e65aa1598258a4bf7c487680acd9170002c8649a4c5badfe7186` | PASS |
| llm-dp-finetune | current | acm | `326d25acf55602562bb0c8cff27704b4a83f037a3c4547a27a876a2f789b7ced` | PASS |
| llm-dp-finetune | current | default | `6c49f8e7ab467649d3ea69fcc945e5e1f5207d20bcca90c7dd442cc5ef2fe12e` | PASS |
| llm-dp-finetune | current | neurips | `a813612de5020bab5e90b215ef5ff868a305d6f92c058188f74baad00decbcc6` | PASS |
| llm-dp-finetune | historical | acl | `a15f9066fa92f6ae8059ade0e26bebe534b39b0d42e1b853fda80a1291b76a26` | PASS |
| llm-dp-finetune | historical | acm | `7cc310e5fa8e479860d490027c06d85bd4a8317af625a848276b8511db769636` | PASS |
| llm-dp-finetune | historical | default | `c625f71c370263155aeee084ba1688373cd5800c8d8307261aa9dea2d1eee45c` | PASS |
| llm-dp-finetune | historical | neurips | `80b33590e38ac44cf080818d6cec444f5d22eee24c8e3c1b2af22672a297817d` | PASS |
| lm-evaluation-harness | current | acl | `0ef068b7889e0e2a925fdd0c536bd4b6c9e2313b80fde7ba5aee012eb1f72c1a` | PASS |
| lm-evaluation-harness | current | acm | `7c8355094b535dbb71d5f7e79231ebae0c821caa928cc6bde152f0b520bea323` | PASS |
| lm-evaluation-harness | current | default | `80164f1088279b8fc5408a185383eca78e2c5aa58e30c3e617b49ad095179689` | PASS |
| lm-evaluation-harness | current | neurips | `af060e81424c1f193bc8292647be15bd2115f20ed4c7b9a9dc8fddd7392aeb61` | PASS |
| lm-evaluation-harness | historical | acl | `d51cb1d9cc8be0d47fa4ed3b54546a33f533f75b5020f627ee2bf1ae76723488` | PASS |
| lm-evaluation-harness | historical | acm | `0a5d26116d810ebdb93280ebbd84df0d14c2b67f214c58279b72c85141549519` | PASS |
| lm-evaluation-harness | historical | default | `a2cabcb7e9d9245275f8066d0b16861ab62ec916562c9874b65a340242ee9401` | PASS |
| lm-evaluation-harness | historical | neurips | `ce8de5aa0b37ef0868b5c9cc1e9e4e7722f40d6d9eda5fe231a2ad3469ccb7cf` | PASS |

## 40个guard

| 项目 | guard | 期望诊断/结果 | 结果 |
|---|---|---|---|
| FastChat | explicit_dot | `report_target_is_research_input` | PASS |
| HarmBench | explicit_dot | `report_target_is_research_input` | PASS |
| LlamaFactory | explicit_dot | `report_target_is_research_input` | PASS |
| llm-dp-finetune | explicit_dot | `report_target_is_research_input` | PASS |
| lm-evaluation-harness | explicit_dot | `report_target_is_research_input` | PASS |
| FastChat | fresh_clone_index | `handled_result / complete native mapping` | PASS |
| HarmBench | fresh_clone_index | `handled_result / complete native mapping` | PASS |
| LlamaFactory | fresh_clone_index | `handled_result / complete native mapping` | PASS |
| llm-dp-finetune | fresh_clone_index | `handled_result / complete native mapping` | PASS |
| lm-evaluation-harness | fresh_clone_index | `handled_result / complete native mapping` | PASS |
| FastChat | known_hash_overwrite | `handled_result / complete native mapping` | PASS |
| HarmBench | known_hash_overwrite | `handled_result / complete native mapping` | PASS |
| LlamaFactory | known_hash_overwrite | `handled_result / complete native mapping` | PASS |
| llm-dp-finetune | known_hash_overwrite | `handled_result / complete native mapping` | PASS |
| lm-evaluation-harness | known_hash_overwrite | `handled_result / complete native mapping` | PASS |
| FastChat | missing_target_hash | `write_target_approval_required` | PASS |
| HarmBench | missing_target_hash | `write_target_approval_required` | PASS |
| LlamaFactory | missing_target_hash | `write_target_approval_required` | PASS |
| llm-dp-finetune | missing_target_hash | `write_target_approval_required` | PASS |
| lm-evaluation-harness | missing_target_hash | `write_target_approval_required` | PASS |
| FastChat | research_directory_target | `report_target_is_research_input` | PASS |
| HarmBench | research_directory_target | `report_target_is_research_input` | PASS |
| LlamaFactory | research_directory_target | `report_target_is_research_input` | PASS |
| llm-dp-finetune | research_directory_target | `report_target_is_research_input` | PASS |
| lm-evaluation-harness | research_directory_target | `report_target_is_research_input` | PASS |
| FastChat | research_file_target | `report_target_is_research_input` | PASS |
| HarmBench | research_file_target | `report_target_is_research_input` | PASS |
| LlamaFactory | research_file_target | `report_target_is_research_input` | PASS |
| llm-dp-finetune | research_file_target | `report_target_is_research_input` | PASS |
| lm-evaluation-harness | research_file_target | `report_target_is_research_input` | PASS |
| FastChat | stale_input | `write_plan_changed` | PASS |
| HarmBench | stale_input | `write_plan_changed` | PASS |
| LlamaFactory | stale_input | `write_plan_changed` | PASS |
| llm-dp-finetune | stale_input | `write_plan_changed` | PASS |
| lm-evaluation-harness | stale_input | `write_plan_changed` | PASS |
| FastChat | stale_target_hash | `write_target_changed` | PASS |
| HarmBench | stale_target_hash | `write_target_changed` | PASS |
| LlamaFactory | stale_target_hash | `write_target_changed` | PASS |
| llm-dp-finetune | stale_target_hash | `write_target_changed` | PASS |
| lm-evaluation-harness | stale_target_hash | `write_target_changed` | PASS |

## 5个离线discover预览

| 项目 | 完整消息canonical SHA256 | 用户字符/UTF-8 bytes | 结果 |
|---|---|---|---|
| FastChat | `94210251613b1d34ecf84ac73b2e9d3a14249de6779d9ab7cf54a9e80c5356c4` | 32557 / 32563 | PASS_OFFLINE_PREVIEW |
| HarmBench | `70aa425659293cc1e00eae73691d8122724107bd8b338799e6dc039e5f0a6d45` | 33220 / 33377 | PASS_OFFLINE_PREVIEW |
| LlamaFactory | `a246b0ce0d8cc9eb4ec082cb731e48d304a0400fdb288efcc96710b7ef36af55` | 30867 / 32070 | PASS_OFFLINE_PREVIEW |
| llm-dp-finetune | `0fc05639fe86a79bfc4dba19bfa72d4ed7255423c52c23d1faade5aafc11b70a` | 31337 / 31342 | PASS_OFFLINE_PREVIEW |
| lm-evaluation-harness | `e632c7f63b0b30dea3b7fdc6cbf234e405aca515150b3bf810a771854721a93c` | 33079 / 33082 | PASS_OFFLINE_PREVIEW |

## 关键证据

| 证据ID | SHA256 |
|---|---|
| formal_cpu_acceptance | `e8d0234e2905aa625c930ca630db67fc4b915b8d343e2863365a1efd17496bb6` |
| captured_matrix | `47281f215168f52982eebc58bde1a7df14ecba496fd2215de40837e47f728116` |
| first_three_review | `3eead1fce4b41427fb6d7a6422b3dffec20e77f44271262809afec9d3ea75e3a` |
| first_three_readset | `f308374c1d041e43b3f2da656ca65dbc5c485c344e51e5b03d2222eda095a787` |
| first_three_protection | `989b72e5b871ecf069f8d5a1194d36c9f911d6bbb5f9413350b2add4733f3275` |
| last_two_global_review | `ea004849bd40120a4534b062b6793044a556c4dae38edb96fe6e65f213b6e622` |
| last_two_global_summary | `28d2189f6bfba0cb2b98b42814d02eafc07247974d1c2ac927d9ac6094c70f2d` |
| last_two_global_readset_index | `14737bd33afea3655a79d05589b4064f5ac040936b8f784bed29122d45a64e2d` |
| full_global_readset | `e1d85505d9e0e168097fe38858755d309b8be3239f7b6c18a0ee01411ff20b3b` |
| source_binding | `b10f3b74952a9529e4d03adbebd717d68dd9c8caecd8447ec34a9b6226045542` |
| documentation_only_bridge | `bd70a96b1e731c6fc7b41760cb52a4c702ce9b9c7ac86170b9fba2a9c784dbf5` |
| research_distribution_baseline | `31ab1d761698268075feda2560cf63edde667a76106d80d9433945b337ca9923` |
| originals_before | `30e7f8802573e66aff02371e5cd58ee4b5a3284016a85ff9411055365ce634d6` |
| originals_after | `30e7f8802573e66aff02371e5cd58ee4b5a3284016a85ff9411055365ce634d6` |
| environment_before | `f7c09ff377f0f2eb4e31440f9f22539bbeb6dafde81b19262d6058988ad899d4` |
| environment_after | `f3c3d58adbe53090b9eae39cfda7b029d2480b1b85d178373420bd1976c32c31` |
| quality | `70165798e4660d7bae1e12513fd4fcea46d711f5b9621cdb24f180e9c94e0a90` |
| fresh_base | `d8767be27487a6548b80789290532d3f44feafb052e25323a977cbce18fa22a1` |
| installation_identity | `fd17e6aeaf602e71aab5df64202b0246558084efa9e1209c8e2270ef0bc00a8a` |

前三项目独立审阅覆盖24个主导出、24个guard及额外6个成功guard原生比较；末两项目覆盖16个主导出、16个guard及额外4个原生比较，同时闭合五个预览及全局链。最终质量门24项、6,666项测试与fresh Base的50命令/31检查/10份完整JSON比较沿用同代码候选的原始收据；便携文稿生成不重跑产品。

## 独立资源边界

模型权重与数据资源预检、GPU推理/训练、认证或门控模型访问、付费discover/judge、第二Agent宿主及新文稿的真实宿主验收各有独立证据和授权范围，不包含在本CPU结果中。本文生成只读取既有证据，没有执行产品、Git、网络、凭据读取或模型/GPU操作。
