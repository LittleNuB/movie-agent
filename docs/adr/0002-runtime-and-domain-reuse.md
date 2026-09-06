# ADR 0002 · 运行框架与电影领域复用

Status: Accepted

Date: 2026-09-06

## 决定

- 主导演持续承接用户对话，按需委派专业 Agent，后台执行已授权的媒体任务。
- AgentScope 2.0 为首选框架；若实际关键能力不满足，再评审 LangGraph。研究版本不等于已锁定并验证的运行依赖。
- ViMax 是电影领域代码起点，具体领域模块、AgentLoop、Pipeline 和运行时均可按需求替换。
- 吸收 AdCraft 的交互、资产与版本设计，以及 OpenMontage 的工具与技能组织，逐项核对实际价值与许可。
- 不固定七 Agent；四角色为试验基线，按证据拆分合并，并在选定任务上与单 Agent 对照。
- 新电影项目可以舍弃旧后期工程，不要求保留 Pi 或向后兼容。

## 责任与限制

模型判断意图、创作方案、生成路径及修改影响。程序保证消息、授权、任务状态、产物身份和版本关系可靠；不固化所有创作分支。

本次未导入第三方运行代码，也未建立电影运行时。具体 API、Schema、持久化、恢复机制、角色数量和依赖锁定留待实现设计与真实验证。Pi／DSH 的个人部署类比不构成改换底层框架的决定。

依据：[技术基线](../architecture/technical-baseline.md)、[架构研究](../architecture/architecture-review-2026-09-05.md)、[第三方来源](../architecture/third-party-sources.md)。
