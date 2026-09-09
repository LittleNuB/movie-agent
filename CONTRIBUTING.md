# 参与 Movie Agent

当前是 Windows 本地开发预览版。欢迎提交可复现的问题、模型适配和创作体验改进。先阅读 [README](README.md) 的完成度与[设计入口](DESIGN.md)，开发助手另读 [AGENTS](AGENTS.md)。

## 本地开发

按[运行指南](docs/runtime-guide.md)初始化，在自己的分支修改。正式界面来自 `web/`，`prototype/` 只保留模拟交互参考；修改原型不会改变正式产品。

需要独立开发数据时，在启动前设置一个新的数据目录，避免恢复个人项目中的未完成任务：

```powershell
$env:MOVIE_AGENT_DATA = Join-Path $PWD 'local-data\development'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Port 4319
```

不要用真实用户项目做破坏性验证，也不要在自动化测试中调用付费模型。API Key 通过设置页写入 Windows 凭据管理器，不提交到仓库；项目数据、生成素材、日志及缓存也不提交。

## 验证与提交

```powershell
uv run --frozen ruff check src tests
uv run --frozen pytest -q
node --test tests/test_workspace_markdown.mjs
git diff --check
```

Node 用于前端文本测试；FFmpeg 用于本地合成检查。按照变化风险选择必要验证。界面改动同时检查实际浏览器；协议改动需要区分模拟响应、真实接口成功与实际素材质量，不能用单项成功替代整片人评。

提交 PR 时说明问题、修改后的行为、验证和剩余限制。涉及公开接口、数据迁移或已确认设计决定时，更新对应文档和 ADR；保护用户手改与不可变的产物版本。依赖变化更新 `uv.lock`，复制或改写第三方代码时补充具体版本、来源和许可。

## 反馈问题

普通问题可以使用 [GitHub Issues](https://github.com/LittleNuB/movie-agent/issues)。请说明版本、Windows 环境、操作步骤、预期与实际行为，以及经过脱敏的错误信息。涉及模型时提供协议类型和模型 ID，不提供 Key、认证头、完整数据库、私有故事、素材下载签名或未经授权的图片与视频。

安全问题优先使用仓库可用的私密漏洞报告入口，不要在公开 Issue 中张贴真实凭据或未脱敏的复现数据。
