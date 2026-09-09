# Movie Agent · 文档索引

**更新：** 2026-09-09。以下为新项目的阅读入口。已接入真实导演、媒体生成和版本修改，并按反馈完善前端；前期制作与参考工程已确认并进入实施，完整电影质量与验证矩阵仍未通过，实际状态以验证记录为准。

## 当前规格

| 文档 | 阅读目的 |
|---|---|
| [根设计入口](../DESIGN.md) | 快速理解已确认方向与剩余问题 |
| [产品规格](./product/product-spec.md) | 目标用户、电影范围、创作修改与交付 |
| [创作交互](./product/creative-interaction.md) | 提案、剧本、视觉、试拍、声音与 annotation |
| [前端规格](./product/frontend-spec.md) | 三栏、主题、编辑审核、项目与版本、Windows 部署及配置 |
| [模型与 API 设置](./product/model-settings.md) | 通用连接、用户自选模型与用途，产品默认不指定模型 |
| [技术基线](./architecture/technical-baseline.md) | AgentScope 路线、职责试验、模型与程序分工、待接入事项 |
| [架构研究记录](./architecture/architecture-review-2026-09-05.md) | 源码版本、可吸收能力及尚未证明的能力 |
| [第三方来源](./architecture/third-party-sources.md) | 研究与后续代码复用的来源边界 |
| [统一术语](../CONTEXT.md) | 电影、任务、素材、授权和版本的概念 |
| [ADR 索引](./adr/README.md) | 已确认的持续性决定 |

## 执行与验证

| 文档 | 状态与用途 |
|---|---|
| [公开源码与预览发行](./adr/0009-public-source-release.md)及[发布检查](./validation/public-release-2026-09-09.md) | 当前源码采用 MIT 公开；源码包、运行方式与质量边界见根 README，旧私有建仓记录作为历史保留 |
| [Logo与UI视觉优化](./plans/ui-visual-polish.md) | 03「显影」已接入；方案已接受，第一批欢迎页与对话区已实现，见[检查与限制](./validation/ui-visual-batch1-2026-09-09.md)；待人评与后续批次 |
| [任务记录](./agents/issue-tracker.md) | 本地文档任务入口，不自动创建 GitHub Issues |
| [可点击原型规格](./plans/clickable-prototype.md) | 已实现；2026-09-06 用户暂定通过 UI |
| [能力建设范围](./plans/capability-mvp.md) | 已获实施授权，真实电影创作与修改 MVP 进行中 |
| [前期制作能力规格](./plans/preproduction-quality.md)与[决定](./adr/0007-preproduction-and-reference-engineering.md) | 剧本制作说明、参考依赖、镜头输入、分镜预演；已确认，工程与真实收益分别验证 |
| [前期制作首批检查](./validation/preproduction-quality-2026-09-09.md) | Q1—Q3工具、版本与引用检查、隔离浏览器及审查；没有新增真实模型生成 |
| [前期制作真实验证与预演](./validation/preproduction-live-2026-09-09.md) | 同日后续真实导演、参考派生、有声预演、参数修复与质量缺口；按阶段保留真实证据 |
| [实施进度](./plans/runtime-implementation.md) | 代码、真实接入与阶段交付状态 |
| [Windows 运行指南](./runtime-guide.md) | 4318 真实服务、模型设置与恢复 |
| [对话工作区体验](./plans/frontend-experience.md)及[验收](./validation/frontend-experience-2026-09-08.md) | 真实活动、历史原文、草稿、输入保留与资产浏览 |
| [对话专属资产库验收](./validation/conversation-assets-2026-09-08.md) | 当前对话的中间产物集中收录、分类和搜索；完整任务移入运行记录 |
| [用户反馈汇总](./validation/feedback-round-2026-09-08.md)及[中立走查](./validation/neutral-walkthrough-2026-09-08.md) | 原始质量问题、独立审查证据与剩余缺口 |
| [真实运行证据](./validation/runtime-evidence-2026-09-06.md) | 真实产物、24 个 LLM 用例、控制与浏览器检查、尚未完成项 |
| [原型浏览器检查](./validation/clickable-prototype-2026-09-06.md) | 实际桌面交互结果与示例能力限制 |
| [首轮验证矩阵](./validation/first-round-matrix.md) | 七组二十一个场景族，范围已确认，执行中 |
| [历史模型基础接入](./validation/provider-preflight-2026-09-06.md) | 旧工作区 GLM 工具回传成功、媒体只读查询成功；不代表本仓库通过 |
| [仓库初始化验收](./validation/repository-initialization-2026-09-06.md) | 本次文档、来源保护和提交检查的实际结果 |
| [配置示例](../.env.example) | 不含凭据，目前无运行程序加载 |

原型验收、真实 LLM 行为、媒体质量与整片人评分别给出结论，不互相替代。

## 研究历史与迁移

- [生成质量深度研究（2026-09-09）](./research/generation-quality-2026-09-09/report.html)：原研究快照，研究当轮未修改产品或发起生成；后续接受的选择见ADR 0007，不能将全文所有候选方案视为已批准实现。
- [迁移记录](./provenance/source-migration.md)：来源、文件对应、修订与未迁入内容。
- [来源清单](./provenance/source-manifest.json)：原工作树文件哈希与目标文件映射。
- [历史资料索引](./archive/README.md)：早期论证和读者检查，包含已被替代的假设。
- [视觉参考](./assets/frontend-theme-comparison-2026-09-06.png)：A 日间、B 夜间已选；原始对照图中的 C 已否决。

研究中的模型、价格和赛事信息按原日期与来源理解。新调用、集成或提交应记录新的实际证据，不能把引用历史研究当作本次验证。
