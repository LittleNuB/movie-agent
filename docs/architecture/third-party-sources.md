# 第三方研究与代码复用来源

**日期：** 2026-09-06。以下版本与观察来自已迁入的研究记录。本次初始化未下载、复制或执行这些项目的应用代码，未锁定运行依赖，也未选择本项目的开源许可证。

| 项目 | 研究定位 | 已记录版本／出处 | 后续处理 |
|---|---|---|---|
| ViMax | 电影领域代码起点 | [05a48943878312d88fe5a016c12a9654940ecc43](https://github.com/HKUDS/ViMax/tree/05a48943878312d88fe5a016c12a9654940ecc43) | 逐项评审故事、剧本、资产、镜头模块；运行时可替换 |
| AdCraft | 交互、资产与版本参考 | [08cf7e6c90154e5675747214b2f4bf99459dac33](https://github.com/GML-MMGroup/AdCraft/tree/08cf7e6c90154e5675747214b2f4bf99459dac33) | 区分广告专用结构与可迁移能力 |
| OpenMontage | 工具与技能组织参考 | [cd9f3c1f03368be87b140af494914b8ee4e3c7a4](https://github.com/calesthio/OpenMontage/tree/cd9f3c1f03368be87b140af494914b8ee4e3c7a4) | 不把宿主能力直接写成本产品已实现 |
| AgentScope | 首选运行框架 | [2.0.7.post1](https://pypi.org/project/agentscope/2.0.7.post1/)；研究对应源码标签 e90f1c7592896cc95f6e5ee506194f533378247d | 锁定依赖和实际接入时重新验证需求与兼容性 |
| LangGraph | 框架备选 | [官方文档](https://docs.langchain.com/oss/python/langgraph/overview) | 仅在首选路线关键能力不满足时重新评审 |
| Pi／DSH | 个人部署的使用形态参考 | [Pi](https://github.com/earendil-works/pi)、[DSH](https://github.com/deepseek-ai/deepseek-harness) | 不因此改变已选电影运行框架 |

引入代码时新增具体模块、版本、来源链接、许可证、所需声明、修改说明和实际测试结果。当前只列出研究出处，不把未核对的许可写成已确认事实。

项目自己的视觉参考由此前会话的内置 imagegen 生成并经用户审阅；复制到本仓库时保留原图并核对哈希。它是静态 UI 示意，C 被否决，画面中的影片不是生成能力证明。

更多来源与观察见[架构研究](./architecture-review-2026-09-05.md)、[创作交互来源](../product/creative-interaction.md)和[历史资料](../archive/README.md)。
