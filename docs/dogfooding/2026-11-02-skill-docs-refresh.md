# SK21 文稿跟进：当前入口与剩余工作

日期：2026-11-02。起点：`b526d6ed1d74456e2175bdd880ab134d866e3995`。
维护者要求确认 Skill 剩余任务，并按当前进度更新 README 和使用文档。

## 交付范围

- [README](../../README.md)和[文档索引](../index.md)增加 Skill 自然语言入口、保存命令后的短流程及发布版／源码区别。
- [Skill 状态页](../skill-status.md)集中列出已实现任务、支持范围、实际验证和剩余事项。
- [Agent 安装教程](../tutorials/agent-skill.md)给出已验证固定提交；[CLI 初次使用](../tutorials/first-experiment.md)、
  [运行](../run.md)、[声明](../manifest.md)、[FAQ](../faq.md)和[安装验证](../distribution.md)补齐导航与实际操作边界。
- [交付状态](../community/roadmap.md)更新可靠性、易用性与 Skill 进度，移除旧 Llama-2／缺失 manifest 作为当前前置阻塞的说法。
- 原样加入已交付 `b526d6e` 的[五项 CI 收据](2026-11-02-skill-final-ci-correction/evidence/delivery-ci.json)，
  不改写历史失败或原报告提交时的 pending 快照。

SK10–SK21 无尚未实现代码项。认证 metadata、正式 discover 和正式 judge A/B 三项补验仍为
`BLOCKED_NOT_AUTHORIZED`；Claude Code 为 `DEFERRED_BY_MAINTAINER`，外部试用为 `UNOBSERVED`。
MCP、PyPI／Skill 市场发布及对外联系不属于本轮。没有读取新凭据或执行付费请求。

## 本轮检查与证据边界

按[验证工作流 §3](../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义)执行文稿会话：
核对相对链接／锚点、CLI 帮助中的实际选项、便携收据身份与源文件不变。
575 个产品、测试、schema、CI 和生成器输入逐字节保持；生成文档本体未修改，
没有受影响生成器需要重建。CLI 帮助检查不执行实验或 provider 请求。

本轮完整产品质量门、Gate A 和 Gate B 均为 `NOT_APPLICABLE_DOCUMENTATION_ONLY`，
不声称重新运行 6,731 tests 或 GPU 矩阵。之前的质量、GPU、安装和宿主结果保留其原候选及范围。
当前文稿交付的确切 head CI 在提交推送后核对，不预写为 PASS。

PyPI 公开 JSON 于 2026-11-02 返回版本 0.6.1，与
[发布页面](https://github.com/EnumaElish123/ReproLLM/releases)一致；源码仍为未发布 0.7.0／run schema 2。
此检查没有安装包或发布版本。可见入口与维护者验收材料分别维护，
用户不需要先构建候选 wheel 或手工编写适配器 JSON 才能使用 Skill。

维护者已有 README／文档索引的补充段落和七份未跟踪试用材料保留；只暂存本轮新增文稿差异，
不把原有未提交材料纳入提交。
