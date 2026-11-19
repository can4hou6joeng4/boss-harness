# 支持与问题分流

本页帮助使用者找到合适的入口。提交任何材料前，请移除凭据、Cookie、真实候选人信息、本机绝对路径与真实会话记录。

## 先看文档

| 问题类型 | 先读什么 |
| --- | --- |
| 安装与首次启动 | [README 快速开始](README.md#快速开始) |
| 模型配置、自检与故障排查 | [使用指南](docs/USER_GUIDE.md) |
| 搜索、审批、通知、队列与会话界面 | [桌面交互指南](docs/DESKTOP_GUIDE.md) |
| 请求边界、预算、恢复与 RPC 契约 | [内核与业务契约参考](docs/TECHNICAL_REFERENCE.md) |
| 版本范围与实际发布资产 | [CHANGELOG](CHANGELOG.md) 与 [GitHub Releases](https://github.com/can4hou6joeng4/boss-harness/releases) |
| 当前实现与待验收范围 | [项目状态与待验收范围](docs/STATUS.md) |

`none` 线路不调用模型，但仍可能调用 `boss-agent-cli`。本仓库当前从源码构建桌面，不提供独立签名安装包；真实模型、招聘平台与安装包验收需要单独进行。

## 提交可复现问题

桌面提示内核启动失败时，从「设置 → 模型与连接」复制[桌面自检结果](docs/USER_GUIDE.md#桌面启动失败时的自检)。命令行启动失败时，用原来的 provider、启动参数和环境运行 `.venv/bin/boss-harness --check`。`--provider none` 专用于核对无模型启动。详见[本地配置自检](docs/USER_GUIDE.md#本地配置自检)。

按 [Bug 报告模板](https://github.com/can4hou6joeng4/boss-harness/issues/new?template=bug_report.yml) 提供以下信息。

- 源码提交、npm / Python 版本与实际运行方式。
- 使用合成数据的最小复现步骤、期望行为与实际行为。
- 脱敏后的错误码或日志；不要贴入端点、密钥、Cookie、候选人资料或真实会话。
- 是否涉及真实账号或招聘平台；涉及时只描述影响，不要求他人用真实账号复现。

功能建议与集成讨论请使用 [Feature 请求模板](https://github.com/can4hou6joeng4/boss-harness/issues/new?template=feature_request.yml)，说明具体招聘场景、用户价值与验收条件。

## 安全与社区

可能涉及状态目录保护、JSON-RPC 边界、工具审批或导出脱敏的安全问题，请按[安全政策](SECURITY.md)私下报告，不要在公开 Issue 中附带可利用细节。参与讨论时遵守[行为准则](CODE_OF_CONDUCT.md)。

本页只说明渠道；维护者是否启用 Discussions、私密漏洞报告或 Dependabot 等仓库功能，以 GitHub 实际可见配置为准。
