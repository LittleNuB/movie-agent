# ADR 0005：后续视频使用 720P

Status: Partially superseded by [ADR 0006](./0006-provider-resolution-and-seedance-fast.md)

Date: 2026-09-06

用户在真实 MVP 实施期间明确要求“后续全部使用720P规格的视频，降低API成本费用”。该最新决定替代实施计划中的 1080p 默认输出要求。

随后用户进一步明确 H3 使用 768P、Seedance 2.0 Fast 使用 720P，取代以下统一生成规格和视频选择；720P 导出与保留历史文件继续有效。

- 后续新视频生成使用 720P，导出为 1280×720、16:9、24 fps、48 kHz MP4。
- 生成前实际校验参数；不把 768P／2K 生成后缩放当作 720P API 调用。
- 当前 H3 档位不含 720P，因此本轮后续使用个人已经配置的 Seedance 720P。H3 连接和既有结果保留，产品初始模型配置仍为空。
- 已提交云端任务继续查询取回，已生成素材不重复调用 API；高分辨率母版派生本地 720P 版本，原文件和历史采用记录保留。
- 记录源尺寸、输出尺寸和实际用量；费用仍待账单核对，不凭分辨率推定已节省的金额，也不增加预算硬停止。

依据：本次会话用户最新要求；已核对的 [H3 创建接口](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-create) 及本轮 Provider 能力记录。
