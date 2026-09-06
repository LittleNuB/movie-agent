# 模型选定与基础接入 · 旧工作区记录

**日期：** 2026-09-06（北京时间）

**状态：** 2026-09-06 在旧 digital-human-agent-mvp 工作区完成的基础接入记录。本文件迁入作为历史证据；新 movie-agent 仓库未运行这些请求，也没有接入 AgentScope、生成媒体或执行电影验证矩阵。

## 1. 本轮确定的模型

| 用途 | 所有者选择 | 本轮核对的 API 模型 ID | 当前证据 |
|---|---|---|---|
| 意图理解、编剧、规划和委派 | GLM 5.3 Flash | `glm-5.3-flash` | 真实工具调用及结果回传成功，响应模型名一致 |
| 首选视频生成 | MiniMax H3 | `MiniMax-H3` | 官方 V2 文档确认；该凭证的任务列表查询成功，未验证生成权限和效果 |
| 图片生成及参考资产 | Seedream 5.0 Pro | `doubao-seedream-5-0-pro-260628` | 使用指定凭证请求方舟模型列表，返回该 ID；未生成图片 |
| 视频备选，沿用此前决定 | Seedance 2.0 标准版 | `doubao-seedance-2-0-260128` | 同一方舟模型列表返回该 ID；未验证生成权限和回退效果 |

第一批 LLM 验证先使用同一 GLM 模型，具体角色是否需要不同推理强度由验证结果决定。配音、音乐及独立音效模型仍待选；拥有 MiniMax Key 不代表已选定其所有音频模型，也不妨碍第一批 LLM 验证的准备。

## 2. 原工作区本地配置

- 原工作区根目录 `.env.film.local` 保存 Provider、模型 ID、接口地址及 `*_KEY_FILE` 引用。该文件已被现有 `.env.*` 规则忽略；不含密钥值，不修改旧工程的 Gemini／Qwen 配置。
- 三个密钥文件已检查存在、非空且为单行内容；原文件保持原位，未复制密钥。可版本化文档不记录密钥值或用户桌面路径。
- GLM 使用 `https://open.bigmodel.cn/api/paas/v4`，走标准推理接口。
- H3 使用 `https://api.minimax.cn/v2`；创建任务路径为 `/video_generation`，任务列表路径为 `/query/video_generation`，不能直接复用旧海螺 V1 请求格式。
- Seedream 和 Seedance 使用 `https://ark.cn-beijing.volces.com/api/v3`。本轮仅请求 `/models`；生成参数仍需在对应适配器接入时核对。
- 原工作区 v0.4 程序不会自动加载该接入配置。新仓库仅提供不含秘密的 `.env.example`，未迁入 `.env.film.local` 或任何凭据；目前没有加载示例配置的运行代码。

## 3. 实际检查记录

本次请求未发送用户剧本、素材或完整会话，只发送合成的连通性提示及无副作用的工具回执；媒体查询结果仅保留状态与相关模型 ID。

| 检查 | 结果 | 解释与限制 |
|---|---|---|
| GLM 生成 `connection_probe` 工具调用 | HTTP 200；参数符合测试标记；响应模型为 `glm-5.3-flash` | 第一条请求带关闭思考参数，但仍返回思考内容，不能认为关闭已生效 |
| GLM 接收工具结果，继续带关闭思考参数 | HTTP 400，代码 `1210` | 接口提示该模型始终思考，不支持关闭，需使用 `low`、`high` 或 `max` |
| GLM 工具结果回传，改为开启思考与 `reasoning_effort=low` | HTTP 200；准确返回 `FILM-CONNECTION-OK` | 保留完整工具消息关系后得到成功响应；只证明基础协议回传，不能证明复杂委派或稳定性 |
| H3 V2 任务列表只读查询 | HTTP 200；结果包含合法 `items` 列表 | 未创建、取消、删除或下载任何媒体任务；不证明生成权限、额度或视频质量 |
| 方舟模型列表只读查询 | HTTP 200；结果包含表中 Seedream 与 Seedance ID | 模型出现在列表不等于账号实际生成调用已经通过 |

GLM 共提交三次请求，包含一次参数错误；两次成功响应合计返回 491 tokens 的用量。实际账单费用未核对，失败请求费用也不能推定为零。这些数值属于接入检查，不是电影生产成本或场景通过率。

原工作区脱敏回执位于 `.cache/film-provider-setup/preflight-2026-09-06.json`，被 Git 忽略，未随本次文档迁入。本文保留当时记录的结果与失败，不把修正后的成功覆盖到失败请求，也不声称新仓库包含原始回执。

## 4. 后续接入所需工作

1. 在 AgentScope 适配中验证 GLM 的流式输出、工具调用消息及推理配置；本轮 `low` 仅是成功的连通性设置，不冻结创作任务的推理强度。
2. 准备首批场景输入、工具合同、受控后台任务和回执，按[首轮验证矩阵](first-round-matrix.md)开始真实 LLM 验证。
3. 媒体批次再验证真实提交、任务查询、产物质量及回退。仅凭可用 Key 或模型列表，不提前标记任何媒体场景通过。

## 5. 本轮来源

- [智谱官方 GLM 5.3 Flash 介绍](https://autoclaw.z.ai/blog/model/glm-5.3-flash/)：确认模型定位；API 名及本机可调用性以实际响应为准。
- [智谱对话补全文档](https://docs.bigmodel.cn/api-reference/模型-api/对话补全)：标准推理入口与工具消息协议。页面中的模型枚举、推理说明存在更新滞后，本轮新模型参数行为另按真实回执记录。
- [MiniMax H3 创建任务](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-create)、[任务列表查询](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-list)：V2 接口、模型标识与只读查询入口。
- 方舟官方 API `GET https://ark.cn-beijing.volces.com/api/v3/models`：2026-09-06 真实只读响应确认两个模型 ID。未把搜索到的第三方别名或非官方价格当作接入依据。
