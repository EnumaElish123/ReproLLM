# 向 D01 / A01-B 交付的证据合同

本交付对应 R04-A / R04-B 已接受的 R04-S；工程验证结果由同目录会话报告
绑定最终源码。此文只定义后续 recipe 应如何引用证据，不宣称真实资源矩阵关闭。

| 证据 | 主体 / 阶段 | 可支持的结论 | 消费验证仍需 |
|---|---|---|---|
| lock.environment | 已确认 producer 的 recorder / lock_resolution | 解析时可见版本；与兼容 recorder run 事实比较 | child 实际解释器和安装元数据 |
| run.environment.python / packages | recorder / post_child | 结束后 recorder 的版本集合 | child/parser 独立回执；不能从空集合推出 child 没装包 |
| run OS / hardware | host / post_child | collector 可见宿主/硬件 | 远端、容器或 launcher 的实际执行证据 |
| run inherited env、scheduler、hostname hash | inherited_environment 或 host / pre_child | 启动前继承基础；hostname hash 不是结束后重新观测 | child 内部改写和二次 launcher 的证据 |
| run v2 manifest / lock / files / config bindings | input_file / pre_child | 原始启动前指纹与观察值 | child/parser/request 独立读取的值或指纹 |
| run v2 input_capture.after / change | input_file / post_child | 冻结候选路径结束后是否变化、消失、新建或不可判断 | unchanged 也不能证明被消费 |
| outputs | child 结束后 | 输出路径、原始指纹和大小 | 输出内容是否对应声明任务的独立依据 |
| legacy run v1 config / files | input_file / unknown | 旧记录保留的观察值和指纹 | 不把它迁移成 pre_child 或 child-consumed |

受控工程回归用 child 自己写出的消费值/输入 SHA 作为独立依据，再与 recorder
基线和 post-child checks 比较。A01-B 原生推理/训练以及 D01 的实际请求参数，
必须在自己的资源验证中保存相应 child/parser/request 证据并定位 run/path。
两侧 State 相等或语义 diff 正确不能替代 snapshot 保真核对；VAL-R01 原有
快照保真缺陷保持阻塞，等值损坏不算成功。H2 与 LlamaFactory 的既有资源
证据状态保持原记录，不把本会话 stdlib 回归当成额外 GPU/API PASS。
