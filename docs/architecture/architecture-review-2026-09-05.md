# 技术架构评审 · 架构形态与首选框架已确认

**日期：** 2026-09-05

**状态：** 所有者已明确接受“主导演＋按需专业子 Agent＋后台媒体任务”的架构形态，并接受以 AgentScope 2.0 为首选框架推进，发现关键能力不满足时再评审 LangGraph。最终角色划分、具体接入和版本锁定仍待完成。本次架构评审为源码与文档研究；2026-09-06 后续完成的 GLM 基础调用及媒体只读查询见[接入记录](../validation/provider-preflight-2026-09-06.md)，尚无框架运行或电影场景验证结论。

**产品依据：** [产品基线](../product/product-spec.md)、[交互决定](../product/creative-interaction.md)。

## 1. 已确认形态与待审建议

以 ViMax 作为电影领域代码起点，采用一个持续对接用户的主导演、按任务调用的专业子 Agent，以及独立于对话等待的后台媒体任务。共享项目中的剧本、参考素材和成片版本作为创作依据。

上述执行形态已获接受。四类逻辑职责仍是试验基线；按需启动、在一个后端中组织的具体方案继续评审，不将职责数量等同于进程或常驻模型数量。

已接受将 AgentScope 2.0 作为首选框架推进，LangGraph 保留为发现关键缺口后的备选。理由是已核对的 AgentScope 发布版存在与持续对话、团队委派和后台完成反馈直接相关的实现。首选路线的确认不表示真实效果或性能已经通过验证。

## 2. 从产品需要推导结构

| 产品需要 | 架构含义 |
|---|---|
| 共创、托管、插话和批量 annotation | 主 Agent 需要持续掌握意图、授权与新消息；媒体任务执行中也要能继续交互 |
| 统一电影风格和局部修改 | 长期依据保存在项目产物中；子 Agent 接收相关版本和任务上下文 |
| 图像、视频和声音生成等待较长 | 提交、查询、结果回报需要异步执行，不让一次完整生成调用占住整个对话轮次 |
| 连续性与声画检查 | 检查任务需要拿到相关媒体和剧情关系，产出可定位的证据与建议 |
| 用户修改方案由模型判断 | 模型选择委派、复用和修复方式；程序提供实际任务控制与版本校验 |
| 用户审核或授权跳过审核 | 审核记录对应具体产物版本和授权范围，不能只由提示词口头表示已批准 |

## 3. 四类逻辑职责建议

| 角色 | 主要工作 | 当前合并或拆分理由 |
|---|---|---|
| 主导演，含编剧职责 | 与用户对话、理解意图、提出故事与剧本、综合修改意见、委派与整合 | 先把用户意图与故事创作放在一起，减少传递损失；如长剧本挤占交互上下文，再依据验证考虑拆分 |
| 视觉制作子 Agent | 参考资产、人物／场景、镜头设计、图像和视频生成组织 | 这些任务共享大量视觉信息和一致性要求，先保持在同一专业职责中 |
| 后期子 Agent | 剪辑、对白、配乐、音效、字幕和动效，以及声画修改 | 剪辑节奏、声音时点与画面相互影响，先作为同一职责；声音是否独立拆出待验证 |
| 媒体与连续性检查子 Agent | 对单镜、跨镜及整片声画提出问题证据与修复建议 | 与生成任务区分上下文，便于发现遗漏；不承诺独立检查天然更准，不承担剧本有趣度的自动否决 |

图片生成、视频生成、TTS、混音和渲染由工具与后台任务承载。一次工具调用不因此成为独立 Agent。主导演可以直接完成简单任务，专业子 Agent 按需要参与。

本轮提出的是已有四角色试验基线的具体组织方式。最终数量仍要结合真实模型行为和比较结果决定。

## 4. 框架比较与证据

### AgentScope 2.0

本轮确认 PyPI 发布版为 2.0.7.post1，上传时间为 2026-08-28；核对了发布 wheel 中的 Python 源码，没有安装或执行该包。对应 Git 标签提交为 e90f1c7592896cc95f6e5ee506194f533378247d；主分支另观察到 41ba0216b3291b085d964bbf1c52d05a9b9d4c41。能力判断以发布包相关代码为主，不把两个版本混作同一快照。

已读到的实现：

- TeamCreate、AgentCreate、TeamSay 等团队工具可支持 leader／worker 组织。
- InboxMiddleware 在推理步骤开始前读取消息收件箱，注入上下文并发送界面事件。
- ToolOffloadMiddleware 可将超过等待阈值的工具执行转入后台，并让当前推理循环继续。
- BackgroundTaskManager 管理后台任务；结果通过收件箱和唤醒路径交回会话。
- ChatService 维护会话执行与状态保存，WakeupDispatcher 处理恢复和唤醒事件。

这些代码与所需交互结构相近。但后台任务仍保存 asyncio.Task，正常退出时会取消本地任务；注册记录或会话保存不等于媒体调用能跨进程自动恢复。ToolStop 调用本地取消或发送取消信号，也不能证明第三方生成服务已经停止。

