# Movie Agent · 设计入口

**更新：** 2026-09-09。已接入真实电影运行链路并完善对话工作区，完整电影质量仍未通过。用户已确认前期制作与参考工程方向，当前按[实施规格](./docs/plans/preproduction-quality.md)推进；原 MVP 证据和剩余项见[实施记录](./docs/plans/runtime-implementation.md)。

## 已确认方向

- 为 AIGC 零基础用户，以自然语言和多轮对话从无素材的想法创作 90–120 秒科幻电影。
- 首版 Windows 本地个人部署，浏览器使用；用户自备模型 API Key，设置页引导配置与连接检查。
- 仅保留共创（默认）、托管两种模式，支持项目内切换；关键审核遵循实际授权，持续展示真实进展。声音／部分托管已取消，见 [ADR 0008](./docs/adr/0008-two-creation-modes.md)。
- 故事提案包含完整故事和结尾；正式剧本可手动编辑。保存不触发制作，明确提交后先理解并按授权执行。
- 共享参考资产，按镜头选生成路径；视觉审核、代表性试拍、连续声画、声音修改与局部补拍服务故事。
- 采用剧本形成绑定版本的制作说明，记录因果、动机、状态与镜头表达；建立人物／场景／道具参考及派生关系，按模型和镜头选择输入，不固定三视图；随后用带临时声音的分镜预演检查表达。详见 [ADR 0007](./docs/adr/0007-preproduction-and-reference-engineering.md)，研究收益不算当前能力已通过。
- 对话为主，左侧项目列表，右侧可开合的多标签作品页，每次显示一个内容；A 日间、B 夜间，C 不采用。
- 品牌标志采用Logo候选03「显影」，已接入SVG；此编号属于Logo探索，与早期主题编号无关。具体接入见[视觉任务](./docs/plans/ui-visual-polish.md)。
- 视频时间点标注回到输入框，支持单条或批量发送，绑定具体视频版本；历史作品可查看与继续修改。
- 制作期间随时发消息，独立中止按钮；异常正常输出文字。页面关闭时本地服务仍运行则已授权制作继续，审核仍等待用户。
- AgentScope 为首选框架；主导演持续对话、专业 Agent 按需协作、后台工具执行。四角色仅为比较基线，最终数量待验证。
- ViMax 为电影领域代码起点，具体模块和运行时可替换；吸收 AdCraft 与 OpenMontage 的相应能力，允许舍弃旧工程。
- 产品不预设服务商或模型；用户通过连接、模型 ID 和用途分配配置。GLM 5.3 Flash、Seedream 5.0 Pro、H3 与 Seedance 2.0 是所有者个人使用及验证选择，详见 [ADR 0004](./docs/adr/0004-user-configured-models.md)。
- 后续 H3 生成 768P，个人 Seedance 选择改为 2.0 Fast、生成 720P；成片统一导出 720P。已有素材保留并本地转换复用。此项替代初始 1080p 输出及随后统一 720P 生成要求，见 [ADR 0006](./docs/adr/0006-provider-resolution-and-seedance-fast.md)。
- 约 30 分钟与费用预期均非硬门槛。剧本是否有趣由人判断，正式评分属于产品评测。

## 详细规格与证据

| 文档 | 负责范围 |
|---|---|
| [产品规格](./docs/product/product-spec.md) | 用户、目标、主流程、修改与交付 |
| [创作交互](./docs/product/creative-interaction.md) | 提案、剧本、视觉、试拍、标注与声音 |
| [前端规格](./docs/product/frontend-spec.md) | 页面、标签、模式、编辑审核、中止、部署与配置 |
| [模型与 API 设置](./docs/product/model-settings.md) | 用户自定义连接、模型与用途；个人选型与产品预设的边界 |
| [技术基线](./docs/architecture/technical-baseline.md) | 已选技术方向、模型／程序责任、待验证能力 |
| [前期制作能力](./docs/plans/preproduction-quality.md) | 制作说明、参考资产依赖、镜头输入编译、预演与对照验证 |
| [架构研究](./docs/architecture/architecture-review-2026-09-05.md) | 固定版本的源码观察与证据限制 |
| [验证矩阵](./docs/validation/first-round-matrix.md) | 七组二十一个场景族及真实证据要求 |
| [历史模型接入记录](./docs/validation/provider-preflight-2026-09-06.md) | 旧工作区已完成的最小检查及其限制 |
| [决策记录](./docs/adr/README.md) | 仓库、部署、架构、创作控制的已确认决定 |

## 下一项与未解决事项

2026-09-09 最新安排：优先[Logo与UI视觉优化](./docs/plans/ui-visual-polish.md)。03「显影」已选并接入，继续统一日间／夜间界面的视觉。前期制作质量工作及其未通过项继续保留。

当前[可点击原型](./docs/plans/clickable-prototype.md)保存在 `prototype/film-creation` 分支作交互参考。真实运行和对话资产库已有实现；[前期制作能力建设](./docs/plans/preproduction-quality.md)继续承接[真实电影 MVP](./docs/plans/capability-mvp.md)未通过的故事、参考和质量问题。文档接受、工程实现与真实成片验收分别报告。

当前实现采用 Python 3.12、AgentScope 2.0.7.post1、FastAPI、SQLite 与 FFmpeg，同源 REST／SSE，系统凭据管理器保存 Key。独立配音先用 MiniMax；配乐接口对当前验证账号不可用，替代接入待确定。最终角色数量、完整矩阵结论和安装分发仍未定。赛事条件与日程在交付前重新核验。

建仓阶段仅建立文档与配置示例，后续原型也未调用模型。过去提出的固定七 Agent、费用硬上限、必须保留旧 Pi 工程、外部剪辑工程强制导出均已撤回，不应从历史资料重新引入。
