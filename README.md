# Movie Agent

面向 AIGC 零基础用户的个人电影创作 Agent。通过自然语言、多轮共创或明确授权的托管，把一个想法拍成可继续修改的 90–120 秒科幻短片。

首版计划支持 Windows 本地个人部署，通过浏览器使用。Agent、项目和版本保存在本机，模型推理与媒体生成调用云端 API；用户自行准备模型 API Key，通过设置页配置和检查连接。

产品不预设厂商或模型。设置采用“服务连接 → 模型 ID → 用途分配”；此前选定的 GLM、H3、Seedream、Seedance 是所有者个人使用与验证组合。详见[模型与 API 设置](./docs/product/model-settings.md)。

## 当前状态

文档初始化已完成。main 保留设计与任务记录；可点击原型已经制作，代码独立保存在 [prototype/film-creation 分支](https://github.com/LittleNuB/movie-agent/tree/prototype/film-creation)。电影 Agent 运行时、真实生成与安装包尚未实现。

| 项目 | 状态 |
|---|---|
| 产品、交互、Windows 本地部署方向 | 已确认，具体行为见设计文档 |
| AgentScope 首选框架与电影领域复用方向 | 已确认方向，实际集成待验证 |
| 前端视觉 | A 日间、B 夜间已选定；静态示意图不代表可运行产品 |
| 可点击原型 | 独立分支已实现；2026-09-06 用户暂定通过 UI，浏览器检查单独记录 |
| 真实模型基础接入 | 旧工作区完成 GLM 工具回传与媒体只读查询；不是本仓库实测 |
| 电影制作与质量验证 | 未实现，七组二十一个场景族尚未执行 |

约 30 分钟得到首条完整可看片、约 150–220 元/片均为未实测的目标预期，不是硬停止条件。电影质感参考《星际穿越》《挽救计划》《流浪地球2》，不宣称达到相同制作水准。

## 从这里阅读

- [开发助手规则](./AGENTS.md)：进入本仓库工作的方式。
- [设计入口](./DESIGN.md)：当前已确认方向与剩余问题。
- [项目术语](./CONTEXT.md)：统一理解剧本、素材、版本和授权。
- [完整文档索引](./docs/README.md)：产品、架构、验证、研究与决定。
- [可点击原型](./docs/plans/clickable-prototype.md)：已批准范围、交付分支与下一步。
- [下一轮能力建设](./docs/plans/capability-mvp.md)：真实导演、声画生成、成片和修改；已登记，尚未开始。
- [原型启动与体验](https://github.com/LittleNuB/movie-agent/blob/prototype/film-creation/prototype/README.md)：切换到原型分支后，按说明在本机运行。
- [浏览器检查与截图](https://github.com/LittleNuB/movie-agent/blob/prototype/film-creation/docs/validation/clickable-prototype-2026-09-06.md)：示例交互证据，不代表真实电影能力。
- [配置示例](./.env.example)：未来接入所需配置的说明，当前没有读取它的运行程序。

## 仓库边界

本仓库独立于历史后期工程。当前工作树中的电影设计与研究经过整理迁入，来源见[迁移记录](./docs/provenance/source-migration.md)。旧工程代码、Git 历史、实际项目数据、密钥和个人配置均未迁入。

ViMax 是已选择的电影领域代码起点；其运行时可替换。AdCraft 与 OpenMontage 提供可吸收的交互、资产、版本及工具组织思路。本次仅整理文档，没有导入第三方应用代码。后续代码使用须记录具体来源和许可，见[第三方来源](./docs/architecture/third-party-sources.md)。

GitHub 仓库为私有。当前尚未选定本项目的开源许可证；私有仓库初始化不代表公开发布或参赛提交。
