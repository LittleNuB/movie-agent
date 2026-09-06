# 通用模型设置 · 原型修正与验证

Date: 2026-09-06

Status: focused_browser_checks_passed_user_review_pending

## 修正范围

用户审阅初版原型后要求采用常见 API 填写方式，不把所有者的模型组合设成完整产品默认值。本轮从原型提交 `9292c3a` 开始，替换固定模型栏位，增加独立设置模块，更新 [ADR 0004](../adr/0004-user-configured-models.md)、[设置规格](../product/model-settings.md)、设计与配置示例。

## 实际检查

Windows、Node.js 24.14.1、Python Playwright、Chromium 147.0.7727.15；本机实际 DOM 填写与操作，测试只使用伪造 Key、example.com 地址及自定义示例模型 ID。执行 [verify_settings.py](../../prototype/verify_settings.py)，8 组检查通过：

1. 初始连接、模型和用途为空；设置中没有个人选定的厂商／模型。
2. Key 可编辑、默认遮罩并可显隐；模拟成功／失败可辨识，编辑配置使旧检查结果失效。
3. 获取的示例 ID 可编辑，也可手动添加；同一连接多个模型；Key 不写入 localStorage。
4. 用途按声明能力筛选，需要明确保存；不触发创作或实际生成。
5. 多连接可使用同名模型且引用独立；无需 Key 与专用接口边界可见。
6. 删除模型／连接只清除受影响的用途引用；包含账号密码的地址不能保存。
7. 刷新保留连接元数据和已有手改剧本，清除 Key；夜间主题保留。
8. 1440×1000 与 1280×800 桌面布局检查，保存按钮完整可见；零外部浏览器请求、零未捕获 JavaScript 异常。

另执行 `npm run check`、Git 空白与本地文档链接检查。初版 14 组创作检查保留为原提交的历史结果；本轮只验证设置改动及对已有剧本的保护，没有无目的地重跑整条示例影片制作。

原始结果位于忽略的 `.cache/prototype/model-settings/results.json`。代表性界面：[服务连接](../assets/prototype/api-connections.png)、[用途分配](../assets/prototype/api-assignments.png)。

## 能力限制

所有连接检查和模型获取都是演示，图像、视频、声音与导演均未接真实模型。通用表单没有实现任意协议的真实适配。Key 仅页面内存保存不是正式凭据存储方案；当前设置用途不改变预设的创作回复。完整产品的模型能力、凭据存储与实际调用须后续实现和验证。

初版模型设置与测试记录中的固定模型／只读凭据描述由本次更新取代，历史结果不改写为新设置已实现时的证据。
