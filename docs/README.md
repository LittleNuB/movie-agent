# Movie Agent · 文档索引

**更新：** 2026-09-06。以下为新项目的阅读入口。main 保留文档、配置示例与静态视觉参考；独立分支已实现可点击原型，电影运行能力和真实验证尚未完成。

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
| [任务记录](./agents/issue-tracker.md) | 本地文档任务入口，不自动创建 GitHub Issues |
| [可点击原型规格](./plans/clickable-prototype.md) | 独立分支已交付；浏览器检查通过，用户体验审阅待完成 |
| [首轮验证矩阵](./validation/first-round-matrix.md) | 七组二十一个场景族，范围已确认，全部待执行 |
| [历史模型基础接入](./validation/provider-preflight-2026-09-06.md) | 旧工作区 GLM 工具回传成功、媒体只读查询成功；不代表本仓库通过 |
| [仓库初始化验收](./validation/repository-initialization-2026-09-06.md) | 本次文档、来源保护和提交检查的实际结果 |
| [配置示例](../.env.example) | 不含凭据，目前无运行程序加载 |

原型验收、真实 LLM 行为、媒体质量与整片人评分别给出结论，不互相替代。

## 研究历史与迁移

- [迁移记录](./provenance/source-migration.md)：来源、文件对应、修订与未迁入内容。
- [来源清单](./provenance/source-manifest.json)：原工作树文件哈希与目标文件映射。
- [历史资料索引](./archive/README.md)：早期论证和读者检查，包含已被替代的假设。
- [视觉参考](./assets/frontend-theme-comparison-2026-09-06.png)：A 日间、B 夜间已选；原始对照图中的 C 已否决。

研究中的模型、价格和赛事信息按原日期与来源理解。新调用、集成或提交应记录新的实际证据，不能把引用历史研究当作本次验证。