参考：[发布包](https://pypi.org/project/agentscope/2.0.7.post1/)、[收件箱](https://github.com/agentscope-ai/agentscope/blob/e90f1c7592896cc95f6e5ee506194f533378247d/src/agentscope/app/middleware/_inbox_middleware.py)、[后台执行](https://github.com/agentscope-ai/agentscope/blob/e90f1c7592896cc95f6e5ee506194f533378247d/src/agentscope/app/middleware/_tool_offload_middleware.py)、[后台任务管理](https://github.com/agentscope-ai/agentscope/blob/e90f1c7592896cc95f6e5ee506194f533378247d/src/agentscope/app/_manager/_background_task_manager.py)。

本轮最初查到的 doc.agentscope.io 教程采用旧接口，只用于识别历史能力，不能作为 2.0 的完整能力上限。仓库指向 docs.agentscope.io 新站，部分页面本轮未能通过浏览工具打开，因此以发布源码补充核对。

### LangGraph

官方文档支持动态图式 Agent、检查点、子图和人工审核暂停。它可以承载模型自主选择工具，不必采用预写死的电影制作流程。

需要区分两类机制：

- OSS 库的 interrupt() 在应用指定位置暂停、等待输入；恢复时会重跑所在节点前部，因此副作用需要适当处理。
- Agent Server 的 double-texting 支持在运行期间收到新消息后中断、排队等策略；不能把这一服务层能力直接当成只安装 OSS 库就得到的应用功能。

LangGraph 的持久执行与子图是重要优势，但项目版本、第三方任务、消息入口和前端仍需接入。其图检查点与影片版本是不同概念，不能相互替代。

参考：[Agent 与 workflow](https://docs.langchain.com/oss/python/langgraph/workflows-agents)、[持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[审核中断与恢复](https://docs.langchain.com/oss/python/langgraph/interrupts)、[子图](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)、[Agent Server 的运行中插话](https://docs.langchain.com/langsmith/interrupt-concurrent)。

### 取舍结论

| 方案 | 本轮判断 | 尚需验证 |
|---|---|---|
| AgentScope 2.0 + 电影领域层 | 已接受的首选框架路线，已有会话服务、团队和后台反馈路径与产品需求接近 | 所需功能的集成负担、消息和审核行为、进程恢复、实际模型适配 |
| LangGraph + 应用服务 + 电影领域层 | 保留为备选，检查点与可组合子图有价值 | OSS 库与 Agent Server 采用范围，消息入口、后台任务和持久化的实际接入工作 |
| 原样使用 ViMax Runtime | 适合参考和复用，难以直接承载已确定的交互 | 逐轮消息入口、粗粒度生成工具和版本机制改造量 |
| 自研通用 Agent 框架 | 暂不建议作为本轮方向，优先复用现有能力 | 只有现成框架存在经过验证的关键缺口时，再评审定向自研 |

不建议为追求能力清单同时堆叠 AgentScope 与 LangGraph 两套顶层运行时。先验证一个主运行框架是否足够，再决定缺口补在哪层。

## 5. ViMax 的复用边界

已核对的 ViMax 版本为 05a48943878312d88fe5a016c12a9654940ecc43，包含故事开发、分场剧本、角色提取与设定、分镜、镜头分解、相机关系及逐镜生成等方法。

| 部分 | 本轮建议 |
|---|---|
| 故事、角色、分场与镜头等领域方法 | 作为复用候选，逐项调整到当前提案、剧本和审核要求 |
| 单张参考图、单镜头生成方法 | 拆成可独立调用的电影工具，并映射实际 Provider |
| 一次包办完整规划或整片生成的适配工具 | 不直接作为持续对话的唯一长工具，需要拆开任务提交与结果处理 |
| 原 AgentLoop、Web 消息桥与 SessionIndex | 不预设保留，按选定框架和影片版本要求替换或适配 |
| 原拼接与声音处理 | 可参考，不能直接推定已满足当前剪辑、声音和配音修改能力 |

ViMax 依赖 Python 3.12 及 LangChain 相关包，其依赖声明和旧调用方式需要与所选框架一起做兼容检查；本轮没有执行依赖安装，不能宣称无冲突。

参考：[依赖](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/pyproject.toml)、[Idea2Video](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/pipelines/idea2video_pipeline.py)、[Script2Video](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/pipelines/script2video_pipeline.py)、[适配工具](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agent_runtime/vimax_adapters.py)。

AdCraft 的交互、资产与版本思路，OpenMontage 的电影技能和工具组织继续作为参考。具体复制哪些代码及许可适用范围待模块评审，不把所有参考项目都装成一层运行时。

## 6. 仍需由电影应用实现的部分

无论选择哪个框架，都需要把下列产品能力落实到电影领域：

1. 剧本、人物、场景、镜头、声音和成片的版本与引用关系。
2. annotation 的视频版本、时间点、批量提交与修改方案关联。
3. 按产物版本保存的批准和共创／托管授权。
4. H3、Seedance 2.0 及图片／声音 Provider 的任务提交、外部任务 ID、结果查询、用量与异常恢复。
5. 剪辑、字幕、混音、局部声音修改与必要补拍的实际媒体能力。

框架负责 Agent 的对话与执行状态；电影应用负责产物的创作身份和采用关系。两类状态通过引用连接，避免各自保存一份相互矛盾的影片当前版本。

## 7. 下一步评审和验证

主导演、按需专业子 Agent、后台媒体任务的结构形态，以及 AgentScope 2.0 首选框架路线均已确认。四类职责的具体边界、最终数量和模块仍需评审与验证。

所有者指出仅验证插话、委派与恢复过窄，要求扩大范围，并于 2026-09-06 确认[首轮验证矩阵](../validation/first-round-matrix.md)的七组二十一个场景族，覆盖创作、协作、视觉、声音、修改、可靠性与完整影片，分真实 LLM、真实媒体和完整交付三批推进。该矩阵范围已确认，具体接入和执行待完成；Mock 仅补充控制路径，不替代模型行为与真实媒体验证。

这些是后续验证设计，不构成本轮已授权的模型调用或实现。当前没有部署、速度、成本或电影质量的验证结论。
