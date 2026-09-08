# Movie Agent

面向 AIGC 零基础用户的个人电影创作 Agent。通过自然语言、多轮共创或明确授权的托管，把一个想法拍成可继续修改的 90–120 秒科幻短片。

当前实现支持 Windows 本地启动，通过浏览器使用。Agent、项目和版本保存在本机，模型推理与媒体生成调用云端 API；用户自行准备模型 API Key，通过设置页配置和检查连接。

产品不预设厂商或模型。设置采用“服务连接 → 模型 ID → 用途分配”；此前选定的 GLM、H3、Seedream、Seedance 是所有者个人使用与验证组合。详见[模型与 API 设置](./docs/product/model-settings.md)。

后续按用户最新要求控制调用规格：**H3 生成 768P；Seedance 改用 2.0 Fast、生成 720P；成片导出 720P（16:9、1280×720）**。已有素材保留原规格并本地转换复用。这是本轮个人配置，产品仍不预填模型。见[最新规格](./docs/adr/0006-provider-resolution-and-seedance-fast.md)。

## 当前状态

`feat/movie-runtime` 正在实现真实电影 MVP。已经接入 AgentScope、Windows 凭据管理器、后端事件、真实图片／视频／配音和 FFmpeg 后期。完整创作与修改验收仍在进行；不能把接口试拍当作两部整片已交付。原型分支 `prototype/film-creation` 保留作交互参照。

| 项目 | 状态 |
|---|---|
| 产品、交互、Windows 本地部署方向 | 已确认，具体行为见设计文档 |
| AgentScope 与电影领域方法 | 已集成真实对话、工具、SQL 会话、收件箱和按需专业职责；持续验证 |
| 前端视觉 | A 日间、B 夜间已选定；静态示意图不代表可运行产品 |
| 可点击原型 | 已实现；2026-09-06 用户暂定通过 UI，浏览器检查单独记录 |
| 真实版本前端 | 2026-09-08 按反馈完善对话工作区：真实活动、独立草稿、历史原文、输入与播放保留、资产搜索、重命名及三种外观；见[验收记录](./docs/validation/frontend-experience-2026-09-08.md) |
| 本仓库真实接入 | GLM 流式工具及图片输入、Seedream 图像、H3 首帧与参考图视频、MiniMax 配音已取得产物 |
| 配乐接入 | 已实现 MiniMax music-3.0 请求；当前验证账号被 HTTP 410 拒绝，尚无独立配乐产物 |
| 电影制作与质量验证 | 《回声频率》已有 91 秒影片与结尾修改前后版；用户反馈故事无聊、价值不明确、看不懂，故事人评未通过；全部素材正在逐项人评。共创第二部、配乐与完整矩阵尚未完成 |

约 30 分钟得到首条完整可看片、约 150–220 元/片均为未实测的目标预期，不是硬停止条件。电影质感参考《星际穿越》《挽救计划》《流浪地球2》，不宣称达到相同制作水准。

## 从这里阅读

- [开发助手规则](./AGENTS.md)：进入本仓库工作的方式。
- [设计入口](./DESIGN.md)：当前已确认方向与剩余问题。
- [项目术语](./CONTEXT.md)：统一理解剧本、素材、版本和授权。
- [完整文档索引](./docs/README.md)：产品、架构、验证、研究与决定。
- [可点击原型](./docs/plans/clickable-prototype.md)：已批准范围及实际交付。
- [能力建设范围](./docs/plans/capability-mvp.md)及[实施记录](./docs/plans/runtime-implementation.md)：真实导演、声画生成、成片和修改，正在实施。
- [真实运行使用说明](./docs/runtime-guide.md)：Windows 启动、模型配置、创作和恢复。
- [对话工作区体验](./docs/plans/frontend-experience.md)：本轮前端范围、实际行为与验证边界。
- [对话专属资产库](./docs/validation/conversation-assets-2026-09-08.md)：中间文稿、素材、成片与历史版本集中浏览，对话保留简短入口。
- [真实运行验证记录](./docs/validation/runtime-evidence-2026-09-06.md)：实际产物、已发现问题、21 个场景族状态与费用边界。
- [首轮人工反馈与资产审阅](./docs/validation/human-review-2026-09-07.md)：用户实际评价及全部本地资产的核对入口。
- [原型使用说明](./prototype/README.md)：启动、体验路径与示例边界。
- [配置示例](./.env.example)：未来接入所需配置的说明，当前没有读取它的运行程序。

## 启动真实版本

在仓库根目录打开 PowerShell，准备 Python 3.12 与 [uv](https://docs.astral.sh/uv/)。执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

打开 [本地真实版本](http://127.0.0.1:4318)。初始化会按 `uv.lock` 安装依赖，并下载、核对 FFmpeg 校验和；设置页的初始连接、模型和用途均为空。真实版本使用服务端数据，不迁入原型 localStorage。

## 启动保留的交互原型

在本分支仓库目录打开 PowerShell，使用 Node.js 24（本机验证版本 24.14.1）：

```powershell
npm run dev
```

打开 [本地原型](http://127.0.0.1:4317)。无需安装 npm 依赖或填写真实 Key。首次进入可以从一句想法开始，也可点击“打开示例影片”。原型仅监听本机回环地址，状态保存在当前浏览器中；这不是正式产品启动方式。验收结果见[浏览器检查记录](./docs/validation/clickable-prototype-2026-09-06.md)。

## 仓库边界

本仓库独立于历史后期工程。当前工作树中的电影设计与研究经过整理迁入，来源见[迁移记录](./docs/provenance/source-migration.md)。旧工程代码、Git 历史、实际项目数据、密钥和个人配置均未迁入。

ViMax 的固定版本创作与参考选择方法已改写进电影提示，来源和 MIT 声明见[本轮第三方说明](./third_party/README.md)。AdCraft 与 OpenMontage 的吸收依据见[第三方研究](./docs/architecture/third-party-sources.md)。未导入它们的整套运行时。

GitHub 仓库为私有。当前尚未选定本项目的开源许可证；私有仓库初始化不代表公开发布或参赛提交。
