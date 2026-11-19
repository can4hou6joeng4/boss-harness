# 内核与业务契约参考

本页记录 README 主线之外的请求、会话、上下文和资源边界，面向需要评估内核行为或接入宿主的开发者。数值和接口描述以当前源码为准；改动相应行为时应同步更新本页。它不代表供应商容量、计费方式或业务 CLI 的所有内部行为。贡献和验证步骤见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## 快速导航

- [请求与认证边界](#业务-cli-请求与认证边界)
- [暂停与失败恢复](#平台暂停与聊天部分结果)
- [模型与上下文预算](#模型容量与请求预算)
- [会话与模块边界](#模块边界)
- [桌面与队列行为](#工作流会话与桌面设置)
- [JSON-RPC 帧完整性](#json-rpc-帧完整性)
- [启动自检报告](#启动自检报告)
- [服务端通知](#服务端通知)
- [构建前静态检查](#构建前静态检查)
- [返回 README](../README.md)

## JSON-RPC 帧完整性

输入帧在派发前使用严格 JSON 解码：对象键必须唯一，浮点数必须有限，嵌套最多 64 层，字符串不得包含孤立 Unicode 代理项。无效 JSON、坏 UTF-8、重复键、非有限数值或超深结构返回 `-32700` 协议错误，并继续读取后续完整帧；超过 `MAX_FRAME_BYTES` 或缺少 LF 的 framing 错误仍按传输边界终止连接。该解析规则也适用于服务端等待的响应帧，因此审批响应的重复字段不会被最后值静默覆盖。

`initialize` 握手按协议声明校验参数类型：`protocolVersion` 只接受字符串（缺省按 `0.1.0`），`capabilities` 只接受对象或 `null`，其他类型返回 `-32602`；被拒绝的握手不改变连接状态，可在同一连接按正确参数重试。`shutdown` 不要求先完成握手：调用后内核停止服务并返回 `{ "stopped": true }`；连接仍然可读，进程在 stdin 关闭后退出，因此它不等同于立即结束进程。桌面宿主通常直接关闭 stdio，不依赖该方法。

handler 可能已经产生外部或持久副作用，响应编码失败时不能重跑。若结果包含非有限浮点、孤立代理项或不可编码的递归结构，内核返回有界 `-32603` / `RESPONSE_INVALID`；如果响应请求 ID 本身无法安全编码，则省略该 ID。响应过大继续使用 `RESPONSE_TOO_LARGE`，原 handler 同样不会重放。

当前内核收紧已有参数类型校验：`turn/start` 与 `context/read` 只有缺省 `model` 才继承会话模型，显式 null、空字符串、布尔、数字、数组或对象均返回 `-32602`；合法字符串仍按会话模型线路检查，不匹配继续返回 `-32013`。当前内核把同一规则用于 `turn/start.provider`：显式提供时须通过 provider 格式校验并与已选线路一致，null 等其他类型返回 `-32602`，缺省才不核对。`thread/read` 与 `thread/resume` 的 `excludeTurns` 只接受布尔 true / false，缺省为 false；不能传字符串 `"false"`。同两个接口的 `snapshot` 也只接受布尔值，字符串、数字、数组、对象或 null 返回 `-32602`，不会静默降级成普通读取。读取 `view` 只接受 `log` / `branch`，`task/read.kind` 只接受 `turn` / `queue` / `compaction`，数组、对象等非法类型统一返回 `-32602`，不再误报内部错误。`thread/start.projectId` 与 `thread/list.projectId` 筛选限制为最多 200 字符的字符串，超长值在写入会话文件或执行索引查询前返回 `-32602`；旧记录中的超长标识在读取投影中截断为前 200 字符并标记 `projectIdTruncated: true`，原始会话头不改写。会话标题在新建、重命名与 `thread/fork` 自定义标题处共用最多 500 字符的上限，超长值在写入会话文件前返回 `-32602`；旧记录中的超长标题在读取投影中截断为前 500 字符并标记 `titleTruncated: true`，原始会话头不改写。

队列任务的持久状态缺失或非法时，`task/read` 返回字符串 `unknown` 与 `recoveryPolicy: "manual_review"`，合法状态与恢复策略不变。会话索引的 `queueActiveItems` / `queueCounts` 与队列列表共用 `queue_record` 校验，损坏记录不覆盖同 id 先前的有效状态。此计数修正用于后续追加与索引重建；未变化日志的既有缓存索引不强制更新，历史错计数可退出应用后运行 `boss-harness --repair-state` 从日志重建。上述修正不新增 RPC，协议与内核仍为 `0.2.0`。

## 启动自检报告

`boss-harness --check` 只读取本地配置并向 stdout 输出单份报告：默认是单行 JSON（`schemaVersion: 1`、`version`、`protocolVersion`、`pythonVersion`、`ok` 与 `checks`），加 `--format text` 输出人类可读文本（总体结论、版本、逐项中文检查项名称、状态、检查码、说明与建议；存在错误时结论行同时给出警告数量）；两种格式的退出码一致。退出码为 0（无错误）或 2（存在错误）；加 `--strict` 时没有错误但有警告返回 1，报告内容与 `ok` 字段含义不变，桌面主进程不使用该参数。桌面主进程在握手前启动失败时运行同一命令且只解析默认 JSON，解析器只接受这些字段中的报告结构、`schemaVersion: 1`、布尔 `ok`、非空且不超过 16 项的 `checks` 列表，以及可选的单行 `version` / `protocolVersion` / `pythonVersion`；每项的名称、检查码、消息与建议必须符合固定格式，且同一报告中名称不重复。若 `ok` 与「所有检查项均非 error」不一致，整份报告作废，不向界面展示部分内容。

解析器不据此判断报告是否可信于真实运行环境，也不读取 stderr、内核会话或任何凭据；自检超时、输出超限、非 UTF-8 或进程异常退出时统一归入不可用原因。设置页展示报告时，若 `protocolVersion` 存在且与桌面协议包导出的 `PROTOCOL_VERSION` 不同，会并列显示两个版本并提示可能来自不同构建；字段缺失或一致时不追加提示。「设置 → 模型与连接」还可在任意连接状态手动运行同一命令：目标（解释器、工作目录与环境）在应用启动时只确定一次，手动与自动自检共用；手动请求经 `harness:startup-check` 交给主进程，连续点击共用同一份在途结论，自动自检未结束时先等它退出。字段含义与用户处理建议见[使用指南](USER_GUIDE.md#本地配置自检)，桌面展示路径见[桌面指南](DESKTOP_GUIDE.md#界面偏好与恢复)。

## 服务端通知

`packages/protocol` 的 `ServerNotifications` 是内核主动发送的通知方法集合；协议版本仍为 `0.2.0`。客户端应忽略未知方法，并通过后续读取或终态通知补齐状态。`toolCall/executing` 是可选通知，旧内核不发送时客户端仍可从 `toolCall/started` 进入等待或执行状态，并以 `toolCall/completed` 收尾。`kernel/shutdown` 也是可选通知：仅在宿主注入事件观察 hook、且关闭期限仍有余量时随关闭流程发送；客户端不得依赖它判断进程已退出。

| 类别 | 方法 | 说明 |
| --- | --- | --- |
| 回合 | `turn/started`、`turn/completed`、`turn/steeringApplied`、`model/retryStarted`、`model/retryEnded`、`session/error` | 回合开始 / 终态、转向消息已应用、模型重试观测与回合错误。重试通知只用于观察，不写会话条目；回合结果以 `turn/completed.status` 为准。 |
| 流式内容 | `item/started`、`item/completed`、`agentMessage/delta`、`agentThinking/delta` | 条目生命周期与增量文本 / 思考。增量不是持久投影，刷新后以条目读取为准。 |
| 工具与审批 | `toolCall/started`、`toolCall/executing`、`toolCall/completed`、`approval/requested`、`approval/decided` | 工具执行状态与审批。双向连接用 `item/tool/requestApproval` 服务端请求承载审批请求，非双向连接才以 `approval/requested` 通知发送；`approval/decided` 可能来自实时裁决或恢复路径。 |
| 会话 | `thread/created`、`thread/updated`、`thread/leafChanged`、`thread/archived`、`thread/deleted`、`thread/unarchived`、`thread/renamed`、`thread/reasoning/updated`、`thread/model/updated` | 会话生命周期、分支叶变化、归档 / 删除 / 恢复、标题、推理档位与模型线路变更。 |
| 队列 | `queue/updated` | 队列项新增、状态变化或投递结果；客户端应重读 `queue/list`，不要把通知本身当成完整队列快照。 |
| 上下文 | `context/compacted`、`context/compactionStarted`、`context/compactionProgress`、`context/compactionCompleted`、`context/compactionFailed`、`context/edited` | 摘要任务进度 / 终态、上下文已压缩与消息上下文编辑。任务详情仍经 `context/compact/read` 核对。 |
| 宿主连接 | `harness/disconnected`、`harness/connectionStatus`、`kernel/hookError`、`kernel/shutdown` | 宿主连接状态、hook 诊断与关闭生命周期观测。连接状态由宿主发布；内核通知流中的同名帧不应覆盖宿主状态；`kernel/shutdown` 仅在宿主注入事件观察 hook 时发送，不能作为进程退出信号。 |

`ServerNotifications` 是方法名常量，不是完整参数 schema；方法参数仍以 `packages/protocol` 的类型和对应读取接口为准。

## 构建前静态检查

`scripts/check_*.py` 是一组静态检查：CI 的 Source build 在安装依赖前逐个运行，任一失败即终止构建；本地用 `npm run check` 按文件名顺序运行全部（通常在数秒内完成），遇到第一个失败即停止并沿用其退出码，也可以单独运行某个脚本。`npm run check` 默认使用仓库根目录的 `.venv/bin/python`，设置 `PYTHON` 环境变量可改用其他 Python 3.11+ 解释器；它是 POSIX shell 循环，不安装依赖。这些脚本只读取源码、配置与文档（`check_versions.py` 与 `check_search_unicode.py` 另调用本机的 `npm` / `node`），不联网，不调用模型、招聘 CLI 或招聘平台；通过只说明已登记的不变量没有被改动，不代替运行时验证、真实平台或安装包验收。

各脚本的核对范围只在本节维护；README、贡献约定与发布约定链接到这里，不再各自抄写清单。新增检查脚本时须接入 `.github/workflows/build.yml` 并在本节补充同名小节，两处分别由 `check_workflows.py` 与 `check_docs_links.py` 核对。

| 领域 | 脚本 |
| --- | --- |
| 版本与发布元数据 | [`check_versions.py`](#check_versionspy)、[`check_release_assets.py`](#check_release_assetspy) |
| 协议与传输 | [`check_protocol.py`](#check_protocolpy)、[`check_item_content.py`](#check_item_contentpy) |
| 桌面与 IPC 安全 | [`check_desktop_security.py`](#check_desktop_securitypy) |
| 内核工具与审批 | [`check_harness_tools.py`](#check_harness_toolspy)、[`check_tool_schema.py`](#check_tool_schemapy)、[`check_tool_results.py`](#check_tool_resultspy)、[`check_toolkit.py`](#check_toolkitpy)、[`check_approval.py`](#check_approvalpy)、[`check_loop_guard.py`](#check_loop_guardpy) |
| 执行循环与队列 | [`check_queue_steer.py`](#check_queue_steerpy)、[`check_catchup_boundary.py`](#check_catchup_boundarypy)、[`check_request_identity.py`](#check_request_identitypy)、[`check_queue_view.py`](#check_queue_viewpy)、[`check_task_ownership.py`](#check_task_ownershippy) |
| 模型线路 | [`check_model_disable.py`](#check_model_disablepy)、[`check_request_policy.py`](#check_request_policypy)、[`check_usage.py`](#check_usagepy) |
| 启动自检 | [`check_startup_diagnostics.py`](#check_startup_diagnosticspy) |
| 上下文保留提示 | [`check_context_keep.py`](#check_context_keeppy)、[`check_summary.py`](#check_summarypy) |
| 本地资源与隐私 | [`check_private_files.py`](#check_private_filespy)、[`check_export_privacy.py`](#check_export_privacypy)、[`check_skills.py`](#check_skillspy)、[`check_workspace_instructions.py`](#check_workspace_instructionspy)、[`check_attachments.py`](#check_attachmentspy)、[`check_hooks.py`](#check_hookspy)、[`check_persistence.py`](#check_persistencepy)、[`check_settings.py`](#check_settingspy) |
| 连接与浏览器来源 | [`check_browser_source.py`](#check_browser_sourcepy)、[`check_connection_lifecycle.py`](#check_connection_lifecyclepy)、[`check_connection_report.py`](#check_connection_reportpy) |
| 关闭与中止 | [`check_shutdown.py`](#check_shutdownpy)、[`check_bridge_lifecycle.py`](#check_bridge_lifecyclepy) |
| 搜索 | [`check_search_unicode.py`](#check_search_unicodepy)、[`check_search_snippet.py`](#check_search_snippetpy) |
| 工作流与文档 | [`check_workflows.py`](#check_workflowspy)、[`check_docs_links.py`](#check_docs_linkspy) |

### `check_versions.py`

`scripts/check_versions.py` 核对版本一致性：npm 根包 / 工作区 / 锁文件、Python 包版本、`CHANGELOG.md` 首条、全部版本条目严格递减与日期合法非递增、使用指南版本行以及 npm 实际发现的工作区列表。同一脚本还核对许可证与包元数据：根包与全部 npm 工作区的 `license` 必须为 `MIT`，`harness/pyproject.toml` 的 `project.license` 为 `MIT` 且 `license-files` 恰为 `["LICENSE"]`，`LICENSE` 以 `MIT License` 开头并包含 MIT 许可正文；根包的 description / private / repository / homepage / bugs / engines.node，全部工作区的 private 与非空 description，以及 Python 的 readme / requires-python / keywords / project.urls / boss-harness 入口 / hatchling 构建与 wheel 包路径也必须保持。它需要 Node.js 24+ 与 Python 3.11+；成功时向 stdout 输出 Python 版本，Source build 复用该结果生成资产清单并核对隔离安装。

### `check_release_assets.py`

`scripts/check_release_assets.py` 核对发布资产清单守卫：`release_assets.py` 的清单 schema 版本、保留输出名、提交 / 时间 / SHA-256 格式、wheel 与 sdist 的文件名 / 元数据 / 根目录身份校验、输出目录归属、`O_NOFOLLOW`、inode 一致与重复文件名拒绝必须保留；CI 的 `Source build` 还必须保留清单生成命令与 `sha256sum -c SHA256SUMS.txt`。本检查不构建或发布资产，也不授予发布权限。

### `check_protocol.py`

`scripts/check_protocol.py` 在安装依赖前运行，失败时退出码 2。它核对十一类静态不变量：

- `ApplicationService._register()` 注册的方法集合与 `ClientMethods` 双向一致；
- 内核以字面量或模块常量发送的通知、`self.server.request` 字面量请求分别出现在 `ServerNotifications`、`ServerRequests` 中；
- 宿主在 `packages/app-client` 以 `method` 字面量发送的通知出现在 `ServerNotifications` 中；该常量中除内核静态发送、宿主发送与脚本 `DYNAMIC_KERNEL_NOTIFICATIONS` 显式登记的动态方法外，不得有未登记发送方的条目；
- 桌面主进程和渲染层以 `method` 字面量比较或构造、且含 `/` 的方法名出现在 `ClientMethods` 或 `ServerNotifications` 中；
- `on_initialize` 返回的 `capabilities` 键与 `InitializeResponse.capabilities` 的布尔字段一致；
- `RENDERER_METHODS` 是 `ClientMethods` 的子集，仅主进程方法在脚本的 `MAIN_ONLY_METHODS` 中显式登记，`THREAD_METHODS` 是渲染层方法的子集；
- 内核 `protocol.py` 的 `PROTOCOL_VERSION` 与协议包常量相同，且 `application.py` / `session_export.py` 不重复定义；
- 宿主与桌面源码中的 `protocolVersion ?? "…"` 默认值必须引用 `PROTOCOL_VERSION`，不得另立协议版本字面量；
- 根 `package.json` 声明的工作区源码导入 `@boss-harness/*` 时，对应包必须出现在该工作区的 `dependencies` 或 `devDependencies` 中；
- 内核 `rpc.py` 的 `MAX_FRAME_BYTES` 是正整数常量表达式，app-client 的 `maxFrameBytes` 默认值与它相等且全部默认字面量唯一，`maxQueuedBytes` 默认值不小于帧上限；
- 内核 `rpc.py` 的错误分发必须先用 `describe_failure` 处理未捕获异常再脱敏：保留 `OSError` 与文件名判定、`errno.errorcode` 与通用说明、`操作未完成` 文案，登记 `ENOSPC`、`EDQUOT`、`EACCES`、`EPERM`、`EROFS`、`EMFILE`、`ENFILE`、`ENOTDIR`、`ENOENT` 九种 errno，且不得再直接使用 `redact_secrets(str(exc))`；入口 `__main__.py` 的索引修复失败、启动失败、模型线路构造兜底与浏览器来源配置失败四处输出必须经过 `_failure_text`（先 `describe_failure` 再 `redact_secrets`），且不得再有把异常原文直接写到 stderr 的行；具名 `ModelConfigError` 的固定说明除外。

检查是静态扫描：通过变量拼接的方法名、运行时注册或动态生成的字段不在覆盖范围；新增此类路径时仍需人工核对协议常量。

### `check_desktop_security.py`

`scripts/check_desktop_security.py` 扫描桌面主进程、preload 与渲染层的安全边界，按主题核对：

- **窗口隔离**：`apps/desktop/src/main` 中的 `webPreferences` 对象字面量必须核对主窗口与平台登录视图的隔离、沙箱、Node 集成、Web 安全、登录视图 `devTools` 等设置；出现未登记文件或布尔值不符时以文件名与配置项失败。
- **权限与导航**：`permissionPolicy.ts` 的主窗口权限白名单恰为 `clipboard-sanitized-write`，判定函数必须保留请求 URL 非空、权限命中白名单与来源受信三项；两处主进程视图都注册权限请求 / 检查处理器，`setWindowOpenHandler` 返回 `deny`，`will-attach-webview` 调用 `preventDefault`。主窗口的 `will-navigate` / `will-frame-navigate` 处理器必须调用 `isTrustedRendererUrl` 并阻止不符合的导航；登录视图的 `will-navigate` / `will-frame-navigate` / `will-redirect` 必须调用 `isOfficialLoginUrl`（后两者还须限定主框架），`will-prevent-unload` 必须阻止卸载。主窗口两个权限处理器都调用 `allowsMainWindowPermission`，平台登录处理器显式拒绝；登录视图只允许使用 `session.fromPartition(` 创建的独立分区，不得落到默认会话。
- **preload 桥接**：preload 必须经 `contextBridge.exposeInMainWorld` 暴露 API，不得直接暴露 `ipcRenderer`；暴露调用必须恰好一次且为 `exposeInMainWorld("boss", api)`，非相对导入只允许 `electron` 与 `@boss-harness/*` 已知模块。preload 源码也不得出现 `process.env`、`process.exit`、`process.argv` 或 `process.cwd`，避免环境变量、启动参数或工作目录经桥接暴露；当前仅通过 `process.versions` 与 `process.platform` 暴露只读版本信息。
- **桥接类型**：桥接面由 `preload/bridge.ts` 的 `BossBridge` 统一导出：preload 的 `api` 显式标注该类型，`env.d.ts` 只声明 `boss: BossBridge`，方法列表不再在两侧重复；`DesktopHarnessStatus` 也复用 `HarnessConnectionStatus`。
- **渲染层入口**：`apps/desktop/src/renderer` 下的 `.ts` / `.tsx` 源码不得出现 `ipcRenderer`、直接导入 `electron` / `node:*` 或使用 CommonJS `require(`，只能经 `window.boss` 使用桥接 API。`index.html` 必须保留 CSP meta：`default-src` 与 `script-src` 恰为 `'self'`，任何指令不得含 `'unsafe-eval'`、`*` 或 `://` 远程来源，且不得出现无 `src` 的内联脚本；入口必须恰好包含一个 `type="module"` 的 script，`src` 指向本地 `./src/` 模块。入口也不得包含 `iframe` / `webview` / `object` / `embed` 嵌入元素，`src` / `href` / `action` 不得引用远程或协议相对 URL。渲染层源码还不得出现 `dangerouslySetInnerHTML`、`innerHTML` 或 `outerHTML` / `insertAdjacentHTML`，也不得使用 `eval(` 或 `new Function(`。
- **进程边界**：导入方向是单向的：主进程不得导入 `../renderer` 源码，preload 不得导入 `../main` 源码，跨进程只经文件路径与桥接通信。进程角色符号同样单向：主进程源码不得出现 `ipcRenderer`，preload 源码不得出现 `ipcMain`。主进程源码也不得出现 `executeJavaScript` 或 `debugger`，避免绕过桥接向渲染层注入代码、接管调试通道或遗留调试语句。
- **子进程**：主进程只允许 `startupCheck.ts` 调用 `spawn(`，app-client 只允许 `index.ts` 调用 `spawn(`，两处都必须显式设置 `shell: false`，避免命令经 shell 解析。两个区域的 `node:child_process` 导入只允许具名 `spawn` 与 `type` 类型，不得默认导入、命名空间导入或动态导入；源码也不得调用 `exec`、`execFile`、`execSync`、`execFileSync`、`spawnSync` 或 `fork`，避免回退到经 shell 解析参数或执行任意模块的入口。
- **IPC 通道**：脚本解析 preload 的 `ipcRenderer.invoke` / `on` 与主进程 `ipcMain.handle`、`send` / `sendWhenLoaded` 通道，要求 invoke 与 handle、订阅与发送集合完全一致，同一通道不得重复注册，调用处的通道必须写成双引号字符串字面量（模板字符串或变量会失败），每个 handle 处理器必须以 `trustedSender(event)` 开头，剥离大括号后不得先做其它工作；`session-export:save` 还必须保留 `validateSessionExportRequest(payload)`、`validateThreadExportResponse(response, request)`、`writeSessionExport(choice.filePath, exported.content)` 与以 `basename(choice.filePath)` 返回文件名；保存对话框还必须保留 `createDirectory` 与 `showOverwriteConfirmation` 属性。
- **发送方校验**：`trustedSender` 自身还必须校验发送方属于已登记窗口、当前帧为主框架、入口 URL 受信，并在窗口 / 主框架不满足与来源不满足时分别抛出。脚本还固定 `isTrustedRendererUrl` 与 `isOfficialLoginUrl` 的关键判定：开发来源 / 路径与 `file:` 入口比较，以及 `https:`、拒绝 userinfo、443 端口、`zhipin.com` 精确主机与子域后缀。
- **自检通道**：`harness:startup-check` 的处理器只允许声明 `event` 参数，主体必须从模块级 `startupCheckTarget` 取目标、目标缺失时返回固定的 `spawn` 不可用结论、经 `ManualStartupCheck.request` 共用在途请求、先 `await diagnostics?.settled()` 再 `runStartupCheck(target, signal)`；`before-quit` 处理器须在确认退出之后调用 `manualStartupCheck.cancel()`，结束在途的自检进程；preload 的 `runStartupCheck` 与 `bridge.ts` 签名都不得有参数，preload 只能以单个通道实参调用该通道，渲染层调用点不得传参。手动自检的解释器、工作目录与环境始终来自主进程启动配置，渲染层无法借该通道选择要执行的程序。脚本还核对解释器选择：显式配置优先，自动候选须为普通文件且通过执行权限检查，否则回退 `python3`；此检查不启动候选。
- **外链与会话恢复**：渲染层 `RichMarkdown.tsx` 的 `EXTERNAL_SCHEMES` 与 `security.ts` 的 `isAllowedExternalUrl` 必须非空且集合一致，渲染层的 `externalTarget` 还必须保留 `EXTERNAL_SCHEMES.includes(` 与 `new URL(url).protocol` 判定；`window.ts` 的 `openExternal` 必须先调用 `isAllowedExternalUrl` 再交给 `shell.openExternal`，`setWindowOpenHandler` 调用该封装而不是直接打开；`shell.openExternal` 只允许在该函数中出现一次。脚本还核对渲染层会话恢复边界：`harnessReplica.ts` 必须保留分页与正文预算常量，以及内容引用的编码、SHA-256、线程 / 条目 / 快照标识、`part`、字符与 UTF-8 字节关系（含 4 倍上限与 16 MiB 上限）判定。

检查是静态对象字面量与文本扫描，动态生成或包装后的配置仍需人工核对。

### `check_harness_tools.py`

`scripts/check_harness_tools.py` 用标准库 AST 解析 `harness/src/boss_harness/tools/boss_cli.py` 的 `TOOLS` 元组：工具名必须恰为 14 个已登记名称且不重复，其中 13 个只读，仅 `boss_hr_greet` 标记 `requires_approval: True`；每个工具必须带非空描述与 handler，`input_schema` 必须为 `type: object`、`additionalProperties: false`，`required` 只能包含已声明属性且不得重复。它还解析 `context.py` 的 `_WRITE_TOOLS`、`write_tools` 默认值与 `tool_results.py` 的 `LEGACY_WRITE_TOOLS`，要求三处写工具集合均恰为 `boss_hr_greet`。它同时核对 `tools/bundle.py` 保留 `handlers = tool_handlers()`、`approval_required = approval_required_tools()` 与 `for spec in TOOLS`，并要求 `name` / `description` / `input_schema` / `requires_approval` 从 spec 透传，组合层不得把审批标记改写为固定值。工具桥 `tools/boss_cli.py` 的 `Popen` 必须显式 `shell=False`，`BOSS_CLI_DATA_DIR` 必须去除首尾空白且把空值视为未设置，禁止把未规范化的值原样传给上游；`BOSS_CLI_BIN` 同样去除首尾空白并把空值视为未设置，禁止用未规范化的路径直接查找；`harness/src/boss_harness` 下任何 Python 文件出现 `shell=True`、`create_subprocess_shell(`、`os.system(` 或 `os.popen(` 都会失败。工具桥的输出上限固定为 `MAX_CLI_OUTPUT_BYTES = 16 * 1024 * 1024`，`BoundedProcessOutput` 必须接收该上限，`CLI_OUTPUT_LIMIT` 的失败说明必须保留「不要自动重试」；`process_io.py` 必须保留 64 KiB 分块、累计字节与上限比较、溢出标记、`BrokenPipeError` 处理与按 stdout / stderr / 可选 stdin 的收尾计数。检查读取源码字面量，不导入内核、不依赖已安装包；运行时生成的工具或动态 schema 仍需人工核对。

### `check_tool_schema.py`

`scripts/check_tool_schema.py` 核对工具参数边界：`tool_schema.py` 的关键字与类型集合、schema / 参数字节上限、JSON 节点 / 深度上限与规范化访问上限保持不变；根 schema 必须为对象，结构化字符串仅在按对应对象 / 数组 schema 解码且校验通过后才替换原值，参数校验失败统一转为受限错误。`tool_bundle.py` 必须保留工具名格式、描述非空、执行模式与审批互斥、结果预算范围、schema 冻结、注册表名校验与只读投影。检查是常量与文本扫描，运行时 schema 行为仍需按用户指南核对。

### `check_tool_results.py`

`scripts/check_tool_results.py` 核对工具结果分页与引用边界：`tool_results.py` 的内联 64 KiB / 单页 1 MiB 预算、默认 16,384 / 最大 32,768 码点与模型 8,192 码点必须保持不变，且满足 `MODEL_RESULT_READ_CHARS ≤ DEFAULT_RESULT_CHARS ≤ MAX_RESULT_CHARS`、单页预算低于内核帧上限；两条读取路径必须校验 `limit`，RPC 请求字段必须限定在 `threadId` / `itemId` / `sha256` / `cursor` / `limit`，摘要必须为 64 位小写十六进制，过期引用必须返回 `STALE_RESULT` 与 `currentRef`，游标必须校验前缀 `tr1_`、长度、条目归属与偏移。模型只读工具必须使用 `MODEL_RESULT_READ_CHARS` 上限、禁止额外属性，并透传当前引用与错误码。检查是常量与文本扫描，实际分页与读取行为仍需按用户指南核对。

### `check_toolkit.py`

`scripts/check_toolkit.py` 核对工具结果信封的校验、深拷贝与错误收敛边界：`toolkit.py` 的 `ToolResult` 必须保留 `ok` / `command` / `data` / `error` / `hints` / `raw` / `pagination` 七个字段及默认值；`snapshot_result` 只接受 `None`、`str`、`bool`、`int`、有限 `float`、键为字符串的 `dict` 与 `list`，嵌套最多 64 层；信封校验必须要求 `ok` 为布尔、`command` 非空、`raw` 为字符串、三个可选字段为 `dict` 或 `None`，错误信封的 `code` 非空且 `message` 为字符串；`recovery_action` 为 null 时按字段缺失规范化（下游按 `or ""` 读取，合法平台错误不会被替换为 `TOOL_ERROR`），其他非字符串值拒绝；信封必须显式构造并在 `ensure_ascii=False` 下经 JSON 往返深拷贝，任何异常统一收敛为同一个 `ValueError`。脚本反向断言不得整份展开宿主返回值、不得使用 `ensure_ascii=True`，并核对技术参考的深度与 `raw` 说明。检查是常量与顺序扫描，实际信封行为仍需按用户指南核对。

### `check_item_content.py`

`scripts/check_item_content.py` 核对条目正文的传输降级与分页边界：`item_content.py` 必须保留 64 KiB 内联阈值、默认 16 384 / 最大 32 768 码点、64 层投影深度与占位文本；孤立代理项必须替换为 U+FFFD、非有限浮点降级为 `None`，内联正文必须先经 `wire_text`；内容摘要必须按 `wire_text` 后的文本分块计算，超过内联阈值时写入 `textOmitted` / `thinkingOmitted` 与内容引用；读取必须校验 `limit`、64 位摘要、32 位 `snapshotId`、`ic1_` 前缀与 2048 字符上限、线程 / 条目 / 字段 / 摘要 / 快照的归属与 offset 范围，过期引用返回带 `currentRef` 的 `STALE_CONTENT`。脚本同时核对桌面指南的大正文恢复说明。检查是常量与文本扫描，实际降级、分页与渲染行为仍需按桌面指南核对。

### `check_approval.py`

`scripts/check_approval.py` 核对审批裁决边界：`application.py` 的请求必须只有 `approvalId` 与有界 `approved`，遍历活动 runner 时调用持久回调，并将服务端请求取消与恢复 / 执行中回执分开；`agent.py` 只在未裁决、未取消且未过期时接受决定，并在回合清理时丢弃待决集合；`session.py` 必须校验审批 id 格式、索引唯一性、归档与 owner 状态、重复冲突和到期判定。脚本是源码扫描，不执行工具或验证真实用户裁决。

### `check_loop_guard.py`

`loop_guard.py` 只在单次 `TurnRunner.run()` 内观察已执行工具调用：工具名与规范化参数的 SHA-256 摘要一致时累计，命中第 3、5 次后向模型追加一条合成 `UserMessage` 提醒。该提醒不阻断工具执行、不含参数或结果、不写入会话条目、不跨回合保留；用户 steering 注入或不可安全观察时立即重置。两个 provider 都把工具结果后的用户消息按既有顺序序列化，无需新增协议字段。

`scripts/check_loop_guard.py` 固定重复调用提醒的阈值 `(3, 5)`、512 字符上限与 64 KiB 规范化参数上限；`_argument_digest` 必须规范化排序、禁用 NaN、不可安全序列化时回退，`observe` 只按工具名与参数摘要计数，提醒不含参数或结果。脚本还核对 `agent.py` 在工具结果之后、仍有下一次模型请求时观察，且 steering / 无调用后续消息路径会重置。它不执行模型、不写入会话，也不验证模型是否真的响应提醒。

### `check_queue_steer.py`

`scripts/check_queue_steer.py` 为 `queue/steer` 提供专项源码守卫：内核侧核对 `promote_to_steering` 只接受 `queued` 的 `followUp`、拒绝技能 / 自动压缩覆盖，并通过持久 `_save` 保留原 id、正文与请求编号；`on_queue_steer` 必须校验 active turn、`expectedTurnId`、取消状态与 `STEER_UNAVAILABLE`。脚本还核对 `queueSteer` 能力、协议参数类型、主进程两份白名单与方法参数校验、RPC 错误保留、渲染层 bridge 与面板按钮状态。它是 AST 与文本扫描，不替代状态机探针或真实桌面操作。

### `check_catchup_boundary.py`

`scripts/check_catchup_boundary.py` 核对摘要后补领转向的提交批次、最终请求指纹与续接拒绝条件；它是 AST 与文本扫描，不替代真实模型或桌面操作。

### `check_request_identity.py`

`scripts/check_request_identity.py` 核对请求身份的校验、去重与冲突边界：`request_identity.py` 的 `clientUserMessageId` 必须整串匹配 `[A-Za-z0-9_-]{1,128}`，无效格式直接拒绝；持久记录的 `queueId` / `turnId` 链接必须经类型校验后参与两轮收敛，队列记录必须与 `queue/list` 共用 `queue_record` 契约；转向类型冲突、不同输入与身份歧义必须分别以 `CLIENT_REQUEST_CONFLICT`、`CLIENT_REQUEST_AMBIGUOUS`、`REQUEST_REQUIRES_REVIEW` 拒绝；输入摘要按 UTF-8 原文计算，持久事实不一致或「未启动却已完成」的回合必须要求核对。脚本同时核对技术参考与使用指南的请求身份说明。检查是常量与文本扫描，实际去重与恢复行为仍需按用户指南核对。

### `check_queue_view.py`

`scripts/check_queue_view.py` 核对队列读取投影的上限与截断边界：`queue_view.py` 的待处理项上限 200、已终结窗口 50、正文预览 600 字符、可选字符串与队列 id 上限 200、技能 10 项，以及 `_QUEUE_VIEW_FIELDS` 白名单必须逐字段声明（禁止把持久记录整份透传）；`queue_record` 必须校验 `kind` / `status` / `id` 并把编码失败降级到 `wire_value`，仍不可编码时按坏记录跳过；`queue_view_record` 只删除类型不符的可选字段，暂停来源必须是内核枚举，`executionStarted` 只接受 `False`；`project_queue` 必须先保留暂停项再用剩余名额容纳排队 / 投递中项，正文截断时标注 `inputTruncated`，分类计数在调用方传入时不得改由有界子集重算。脚本同时核对技术参考与使用指南的队列读取说明。检查是常量与顺序扫描，实际投影结果仍需按用户指南核对。

### `check_task_ownership.py`

`scripts/check_task_ownership.py` 核对任务读取的归属判定与恢复策略：`task_ownership.py` 的标识符必须整串匹配 `[A-Za-z0-9][A-Za-z0-9_-]{0,127}`，回合与队列快照默认最多 257 项，任务阶段只接受 `admission` / `prepare` / `model_request` / `tool_execution` / `finish` 与终态枚举，`attempt` / `restartLimit` 必须在 1–1 000 与 0–32 内，恢复原因限定 `processExit` / `terminalStateRecovered`、恢复策略限定 `manual` / `closed` 且只在 `finish` 阶段按终态采纳；同一队列记录的身份字段（`kind` / `inputDigest` / `expectedTurnId` / `clientUserMessageId`）在多份快照间变化必须判为冲突；`delivered_as` 需要队列回执、回合记录与用户消息引用三者一致，`targets` 需要 `expectedTurnId` 指向已知回合且投递状态有对应引用，多链接、重复回合或回执不一致一律 conflict；摘要关系只在 `threadId`、checkpoint 与唯一回合一致时 resolved，无归属时区分 `independent` 与 unresolved；`recovery_policy` 对缺失、未知或损坏状态必须优先返回 `manual_review`，进程持有返回 `process_owned`，队列排队返回 `queue_pending`。脚本反向断言标识符不得改用 `search`、用户消息引用不得投影正文，并核对技术参考与使用指南的任务读取说明。检查是常量与顺序扫描，实际归属结果仍需按用户指南核对。

### `check_model_disable.py`

`scripts/check_model_disable.py` 核对显式 `none`（`--provider none` 或 `BOSS_HARNESS_PROVIDER=none`）禁用模型调用的进程级边界：`ApplicationService` 的构造校验、模型目录发现门禁、`_configured_route` 的拒绝提示、`_provider_for` 对真实线路的最后拦截、`_summary_available` 的显式禁用与独立 Anthropic 环境凭据判定（不重新解析配置或创建供应商）、摘要线路解析门禁、分支摘要与续接预检的拒绝提示，以及入口 `_requested_provider` 与启动自检 `MODEL_DISABLED` / `MODEL_NOT_CONFIGURED` 的措辞；自动回退提示只在本机 OpenAI 线路按同一套解析（含命令行 `--model`）可读通且 `openai` 包可发现时点名该线路，解析失败保持通用建议，缺包时改为安装提示。它还核对结构边界：`provider_factory` 在 `application.py` 只经 `_provider_for` 调用、在 `connections.py` 只经 `_run` 调用，`build_provider` 只允许入口调用，`AnthropicProvider` / `OpenAIResponsesProvider` 只允许在 `models/provider.py` 构造，`ApplicationService` 在构造连接检查时传入进程级开关，`ConnectionChecks` 仅对 `none` 默认线路接受启用该开关，并给显式禁用的模型卡片标注 `MODEL_DISABLED`。模型卡片为 `disabled` 时在启动检查线程前直接返回报告。脚本同时核对模型值的回退。启动和自检的回退提示都把 `--model` 交给 `resolve_config`，只在去除首尾空白后仍非空时覆盖通用模型变量。两条线路都经 `_configured_model` 从环境中取第一个去除首尾空白后仍非空的值；自动线路判断、模型目录发现、摘要线路解析与自检共用 `has_anthropic_credential`：只有两项凭据都去除首尾空白后仍为空才视为未配置，`application.py` 不得直接读取凭据变量。脚本还核对 Anthropic 凭据的交付方式：环境里的两项凭据先去除首尾空白，只有非空值才显式传给 SDK，纯空白 `ANTHROPIC_API_KEY` 不遮蔽真实 `ANTHROPIC_AUTH_TOKEN`；让 SDK 直接读取未处理环境变量的裸构造会被拒绝。它是静态扫描，不证明运行时行为；嵌入方自带的 `provider_factory` 不经入口，不在该脚本的边界内，仍受 `_provider_for` 的结构拦截约束。

### `check_request_policy.py`

`scripts/check_request_policy.py` 核对模型请求策略的拒绝投影与脱敏边界：拒绝载荷必须只保留 purpose / provider / model / requestIndex / threadId / turnId / jobId，并把 `errorInfo.source` 记为 `request_policy`，同时带 `requestRejected: true`、`outputObserved: false` 与 `contextRecoveryEligible: false`；历史单元预览必须把用户文本截到 1 000 字符并脱敏、工具名最多 64 个；转换必须按整单元丢弃、取消优先；`check_model_request` 必须先把任务身份写入最终请求，并在 hook 允许后才放行；两条拒绝路径都必须先经 `redact_secrets` 再抛出；`model_error` 记录必须按 `recorded` 只写一次。脚本同时核对技术参考中的策略拒绝与取消优先级说明。检查是常量与文本扫描，实际 hook 行为仍需按技术参考核对。

### `check_usage.py`

`scripts/check_usage.py` 核对 provider 用量汇总的校验、来源与缓存估算边界：`usage.py` 的单次请求上限 50 000 000、四个 token 字段与两个线路的 `_REPORTED` 能力表（OpenAI 缓存 input 是子集、Anthropic 缓存读写独立计数）、七类未验证原因（`unknownProvider` / `missing` / `invalidType` / `negative` / `outOfRange` / `inconsistent` / `zero`）与 `unreportedRequests` 只来自 `missing`；来源列表 8 条、provider 64 字符、model 200 字符上限与 `wire_text` 降级；摘要任务窗口 50 条、`summaryJobCount` 与 `summaryJobsTruncated`；缓存未命中只按日志视图、`CACHE_MISS_FLOOR = 1024` 与 `min(previousPrompt, prompt) - cacheRead` 估算，checkpoint 与分支摘要重置基线，分支视图不报告 `cacheWaste`。费用没有可信价目来源，`costUsd` 必须保持 `None`。脚本同时核对技术参考与使用指南的用量说明。检查是常量与顺序扫描，实际计数仍需按用户指南核对。

### `check_startup_diagnostics.py`

`scripts/check_startup_diagnostics.py` 核对启动自检文本与桌面解析上限的一致性：`startup_check.py` 的每个 `_check(...)` 调用必须给出来自桌面 `NAME_PATTERN` / `CODE_PATTERN` 的固定名称与检查码、合法状态，以及不超过桌面 `MAX_TEXT_LENGTH`（按 UTF-16 码元计数）且不含控制字符的说明与建议；动态文本只允许来自已单独校验的来源（`_model_check` 的 `exc` 与回退提示、`_runtime_check` 的运行参数表项）。脚本还用 AST 核对 `_RUNTIME_OPTIONS` 四元组、`_DIAGNOSTICS` 二元组的全部文本，`ModelConfigErrorCode` 与 `_DIAGNOSTICS` 键集合双向一致，`_unconfigured_hint` 只返回三条已登记的提示常量（通用、OpenAI 线路可用、缺少 `openai` 包），点名线路前用 `find_spec` 确认包可发现；桌面 `startupCheck.ts` 的解析防护（字段名 / 检查码 / 状态 / 文本校验、`MAX_TEXT_LENGTH`、`ok` 一致性、报告与检查数量上限）与 `StartupCheckEntry` 协议字段作为文本片段核对。脚本还解析 `docs/USER_GUIDE.md` 的模型配置错误、目录错误与运行参数三张检查码表，分别与 `_DIAGNOSTICS` 键、`_state_check` 的错误码与 `_RUNTIME_OPTIONS` 的检查码集合双向一致，并确认内核可能输出的全部检查码都出现在使用指南中；`SETUP.md` 的检查结果表同样纳入核对，表内检查码必须由内核实际产出，`PREFIX_*` 通配至少匹配一个内核检查码，表不得为空或重复。脚本还核对 `__main__.py` 的严格模式：`--strict` 参数定义、与 `--check` 的绑定报错、报告先输出、错误优先返回 2、再按 `warning` 状态返回 1 的片段必须各出现一次且保持顺序，使用指南必须保留三种退出码的说明。`--state-dir` 的非空校验、`--listen` 的端点校验及各自的固定说明必须位于自检与索引修复分支之前，使相同参数下的自检结论与实际启动一致。脚本还核对 `startup_report()` 的检查项名称与顺序：桌面 `connectionNotice.ts` 的 `CHECK_TITLES` 键按同一顺序一致，中文标签与使用指南「检查项」表格的行按同一顺序一致。警告优先级同样核对：`_state_check` 必须按 `STATE_DIRECTORY_IN_REPO`、`STATE_DIRECTORY_TILDE`、`LEGACY_STATE_ENV_PRESENT`、`STATE_DIRECTORY_LOW_SPACE` 的顺序报告。运行参数顺序也纳入核对：按源码顺序收集 `ApplicationService.__init__` 中以 `from_environment` 结尾的读取调用，要求与 `_RUNTIME_OPTIONS` 的加载函数逐项一致，使 `--check` 报告的第一个错误与实际启动相同。审批期限由 `approval_timeout_from_environment` 统一解析，启动与自检共用；显式值无效时启动回退默认 300 秒，自检在其余参数有效时报告 `APPROVAL_TIMEOUT_DEFAULTED` 警告。模型重试配置同样由 `retry_settings_from_environment` 统一解析，返回生效次数、基础退避与显式值是否原样生效；非整数回退默认值，越界或负数收敛到边界，自检在审批期限有效时报告 `RETRY_CONFIG_DEFAULTED` 警告。`render_text` 也纳入核对：只能按固定字段读取报告与检查项，不得访问环境、文件、进程或打印 API，`_STATUS_TEXT` 覆盖三种状态并保留「说明」「建议」结构，检查项标题取自 `_CHECK_TITLES` 并要求与桌面 `CHECK_TITLES`、使用指南检查项标签三方一致，使复制到 Issue 的自检文本只含已校验内容。脚本还从 `render_text` 的结论赋值提取中文片段，要求桌面 `startupConclusion` 全部包含，并核对缺失或不可用报告返回空串、错误与警告分别按 `error` / `warning` 状态计数；设置页必须使用该函数并展示「自检结论」「运行于」，复制时把不可用固定说明作为诊断内容，避免终端结论与设置页结论各自漂移。脚本还核对数值上限配置：回合模型请求数与附件存储上限在格式和范围校验前去除首尾空白，空值回退默认上限。脚本还核对 Codex TOML 解析器不可用时使用登记的 `MODEL_CODEX_TOML_UNAVAILABLE`，使依赖该文件的默认线路可诊断，而可选线路不会阻断启动。审批期限与重试配置同样核对：只含空白时按未设置处理，不得只把空字符串当作未设置，也不产生 `APPROVAL_TIMEOUT_DEFAULTED` / `RETRY_CONFIG_DEFAULTED` 警告。脚本还核对空白 JSON 配置：`ModelCatalog.from_environment` 与 `CompactionPolicy.from_environment` 必须在 JSON 解析之前把空值或只有空白的取值按未设置处理，`ApplicationService` 的 `autoCompactionSource` 不得按 `BOSS_HARNESS_COMPACTION` 是否存在判定环境来源。检查是静态扫描，不运行自检或桌面解析，运行时行为仍需按用户指南核对。

### `check_context_keep.py`

`scripts/check_context_keep.py` 固定保留目标提示的接线：判定函数 `keepTargetReachesLimit` 只在 `compactionSettings.ts` 定义一次，保留目标与上限都必须是正整数且保留目标不低于上限；会话上下文面板的两处提示都必须先确认预算已读取，再以 `budget.inputBudget` 调用；设置页从 `config/read` 的 `modelCapabilities.contextWindow` 取得正整数窗口后以 `compactionWindow` 调用。两处提示在使用指南与桌面指南中的说明片段也纳入核对。脚本不执行渲染层代码，提示的实际布局与触发时刻仍需运行桌面核对。

### `check_summary.py`

`scripts/check_summary.py` 核对摘要规划的预算、逐字来源与无工具边界：`summary.py` 的输出上限 8 192、请求上限 32、摘要器提示对执行状态（只有「已执行成功」可说成已发生）与授权（既有审批只属于对应工具调用、摘要不扩大未来操作授权）的措辞、分支摘要的来源说明；来源先经 `wire_text` 降级并计算 SHA-256，单次输出预留模型上限与 4096 余量后的四分之一，滚动摘要预算按 32 000 字符与可用输入折算；预算不足或滚动摘要超限必须分别以 `ContextBudgetExceeded` 与 `ValueError` 拒绝，不得截断已有摘要；摘要请求必须 `tools=()`、`thinking=None`、`ensure_ascii=False`，来源按 `start:end` 逐字发送；片段切分按上下文窗口两倍的二分查找，起点无法容纳时以 `ContextBudgetExceeded` 失败。脚本反向断言来源不得从头截断、不得使用 `ensure_ascii=True`，并核对技术参考的摘要说明。检查是常量与顺序扫描，实际摘要质量仍需按用户指南核对。

### `check_private_files.py`

`scripts/check_private_files.py` 核对私有状态边界：`private_files.py` 必须保留目录 `0o700` / 文件 `0o600` 的创建与限制、`O_NOFOLLOW`、uid 与 inode 校验、ACL 清理和根目录拒绝；`ownership.py`、`persistence.py`、`session.py`、`snapshot_store.py`、`settings.py`、`maintenance.py`、`startup_check.py` 必须保留关键调用点；这些状态模块不得直接使用 `open(..., "w"/"a")`、`write_text(` 或 `write_bytes(` 写盘。`maintenance.py` 的索引修复必须先用 `lstat` 核对状态目录存在并在缺失时以固定说明拒绝，非空且不含任何状态标志（占用锁、`sessions`、`state.sqlite3`）的目录同样拒绝，再获取占用锁与创建备份目录，顺序与标志集合由脚本核对。检查是静态文本扫描，符号链接与权限的运行时行为仍需按平台核对。

### `check_export_privacy.py`

`scripts/check_export_privacy.py` 核对会话导出的默认脱敏边界：`session_export.py` 的 `EXPORT_FORMATS` 必须恰为 `markdown` / `json` / `html`，三个字节上限必须满足 `MIN_EXPORT_BYTES ≤ DEFAULT_EXPORT_BYTES ≤ MAX_EXPORT_BYTES` 且最大值低于 1 MiB；`application.py` 的 `thread/export` 请求字段白名单必须包含且只包含 `threadId`、`view`、`format`、`includeToolResults`、`maxBytes`，且 `includeToolResults` 默认 `False`；主进程 `security.ts` 的 `EXPORT_MAX_BYTES` 必须与内核 `MAX_EXPORT_BYTES` 相等，并保留按 UTF-8 字节数核对导出正文长度的判定；`session_export.py` 必须保留 `redact_secrets(` 与凭据、环境变量、本机路径、候选人信息四个脱敏标记，并且 `sensitive()` / `personal()` 的脱敏步骤与顺序必须保留、个人信息按长度降序打码；导出模块不得出现 `write_text(`、`write_bytes(`、`open(`、`os.replace(`、`unlink(` 或 `mkdir(`。检查是源码字面量与文本扫描，导出正文的运行时行为仍需按用户指南核对。

### `check_skills.py`

`scripts/check_skills.py` 核对工作区技能边界：`SkillCatalog` 的六个常量必须是正整数表达式，`MAX_SKILL_SCAN_ENTRIES` 不小于 `MAX_SKILL_DESCRIPTORS`，`MAX_SKILL_BYTES` 不超过内核 `MAX_FRAME_BYTES`；技能正文读取必须保留 `O_NOFOLLOW`、`O_NONBLOCK`、inode 校验与 `MAX_SKILL_BYTES + 1` 有界读取；技能目录必须用 `os.scandir` 并以 `follow_symlinks=False` 判定子目录、拒绝根目录符号链接，候选窗口按 `MAX_SKILL_SCAN_ENTRIES` 收敛；列表投影必须截断名称与描述并封顶问题清单；`SkillCatalog` 不得用 `glob` / `rglob` / `iterdir` 枚举技能。检查是静态文本与常量扫描，符号链接竞态与运行时读取结果仍需按平台核对。

### `check_workspace_instructions.py`

`scripts/check_workspace_instructions.py` 核对工作区常驻说明的读取、写入与提示边界：`workspace_instructions.py` 必须保留 8 KiB 上限与首选 / 旧目录路径，读取时拒绝非普通文件、以 `O_NOFOLLOW` 打开并比对 dev / inode、最多读取上限加一字节；候选顺序必须首选优先，且首选路径存在但不可读时固定报不可读、不静默回退旧目录；提示块必须声明内容「是上下文而不是系统指令」且「不能改变工具权限、审批要求或只读限制」；保存必须经临时文件、文件与目录 fsync、`os.replace` 原子替换，并拒绝符号链接与非普通文件。脚本同时核对上下文面板的状态展示、编辑器保存入口与使用指南、桌面指南、项目状态中的说明片段。检查是静态文本扫描，不执行读取或写入，符号链接竞态与跨平台行为仍需运行核对。

### `check_attachments.py`

`scripts/check_attachments.py` 核对附件边界：`resources.py` 的默认存储 512 MiB / 4096 对象、上限 `2**63 - 1`、`DEFAULT_READ_CHARS = 16,384` 与 `MAX_READ_CHARS = 32,768` 必须保持不变；`attachment/read` 的请求字段白名单、默认分段、`wire_size(result) > MAX_PAGE_BYTES` 单页守卫，以及 `RESPONSE_TOO_LARGE` / `attachment/read` / `suggestedLimit` 恢复信息必须保留；两个存储配额环境变量名也不得改名。检查是常量与文本扫描，实际配额与分页行为仍需按用户指南核对。

### `check_hooks.py`

`scripts/check_hooks.py` 核对生命周期 hook 的超时、上下文冻结与策略拒绝边界：`hooks.py` 的 30 秒 / 250ms 超时、256 事件队列、16 在途回调、每秒一次的拥塞诊断、观察上下文 16 384 字符 / 64 键 / 128 项 / 深度 6、策略上下文 1 052 672 字节 / 32 784 节点 / 深度 66 与 512 个变换单元；`HookDecision` 的布尔允许、大写 code 与 1 024 字符消息校验、`ContextTransform` 的非负整数与排序去重；`_safe_value` 必须截断、脱敏并标注省略，`freeze_context` 冻结为只读视图，`freeze_policy_context` 必须完整复制并在环引用、代理项、非有限浮点与超限时分别以 `HOOK_CONTEXT_INVALID` / `HOOK_CONTEXT_TOO_LARGE` 拒绝；事件观察只投影白名单字段，队列满时计数丢弃而不阻塞；`_invoke` 必须先检查取消再检查关闭与容量，超时使用 25ms 轮询且迟到返回不改写回合；策略与请求路径必须把 `HOOK_CLOSED` / `HOOK_CONTEXT_TOO_LARGE` / `HOOK_CONTEXT_INVALID` / `HOOK_BUSY` / `HOOK_ERROR` / `HOOK_RESULT_INVALID` 映射为拒绝；`transform_context` 不得省略当前单元，`after_tool_call` 只观察且仅在 `expose_tool_results` 时附带结果；关闭时限内未收尾时报告 `HOOK_TIMEOUT`。脚本同时核对技术参考的队列、在途上限、策略上限与超时说明。检查是常量与顺序扫描，实际 hook 行为仍需按用户指南核对。

### `check_persistence.py`

`scripts/check_persistence.py` 核对 SQLite 投影索引的迁移、私有权限与连接边界：`persistence.py` 的 `SCHEMA_VERSION = 2`、文本列 `utf-8` 宽容解码（非法字节替换为 U+FFFD，避免损坏行变成内部错误）、私有目录与索引文件 / WAL / SHM 的权限收紧、`version > SCHEMA_VERSION` 拒绝、1 → 2 迁移顺序与 `user_version` 写入、`UPDATE threads SET indexed_size=-1` 的旧索引失效标记；表结构必须保留会话、回合、事件、审批与 checkpoint 的主键及 `ON DELETE CASCADE`；每个操作独占连接并启用 `foreign_keys`、`busy_timeout=10000`、`synchronous=FULL`，事务以 `BEGIN IMMEDIATE` 开始并在异常时回滚；事件索引 `events_method_cursor` 必须存在。脚本反向断言不得使用严格 `decode("utf-8")`，并核对技术参考与使用指南的「日志是事实源、SQLite 是可重建索引」口径。检查是常量与顺序扫描，实际索引行为仍需按用户指南核对。

### `check_settings.py`

`scripts/check_settings.py` 核对自动压缩设置的有界读取、原子写入与持久边界：`settings.py` 的 `config.json`、三个自动压缩字段、256 KiB 与深度 64 上限；读取只经 `open_private_file` 的私有描述符，确认 `S_ISREG`，只读到上限 + 1 字节并在多出时按不可读处理，`json.loads` 的 UTF-8 解码与宽泛异常收敛为默认值，结果必须是深度受限的 JSON 对象；保存前必须验证三个字段齐全，已存在但不可读的配置拒绝覆盖；序列化使用 `ensure_ascii=False` 保留无关键，编码异常、孤立代理项与超限分别收敛为可读中文错误；写入必须经 `tempfile.mkstemp`、`fsync` 文件、`os.replace` 与目录 `fsync`，异常时清理临时文件。脚本按首次出现顺序核对 fsync → replace → 目录同步，并反向断言不得使用 `read_text` / `write_text`；同时核对技术参考与使用指南的设置口径。检查是常量与顺序扫描，实际持久行为仍需按用户指南核对。

### `check_bridge_lifecycle.py`

`scripts/check_bridge_lifecycle.py` 核对宿主工具桥的幂等清理：`BridgeLifecycle` 必须以 `RLock` 保护清理表，扫描时剔除已回收的弱引用并保留存活引用，同一对象只清理一次并直接返回；只有可弱引用的对象才登记；`close()` 优先于 `dispose()`，钩子必须在释放清理表锁之后调用；清理异常必须吞掉，日志只记录异常类型名。反向断言禁止重新抛出、记录堆栈或异常原文；同时核对技术参考的桥清理口径。脚本只扫描源码，不证明运行时桥已释放。

### `check_shutdown.py`

`scripts/check_shutdown.py` 核对内核关闭的等待预算与中止线程所有权：`TrackedAbort` 必须只发信号（显式 callback 优先、否则回退 `request_abort`，异常收敛，`finally` 收尾），收尾必须先占锁判重、再置位 `done`、最后执行 `on_done`；启动只允许一次，线程启动失败只退休记账，绝不回退为内联中止；`join_until` 必须跳过未启动、当前线程与重复 worker，并按剩余期限 `join`。脚本同时固定 runtime / application / connections 的最多两秒共享期限、关闭时「冻结准入 → 派发取消 → 各域依次等待 → 关闭 hook 与快照」的顺序，以及技术参考与使用指南的关闭口径。脚本只扫描源码，不证明运行时线程已退出。

### `check_browser_source.py`

`scripts/check_browser_source.py` 核对 `BOSS_HARNESS_BROWSER_SOURCE` 的严格白名单 `auto` / `existing-browser` / `stored-cookie`、空值回退与规范化，要求上游参数以独立 `--browser-source` 值构造且子进程保持 `shell=False`；同时核对启动自检码、连接报告与桌面设置页的来源策略展示。脚本不启动上游、不读取浏览器或 Cookie，也不验证上游是否支持该参数。

### `check_connection_lifecycle.py`

`scripts/check_connection_lifecycle.py` 核对连接检查的异步生命周期：`_ModelCheck` 必须保留取消事件、provider、worker 终态与中止线程字段；`start` 必须串行化 CLI / 平台检查并处理失败启动，模型检查必须以 worker、取消事件与 `_ModelCheck` 三重归属判定所有权，abort 未完成时不得退休；超时、空闲通知和关闭阶段必须按取消、请求中止、等待的顺序回收。脚本只扫描源码，不证明运行时线程已退出。

### `check_connection_report.py`

`scripts/check_connection_report.py` 核对连接报告字段投影：内核 `connections.read()` 是 `connection/read` 与 `connection/check` 的共同数据源，报告固定为 `cli` / `model` / `platform` 三卡；渲染层解析器必须收口状态、浏览器来源与认证状态枚举，并限制正文、代码、时间与文本字段长度，未知值整份拒绝而非显示空白。脚本同时核对桌面 bridge 与 `connection/check` 目标白名单。它是静态扫描，不证明运行时报告内容一定可信。

### `check_search_unicode.py`

`scripts/check_search_unicode.py` 同样在安装依赖前运行：Python 侧按内核 `needs_extra` 选择补表归一化路径，Node 侧导入桌面 `caseFold.ts`，对全部 Unicode 标量值按 `0x1000` 分块计算 SHA-256 摘要并比较；不一致时列出码点区间。它验证映射表与两端 Unicode 数据的组合结果，不覆盖按字素簇切分的文本级行为。Source build 在 Python 3.12 上运行一次，独立的 Python matrix job 另在 Python 3.10、3.11、3.12、3.13、3.14 上分别运行，均使用 Node 24；同一 job 还用 `python -m compileall -q harness/src scripts` 验证这些解释器能编译内核与脚本源码（不导入依赖、不联网）。全量核对报告分块差异，可加 `--block 0xN` 只比较该 0x1000 分块并逐码点列出 Python 与 Node 的结果。

### `check_search_snippet.py`

`scripts/check_search_snippet.py` 核对搜索片段与高亮的一致性：`SessionStore._search_snippet` 只折叠命中两侧空白，必须原样复制命中区间，预算不足时先保留命中词再收窄上下文，并保留截断省略号；桌面的 `findKernelTextRanges` / `splitKernelHighlight` 必须使用内核 casefold 归一化，`SearchDialog` 必须把 `hit.snippet` 交给该高亮路径。脚本不执行搜索，也不验证运行时命中数量。

### `check_workflows.py`

`scripts/check_workflows.py` 扫描 `.github/workflows` 下的 YAML：要求顶层 `permissions` 含 `contents: read` 且不含 `write`，且顶层之外不得再声明 `permissions`（job 级或 step 级声明同样会使检查失败）；`concurrency` 启用 `cancel-in-progress: true`，每个 `actions/checkout` 步骤带 `persist-credentials: false`，并禁止 `pull_request_target` / `workflow_run` 与非 `actions/` 的 `uses`，每个作业必须声明正整数 `timeout-minutes`；每个 `uses` 引用必须匹配 `actions/<名称>@v<主版本>`，`@main` / `@master` 等可变引用失败；工作流聚合文本还必须保留两条 `npm audit` 命令（生产 moderate、全量 critical），缺失即失败。它还收集 `scripts/check_*.py` 与工作流文本中的脚本引用，要求集合完全一致；未接入 CI 的检查脚本或引用不存在的脚本都会失败。检查是文本静态扫描，不解析完整 YAML 语义；复用工作流或动态表达式仍需人工核对。

### `check_docs_links.py`

`scripts/check_docs_links.py` 扫描根目录、`docs/`、`harness/` 与 `.github/` 下的全部 Markdown（含 `harness/README.md` 与 PR 模板）：跳过代码围栏、行内代码与 HTML 注释中的示例、外链，核对相对文件路径存在；带 `#片段` 的链接同时按 ATX 标题生成 GitHub 风格锚点（小写、去标点、空格转连字符、重复标题全局追加 `-1`、`-2`），并解码百分号编码后校验同文件与跨 Markdown 文件的页内锚点。代码围栏识别 ``` 与 ~~~，最多允许 3 个前导空格，关闭标记不得短于开启标记且不得带信息串；未闭合时以文件名失败。它还要求 `docs/README.md` 索引 `docs/` 下其余 Markdown 文件，并要求上述目录中的 Markdown 全部登记在检查清单内，未登记或登记后移出约定位置都会失败。它不检查远程 URL 是否可访问，也不处理 setext 标题或运行时生成的页面锚点。它还要求 `scripts/` 下每个 `check_*.py` 在本文档恰有一个以脚本名为标题的三级小节，小节对应的脚本也必须存在；代码围栏与 HTML 注释中的标题不计入。

## 业务 CLI 请求与认证边界

本项目按工具契约派发一次业务 CLI 进程调用，不自动展开组合或追加页面；其中的网络尝试、认证刷新、缓存及摘要补取由所配置的业务 CLI 决定。“只读”描述招聘业务动作，不表示单次网络请求，也不表示不维护本地状态。

每个业务 CLI 子进程的 stdout 与 stderr 合计最多读取 16 MiB 原始字节，包含空白和诊断输出。超过上限会停止进程组并返回 `CLI_OUTPUT_LIMIT`，不解析或保存残缺信封、不自动重试；当前回合、同批后续工具及后续队列暂停。若写操作已经派发，其结果记为未知，须先核对实际状态。通过持久记录预算的结果完整保存，再沿用大结果引用和分段读取；这不是截断成功模式，也不是平台请求次数限制。

会话 JSONL 正文与冻结快照的单条记录上限统一为 32 MiB；会话头和事件日志仍为 8 MiB。预算按最终序列化的 UTF-8 JSON 字节计算，不含行分隔符；追加、新会话/分支与摘要 checkpoint 均在写入或创建发布候选前校验，避免写出内核无法重读的记录。CLI 原始输出与持久记录各自计量，数值规范化、JSON 转义或元数据复制可能扩大记录；16 MiB 内的 CLI 输出不保证能通过 32 MiB 记录预算。超限工具结果不会被截断为成功，也不会写入超限行；原操作不重放，按既有结果持久化失败路径暂停并要求人工核对。该限制不约束序列化前的宿主对象内存。新的合法大记录超过旧内核的 8 MiB 读取上限，使用这些会话需保留兼容的新内核。

JSONL 追加使用无缓冲文件描述符；短写或 `fsync` 失败时，仅在确认目标 inode、预期后缀与追加长度仍匹配时回滚至原文件长度并同步。若日志在期间被替换、追加后缀不符、回滚或回滚后的 `fsync` 失败，返回持久化结果未知错误，不覆盖外部变化；保留状态目录并人工核对后再恢复。该回滚依赖本地文件系统对 `ftruncate`/`fsync` 的实现，不能保证硬件故障、网络文件系统超时或掉电场景下的绝对持久性。

会话和事件 JSONL 的冷读、事件索引重建及删除清理对无效 UTF-8、JSON、重复对象键、非有限浮点、孤立 Unicode 代理项及无效记录结构严格失败，并指出日志类型与行号。空行仍会跳过；损坏的末尾记录也不会作为有效历史返回。普通读取和冻结快照不会静默省略中间记录，失败时不发布部分快照；两者对持久条目的编号字段采用同一规则，`revises` / `parentId` 等非字符串编号按缺失处理；顶层条目 id 为空字符串时同样按缺失处理，普通投影与快照构建都跳过该条记录，保证快照分页仍只需处理非空、唯一 id。修订记录在合并前即按此规则清理，非对象 `approval` 与非字符串编号字段不会覆盖被修订条目中原本合法的值，避免修订误合并或自洽但少条目的分页结果。上下文编辑标识允许空字符串，`page()` / `edit_state()` 与普通展示投影一致保留其编辑状态；损坏的排除标记仍按无编辑状态处理。若 SQLite 已有会话索引，索引刷新会保留旧列表投影以便定位，实际读取会报损坏行；若索引不存在且损坏日志无法重建，状态初始化会明确失败。分页列表在过滤本轮无法重建的会话后仍按有效记录保留一条 lookahead，游标绑定最后一条实际返回的有效会话，避免损坏行吃掉 lookahead 后让后续健康会话没有下一页。事件日志损坏会阻止冷重建提交，也会阻止删除重写发布临时日志；删除意图保持可恢复，避免把部分清理结果当成成功。日志是事实源，SQLite 是可重建索引；索引修复不能补回损坏的 JSONL 内容，恢复前应保留原始状态文件供人工检查。

JSON-RPC 输入帧在派发前使用严格 JSON 解码：对象键必须唯一，浮点数必须有限，嵌套最多 64 层，字符串不得包含孤立 Unicode 代理项。无效 JSON、坏 UTF-8、重复键、非有限数值或超深结构返回 `-32700` 协议错误，并继续读取后续完整帧；超过 `MAX_FRAME_BYTES` 或缺少 LF 的 framing 错误仍按传输边界终止连接。该解析规则也适用于服务端等待的响应帧，因此审批响应的重复字段不会被最后值静默覆盖。handler 可能已经产生外部或持久副作用，响应编码失败时不能重跑；无效结果返回有界 `-32603` / `RESPONSE_INVALID`，响应请求 ID 本身不安全编码时会省略该 ID。未捕获异常的错误消息经既有凭据脱敏后返回；带文件名的 `OSError` 还会改写为固定中文原因（如 `ENOSPC` 磁盘空间不足、`EACCES` 权限不足、`EROFS` 只读文件系统），附 errno 名称并去掉 `filename` / `filename2`，避免把本机路径写入响应或 stderr。无文件名的 `OSError`、`ValueError` 与 `RpcError` 保留原消息。

招聘 CLI 自行管理部分网络重试、认证刷新和缓存行为；Harness 能依据的是它收到的最终错误或支持的结构化停止元数据，无法从成功结果推断此前是否出现过隐藏响应。更换 `BOSS_CLI_BIN`、业务 CLI 版本或上游配置后，应重新核对这些边界；不要把单次工具派发等同于单次平台请求，也不要据此声称“首次限流即停止”或“没有触碰浏览器”。

Harness 可通过进程环境变量 `BOSS_HARNESS_BROWSER_SOURCE` 显式传递上游支持的来源：`auto` 保留上游默认自动选择，可能探测 CDP 或降级到 headless；`existing-browser` 只复用现有 CDP 浏览器且不读取存储凭据；`stored-cookie` 使用上游存储凭据并只连接显式配置的 CDP，不自动探测或启动浏览器。后二者会改变请求通道和运行前提，不能视为“无重试”或“零平台访问”模式。未设置变量时不添加参数，继续继承上游 `config.json`；显式参数被上游拒绝时只失败一次，不静默删参或重放。该参数只对支持它的业务 CLI 有效，更换 `BOSS_CLI_BIN` 后须重新核验。

`boss-agent-cli --json` 的输出在进入七键集合、退出码和暂停码适配前，先经过严格 JSON 校验：对象键必须唯一，浮点数必须有限，嵌套最多 64 层，字符串不得包含孤立 Unicode 代理项。JSON 语法错误返回 `CLI_ERROR`；可解析但违反这些完整性约束的信封返回 `CLI_CONTRACT_ERROR`，不保存 `data`、不回交模型，且暂停当前回合、后续工具与队列，不自动重试。已派发写工具的该类错误仍记录 `outcome_unknown` 并要求核对外部状态。单次 CLI 派发仍不等于单次平台请求；这项校验只约束 Harness 与上游进程之间的信封边界。

该覆盖不会读取 Chrome Cookie 数据库或 Keychain，也不修改共享上游配置；但 `auto` 仍允许上游的浏览器行为。Harness 无法约束忽略或误解该选项的任意二进制，也不能保证上游不会通过其他路径访问本地状态。浏览器来源策略不替代独立的请求预算或认证刷新契约；需要这些保证时，应使用明确支持并验证相应行为的上游版本。

平台扫码登录使用 `platform/login/start`、`platform/login/read`、`platform/login/complete` 与 `platform/login/cancel` 四个请求方法，对应 `packages/protocol` 的 `ClientMethods` 常量。它们只由宿主主进程调用，不在渲染层请求白名单内；`complete` 的 cookies 与 userAgent 由内核按官方登录态格式校验后直接交给业务 CLI 验证，不写会话、事件或错误日志。渲染层只经主进程的登录状态机取得脱敏后的 `PlatformLoginStatus`，本协议不向模型暴露这些方法。

固定调用链、可观察范围及后续能力接入条件见 [UPSTREAM.md](../UPSTREAM.md)。

## 平台暂停与聊天部分结果

`boss_hr_chat` 读取本页沟通列表时，业务 CLI 还可能为会话补取最近消息；列表只读不等于只有一个网络请求。默认摘要预算及补取行为沿用业务 CLI，本项目不追加补批或探测。

如果列表已取得、最近消息补取遇到认证、验证码、风控或限流停止码，工具保留已取得的 `data`、原始 `hints` 及分页，但以本地失败结果明确标记“部分结果，平台要求暂停”。收到这一可见停止信号后，当前回合暂停，同批后续工具不执行，也不再自动请求模型；列表不等于完整最近消息，未知未读状态不能当成已读。

适配仅识别 `hr chat` / `recruiter-chat` 的固定元数据 `hints.summary_sources.last_messages_error_code` 及既有停止码，不从候选人文本、任意错误字符串或其他命令推断授权和状态。原始 CLI 信封保留在适配对象的 `raw` 中，仍反映上游成功；会话与桌面保存、展示的是本地失败状态及部分结果。原有顶层失败保持原错误，普通成功和非停止摘要错误保持既有行为。

用户处理平台限制后再明确发起后续任务。恢复会话不会自动重试、补取消息、翻页或探测状态；上游 `hints` 中的建议命令仅作为来源数据，不构成执行授权。

## 模型截断与回合上限

OpenAI Responses 的 `response.completed` / `response.incomplete` 与 Anthropic 的 `message_stop` 都是响应终态；SDK 在终态后若继续交付任何流事件，内核按协议错误结束本次请求，不执行该响应的工具、不重试或继续后续队列，已接收的有界文本前缀标为失败保留。SSE 注释与 OpenAI 的 `[DONE]` 由 SDK 处理，不属于这些内容事件。

模型输出达到长度上限时，本次响应中的工具全部记为未执行，截断文本保留并以错误收尾，不自动重试或启动后续队列。每次模型响应的工具参数文本按原始 UTF-8 字节计数，每项及所有工具合计均最多 1 MiB；已解码的初始对象先检查结构和紧凑 JSON 字节数，再序列化。空白、转义及多个工具合计会触发这一新增边界，即使各项规范化 JSON 未超限。超限时关闭模型流并以错误结束，不保存超限参数、不调用 handler 或审批。该限制作用于 provider 已收到的事件，不能限制单个 HTTP/SSE 事件帧在解码前的内存，也不是进程 RSS 上限。文本与思考另按每次响应合计 1 MiB 原始 UTF-8 字节限制，增量和权威终态都在缓冲、事件持久化及通知前检查。超限以错误终止整轮，关闭流、不审批或执行该响应的工具、不重试或自动继续队列；已接收的有界前缀标为失败保留。增量事件拆为最多 32 KiB UTF-8，以便事件分页恢复；最终实时通知保留预算内全文，最坏 JSON 字符串转义仍在 8 MiB 帧限制内。该保证不包含 provider 附加元数据、无限事件数量或 SDK 解码单个 SSE 帧的内存。

每回合默认最多 6 次业务模型请求；启动环境变量 `BOSS_HARNESS_MAX_MODEL_REQUESTS` 去除首尾空白后可设为 1–64 的十进制整数，空值或只有空白时使用默认上限。嵌入方可传入 `ApplicationService(max_model_requests=...)` 显式指定并覆盖环境配置。`config/read.maxModelRequests` 返回宿主上限；`turn/start.maxModelRequests` 只可为本回合收紧，必须是 1 到宿主上限的整数，不修改后续回合或队列默认值。非法配置在预留回合、保存输入或创建该回合 provider 前拒绝，布尔值、字符串和小数不作为 RPC 整数接受。

每个工具回路、steering 续答和上下文溢出恢复重试均计入本回合上限；provider/SDK 内部传输重试不在此计数中。另有每个逻辑业务回合默认 8 次的运行时恢复预算，由 OpenAI / Anthropic 瞬时传输重试、自动上下文溢出恢复及自动摘要中的 provider 重试共同消耗；退避期间取消会退还预留额度，预算耗尽后不再等待或发起后续恢复。手动摘要使用独立预算。该预算不进入会话记录、RPC 或模型请求，也不计正常模型请求或摘要分片；摘要仍使用独立的 32 次生成上限。最后一次工具批次后仍需续答时，以 `blocked / TURN_ROUND_LIMIT` 暂停并保留结果，需核对后明确发起新回合；通知带 `maxModelRequests` 和 `modelRequestCount`，回合历史记录实际上限。最后一次正常最终文本仍可完成，最后到达而未能响应的 steering 保留为暂停队列项；已执行工具和审批不会重放。

## 模型容量与请求预算

进程的生效默认线路取自模型目录：`none` provider 在目录中规范为 `model=none`、无推理档位，`initialize.modelBridge`、`config/read`、`model/list` 与 `thread/start` 使用同一份配置，新建会话不再因握手模型名与可选目录不一致被 `MODEL_ROUTE_UNAVAILABLE` 拒绝。显式 none、自动回退及残留的模型 / 档位变量都落到该目录项，不发起模型请求；`anthropic` / `openai` 等真实线路仍使用解析出的原配置，不迁移或改写既有会话。显式覆盖其他线路模型时，解析与校验规则不变。目录只在 Anthropic 凭据去除首尾空白后仍非空时才加入 `anthropic` 线路；只有空白的 `.env` 占位值不会被列出，摘要线路解析也用同一判定提前以 `COMPACTION_MODEL_UNAVAILABLE` 拒绝。

显式 `none` 是进程级开关，与自动回退不同：以 `--provider none`（或未传 `--provider` 时 `BOSS_HARNESS_PROVIDER=none`）启动后，目录只保留 `none · none`，不发现其他已配置线路；摘要线路不再独立解析，`summaryAvailable` 为 `false`；记录在真实线路上的旧会话读取上下文、发起回合或续接会被 `MODEL_PROVIDER_UNAVAILABLE` / `CONTINUATION_PROVIDER_UNAVAILABLE` 拒绝，这类会话仍可切到 `none` 线路使用只读指令；`queue/add` 为新建队列项调用与 `turn/start` 相同的会话线路解析，拒绝时返回同一错误码且不写入队列记录，既有队列项仍按幂等返回。自动回退得到的 `none` 只是本机没有默认线路，其他已配置线路仍会进入目录并可在会话内选用。构造方以 `ApplicationService(model_calls_disabled=True)` 显式指定时，要求默认线路为 `none` 且不注入 provider 实例。该状态经 `initialize.modelBridge.modelCallsDisabled` 与 `config/read.modelCallsDisabled` 暴露给客户端：显式禁用时为 `true`，自动回退与真实默认线路为 `false`，两处取值恒一致；旧内核不返回该字段。显式禁用时目录仍有可选的 `none · none`，桌面的模型菜单并不为空，因此说明以附注形式显示在选项之后（目录为空时顶替空态文案，预览模式不显示）；「运行状态」概览的「模型调用」取 `config/read` 字段，显示「已由进程禁用（显式 none 启动）」「未被进程禁用」或「未提供」。握手缺该字段时模型菜单保持上一次取值。

`connection/read` 的 `model` 卡片在显式禁用时返回 `state: "disabled"`、`code: "MODEL_DISABLED"` 和重启提示；启用招聘平台能力的工具组合还会提示招聘 CLI 仍可运行。默认线路为 `none` 且进程级开关关闭时，卡片保持 `disabled` 并返回默认线路说明，`code` 省略。`connection/check` 的 `model` 目标在这两种情况下直接返回报告。桌面在状态行展示 `summary` 与 `code`；报告缺少 `MODEL_DISABLED` 且握手标明禁用时，描述行使用握手提示。

握手 `initialize.modelBridge` 的 `thinking` 与 `serverSideFallback` 只在默认线路为 `anthropic` 时报告生效配置。默认线路为 `none` 或 `openai` 时，这两个字段分别为 `null` 和 `false`。客户端可按已有字段类型读取；运行时模型配置和续接指纹仍使用原始配置。

内核在每次模型请求前估算完整输入，包括 system/技能、用户材料、消息与思考、工具调用及结果、工具 schema 和请求选项。输出预留受模型声明的上限约束，输入增长不会静默缩小输出；保留 4096 token 安全余量。接近或超过预算时可先自动摘要更早的完整回合；仍无法容纳时以 `blocked / CONTEXT_BUDGET_EXCEEDED` 或明确的压缩错误暂停，不请求业务模型、不自动启动后续队列，已有工具结果继续保留。steering 只有在下一请求通过预算检查后才标记已投递；预算失败时保留为暂停项。

通过启动环境变量 `BOSS_HARNESS_MODEL_LIMITS` 配置精确的 `provider/model` 容量，例如：

```sh
export BOSS_HARNESS_MODEL_LIMITS='{"openai/custom-model":{"contextWindow":128000,"maxOutputTokens":16000,"reasoningEfforts":["low","medium","high"]}}'
```

键中的 provider 使用 `anthropic`、`openai` 或 `none`（`codex` 线路解析为 `openai`）；模型名精确匹配且可含 `/`。两个容量均为整数，窗口须大于 4096，输出上限须为不超过窗口的正数。可选 `reasoningEfforts` 只接受 `none`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max` 的非重复数组，且最多 7 项；省略时表示该模型没有可供会话选择的已声明档位，不会猜测供应商能力。配置的 `BOSS_HARNESS_EFFORT` 属于全局七档但不在某模型声明的档位内时，`--check` 以 `MODEL_EFFORT_UNSUPPORTED` 警告说明与声明不符；未声明或未配置强度时不做推断。配置最多 128 项、UTF-8 编码 64 KiB，拒绝重复键、未知字段、布尔值和无效类型；错误不显示原配置。空值或只有空白视为未设置，使用内置默认容量；嵌入方可显式传入不可变 `ModelCatalog`，不读取该环境变量。

未知模型使用 200000/64000 的兼容预算，返回 `capabilitySource=legacy-default`、`capacityIsEstimate=true`；这是本地假设，不能证明真实服务容量。请求输出大于此默认上限时会裁剪到 64000，需要更高额度时应显式配置。显式容量标记为 `configured`，仍由部署者核对模型及网关约束，不自动探测或下载模型目录。

`context/read` 传 `threadId` 可查看完整预算；空闲时还可传与下一回合一致的 `model`、`input`、`skillIds`、`attachmentIds` 做预览。运行中返回当前已准备请求的快照，并拒绝预览参数。`requestSource` 区分 `active`、`preview`、`default`；准备完成前的 `active` 是按当前回合配置生成的候选预算。`summaryAvailable` 表示当前摘要策略有非 `none` 线路、宿主提供了独立 provider factory，且进程未以显式 `none` 禁用模型调用。若摘要另选 Anthropic，至少一项 Anthropic 环境凭据去除首尾空白后须非空，与实际摘要配置解析一致；复用会话自身线路时不重新核对环境凭据。该字段不构造供应商、不额外读取模型配置文件，也不保证实际认证或摘要成功。`requestedOutputTokens` 保留原请求值，`outputReserve` 是裁剪后的值；`breakdown` 分列 system/messages/tools/options。每次请求记录预算，重启后 `lastBudget` 可追溯最后一次准入或拒绝，读取不会执行模型或工具。

会话菜单可通过 `thread/reasoning/read` 读取模型声明的推理档位，并用 `thread/reasoning/set` 保存当前会话选择；传 `null` 恢复启动配置。设置追加到会话历史，不修改环境变量或 Codex profile；会话分支继承创建时的设置。设置在下一次请求准备边界生效，已经准备或正在传输的请求保持原档位。业务回合与上下文预算使用当前会话的有效档位；摘要默认继承该档位，显式设置摘要 effort 后则使用独立档位。当活动模型与摘要模型的能力集合不一致时，只显示两者交集，避免档位设置使业务回合无法执行。重启后若部署的能力表移除了已保存档位，读取会标记为不受支持，用户可恢复继承配置。

token 数默认采用 `characters/2+message-overhead` 分类估算，不是供应商 tokenizer 或计费值。成功 usage 的 provider、模型和完整请求前缀匹配时，使用 usage 基线和新增尾部估算，返回 `usageApplied=true`；否则回退到字符估算。模型摘要使用独立 provider，不带招聘工具，支持取消和分段进度；可显式启动或在业务请求边界自动生成。来源及兼容差异见 [内核建设记录](../UPSTREAM.md)。

用户主动触发的模型连接检查也应用同一容量约束，其最多 512 token 的诊断请求会按模型输出上限裁剪；预算不足在构造供应商前返回检查失败。诊断不属于会话回合，不写入会话预算历史。

关闭内核时，应用先冻结准入，并为业务回合、摘要任务和连接检查统一置位取消，再异步分发各自的中止。所有 worker 与 abort 共享同一个最多两秒的等待期限；尚在检查中的模型诊断以 `failed / CANCELLED` 收尾，已经超时的检查保留 `CHECK_TIMEOUT`。不可协作的 provider 可能稍后才退出，取消不能保证强制终止 SDK 建连；尚未退出或仍在发布终态通知的任务继续保留 provider、bridge 与状态目录所有权，旧超时回调、迟到响应和异常不会覆盖新检查或既有终态。关闭期间工厂才返回的实例不会开始模型请求。

连接检查和官方登录保存任务在 worker 构造或实际启动前失败时返回固定失败状态并释放槽位；登录返回 `LOGIN_SAVE_START_FAILED`，需要重新打开官方登录窗口，不自动重试保存。若启动包装层在 worker 已实际启动后抛错，内核继续跟踪原任务和取消信号，直至 worker 与已启动的模型 abort 完成清理；不会据此重复检查或保存登录态。桥接工厂、本机可用性及认证检查返回后，已观察到取消的任务不再发起后续 CLI 调用。

`turn/interrupt` 和 `context/compact/abort` 返回的是取消请求确认，不表示 worker 或供应商连接已经退出。应用先设置相关取消信号，再异步分发业务与摘要各自的中止，慢 hook 不占用 RPC 处理线程或全局运行锁；中断自动摘要所属回合时，两者都先收到取消。重复取消及随后关闭共用同一次中止，实际完成状态以回合/摘要终态及收尾为准。直接嵌入使用 `TurnRunner.interrupt()` 的同步接口保持原有约定。

内置 OpenAI Responses 与 Anthropic Messages provider 在交付失败事件前再次检查自身取消标志。若 `request_abort()` 已被观察，即使后台 producer 已结束且 EOF、SDK 或协议异常尚未被消费，交付的事件也统一为 `error / aborted` 与“请求已取消”，不附带 `errorInfo`；OpenAI 同时清除该失败的重试状态，不自动重发。未取消的 EOF、连接和协议失败仍保留原分类；已确认的正常完成消息、文本及私密思考续接数据保持原结果。此边界约束 provider 的失败交付，不改写此前已交付的终态，也不改变回合中断、worker 收尾及工具副作用的独立事实。

回合终态提交与取消接受使用同一运行锁边界。终态提交前已接受的取消以 `interrupted` 收尾，并暂停结算时已排入的后续队列；即使模型已经给出完成结果，也不会继续自动派发。已产生的文本、工具结果、审批及外部动作事实仍保留，取消不表示撤销。终态已提交并释放执行槽位后，若没有活动回合则返回未中断；旧 `turnId` 不能中断新回合。桌面停止请求携带界面正在展示的回合 id，该回合已被后续回合替代时以 `-32004` 拒绝且不取消新回合，与 `turn/steer` 的 `expectedTurnId` 同一约定；不带 `turnId` 时仍取消该会话当前活动回合（旧客户端行为）。显式 `turnId` 必须是非空、非纯空白、最多 128 字符的字符串；null、空字符串、数字、布尔值、数组或对象在设置取消信号前返回 `-32602`，闲置回合同样校验，不能退回取消当前回合。用户之后仍可显式发起新任务，已暂停的队列不会因此自动恢复。

回合最终 `finish` 阶段 checkpoint 无法确认持久化时，当前执行以 `error` 收尾，尽力追加 `phasePersistenceFailure` 修正记录，并在释放容量前暂停当前会话全部待处理队列。暂停写入也失败时，内核保留暂停责任；后续准入或领取必须先完成暂停，存储恢复不会自动执行旧 follow-up。其他会话仍可按既有 FIFO 等待顺序取得空出的容量。

## 自动压缩与溢出恢复

模型回合默认开启自动压缩：完整输入估算达到 `inputBudget` 的 80%，或预算检查拒绝请求时，尝试摘要更早的完整回合，保留近期估算 20000 token。`inputBudget` 已扣除业务输出储备和 4096 token 安全余量，阈值不重复扣减。小窗口应降低保留目标；当前运行回合始终完整保留，因此单个过大输入或工具结果仍可能无法容纳。

保留目标按 token 口径估算，但不承诺与供应商 tokenizer 一致：`_retained_usage_estimate()` 仅使用同一业务 provider/model 且请求指纹匹配的可信 `model_usage` 前缀校准消息区间，其余回合回退到 `estimate_tokens()` 的字符估算。计划只在完整、已收尾的回合边界切分，当前运行回合和已有摘要覆盖的来源不重复摘要；若切点之前只剩空回合或全部来源已被覆盖，则拒绝计划。计划中的 `estimatedRetainedTokens` 与切点选择同源，仍只是预算估算，不能代替提交前的完整请求预算校验。

启动配置 `BOSS_HARNESS_COMPACTION` 接受 JSON 对象，例如 `{"enabled":true,"triggerPercent":80,"keepRecentTokens":4000,"provider":"openai","model":"summary-model","effort":"low"}`；可省略字段，其余使用默认值。`enabled` 为布尔值，`triggerPercent` 为 1–100 整数，`keepRecentTokens` 为 1–1000000 整数；`provider` 可为 `anthropic`、`openai` 或 `codex`，`model` 是本机线路上的模型 ID，`effort` 只能使用 `none`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max`。显式 effort 必须在 `BOSS_HARNESS_MODEL_LIMITS` 中为摘要模型声明支持；未声明时拒绝开始摘要。拒绝未知字段、重复键和无效类型，错误不显示原配置；空值或只有空白视为未设置，来源不报告为 `environment`。`config/read` 返回解析后的 `autoCompaction`，摘要任务与 checkpoint 记录实际 `summaryProvider`、`summaryModel` 和 `summaryEffort`。嵌入方可传入不可变 `CompactionPolicy`；不传时才读取环境变量。

单次 `turn/start` 可通过 `autoCompaction` 部分覆盖触发策略，例如 `{"threadId":"…","input":"继续分析","autoCompaction":{"enabled":false}}`。`queue/add` 接受相同的部分覆盖字段并随队列项持久化，入队前和后续回合投递时均按 `turn/start` 的同一校验与合并规则应用。只有缺省 `autoCompaction` 才不指定覆盖；显式 null 或其他非法类型在入队前返回 `-32602`，已有请求重试也执行该校验，不改变原队列项；空对象 `{}` 仍是合法的部分覆盖。相同 `clientUserMessageId` 显式重发不同合法覆盖时以 `CLIENT_REQUEST_CONFLICT` 拒绝。覆盖仅适用于该回合，不修改会话或全局默认值；摘要的 provider/model/effort 仍使用启动时的独立摘要配置。未设置摘要配置时继续沿用当前会话模型与推理档位；可显式指定不同摘要线路或档位，模型容量、输入预算和 4096 安全余量按摘要模型计算。摘要完成后，checkpoint 仍须通过当前业务模型的完整请求预算校验才会提交。自动压缩与溢出恢复均使用实际业务回合的 provider 和请求模型查询容量、匹配 usage，不能用摘要 provider 与业务模型拼接容量键；校验包含摘要、保留尾部、system、工具与业务输出预留。失败时以 `COMPACTION_INSUFFICIENT` 暂停，不提交新 checkpoint、不派发后续业务请求。模型路线必须是本机可配置线路，要求 provider factory 创建与业务回合隔离的实例；嵌入方未提供工厂时不执行可选自动摘要，预算超限仍暂停。

自动摘要复用分段生成、来源 digest 和单次提交机制，只替换核对一致的历史前缀。当前回合的用户材料、思考、工具调用及结果、已交付与暂存 steering 保持原对象和顺序；摘要成功后、业务请求前再领取一次新 steering 并重检预算。首批与补领的转向在提交后共用最终请求指纹写入请求边界，确保中断续接可核对所有已投递转向；预算失败与请求拒绝仍按原顺序记录。每个业务请求边界最多启动一次阈值/预算摘要，因此工具返回新结果后会重新检查；超过窗口的恢复另有每回合一次上限。没有可摘要前缀但请求仍在预算内时继续，已启动摘要失败则暂停。任务通过同一压缩任务接口和通知报告进度，`reason` 为 `threshold`、`budget` 或 `overflow`，并附所属 `turnId`。自动摘要线路解析失败以 `COMPACTION_MODEL_UNAVAILABLE` 结束并暂停所属业务回合；显式推理档位不被摘要模型支持时以 `COMPACTION_EFFORT_UNSUPPORTED` 结束，两者都不会把配置错误笼统包装成 `TURN_EXECUTION_FAILED`。中断回合或取消自动摘要都会停止该回合及独立摘要流；已成功提交的 checkpoint 保留，取消后不再请求业务模型。

实际供应商窗口小于本地容量时，仅在 OpenAI 可信错误字段精确返回 `context_length_exceeded`，OpenAI-compatible llama.cpp 返回有界且精确的 `Context size has been exceeded.`，OpenAI-compatible LiteLLM 的 HTTP 400 错误消息有界且同时包含 `litellm.ContextWindowExceededError`、`Context Window exceeded for given call.` 和 `Got > Max Input Tokens`，或 Anthropic 返回类型明确且包含数字上下限的 `prompt is too long` 错误时标记 `CONTEXT_OVERFLOW`。OpenAI 与 Anthropic 的可信 HTTP 413 还接受不超过 512 字符、完整匹配 `Request body too large` 或 `payload too large` 的消息（忽略大小写，可带末尾句点），以处理代理在 token 窗口内按请求字节数拒绝的情况。当前请求未产生任何文本、思考或工具事件且未取消，才允许本回合最多一次压缩后重试；失败请求与重试都计入本回合业务模型请求上限，最后一次失败不再摘要。只继续当前请求，不重新运行已执行工具或复用旧审批。裸 HTTP 413、其他 413 消息、输出 `length`、限流、认证、连接错误、任意其他错误文字或超窗 usage 均不触发此恢复；旧 provider 没有结构化分类时保持普通失败。

供应商终态模型错误会把有界 `errorInfo` 附加到 `session/error` 并保存在 `model_error` 记录中，字段包括 provider、错误来源、可用 HTTP 状态、经过字符集与长度筛选的 provider code，以及可选 `retryable`。OpenAI 流内错误的 HTTP 状态记录为 200；缺少状态或明确分类时省略对应字段。流传输异常还可携带固定原因分类（如读取超时或连接错误）和白名单 errno；界面错误消息使用同一受控分类。此范围也覆盖 SDK 未包装的 HTTP 客户端传输异常，正文读取失败使用固定错误文案，保持原有重试策略。底层 cause 原文、cause 类型名、URL、请求正文、响应头和凭据不会进入诊断元数据。总时限错误沿用独立的明确超时消息，不伪造 SDK cause。另有 `outputObserved` 标记请求是否已向调用方输出文本、思考或工具增量。`retryable` 描述 provider 请求级错误分类，不代表整回合可以重放；现有 OpenAI 内部重试行为不变，Anthropic 不新增重试。只有上文列出的精确 `CONTEXT_OVERFLOW` 条件能触发上下文恢复；状态码或 `retryable` 不会改变审批、工具派发或回合恢复策略。错误记录不包含响应正文、请求、响应头或凭据；明确的额度耗尽 code 标记为不可重试，只有已知的临时限流/服务端错误才标记可重试，含义不明的 HTTP 429 保持未知。

摘要请求自身或连接诊断不会进入业务溢出恢复。自动任务由当前业务 worker 持有，重启只恢复历史，不自动重放摘要、业务请求或外部操作。全局自动策略编辑仍通过配置和协议控制。

## 桌面上下文与手动摘要

在真实会话中打开“上下文”，查看内核返回的当前会话或活动请求预算，包括估算输入、有效输入预算、输出预留、容量来源及 usage 校准依据。该读取不包含尚未发送的草稿、技能或附件；token 数不是精确 tokenizer 结果或账单。打开面板、刷新预算和规划均不调用模型或招聘工具，也不会停止当前任务。

会话空闲时可设置保留近期上下文的估算 token 目标，先读取计划，核对整理的历史范围与保留的完整回合，再显式生成摘要。摘要默认沿用当前会话模型，也可通过 `BOSS_HARNESS_COMPACTION` 配置独立 provider、model 和 effort；手动摘要请求中的 `model` 可覆盖启动时设置的摘要模型。显式 `model` 须为最多 200 字符、不含空白的非空模型 ID，空串、空白、其他类型、null 与超长值在创建摘要任务前返回 `-32602`；只有缺省才继承启动时的摘要模型，合法的显式覆盖继续生效。摘要可能增加用量；计划来源 digest 与选定范围一同提交，过期时需要重新核对，不移除校验自动重试。摘要仍保留原始历史，不能保证语义无损，也不会执行招聘工具或重复既有审批。

面板按会话与任务 ID 展示分段进度、取消确认及终态。取消受理不表示 worker 和模型连接已经退出；终态之后也可能仍在收尾。完成后重新读取预算和 checkpoint，不从字符进度推断成功。运行中的自动摘要由所属业务回合控制，不因打开面板而被取消。

`context/read.compactionJob` 是可选任务引用，包含 `jobId`、`status`、`active`；`active=true` 表示当前进程仍持有会话执行责任，可能与终态同时出现。最近保留的终态任务从持久事件日志重建，详情继续通过 `context/compact/read` 核对；嵌套的 `job.result` 是历史快照，不能代表当前收尾状态。旧服务缺少字段表示无法发现，`null` 表示当前没有保留的任务。

切换会话、关闭面板、断连或开始回执未知时不会自动再次生成摘要；已知任务通过读取对账。进程重启后，未终结任务会检查对应 `summaryJobId` 是否已写入 checkpoint：已提交的恢复为 completed，否则恢复为 `failed / COMPACTION_INTERRUPTED`。恢复只补写可观察终态，不恢复 provider 请求或 checkpoint；用户须重新读取计划并显式开始新任务。最近 64 条终态可查询，之后被淘汰的旧任务可能无法查询。

## 大结果与会话恢复

模型可见工具结果按工具定义的 `max_model_result_bytes` 限制，默认 20 KiB，允许范围为 8 KiB 至 1 MiB。较大结果在模型上下文中显示明确的省略标记、摘要和结果 SHA-256；完整结构化结果继续保存在会话记录中。模型可见结果与历史回放还携带可选的 `executionState` 和 `disposition`：`not_executed` / `not_approved` 标记为 `not_delivered` + `safe`，`outcome_unknown` 标记为 `delivery_uncertain` + `unsafe`，只读工具失败标记为 `not_delivered` + `safe`，写工具失败但无未执行证据标记为 `unknown` + `unknown`；旧版失败条目按工具名识别写工具；无法确认时只标记状态、不推断可安全重试，持久记录中的非法 disposition 值被忽略而不是让上下文构建失败。历史结果在预算不足时会重新投影以保留这些状态字段；截断标记、非法 `ok` 与超长标识同样计入预算，所有返回路径都守住上限，无法被只读工具读取的 itemId 退化为 `resultUnavailable` 而不是生成无效 `resultRef`。不得仅凭错误码推断可安全重试。Harness 提供只读内核工具 `read_session_tool_result`，模型可按 item ID、摘要和游标每次读取至多 8,192 个 Unicode 字符；读取只访问当前会话已保存的数据，不重新调用招聘工具。桌面/RPC 展示使用独立结果引用，超过 64 KiB 时不内联传输；两条读取路径预算不同是职责差异，不是同一上限的两种写法：模型侧只提供受控分段，避免把完整大结果回灌模型上下文；桌面/RPC 侧供人审阅完整结果。

RPC 客户端可通过 `thread/item/result/read`，传入 `threadId`、`itemId`、引用中的 `sha256` 及可选 `cursor`、`limit` 读取标准 JSON 文本；默认 16,384、最多 32,768 个 Unicode 码点。引用包含该文本的 UTF-8 SHA-256、字节数和码点数，服务端游标绑定会话、条目及版本。模型上下文中的历史投影与两条分块读取路径共享同一份规范化文本：深度超限子树、非有限浮点等不可直接写入 JSON 的旧记录按相同规则降级，投影里的引用可直接读取。结果发生修订时返回 `STALE_RESULT`，错误数据的 `currentRef` 给出当前版本的同形引用；客户端须重新获取并确认引用，不能混用不同版本。桌面主进程为 `thread/item/result/read` 保留该结构化错误，渲染层解包后按合法 `currentRef` 显示核对提示。

桌面与内核搜索的归一化按字素簇进行：内核字素合并与组合类补表对齐桌面 Unicode 17，旧版已退役记号不再合并。含补表码点的簇先做 NFKD 全分解，递归展开新增规范分解，按桌面组合类在 starter 之间稳定分桶排序后单遍合成，再逐码点 casefold；规范分解键及其部件、Kirat Rai GCB=V 序列都会触发该路径，避免长组合串退化成二次复杂度。普通文本仍走运行时 NFKC + casefold。这样新增记号不会因运行时旧组合类被当作 starter 而阻塞重音合成，兼容字符与规范等价文本在两端取得同一搜索键和高亮区间。

超过 64 KiB 的 Agent 文本与思考字段在条目读取和持久完成事件中改为 `textRef` / `thinkingRef`，原文仍保留在会话。`thread/item/content/read` 按 `part`（`text` 或 `thinking`）、会话、条目及 SHA-256 读取，默认 16,384、最多 32,768 个 Unicode 码点；游标绑定字段与内容版本，变更返回 `STALE_CONTENT`，错误数据的 `currentRef` 给出当前版本的同形引用。冻结快照的引用还绑定 `snapshotId`，在快照有效期内始终读取该版本。桌面恢复时逐段校验长度与摘要，再展示快照；冻结快照还会核对声明的 `itemCount`，分页结束后实际条目数必须一致，且每个条目必须带非空、唯一的字符串 `id`，少读、多读、缺标识或重复都整体失败，不展示部分快照。桌面恢复对分页设置有限预算：单个字段按自身长度限流，一次会话恢复还共享正文分页总预算；超小分段或大量小字段都不能把恢复拖成过多往返，预算耗尽即明确失败，不展示部分正文。每个历史字段自动恢复上限为 16 MiB，超过时明确报错，原文仍可由该接口分段读取。桌面主进程为 `thread/item/content/read` 保留 `STALE_CONTENT / currentRef`，渲染层统一解包并只在引用数据合法时显示核对提示。恢复失败不重放招聘动作。新方法保持协议版本 `0.2.0`；自定义客户端需支持内容引用，才能完整恢复大字段。

会话条目和事件回放还按约 1 MiB 响应预算分页，游标只推进到实际返回的数据。非分页读取或单条记录无法传输时会返回明确的 `RESPONSE_TOO_LARGE` 错误，连接继续可用；支持快照的客户端应通过 `thread/resume` 的冻结分页恢复。原始记录不被裁剪，读取不触发招聘工具。

内核汇总用量时，provider / model / 摘要任务标识与 `model_usage.turnId` 使用会话读取相同的 `wire_text` 降级规则：孤立代理项替换为 U+FFFD，长度上限在降级后仍成立；超过 128 字符的 `turnId` 跳过。当前分支 checkpoint 的活跃任务标记也使用同一有界标识规范化，降级后的 `summaryJobId` 仍能正确标记 `active`，不会把当前任务误显示为历史任务。这些约束只影响展示来源与关联，合法记录的请求数和 token 合计不变。标识只校验非空字符串与长度上限，不做额外字符集过滤；桌面端采用同一规则，坏标识不影响整页用量展示。 长度按 Unicode 码点而非 UTF-16 码元计算，补充平面标识不会被桌面误判超限。原因键在桌面映射中保留原文，超过展示上限时合并为“其他”汇总；`unreportedRequests` 必须等于 reason `missing`，旧内核缺失该字段时由原因表补齐。CSV 的摘要任务说明在无元数据时回退到 `jobId`。摘要任务明细在每页用量响应中重复返回；桌面只取首份并保留最近 50 条，与内核 `[-MAX_SUMMARY_JOBS:]` 同向，兼容实现返回超量明细时不会展示旧任务；`summaryJobCount` 仍按完整接收数量与展示数量判断截断。压缩任务的 `reason` 表示自动触发原因、`origin` 只表示摘要作者，`origin="model"` 不表示自动压缩；手动压缩也由模型生成但没有 `reason`。桌面明细、CSV 与内核会话导出统一按 `reason` 是否存在区分自动/手动压缩。用量分页除条数上限外还按约 1 MiB 响应预算增量缩减本页回合数，游标绑定到实际返回条数；固定字段与摘要任务明细本身超预算时返回用量专属 `RESPONSE_TOO_LARGE`，`recoveryMethod=thread/usage/read` 且 `retryWithSmallerLimit=true`，不再误导为会话快照恢复。桌面会话用量面板按页读取 `thread/usage/read`，读完后要求同一 `turnId` 只出现一次；未截断（`nextCursor: null`）时累计条目数必须等于最后一页声明的 `turnCount`，重复或数量不一致都整体报错且不展示部分数据。面板展示的回合总数取最后一页计数，分页期间并发完成的回合不会让列表行数超过声明；达到页数上限的截断读取保留「仅显示前 N 个」提示，只校验已读部分不重复。该保护只作用于渲染层，不改变 RPC 或内核。

`thread/start.projectId` 与 `thread/list.projectId` 筛选须为最多 200 字符的字符串，超长值在写入会话文件或执行索引查询前返回 `-32602`。旧版本可能已把超长标识写入会话头；元数据投影固定截断为前 200 字符并附 `projectIdTruncated: true`，原始会话头不改写，使这类会话的普通读取、`thread/resume` 与冻结快照重新可读。

会话标题在新建、重命名与 `thread/fork` 自定义标题处共用最多 500 字符的上限，超长值在写入会话文件前返回 `-32602`。旧版本可能已把超长标题写入会话头；元数据投影固定截断为前 500 字符并附 `titleTruncated: true`，原始会话头不改写，使这类会话的普通读取、`thread/resume` 与冻结快照重新可读，`thread/list` 的响应也回到单页预算内。

### 持久附件存储

文本附件单文件最多 2 MiB，每回合注入上下文的附件正文合计最多 2 MiB（名称标签与分隔符不计入该额度）；会话状态目录中的持久附件另有默认 512 MiB 和 4096 个文件对象上限，可分别用 `BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_BYTES` 与 `BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_OBJECTS` 设置为 1 至 `2^63-1` 的十进制整数。取值先去除首尾空白，空值或只有空白时使用各自默认上限；`config/read` 返回实际生效的 `maxAttachmentStorageBytes` 与 `maxAttachmentStorageObjects`。字节按文件逻辑长度计量；容量扫描包含已引用附件和孤儿对象。进程中断留下的临时文件会在下次启动时按私有文件规则清理；未引用的内容寻址对象保留并计入容量。降低上限不会阻止读取已有附件，但会拒绝新增的唯一内容；相同 SHA-256 内容复用现有可信对象，不增加容量。附件名来自工作区文件，可能由外部仓库或下载提供：进入提示词标签时按技能注入的同一口径以 JSON 字符串字面量转义换行、引号与控制字符，避免伪造出额外的附件标注行；持久记录中的孤立代理项降级为 U+FFFD，正常文件名语义不变。

附件准入、对象发布及会话引用追加共用 SQLite 写事务，与会话删除的引用扫描和清理串行。发布前流式校验目标会话的完整日志；发现既有损坏时保留原日志和对象目录，不追加附件引用。写入失败后会在同一写锁下检查所有会话引用，再清理新发布且未引用的对象。对象目录中出现符号链接、非普通文件、非当前用户文件、额外硬链接或目标摘要与内容不符时，相关操作会 fail closed。容量拒绝通过 `attachment/add` 返回 JSON-RPC `-32005`，错误数据包含 `code=ATTACHMENT_STORAGE_LIMIT`、当前用量、限制和本次请求量；容量拒绝不会写入会话引用或部分附件。

正文读取按与工具结果相同的口径收敛：省略 `cursor`、`limit` 与 `sha256` 时整份返回 `{"attachment": {..., "content": ...}}`，整份回执超过约 1 MiB 单页预算返回 `-32010 / RESPONSE_TOO_LARGE`，数据含 `recoveryMethod=attachment/read`、`attachmentId`、`totalCharacters` 与 `suggestedLimit`，不再靠 8 MiB 帧上限兜底。显式给出三者任一即走分段：`limit` 默认 16384、最多 32768 个 Unicode 码点，回执为 `text`、`offset`、`nextCursor` 与 `contentRef`（绑定 `threadId`、`attachmentId`、名称、摘要、字节数与码点数）；游标前缀 `at1_` 绑定会话、附件与摘要，续读时传 `sha256` 与附件不符会返回 `STALE_ATTACHMENT`，错误数据的 `currentRef` 给出当前附件的同形引用。未知参数、非法游标与越界 `limit` 返回 `-32602`，附件不存在或不属于会话仍按原错误文本拒绝。读取不触发招聘工具，也不改写附件记录。握手能力 `capabilities.attachmentReadPaging` 为真表示内核支持这组分页参数；旧客户端省略新参数时行为与之前一致。

## 模块边界

| 路径 | 职责 |
| --- | --- |
| `apps/desktop` | Electron 主进程、preload 和 React 工作台 |
| `packages/protocol` | JSON-RPC、会话条目及通知契约 |
| `packages/app-client` | 进程连接、双向请求、握手、超时及重连 |
| `harness/src/boss_harness` | 执行、上下文、持久化、恢复和模型接入 |
| `harness/src/boss_harness/tools` | 招聘提示、工具契约、CLI 适配及平台暂停规则 |

## 显式工具组合

内嵌 Python 应用可通过 `ToolDefinition`、`ToolBundle` 与 `ApplicationService(tool_bundle=..., bridge_factory=...)` 组合工具。每个定义固定工具名、描述、对象 schema、handler 和是否逐次审批；注册表提供不可变的 handler/审批快照，以及只读 schema 投影。`requires_approval` 是安全分类：任何有外部或持久副作用的工具都必须设为 `True`。Bridge 工厂每次须返回独立、可弱引用且支持 `cancel_event` 的实例；应用会拒绝仍存活的重复实例。Bridge 可提供同步且应快速返回的 `close()`，或以 `dispose()` 作为兜底；临时运行器、连接检查和应用级实例分别由其所有者在工作结束或关闭时释放，重复关闭不会再次调用钩子。清理异常不会改写任务结果。

注册时只接受根为 object 的受限 JSON Schema 子集：`type`（单类型）、`properties`、`required`、`additionalProperties`（布尔）、`enum`、`anyOf`、数值上下界、`minLength` / `maxLength`、`pattern`（Python `re.search`）、`items`、`minItems` / `maxItems` 与 `uniqueItems`；`description`、`title`、`default` 仅作注释，不参与校验。`$ref`、`oneOf`、`allOf` 等关键字在注册时直接拒绝。规范化 schema 快照上限为 128 KiB，嵌套 schema 不超过 32 层；参数在运行期上限为 1 MiB，JSON 深度不超过 64、节点不超过 32768，非有限浮点、循环引用和非字符串键都会被拒绝。`tool/list` 投影与执行校验使用同一份规范化 schema。运行期只做校验，不填 `default`，也不做隐式标量转换；只有规则要求 `object` 或 `array` 且传入字符串时，才会尝试把该字符串解码为 JSON 结构，解码结果仍须完整通过同一 schema。需要“非空白”语义的必填字符串应显式声明 `minLength: 1` 与 `pattern: \S`；默认招聘工具即按此约定声明，使模型请求、`tool/list` 与执行前校验保持一致。

逐次审批在会话 JSONL 中保存审批 ID、期限、已校验参数摘要与裁决；`approval/list` 只返回未过期的待审批摘要，不返回原始参数，默认最多 100 条（上限 200），并可附可选 `threadCounts` 按会话统计全部待审批数量，不受列表上限影响，旧内核缺省该字段。工具名或条目 id 去空白后为空、超过 200 字符的损坏审批不进入索引、列表或计数，避免持久总数大于通知面板中可处理的条目。桌面渲染真实会话的审批卡时，缺少有效审批 ID 的记录不可提交并提示刷新会话核对，不会退回示例模式的本地裁决；审批结论仍须结合工具结果核对。`approval/respond` 会先持久化裁决，再唤醒仍活动的执行器；相同裁决重试幂等，相反裁决返回冲突。进程退出后，未过期审批仍可读取和裁决，但原回合会保持中断。恢复后的拒绝、过期会以 `not_executed` 收尾；恢复后的批准只记录批准事实，也以 `not_executed` 结束，旧工具不会被重放。若仍需该操作，用户须明确发起新回合并重新审批。归档会使未决审批过期，删除后旧审批 ID 不再有效。

默认招聘工具组合支持 `ApplicationService(prompt_preamble="...")` 只替换系统提示的身份段，默认工具说明、招聘规则、技能和只读限制仍由内核组装；默认路径仍启用平台连接检查及官方登录 host API。身份文本只接受非空、无控制字符且不超过 16 KiB 的 UTF-8 文本，不写入会话或事件。自定义 `ToolBundle` 的任意完整 `system_prompt` 没有可推断的分段，和 `prompt_preamble` 同时传入会明确拒绝；需要完全自定义提示时应自行提供完整 bundle。

嵌入方可向 `ApplicationService(lifecycle_hooks=[...])` 显式注入宿主策略对象。`on_event(context)` 在持久事件落库后按序异步接收有界投影，不含消息正文、思考、工具参数或结果；队列容量为 256，拥塞会记录 `kernel/hookError`。每个 `LifecycleHooks` 实例中所有 hook callback 合计最多 16 个在途 worker；名额在 callback 实际退出后释放，超时不会取消线程。容量满时观察回调会被跳过并按每秒最多一次合并诊断，关闭时刷新剩余汇总；持久事件仍正常处理。策略回调容量满时返回 `HOOK_BUSY` 并 fail closed。`before_tool_call(context)` 在 schema 校验后、审批和 handler 之前运行，可返回 `HookDecision(False, code, message)` 拒绝本次工具并暂停回合。策略收到与已验证工具参数一致的完整深只读 JSON 快照，不做事件观察所用的脱敏或截断；紧凑 JSON 以 UTF-8 编码后的总量上限为 1,052,672 字节，另受 32,784 个节点、深度 66 限制，超限或非 JSON 输入会在策略回调前 fail closed。返回允许、抛错、返回无效值或超时都不能跳过原有逐次审批，策略检查异常按拒绝处理。回调运行在独立 daemon worker 上，默认限时 250ms，宿主可传入 `hook_timeout`（最大 30 秒）；超时回调的迟到返回不会改写回合。hook 由宿主代码直接注入，不扫描或导入工作区文件，也不提供进程沙箱；嵌入方须把它视作可信代码。关闭时内核先收尾 worker，再在共享关闭期限内等待事件观察并调用 hook 的 `close()`。

`before_tool_call(context)` 保持旧的一参数形式兼容；需要协作取消的宿主可改为 `before_tool_call(context, *, signal)`，其中 `signal.aborted` 表示回合已取消，`signal.wait(timeout)` 可等待该状态。取消会结束内核的策略等待并忽略迟到决策；如果 hook 不检查 signal，它的 Python 线程仍会继续运行并占用在途名额直到退出，因此策略 hook 应保持无副作用并在可取消工作点检查 signal。取消接受与工具派发认领通过同一运行时锁排序：若取消先于派发认领，当前工具记录为 `CANCELLED / not_executed`，handler 不会被调用；此前已发出的审批请求不会撤回。若派发认领先发生，操作已被派发，handler 可能即将开始或已经开始，中断不能保证阻止该操作或撤销其副作用。

`before_request(context)` 同样兼容一参数和可选 `signal` 形式，在业务模型请求、每个摘要分片和模型连接检查的完整请求预算准备后、provider 调用前统一执行。`purpose` 分别为 `turn`、`compaction`、`connection_check`，`requestIndex` 从 0 开始，按对应回合、摘要任务或连接检查计数；上下文还包含 provider/model、消息与工具数量及预算快照，以及适用的 `threadId`、`turnId`、`jobId` 和业务请求上限，不包含消息正文、工具参数或凭据。策略不能改写请求；provider/SDK 内部的传输重试不重复经过此闸门。

自定义 provider 的 `stream(request)` 可读取 `request.task_context`，类型为从 `boss_harness.models` 导出的不可变 `ModelTaskContext`。它与上述策略检查使用同一请求身份，字段为 `purpose`、从零开始的 `request_index` 及可选 `thread_id`、`turn_id`、`job_id`；完整请求准备后由执行 owner 绑定，preparer 重建请求也不会丢失或改变归属。自动摘要沿用创建该任务时的回合 ID，每个分片独立编号；手动摘要的 `turn_id` 和连接检查的三个 ID 保持 `None`，不借用最近或正在运行的回合。直接构造 `ModelRequest` 时 `task_context` 默认为 `None`，旧 provider 可继续忽略该字段。

任务上下文只供本地嵌入方路由和关联请求使用；任务 ID 不能证明用户身份或计费归属。内置 OpenAI / Anthropic provider 不把它写入模型消息、HTTP metadata、预算或请求指纹，供应商内部传输重试沿用原上下文，不增加一次逻辑请求计数。

`after_tool_call(context, *, signal)` 在工具终态已持久化后、回合继续向模型请求前同步调用，覆盖成功、失败、拒绝、未执行和可确认的结果未知终态；即使回合已取消也会启动观察回调，并以 `signal.aborted=true` 告知宿主，内核可停止等待并记录 `kernel/hookError`。超时、异常、容量耗尽或取消都不改写工具事实，也不会重跑工具或审批。默认上下文只包含会话/回合/条目标识、工具名、状态、执行状态和错误码。要读取完整结构化结果，须显式使用 `ApplicationService(..., expose_tool_results_to_hooks=True)`，或构造 `LifecycleHooks(..., expose_tool_results=True)`；该结果可能含候选人个人信息。回调收到深只读快照且返回值被忽略，不能修改持久化结果或模型可见结果。若传入预构造的 `LifecycleHooks`，访问权限须在其构造时设置。

返回 `HookDecision(False, code, message)` 拒绝对应请求，provider 不会被调用。业务拒绝以 `error` 终止回合；摘要拒绝将任务以 `failed` 收尾，不提交新 checkpoint、不重试或继续后续业务请求，自动/溢出恢复摘要所在回合同样以 `error` 终止。业务与摘要的脱敏拒绝原因保存在 `model_error`，并分别通过 `session/error`、`context/compactionFailed` 通知，`requestRejected=true` 区分策略拒绝；模型连接检查在读取报告中保留 `failed`、策略 code、脱敏原因和该标记，下一次显式检查会清除旧标记。未发送的请求不会执行工具或申请审批；先前已完成的模型、工具和摘要分片事实仍保留。取消优先于拒绝；策略关闭或正在关闭时 fail closed，已运行 hook 的迟到允许结果也不能放行新请求。

## 模型运行所有权

活动业务回合仍受 `parallelThreads` 限制；活动与收尾回合合计最多保留 `2 * parallelThreads` 个执行 owner，`config/read.maxRetainedTurns` 返回这个上限。终态通知、bridge 清理或已认领 abort 尚未完成的任务继续占 owner 额度，允许一批收尾与下一批活动回合重叠。超过总量上限时直接请求返回 `TURN_OWNER_LIMIT`，不创建新 provider 或写入新回合/输入；相同请求编号的既有回执仍可去重读取。follow-up 保持 queued 并沿既有 FIFO 等待，worker 或迟到 abort 真正释放 owner 后再唤醒。迟到 abort 只向初始化时启动的单一 worker 发信号，避免在线程启动失败的取消路径里同步执行其他会话；通知合并，关闭会等待该 worker 收尾并拒绝新工作。额度不计历史终态、纯回执通知或不再持有 provider 的队列存储收尾，也不授权重放任何请求。

`runtime/resources/read` 返回当前进程的 active/cleanup turn 与手动/自动摘要 owner、阶段、取消/abort 状态及运行时长，并展示去重 FIFO follow-up 等待列表的位置和等待时长。owner 最多返回 32 项，waiter 最多 32 项；总数与截断标志明确表示省略内容。时长使用单调时钟，仅在进程内有效。读取只投影内存中的 live owner，不扫描历史 session、不持久化、不调度/取消工作，也不暴露输入正文、工具参数或结果、模型内容、异常原文和凭据。已完成的历史 task 不能据此推断为当前 owner；持久 parent/child 关系由独立任务读取能力负责。

嵌入方使用 `ApplicationService(provider_factory=...)` 并发运行模型回合时，工厂须提供独立实例。非空返回值不能是应用主 provider，也不能被其他业务 worker（包括已释放执行槽位但仍在通知/收尾的 worker）或尚未完成收尾的摘要持有；违规调用在预留回合、保存输入前拒绝，不会中断原 owner。手动与自动摘要同样拒绝借用尚未完成收尾的业务 provider。模型执行、终态通知、bridge 清理及已认领的 abort 都完成后才允许临时实例串行复用，防止旧中止误伤新请求；后续队列派发的尾部继续单独持有状态目录责任。未传工厂的主实例串行路径也遵守上述条件，工厂返回 `None` 的无模型路径保持兼容。默认内建工厂创建新实例，模型摘要仍要求独立于主回合的 provider。

## 上下文 usage

完整请求预算默认使用保守字符估算。成功的 OpenAI 或 Anthropic 响应会保存 provider、模型、完整请求指纹和消息前缀长度；下一次请求只有在这些边界仍匹配时才使用 input usage 作为基线，并对新增消息继续估算。OpenAI 的缓存 input 是总 input 的子集，Anthropic 的缓存读写字段按独立计数处理，避免重复计算。模型、提示、工具、请求选项或可追溯摘要变化后会回退到字符估算；这不是精确 tokenizer 或计费保证。

按 `keepRecentTokens` 规划保留范围时，也只在相邻的成功请求锚点都与当前 provider、模型和消息前缀指纹精确匹配时，使用两次 input usage 的差值校准对应消息，再聚合到完整回合。没有被后续请求观察到的最新消息、摘要占位或无法证明回合归属的投影继续使用字符估算；无效、冲突或非单调锚点不参与校准。计划会说明是否用了匹配区间和锚点数量；目标仍是估算值，完整回合边界可能让实际保留量超过目标。

长会话可先调用 `context/compact/plan` 获取完整回合的 source item IDs 和 SHA-256，再将 `sourceDigest` 一并提交给 `context/compact`，或调用 `context/compact/start` 让内核后台生成摘要。来源在摘要准备期间发生变化时，内核拒绝写 checkpoint；原始条目、工具调用和工具结果始终保留。摘要任务不执行招聘工具，也不改变工具权限。

已结束回合中的用户消息和助手文本可通过 `context/edit/read` 查看原始文本及当前模型上下文，再用 `context/edit` 追加替换文本或以 `replacementText=null` 从后续模型请求中排除。编辑只影响模型上下文，不删除或改写原始会话记录，也不撤销已执行工具或外部操作；读取会话时的 `contextEdit` 标记及桌面消息提示说明该状态。编辑请求绑定 `sourceDigest`，并发变化时拒绝提交，应重新读取后由用户确认，不自动重试。活动条目、工具调用/结果和已由摘要检查点覆盖的消息不能编辑；可从已有摘要之后继续编辑保留尾部。摘要的 `sourceItemCount` 先按未过滤的规范条目定位来源，再应用 excluded 投影，避免排除一条旧消息后隐藏尚未摘要的尾部；预览、保存、重开、fork 和后续请求使用相同投影。预算与之后的摘要都采用当前编辑投影，fork 只继承其所选历史内的编辑。要恢复原文参与模型上下文，可在既有替换文本上限内将原始文本作为新的替换内容提交。`context/edit/read` 与编辑成功回执均受既有约 1 MiB 单页响应预算约束，按 UTF-8 与 JSON 转义后的完整投影计算；编辑在同一 writer 锁内先构造并校验提交后的回执，再追加记录。预算超限返回 `-32010 / RESPONSE_TOO_LARGE`（恢复提示为 `thread/resume`、`snapshot=true`），拒绝的编辑不落盘也不发送 `context/edited`。快照及正文分页可核对完整助手原文，但不会绕过编辑回执预算；需要继续整理时，可从目标消息之前的完整回合创建分支，或在新会话中提供必要内容。

`plan` 和 `start` 可指定 `throughTurnId`，或省略截止回合并指定 `keepRecentTokens`（默认 20000，正整数、最多 1000000）；两者互斥。内核从最新回合向前估算，保留达到目标的完整近期回合，只摘要更早前缀；实际保留量可能大于目标，工具调用与结果不会被拆开。没有可摘要前缀时明确拒绝，可读取计划的 `retainedTurnIds`、`firstKeptItemId` 和 `estimatedRetainedTokens` 核对范围。小窗口应选择适合窗口的保留目标。

例如先读取 `context/compact/plan` 参数 `{"threadId":"…","keepRecentTokens":4000}`，再将同样参数与计划返回的 `sourceDigest` 传给 `context/compact/start`。`digestVersion=2` 同时绑定原始选中条目和最新旧摘要 checkpoint；旧客户端持有的 v1 digest 会冲突，应重新读计划，不能移除 digest 自动重试。用户直接提交摘要的 `context/compact` 仍要求明确截止回合，省略 digest 的旧调用保持兼容。

原文和执行状态会完整序列化，超长单条工具结果也按 Unicode 码点连续分片。每步使用独立于业务回合的同一摘要 provider、前一步临时摘要和下一片原文，重新检查完整请求预算；摘要输出储备按窗口适配，业务回合输出储备保持原配置。最多 32 个摘要生成阶段，传输层重试仍由 provider 管理；原文不截断、中间摘要不写 checkpoint。取消、非法输出、来源变化、阶段上限或预算不足都不提交新摘要；旧摘要覆盖的原始记录后来被修订时也会拒绝继续压缩，须先核对一致性。全部片段成功后再核对默认业务模型的 system、工具与保留历史预算，通过后只追加一次 checkpoint。这不保证后续新增输入、技能、附件或切换模型仍能容纳，也不保证模型摘要语义无损；原始记录始终保留。

读取模型历史与上下文时也会核对摘要来源。已覆盖条目发生追加修订、来源不完整或摘要字段无效时，历史回退最新完整逻辑原文，`context/read` 返回 `checkpoint=null`，原始 checkpoint 仍留在记录中；回退后的完整请求继续受预算约束。正常活动尾部与未被摘要覆盖的修订保留原有投影。显式摘要规划仍会拒绝不一致来源，尚未提供失效摘要的自动重建流程。

`context/compact/read` 和 `abort` 通过 `jobId` 定位任务；`context/compactionProgress` 与任务读取返回 `modelRequestCount`、`processedCharacters`、`totalCharacters`。逐步 usage 保存来源字符范围和整份材料 SHA-256，`eligible=false`，失败前已使用的模型用量仍可追溯。错误消息擦除配置中的 API key；checkpoint 写入成功后，后续读取或通知异常不会将任务改为失败。任务和取消句柄属于当前内核进程，重启后不自动续跑摘要或招聘工具。

摘要 checkpoint 使用专用原子发布：最终来源校验与复制都持有同一个 SQLite writer 锁，旧日志逐字节复制到同目录临时文件，追加 checkpoint 并成功 flush/fsync 后才替换会话路径。公开前的写入、同步或替换失败不会改变原文件及旧摘要；替换异常时若目标 inode 确认为已同步的候选，则仍视为已提交。无法确认目标时返回 `COMPACTION_COMMIT_UNCERTAIN`，表示摘要可能已生效，应先重新读取状态，不自动重复生成；该结果不会被取消改称为干净取消。已提交后的索引、读取或通知故障使用 `COMPACTION_COMMITTED_REFRESH_FAILED`，后台任务保持 completed 并显示刷新提示；同步 `context/compact` 的错误数据明确携带 `checkpointCommitted=true`，自动摘要则停止当前业务回合。

新 checkpoint 只持久化 `sourceItemCount`，不再重复保存完整覆盖前缀的 `sourceItemIds`；读取时按 `throughTurnId` 重建完整回合前缀，并校验条目数、完整回合边界及 checkpoint 写入前的原始来源。旧 checkpoint 中的 `sourceItemIds` 仍可读取；`context/read` 和 `context/compact/plan` 继续返回完整 `sourceItemIds`，接口调用方无需迁移。下一次摘要请求会保留前一摘要和必要元数据，但把旧 checkpoint 的 ID 列表规范化为条目数，避免将不断增长的来源 ID 重复放入模型输入。原始记录仍保留，读取和原子发布仍须处理整份会话日志。

此机制保留旧 checkpoint、旧记录及普通追加语义。所有会话写入须经由 `SessionStore`，以共享 SQLite writer 锁串行化；不支持其他进程直接修改会话 JSONL。每次摘要需要复制整份日志，占用一份日志大小的临时空间，并在复制期间串行化同库其他 writer；磁盘不足时保留原文件。仅支持本地文件系统上的当前用户普通单链接会话文件，拒绝符号链接及额外硬链接，保留 POSIX mode 与 group；ACL、扩展属性等额外文件元数据不在复制保证内。候选路径在发布前按已同步 inode 和元数据核验，替换后也核验目标 inode；无法确认时按结果不确定处理。临时文件在成功 fsync 后才公开，事务内还会同步会话目录项，保证进程内及重新打开时的完整快照边界，并让本地文件系统上的已公开替换在掉电后仍可解析；远程文件系统的目录同步语义及硬件/文件系统自身缺陷不在保证内。读取时可能取得完整旧快照或完整新快照，不会看到未同步的候选 checkpoint。

手动后台摘要最多同时持有 `parallelThreads` 个执行额度；已显示 completed、cancelled 或 failed 但 worker、终态通知或已认领 abort 尚未完成的任务仍占额度，新任务返回 `COMPACTION_CONCURRENCY_LIMIT`，不创建 provider。自动摘要随活动回合并发槽位受限，不重复占用手动池。任务的 worker、终态通知及已认领 abort 全部完成后，释放 provider、模型凭据配置、取消句柄和 worker，再进入最近 64 条终态缓存；历史及重启恢复的终态不占执行额度，错误消息最多保留 2048 个字符。已显示取消但尚未完成 abort 的任务继续保留实例及会话所有权。更旧的任务仍可从会话事件历史追溯，但 `jobId` 读取和取消会返回 `COMPACTION_JOB_NOT_FOUND`。桌面取消入口收到该错误时会收敛本地 running 状态并说明任务不会重放；其他失败仍按回执未知处理。桌面面板对开始应答缺失、终态引用存在但详情不可读的情况也会停止跟踪并解除本地锁；运行中任务连续无法核对时设置 `lifecycleReleased`，停止轮询并允许重新规划。这些只是渲染层收敛，不改写内核任务状态或并发额度，新请求仍可能被内核拒绝。摘要 checkpoint、usage 与事件不会因内存任务淘汰而删除。

schema 接受受限 JSON 子集：单一 `type`、`properties`、`required`、布尔型 `additionalProperties`、`enum`、`anyOf`、数值/长度/数组边界、Python `re.search` `pattern`、数组 `items`/`uniqueItems`，以及 `title`、`description`、`default` 注释。不支持引用和未知关键字；`default` 不会自动填充。若 schema 要求 object/array 而模型将该值作为 JSON 字符串返回，内核会解码一层并按同一 schema 复验；`anyOf` 已接受原字符串时保持原值。定义、桥接和暂停回调由嵌入应用显式提供，属于可信宿主代码，不构成进程沙箱。

默认 CLI 仍装配原招聘工具组合。传入自定义 bundle 时，平台 local 检查及登录 host API 显示为 disabled/`NOT_SUPPORTED`，不会按 bundle id 获得招聘权限；模型连接检查仍可用。不会扫描技能目录、自动导入扩展或提供插件市场。

## 工作流、会话与桌面设置

### 上下文：可追溯地压缩，而不是删除历史

会话原始记录保留在 JSONL；模型看到的是经过摘要、编辑和预算校验的投影。手动摘要可生成、观察、取消，摘要来源切点、usage、checkpoint 和重启结果都可追溯。冻结快照用于读取一致的历史切面，不会让模型重新执行已经完成的工具。

### 桌面运行与队列

Electron 运行时从官方源单独下载和校验，失败后需先恢复安装再启动。`none` 模式不调用模型；使用 `/tools` 或 `/search 关键词` 时仍会调用配置的上游 CLI。

默认桌面模型为 OpenAI Responses，可由 `BOSS_HARNESS_PROVIDER` 选择 `openai`、`anthropic` 或 `none`；`auto` 与省略等价，空值或只有空白按未设置处理，使用 `openai`。OpenAI 配置读取本地 Codex 配置或 `BOSS_HARNESS_OPENAI_*` 环境变量；Codex profile 的凭据支持 `experimental_bearer_token` 与 `env_key`（显式环境凭据优先于文件令牌，文件令牌优先于 `env_key`）。可用 Codex profile 的 `wire_api` 仅接受 `responses`，忽略大小写与首尾空白，缺省或空白使用该默认值；其他协议或非字符串在配置解析时以 `MODEL_CODEX_WIRE_API_UNSUPPORTED` 拒绝，正常启动与 `--check` 均在请求前退出 `2`，不尝试其他协议。完整显式 OpenAI 配置仍跳过该文件。Anthropic 使用 `ANTHROPIC_*`。`--check` 对显式 `http://` 且非本机回环的模型端点报告 `MODEL_ENDPOINT_INSECURE` 警告，提示凭据可能明文传输，不输出端点；该判断只解析配置字符串，不联网、不构造 SDK。显式 `BOSS_HARNESS_EFFORT` 不属于内核支持的七档时报告 `MODEL_EFFORT_UNSUPPORTED` 警告；Anthropic 线路下 `BOSS_HARNESS_THINKING` 非空且不是 `summarized` 时报告 `MODEL_THINKING_IGNORED` 警告，OpenAI 与 none 线路不因该变量报警。两项都只说明配置不会按预期生效，不阻止启动，也不回显原值。真实模型请求可能联网并产生费用。不要将凭据写入仓库或公开日志。

工具可执行文件按 `BOSS_CLI_BIN`、并排 `boss-agent-cli/.venv/bin/boss`、PATH 的顺序查找；仅为目录、断链或不可执行的候选会被跳过；指向可执行文件的符号链接仍可使用。显式设置 `BOSS_CLI_BIN` 却回退到其他来源时，`--check` 以 `BOSS_CLI_BIN_IGNORED` 警告说明实际未采用显式配置，不输出路径；最终没有可用 CLI 时仍报 `BOSS_CLI_UNAVAILABLE`。`BOSS_CLI_DATA_DIR` 是上游登录及平台状态目录，`BOSS_HARNESS_DIR` 是本项目的会话目录（默认 `~/.boss-harness/harness`；旧 `BOSS_CLI_HARNESS_DIR` 与 `~/.boss-cli/harness` 仍兼容读取），两者分别管理。环境变量值以 `~` 开头且本次检查使用的正是该字面路径时，`--check` 以 `STATE_DIRECTORY_TILDE` 警告说明内核不展开 `~`；显式 `--state-dir` 指向其他路径时不因残留环境变量报警。旧变量显式非空时，`--check` 以 `LEGACY_STATE_ENV_PRESENT` 警告提示迁移，路径条件失败时仍优先报告目录错误码。状态目录路径检查通过后，`--check` 还读取该目录或最近存在祖先所在文件系统的剩余空间，低于 512 MiB 时以 `STATE_DIRECTORY_LOW_SPACE` 警告建议释放空间；不输出路径或确切字节，读取失败时保持通过。业务 CLI 可执行文件存在时，`--check` 若发现两者解析后相同或互相包含，会以 `BOSS_CLI_DATA_DIR_OVERLAP` 警告；只读路径，不创建目录，也不执行 CLI。数据目录与状态目录不重叠、解析后等于或位于当前 git 工作区内时，`--check` 以 `BOSS_CLI_DATA_DIR_IN_REPO` 警告建议移出仓库，避免登录态与平台缓存被提交；以 `~` 开头的值不展开，也不参与该判断。

启动 Harness 或桌面应用前，可用 `BOSS_HARNESS_BROWSER_SOURCE` 覆盖业务 CLI 的浏览器来源：`auto`、`existing-browser` 或 `stored-cookie`；取值去除首尾空白并忽略字母大小写。未设置、空值或仅含空白时完整继承上游 `config.json`。显式覆盖只传递上游 `--browser-source` 参数，不读取或改写该共享配置；不支持该参数的 CLI 会明确失败，不自动去掉参数重试。连接设置页会显示当前覆盖值或“继承上游 CLI 配置”。

运行中的会话支持把新消息“转向当前回合”或“排到后续回合”。转向消息会在当前工具批次结束后、下一次模型请求前加入；后续消息等当前任务自然结束后再启动。内核声明 `queueSteer` 时，排队中的 follow-up 可经 `queue/steer` 原子改为当前回合 steering：必须存在 active turn 且 `expectedTurnId` 匹配，只接受 `queued` 的 follow-up；带 `skillIds` 或 `autoCompaction` 的项返回 `STEER_UNAVAILABLE` 且不修改记录，成功后沿用现有 steering 领取 / 注入 / 暂停路径。停止任务仍是独立操作。队列显示持久状态，尚未投递的项目可以撤回；未知提交回执会保留原文并使用同一请求编号重试，不会自动重复排队。仅当后续回合项为 `paused / TURN_START_FAILED` 且 `inputPersisted` 明确为 `false` 时，桌面提供“重新排队”：以新的 `clientUserMessageId` 和原输入、`skillIds` 调用 `queue/add`，受理后再 `queue/remove` 撤回旧项；旧项撤回失败时保留为暂停项可手动撤回，不自动重放任何工具、审批或平台操作。重新排队已受理但队列刷新失败时，本地持久总数只按新项增加；撤回只把旧项标记为已取消，不删除持久记录。队列读取有界：`thread/read`、`thread/resume`（含快照）与 `queue/list` 优先保留 `paused` 项，再按最近顺序保留 `queued` / `delivering` 项；待处理项单次最多 200 项，名额允许时另返回最近 50 个已终结项。正文预览截断为 600 字符并标 `inputTruncated`，响应附 `queueTotalItems` / `queueActiveItems` / `queueCounts` / `queueTruncated`（`queue/list` 为 `totalItems` / `activeItems` / `counts` / `truncated`）；总数与分类计数按全部有效持久记录统计，不受条目投影截断影响，旧内核缺省这些字段。完整单项正文经只读 `queue/get` 读取，重新排队使用该结果而不是预览。桌面渲染层对 `queue/list` 与 `thread/resume` 共用同一套元数据校验：已接受的总数或待处理数大于已载入项时按截断处理，截断标记缺失或误报为 `false` 不改变结论；分类计数必须与已接受的待处理总数一致，`thread/list` 会话行的分类计数也以待处理总数通过校验为前提。提交核对因此不会把未载入的消息判为「不存在」，队列面板与驾驶舱也不会把截断投影当成完整队列。驾驶舱的队列摘要优先采用内核持久分类计数，与队列面板、侧栏徽标一致；只有旧内核缺省分类、或分类合计与待处理总数不一致时，才按已载入项统计并在截断时标注「分类按可见项计数」。

后续回合在线程启动前失败时，队列暂停并显示“启动失败，未执行”，同时注明输入是否已保存在当前会话；无法核实时提示先核对。已保存输入保留，相同请求编号不会重复写入或执行。暂停项可撤回，核对后可明确发起新任务，不会自动重试。线程已经实际启动时，即使启动调用随后抛错，也继续由原 worker 完成执行和资源收尾。旧记录缺少失败关联信息时保持原状态，不推断可重试。

工具 handler 返回后若结果记录写入异常，内核先按原条目身份核对完整结果并有限重试，不会重新执行工具或复用审批。恢复到完整结果后会暂停当前批次和后续队列；若结果不能确认，保存 `outcome_unknown` 并要求先核对外部状态。连未知状态也无法确认时，该会话在当前进程内拒绝新的模型回合和排队请求，重启后由会话恢复流程核对，不自动重放工具。

同一会话内，直接发送和后续排队共用 `clientUserMessageId` 请求身份。相同编号与原始输入命中旧请求时，队列关联原回合，不新增输入或执行；“已投递”仅表示输入已被接受，不表示原回合成功。明确未启动的旧失败保留暂停，执行证据不足时提示核对，不从 `error` 推断未执行。尚未产生回合的排队、暂停或撤回请求不能通过直接发送绕过原状态；新任务应使用新编号。相同编号的不同输入、steering 类型冲突或历史身份歧义会明确拒绝。

桌面恢复边界：`context/edit` 与 `context/edit/read` 的内核错误在主进程保留结构，渲染层可展示错误码并区分明确拒绝与传输未确认。分支切换的队列核对、`thread/leaf/set` 回执与后续会话重读均绑定发起时的连接代次；断连释放旧操作的界面等待状态，旧调用不再继续提交、采纳任务、触发刷新或以成功关闭新窗口，其收尾也不清除新操作状态。已提交的切换不回滚，不自动重放；恢复连接后仍由用户核对当前位置并显式确认。

分支摘要 `context/compact/abort` 的界面回执与收尾绑定到发起时的连接代次和 `jobId`；断连、卸载或当前任务被替换后，旧成功、失败及 `finally` 不再采纳任务、写入提示、释放新取消锁或触发刷新。新运行任务不继承旧任务的 `cancelInFlight`，同一任务继续保留其在途取消锁。返回的任务必须属于同一会话且 `jobId` 与请求一致，否则提示核对；已确认的任务终态优先于迟到取消失败。正常取消仍只表示请求受理，实际停止以终态为准，已生效的分支切换不回滚，也不自动重发取消。

从已结束回合创建分支时，只复制该边界内的历史与上下文，不继承原会话的执行队列。已投递的消息保留为普通历史，原会话队列保持不变。`thread/fork` 可用 `title` 指定新分支名称；显式非 null 值须为最多 500 字符的字符串，超限或错误类型在创建文件前返回 `-32602`，与新建、重命名的标题长度上限一致。缺省或 null 继承原标题，空字符串保持可用；该长度校验不追溯改写已有会话。分支不复制读取投影的派生标记（`projectIdTruncated`、`titleTruncated`）：这些标记只描述来源会话的读取结果，写入新会话头会变成无法清除的永久状态。来源会话的 `projectId` 已被投影截断时，分支省略该字段而不复制截断值。这项继承修正作用于此后创建的分支，已有会话文件不追溯改写。

宿主可通过 JSON-RPC `thread/delete({threadId})` 永久删除空闲会话。仍有回合、摘要、队列交接或清理 worker 持有的会话会以 `THREAD_BUSY` 拒绝；成功后发送不含会话正文的 `thread/deleted` 事件。删除覆盖会话记录、该会话的事件、SQLite 投影、应用管理的索引修复备份，以及未被其他会话引用的附件。历史分支是独立副本，会继续保留；已经发给模型、客户端或 hook 的数据、外部工具创建的文件与平台操作不会被撤销。`thread/delete` 在桌面 renderer 白名单中；桌面在标题栏与侧栏会话菜单提供「删除聊天」，经确认框后调用该接口。确认框会在存在时列出会一并清除的本机未发送正文、附件、已选技能、正在读取的附件与消息反馈，并说明操作不可恢复；成功后桌面移除该会话的列表项、缓存、本机置顶 / 隐藏 / 别名 / 分组记录与返回历史。内核以 `THREAD_BUSY` 拒绝时聊天原样保留；`THREAD_DELETE_INCOMPLETE` 与 `THREAD_NOT_FOUND` 表示会话已隐藏或已不存在，桌面移除列表项并提示后续清理；其他未确认结果保留列表，提示刷新核对，不把未确认说成已删除。

桌面分别分页读取普通与已归档列表，通过单飞和尾随刷新合并通知。会话新建、删除、重命名、归档 / 恢复及模型设置的通知或本地成功回执会使在途列表失效；旧成功结果不回写列表或当前会话，旧失败不覆盖提示，沿用尾随刷新补读最新列表。当前读取失败仍保留已有列表并显示错误。该保护只作用于桌面投影，不改变内核列表、删除结果或持久化语义。

删除使用可恢复的私有意图标记；清理中断时会话立即从读取、列表及事件回放中隐藏，内核启动时继续清理。该操作移除应用当前存储中的逻辑副本，不承诺覆盖 APFS/SSD 上的历史文件块，也不会清理 Time Machine、文件系统快照或用户自行复制的备份。

### 技能上下文

将运行时技能放在工作区 `.boss-harness/skills/<id>/SKILL.md`（旧 `.boss-cli/skills` 仍兼容读取） 中，可用 frontmatter 的 `name`、`description` 提供名称和说明。输入区“技能”菜单从内核加载目录，允许刷新或失败后重试；目录发现按字典序保留候选，可加载技能最多 100 个，单文件按 UTF-8 原始字节限制为 64 KiB，坏编码、超限文件、符号链接和非普通文件会被跳过，单个无效文件不会阻断其他技能。`skills/list`、`skills/read`、`skills/create` 与 `skills/write` 共用的投影把名称限制为最多 200 字符、描述限制为最多 500 字符，超长部分截断并分别附 `nameTruncated` / `descriptionTruncated`；`skills/read` 的 `content` 仍返回完整正文。`skills/list` 另有单页响应预算检查，避免 100 个接近上限的描述因总量或 JSON 转义超过协议帧上限。未加载项清单与可加载技能分别封顶：已加载技能最多 100 个，未加载项同样最多列出 100 个，任一不足上限且候选窗口未覆盖全部目录时按 100→200→400→800 扩大，单次扫描最多检查 800 个目录项；可加载技能被展示上限截断时返回 `skillsTruncated`，未加载项被截断时返回 `problemsTruncated`，仍有目录未检查时返回 `candidatesTruncated`，三者缺省即表示对应清单完整；「未检查」以候选枚举是否丢弃过目录为准，目录总数恰好等于窗口时不算截断。每次最多选择 10 项，随新会话首轮、已有会话的直接发送或「排到后续回合」的队列消息生效：`queue/add` 的 `skillIds` 在入队时按目录校验并去重持久化，后续回合启动时加载，相同请求编号重试须使用同一技能组合，成功转交后清空选择。技能作为该回合的提示上下文，不自动执行目录脚本，也不扩大工具允许清单或审批权限。转向当前回合的消息不使用技能；有选择时会提示清除或改为后续回合。
