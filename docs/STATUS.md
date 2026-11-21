# 项目状态与待验收范围

本页说明 BOSS Harness 当前可核实的能力、尚未完成的范围与不承诺的事项。版本号以根 [package.json](../package.json) 和 [CHANGELOG](../CHANGELOG.md) 为准；实际发布以 [GitHub Releases](https://github.com/can4hou6joeng4/boss-harness/releases) 为准。

> **English summary**: `main` is the development branch. The latest published prerelease is `v0.2.0-rc.15`; its tag, release notes and downloadable asset hashes were re-checked on 2026-11-20. Later source candidates on `main` have not been published. The desktop is built from source and has no standalone installer. npm / PyPI publishing, real-model and real-platform acceptance, and signed installers remain pending. See the [English overview](../README.md#english-overview) for architecture and setup.

## 发布状态

- `main` 是开发分支，源码候选号随合并推进，不等同于已发布版本。
- 最新实际预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。桌面从源码构建，尚无独立安装包或签名发行。
- 该预发布的发布记录已于 2026-11-20 重新核对：远程 annotated tag、Release 正文与 `build-info.json`（`schemaVersion: 1`）指向同一提交 `560c86e2593592f86c61bdeddf0be099ec9d1272`；从 GitHub 下载的 wheel、sdist 与清单的 SHA-256 与 `SHA256SUMS.txt` 一致，清单记录的版本、包长度与哈希也与下载文件一致。这次核对由项目维护流程执行，只覆盖发布记录与可下载资产，不是第三方审计，也没有重建该版本或重做桌面验收。
- `v0.2.0-rc.15` 之后合入 `main` 的源码候选尚未聚合为新的预发布。下一次发布的准备记录滚动维护在 [Issue #2351](https://github.com/can4hou6joeng4/boss-harness/issues/2351)，包含固定的候选提交、变化范围、本地构建与隔离安装结果；其中的本地候选资产没有上传，实际发布须从最终 tag 提交重新构建并复核。
- Python wheel / sdist 可构建并隔离安装，但尚未发布到 npm 或 PyPI。
- 社区介绍草稿保存在 [Issue #2312](https://github.com/can4hou6joeng4/boss-harness/issues/2312)，尚未向外部渠道发送；发送目标与正文按[对外介绍](../RELEASING.md#对外介绍)的规则单独确认。
- 源码采用 MIT 许可证；仓库可见性与许可证不因发布候选而改变。

## 已具备

- 执行循环：流式回合、steering / follow-up 队列、逐次审批与停止、连续同名同参调用的内存态提醒（仅提示、不阻断、不持久化）、持久化与恢复。
- 上下文：预算、分段摘要、自动压缩与溢出恢复；摘要任务可查询；工作区常驻说明（有界、只读、每回合重新读取，内容不授予工具权限）。
- 会话：append-only JSONL、SQLite 索引、冻结快照、分支（含被放弃分支摘要与按当前分支的末回合状态）、中断回合续接（只读预检、已完成工具不重跑）、归档与删除、导出脱敏。
- 工具边界：14 个 allowlist 工具（13 个只读工具与需逐次审批的 `boss_hr_greet`）；桌面新建会话固定使用只读策略；业务 CLI 的浏览器来源可按进程覆盖（`BOSS_HARNESS_BROWSER_SOURCE`），只在启动阶段校验取值，不读取浏览器或 Cookie。
- 桌面：审批卡、会话查找、任务队列面板（暂停项重试 / 撤回、完整输入核对与把排队 follow-up 转为当前回合 steering）、技能选择器与工作区技能管理、自动压缩策略设置、启动失败与手动配置自检（含内核、协议与 Python 版本展示、协议不一致提示、错误与警告分列与结果复制）、用量与附件分段读取；平台登录使用隔离分区。
- 协议：stdio JSON-RPC `0.2.0`；握手、请求预算、错误码与通知有静态核对。
- 工程检查：CI 在安装依赖前运行全部 `scripts/check_*.py`，覆盖版本与发布元数据、协议与传输、桌面与 IPC 安全、内核工具与审批、执行循环与队列、本地资源与隐私、连接与浏览器来源、搜索、工作流与文档；随后执行依赖审计、TypeScript 检查、Electron 源码构建、Python 包构建与隔离安装，并在 Python 3.10–3.14 上分别核对搜索归一化与源码编译。各脚本的核对范围见[构建前静态检查](TECHNICAL_REFERENCE.md#构建前静态检查)；这些检查是静态扫描，不代替下方列出的待验收项。

## 待完成与待验收

- 独立安装包、代码签名与 macOS / Windows / Linux 完整安装验收。
- 真实模型线路、真实招聘平台账号与浏览器登录的完整验收。
- 下一次实际预发布：独立 release PR 尚未建立；tag、GitHub Release 与资产上传需对应授权后执行，发布后按[合并与发布](../RELEASING.md#合并与发布)再次核对远程记录。
- npm / PyPI 发布渠道尚未启用，发布需单独授权。

## 非目标

- 自动投递、批量沟通或绕过平台风控与验证码。
- 在仓库、Issue 或日志中保存凭据、Cookie、真实候选人资料或真实会话。
- 把 Electron `out/` 目录或 CI 构建产物称作独立安装包。
- 用本地离线验证代替真实平台或签名安装包验收。

## 参与方式

- 先按[支持与问题分流](../SUPPORT.md)选择入口；缺陷使用 Bug 模板，建议使用 Feature 模板。
- 安全问题按[安全政策](../SECURITY.md)私下报告。
- 开发、验证、提交与 PR 约定见[贡献与交付约定](../CONTRIBUTING.md)。
- 候选版本节奏、构建与对外介绍见[版本交付与项目介绍](../RELEASING.md)。
