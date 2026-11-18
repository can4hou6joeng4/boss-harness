# 项目状态与待验收范围

本页说明 BOSS Harness 当前可核实的能力、尚未完成的范围与不承诺的事项。版本号以根 [package.json](../package.json) 和 [CHANGELOG](../CHANGELOG.md) 为准；实际发布以 [GitHub Releases](https://github.com/can4hou6joeng4/boss-harness/releases) 为准。

> **English summary**: `main` is the development branch. The latest published prerelease is `v0.2.0-rc.15`; the desktop is built from source and has no standalone installer. npm / PyPI publishing, real-model and real-platform acceptance, and signed installers remain pending. See the [English overview](../README.md#english-overview) for architecture and setup.

## 发布状态

- `main` 是开发分支，源码候选号随合并推进，不等同于已发布版本。
- 最新实际预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。桌面从源码构建，尚无独立安装包或签名发行。
- Python wheel / sdist 可构建并隔离安装，但尚未发布到 npm 或 PyPI。
- 源码采用 MIT 许可证；仓库可见性与许可证不因发布候选而改变。

## 已具备

- 执行循环：流式回合、steering / follow-up 队列、逐次审批与停止、持久化与恢复。
- 上下文：预算、分段摘要、自动压缩与溢出恢复；摘要任务可查询。
- 会话：append-only JSONL、SQLite 索引、冻结快照、分支、归档与删除、导出脱敏。
- 工具边界：14 个 allowlist 工具（13 个只读工具与需逐次审批的 `boss_hr_greet`）；桌面新建会话固定使用只读策略。
- 桌面：审批卡、会话查找、任务队列面板（暂停项重试 / 撤回与完整输入核对）、技能选择器与工作区技能管理、自动压缩策略设置、启动失败自检（含内核、协议与 Python 版本展示、协议不一致提示与结果复制）、用量与附件分段读取；平台登录使用隔离分区。
- 协议：stdio JSON-RPC `0.2.0`；握手、请求预算、错误码与通知有静态核对。
- 工程检查：版本、协议（含传输帧 / 队列上限双端一致）、内核工具清单、写工具集合、bundle 投影与工具子进程边界、会话导出默认脱敏、桌面安全、CI 工作流安全、搜索归一化、文档链接与页内锚点；桌面安全覆盖进程导入方向、IPC 角色符号、主进程脚本 / 调试器入口、主进程与 app-client 子进程启动及 `node:child_process` 导入 / 调用限制、preload 暴露面、导入来源与进程能力面、IPC 通道字面量与受信发送方、会话导出处理器不变量、渲染层模块 / CSP / 嵌入与远程资源 / HTML 注入边界；CI 工作流安全覆盖顶层只读权限、禁用特权触发器、作业超时、checkout 凭据、action 固定主版本与检查脚本接入；CI 覆盖 Python 3.10–3.14。

## 待完成与待验收

- 独立安装包、代码签名与 macOS / Windows / Linux 完整安装验收。
- 真实模型线路、真实招聘平台账号与浏览器登录的完整验收。
- npm / PyPI 发布渠道与版本发布授权。
- 已发布资产的独立复核（tag、Release 正文与资产哈希）。

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
