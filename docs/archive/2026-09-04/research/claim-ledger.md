> 历史材料：迁自旧工作区。保留当时的判断与验证范围；其中被后续决定取代的内容不得作为新项目指令。迁移仅增加此提示并修复本地链接，来源见[迁移记录](../../../provenance/source-migration.md)。

# AI 电影 Agent 调研主张—来源台账

**访问日期：** 2026-09-04
**说明：** 优先记录一手技术文档、论文与源代码。GitHub README 中的能力声明仅代表项目自述；已对 OpenDirector、Butterfly Director AI 的关键编排源码做额外核对。

**用户决定与外部证据分离：** 2026-09-04 用户接受 60–90 秒，并否决将单主角、单空间、单异常作为产品范围；该组合只属于一个测试用例。外部选题建议与模型风险经验不能覆盖这个决定。其余方案建议不因此获得批准。

| ID | 支撑主张 | 来源与机构 | 日期 | URL | 备注 |
|---|---|---|---|---|---|
| S01 | 比赛主题、赛程、Agent 评分、提交物、版权要求 | AI+∞ 开发者创作大赛，ModelScope × Qoder | 2026 | https://modelscope.cn/active/AIstudio | 动态页面，逐项展开本期赛题、日程、奖项、评选、指南、须知 |
| S02 | Studio 类型、Docker 7860、Secrets、Git 同步、持久目录 | ModelScope Studio 官方 Skill/文档 | 2026-06-29 验证 | https://modelscope.cn/skills/modelscope/modelscope-studio | 默认数据重启丢失，`/mnt/workspace` 持久；Docker 需账号绑定与实名 |
| S03 | xGPU 动态调度、免费测试与时长限制 | ModelScope xGPU 文档 | 2026 | https://modelscope.cn/docs/studios/xGPU | 需申请组织，空闲会暂停 |
| S04 | DGX Spark ARM64、128GB 统一内存、CUDA/Docker | NVIDIA DGX Spark User/Porting Guide | 2026-08 | https://docs.nvidia.com/dgx/dgx-spark/system-overview.html | 需验证第三方 CUDA 扩展的 ARM64 兼容 |
| S05 | DGX Spark 官方 ComfyUI 视频工作流 | NVIDIA Build | 2026-08-04 | https://build.nvidia.com/spark | 覆盖 Wan、HunyuanVideo 等本地视频生成 |
| S06 | 电影剧组角色、多阶段协作、Critique-Correct-Verify | FilmAgent，Xu et al. | 2025-01-22 | https://arxiv.org/abs/2501.12909 | 3D 虚拟空间研究原型，环境和动作空间受限 |
| S07 | 分层场景/镜头规划、人物一致与长视频 | MovieAgent，Wu et al. | 2025-03-10 | https://arxiv.org/abs/2503.07314 | 代码需预先脚本与角色库，部分模型/LoRA 手工配置 |
| S08 | 镜头语言 RAG、粗剪/精剪、观众反馈、分轨声音、OTIO | FilMaster，Huang et al. | 2025-06-23；ICLR 2026 | https://arxiv.org/html/2506.18899 | 与本项目质量根因最直接对应 |
| S09 | Explore-Examine-Enhance、有约束的可生成脚本、每镜单动作 | MAViS，Wang et al.，EACL 2026 | 2026-03 | https://aclanthology.org/2026.eacl-long.101/ | 同时给出成本/时延与迭代消融 |
| S10 | 分层图、按需上下文、有界回边优于扁平编排的初步证据 | Hollywood Town / OmniAgent | 2025-10-25 | https://arxiv.org/abs/2510.22431 | 样本仅 3 个提示，专家仅 4 人，应限制外推 |
| S11 | 视觉锚点对人物一致性的必要性 | Lights, Camera, Consistency | 2025-12-17 | https://arxiv.org/abs/2512.16954 | 消融显示无锚点时人物一致性大幅下降 |
| S12 | 电影级评价三轴、镜头语言、动态美学与多镜头瓶颈 | FilmBench，Wang et al. | 2026-07-29 v2 | https://arxiv.org/html/2607.24241v2 | 与北京电影学院/专业片场共建；仍是新近预印本 |
| S13 | FilmOps 六类电影语言算子与许可 | Neo-yk/FilmOps | 2026-07-28 | https://github.com/Neo-yk/FilmOps | 代码 Apache-2.0，部分模型权重有单独限制 |
| S14 | 分检查点评价、跨镜转场是共同低分项 | DirectorBench，Chen et al. | 2026-05-28 | https://arxiv.org/abs/2605.30090 | 新近预印本；14 人验证，适合作为诊断框架而非最终真理 |
| S15 | VBench 通用视频质量维度 | VBench，CVPR 2024 | 2024 | https://github.com/Vchitect/VBench | 可做底层画质门禁，不能替代电影级人评 |
| S16 | 多 Agent 的规范、错位、验证、终止失败 | Why Do Multi-Agent LLM Systems Fail? | 2025-03-17 | https://arxiv.org/abs/2503.13657 | 150+ 任务、14 类失败模式 |
| S17 | AgentScope 的工作流、状态、追踪、评价能力 | AgentScope，Alibaba | 当前文档 | https://doc.agentscope.io/ | Python 生态；迁移现有 TS 成本高 |
| S18 | LangGraph JS 的持久检查点、恢复与中断 | LangChain 官方文档 | 当前文档 | https://docs.langchain.com/oss/javascript/langgraph/persistence | 可用 SQLite Saver，但引入会形成第二套状态源 |
| S19 | Pi SDK 会话、工具、扩展与分支；无内置沙箱 | Pi 官方文档 | 当前文档 | https://pi.dev/docs/latest/sdk | https://pi.dev/docs/latest/security |
| S20 | OpenDirector 的九角色自述与实际内存检查点、图像/音频 Runner | seme-org/open-director | 2026-05-29 最后推送 | https://github.com/seme-org/open-director | 源码检查显示主媒体任务类型不含视频生成，适合作为 UI/流水线参考而非成片基线 |
| S21 | Butterfly Director AI 的领域/版本设计与真实图编排差距 | abhijha8287/butterfly-director-ai | 2026-08-07 最后推送 | https://github.com/abhijha8287/butterfly-director-ai | 架构写 11 Agent；当前主图源码只串联前三个叙事 Agent |
| S22 | H3 多模态参考、原生视频音频、部署与许可 | MiniMax H3 官方发布 | 2026-08-03 | https://www.minimax.io/news/minimax-h3-open-source | 开源 Context-IR 不完整；官方完整预处理仍是托管服务 |
| S23 | H3 API 输入组合、异步任务、参考限制 | MiniMax API 文档 | 当前文档 | https://platform.minimax.io/docs/api-reference/video-generation-v2-create | 4–15 秒；768P/2K；最多 9 图、3 视频、3 音频参考 |
| S24 | H3 当前按秒价格 | MiniMax API 定价 | 2026-09-04 访问 | https://platform.minimax.io/docs/guides/pricing-paygo | 768P $0.08/s、2K $0.13/s、768→2K $0.05/s，价格可能变化 |
| S25 | Wan2.2 5B 的 720P、24GB、本地/ModelScope 和 Apache-2.0 | Wan-Video/Wan2.2 | 当前仓库 | https://github.com/Wan-Video/Wan2.2 | 14B 路径约需 80GB，5B 更适合回退 |
| S26 | HunyuanVideo 1.5 8.3B、最低 14GB、训练与 Diffusers | Tencent HunyuanVideo 1.5 | 2025-11 起 | https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5 | 适合备选探针，权重许可需单独复核 |
| S27 | LTX-2.5 原生多镜头音视频与 32GB+ 要求 | LTX 官方文档 | 2026-08 | https://docs.ltx.io/open-source-model/getting-started/overview | 新模型与社区许可，首发集成风险较高 |
| S28 | Qwen-Image-Edit-2511 的多人/人物一致编辑与 Apache-2.0 | Qwen 官方模型卡 | 2025-12 | https://huggingface.co/Qwen/Qwen-Image-Edit-2511 | 适合作为角色/场景锚点工具 |
| S29 | CosyVoice 3 多语、情感控制与 Apache-2.0 | FunAudioLLM/CosyVoice | 2025-12 | https://github.com/FunAudioLLM/CosyVoice | 声音克隆仍需用户权利与同意 |
| S30 | ACE-Step 音乐生成能力与许可 | ace-step/ACE-Step、ACE-Step 1.5 | 2026-01-28 | https://ace-step.github.io/ACE-Step-1.5/ | 1.5 项目页称 MIT；旧主仓为 Apache-2.0，采用时锁定具体版本和许可文件 |
| S31 | OTIO 的剪辑交换范围与成熟度 | Academy Software Foundation | 当前文档 | https://opentimelineio.readthedocs.io/en/latest/ | 只表达剪辑数据和外部媒体引用，不是媒体容器或渲染器 |
| S32 | 科幻以大观念/希望恐惧为核心，声音和低成本效果的重要性 | British Film Institute | 多篇 | https://www.bfi.org.uk/bfi-distribution/bfi-international-distribution/touring-programmes/sci-fi-days-fear-wonder | https://www.bfi.org.uk/bfi-film-academy-opportunities-young-creatives/bfi-film-academy-how-do-i-work-film-television-industries/create-sci-fi-effects-budget |
| S33 | 短片应按所需长度讲述，不塞满长片结构；开场抓人，配乐服务叙事 | Sundance Institute | 2022 | https://www.sundance.org/blogs/pep-talks-and-advice-for-makers-of-short-films-from-our-sundance-programmers/ | 专业经验建议，不是实验性定律 |
| S34 | 镜头选择、构图、视点、运动应服务信息/情绪/叙事 | Sundance Collab | 当前课程纲要 | https://collab.sundance.org/catalog/Visual-Storytelling-The-Shot-The-Camera-On-Demand | 课程正文付费，仅使用公开纲要 |

## 本地证据

- `README.md` 与 `docs/status/project-handoff-2026-09-03.md`：当前 v0.4 Ticket 01–19 状态及方向调整。
- `.scratch/video-post-agent-v0.4/current-video-quality-root-cause.md`：固定模板、单帧审查、声音/调色/整片观看缺口。
- `server/v2/runtime.ts`、`server/v2/project-repository.ts`：成熟但过大的持久运行与仓储实现。
- `server/v2/local-pi-creative-agent.ts`、`server/v2/local-creative-workspace.ts`：本地 Pi、检查点、工具和授权门。
- `server/v2/first-cut-producer.ts`：三模板和单帧 before/after 路径，证明旧制作合同不适合一句话电影生成。
- `shared/creative-plan-contract.ts`、`shared/edit-patch-contract.ts`、`shared/review-contract.ts`、`shared/creative-run-metrics.ts`：可复用的严格合同、可撤销修改、审查和指标基础。
