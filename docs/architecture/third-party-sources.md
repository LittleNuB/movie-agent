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

## 交互原型来源补充

`prototype/film-creation` 分支使用自行编写的 HTML、CSS、JavaScript 和 Node.js 内置静态服务，没有第三方 npm 运行依赖，未复制参考项目的应用代码。界面依据本项目 A／B 静态参考重新实现，C 不采用。图标为自行编写的简单路径，动态画面与低鸣分别由 Canvas、Web Audio 原创构造；未使用三部参考电影的画面或音乐。

浏览器验收使用本机已安装的 Python Playwright 工具与 Chromium，工具及其浏览器二进制不随仓库提交。该测试依赖与最终产品依赖分开；没有因原型选择新增本项目开源许可证。

更多来源与观察见[架构研究](./architecture-review-2026-09-05.md)、[创作交互来源](../product/creative-interaction.md)和[历史资料](../archive/README.md)。

## 2026-09-09 前期制作复用决定

[生成质量研究](../research/generation-quality-2026-09-09/report.html)核对了上述三个固定版本。ViMax为MIT；AdCraft为个人及非商业许可，不能默认商用；OpenMontage为AGPL-3.0。许可原文入口位于报告第6节，复制实现或文档时仍须记录具体来源和声明。

按[ADR 0007](../adr/0007-preproduction-and-reference-engineering.md)优先复用ViMax人物派生、选参考和镜头分解方法；吸收AdCraft的父资产与状态关系、OpenMontage的镜头意图和输入编译思路。DOC／Re³用于分层事件与相关上下文的方法参考。GroundShot为有条件的研究证据，未确认可直接引入的公开代码包。当前决定不导入它们的整套运行时，也不选择新的本项目许可证。

## 2026-09-09 公开源码补充

后续发布授权见 [ADR 0009](../adr/0009-public-source-release.md)，项目现采用 [MIT](../../LICENSE)。这一选择取代上文当时的本项目许可待定状态；第三方许可、具体改写来源与依赖边界继续按[当前来源声明](../../third_party/README.md)保留。
