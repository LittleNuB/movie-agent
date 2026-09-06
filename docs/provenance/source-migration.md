# 来源与迁移记录

**日期：** 2026-09-06。来源仓库为 LittleNuB/digital-human-agent-mvp，来源 HEAD 为 `edb74cd913bf40c6ed82c2f1c4968c1f2fd1ff1c`。迁移依据是该仓库当前工作树，包含未提交的新电影文档，不能将全部来源文件描述为已存在于此提交。

## 来源对应

机器可读哈希记录见[来源清单](./source-manifest.json)。哈希以原文件字节计算，当前文档经整理后不会与原文件逐字相同；视觉参考图保持原始字节。

| 原仓库相对路径 | 新仓库目标 | 处理 |
|---|---|---|
| `docs/research/ai-film-agent-competition-2026-09-04/product-proposal.md` | [docs/product/product-spec.md](../../docs/product/product-spec.md) | 修复链接并同步最新状态 |
| `docs/research/ai-film-agent-competition-2026-09-04/story-proposal-structure.md` | [docs/product/creative-interaction.md](../../docs/product/creative-interaction.md) | 修复链接并同步最新状态 |
| `docs/research/ai-film-agent-competition-2026-09-04/frontend-grilling.md` | [docs/product/frontend-spec.md](../../docs/product/frontend-spec.md) | 修复链接并同步最新状态 |
| `docs/research/ai-film-agent-competition-2026-09-04/technical-proposal.md` | [docs/architecture/technical-baseline.md](../../docs/architecture/technical-baseline.md) | 修复链接并同步最新状态 |
| `docs/research/ai-film-agent-competition-2026-09-04/architecture-review-2026-09-05.md` | [docs/architecture/architecture-review-2026-09-05.md](../../docs/architecture/architecture-review-2026-09-05.md) | 修复链接并同步最新状态 |
| `docs/research/ai-film-agent-competition-2026-09-04/first-round-validation-matrix.md` | [docs/validation/first-round-matrix.md](../../docs/validation/first-round-matrix.md) | 修复链接并同步最新状态 |
| `docs/research/ai-film-agent-competition-2026-09-04/provider-setup-2026-09-06.md` | [docs/validation/provider-preflight-2026-09-06.md](../../docs/validation/provider-preflight-2026-09-06.md) | 修复链接并同步最新状态 |
| `docs/research/ai-film-agent-competition-2026-09-04/product-proposal-2026-09-04-early-draft.md` | [docs/archive/2026-09-04/product-early-draft.md](../../docs/archive/2026-09-04/product-early-draft.md) | 增加历史提示，修复链接 |
| `docs/research/ai-film-agent-competition-2026-09-04/technical-proposal-2026-09-04-early-draft.md` | [docs/archive/2026-09-04/technical-early-draft.md](../../docs/archive/2026-09-04/technical-early-draft.md) | 增加历史提示，修复链接 |
| `docs/research/ai-film-agent-competition-2026-09-04/document-review-2026-09-05.md` | [docs/archive/2026-09-05/document-review.md](../../docs/archive/2026-09-05/document-review.md) | 增加历史提示，修复链接 |
| `.scratch/ai-film-agent-competition-2026-09-04/research/claim-ledger.md` | [docs/archive/2026-09-04/research/claim-ledger.md](../../docs/archive/2026-09-04/research/claim-ledger.md) | 增加历史提示，修复链接 |
| `.scratch/ai-film-agent-competition-2026-09-04/research/gap-matrix.md` | [docs/archive/2026-09-04/research/gap-matrix.md](../../docs/archive/2026-09-04/research/gap-matrix.md) | 增加历史提示，修复链接 |
| `.scratch/ai-film-agent-competition-2026-09-04/research/report-source.md` | [docs/archive/2026-09-04/research/report-source.md](../../docs/archive/2026-09-04/research/report-source.md) | 增加历史提示，修复链接 |
| `.scratch/ai-film-agent-competition-2026-09-04/research/reader-check.md` | [docs/archive/2026-09-04/research/reader-check.md](../../docs/archive/2026-09-04/research/reader-check.md) | 增加历史提示，修复链接 |
| `docs/research/ai-film-agent-competition-2026-09-04/assets/frontend-theme-comparison-2026-09-06.png` | [docs/assets/frontend-theme-comparison-2026-09-06.png](../../docs/assets/frontend-theme-comparison-2026-09-06.png) | 原样复制，SHA256 相同 |

## 整理原则与修订

- 旧产品、交互、前端、技术、研究与验证文件经重新分组迁入；修复相对链接，让新仓库可独立阅读。
- 同步最新用户决定：Windows 本地个人部署、自备模型 API Key、设置页检查连接、独立私有仓库，以及原型已批准且在初始化后承接。
- 将“仍需决定所有页面”“尚未授权任何实施”等过时状态改为具体范围；保留原型未实现、电影未生成、矩阵未执行的事实。
- GLM 的基础工具回传与媒体只读检查明确来自旧工作区；原始脱敏回执及个人接入配置未迁入，新仓库未运行模型请求。
- 历史材料保留当时结论和来源；仅增加迁移提示与修复本地链接。日期、失败、旧设想不改写为当前结果。
- 根 README、AGENTS、DESIGN、CONTEXT，以及本仓库文档索引、ADR、任务说明和配置示例根据已批准计划重新编写。旧 AGENTS 的 Pi 保留、兼容旧项目与移动端验收规则未继承。
- 原始视觉图保留 A／B／C 对照；C 已被所有者否决，原图归档不代表采用 C。

## 未迁入内容

旧 Git 历史、旧应用代码、旧项目与媒体、依赖目录、下载的第三方源码／wheel、缓存、真实密钥、个人密钥路径及个人配置均未迁入。旧工程的完整历史设计和 Ticket 保留在原处，理解新产品无需访问它们。

本次未为新项目选定开源许可证，也未复制参考项目的运行代码。研究与未来代码复用边界见[第三方来源](../architecture/third-party-sources.md)。

## 工作树保护与验证

执行前已对旧工程 1565 个 Git 已跟踪或未忽略的未跟踪文件记录 SHA256、HEAD 和状态。完成时复核这些文件、文件集合与 Git 状态，结果写入[初始化验收](../validation/repository-initialization-2026-09-06.md)。检查辅助回执保留在被忽略的本地缓存，未导出旧文件内容。
