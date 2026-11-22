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
- [构建前检查](#构建前检查)
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

<a name="构建前静态检查"></a>

## 构建前检查

`scripts/check_*.py` 核对源码、配置和文档。部分脚本还直接调用内核函数或本地子进程，验证工具结果投影、会话归并和双端搜索归一化等行为。涉及持久化写入的离线检查使用临时目录。运行这组脚本无需网络、模型凭据或招聘平台账号。

在仓库根目录使用 Node.js 24+、npm 和 Python 3.11+ 运行 `npm run check`。命令默认使用 `.venv/bin/python`，也可通过 `PYTHON` 指定解释器。它按文件名顺序运行全部脚本，遇到首个失败即返回该脚本的退出码。可用同一个解释器单独运行某个脚本，例如 `.venv/bin/python scripts/check_tool_results.py`。

CI 的 Source build 在安装项目依赖前逐个运行同一组脚本。Python 3.10–3.14 的矩阵运行部分检查并编译源码。各脚本的覆盖范围见本节下表与对应说明，实际环境的验收范围见[项目状态](STATUS.md#待完成与待验收)。

新增检查脚本时须接入 `.github/workflows/build.yml` 并在本节补充同名小节。两处分别由 `check_workflows.py` 与 `check_docs_links.py` 核对。

| 领域 | 脚本 |
| --- | --- |
| 版本与发布元数据 | [`check_versions.py`](#check_versionspy)、[`check_release_assets.py`](#check_release_assetspy) |
| 协议与传输 | [`check_protocol.py`](#check_protocolpy)、[`check_rpc.py`](#check_rpcpy)、[`check_rpc_pending.py`](#check_rpc_pendingpy)、[`check_item_content.py`](#check_item_contentpy) |
| 共享工具 | [`check_shared_utils.py`](#check_shared_utilspy)、[`check_duration_parity.py`](#check_duration_paritypy) |
| 桌面与 IPC 安全 | [`check_desktop_security.py`](#check_desktop_securitypy)、[`check_login_security.py`](#check_login_securitypy)、[`check_notifications.py`](#check_notificationspy)、[`check_window_state.py`](#check_window_statepy)、[`check_renderer_recovery.py`](#check_renderer_recoverypy)、[`check_deleted_thread_state.py`](#check_deleted_thread_statepy)、[`check_compaction_override.py`](#check_compaction_overridepy)、[`check_branch_switch.py`](#check_branch_switchpy)、[`check_branch_pagination.py`](#check_branch_paginationpy)、[`check_harness_events.py`](#check_harness_eventspy)、[`check_harness_replica.py`](#check_harness_replicapy)、[`check_lifecycle.py`](#check_lifecyclepy)、[`check_client_transport.py`](#check_client_transportpy)、[`check_host_connection.py`](#check_host_connectionpy) |
| 内核工具与审批 | [`check_harness_tools.py`](#check_harness_toolspy)、[`check_process_io.py`](#check_process_iopy)、[`check_tool_schema.py`](#check_tool_schemapy)、[`check_tool_arguments.py`](#check_tool_argumentspy)、[`check_model_tools.py`](#check_model_toolspy)、[`check_domain_tools.py`](#check_domain_toolspy)、[`check_tool_results.py`](#check_tool_resultspy)、[`check_tool_revision.py`](#check_tool_revisionpy)、[`check_toolkit.py`](#check_toolkitpy)、[`check_approval.py`](#check_approvalpy)、[`check_approval_item.py`](#check_approval_itempy)、[`check_approval_digest.py`](#check_approval_digestpy)、[`check_pending_approvals.py`](#check_pending_approvalspy)、[`check_approval_remember.py`](#check_approval_rememberpy)、[`check_loop_guard.py`](#check_loop_guardpy) |
| 执行循环与队列 | [`check_queue_steer.py`](#check_queue_steerpy)、[`check_queue_state.py`](#check_queue_statepy)、[`check_catchup_boundary.py`](#check_catchup_boundarypy)、[`check_request_identity.py`](#check_request_identitypy)、[`check_queue_view.py`](#check_queue_viewpy)、[`check_queue_counts.py`](#check_queue_countspy)、[`check_task_ownership.py`](#check_task_ownershippy)、[`check_task_relation.py`](#check_task_relationpy)、[`check_turn_stream.py`](#check_turn_streampy)、[`check_turn_continuation.py`](#check_turn_continuationpy) |
| 模型线路 | [`check_model_disable.py`](#check_model_disablepy)、[`check_request_policy.py`](#check_request_policypy)、[`check_usage.py`](#check_usagepy)、[`check_turn_limits.py`](#check_turn_limitspy)、[`check_output_budget.py`](#check_output_budgetpy)、[`check_stream_pump.py`](#check_stream_pumppy)、[`check_errors.py`](#check_errorspy)、[`check_continuation.py`](#check_continuationpy)、[`check_capabilities.py`](#check_capabilitiespy)、[`check_codex_config.py`](#check_codex_configpy)、[`check_retry.py`](#check_retrypy)、[`check_openai_responses.py`](#check_openai_responsespy)、[`check_anthropic_provider.py`](#check_anthropic_providerpy) |
| 启动自检 | [`check_startup_diagnostics.py`](#check_startup_diagnosticspy) |
| 上下文保留与编辑 | [`check_context_keep.py`](#check_context_keeppy)、[`check_context_edits.py`](#check_context_editspy)、[`check_context_estimate.py`](#check_context_estimatepy)、[`check_summary.py`](#check_summarypy)、[`check_compaction.py`](#check_compactionpy)、[`check_session_fork.py`](#check_session_forkpy)、[`check_fork_checkpoints.py`](#check_fork_checkpointspy)、[`check_branch_projection.py`](#check_branch_projectionpy)、[`check_item_ownership.py`](#check_item_ownershippy)、[`check_branch_list.py`](#check_branch_listpy)、[`check_turn_records.py`](#check_turn_recordspy)、[`check_set_leaf.py`](#check_set_leafpy)、[`check_branch_summary.py`](#check_branch_summarypy)、[`check_item_projection.py`](#check_item_projectionpy)、[`check_read_item.py`](#check_read_itempy)、[`check_page_cursor.py`](#check_page_cursorpy)、[`check_entries_snapshot.py`](#check_entries_snapshotpy) |
| 本地资源与隐私 | [`check_private_files.py`](#check_private_filespy)、[`check_secret.py`](#check_secretpy)、[`check_export_privacy.py`](#check_export_privacypy)、[`check_export_write.py`](#check_export_writepy)、[`check_export_html.py`](#check_export_htmlpy)、[`check_export_markdown.py`](#check_export_markdownpy)、[`check_export_json.py`](#check_export_jsonpy)、[`check_local_export.py`](#check_local_exportpy)、[`check_export_dialog.py`](#check_export_dialogpy)、[`check_usage_report.py`](#check_usage_reportpy)、[`check_recent_search.py`](#check_recent_searchpy)、[`check_session_title.py`](#check_session_titlepy)、[`check_search_rows.py`](#check_search_rowspy)、[`check_message_search.py`](#check_message_searchpy)、[`check_find_highlight.py`](#check_find_highlightpy)、[`check_search_status.py`](#check_search_statuspy)、[`check_search_options.py`](#check_search_optionspy)、[`check_find_step.py`](#check_find_steppy)、[`check_find_status.py`](#check_find_statuspy)、[`check_find_seed.py`](#check_find_seedpy)、[`check_thread_search_result.py`](#check_thread_search_resultpy)、[`check_model_switch.py`](#check_model_switchpy)、[`check_session_index_health.py`](#check_session_index_healthpy)、[`check_queue_status.py`](#check_queue_statuspy)、[`check_notification_labels.py`](#check_notification_labelspy)、[`check_sidebar_notice.py`](#check_sidebar_noticepy)、[`check_usage_view_keys.py`](#check_usage_view_keyspy)、[`check_send_failure.py`](#check_send_failurepy)、[`check_last_session.py`](#check_last_sessionpy)、[`check_ui_storage.py`](#check_ui_storagepy)、[`check_thread_list.py`](#check_thread_listpy)、[`check_session_start.py`](#check_session_startpy)、[`check_time_format.py`](#check_time_formatpy)、[`check_preferences_file.py`](#check_preferences_filepy)、[`check_theme_preference.py`](#check_theme_preferencepy)、[`check_single_flight.py`](#check_single_flightpy)、[`check_queue_read_guard.py`](#check_queue_read_guardpy)、[`check_attempt_token.py`](#check_attempt_tokenpy)、[`check_delete_thread_error.py`](#check_delete_thread_errorpy)、[`check_session_error_notice.py`](#check_session_error_noticepy)、[`check_alias_migration.py`](#check_alias_migrationpy)、[`check_queue_retry.py`](#check_queue_retrypy)、[`check_clipboard_copy.py`](#check_clipboard_copypy)、[`check_home_draft.py`](#check_home_draftpy)、[`check_queue_badge.py`](#check_queue_badgepy)、[`check_skills.py`](#check_skillspy)、[`check_workspace_instructions.py`](#check_workspace_instructionspy)、[`check_attachments.py`](#check_attachmentspy)、[`check_attachment_add.py`](#check_attachment_addpy)、[`check_attachment_read.py`](#check_attachment_readpy)、[`check_attachment_context.py`](#check_attachment_contextpy)、[`check_skill_context.py`](#check_skill_contextpy)、[`check_skill_catalog.py`](#check_skill_catalogpy)、[`check_skill_write.py`](#check_skill_writepy)、[`check_skill_descriptor.py`](#check_skill_descriptorpy)、[`check_hooks.py`](#check_hookspy)、[`check_persistence.py`](#check_persistencepy)、[`check_session_log.py`](#check_session_logpy)、[`check_exact_read.py`](#check_exact_readpy)、[`check_delete_intent.py`](#check_delete_intentpy)、[`check_delete_cleanup.py`](#check_delete_cleanuppy)、[`check_repair_backup.py`](#check_repair_backuppy)、[`check_event_page.py`](#check_event_pagepy)、[`check_event_rewrite.py`](#check_event_rewritepy)、[`check_thread_meta.py`](#check_thread_metapy)、[`check_thread_page.py`](#check_thread_pagepy)、[`check_turn_phase.py`](#check_turn_phasepy)、[`check_turn_page.py`](#check_turn_pagepy)、[`check_summary_issue.py`](#check_summary_issuepy)、[`check_recovery.py`](#check_recoverypy)、[`check_session_batch.py`](#check_session_batchpy)、[`check_checkpoint_publish.py`](#check_checkpoint_publishpy)、[`check_entries_cache.py`](#check_entries_cachepy)、[`check_settings.py`](#check_settingspy)、[`check_maintenance.py`](#check_maintenancepy)、[`check_snapshot_store.py`](#check_snapshot_storepy)、[`check_ownership.py`](#check_ownershippy) |
| 连接与浏览器来源 | [`check_browser_source.py`](#check_browser_sourcepy)、[`check_connection_lifecycle.py`](#check_connection_lifecyclepy)、[`check_connection_report.py`](#check_connection_reportpy)、[`check_login_flow.py`](#check_login_flowpy) |
| 关闭与中止 | [`check_shutdown.py`](#check_shutdownpy)、[`check_runtime_capacity.py`](#check_runtime_capacitypy)、[`check_bridge_lifecycle.py`](#check_bridge_lifecyclepy) |
| 搜索 | [`check_search_unicode.py`](#check_search_unicodepy)、[`check_search_clusters.py`](#check_search_clusterspy)、[`check_search_index.py`](#check_search_indexpy)、[`check_search_scan.py`](#check_search_scanpy)、[`check_search_snippet.py`](#check_search_snippetpy) |
| 工作流与文档 | [`check_workflows.py`](#check_workflowspy)、[`check_docs_links.py`](#check_docs_linkspy) |

### `check_versions.py`

`scripts/check_versions.py` 核对版本一致性：npm 根包 / 工作区 / 锁文件、Python 包版本、`CHANGELOG.md` 首条、全部版本条目严格递减与日期合法非递增、使用指南版本行以及 npm 实际发现的工作区列表。同一脚本还核对许可证与包元数据：根包与全部 npm 工作区的 `license` 必须为 `MIT`，`harness/pyproject.toml` 的 `project.license` 为 `MIT` 且 `license-files` 恰为 `["LICENSE"]`，`LICENSE` 以 `MIT License` 开头并包含 MIT 许可正文；根包的 description / private / repository / homepage / bugs / engines.node，全部工作区的 private 与非空 description，以及 Python 的 readme / requires-python / keywords / project.urls / boss-harness 入口 / hatchling 构建与 wheel 包路径也必须保持。`harness/pyproject.toml` 的 Python classifiers 还必须与 `.github/workflows/build.yml` 的 Python 版本矩阵完全一致，PyPI 页面展示的支持版本不会与 CI 实际运行的版本漂移。它需要 Node.js 24+ 与 Python 3.11+；成功时向 stdout 输出 Python 版本，Source build 复用该结果生成资产清单并核对隔离安装。

### `check_release_assets.py`

`scripts/check_release_assets.py` 核对发布资产清单守卫：`release_assets.py` 的清单 schema 版本、保留输出名、提交 / 时间 / SHA-256 格式、wheel 与 sdist 的文件名 / 元数据 / 根目录身份校验、输出目录归属、`O_NOFOLLOW`、inode 一致与重复文件名拒绝必须保留；CI 的 `Source build` 还必须保留清单生成命令与 `sha256sum -c SHA256SUMS.txt`。本检查不构建或发布资产，也不授予发布权限。

### `check_shared_utils.py`

`scripts/check_shared_utils.py` 核对跨包共享工具：`choosePythonInterpreter` 与 `chooseProviderOverride` 对显式变量去空白后非空才采用，否则回退仓库 `.venv` / PATH `python3` 与 `openai`；`parseIsoDateTime` 只接受带秒与时区的完整 ISO 时间，正则外形之后必须按月份天数、闰年与字段范围校验，最后才构造 `Date`；`formatRelativeTime` 从秒逐级取整并在 30 天后回退本机日期；`formatDurationMs` 与内核导出同一口径；`safeSlice` 按 UTF-16 截断但不切开代理对，`codePointLength` 与 Python `len()` 一致；`truncate`、`stripIpcErrorWrapper` 与 `createFocusRelay` 的缓存 / 微任务交付 / 交付后清除固定。检查是源码字面量与首次出现顺序扫描，不执行时间格式化或定位转发。

### `check_duration_parity.py`

`scripts/check_duration_parity.py` 核对会话导出与桌面界面的时长文案：内核 `session_export._duration_text` 必须按 `(ms + 500) // 1000` 取整，`packages/shared/src/index.ts` 的 `formatDurationMs` 必须按 `Math.round(ms / 1000)` 取整；两侧的「不足 1 秒」、秒、分（带剩余秒）、小时（带剩余分）阈值与分支顺序必须一致，四个中文标签必须同时存在；内核导出至少四处调用 `_duration_text`，桌面通知经 `formatDurationMs` 共用同一实现。反向断言两侧不得改用其它取整方式；并直接调用 `_duration_text`（61 项），覆盖 0 / 499 / 500 / 999 / 1000 / 1499 / 1500 毫秒的取整边界、59 秒 / 60 秒 / 61 秒 / 90 秒、59 分 58 秒 / 59 分 59 秒 / 60 分 / 1 小时 / 1 小时 1 分 / 2 小时、小时分支只保留整分、负数与极大值。检查不做跨语言运行比对。

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

### `check_rpc.py`

`scripts/check_rpc.py` 核对 JSON-RPC 帧解析、错误脱敏与响应降级边界：`rpc.py` 的 `MAX_FRAME_BYTES` 8 MiB 与 `MAX_JSON_DEPTH` 64；带文件名的 `OSError` 必须按九种 errno 改写为固定中文原因并附 errno 名称、去掉本机路径，无文件名时保留原消息；JSON 解码必须拒绝重复键、非有限常量与非有限浮点、超过 64 层的嵌套与孤立代理项，并把解码失败统一收敛为 `无效的 JSON 帧`；stdin 必须以 `surrogateescape` 重配置并逐帧 `readline(MAX_FRAME_BYTES + 1)` 有界读取；服务端请求的计时器必须设 `daemon`，启动失败时以 `cancel_request` fail closed；响应写出必须先紧凑编码（`ensure_ascii=False`、`allow_nan=False`）、按 UTF-8 字节数检查帧上限再写出；响应超限与编码失败分别降级为 `-32010` / `RESPONSE_TOO_LARGE` 与 `-32603` / `RESPONSE_INVALID`（请求 ID 本身不安全编码时省略 ID），且不得重跑 handler；未捕获异常必须经 `redact_secrets(describe_failure(exc))` 后返回；所有诊断输出必须写到 stderr。反向断言禁止无钩子解析、`allow_nan=True` 与 stdout 诊断。检查是常量与文本扫描，真实管道读写与并发关闭仍需按平台核对。

### `check_rpc_pending.py`

`scripts/check_rpc_pending.py` 核对服务端发起请求的锁边界与响应降级：`JsonRpcServer.request` 在 `_pending_lock` 内只做关闭检查与 `(future, timer)` 登记，写出在锁外；写出失败必须 `cancel_request` 并重抛，计时器启动失败必须按「客户端请求计时器未能启动」fail closed，计时器是守护线程且先设置后启动。`cancel_request` 锁内只 `pop`，`timer.cancel()` 与 `future.set_exception`（先检查 `done()`）在锁外，未找到时返回 false。`close` 锁内设置关闭标志并复制 id 快照，锁外逐个以「客户端连接已断开」取消。`_receive_response` 只接受字符串 id 且 `result` / `error` 恰好其一，锁内 `pop` 后锁外结束计时器并完成 Future，过期或未知 id 静默忽略。`_respond_too_large` / `_respond_invalid` 在带 id 帧编码失败后回退为无 id 的有界错误，后者再失败直接丢弃；`_dispatch` 对 params 错误、处理错误与成功三类回复都只在有 id 时发出，错误帧与成功帧各自按 `FrameTooLargeError` → `RESPONSE_TOO_LARGE`、其他编码异常 → `RESPONSE_INVALID` 降级，诊断先写 stderr，handler 只运行一次。脚本反向断言锁只加一次、快照先于逐个取消、`ServerRequest` 保持冻结记录。检查是 AST 切片与顺序扫描，不启动线程或管道，运行时并发行为仍需按平台核对。

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

### `check_login_security.py`

`scripts/check_login_security.py` 核对平台登录的官方域名、Cookie 选择与回执形状：`security.ts` 的官方地址必须是 `https:`、无内嵌用户名或密码、端口为空或 443、主机名恰为 `zhipin.com` 或以 `.zhipin.com` 结尾；验证页判定必须失败关闭；扫码就绪先排除非官方与验证页，再要求 `wt2`、`www.zhipin.com` 的根路径或 `/web/{geek,boss,chat}/` 路径与 `__zp_stoken__`，身份按路径前缀映射；登录视图边界要求有限数值、`y ≥ 48`、`width ≥ 100`、`height ≥ 80`，`x + width` / `y + height` 不得超过内容区宽高 + 1，并按 ceil / floor 取整；登录上下文要求 `threadId` 匹配 1–200 位受限字符、`browserId` 至多 100、`visible` 为布尔。`loginCookies.ts` 只接受 `zhipin.com` 与 `www.zhipin.com`，域先去前导点再小写；同名同值只计覆盖，host-only、路径长度、域长度依序决定更具体者，三者完全相同才以固定错误失败，输出使用无原型对象。主进程 `loginAttempt.ts` 与渲染层 `platformLoginState.ts` 必须共享 9 个状态、4 个阶段、3 种身份与 4096 / 120 / 200 上限；attempt id 非空且不超限。`loginFailure.ts` 保留内核原因码，消息经 `stripIpcErrorWrapper` 与 `safeSlice(raw, 200)`。检查是源码片段与顺序扫描，不执行登录或读取真实 Cookie。

### `check_notifications.py`

`scripts/check_notifications.py` 核对桌面通知的内容、去重、保留与点击定位边界：`approvalNotification.ts` 只接受 `approval/requested`，`approvalId` / `threadId` / `itemId` 至多 200、工具名 120、标题 80、正文 240、已提醒集合 200；字段先 trim 且不超限，摘要折叠空白后以 `safeSlice(limit - 1)…` 截断，缺摘要时用固定回退文案，会话与条目 id 必须成对出现；`rememberApproval` 首次返回 `true`，满额淘汰最早一条。`turnNotification.ts` 只接受 `turn/started` 与 `turn/completed`，状态截断 32 字符，开始时间表上限 200 并按插入顺序淘汰；时长必须是有限非负数；结束提醒只接受 `completed`、窗口不在前台且运行不少于 `TURN_NOTIFY_MIN_MS = 20_000`，标题为状态标签、正文为时长，不携带会话内容。`notificationRegistry.ts` 保留上限 32、校验正整数，重复显示重新排到最新，先注册 `close` / `failed` 释放监听再 `show()`。`notificationBadge.ts` 只接受 0–999 的整数。`harness.ts` 的前台守卫、同一审批去重、`Notification.isSupported()`、点击聚焦与审批双 id 定位、徽标空值忽略、测试通知固定文案都必须保留。反向断言通知内容不得出现会话标题、预览或记录参数。检查是源码字面量与首次出现顺序扫描，系统通知的实际展示与点击仍需按平台核对。

### `check_window_state.py`

`scripts/check_window_state.py` 核对窗口状态的解析、恢复与原子保存边界：`windowState.ts` 的最小尺寸 240×160、默认 1440×900、上限 16_384、最小可见 80×40；解析要求 JSON 对象、四个字段都是安全整数、宽高在上下限内，任何一项不合格整体丢弃，`maximized` 只在严格 `true` 时成立；恢复要求至少一块工作区的重叠达到最小可见尺寸，否则回到默认尺寸并交给系统居中；有效状态收敛到重叠面积最大的工作区，宽高不超过工作区，位置钳制在工作区内。保存用 `${path}.${pid}.${时间戳36}.${计数器36}.tmp` 独占创建（`0600` 与 `wx`），`EEXIST` 说明路径被预植文件或链接占用、不得删除，改名失败清理临时文件；`resize` / `move` 后 500 毫秒防抖保存，关闭前补存一次，最大化时用 `getNormalBounds()` 保存还原边界。`index.ts` 从 `userData/window-state.json` 读取、按 `workArea` 恢复并开始跟踪。检查是源码字面量与首次出现顺序扫描，不创建窗口或写盘。

### `check_renderer_recovery.py`

`scripts/check_renderer_recovery.py` 核对渲染层恢复与诊断页：`rendererRecovery.ts` 的自动重载上限 2、滚动窗口 120 秒；六个已知退出原因只经 `hasOwnProperty` 查表，未知原因保留原文或回退「未知原因」；退出码只接受安全整数；恢复参数分别校验安全整数 / 有限正数 / 有限数，历史重载先过滤到 `(now - windowMs, now]`；`clean-exit` 忽略，预算内重载并记录时间戳，超限报告并给出已重载次数。`rendererLoadFailure.ts` 以 `errno: -3` 或 `ERR_ABORTED` 判定被取代的导航，仅当前加载才报告。`rendererFailure.ts` 的诊断页截断 300 字符、修复孤立代理项、转义五个 HTML 实体、使用 `default-src 'none'; style-src 'unsafe-inline'` 的 CSP，并以 `encodeURIComponent` 生成 data URL；不得含脚本或外链。`window.ts` 的失败显示有一次性标记，崩溃决策顺序、`activeLoad` 竞态守卫与初始加载报告固定。检查是源码字面量与首次出现顺序扫描，不启动渲染进程。

### `check_lifecycle.py`

`scripts/check_lifecycle.py` 核对桌面启动接管、单实例与退出确认：`quitConfirmation.ts` 只在运行中回合不少于 1 时返回确认内容，标题、单复数文案、明细、按钮 `["继续运行", "停止并退出"]` 固定，`defaultId` / `cancelId` 都为 0，`noLink` 为 true；`harness.ts` 的 `confirmQuit` 先放行已确认退出，再按 `turnStartedAt.size` 判定是否拦截，`preventDefault` 后同一时刻只开一个确认框；选择「继续运行」恢复主窗口，选择「停止并退出」或确认框无法显示才置确认位并退出；`before-quit` 在确认后清理登录、自检与 Host。`profile.ts` 只在新目录为空壳时删除并改名接管旧目录，旧目录非空、删除失败或改名失败都保留新目录，且不递归删除或复制。`index.ts` 先设置应用名并接管旧目录，再注册窗口工厂与单实例锁。检查是源码字面量与首次出现顺序扫描，不弹确认框、不改用户目录。

### `check_client_transport.py`

`scripts/check_client_transport.py` 核对 Node 侧进程传输客户端：`packages/app-client/src/index.ts` 必须以 `shell: false` 与三条 pipe 启动内核，单帧上限 8 MiB、输入队列上限 16 MiB，请求超时默认 30 秒且提示结果未知、不自动重试，超时后移除尚未写出的帧；计时器必须 `unref()`；输出按 LF 分帧、以 `fatal: true` 严格解码 UTF-8，坏帧只记录固定诊断，超限帧触发失败并 `dispose`。回包必须恰好带 `result` 或 `error` 之一，非法回包与非法错误帧都以 `-32603` 结算；服务器请求必须校验 id、忽略重复 id、超过 256 条待答即失败，无监听者返回 `-32601`，处理器异常返回 `-32603`；失败路径清空待答、待答服务器请求、输出队列与缓冲并发出 `harness/disconnected`。关闭流程必须先 `stdin.end()`，2.5 秒后 `SIGTERM`，再 1 秒后 `SIGKILL`。反向断言禁止 `shell: true`、继承 stdio、`console.*` 与诊断夹带帧内容。

### `check_host_connection.py`

`scripts/check_host_connection.py` 核对 Node 宿主的连接代际、重连预算与审批路由：`host.ts` 的连接状态集合与 `willRetry` 公式；`ensureReady` 共享同一次初始化、递增代际、断开必须先确认传输层已失败、初始化回执必须带服务器名与协议版本、成功后发送 `initialized` 并进入 `ready`；`approval/respond` 的裁决必须是布尔值、审批路由必须属于当前代际、持久审批成功后释放客户端待答槽位、v0.1 内核保留兼容分支；`reconnect` 重置恢复预算并清理审批，`dispose` 后不再重连；断开事件固定携带 `outcome: unknown` 与 `automaticReplay: false`。自动重连受 `supportsReconnect`、次数上限与退避封顶约束，计时器 `unref()`。审批请求只接受 `item/tool/requestApproval`，字段缺失或重复 id 返回 `-32602`，期限默认 300 秒，损坏期限回退初始化回执、过去时间以 `-32001` 过期，计时上限 2,147,483,647 毫秒；回合终态、条目完成、工具调用完成与已裁决通知四条路径撤销审批路由。反向断言禁止 `String(params.status)` 宽松归一化、自动重放与跳过审批清理。

### `check_harness_tools.py`

`scripts/check_harness_tools.py` 用标准库 AST 解析 `harness/src/boss_harness/tools/boss_cli.py` 的 `TOOLS` 元组：工具名必须恰为 14 个已登记名称且不重复，其中 13 个只读，仅 `boss_hr_greet` 标记 `requires_approval: True`；每个工具必须带非空描述与 handler，`input_schema` 必须为 `type: object`、`additionalProperties: false`，`required` 只能包含已声明属性且不得重复。它还解析 `context.py` 的 `_WRITE_TOOLS`、`write_tools` 默认值与 `tool_results.py` 的 `LEGACY_WRITE_TOOLS`，要求三处写工具集合均恰为 `boss_hr_greet`。它同时核对 `tools/bundle.py` 保留 `handlers = tool_handlers()`、`approval_required = approval_required_tools()` 与 `for spec in TOOLS`，并要求 `name` / `description` / `input_schema` / `requires_approval` 从 spec 透传，组合层不得把审批标记改写为固定值。工具桥 `tools/boss_cli.py` 的 `Popen` 必须显式 `shell=False`，`BOSS_CLI_DATA_DIR` 必须去除首尾空白且把空值视为未设置，禁止把未规范化的值原样传给上游；`BOSS_CLI_BIN` 同样去除首尾空白并把空值视为未设置，禁止用未规范化的路径直接查找；`harness/src/boss_harness` 下任何 Python 文件出现 `shell=True`、`create_subprocess_shell(`、`os.system(` 或 `os.popen(` 都会失败。工具桥的输出上限固定为 `MAX_CLI_OUTPUT_BYTES = 16 * 1024 * 1024`，`BoundedProcessOutput` 必须接收该上限，`CLI_OUTPUT_LIMIT` 的失败说明必须保留「不要自动重试」；`process_io.py` 必须保留 64 KiB 分块、累计字节与上限比较、溢出标记、`BrokenPipeError` 处理与按 stdout / stderr / 可选 stdin 的收尾计数。检查读取源码字面量，不导入内核、不依赖已安装包；运行时生成的工具或动态 schema 仍需人工核对。

### `check_process_io.py`

`scripts/check_process_io.py` 核对子进程输出捕获 `BoundedProcessOutput`：分块上限 64 KiB，读取循环在共享字节上限处双重检查并停止，按块累计与拼接；任一操作抛异常置 `failed`，三条线程（stdout / stderr / 可选 stdin）结束时递减 `_remaining` 并在归零时置 `done`；stdin 按 UTF-8 写入、冲刷并关闭，`BrokenPipeError` 被容忍；`join` 只做有界等待并返回是否全部停止，`alive` 只统计已启动且存活的线程，`close_unstarted` 只关闭未启动线程对应的管道。行为侧用本地 Python 子进程与自定义流覆盖 stdout / stderr 聚合、stdin 往返、跨块与单块溢出、读取异常置失败、断管容忍、超时后仍存活并在释放后收尾、未启动管道的关闭。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用本地子进程与内存流，不访问网络、模型或招聘平台。

### `check_tool_schema.py`

`scripts/check_tool_schema.py` 核对工具参数边界：`tool_schema.py` 的关键字与类型集合、schema / 参数字节上限、JSON 节点 / 深度上限与规范化访问上限保持不变；根 schema 必须为对象，结构化字符串仅在按对应对象 / 数组 schema 解码且校验通过后才替换原值，参数校验失败统一转为受限错误。`tool_bundle.py` 必须保留工具名格式、描述非空、执行模式与审批互斥、结果预算范围、schema 冻结、注册表名校验与只读投影。检查同时直接调用 `canonical_schema` 与 `validated_arguments` 做行为对照（87 项）：根必须是 Mapping 且规范化为对象、未知关键字与非法规则整体拒绝、规范化输出的键序与非 ASCII 保留、Mapping 子类、类型精确匹配（布尔不是整数 / 数值）、required 与 additionalProperties、字符串长度与 `re.search` 正则语义、anyOf、数组长度与 `uniqueItems` 的数值等价、结构化字符串仅按 schema 选中的对象 / 数组解码且失败保留原文、不可传递字符单独点名，以及非对象 / 循环 / 超深 / NaN / 元组 / 字节 / 非字符串键 / 非法 schema JSON 的拒绝与返回独立副本。

### `check_tool_arguments.py`

`scripts/check_tool_arguments.py` 核对工具参数里的空字符与未启动结算：`tool_schema.py` 必须在参数快照阶段拒绝含 `\u0000` 的字符串与对象键（孤立代理项同样拒绝），使需批准的工具在审批之前就返回参数错误；这类错误必须点名「无法作为命令行参数传递的字符」，与其他 schema 不符的通用文案分开，模型才能据此删掉字符重试；`tools/boss_cli.py` 在 `Popen` 因参数无法编码或含空字符而抛 `ValueError` 时返回独立的 `CLI_ARGUMENT_ERROR`，不得与「可执行文件缺失」共用错误码；`agent.py` 必须把该错误码结算为 `not_executed` 并暂停回合，同时不进入「已派发、结果不确定」集合。脚本还会构造真实注册表与执行器跑一遍：空字符参数被拒绝并点名原因、普通 schema 不符保持通用文案、正常参数放行、`CLI_ARGUMENT_ERROR` 收尾为 `not_executed` 且暂停、`TOOL_ERROR` 仍收尾为 `outcome_unknown`。临时会话目录在隔离环境创建，检查不调用模型、招聘平台或真实 CLI 二进制。

### `check_model_tools.py`

`scripts/check_model_tools.py` 固定模型可见的结果读取工具：`model_tools.py` 的 `read_session_tool_result` 模式只接受 `itemId`（1–128 字符）、`sha256`（64 位小写十六进制）两个必需字段，以及有界 `cursor`（至多 2,048 字符）与 `limit`（引用 `MODEL_RESULT_READ_CHARS`），禁止额外字段；读取流程必须依次完成参数校验、按 thread 与 item 查找会话记录、缺失拒绝、只允许 `toolCall` 条目、规范化结果正文、按 `sha256` 与游标返回有界分段，整份载荷上限固定为 64 KiB，禁止把完整条目或全文直接回灌模型；错误映射必须按 `ItemLookupError`、`RpcError`、`ValueError` 的顺序收敛为固定码，`RpcError` 的 `currentRef` 必须透传，名称冲突守卫必须拒绝与内核工具同名的自定义工具。检查是文本扫描，运行时读取行为仍需按用户指南核对。

### `check_domain_tools.py`

`scripts/check_domain_tools.py` 固定离线指令与默认领域提示：`tools/commands.py` 的只读指令表必须恰为 `/tools`、`/status`、`/stats`、`/recommend`、`/jobs`、`/chat`、`/candidates` 七项并指向对应工具与标题，`/search` 必须保留独立分支、先拒绝空参数再调用 `boss_search`，`/candidates` 仅在有关键词时携带 `query`，业务 CLI 缺席与未配置模型两种降级文案保持不变；反向断言禁止把 `/search` 做成表项、禁止指令表包含写工具或默认关键词。`tools/recruitment.py` 必须保留默认身份、`SYSTEM_PROMPT` 组合、14 个领域工具说明中的关键条目，以及审批门禁、不自动重试与分页如实说明等规则；`compose_system_prompt` 只替换身份并保留全部领域规则，身份文本必须非空、按 UTF-8 字节不超过 16 KiB 且拒绝控制字符。检查是文本扫描，运行时提示效果仍需人工核对。

### `check_tool_results.py`

`scripts/check_tool_results.py` 核对工具结果分页与引用边界：`tool_results.py` 的内联 64 KiB / 单页 1 MiB 预算、默认 16,384 / 最大 32,768 码点与模型 8,192 码点必须保持不变，且满足 `MODEL_RESULT_READ_CHARS ≤ DEFAULT_RESULT_CHARS ≤ MAX_RESULT_CHARS`、单页预算低于内核帧上限；两条读取路径必须校验 `limit`，RPC 请求字段必须限定在 `threadId` / `itemId` / `sha256` / `cursor` / `limit`，摘要必须为 64 位小写十六进制，过期引用必须返回 `STALE_RESULT` 与 `currentRef`，游标必须校验前缀 `tr1_`、长度、条目归属与偏移。模型只读工具必须使用 `MODEL_RESULT_READ_CHARS` 上限、禁止额外属性，并透传当前引用与错误码。检查同时直接调用 `tool_execution_state`、`tool_disposition`、`disposition_for_state`、`result_text`、`result_reference`、`canonical_result_text`、`wire_size` 与 `project_item` 做行为对照（28 项）：九个执行状态原样返回、非法值丢弃，处置只保留两个合法字段，状态→处置矩阵区分 failed 的写读差异，结果按紧凑 JSON 与非 ASCII 拼写且拒绝 NaN，引用按 UTF-8 字节（surrogatepass）计算 SHA-256 与字节 / 码点双长度，规范化把孤立代理项降级为 U+FFFD、非有限浮点降级为 null，wire 预算加 512 字节帧余量且代理项按超限处理，内联上限恰好 64 KiB 保留、超出后省略结果并生成引用、截断固定字段且不修改输入。

另有 32 项分页行为检查直接调用 `read_result_chunk` 和 `read_result_text_chunk`。两条入口可交替使用游标续读，分段偏移按 Unicode 码点推进，孤立代理项按规范化结果读取，末页没有续页游标。检查还核对每条入口的 `limit` 边界、过期摘要返回的 `currentRef`、游标绑定的会话 / 条目 / 摘要以及偏移的类型和范围，并覆盖条目入口的摘要格式和结果类型校验。

### `check_tool_revision.py`

`scripts/check_tool_revision.py` 核对工具结果修订的恢复口径：`SessionStore.append_tool_revision` 只接受 `item` / `toolCall` / 字符串 `revises` 的条目；首次追加与 `append` 一样在写前、写后各刷新一次索引并返回 `(entry, False)`。首次失败后重新逐行解码日志：同 id 且内容一致才可复用，内容不同为 `conflict`，解码失败为 `invalid`，已存在且 `r+b` 打开后 `fsync` 成功为 `durable`，`fsync` 失败为 `present_uncertain`，未找到为 `absent`。`durable` 刷新索引后返回 `(entry, True)`；`conflict` / `present_uncertain` 直接抛 `ToolRevisionPersistenceError`；`absent` 只允许在首轮重试追加一次，之后一律按持久化错误抛出。异常路径会再核对一次，二次核对失败标记 `uncertain`，并把最后一次错误附在最终异常上。脚本反向断言恢复路径不引用 handler 或审批、追加机会恰为两次、`except ToolRevisionPersistenceError` 必须重新抛出、`ToolRevisionPersistenceError` 保持 `OSError` 语义。结构检查使用 AST 切片与顺序扫描。

脚本还在临时会话中运行 10 个离线恢复场景。首写成功、写前失败后重试、首次或重试写入后才报错时，核对返回条目、恢复标记、追加次数和日志条目。另在首次或重试追加后注入同 ID 内容冲突和损坏行，并模拟同步已有条目失败、连续两次追加失败，核对失败分类和最后一次错误。

### `check_toolkit.py`

`scripts/check_toolkit.py` 核对工具结果信封的校验、深拷贝与错误收敛边界：`toolkit.py` 的 `ToolResult` 必须保留 `ok` / `command` / `data` / `error` / `hints` / `raw` / `pagination` 七个字段及默认值；`snapshot_result` 只接受 `None`、`str`、`bool`、`int`、有限 `float`、键为字符串的 `dict` 与 `list`，嵌套最多 64 层；信封校验必须要求 `ok` 为布尔、`command` 非空、`raw` 为字符串、三个可选字段为 `dict` 或 `None`，错误信封的 `code` 非空且 `message` 为字符串；`recovery_action` 为 null 时按字段缺失规范化（下游按 `or ""` 读取，合法平台错误不会被替换为 `TOOL_ERROR`），其他非字符串值拒绝；信封必须显式构造并在 `ensure_ascii=False` 下经 JSON 往返深拷贝，任何异常统一收敛为同一个 `ValueError`。脚本反向断言不得整份展开宿主返回值、不得使用 `ensure_ascii=True`，并核对技术参考的深度与 `raw` 说明。

27 项离线行为检查直接调用 `snapshot_result`。检查修改宿主的嵌套数据、错误、提示和分页字段后，确认快照保留原内容及 Unicode。另核对信封的深度 64 和 65 边界，恢复动作缺省、null 与字符串的处理，以及循环引用、非有限浮点、非字符串键和非法信封字段的异常类型与提示。

### `check_item_content.py`

`scripts/check_item_content.py` 核对条目正文的传输降级与分页边界：`item_content.py` 必须保留 64 KiB 内联阈值、默认 16 384 / 最大 32 768 码点、64 层投影深度与占位文本；孤立代理项必须替换为 U+FFFD、非有限浮点降级为 `None`，内联正文必须先经 `wire_text`；内容摘要必须按 `wire_text` 后的文本分块计算，超过内联阈值时写入 `textOmitted` / `thinkingOmitted` 与内容引用；读取必须校验 `limit`、64 位摘要、32 位 `snapshotId`、`ic1_` 前缀与 2048 字符上限、线程 / 条目 / 字段 / 摘要 / 快照的归属与 offset 范围，过期引用返回带 `currentRef` 的 `STALE_CONTENT`。脚本同时核对桌面指南的大正文恢复说明。行为侧直接调用内核函数：覆盖代理项替换与长度不变、递归清理与键替换、深度与 `inf` / `nan` 占位、引用字段与分块摘要一致、内联清理与旧引用清除、超长省略、分页往返与末页、`limit` 边界、摘要 / 快照格式、过期引用错误码、游标跨线程 / 条目 / 字段 / 摘要与格式拒绝（77 项）。实际降级、分页与渲染行为仍需按桌面指南核对。

### `check_approval.py`

`scripts/check_approval.py` 核对审批裁决边界：`application.py` 的请求必须只有 `approvalId` 与有界 `approved`，遍历活动 runner 时调用持久回调，并将服务端请求取消与恢复 / 执行中回执分开；`agent.py` 只在未裁决、未取消且未过期时接受决定，并在回合清理时丢弃待决集合；`session.py` 必须校验审批 id 格式、索引唯一性、归档与 owner 状态、重复冲突和到期判定。脚本是源码扫描，不执行工具或验证真实用户裁决。

### `check_approval_item.py`

`scripts/check_approval_item.py` 核对审批条目的展示、归属与状态校验口径：`_valid_approval_item` 只接受 `toolCall` 条目与对象形态的 `approval`，`decision` 只能是 `approve` / `deny` / `expired`，`approvalId` 必须是 32 位小写十六进制事件 id，`turnId` 必须符合标识符格式；展示用工具名与条目 id 去空白后非空且不超过 200 字符，两者必须与条目字段一致，`toolArguments` 必须与 `approval.params` 完全相等；`status` / `executionState` 随 `decision` 收紧（待决为 `running` + `pending_approval`，批准、拒绝与过期各有终态集合），截止时间必须是有限正数，描述不超过 1000 字符，`paramsDigest` 必须与参数摘要一致。脚本按源码顺序固定这些边界，用反向断言要求九处拒绝分支、两处 200 字符上限、参数与摘要各只比对一次、使用精确 `dict` 类型判断、截止时间严格大于零，并要求全部五处调用点以关键字传入 `pending_only`。脚本并构造条目直接调用校验函数（92 项），覆盖展示字段去空白与 200 字符边界、工具名一致性、`approvalId` 的 32 位小写十六进制、`turnId` 标识符、精确 `dict` 参数与 `params` 一致性、`pending_only` 强制、`approve` / `deny` / `expired` 三组状态组合、`deadline` 的类型 / 有限性 / 正值、描述 1000 字符上限与参数摘要不匹配。检查不执行裁决或启动模型。

### `check_approval_digest.py`

`scripts/check_approval_digest.py` 核对审批参数摘要的规范化、负载一致与索引往返：`approval_parameters_digest` 必须用精确 `dict` 类型判断，以 `sort_keys=True`、`ensure_ascii=False`、紧凑分隔符与 `allow_nan=False` 规范化，UTF-8 编码后取 SHA-256 十六进制摘要，序列化失败（含递归过深）统一收敛为固定错误；`agent.py` 的 `_prepare_tool` 审批负载必须恰好包含 `approvalId` / `toolName` / `description` / `params` / `paramsDigest` / `consequential` / `deadline` 七个字段，`params` 与摘要都直接引用同名 `arguments`，描述不回显参数，`start_tool_call` 把同一份参数写入条目；`session.py` 的 `_index_thread` 直接持久化必填摘要并把截止时间转为数值，`pending_approvals` 从 `params_digest` 列回读。脚本用 AST 核对负载键集合与摘要调用参数，反向断言禁止第二份摘要实现、宽松类型判断、可选摘要读取与参数拷贝；并直接调用 `approval_parameters_digest`（72 项），覆盖空对象、键序稳定、嵌套键序、紧凑分隔符、非 ASCII 不转义与键排序、数字键转字符串、布尔 / 空值 / 浮点 / 大整数 / 元组转数组、不同参数不同摘要与 64 位小写十六进制，以及 list / None / 字符串 / dict 子类、NaN / Infinity / 不可序列化值 / 字节值 / 混合键 / 循环引用 / 超深嵌套 / 嵌套 NaN 的固定错误收敛。检查不启动审批流程或持久化。

### `check_pending_approvals.py`

`scripts/check_pending_approvals.py` 核对待审批分页与计数的共享过滤口径：`_pending_approvals_where` 必须在删除占位超过 800 时整次放弃读取，连接会话与回合表，只取未裁决、`running` + `pending_approval`、未归档且回合为 `running` / `interrupted` 的审批；七个 `typeof` 类型守卫、六个非空守卫与 `deadline BETWEEN 0 AND 1e15` 必须完整，当前时间与会话 / 删除 id 全部走参数绑定，删除会话用占位符 `NOT IN` 过滤。`pending_approvals` 的条目上限为 200，按会话更新时间、会话 id 与条目 id 倒序排列，多取一行得出 `truncated`，并按上限切片；损坏的 `deadline` 或非字符串 / 空字段按缺失跳过。`pending_approval_counts` 共用同一条件并按会话分组，不得出现 `LIMIT` 或条目上限校验，返回字符串键与整数计数。脚本用反向断言要求两处读取共用条件、删除过滤逐个绑定、列表摘要只回显工具名。检查是源码扫描，不执行 SQL 或审批读取。

### `check_approval_remember.py`

`scripts/check_approval_remember.py` 核对桌面端审批高风险标记的失败关闭：`approvalConsequential` 只把明确的布尔 `false` 当作可记住，缺省、`null`、数字与字符串一律按必须逐次确认；实时 `approval/requested` 归并、快照与通知恢复的 `toApproval`、受理后写入「本次会话记住选择」与 `autoApprovalTarget` 都经过这一判定；自动批准还要求通知方法、记住集合、非空字符串的审批标识与工具名，并排在其他回合事件过滤之后。反向断言标记名在桥接、事件归并、应用层与对话区的出现次数固定（含解构与类型判断写法），应用层只有手动裁决与自动批准两处提交，记住集合只在受理后的一处写入。检查是源码字面量扫描，不执行审批，也不替代 Electron 窗口中的目视核对。

### `check_loop_guard.py`

`loop_guard.py` 只在单次 `TurnRunner.run()` 内观察已执行工具调用：工具名与规范化参数的 SHA-256 摘要一致时累计，命中第 3、5 次后向模型追加一条合成 `UserMessage` 提醒。该提醒不阻断工具执行、不含参数或结果、不写入会话条目、不跨回合保留；用户 steering 注入或不可安全观察时立即重置。两个 provider 都把工具结果后的用户消息按既有顺序序列化，无需新增协议字段。

`scripts/check_loop_guard.py` 固定重复调用提醒的阈值 `(3, 5)`、512 字符上限与 64 KiB 规范化参数上限；`_argument_digest` 必须规范化排序、禁用 NaN、不可安全序列化时回退，`observe` 只按工具名与参数摘要计数，提醒不含参数或结果。脚本还核对 `agent.py` 在工具结果之后、仍有下一次模型请求时观察，且 steering / 无调用后续消息路径会重置。行为侧直接构造 `LoopGuard`：覆盖第 3、5 次提醒与其余次数静默、参数与工具名变化重置计数、键序与嵌套顺序归一、`reset` 清空、NaN / 混合键 / 循环引用与超长参数放弃观察并清空旧计数、提醒不含参数、工具名截断 64 字符与上限、实例隔离。它不执行模型、不写入会话，也不验证模型是否真的响应提醒。

### `check_queue_steer.py`

`scripts/check_queue_steer.py` 为 `queue/steer` 提供专项源码守卫：内核侧核对 `promote_to_steering` 只接受 `queued` 的 `followUp`、拒绝技能 / 自动压缩覆盖，并通过持久 `_save` 保留原 id、正文与请求编号；`on_queue_steer` 必须校验 active turn、`expectedTurnId`、取消状态与 `STEER_UNAVAILABLE`。脚本还核对 `queueSteer` 能力、协议参数类型、主进程两份白名单与方法参数校验、RPC 错误保留、渲染层 bridge 与面板按钮状态。它是 AST 与文本扫描，不替代状态机探针或真实桌面操作。

### `check_turn_stream.py`

`scripts/check_turn_stream.py` 核对回合循环与流式终态：`agent.py` 的 13 个通知名、`MAX_TOOL_ROUNDS` 与 300 秒审批默认值；请求偏移必须是非负整数且不超过请求上限，恢复预算与循环守卫在回合级创建；工具批次上限必须先于续接签名与长度截断处理，截断或续接失败都不得执行本批工具，`MODEL_OUTPUT_TRUNCATED` / `PROVIDER_CONTINUATION_TOO_LARGE` / `TOOL_BATCH_LIMIT` / `CONTEXT_BUDGET_EXCEEDED` 保持固定码；并行批次不可用时回退串行，取消时仅整批执行完成后才记完成。`_stream_round` 的 `retry_start` 只做观测、`retry_end` 与已发起点成对且早于回合终态，文本 / 思考增量计入输出预算，文本 / 思考 / 工具调用增量都记为已观测产出（工具参数预算在 provider 层），`done` 事件对最终文本复核预算；`CONTEXT_OVERFLOW` 恢复资格要求无中断、无产出与无助手消息，用量条目在中断、错误与 `aborted` / `error` 终态下标记不合格；条目终态在中断 / 错误 / 截断时为 `failed`。源码侧固定片段与首次出现顺序，`model_result` 默认沿用 `DEFAULT_MODEL_TOOL_RESULT_BYTES`。反向断言禁止中断时标成完成、`redact_secrets(str(exc))` 与未定义恢复标记。检查还直接调用 `summarize_result` 与 `tool_source` 做行为对照（10 项）：成功结果的命令、正文与分页元数据顺序，非 ASCII 原样输出，不可序列化数据降级为文本，成功与失败路径都受 `limit` 截断，失败缺省为 `UNKNOWN`，错误码 / 消息 / 恢复建议按序拼接并经凭据脱敏，来源引用固定为 `tool:<会话>:<条目>` 并带查询时间。检查仍不执行完整回合，不替代真实模型与桌面验收。

### `check_queue_state.py`

`scripts/check_queue_state.py` 核对 `TurnQueue` 的新增、编辑、状态转移与暂停结算口径：`_pending_usage` 只统计 `queued` / `delivering` 并按 UTF-8 字节求和；`add` 校验 kind、1–100000 字符正文、1–128 位客户端消息 id、最多 10 项非空技能并先去重，转向消息不得携带技能，同一客户端 id 只接受完全相同的输入、类型、技能与自动压缩覆盖，条目上限用 `>=`、字节上限用 `>`，超限返回 `QUEUE_LIMIT`，新记录固定为 `queued` 并保留 `expectedTurnId`。`update_input` 只编辑 `queued` 项，按替换后的字节重算上限且只改正文。`transition` 的转移表固定为 `queued → delivering / delivered / paused / cancelled`、`delivering → delivered / paused`、`paused → cancelled`。`claim` 只领取 `queued`，steering 还要求字符串 `expectedTurnId` 与当前回合相等。`pause` 保留已有的具体来源；`settle_pauses` 让 kind 来源优先于无作用域兜底，只处理排队 / 投递中项，有原因才写 `pausedReason`，一次 `append_many` 写回后清理作用域并返回实际暂停的 id。源码侧固定片段与顺序。检查还在临时会话存储上直接调用 `TurnQueue` 做行为对照（29 项）：技能去重保序、空白正文与非法 kind / 技能上限被拒绝、同输入幂等与不同输入冲突、转向消息拒绝技能、编辑只改正文且投递中不可编辑、转移表与已投递 / 暂停项不可回退、steering 领取要求回合匹配且重复领取为空、followUp 领取忽略回合、按 kind 与无来源暂停的范围和原因保留、作用域清理后新项不受影响，以及 129 个待处理项触发 `QUEUE_LIMIT`、暂停项不占容量。

### `check_catchup_boundary.py`

`scripts/check_catchup_boundary.py` 核对摘要后补领转向的提交批次、最终请求指纹与续接拒绝条件；它是 AST 与文本扫描，不替代真实模型或桌面操作。

### `check_request_identity.py`

`scripts/check_request_identity.py` 核对请求身份的校验、去重与冲突边界：`request_identity.py` 的 `clientUserMessageId` 必须整串匹配 `[A-Za-z0-9_-]{1,128}`，无效格式直接拒绝；持久记录的 `queueId` / `turnId` 链接必须经类型校验后参与两轮收敛，队列记录必须与 `queue/list` 共用 `queue_record` 契约；转向类型冲突、不同输入与身份歧义必须分别以 `CLIENT_REQUEST_CONFLICT`、`CLIENT_REQUEST_AMBIGUOUS`、`REQUEST_REQUIRES_REVIEW` 拒绝；输入摘要按 UTF-8 原文计算，持久事实不一致或「未启动却已完成」的回合必须要求核对。脚本同时核对技术参考与使用指南的请求身份说明。检查是常量与文本扫描，实际去重与恢复行为仍需按用户指南核对。

### `check_queue_view.py`

`scripts/check_queue_view.py` 核对队列读取投影的上限与截断边界：`queue_view.py` 的待处理项上限 200、已终结窗口 50、正文预览 600 字符、可选字符串与队列 id 上限 200、技能 10 项，以及 `_QUEUE_VIEW_FIELDS` 白名单必须逐字段声明（禁止把持久记录整份透传）；`queue_record` 必须校验 `kind` / `status` / `id` 并把编码失败降级到 `wire_value`，仍不可编码时按坏记录跳过；`queue_view_record` 只删除类型不符的可选字段，暂停来源必须是内核枚举，`executionStarted` 只接受 `False`；`project_queue` 必须先保留暂停项再用剩余名额容纳排队 / 投递中项，正文截断时标注 `inputTruncated`，分类计数在调用方传入时不得改由有界子集重算。脚本同时核对技术参考与使用指南的队列读取说明。检查另用临时合成记录执行 `queue_record`、`queue_view_record` 与 `project_queue`：合法与坏记录、id 与可选字符串上限、代理项降级、NaN 跳过、白名单、技能去重与上限、自动压缩清理、暂停来源与执行标志收敛，以及输入截断、暂停优先、终结窗口、坏记录跳过与显式计数；桌面渲染仍按用户指南核对。

### `check_queue_counts.py`

`scripts/check_queue_counts.py` 核对队列计数与列表元数据口径：`_queue_status_counts` 只读取 `queue` 条目，经 `queue_record` 过滤后按 id 覆盖为最新状态，计数键恰好是 `queued` / `delivering` / `paused`，只统计 `ACTIVE_QUEUE_STATUSES` 并按状态累加；`_index_thread` 必须由三项求和得到 `queueActiveItems`，非零时写入 `queueCounts`、为零时清除旧字段。反向断言：不得使用 `setdefault` 保留首个状态；损坏记录必须跳过；求和与清除各只出现一次。检查同时直接调用 `SessionStore._queue_status_counts` 做行为对照（42 项）：空列表与非队列条目、三个活动状态计数、终止状态不计、不同 id 累加、同 id 最新状态覆盖（活动到终止、终止到活动、三次记录）、损坏记录（payload 非对象 / 缺或未知 kind / 缺或未知 status / 非字符串、空或超长 id / input 非字符串 / NaN 字段）跳过且不覆盖有效状态、额外字段不影响、返回键恰好三个与输入不被修改。

### `check_task_ownership.py`

`scripts/check_task_ownership.py` 核对任务读取的归属判定与恢复策略：`task_ownership.py` 的标识符必须整串匹配 `[A-Za-z0-9][A-Za-z0-9_-]{0,127}`，回合与队列快照默认最多 257 项，任务阶段只接受 `admission` / `prepare` / `model_request` / `tool_execution` / `finish` 与终态枚举，`attempt` / `restartLimit` 必须在 1–1 000 与 0–32 内，恢复原因限定 `processExit` / `terminalStateRecovered`、恢复策略限定 `manual` / `closed` 且只在 `finish` 阶段按终态采纳；同一队列记录的身份字段（`kind` / `inputDigest` / `expectedTurnId` / `clientUserMessageId`）在多份快照间变化必须判为冲突；`delivered_as` 需要队列回执、回合记录与用户消息引用三者一致，`targets` 需要 `expectedTurnId` 指向已知回合且投递状态有对应引用，多链接、重复回合或回执不一致一律 conflict；摘要关系只在 `threadId`、checkpoint 与唯一回合一致时 resolved，无归属时区分 `independent` 与 unresolved；`recovery_policy` 对缺失、未知或损坏状态必须优先返回 `manual_review`，进程持有返回 `process_owned`，队列排队返回 `queue_pending`。脚本反向断言标识符不得改用 `search`、用户消息引用不得投影正文，并核对技术参考与使用指南的任务读取说明。检查另用临时合成记录执行 `recovery_policy`、`resolve_compaction_relation`、`resolve_queue_relation`、`turn_snapshot`、`queue_snapshot` 与 `user_message_refs`：unknown 优先、进程持有、排队 / 投递 / 终态、独立 / 冲突 / unresolved / resolved、delivered_as / targets、重复与身份冲突、阶段绑定、超限溢出与不投影正文；真实持久记录分布仍按用户指南核对。

### `check_model_disable.py`

`scripts/check_model_disable.py` 核对显式 `none`（`--provider none` 或 `BOSS_HARNESS_PROVIDER=none`）禁用模型调用的进程级边界：`ApplicationService` 的构造校验、模型目录发现门禁、`_configured_route` 的拒绝提示、`_provider_for` 对真实线路的最后拦截、`_summary_available` 的显式禁用与独立 Anthropic 环境凭据判定（不重新解析配置或创建供应商）、摘要线路解析门禁、分支摘要与续接预检的拒绝提示，以及入口 `_requested_provider` 与启动自检 `MODEL_DISABLED` / `MODEL_NOT_CONFIGURED` 的措辞；自动回退提示只在本机 OpenAI 线路按同一套解析（含命令行 `--model`）可读通且 `openai` 包可发现时点名该线路，解析失败保持通用建议，缺包时改为安装提示。它还核对结构边界：`provider_factory` 在 `application.py` 只经 `_provider_for` 调用、在 `connections.py` 只经 `_run` 调用，`build_provider` 只允许入口调用，`AnthropicProvider` / `OpenAIResponsesProvider` 只允许在 `models/provider.py` 构造，`ApplicationService` 在构造连接检查时传入进程级开关，`ConnectionChecks` 仅对 `none` 默认线路接受启用该开关，并给显式禁用的模型卡片标注 `MODEL_DISABLED`。模型卡片为 `disabled` 时在启动检查线程前直接返回报告。脚本同时核对模型值的回退。启动和自检的回退提示都把 `--model` 交给 `resolve_config`，只在去除首尾空白后仍非空时覆盖通用模型变量。两条线路都经 `_configured_model` 从环境中取第一个去除首尾空白后仍非空的值；自动线路判断、模型目录发现、摘要线路解析与自检共用 `has_anthropic_credential`：只有两项凭据都去除首尾空白后仍为空才视为未配置，`application.py` 不得直接读取凭据变量。脚本还核对 Anthropic 凭据的交付方式：环境里的两项凭据先去除首尾空白，只有非空值才显式传给 SDK，纯空白 `ANTHROPIC_API_KEY` 不遮蔽真实 `ANTHROPIC_AUTH_TOKEN`；让 SDK 直接读取未处理环境变量的裸构造会被拒绝。这些进程级限制由结构检查覆盖。嵌入方自带的 `provider_factory` 仍受 `_provider_for` 的结构拦截约束。

5 个离线场景执行 `--check` 命令入口，核对命令行与环境变量的 `none`、未指定时的自动回退、退出码和报告诊断。显式禁用时验证不探测备用 OpenAI 线路。自动回退时使用合成配置核对 `--model` 的传递，以及备用线路不可解析、缺少 SDK、已配置并可发现 SDK 三种提示。

### `check_request_policy.py`

`scripts/check_request_policy.py` 核对模型请求策略的拒绝投影与脱敏边界：拒绝载荷必须只保留 purpose / provider / model / requestIndex / threadId / turnId / jobId，并把 `errorInfo.source` 记为 `request_policy`，同时带 `requestRejected: true`、`outputObserved: false` 与 `contextRecoveryEligible: false`；历史单元预览必须把用户文本截到 1 000 字符并脱敏、工具名最多 64 个；转换必须按整单元丢弃、取消优先；`check_model_request` 必须先把任务身份写入最终请求，并在 hook 允许后才放行；两条拒绝路径都必须先经 `redact_secrets` 再抛出；`model_error` 记录必须按 `recorded` 只写一次。脚本同时核对技术参考中的策略拒绝与取消优先级说明。行为侧直接调用策略函数：覆盖 `history_units` 的空输入、无用户消息与中途用户消息切分，`_unit_view` 的截断、脱敏与工具名上限，`transform_request_context` 的单元不足、无结果、空丢弃、取消优先、丢弃单元与拒绝脱敏，`check_model_request` 的归属重写、取消短路、回合专属变换、拒绝上下文与省略规则，`ModelRequestRejected` 的载荷白名单，以及 `record_model_rejection` 的单次记录与幂等。实际 hook 行为仍需按技术参考核对。

### `check_usage.py`

`scripts/check_usage.py` 核对 provider 用量汇总的校验、来源与缓存估算边界：`usage.py` 的单次请求上限 50 000 000、四个 token 字段与两个线路的 `_REPORTED` 能力表（OpenAI 缓存 input 是子集、Anthropic 缓存读写独立计数）、七类未验证原因（`unknownProvider` / `missing` / `invalidType` / `negative` / `outOfRange` / `inconsistent` / `zero`）与 `unreportedRequests` 只来自 `missing`；来源列表 8 条、provider 64 字符、model 200 字符上限与 `wire_text` 降级；摘要任务窗口 50 条、`summaryJobCount` 与 `summaryJobsTruncated`；缓存未命中只按日志视图、`CACHE_MISS_FLOOR = 1024` 与 `min(previousPrompt, prompt) - cacheRead` 估算，checkpoint 与分支摘要重置基线，分支视图不报告 `cacheWaste`。费用没有可信价目来源，`costUsd` 必须保持 `None`。脚本同时核对技术参考与使用指南的用量说明。除静态扫描外，脚本直接构造用量记录，对照 `verify_usage` 的 provider 归一化与七类原因、`bounded_identifier` 的长度与代理项降级，以及 `summarize_usage` 的回合桶、摘要任务、来源去重与上限、压缩策略、任务元数据与截断、活动任务标记与缓存估算（噪声下限、前缀缩短、无效记录、checkpoint / 分支摘要重置、分支视图不估算），共 139 项。实际计数仍需按用户指南核对。

### `check_startup_diagnostics.py`

`scripts/check_startup_diagnostics.py` 核对启动自检文本与桌面解析上限的一致性：`startup_check.py` 的每个 `_check(...)` 调用必须给出来自桌面 `NAME_PATTERN` / `CODE_PATTERN` 的固定名称与检查码、合法状态，以及不超过桌面 `MAX_TEXT_LENGTH`（按 UTF-16 码元计数）且不含控制字符的说明与建议；动态文本只允许来自已单独校验的来源（`_model_check` 的 `exc` 与回退提示、`_runtime_check` 的运行参数表项）。脚本还用 AST 核对 `_RUNTIME_OPTIONS` 四元组、`_DIAGNOSTICS` 二元组的全部文本，`ModelConfigErrorCode` 与 `_DIAGNOSTICS` 键集合双向一致，`_unconfigured_hint` 只返回三条已登记的提示常量（通用、OpenAI 线路可用、缺少 `openai` 包），点名线路前用 `find_spec` 确认包可发现；桌面 `startupCheck.ts` 的解析防护（字段名 / 检查码 / 状态 / 文本校验、`MAX_TEXT_LENGTH`、`ok` 一致性、报告与检查数量上限）与 `StartupCheckEntry` 协议字段作为文本片段核对。脚本还解析 `docs/USER_GUIDE.md` 的模型配置错误、目录错误与运行参数三张检查码表，分别与 `_DIAGNOSTICS` 键、`_state_check` 的错误码与 `_RUNTIME_OPTIONS` 的检查码集合双向一致，并确认内核可能输出的全部检查码都出现在使用指南中；`SETUP.md` 的检查结果表同样纳入核对，表内检查码必须由内核实际产出，`PREFIX_*` 通配至少匹配一个内核检查码，表不得为空或重复。脚本还核对 `__main__.py` 的严格模式：`--strict` 参数定义、与 `--check` 的绑定报错、报告先输出、错误优先返回 2、再按 `warning` 状态返回 1 的片段必须各出现一次且保持顺序，使用指南必须保留三种退出码的说明。`--state-dir` 的非空校验、`--listen` 的端点校验及各自的固定说明必须位于自检与索引修复分支之前，使相同参数下的自检结论与实际启动一致。脚本还核对 `startup_report()` 的检查项名称与顺序：桌面 `connectionNotice.ts` 的 `CHECK_TITLES` 键按同一顺序一致，中文标签与使用指南「检查项」表格的行按同一顺序一致。警告优先级同样核对：`_state_check` 必须按 `STATE_DIRECTORY_IN_REPO`、`STATE_DIRECTORY_TILDE`、`LEGACY_STATE_ENV_PRESENT`、`STATE_DIRECTORY_LOW_SPACE` 的顺序报告。运行参数顺序也纳入核对：按源码顺序收集 `ApplicationService.__init__` 中以 `from_environment` 结尾的读取调用，要求与 `_RUNTIME_OPTIONS` 的加载函数逐项一致，使 `--check` 报告的第一个错误与实际启动相同。审批期限由 `approval_timeout_from_environment` 统一解析，启动与自检共用；显式值无效时启动回退默认 300 秒，自检在其余参数有效时报告 `APPROVAL_TIMEOUT_DEFAULTED` 警告。模型重试配置同样由 `retry_settings_from_environment` 统一解析，返回生效次数、基础退避与显式值是否原样生效；非整数回退默认值，越界或负数收敛到边界，自检在审批期限有效时报告 `RETRY_CONFIG_DEFAULTED` 警告。`render_text` 也纳入核对：只能按固定字段读取报告与检查项，不得访问环境、文件、进程或打印 API，`_STATUS_TEXT` 覆盖三种状态并保留「说明」「建议」结构，检查项标题取自 `_CHECK_TITLES` 并要求与桌面 `CHECK_TITLES`、使用指南检查项标签三方一致，使复制到 Issue 的自检文本只含已校验内容。脚本还从 `render_text` 的结论赋值提取中文片段，要求桌面 `startupConclusion` 全部包含，并核对缺失或不可用报告返回空串、错误与警告分别按 `error` / `warning` 状态计数；设置页必须使用该函数并展示「自检结论」「运行于」，复制时把不可用固定说明作为诊断内容，避免终端结论与设置页结论各自漂移。脚本还核对数值上限配置：回合模型请求数与附件存储上限在格式和范围校验前去除首尾空白，空值回退默认上限。脚本还核对 Codex TOML 解析器不可用时使用登记的 `MODEL_CODEX_TOML_UNAVAILABLE`，使依赖该文件的默认线路可诊断，而可选线路不会阻断启动。审批期限与重试配置同样核对：只含空白时按未设置处理，不得只把空字符串当作未设置，也不产生 `APPROVAL_TIMEOUT_DEFAULTED` / `RETRY_CONFIG_DEFAULTED` 警告。脚本还核对空白 JSON 配置：`ModelCatalog.from_environment` 与 `CompactionPolicy.from_environment` 必须在 JSON 解析之前把空值或只有空白的取值按未设置处理，`ApplicationService` 的 `autoCompactionSource` 不得按 `BOSS_HARNESS_COMPACTION` 是否存在判定环境来源。桌面解析由结构检查覆盖。

19 个离线场景直接调用运行参数自检和终端渲染。检查验证五个解析器的错误码及相邻错误的优先级，覆盖空值、空白、合法配置、审批与重试警告，并校验 JSON 编码及终端文本均不含合成的无效配置原文。终端结论覆盖通过、仅有警告、仅有错误和错误与警告并存。

### `check_context_keep.py`

`scripts/check_context_keep.py` 固定保留目标提示的接线：判定函数 `keepTargetReachesLimit` 只在 `compactionSettings.ts` 定义一次，保留目标与上限都必须是正整数且保留目标不低于上限；会话上下文面板的两处提示都必须先确认预算已读取，再以 `budget.inputBudget` 调用；设置页从 `config/read` 的 `modelCapabilities.contextWindow` 取得正整数窗口后以 `compactionWindow` 调用。两处提示在使用指南与桌面指南中的说明片段也纳入核对。脚本不执行渲染层代码，提示的实际布局与触发时刻仍需运行桌面核对。

### `check_context_edits.py`

`scripts/check_context_edits.py` 核对上下文编辑与摘要检查点的读取边界：`_FINISHED_TURN_STATUSES` 固定四种已结束状态，替换文本上限为 32 000 字符与 128 KiB UTF-8；编辑记录的负载必须恰好是 `targetItemId` 与 `replacementText`，目标必须指向此前出现过的条目，替换文本不得为空白或超限；模型路径严格校验时整体拒绝损坏记录，`context_edit_states` 是唯一允许 `strict=False` 跳过的展示入口。`_apply_context_edits` 必须剥离 `originalInput`，只允许用户或助手文本，并把排除标记写入 `contextEdit`；读取侧统一经 `_context_edit` 映射，标注缺失或类型不符时按空对象处理。编辑入口 `context_edit` 先校验替换文本、`sourceDigest` 的 64 位小写十六进制与 `itemId`，在同一写入锁与索引事务内读取现状、拒绝不可编辑与摘要不符，再构造提交后的投影并先经 `validate_response` 校验，之后才追加记录并重建索引。检查点只信任 `_PUBLIC_CHECKPOINT_TEXT_LIMITS` 与 `_PUBLIC_CHECKPOINT_INT_FIELDS` 白名单字段，整数字段必须是非负安全整数；`_validated_checkpoint` 要求摘要非空且不超过 32 000 字符、来源摘要为规范 SHA-256、`throughTurnId` 存在、前缀回合全部结束、`sourceItemIds` / `sourceItemCount` 至少一项且与实际条目一致、拒绝运行中条目，并比对摘要前的原始记录与当前选择一致。脚本反向断言宽松读取只有一处、编辑标注只经 `_context_edit` 读取。检查同时直接调用纯函数做行为对照（137 项）：`_public_checkpoint` 的文本 / 整数字段白名单、上限与 2^53-1 边界；`_is_one_of` 与 `_context_edit` 的类型收窄；`_context_edit_entries` 的合法替换 / 删除、严格报错与宽松跳过、目标先出现、payload 精确键集、纯空白与 32 000 / 32 001 字符边界、同目标后写覆盖与其他类型忽略；`_apply_context_edits` 的副本语义、`originalInput` 剔除、删除标注、目标缺失 / 非消息 / 正文非字符串报错；`_context_edit_source_digest` 的格式、确定性与敏感性；`_checkpoint_source_item_ids` 的 `sourceItemIds` 与 `sourceItemCount` 两种来源及布尔 / 负数 / 超长拒绝；`context_edit_states` 的宽松展示投影。

### `check_context_estimate.py`

`scripts/check_context_estimate.py` 核对上下文规模估算、请求指纹与成功用量校准口径：`_message_size` 必须逐类型累加用户正文、助手文本、思考签名与脱敏数据、工具调用 id / 名称 / 参数 JSON、工具结果正文与调用 id，并为每条消息加 32 字符开销，参数先复制再序列化且不转义非 ASCII；`estimate_tokens` 必须包含系统提示并以 `(size + 1) // 2` 向上取整，不依赖厂商分词器；`_usage_input_tokens` 的字段按 provider 固定（OpenAI 仅 `input`，Anthropic 含缓存字段），只接受精确非负整数且总量受 `MAX_REQUEST_TOKENS` 约束；`request_fingerprint` 覆盖 provider、模型、系统提示、消息负载、工具 schema、输出预算、推理档位与思考配置，经规范 JSON 计算 SHA-256；`_message_fingerprint_payload` 的角色与块字段固定，包含 `signature` / `redactedData` / `prefixDigest` / `isError`。`_retained_usage_estimate` 的 fallback 逐条向上取整，只接受 `model_usage` 中 provider / 模型一致、`eligible` 为 `True`、消息数在界内、前缀逐条相等且前缀指纹复核通过的锚点；冲突锚点整体清空，用量必须严格递增，归属为空的区间跳过，按累计值四舍五入后换算为单条增量并记录已应用区间。除源码片段与顺序扫描外，脚本直接构造消息与 `ModelRequest`，对照 JSON 计数、各类内容块与固定开销、系统提示与向上取整、两家 provider 的用量字段与上限、指纹的确定性与字段变化、消息负载的可选字段，以及校验失败、冲突、归属、指纹与区间校准的结果，共 192 项。

### `check_summary.py`

`scripts/check_summary.py` 核对摘要规划的预算、逐字来源与无工具边界：`summary.py` 的输出上限 8 192、请求上限 32、摘要器提示对执行状态（只有「已执行成功」可说成已发生）与授权（既有审批只属于对应工具调用、摘要不扩大未来操作授权）的措辞、分支摘要的来源说明；来源先经 `wire_text` 降级并计算 SHA-256，单次输出预留模型上限与 4096 余量后的四分之一，滚动摘要预算按 32 000 字符与可用输入折算；预算不足或滚动摘要超限必须分别以 `ContextBudgetExceeded` 与 `ValueError` 拒绝，不得截断已有摘要；摘要请求必须 `tools=()`、`thinking=None`、`ensure_ascii=False`，来源按 `start:end` 逐字发送；片段切分按上下文窗口两倍的二分查找，起点无法容纳时以 `ContextBudgetExceeded` 失败。脚本反向断言来源不得从头截断、不得使用 `ensure_ascii=True`，并核对技术参考的摘要说明。检查另用临时合成配置执行 `SummaryPlanner`：四路输出约束、字符预算公式、逐字片段与来源摘要、恰好上限与超限拒绝、预算不足与来源末尾的 `ContextBudgetExceeded`、孤立代理项降级与重复规划稳定性；摘要质量本身仍需按用户指南核对。

### `check_private_files.py`

`scripts/check_private_files.py` 核对私有状态边界：`private_files.py` 必须保留目录 `0o700` / 文件 `0o600` 的创建与限制、`O_NOFOLLOW`、uid 与 inode 校验、ACL 清理和根目录拒绝；`ownership.py`、`persistence.py`、`session.py`、`snapshot_store.py`、`settings.py`、`maintenance.py`、`startup_check.py` 必须保留关键调用点；这些状态模块不得直接使用 `open(..., "w"/"a")`、`write_text(` 或 `write_bytes(` 写盘。`maintenance.py` 的索引修复必须先用 `lstat` 核对状态目录存在并在缺失时以固定说明拒绝，非空且不含任何状态标志（占用锁、`sessions`、`state.sqlite3`）的目录同样拒绝，再获取占用锁与创建备份目录，顺序与标志集合由脚本核对。行为侧用临时目录覆盖路径解析与符号链接环、根目录拒绝、两层目录创建与 `0o700`、已有目录不改权限、末级与父目录可写拒绝、只读核对不创建路径、文件创建 `0o600` 与读取收紧、只读打开不创建、符号链接与目录打开拒绝、收紧拒绝符号链接与目录（64 项）。符号链接竞态与跨平台 ACL 行为仍需按平台核对。

### `check_secret.py`

`scripts/check_secret.py` 核对凭据包装与错误文本脱敏的结构性边界：`secret.py` 必须恰有三种凭据形态（Bearer 令牌、`sk-` 密钥、key/token/secret/password 赋值），占位符固定为 `<redacted>`；`Secret` 只用 `__slots__` 保存单值、不是 dataclass、`repr` 与 `str` 共用占位符、取值必须显式调用 `get()`；`redact_secrets` 必须先短路空文本、再按长度至少 6 的已知原值替换，然后依次处理 Bearer（保留 `Bearer ` 前缀）、`sk-` 与赋值形式（保留键名与分隔符）。反向断言禁止 dataclass、明文 repr、第四种形态与改变占位符。同时核对技术参考的凭据包装口径。在此之上直接调用 `redact_secrets` 与 `Secret`：覆盖空文本 / `None` / 纯文本短路，已知原值的长度下限、空值与多次替换，Bearer 大小写与长度边界，`sk-` 前缀，赋值形式的 `:` / `=` / 引号 / 下划线 / 连字符，短值不替换与组合文本；以及 `get`、布尔值、`str` / `repr` 占位符、明文不出现、不可 JSON 序列化、仅槽位与拒绝额外属性。总项数 63。

### `check_export_privacy.py`

`scripts/check_export_privacy.py` 核对会话导出的默认脱敏边界：`session_export.py` 的 `EXPORT_FORMATS` 必须恰为 `markdown` / `json` / `html`，三个字节上限必须满足 `MIN_EXPORT_BYTES ≤ DEFAULT_EXPORT_BYTES ≤ MAX_EXPORT_BYTES` 且最大值低于 1 MiB；`application.py` 的 `thread/export` 请求字段白名单必须包含且只包含 `threadId`、`view`、`format`、`includeToolResults`、`maxBytes`，且 `includeToolResults` 默认 `False`；主进程 `security.ts` 的 `EXPORT_MAX_BYTES` 必须与内核 `MAX_EXPORT_BYTES` 相等，并保留按 UTF-8 字节数核对导出正文长度的判定；`session_export.py` 必须保留 `redact_secrets(` 与凭据、环境变量、本机路径、候选人信息四个脱敏标记，并且 `sensitive()` / `personal()` 的脱敏步骤与顺序必须保留、个人信息按长度降序打码；导出模块不得出现 `write_text(`、`write_bytes(`、`open(`、`os.replace(`、`unlink(` 或 `mkdir(`。在此之上直接构造 `Redactor` 并调用 `sensitive` / `personal` / `text` / `collect_personal`：核对已知凭据与短凭据、Bearer 与 Cookie 头、`sk-` 与 JWT、`__zp_*`、长 token、URL userinfo、环境变量赋值的替换结果和计数；已知路径尾段、含空格路径、通用绝对路径、Windows / UNC / file URL、单段根路径与正文斜杠词；PII 键归一化、数值 / 布尔 / 长度 / 深度 / 总量边界、`finalize` 的长值优先排序、邮箱 / 手机号 / 身份证 / 微信号、非文本输入、文本截断与组合管线。另核对 `_known_secrets` / `_known_paths` / `_continues_path` / `_path_end` / `_short_text` / `_status_text` / `_normalize_key` 的边界。总项数 149。

### `check_export_write.py`

`scripts/check_export_write.py` 核对会话导出的原子写入与失败诊断：临时文件必须由 `O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW` 在目标同目录独占创建、命名固定为 `.boss-harness-export-<uuid>.tmp` 且默认 `0600`；`O_NOFOLLOW` 缺失时回退为 0；`lstat` 的 `ENOENT` 视为新文件，`ELOOP` 与现成符号链接固定报 `symlink`；`sameTarget` 必须同时比较 dev、ino 与可得的 ctime；写入顺序固定为写入 → `sync` → `chmod(0o600)` → 关闭并置 `closed` → 再次核对目标身份 → `rename` 原子替换；`rename` 失败先删除临时文件再抛出原始错误；`chmod` 失败只记录 `permissionError` 并返回 `permissionsUnchanged: false`，不得中断保存；finally 在未关闭时补关闭并清理临时文件。`harness.ts` 的保存对话框必须带 `createDirectory` 与 `showOverwriteConfirmation`，默认目录为下载目录，失败日志只写诊断文本，回执只返回 `basename`。反向断言禁止声称沿用旧权限与回显完整路径。检查是源码字面量与首次出现顺序扫描，实际写入行为仍需按用户指南核对。

### `check_export_html.py`

`scripts/check_export_html.py` 核对会话导出 HTML 的转义与页面约束：`session_export.py` 必须以 `html.escape(str(value), quote=True)` 提供 `_h`，会话元数据、回合标题 / 用时 / 用量、用户与模型正文、附件元数据、工具名 / 执行状态 / 审批 / 错误码 / 恢复建议 / 来源 / 参数、结果明文与事实、摘要与队列 id / 类型 / 事实 / 完整输入都必须经 `_h` 进入页面；结果明文只在 `included` 分支以 `<pre class="plaintext">` 写入；文档头保留 charset、viewport、`default-src 'none'; style-src 'unsafe-inline'` 与 `no-referrer`。反向断言页面不含脚本、事件属性、帧、`javascript:`、`src=` 或 `href=`。在此之上直接调用 `_h` 与 `_render_html`：核对 `& < > " '` 与非字符串输入，最小 `meta` / `units` / `counts` / `queue` 下的 doctype、CSP、referrer、页脚闭合与主体结构，恶意会话 id 与标题转义，两种工具结果提示，日志与当前分支视图，脱敏统计，截断与孤立条目提示，以及空标题回退。总项数 81。

### `check_export_markdown.py`

`scripts/check_export_markdown.py` 核对会话导出 Markdown 的定界与代码围栏：`_code_text` 必须把反引号替换为单引号、把回车与换行替换为空格，供行内代码与 HTML 文本使用；`_inline_text` 必须在这之后把 `\`、`[`、`]`、`<`、`>`、`*`、`_`、`~`、`|` 转义为字面字符；`_inline_code` 必须用 `_code_text` 包裹反引号，不得改用会插入反斜杠的正文转义；`_fence` 必须用 `re.findall(r"`+|~+", text)` 取最长连续反引号或波浪线，再以「最长长度加一、最少三个」的反引号作为围栏，语言标记默认 `text`。回合 id / 状态 / 工具名 / 错误码 / 队列 id 必须走行内代码，标题、时间、来源、参数键与参数值、恢复建议、摘要模型与任务 id 必须走正文转义；用户输入、模型输出、结果明文、摘要正文与队列输入必须走围栏，结果明文只在 `included` 分支以 `json` 围栏写入。反向断言围栏不退回固定三个反引号或波浪线、正文不再经 `_inline_text`、行内代码不得改用正文转义。在此之上直接调用 `_code_text` / `_inline_text` / `_inline_code` / `_fence`，核对反引号、回车、换行与非字符串输入，九个行内定界符与反斜杠转义，行内代码不转义正文定界符，动态围栏取反引号与波浪线最长的加一长度、语言参数、空正文与内部换行保留。总项数 111。

### `check_export_json.py`

`scripts/check_export_json.py` 核对会话导出 JSON 的分组结构与严格编码：回合前的条目必须进入 `beforeFirstTurn`，后续条目追加到最近回合的 `entries`，不得平铺或重排；文档必须展开 `meta` 并带 `redaction.marks` 的四项脱敏标记、`redaction.counts`、三类 `origins`、`beforeFirstTurn` / `turns` / `queue`、`truncated` / `exportedEntries` / `totalEntries` / `maxBytes`。编码固定为 `ensure_ascii=False`、`indent=2`、`default=str`、`allow_nan=False`，`RecursionError` 与非有限数值分别降级为可读的 `ValueError`。`EXPORT_SCHEMA` 必须固定为 `boss-harness-session-export/1`，采用「名称/整数版本」形式，`meta` 只引用该常量，不得另写 schema 字面量。反向断言不得允许 NaN / Infinity、不得改用 ASCII 转义或绕过参数直接编码。在此之上直接调用 `_render_json` 并解析结果：核对 schema、四项脱敏标记、计数写入、三类来源、回合前 / 回合内 / 无回合分组、截断与条目计数、queue、额外 `meta` 字段、中文不转义、两空格缩进与尾部换行、非 JSON 值转字符串，以及 NaN / Infinity / 深层嵌套的可读错误。总项数 68。

### `check_local_export.py`

`scripts/check_local_export.py` 核对旧内核回退路径的本地 Markdown 导出：标题必须先经 `replace(/\s+/g, " ")` 折叠连续空白、`trim()` 去除首尾空白、共享 `safeSlice` 限制 200 个字符，空标题回退为「当前会话」，最终模板只能引用收敛后的 `exportedTitle`。正文顺序固定为消息正文、段落、`-` 列表与工具复制文本，空项过滤后以空行连接；工具或审批记录继续复用 `messageCopyText`，不改写用户或模型的 Markdown 正文。反向断言标题不得直接进入模板，也不得绕过共享截断改用 `title.slice` 或 `substring`。检查是源码字面量扫描，不执行渲染或导出。

### `check_export_dialog.py`

`scripts/check_export_dialog.py` 核对导出弹窗的目标固定与明文确认：打开新目标时先记录 `threadId`，变化时递增版本，保存回执必须核对版本，旧目标的结果不得覆盖新目标；保存期间锁定选项与关闭入口，关闭必须经 `requestClose`；勾选「包含工具结果明文」后先清空确认，只有 `includeToolResults && acknowledged` 同时成立才发送 `acknowledgePlaintext: true`。请求字段固定为 `threadId` / `view` / `format` / `includeToolResults` / `acknowledgePlaintext`，保存、取消、失败、截断与权限提示都有固定回执。桥接能力缺失时显示「当前桌面外壳不支持会话导出，请更新桌面端后重试。」。反向断言不得发送未确认明文、不得在保存期间关闭、不得绕过 `requestClose`。检查是源码字面量扫描，不执行弹窗。

### `check_usage_report.py`

`scripts/check_usage_report.py` 核对用量弹窗「复制 CSV」的公式防护与转义：以 `= + - @`、制表符或回车开头的单元格必须先加前导单引号，含逗号、双引号、CR 或 LF 的单元格按 RFC 4180 加引号并翻倍内部双引号；没有已验证请求或字段为空时输出空单元格，不把未知写成 0。表头固定为 16 列，行序固定为合计、缓存未命中、摘要任务合计、摘要任务明细、每回合与两类截断说明，行尾为 CRLF。原因键只读 `USAGE_REASONS` 的自有属性，未知键原样显示；费用没有价目来源，不输出。检查还固定 `usageJobSource` 的分支、`usageClip` 的折叠 / 截断 / 回退，并反向断言不得直接返回原文、不得绕过自有属性检查或增加费用列。检查是源码字面量扫描，不执行表格软件或剪贴板写入。

### `check_recent_search.py`

`scripts/check_recent_search.py` 核对搜索弹窗最近搜索的阈值来源与本地存储回退：最短长度必须引用 `MESSAGE_SEARCH_MIN_LENGTH`，最长长度引用 `MESSAGE_SEARCH_MAX_LENGTH`，不得写死数字；去重键使用整串 NFKC 小写归一化，保留用户输入的原始大小写与全角写法；上限为 5，空查询不改变历史。读取、解析、写入与清除各自在存储不可用时回退：损坏 JSON 与非数组一律回退为空，写入失败仍返回当前列表，清除失败不抛出。检查是源码字面量扫描，不执行浏览器存储。

### `check_session_title.py`

`scripts/check_session_title.py` 核对新建会话标题的生成顺序：先剥离首页固定格式的「招聘项目：<名称>」前缀（不匹配时原样返回），再折叠连续空白、`trim()`，按 Unicode 码点判定是否超过 `SESSION_TITLE_LIMIT`（32），超限时按码点截断，空内容回退「新会话」。`compactTitle` 在空值或非正上限时回退，只有真正超限才截断并保留省略号；`trimEnd()` 去掉截断点前的空格。检查还确认默认上限不超过内核的 `MAX_THREAD_TITLE_CHARS`，并反向断言不得用 `slice` / `substring` 直接截断或把超限判断写成 `>=`。检查是源码字面量扫描，不执行界面。

### `check_search_rows.py`

`scripts/check_search_rows.py` 核对搜索弹窗与侧栏共用的会话行：已归档会话默认排除，只有 `includeArchived === true` 时纳入；同一会话 id 只保留首次出现的行，去重键在关键词匹配之前登记。标题与项目名拼接后做整串 NFKC 小写，查询按空白拆分为关键词并全部命中（`every`）才算匹配；结果按 `sessionUpdatedAt` 降序，缺失或非完整 ISO 时间由共享解析回退 0。检查还核对高亮使用的 `searchText` 是同一 NFKC + `zh-CN` 小写口径，并反向断言不得默认纳入归档、不得退回 `some` 单关键词匹配、不得只匹配标题。检查是源码字面量扫描，不执行过滤或排序。

### `check_message_search.py`

`scripts/check_message_search.py` 核对消息搜索的批次失效与内核响应校验：批次记录的查询或归档范围与当前输入不一致时返回空结果；`matches` 非数组按空结果处理；每项命中必须是对象，`threadId` / `itemId` 非空，`threadTitle` 与 `snippet` 是字符串，`role` 只能是 `user` / `agent` / `tool`；通过校验的命中还要按当前可见会话过滤，`truncated` 只认布尔真。`liveMessageSearchState` 在未启用、过短或过长时保持组件状态，批次尚未对应当前输入时按检索中呈现。反向断言不得直接映射批次、不得把未校验命中交给渲染、不得用布尔真值判断截断并保留 `tool` 角色。检查是源码字面量扫描，不执行搜索请求。

### `check_find_highlight.py`

`scripts/check_find_highlight.py` 核对会话内查找的高亮区间：先在整串 NFKC 小写归一化文本中扫描命中，再把归一化偏移映射回原文；同一次字素展开产生的重叠区间合并时取最大结束位置，并从命中末尾继续；单段文本最多 200 个区间。拆分按区间顺序输出未命中与命中片段，末尾补剩余原文。关闭的 `<details>` 内文字默认不参与匹配与高亮，`summary` 例外；`includeFolded` 为假时只收集可见正文。反向断言不得直接对原文使用 `indexOf`、不得省略重叠合并、不得移除折叠块排除，且上限保持 200。检查是源码字面量扫描，不执行 DOM 或查找。

### `check_search_status.py`

`scripts/check_search_status.py` 核对搜索弹窗的状态行与空态只描述真正完成的搜索范围：状态行按「空查询 → 完成（含截断）→ 过长 → 失败 → 其他」排列，零命中且截断时使用「消息搜索不完整」；空态在未启用、失败、过长、过短或检索中时给出各自原因，只有完整分支才出现「没有找到相关聊天或消息」。空态的最短字符数提示必须引用 `MESSAGE_SEARCH_MIN_LENGTH`，最长字符数引用 `MESSAGE_SEARCH_MAX_LENGTH`。检查还反向断言完整结论只出现一次且在未完成分支之后、不得写死数字阈值。检查是源码字面量扫描，不执行界面或搜索。

### `check_search_options.py`

`scripts/check_search_options.py` 核对搜索结果的顺序与定位意图：消息命中排在会话标题结果之前，消息按 `threadId:itemId` 去重并入列，找不到对应会话行的命中直接跳过；随后遍历会话行，按 `session:<id>` 键去重入列。角色标签把 `user` / `tool` / 其他分别显示为「你」「工具」「助手」。`searchHitFocus` 只对工具命中返回 `revealToolBlock: true`，其余保持折叠，查询词去掉首尾空白后带回会话。反向断言缺行不得中断列表、只有工具命中可以展开工具块、关键词必须 `trim()`。检查是源码字面量扫描，不执行搜索或打开会话。

### `check_find_step.py`

`scripts/check_find_step.py` 核对会话内查找的跳转游标：每条匹配消息至少一处位点（`Math.max(1, whole(count))`），游标的消息下标与消息内位点都夹进范围；段内还有命中时先走完，跨消息用 `(current.message + delta + length * length) % length` 循环到另一端，反向进入该消息的最后一处。全局序号把前面每条消息的位数累加后加当前位点，用于「第 N / M 处命中」。反向断言数值必须向下取整、反向循环不得出现负模、序号不得由消息下标与位点直接相加。检查是源码字面量扫描，不执行查找或跳转。

### `check_find_status.py`

`scripts/check_find_status.py` 核对会话内查找状态行的计数单位与分支：空查询显示「输入关键词」；`total > 0` 时把位次夹进范围并按 1 起始显示「第 N / M 处命中」，只有 `capped === true` 才追加「仅前 N 处高亮」，上限取 `input.highlightLimit ?? FIND_HIGHLIGHT_LIMIT`；零命中时先看 `detailHits`，给出「正文无匹配 · 含详情可命中 N 条消息」，最后才是「无匹配消息」。反向断言数值向下取整、详情提示只在零命中分支出现一次、上限不得写死。检查是源码字面量扫描，不执行查找或界面渲染。

### `check_find_seed.py`

`scripts/check_find_seed.py` 核对会话内查找沿用选中文本的放行条件：焦点落在 `input` / `textarea` / `select` 或 `isContentEditable` 时返回 `null`；选择不是字符串、`trim()` 后为空、含 `\r` / `\n`、或按 `codePointLength` 超过 `FIND_SEED_MAX_LENGTH = 120` 时不沿用，否则返回去掉首尾空白的文本。判定顺序固定为「可编辑 → 类型 → 去空白 → 空选择 → 多行 → 码点上限」，反向断言不得按 `String.length` 判长、多行校验不得先于 `trim()`。检查是源码字面量扫描，不执行查找或选择。

### `check_thread_search_result.py`

`scripts/check_thread_search_result.py` 核对搜索回执的形状校验与上限：单条命中要求对象、非空且不超过 200 字符的 `threadId` / `itemId`、不超过 4096 字符的标题与片段（允许为空）、`user` / `agent` / `tool` 三种角色，角色先过白名单再断言类型；整体回执要求 `matches` 为数组且不超过 `SEARCH_MATCH_LIMIT = 200`，`truncated` 只接受布尔或缺省，任一命中非法时整体拒绝，`truncated` 只取显式 `true`。

同一脚本固定跨分支命中的标记：会话区按当前分支视图展示，`thread/search` 却覆盖完整日志，因此 `search_messages` 对含位置记录的会话额外按 `_active_entries` 投影出当前分支的条目集合，逐条给出 `onBranch`（投影失败时省略字段，搜索结果照常返回）；客户端只接受显式布尔，弹窗仅在 `onBranch === false` 时显示「其他分支」标签，并把该事实随打开动作传给会话区。会话区在历史未读尽时继续等待定位，列表就绪仍找不到才显示说明（已确认在其他分支 / 可能在其他分支或尚未载入），不再静默放弃；说明可关闭，关闭时才清除定位意图。检查是源码字面量扫描，不执行搜索或渲染。

### `check_model_switch.py`

`scripts/check_model_switch.py` 核对模型线路切换的在途锁与回执令牌：`begin` 在 `pending` 时返回 `null`，否则令牌自增、清空错误并交出令牌；`settle` 只结算发起它的那次请求，令牌不符直接返回；`switches` 按 `threadId` 缓存实例，`useModelSwitch` 在未关联会话时使用组件本地实例，不把匿名预览的状态混进会话缓存。反向断言在途会话不得再次交出令牌、迟到回执不得越过令牌核对、实例必须复用。检查是源码字面量扫描，不执行设置请求或切换模型。

### `check_session_index_health.py`

`scripts/check_session_index_health.py` 核对会话索引健康度的读数与设置页文案：配置必须是对象，`unreadableThreadCount` 必须是非负安全整数，否则返回 `null`；计数为零却列出不可读 id 是矛盾响应，同样返回 `null`；有计数时只收集 1–64 字符的字符串 id，去重后按 `SESSION_INDEX_MAX_IDS = 20` 截断。文案三态为「未报告」「N 个无法读取」「正常」，未报告不得写成正常。检查是源码字面量扫描，不执行配置读取或界面渲染。

### `check_queue_status.py`

`scripts/check_queue_status.py` 核对任务队列的状态与暂停原因文案：五种通用标签按 `queued` / `delivering` / `delivered` / `paused` / `cancelled` 排列；暂停项先看 `TURN_START_FAILED`，再按 `COMPACTION_FAILED`、`THREAD_ARCHIVED`、`TURN_NOT_COMPLETED` 排序，关联去重项显示「已关联已有回合」。暂停说明在非暂停项先返回 `null`，启动失败按 `inputPersisted` 三态分支，`retryAvailable` 只作为「未写入」分支的措辞选择。检查是源码字面量扫描，不执行队列操作。

### `check_notification_labels.py`

`scripts/check_notification_labels.py` 核对通知分组标题的拼接与截断：空白折叠后取线程 id 前 8 位回退，缺失会话显示「会话 <id>」；项目名与会话标题相同时不重复拼接；归档会话补「 · 已归档」。长度判断把后缀计入 120 上限，超限时按码点用 `safeSlice` 截断并保留后缀与省略号。反向断言不得按 UTF-16 码元截断、长度判断不得忽略后缀。检查是源码字面量扫描，不发送通知。

### `check_sidebar_notice.py`

`scripts/check_sidebar_notice.py` 核对侧栏操作回执的序号重播与清空语义：每次回执都生成新记录并让 `seq + 1`，即使文案相同也不复用；计时器到点只清空文案，空态返回原对象，序号不重置。`ProjectSidebar` 以 `notice.seq` 作为提示节点的 key，容器保留 `role="status"`，停留时长取 `SIDEBAR_NOTICE_TIMEOUT_MS = 2600`。反向断言相同文案不得复用对象、清空不得重置序号、组件不得改用文案作 key。检查是源码字面量扫描，不执行复制或渲染。

### `check_usage_view_keys.py`

`scripts/check_usage_view_keys.py` 核对用量范围单选组的方向键循环：左右与上下方向键映射为 ±1，其他按键返回 `null`；视图先经 `indexOf` 越界保护，再以 `(index + delta + USAGE_VIEWS.length) % USAGE_VIEWS.length` 非负取模循环，选项顺序为 `log`、`branch`。反向断言四个方向键都必须参与映射、取模前必须补齐长度、未知视图不得回退首项。检查是源码字面量扫描，不执行键盘事件或渲染。

### `check_send_failure.py`

`scripts/check_send_failure.py` 核对发送失败与结果未确认的措辞边界：`isHarnessRpcRejection` 为真时写「发送失败」，否则写「提交结果尚未确认」，两条主提示都带读取会话状态的下一步；复核提示复用同一主因，只追加读取结论，不重复包裹说明。反向断言两种来源不得对调、复核提示不得重复「正在读取会话状态」。检查是源码字面量扫描，不发送请求。

### `check_last_session.py`

`scripts/check_last_session.py` 核对上次打开会话的存储解析与回退：`LAST_SESSION_KEY` 以 `UI_STORAGE_PREFIX` 为命名空间；解析要求字符串、去空白后非空、不超过 200 字符，且 `id === raw`（带首尾空白视为损坏）；读取与写入都捕获存储异常并退回首页；`rememberLastSessionId(null)` 删除键而不是写入空字符串。检查是源码字面量扫描，不访问本地存储。

### `check_ui_storage.py`

`scripts/check_ui_storage.py` 核对界面偏好的旧命名空间迁移：先收集 `boss-cli.ui.*` 旧键，再逐个把前缀替换为 `boss-harness.ui.`；新键已存在时跳过，旧值只用于补齐，不删除旧键；整体捕获存储异常，隐私模式下界面按默认值运行。检查是源码字面量扫描，不访问本地存储。

### `check_thread_list.py`

`scripts/check_thread_list.py` 核对 `thread/list` 条目的逐项校验与分页去重：标识、标题、更新时间与可选文本各有上限；`archived` 只接受布尔，`toolPolicy` 只接受 `readOnly` / `approval`；`optionalText` 把缺省与非法分开；`lastTurn` 与 `branchLastTurn` 共用一个校验函数：非空 `turnId`、状态属于 `running` / `completed` / `interrupted` / `blocked` / `error`，失败码与恢复策略出现时必须是字符串。`uniqueThreadIds` 用集合大小比较拒绝重复 id。

同一脚本还固定末回合的来源：切换过分支位置的会话，`lastTurn` 仍是日志中最后写入的回合，可能属于已放弃的分支；内核索引另写 `branchLastTurn`（当前分支末回合，位于会话开头时为 `null`），写入前先清掉会话头或会话信息记录带来的同名值，只对含位置记录的会话推导，分支无法投影时不写字段也不让列表失败，分叉出的会话头不继承。`thread/read` / `thread/resume` 的分支视图（普通读取与冻结快照）经同一个辅助函数把两个字段换成本次读取的同一个值，未切换过位置的会话不补字段。桌面端两处会话摘要映射都经 `summaryTurnOf` 选出回合（有 `branchLastTurn` 键就用它，否则用 `lastTurn`），不得直接读取任一字段；收到 `thread/leafChanged` 后除重读会话外还刷新会话列表，继续检查取自刷新后的摘要。索引只在会话文件变化后重建：升级前已切换过位置的会话由投影内容版本在首次启动时失效一次（见 [`check_persistence.py`](#check_persistencepy)）；之后若降级到不带该字段的版本并写入过这类会话，再升级后要到下一次写入才重新带上字段，缺省时桌面端按 `lastTurn` 处理。检查是源码字面量扫描，不读取会话索引。

### `check_session_start.py`

`scripts/check_session_start.py` 核对新建会话与首条消息的四种结果：`started` / `unsent` / `unconfirmed` 都必须能打开已建立的会话，只有 `failed` 返回 `null`；发送结果把 `started` 映射为 `true`、`unconfirmed` 映射为 `"uncertain"`，其余为 `false`；主界面提示只覆盖 `unsent` 与 `unconfirmed`，快速提问提示额外覆盖 `failed` 并给出「未能创建会话」。反向断言 `unconfirmed` 不得按失败处理、创建失败提示只出现在快速提问。检查是源码字面量扫描，不发送消息。

### `check_time_format.py`

`scripts/check_time_format.py` 核对界面统一时间格式与会话排序键：`pad` 必须补足两位；`formatLocalDateTime` / `formatLocalClock` 先判 `Number.isNaN` 再分别输出 `YYYY-MM-DD HH:mm` 与 `HH:mm:ss`；`formatIsoDateTime` / `formatIsoClock` 经严格 `parseIsoDateTime` 解析，无效值返回空字符串；`sessionUpdatedAt` 以 `?? 0` 回退。反向断言不得调用 `toLocaleString` / `toLocaleDateString`、排序键不得使用 `Date.parse`、两个格式化函数都要判非法。检查是源码字面量扫描，不执行 TypeScript，也不改变运行时区。

### `check_preferences_file.py`

`scripts/check_preferences_file.py` 核对界面偏好导出文件：空文本与 64 KiB 字节上限先于 JSON 解析；结构、版本 `1`、`boss-harness.ui` / `boss-cli.ui` 两种作用域与偏好对象依次校验；旧作用域按 `LEGACY_UI_STORAGE_PREFIX` 读取；字体大小只接受 12–16 的字符串，会话密度、动态效果、审批提示音与主题各有枚举；任一已知键非法即整体拒绝，未知键忽略，零字段拒绝。导出只写五个白名单键，序列化为带版本与作用域的文件。反向断言不得导出别名或项目名、旧作用域不得按新前缀读取、非法已知键不得跳过、不得展开偏好对象。检查是源码字面量扫描，不读取本地存储。

### `check_theme_preference.py`

`scripts/check_theme_preference.py` 核对主题偏好的三态语义：联合类型只含 `system` / `light` / `dark`；解析先拒绝非字符串，再 `trim().toLowerCase()` 折叠空白与大小写，无法识别时回退 `system`；`resolveDarkTheme` 按 `dark` → 真、`light` → 假、其余跟随系统外观；`serializeThemePreference` 只保留 `light` / `dark`，其他值规范化为 `system`。反向断言解析不得跳过空白折叠、写回不得原样保留未知值、回退不得落到固定外观。检查是源码字面量扫描，不执行 TypeScript。

### `check_single_flight.py`

`scripts/check_single_flight.py` 核对单飞读取的尾随补跑与取消：入口先判取消与 `canRun`，在途期间只置尾随标记并返回；同步抛错也以已解决的 Promise 释放单飞标记；`.catch().finally()` 链在收尾释放单飞标记，再按取消与尾随标记决定是否补跑一次；`cancel` 同时清除取消与尾随标记且不直接补跑。反向断言单飞标记只能在收尾释放、尾随标记只在补跑与取消时清除、不得用延时轮询代替尾随补跑。检查是源码字面量扫描，不执行 TypeScript。

### `check_queue_read_guard.py`

`scripts/check_queue_read_guard.py` 核对队列并发读取的先后守卫：`QueueReadTicket` 的 `commit` 只在 `isCurrent` 为真时执行写入；`issue` 先推进该会话的代数再快照己方代，`isCurrent` 严格比较当前代与己方代；`invalidate` 只推进代数，让此前发出的读取全部失效；缺失会话从 0 起算，代数单调递增。反向断言写入必须经过当前代检查、失效不得删除代数记录、缺失会话不得使用负值起点。检查是源码字面量扫描，不执行 TypeScript。

### `check_attempt_token.py`

`scripts/check_attempt_token.py` 核对在途请求标记：标记初值为 0，`startAttempt` 与 `invalidateAttempts` 都递增，`startAttempt` 返回推进后的值；`attemptCurrent` 只做 `token === tracker.current` 的严格比较。反向断言开始与作废都必须推进标记、开始提交不得重置标记、比较不得放宽。检查是源码字面量扫描，不执行 TypeScript。

### `check_delete_thread_error.py`

`scripts/check_delete_thread_error.py` 核对删除会话失败的原因码映射：只有内核 `rpcError === true` 且 `data.code` 为字符串时才读取原因码；`THREAD_BUSY` 按 `data.reason` 查表给出运行中回合、摘要任务、队列投递与后台清理四种可执行提示，原因缺失、非字符串或未知时回退到不针对具体原因的兜底文案，且查表只走 `Map`，`__proto__`、`constructor` 等键名不能命中原型链；`THREAD_DELETE_INCOMPLETE` 与 `THREAD_NOT_FOUND` 映射为 `incomplete`，其他原因映射为 `unknown` 并带原始错误文本与刷新核对提示。反向断言原因码只允许三种、四种占用提示互不相同、不得把结果说成已删除、未知原因必须带原始错误文本。检查是源码字面量扫描，不调用内核。

### `check_deleted_thread_state.py`

`scripts/check_deleted_thread_state.py` 核对删除会话通知的连接内状态清理：`deletedThreadState.ts` 的 `forgetDeletedThread` 接受可按键删除的状态，空 id 直接返回 `false`，逐项删除并返回是否确实删除过内容；`approvalSubmission.ts` 的 `forgetApprovalSubmission` 同样拒绝空 id 并丢弃模块表中的会话条目；`deletedDialogTarget.ts` 的 `detachedTarget` 只在删除标记与目标会话一致时返回 `null`，空目标、空删除标记与其他会话原样返回同一对象。主界面的 `thread/deleted` 分支先让该会话的在途队列读取失效，再按消息缓存、队列投影、失败提示、条目版本、回合标识与记住的审批依次遗忘，随后丢弃审批提交状态、清后台完成标记、释放停止状态、退出被删除的当前会话、收起固定在该会话的上下文 / 用量 / 导出 / 分支 / 回退弹窗、移除列表项并刷新；`handleDeleteSession` 复用同一组调用并直接退出视图。审批回执另按实例归属收敛：`approvalSubmissionIsCurrent` 只通过 `Map.get` 比较发起时的实例，不创建状态；手动与自动路径在发送前固定实例，在回执到达后、任何投影或提示写入前核对归属，删除或替换后原实例不能结算。自动路径直接用捕获的实例记录错误，不重新取得状态。反向断言两条删除路径不得退回只删缓存的旧写法，删除回执不得依赖通知回调；弹窗清理必须逐一判定五个固定目标，不得无条件清空目标。`withoutThread` 从按会话保存的状态表中移除条目，未命中时返回同一对象。`thread/deleted` 通知按内核与协议约定携带 `deletedThreadId`（不是普通通知的 `threadId`），四个 hook 都只读取该字段，检查另附反向断言禁止删除分支读取通用 `threadId`。上下文面板与分支弹窗在 `thread/deleted` 时直接遗忘该会话：记录当前连接内的已删除 id，`update` 与 `refresh` 对已删除会话不写状态、不发起读取；上下文面板另作废该会话的读取版本与重读请求，分支面板作废版本、清除轮询失败计数，并在删除的正是弹窗目标时解除固定。两个 hook 的删除分支都必须在通用会话 id 分支之前处理并直接返回，遗忘直接改写状态表而不经 `update`；定时器继续只遍历状态表，会话被移除后自然不再轮询。推理档位同样按会话保存读取结果、保存锁与失败原因：删除通知先于方法白名单处理，遗忘直接移除状态表条目并递增读取版本，读取的归属判定同时要求会话未被遗忘，删除后不再发起读取；保存回执在写回与回读前核对会话未被遗忘。三个 hook 断连时连同该记录一起重置。自动压缩覆盖按会话保存未应用草稿、已应用覆盖与手动改动标记：删除通知移除该会话的三项记录，删除的正是当前会话时表单回到默认占位值、清除旧错误并作废在途默认值读取；覆盖先复制再删除，不原地改写已有对象。分支切换的入口与回执归属判定同样要求会话未被遗忘：已删除会话不会发起切换，删除途中发出的 `thread/leaf/set` 回执不再调用 `onSwitched`、写状态或刷新。检查是源码字面量与首次出现顺序扫描，不渲染界面。

### `check_compaction_override.py`

`scripts/check_compaction_override.py` 核对自动压缩覆盖从取出到恢复的语义：`take` 先登记本次消耗（覆盖对象与当时的标记）再移除覆盖，成功或回执未知都保持已消耗；`restore` 只对取出时的同一份覆盖、同一标记生效，期间重新应用、清除或再次取用都不恢复，且只写回覆盖与表单，不重建草稿或改动标记、不重新取用、不改写失败提示。主界面直接发送按「取出 → 发送 → 判定拒绝 → 恢复」处理，恢复只在明确拒绝分支出现一次；排队发送只在明确拒绝时恢复一次，并继续抛出原错误。检查是源码字面量与首次出现顺序扫描，不执行 React hook。

### `check_branch_switch.py`

`scripts/check_branch_switch.py` 核对会话内分支切换的步骤与失败文案分界：切换先读取目标会话自己的队列，再置提交标记并调用 `thread/leaf/set`，回执必须与所选会话和位置一致，最后才重新读取会话。内核确认切换后重读失败，必须在就近的 `catch` 内提示「分支已切换，但重新读取会话失败」，不得使用「切换结果尚未确认」；未提交（队列核对失败）、已提交但明确拒绝、已提交但回执未知三类失败各有固定文案，未确认文案不得出现在尚未提交的路径。检查是源码字面量与首次出现顺序扫描，不执行 RPC。

### `check_branch_pagination.py`

`scripts/check_branch_pagination.py` 核对分支读取期间的位置漂移：`readPagedItems` 必须回报实际请求页数（`pages`）；分支面板按请求顺序记录端点每一页的 `leafTurnId` 与回合每一页 `branch.leafTurnId`，全部一致才写入状态，单页读取同样生效且位置稳定时不增加请求。不一致时两处核对都只上报、由唯一一处决定：只读重读一遍（读取函数恰好调用两次，中间不得有循环、延时或递归刷新），一致就照常写入，仍不一致才提示并放弃；过期判定沿用同一个版本号，重读期间被更新的刷新或断连取代时不写入。`branchPageLeafOf` 把缺失的 `branch` 归为旧内核（`missing`），归属其他会话或形状不符归为无效并按响应错误处理，不得当作空位置；`sameLeafAcrossPages` 逐页比较而不是只比较首尾。回合页缺少位置且发生翻页时才回退到端点复核，端点复核只允许出现在该分支内。步骤顺序固定为列表拼接 → 逐页比较 → 回退复核 → 重读一遍 → 过期退出 → 提示 → 摘要读取，仍不一致时立即返回、不写入旧 leaf 与端点；反向断言只在翻页时复核、发现变化后不重读直接提示的旧实现不再出现。读取失败只更新提示、不清除已载入的列表，`BranchDialog` 必须在错误提示之后、端点列表之前用 `data-branch-stale` 说明下方是上次成功读取的结果，且只在已成功读取过时显示。重读触发清单 `BRANCH_REFRESH_EVENTS` 固定为 `thread/leafChanged`、`turn/started`、`turn/completed`、`thread/updated`、`context/compacted`，只定义一次、只在目标会话的通知上使用一次；内核两处 `turn/started` 都必须晚于对应的运行中回合写入，界面收到通知后重读才能读到新位置。「会话上下文」面板的 `PLAN_INVALIDATING_EVENTS` 在回合与压缩通知之外包含 `thread/leafChanged`：清除整理计划、推进修订号（在途计划请求按修订号作废）、面板打开时重读预算，回合运行标记只随回合通知变化；内核的位置切换通知保持唯一。内核侧，`list_branch_turns` 在同一次持锁读取里用同一份条目算出回合集合与 `branch`（只读取一次条目、不调用 `read_leaf`），`thread/turns/list` 处理器按字段返回该 `branch`，不得在释放锁后另行读取位置或透传未声明的字段。`thread/read` / `thread/resume` 的非快照分支视图把处理器读到的条目快照传给 `branch_last_turn`、`list_branch_turns` 与 `read_leaf`，`items`、`thread.lastTurn`（及已分支会话的 `thread.branchLastTurn`）、`turns` 与 `branch` 同源；这三个读取带快照时不得重新读取条目，处理器内不带快照的旧调用不得再出现。「会话用量」的当前分支视图同样逐页记录 `branch.leafTurnId`：位置只在分支视图读取一次，读完先比较位置、再做重复与总数校验，不一致就放弃并提示刷新，不为核对增加请求；内核 `usage_page` 的位置与回合在同一次持锁读取内由同一份条目算出。检查是源码字面量与首次出现顺序扫描，不执行分页读取。

### `check_harness_events.py`

`scripts/check_harness_events.py` 核对 `harnessEvents.ts` 的实时事件映射：`toolCall/completed` 的错误码、恢复建议、执行状态、状态与耗时都先读取字段，再在缺失时删除旧值，错误码与恢复建议只接受字符串；结果摘要按「结果摘要 → 错误正文 → 状态 → 已结束」回退；大结果按内联、引用、省略三路投影，互斥且各自清理另一个字段；运行中文案区分等待审批、排队、未获批准与正在执行。自动批准要求同一审批通知、已记住该工具、内核明确标为非高风险且标识都是非空字符串。反向断言恢复建议不得跳过字符串校验直接透传，错误码与恢复建议必须在缺失时清除旧值，自动批准不得省略高风险判定。检查是源码字面量与首次出现顺序扫描，不渲染 React 节点。

### `check_harness_replica.py`

`scripts/check_harness_replica.py` 核对 `harnessReplica.ts` 删除会话后的在途恢复抑制：删除通知只接受非空字符串标识，先登记删除记号，再按会话清理世代、在途读取、游标、失败记录与前缀匹配的条目版本；删除分支不得整表清空条目版本。`ingest` 与 `apply` 丢弃已删除会话的事件，`current` 校验把删除记号与世代一起比较，`resume` 对已删除会话直接返回空结果。连接重置依次清空世代、条目版本与删除记号，其他会话不受影响。检查是源码字面量与首次出现顺序扫描，不建立连接。

### `check_session_error_notice.py`

`scripts/check_session_error_notice.py` 核对 `session/error` 通知：`threadId` 必须是非空且不超过 200 的字符串；`message` 缺省或 `null` 时回退通用文案，字符串折叠空白、按 600 码点用 `safeSlice` 截断并补省略号，其他类型整条丢弃；结果只含 `threadId` 与 `message`。反向断言不得直接按 UTF-16 码元切正文、空白正文必须回退通用文案、多余字段不得进入结果。检查是源码字面量扫描，不渲染 React 节点。

### `check_alias_migration.py`

`scripts/check_alias_migration.py` 核对旧显示名称迁移：计划只遍历当前会话列表并按会话去重，缺失别名的会话跳过；非字符串、空白或与内核标题一致的别名只删除；名称按 `Array.from` 码点计数，超过 500 或单次已列 50 条时跳过；迁移项保存会话与去空白后的名称。反向断言不得遍历别名键、不得按 UTF-16 码元判长、空白或同名别名不得发起写入。检查是源码字面量扫描，不读取本机偏好。

### `check_queue_retry.py`

`scripts/check_queue_retry.py` 核对暂停队列项的重试条件与原因文案：只有 `followUp` + `paused` 且未去重的项可重试；`TURN_START_FAILED` 要求 `inputPersisted === false`，归档、回合未完成与摘要失败要求 `!== true`；文案按「去重 → 输入已写入 → 可重试」顺序返回，转向消息与非 `followUp` 早退，未知原因不声称可重新排队。反向断言去重与输入已写入在各分支最先拦截、`TURN_START_FAILED` 只出现两次。检查是源码字面量扫描，不调用内核。

### `check_clipboard_copy.py`

`scripts/check_clipboard_copy.py` 核对剪贴板写入与反馈：`copyText` 先检查 `navigator.clipboard.writeText`，系统写入成功才返回 `ok: true`；失败原因只取错误消息、按 80 字符截断，为空时回退固定文案，且不包含被复制正文；`useClipboardCopy` 用版本令牌丢弃迟到回执，计时器到期、重置与卸载都会清空反馈。反向断言失败原因不得拼接正文、迟到回执不得恢复提示、版本令牌必须在卸载与重置时推进。检查是源码字面量扫描，不访问真实剪贴板。

### `check_home_draft.py`

`scripts/check_home_draft.py` 核对首页草稿的填充意图与技能并入：正文、附件、已选技能、正在读取附件与提交中都算「有未发送内容」；模板只有在读取或提交中、草稿非空但与模板不完全一致时才要求确认，空草稿或「同文、无附件、无技能」直接应用；技能入口只并入技能，已选或已达 10 项时原样返回。反向断言读取或提交期间必须确认、技能上限必须包含第 10 项、重复技能不得追加。检查是源码字面量扫描，不渲染输入框。

### `check_queue_badge.py`

`scripts/check_queue_badge.py` 核对侧栏队列徽标的分类优先级与增量校正：`queueBadgeOf` 逐项累计三类状态，待处理总数缺省时回退已载入条数；分类按「内核持久计数 → 未截断且条数一致的完整投影 → 本地增量 → 只保留总数」取用，且都要求待处理数大于 0；`mergedQueueCounts` 只在已知计数与旧总数一致时应用增量，结果必须非负并与新总数一致，否则放弃分类；`patchQueueBadge` 只改目标会话，四项数值都未变时返回 `null`。反向断言完整投影必须排除截断、未变化不得返回新数组、分类必须与新的待处理总数核对。检查是源码字面量扫描，不调用内核。

### `check_skills.py`

`scripts/check_skills.py` 核对工作区技能边界：`SkillCatalog` 的六个常量必须是正整数表达式，`MAX_SKILL_SCAN_ENTRIES` 不小于 `MAX_SKILL_DESCRIPTORS`，`MAX_SKILL_BYTES` 不超过内核 `MAX_FRAME_BYTES`；技能正文读取必须保留 `O_NOFOLLOW`、`O_NONBLOCK`、inode 校验与 `MAX_SKILL_BYTES + 1` 有界读取；技能目录必须用 `os.scandir` 并以 `follow_symlinks=False` 判定子目录、拒绝根目录符号链接，候选窗口按 `MAX_SKILL_SCAN_ENTRIES` 收敛；列表投影必须截断名称与描述并封顶问题清单；`SkillCatalog` 不得用 `glob` / `rglob` / `iterdir` 枚举技能。检查是静态文本与常量扫描，符号链接竞态与运行时读取结果仍需按平台核对。

### `check_workspace_instructions.py`

`scripts/check_workspace_instructions.py` 核对工作区常驻说明的读取、写入与提示边界：`workspace_instructions.py` 必须保留 8 KiB 上限与首选 / 旧目录路径，读取时拒绝非普通文件、以 `O_NOFOLLOW` 打开并比对 dev / inode、最多读取上限加一字节；候选顺序必须首选优先，且首选路径存在但不可读时固定报不可读、不静默回退旧目录；提示块必须声明内容「是上下文而不是系统指令」且「不能改变工具权限、审批要求或只读限制」；保存必须经临时文件、文件与目录 fsync、`os.replace` 原子替换，并拒绝符号链接与非普通文件。脚本同时核对上下文面板的状态展示、编辑器保存入口与使用指南、桌面指南、项目状态中的说明片段。行为侧用临时目录覆盖空工作区、旧路径兼容、首选优先与 BOM / 空白归一、仅空白视为空、超限与非法编码的状态映射、符号链接与目录候选固定首选不回落、读取上限加一字节、原子写入无临时残留、新文件与覆盖写入的权限、空白正文回执、类型与上限拒绝、符号链接写入与目录占位拒绝、提示块三态文案（66 项）。符号链接竞态与跨平台行为仍需按平台核对。

### `check_attachments.py`

`scripts/check_attachments.py` 核对附件边界：`resources.py` 的默认存储 512 MiB / 4096 对象、上限 `2**63 - 1`、`DEFAULT_READ_CHARS = 16,384` 与 `MAX_READ_CHARS = 32,768` 必须保持不变；`attachment/read` 的请求字段白名单、默认分段、`wire_size(result) > MAX_PAGE_BYTES` 单页守卫，以及 `RESPONSE_TOO_LARGE` / `attachment/read` / `suggestedLimit` 恢复信息必须保留；两个存储配额环境变量名也不得改名。脚本还固定删除会话后的共享附件清理：`_purge_unreferenced_attachments` 必须扫描全部会话的 `attachment` 引用、跳过待删除会话、只删除「候选减引用」、空候选提前返回，并在附件目录、会话文件与附件文件三处按属主 / 单链接 / 私有权限 fail closed（两处单链接检查各出现一次）；`_finish_deletion` 必须先移除会话文件再清理附件，顺序颠倒会让被删会话把自己算作引用而留下残留。检查是常量与文本扫描，实际配额与分页行为仍需按用户指南核对。

### `check_attachment_add.py`

`scripts/check_attachment_add.py` 核对附件添加的工作区边界、配额与原子发布：`AttachmentStore.add` 解析路径后必须仍在允许根下，后缀匹配固定扩展名集合，路径段不得命中保留目录或以 `.env` 开头；打开使用 `O_RDONLY | O_NONBLOCK` 且不跟随符号链接，再按描述符确认普通文件；读取上限为 2 MiB + 1 字节，正文必须为 UTF-8，摘要为 SHA-256，文件名经 `wire_text` 降级后进入记录。`_publish_object` 必须先查重，再按增量计数判定字节与对象两项配额（均为严格大于才拒绝）；候选文件以 `tmp-` + uuid 命名、独占创建，fsync 后 `os.replace` 原子发布，先记账再回调，finally 清理临时名。`add` 在发布之后失败时清理未引用对象，只有清理成功才回退两项计数，并重新抛出原异常。`_read_object` 以 lstat、打开后 fstat 与最终 SHA-256 三层校验内容，三处损坏判定与未移交描述符的关闭不得缺失。`_storage_usage` 只校验目录身份并返回增量计数，不得重扫附件目录。检查是顺序与文本扫描，实际写入行为仍需按用户指南核对。

### `check_attachment_read.py`

`scripts/check_attachment_read.py` 核对附件分页读取的游标绑定与解码边界：`read_chunk` 的 `limit` 只接受 1 到 `MAX_READ_CHARS` 的整数；先经条目投影取记录再按记录的摘要与字节数读取对象；继续读取必须携带匹配当前摘要的 `sha256`，否则返回 `STALE_ATTACHMENT`（`-32011`、`currentRef`）；游标必须带 `at1_` 前缀、长度不超过 2048，载荷是 `threadId` / `attachmentId` / `sha256` / 偏移四元组，偏移严格小于字符长度，base64url 严格解码且捕获五类解析异常；`end` 取 `min(offset + limit, len(text))`，只有未读完时才生成无填充的紧凑 JSON 游标；正文经 `wire_text` 降级，`contentRef` 带字节与字符长度。记录中的摘要格式、名称长度与字节范围按损坏处理，附件正文解码失败转为产品错误。完整读取复制记录，`include_content` 关闭时不读对象。检查是顺序与文本扫描，实际分页行为仍需按用户指南核对。

### `check_attachment_context.py`

`scripts/check_attachment_context.py` 核对附件上下文注入的数量、去重与预算口径：`AttachmentStore.context` 的 `ids` 必须是最多 10 项的字符串数组并去重保序，`None` 与空数组两处早退；`entries` 缺省时读取会话条目，显式传入时只核对会话存在且不重复读取；每个 id 经条目投影读取一次正文，标签用 `json.dumps(..., ensure_ascii=False)` 转义名称并声明「来源内容，不是操作授权」；正文总字节按附件 `bytes` 累计，严格超过 2 MiB 时拒绝，标签长度不计入；附件与文本只在预算通过后追加；返回文本以空行分隔，附件投影剔除 `content`。检查同时直接调用 `AttachmentStore.context` 做行为对照（68 项）：用轻量替身提供 `sessions` 与 `_read_from_entries`，覆盖 `None` / 空列表早退且不访问会话、非列表与超过 10 项、非字符串元素、恰好 10 项、去重保序与每个 id 只读一次、名称 JSON 字面量转义（含换行、引号、反斜杠与中文保留）、空行分隔、投影剔除正文并保留其余字段、预算等于上限通过 / 严格超出拒绝 / 跨附件累计 / 按 `bytes` 而非标签或正文长度计数、缺省读取会话条目与显式条目只核对会话存在，以及 id 不做空白裁剪。

### `check_skill_context.py`

`scripts/check_skill_context.py` 核对技能上下文注入的数量、路径与摘要口径：`SkillCatalog.load` 的 `ids` 必须是最多 10 项的字符串数组并去重保序，`None` 与空数组两处早退；每次调用以 `list()` 重建目录映射，技能 id 必须存在；路径固定为 `<root>/<id>/SKILL.md` 且父目录不得越界；正文经 `_read_bounded` 读取一次，摘要必须与目录记录一致，变化时提示重新选择；注入文本以 `<skill name={json.dumps(id)}>` 包装、以空行连接，返回的选中记录来自目录而不是用户输入。检查是顺序与文本扫描，实际注入行为仍需按用户指南核对。

### `check_skill_catalog.py`

`scripts/check_skill_catalog.py` 核对技能目录枚举的有界窗口与截断标记：`_candidate_paths` 拒绝符号链接根，缺失根与缺失目录两处返回空，非目录与扫描失败如实报错，`follow_symlinks=False`，窗口只保留字典序更小的候选并用 `dropped` 记录替换；`scan` 以 `limit = MAX_SKILL_DESCRIPTORS` 起步、翻倍且不超过 `MAX_SKILL_SCAN_ENTRIES`，代理项 id 转 `repr` 截断 200、超长 id 截断后归入问题清单，`_read_bounded` 失败时给出 `_problem_reason`，有效技能经 `_descriptor` 投影；`exhausted` 由 `dropped` 决定，`fulfilled` 要求两份清单都达到上限，问题清单截断到 `MAX_SKILL_DESCRIPTORS`，`skillsTruncated` / `problemsTruncated` / `candidatesTruncated` 只在各自条件出现；`_problem_reason` 覆盖文件缺失、两处不可读、两处超限、非 UTF-8 与兜底；`list()` 只投影扫描结果。检查是顺序与文本扫描，实际枚举行为仍需按用户指南核对。

### `check_skill_write.py`

`scripts/check_skill_write.py` 核对技能创建、替换与删除的独占、原子与摘要口径：`create` 要求 `SKILL_ID` 规则、非空且不超限的 UTF-8 正文、按需创建父与根目录、`mkdir` 独占目标、重复时拒绝覆盖、写入失败回退空目录、技能目录 → 根 → 父目录依次 fsync；`_write_atomic` 以 `.SKILL-*.tmp` 临时文件写入、fsync、`chmod 0644`、`os.replace` 发布并 fsync 目录，失败清理临时文件且清理失败不影响原异常；`replace` / `delete` 先校验 id、正文与摘要格式，再确认根与技能目录均为普通目录，`_read_bounded` 的当前摘要必须与调用方一致，替换经原子写入，删除要求目录恰好只有 `SKILL.md` 并先 unlink 后 rmdir；`_existing_id` 拒绝点目录、路径分隔符、控制字符与超长 id。检查是顺序与文本扫描，实际写入行为仍需按用户指南核对。

### `check_skill_descriptor.py`

`scripts/check_skill_descriptor.py` 核对技能 frontmatter 解析与列表投影的截断口径：`_fields` 先去除 BOM 再按行解析，起始行 `strip()` 后必须恰为 `---`，结束行只认整行 `---`，仅解析两者之间的行，字段白名单只有 `name` / `description`，值去除包裹引号；`_descriptor` 以 `fields.get` 提供缺省值（名称回退技能 id、描述为空串），投影包含 id / name / description / digest / bytes，名称超过 200 字符、描述超过 500 字符时截断并分别写 `nameTruncated` / `descriptionTruncated`，先截断再标记，未超限不写标记。检查是顺序与文本扫描，实际投影行为仍需按用户指南核对。

### `check_hooks.py`

`scripts/check_hooks.py` 核对生命周期 hook 的超时、上下文冻结与策略拒绝边界：`hooks.py` 的 30 秒 / 250ms 超时、256 事件队列、16 在途回调、每秒一次的拥塞诊断、观察上下文 16 384 字符 / 64 键 / 128 项 / 深度 6、策略上下文 1 052 672 字节 / 32 784 节点 / 深度 66 与 512 个变换单元；`HookDecision` 的布尔允许、大写 code 与 1 024 字符消息校验、`ContextTransform` 的非负整数与排序去重；`_safe_value` 必须截断、脱敏并标注省略，`freeze_context` 冻结为只读视图，`freeze_policy_context` 必须完整复制并在环引用、代理项、非有限浮点与超限时分别以 `HOOK_CONTEXT_INVALID` / `HOOK_CONTEXT_TOO_LARGE` 拒绝；事件观察只投影白名单字段，队列满时计数丢弃而不阻塞；`_invoke` 必须先检查取消再检查关闭与容量，超时使用 25ms 轮询且迟到返回不改写回合；策略与请求路径必须把 `HOOK_CLOSED` / `HOOK_CONTEXT_TOO_LARGE` / `HOOK_CONTEXT_INVALID` / `HOOK_BUSY` / `HOOK_ERROR` / `HOOK_RESULT_INVALID` 映射为拒绝；`transform_context` 不得省略当前单元，`after_tool_call` 只观察且仅在 `expose_tool_results` 时附带结果；关闭时限内未收尾时报告 `HOOK_TIMEOUT`。脚本同时核对技术参考的队列、在途上限、策略上限与超时说明。检查另在临时合成数据上执行上下文场景：策略副本完整、只读且不脱敏，观察副本脱敏、截断、键项与深度省略，字节 / 节点 / 深度边界分别接受与拒绝，环引用、非字符串键、代理项、非有限浮点、不支持类型与非映射顶层分别报告 `HOOK_CONTEXT_INVALID`；宿主回调线程、超时与关闭行为仍按用户指南核对。

### `check_persistence.py`

`scripts/check_persistence.py` 核对 SQLite 投影索引的迁移、私有权限与连接边界：`persistence.py` 的 `SCHEMA_VERSION = 2`、文本列 `utf-8` 宽容解码（非法字节替换为 U+FFFD，避免损坏行变成内部错误）、私有目录与索引文件 / WAL / SHM 的权限收紧、`version > SCHEMA_VERSION` 拒绝、1 → 2 迁移顺序与 `user_version` 写入、`UPDATE threads SET indexed_size=-1` 的旧索引失效标记；表结构必须保留会话、回合、事件、审批与 checkpoint 的主键及 `ON DELETE CASCADE`；每个操作独占连接并启用 `foreign_keys`、`busy_timeout=10000`、`synchronous=FULL`，事务以 `BEGIN IMMEDIATE` 开始并在异常时回滚；事件索引 `events_method_cursor` 必须存在。脚本反向断言不得使用严格 `decode("utf-8")`，并核对技术参考与使用指南的「日志是事实源、SQLite 是可重建索引」口径。

同一脚本固定投影内容版本：会话投影只在会话文件的大小或修改时间变化后重建，投影新增派生字段时已有会话不会自动获得。`session.py` 的 `THREAD_PROJECTION_VERSION` 记在 `checkpoints` 表的 `threadProjection` 行，不并入 `SCHEMA_VERSION`（结构没有变化，旧版本仍能打开同一状态目录）。启动时在恢复未完成的删除之后、刷新会话之前比对一次：记录缺失或不同就按字节查找位置记录的类型标记（紧凑与带空格两种写法，1 MiB 分块并保留跨块尾部，不解析日志），只让命中的已索引会话失效，再在同一事务写回版本；文件已不存在的行跳过，读取失败的行按需要重建处理。失效函数只在构造时调用一次，失效语句必须限定到具体会话，不得整库失效。工具数据里出现同样片段只会多重建一次，重建结果仍由解析后的条目决定。重建中途退出时这些行保持失效，下次启动继续。检查是常量与顺序扫描，实际索引行为仍需按用户指南核对。

### `check_session_log.py`

`scripts/check_session_log.py` 核对会话 JSONL 的编码、严格解码与有界快照：单行上限 32 MiB，编码为 `ensure_ascii=False` 的 UTF-8 且以换行结尾，写入前按字节判定上限；线程 id 为 12 位十六进制，标识为 1–128 位受限字符，事件 id 为 32 位十六进制，附件摘要为 64 位十六进制。解码使用重复键、非法常量与非有限浮点钩子，并在返回前拒绝孤立代理项；损坏行按行号停止读取。会话头只允许出现在第 1 行，重复出现即停止；其余记录要求 `type` / `id` / `timestamp` 为字符串、`parentId` 为字符串或 null、`payload` 为对象。有界读取按 64 KiB 分块，累计与单行分别检查上限，末尾无换行的残段只丢弃；快照长度在写入锁内收敛到最后一个完整记录边界，缺失边界或残段超限时按固定说明拒绝；追加前截掉残段并 `fsync`，读取上限 + 1 字节后超限拒绝；快照按固定字节范围、通用换行与逐行 `_decode_session_record` 解码，空行跳过。脚本反向断言不得把残段作为记录产出、不得转义非 ASCII。检查另用临时文件与内存流执行编码、严格解码、有界读取、快照边界与追加前截断：完整行与残段丢弃、单行与残段超限、快照长度恰等与不完整、CRLF、重复会话头与各类坏行；真实追加并发仍按用户指南核对。

### `check_exact_read.py`

`scripts/check_exact_read.py` 核对会话日志精确读取原语 `_read_exactly_at`：偏移固定用 `SEEK_SET`，循环读取直到取满请求长度，空块抛「会话日志读取不完整」，绝不返回部分数据；同一描述符上的多次调用按各自偏移重新定位。行为侧打开真实临时文件，覆盖中段与跨换行读取、整文件、开头 / 末尾 / 越界零长度、空文件、读取后文件位置落在 offset + length、两次调用复位、末尾与远端越界及超长读取的 `OSError`、失败后描述符仍可复用；源码扫描定位、循环、空块拒绝、按实际字节递减、拼接返回与唯一返回点，反向断言不预读、不截断、不写入。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_delete_intent.py`

`scripts/check_delete_intent.py` 在临时目录构造 `SessionStore`，核对 `.delete-<threadId>.json` 删除标记：写入返回 `version` / `threadId` / `attachmentDigests` / `eventId` 四键，摘要去重排序并忽略非法项，事件编号为 32 位十六进制，标记为 `0600` 私有文件且不残留临时文件；已存在时读回而不覆盖；阻塞列表只来自标记名称。损坏标记（非 JSON、非对象、版本或会话不符、额外字段、摘要或事件编号非法、超大文件）全部以固定说明拒绝，重启后保留并继续阻塞，合法标记重启后完成删除且保留其他会话。脚本同时扫描源码固定 `_read_delete_intent` 的两处拒绝与排序去重、`_write_delete_intent` 的独占临时文件与 `os.link` 发布、`_pending_deletion_ids` 只按名称、`_recover_deletions` 的保留语义，以及初始化收紧标记权限与完成删除时的删除顺序；反向断言写入不使用 `os.replace`、阻塞列表不读取内容、移除标记后才刷新目录。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录，不读取用户状态目录。

### `check_delete_cleanup.py`

`scripts/check_delete_cleanup.py` 在临时目录构造 `SessionStore`，核对删除会话时的私有文件清理：临时文件必须是当前用户拥有的普通文件，链接计数为 2 时必须确认目标文件也是同一 inode 的私有普通文件，其余链接计数一律暂停；删除前收紧权限（硬链接共享 inode，目标随之一并收紧），删除后刷新目录。普通与缺失临时文件被安全处理，目标缺失、不同 inode、三重链接、符号链接与目录全部拒绝且不删除。`_remove_thread_files` 先清理会话临时文件、删除标记临时文件与事件日志临时文件三类残留，再删除链接计数为 1 的会话主体；主体缺失时直接返回，硬链接与符号链接主体被拒绝。脚本同时扫描两类清理的所有者、普通文件、链接计数、同一 inode、权限收紧、三类临时文件与刷新目录；反向断言临时文件先于主体、主体检查恰好一处拒绝。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_repair_backup.py`

`scripts/check_repair_backup.py` 在临时目录构造 `SessionStore` 与备份目录，核对删除会话时的修复备份清理：`repairs/` 目录与递归发现的 `state.sqlite3`、`-wal` / `-shm` sidecar 都必须是当前用户拥有的私有普通文件；数据库版本不得高于 `SCHEMA_VERSION`，在事务内只删除该会话的 events / turns / threads 行，`VACUUM` 后截断 WAL；存在 `manifest.json` 时过滤两个 sidecar 条目、按实际文件更新数据库条目的 bytes 与 sha256，以独占临时文件加 `os.replace` 发布并刷新目录。行为侧覆盖无备份目录、目录不可信、多备份目录与嵌套目录、目标会话删除与其他会话保留、空库与恰好当前版本、较新版本拒绝且不改行、数据库与 sidecar 的硬链接 / 符号链接拒绝、清单损坏与非 UTF-8 与格式无效、清单过滤与摘要更新、清单缺失不创建、数据库与清单权限收紧。sidecar 用例用 WAL 模式并保持连接，避免 SQLite 在关闭时提前清理 sidecar；清单中存在数据库条目时 `_sha256_file` 也会收紧数据库权限，独立权限断言放在无清单用例。脚本同时扫描所有权、版本守卫、事务与回滚、`VACUUM`、WAL 截断、sidecar 清理、清单捕获与格式、过滤与更新、独占临时文件与原子替换、两处目录刷新；反向断言不删除清单本身。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_event_page.py`

`scripts/check_event_page.py` 在临时目录构造 `SessionStore`，核对事件回放的游标分页：追加帧的游标从 1 严格递增并携带 32 位事件编号，首页按 `limit + 1` 报告 `hasMore` 与最后一条游标，续页、空页与 `latest_event_cursor` 保持游标推进；`threadId` 与 `methods` 筛选、`limit` 与游标校验、保护字段、方法名与参数形状都被固定；写入删除标记后该会话事件从回放中过滤，索引行被篡改时从 `events.jsonl` 重建并重试，重启后完成删除会剔除该会话事件并追加 `thread/deleted`。脚本同时扫描 `events_after` 的 `limit + 1`、删除标记注入、重建重试与 `nextCursor`，`_event_rows` 的原始字节预算与首行特例，`_event_page_entries` 的四类索引损坏与 `method` 类型，以及 `append_event` 的保护字段与落盘顺序；反向断言只在条数与字节两处截断。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_event_rewrite.py`

`scripts/check_event_rewrite.py` 在临时目录构造 `SessionStore`，核对删除会话时的事件日志重写：源日志必须是私有普通文件，打开后设备与 inode 必须与可见路径一致，写入后再复核九元组签名；逐行校验事件帧、游标与事件编号唯一、会话编号合法，只丢弃目标会话的事件，匹配恢复标记的删除事件必须恰好一条且形态正确，缺失时按高水位加一生成；临时文件独占创建并以硬链接或替换发布，最后刷新目录。行为覆盖删除重写保留其他会话与无会话事件、游标自增、重复删除返回同一事件、预置删除事件复用、冲突拒绝、损坏 / 重复游标 / 重复事件 / 非法帧 / 非法会话编号拒绝、符号链接日志拒绝、缺失日志新建，以及 `_event_high_water` 取最大游标与 `_previous_deletion_event` 的两类损坏跳过与按会话匹配。脚本同时扫描重写的校验顺序、去重集合、签名复核、发布分支与落盘，以及两个辅助方法的取数与跳过；反向断言三类变化拒绝、两类格式拒绝、硬链接与替换各一次。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_thread_meta.py`

`scripts/check_thread_meta.py` 在临时目录构造 `SessionStore`，核对会话元数据更新：`project_id` 规范化为 `projectId` 且重复提供被拒绝，白名单恰好 `title` / `projectId` / `provider` / `model` / `cwd` / `toolPolicy` / `reasoningEffort` 七个字段，身份与归档字段不可改写；`toolPolicy` 与 `reasoningEffort` 用固定枚举，`title` 上限 500、`projectId` 上限 200、`provider` 非空且无空白，`cwd` / `model` 类型与 `null` 均被覆盖；空更新不写记录，归档与恢复只在状态变化时各写一条并幂等，两个别名与完整方法一致。脚本同时扫描 `_validate_changes` 的规范化、白名单、逐字段校验与序列化位置，以及 `update_thread` / `archive_thread` / `unarchive_thread` 的写入门槛；反向断言白名单恰好七个字段、规范化先于白名单、序列化校验在逐字段校验之后。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_thread_page.py`

`scripts/check_thread_page.py` 在临时目录构造 `SessionStore`，核对会话列表分页：按更新时间倒序、相同时间按会话编号倒序，续页与 `nextCursor` 只在确有下一页时返回，恰好一页与空库不返回游标；归档与项目筛选各自精确匹配，`archived` / `projectId` 绑进分页游标范围，跨范围复用游标被拒绝，非法游标分别以「游标无效」与「会话分页游标无效」拒绝；`limit` 上限 200、布尔与浮点被拒绝且校验先于筛选；待删除标记在分页与旧列表接口中都被过滤。损坏投影行必须从候选窗口之外继续取行并登记为不可读，不得吃掉翻页余量；投影损坏但源日志完好时重建返回，`updated_at` 被外部改写为 BLOB 时同样重建而不是把内部错误送给调用方；超长标题与项目编号截断到 500 / 200 并带标记，不改写会话编号。脚本同时扫描 `list_threads_page` 的入参校验、参数绑定、双列游标、`skip` 重建重试与 `nextCursor` 条件，以及 `_thread_metadata` 的五处结构损坏信号与两处截断；反向断言排序恰好一处、项目筛选走参数绑定、日期解析在 `try` 内。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_turn_phase.py`

`scripts/check_turn_phase.py` 在临时目录构造 `SessionStore`，核对回合阶段与失败回合收尾：`record_task_phase` 的最小记录只含 `taskId` / `ownerKind` / `phase` / `status` / `attempt` / `restartLimit`，恢复原因与恢复策略只在提供时写入；任务编号标识符、五个阶段、`_TERMINAL` 加 `running` 的状态、`attempt` 1–1000、`restartLimit` 0–32、可选文本 256 字符与两组枚举都被固定。`_abandoned_item_payload` 剥离 `id` / `threadId`、状态恒为 `failed` 并指向原条目，待决审批结算为 `expired` 且保留原字段，工具调用在 `queued` / `pending_approval` / `approved` / `not_approved` 下按「未执行」、其余按「结果不确定」处理。`settle_abandoned_turn` 只结算属于该回合的 `running` 条目与待决审批，其他回合与已终态条目不动，多条逐条结算且重复调用幂等。脚本同时扫描三个阶段方法的固定字段、枚举与顺序；反向断言阶段记录恰好一条、在线结算只有状态与归属两处跳过、计数恰好一次。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_turn_page.py`

`scripts/check_turn_page.py` 在临时目录构造 `SessionStore`，核对回合分页：按 `first_ordinal` 升序、相同序号按回合编号升序，续页与 `nextCursor` 只在确有多取一行时返回，空回合返回空页；游标绑定 `{"threadId"}` 范围，键必须是整数序号加合法回合标识符，十类非法键分别以「回合分页游标无效」或「turnId 格式无效」拒绝，跨会话与跨种类游标被拒绝，前缀、编码与超长按「分页游标无效」拒绝；`limit` 上限 200、布尔与浮点被拒绝，会话格式与不存在会话各自报错。`first_ordinal` / `turn_id` 被外部改写为 BLOB、`metadata_json` 被改写为非对象时，分页按会话重建后恢复返回，而不是把内部错误送给调用方。脚本同时扫描 `list_turns` 的游标种类、双列比较、多取一行、索引刷新与两处类型守卫，以及 `_turn_metadata` 的两处损坏信号；反向断言单会话读取不带跳过集合、损坏信号读取 `thread_id` 而不是条目 id。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_summary_issue.py`

`scripts/check_summary_issue.py` 核对分支摘要合法性 `branch_summary_issue` 的固定原因、上限与判定顺序：正文必须是非空字符串且不超过 32000 字符；`targetTurnId` 可以缺省，但提供时必须是参考分支位置表里的字符串；`abandonedTurnIds` 必须是 1 到 200 个、单个最多 128 字符、总长最多 4096 字符的字符串列表；`sourceTextDigest` 与 `summaryJobId` / `fromTurnId` 只在提供时有界（128 字符）。六类中文原因按正文类型、空正文、正文超限、目标回合、放弃列表、来源摘要、辅助标识的顺序返回第一条；来源摘要与辅助标识为空时放行。脚本按顶层函数切片做顺序断言，行为侧直接调用纯函数覆盖各上限的恰好通过 / 超限拒绝、空位置表、七组多错误优先级，并确认载荷不被改写；内核抛出的意外类型异常折算为检查失败原因。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，不访问网络、模型或招聘平台。

### `check_recovery.py`

`scripts/check_recovery.py` 核对启动恢复 `recover` 的阶段收尾、条目结算与回合中断口径：必须遍历含归档的全部会话，无法读取的损坏会话跳过且不阻断其他会话；按每个任务最新的 `task_phase` 归并，已终态回合补 `terminalStateRecovered` / `closed` 收尾，未终态回合写 `processExit` / `manual` 中断；仍为 running 的条目或失效审批按 `_abandoned_item_payload` 结算为失败修订，并把受影响回合改为 `interrupted`。结构侧按顺序扫描归档遍历、损坏跳过、最新阶段归并、两种收尾、两条阶段记录、条目结算与回合中断，反向断言各条原因与错误码文案、调用次数及审批截止时间判据固定。行为侧在临时目录构造 `SessionStore`，覆盖 running 回合与阶段的中断收尾、已终态回合只补终态收尾、已收尾阶段幂等、运行中条目结算、已完成条目与未知回合跳过、损坏会话不阻断其他会话、归档会话同样恢复。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，不访问网络、模型或招聘平台。

### `check_session_batch.py`

`scripts/check_session_batch.py` 核对会话写入路径的批量追加、新建发布与附件引用顺序：`append_many` 先校验批次是 `Entry` 列表与 `maximum_bytes` 是正整数，空批在编码与事务之前早退，整批只编码一次；事务内在写入前后各刷新一次索引投影，末尾缺换行时按 1 字节前缀计入上限，超过上限抛 `SessionSizeLimitExceeded`。`append` 在同一事务内 require → 刷新 → 写一行 → 再刷新，不得委托批量路径。`_write_new` 把会话头与初始条目一次编码到以 `.tmp` 结尾的临时文件，`fsync` 后用 `os.link` 发布，`finally` 清理临时名，不得使用覆盖式发布。`append_attachment` 先在快照上逐行读取完整历史拒绝损坏会话，再发布内容并 `fsync` 附件目录，最后写一行引用并刷新索引；摘要必须匹配 64 位十六进制。`cleanup_unreferenced_attachments` 只在写锁与索引事务内委托 `_purge_unreferenced_attachments`，不得内联删除；临时清理只匹配 `tmp-` 加 32 位十六进制，删除后 `fsync` 目录。脚本反向断言调用次数、严格大于的上限、编码不得进入事务等。检查是 AST 切片与顺序扫描，不执行写入或清理，运行时行为仍需按用户指南核对。

### `check_checkpoint_publish.py`

`scripts/check_checkpoint_publish.py` 核对摘要 checkpoint 的原子发布：`SessionStore.append_checkpoint` 先校验两个回调可调用，并在写锁与索引事务内对源日志做 lstat 与已打开描述符的九字段双重签名；源必须是当前用户拥有的普通单链接文件。条目工厂在锁内只调用一次，并且必须构造 `context_checkpoint`。候选文件固定为 `.checkpoint.tmp`、`O_EXCL` 独占创建、按 1 MiB 分块复制；末尾缺换行时只截到最后一个完整记录边界，找不到边界即拒绝发布；追加编码条目后固定 `0600`、继承源 gid 并 `fsync`。复制完成后的源 fstat、候选 lstat 与发布前源 lstat 必须分别等于原始签名；`os.replace` 是唯一提交点，替换异常按可见 inode 区分「原始未变 → 重抛」「候选 → 已提交」「其他 → `CheckpointCommitUncertain`」。提交成功后固定顺序为目录 fsync → `on_committed` → 索引刷新；已提交后的任何异常转换为 `CheckpointCommittedError`，未提交原样抛出，临时文件在 finally 清理且清理失败被吞掉。脚本反向断言提交点唯一、条目工厂只调用一次、不走追加路径、`CheckpointCommitUncertain` 四处身份判断。检查是 AST 切片与顺序扫描，不执行复制或替换，运行时行为仍需按用户指南核对。

### `check_entries_cache.py`

`scripts/check_entries_cache.py` 核对会话读取缓存与增量解析：`read_entries` 在写锁内以 `(size, mtime_ns, ino)` 命中缓存并返回副本，未命中时 `_appendable_entries` 只接受同一 inode、严格更短（`0 < size < 新 size`）且旧前缀末尾为换行的缓存，命中后同样移到最近使用；否则 `_read_all_entries` 从 0 开始按快照字节数设限、行号从 1 开始。增量路径从旧前缀末尾起只读新增范围，行号以 `line_count + added` 接续。只有 `_line_boundary` 成立（非空且最后一字节为换行）才 `_store_entries`，缓存先移除再插入，超过 4 个会话时按最久未用淘汰。`read_entries_snapshot` 在锁内查缓存、锁外解码快照，随后复核当前 stamp 等于快照 stamp 才写缓存；缺失或损坏时为不缓存。脚本反向断言读取路径不直接操作缓存、两处返回值都是副本、空文件不缓存。检查是 AST 切片与顺序扫描，不执行读取，运行时行为仍需按用户指南核对。

### `check_settings.py`

`scripts/check_settings.py` 核对自动压缩设置的有界读取、原子写入与持久边界：`settings.py` 的 `config.json`、三个自动压缩字段、256 KiB 与深度 64 上限；读取只经 `open_private_file` 的私有描述符，确认 `S_ISREG`，只读到上限 + 1 字节并在多出时按不可读处理，`json.loads` 的 UTF-8 解码与宽泛异常收敛为默认值，结果必须是深度受限的 JSON 对象；保存前必须验证三个字段齐全，已存在但不可读的配置拒绝覆盖；序列化使用 `ensure_ascii=False` 保留无关键，编码异常、孤立代理项与超限分别收敛为可读中文错误；写入必须经 `tempfile.mkstemp`、`fsync` 文件、`os.replace` 与目录 `fsync`，异常时清理临时文件。脚本按首次出现顺序核对 fsync → replace → 目录同步，并反向断言不得使用 `read_text` / `write_text`；同时核对技术参考与使用指南的设置口径。检查另用临时状态目录执行 `_within_depth`、`_read_object`、`load_auto_compaction` 与 `save_auto_compaction`：深度边界、缺失 / 非对象 / 损坏 / 非法 UTF-8 / 超限 / 深层配置回退、合法与部分字段加载、无关键保留、各类拒绝与临时文件清理；真实掉电时序仍按用户指南核对。

### `check_snapshot_store.py`

`scripts/check_snapshot_store.py` 核对冻结快照的预算、发布与读取边界：`snapshot_store.py` 的十条预算常量；快照库文本的 `utf-8` 宽容解码、条目载荷与 id 的损坏校验；单条记录 32 MiB 与源文件 1 GiB 上限；构建器的私有建库、`max_page_count` 余量、条目与队列共享的内容预算、重复 id 保留首条与先保存修订目标再清理载荷；构建取消每 128 行、叶过滤、磁盘预算与悬空编辑拒绝；临时 `.building` 文件完成后 `os.replace`、收紧权限并同步父目录，成功后登记缓存与 TTL，失败清理临时与最终文件；读取的视图 / 游标 / 载荷预算 / 编辑状态校验；叶失效墓碑与缓存淘汰；关闭时失效在途构建并清理残留文件。反向断言禁止严格 `utf-8` 解码、裸 `unlink`、`shutil.rmtree` / `os.remove` 与 NaN 序列化；同时核对技术参考与使用指南的快照口径。脚本只扫描源码，不证明运行时快照已落盘。

### `check_turn_limits.py`

`scripts/check_turn_limits.py` 核对回合模型请求上限的严格整数与有界解析：`turn_limits.py` 的默认 6 次与最大 64 次；`model_request_limit` 只接受精确整数并限定 1 到宿主上限，布尔值按非法拒绝；环境变量先去首尾空白、空值回退默认值，再按最多两位的十进制文本形态判定，转换失败与格式错误统一使用固定说明。反向断言禁止错误回显原值；同时核对技术参考与使用指南的回合上限口径。除静态扫描外，脚本直接调用 `model_request_limit` 覆盖 1 / 64 边界、自定义 ceiling 与布尔 / 浮点 / 字符串 / None 的拒绝，并在保存与恢复 `BOSS_HARNESS_MAX_MODEL_REQUESTS` 的前提下核对未设置、空值 / 空白、首尾空白、前导零、超长、符号 / 小数 / 字母、越界值与不回显原值的错误文案，共 59 项。

### `check_output_budget.py`

`scripts/check_output_budget.py` 核对模型输出的字节预算、有界错误与 UTF-8 分块：`output_budget.py` 的工具参数、响应工具参数与文本 / 思考三项上限均为 1 MiB；`utf8_size_at_most` 必须先按码点数预检、再编码并核对字节上限，孤立代理项抛固定异常；快照必须按紧凑 JSON（`ensure_ascii=False`、`allow_nan=False`）逐字符计费，拒绝非文本键与超过 64 层 / 32768 节点的结构，整数按位长预判；`bounded_error` 不得拆开 UTF-8 字符，截断处以 `…` 收尾；`utf8_chunks` 要求最小 4 字节上限并按字符累计分块。反向断言禁止 `allow_nan=True`、`ensure_ascii=True` 与无选项的 `json.dumps(value)`；同时核对技术参考的 1 MiB 与 32 KiB 口径。行为侧直接构造预算对象：覆盖尺寸预检与非法 Unicode、逐次计费与本地 / 总量上限、快照的紧凑编码与转义、代理项 / 非文本键 / 非 JSON 值 / 深度 / 节点 / 整数位长拒绝、`reconcile` 高水位、响应文本的分隔符拼接与完整响应取最大、诊断截断不拆字符、分块对齐与重组（124 项）。实际分配与截断行为仍需按技术参考核对。

### `check_stream_pump.py`

`scripts/check_stream_pump.py` 核对异步流泵的缓冲预算、终止事件与线程收尾边界：`stream_pump.py` 的 64 个缓冲事件、4 MiB 合计缓冲、2 MiB 单事件、32768 个节点、8 个在途泵与 1 秒清理等待；文本计费按 4096 字符分块并使用 `errors="replace"`，事件计费覆盖标量、文本、字节、容器与 Pydantic 附加值，循环引用记 0 并受 32 层嵌套限制；发布必须先在入队前计费、超限拒绝，再同时满足事件数与合计字节配额；取消、超时与 producer 失败都必须先丢弃排队事件、只入队一个终止事件，并在锁外取消任务；线程收尾必须依次关闭异步生成器、关闭事件循环、释放名额并置位完成；`close()` 不得 join 当前线程。反向断言禁止非 daemon 线程、严格编码计费、无超时 join 与缺少终止事件槽位的队列。同时核对技术参考的缓冲口径。行为侧直接调用计费函数并构造真实泵：UTF-8 分块与代理项替换、标量 / 容器 / 对象 / Pydantic 额外字段的尺寸、循环与共享引用、深度与节点哨兵、顺序交付与完成停止、取消 / 超时终态、单事件超限与容量拒绝（151 项）。真实并发与线程退出仍需按平台核对。

### `check_errors.py`

`scripts/check_errors.py` 核对模型错误的溢出分类、重试提示与传输诊断边界：`errors.py` 的 provider code 字符集与 128 字符上限、配额 / 临时错误码集合、408/409/500/502/503/504 状态集合、LiteLLM 2048 与代理 512 字符上限、Anthropic prompt / llama.cpp / LiteLLM / 代理正文四条精确文本模式；溢出只接受 OpenAI 精确 `context_length_exceeded`、有界 llama.cpp 文本、HTTP 400 的有界 LiteLLM 窗口拒绝、Anthropic `invalid_request_error` 的有界 prompt 数字上限，以及 HTTP 413 的有界代理正文拒绝；配额耗尽必须不可重试，临时码与状态可重试，400/401/403 不可重试，其余 429 保持未知；传输诊断必须逐层去重遍历因果链、区分 getaddrinfo 命名空间、只输出白名单 errno 与固定中文标签。反向断言禁止宽松类型判定、`search` 代替完整匹配、放开 413 状态与异常原文。同时核对技术参考的溢出与重试口径。行为侧直接构造错误载荷与异常链：来源校验、provider code 白名单与回退、智谱 1308 的字符串 / 整数 / 浮点边界、重试提示的配额优先与裸 429 未知、四条有界文本匹配的空白与长度边界、两家 provider 的溢出组合与显式 `retryable` 覆盖、传输因果链 / errno 白名单 / 抑制上下文 / 固定诊断文案（199 项）。实际分类结果仍需按技术参考与 provider 行为核对。

### `check_continuation.py`

`scripts/check_continuation.py` 核对 Anthropic 私有续接元数据的预算、构造与恢复校验：`continuation.py` 的四个预算常量与 `_anthropicContinuation` 字段名；前缀 digest 必须固定排序并紧凑编码后取 SHA-256；构造只保存文本 / 思考的长度与 SHA-256、签名或 redacted 数据引用与工具调用 ID，单项签名、签名合计、块数与载荷各自有界，redacted 块不得同时带签名或正文；恢复必须精确匹配六个字段与版本 / provider、64 位十六进制前缀与内容 digest、调用 ID 的连续前缀、助手引用与回合归属，拒绝被上下文编辑的助手消息与不可持久调用之后的内容，并逐块校验内容 digest；编码失败降级为普通工具批次，其余字段错配按固定说明拒绝。反向断言禁止 ASCII 转义、MD5/SHA-1 摘要与宽松字段比较。同时核对技术参考的续接元数据口径。行为侧直接构造消息与持久条目：前缀 digest 的排序 / 非 ASCII、正文 / 思考 / 隐藏块描述、单签名 / 合计 / 描述块 / 载荷上限、普通批次与失败结算、恢复的字段与 digest / 调用 ID / 助手引用 / 回合归属 / 尾随内容、编码失败降级（189 项）。真实签名校验仍需按 provider 行为核对。

### `check_turn_continuation.py`

`scripts/check_turn_continuation.py` 核对中断回合续接的预检边界与文档一致性：`_turn_continuation_plan` 的原因码集合必须与「中断回合续接」一节的表格双向一致（当前 28 个，其中 6 个是与其它操作共用的 `THREAD_*` / `KERNEL_*` / `QUEUE_*` / `TURN_*` 门禁码）；运行状态门禁的先后顺序、最新回合与已有续接回合必须按当前分支（`_active_entries`）判定；`turn/continue` 的 `continuationId` 去重必须读取整份日志，并对来源不一致返回 `CONTINUATION_ID_CONFLICT`；预检回执的固定字段与可选字段、只读参数校验、`CONTINUATION_WARNING` 文案、桌面入口条件（当前分支中断回合、`explicitTurnContinuation`、未归档）、回执形状整体校验，以及按钮禁用条件（提交中、回执未知、运行中、内核未连接）也必须保留。反向断言禁止去重读取改用分支投影、禁止 `eligible` 使用真假值判断。续接边界摘要必须由 `session.continuation_entries_digest` 单点计算，`ApplicationService` 只做委托；`fork_thread` 在 `_write_new` 之前按复制前缀重算继承边界、边界条目未复制时清除摘要；`_on_turn_start` 在 `_runner_for` 之后、设置 `max_model_requests` 之前调用 `_reset_runner_history`。检查是源码文本与首次出现顺序扫描，不执行续接，也不调用模型。

### `check_capabilities.py`

`scripts/check_capabilities.py` 核对模型容量配置的预算、校验与错误收敛：`capabilities.py` 的 64 KiB / 128 项上限、三种 provider、两个必需字段与一个可选字段、七档推理集合与固定错误说明；`ModelCapabilities` 必须要求窗口大于 4096、输出为正且不超过窗口、来源非空、估算标记为精确布尔、推理档位为非重复的已声明子集；`ModelCatalog` 覆盖表必须只读、键必须为 `(provider, model)` 且模型名非空无空白，解析必须拒绝重复键与非有限常量、逐项要求 `provider/model` 分隔、必需字段齐全且无未知字段，任何解析错误都收敛为固定说明且不回显原配置。反向断言禁止无钩子解析、错误回显原配置与可变覆盖表。同时核对技术参考的容量口径。行为侧直接构造容量与目录：覆盖容量关系与布尔拒绝、来源与估算标记、推理档位白名单 / 去重 / 元组类型、描述投影、覆盖命中与大小写、默认容量复用、覆盖表只读与构造校验、未设置 / 空白 / 有效配置、二十种非法配置的固定错误消息与常量钩子（132 项）。实际解析结果仍需按技术参考核对。

### `check_codex_config.py`

`scripts/check_codex_config.py` 核对 Codex 配置的路径优先级、严格错误与 profile 解析：`codex_config.py` 只读 `~/.codex/config.toml`，路径按显式入参、`BOSS_HARNESS_CODEX_CONFIG`、`CODEX_HOME/config.toml` 与默认路径依次选择；`strict` 只让实际需要的文件错误明确失败，非普通文件、不可读与 TOML 语法错误分别使用固定码且不回显配置原文，Python 3.10 缺 `tomllib` 时以 `MODEL_CODEX_TOML_UNAVAILABLE` 报错；profile 必须同时具备模型、provider 与端点，`wire_api` 先去空白转小写、缺省或空值使用 `responses`，其他值以 `MODEL_CODEX_WIRE_API_UNSUPPORTED` 拒绝；凭据必须用 `Secret` 包装，`env_key` 只记录变量名。反向断言禁止文本模式读取、任何写入与配置原文回显。同时核对使用指南与技术参考的路径、协议与只读口径。除常量与文本扫描外，脚本直接调用 `config_path`、`profile_from_mapping` 与 `load_profile`，对照路径优先级与去空白、映射归一化与协议拒绝、凭据包装与不可序列化，以及临时目录下缺失 / 目录 / 非法 TOML / 不完整配置的 strict 结果、错误码与不回显原文，共 114 项。真实 TOML 解析仍需按平台核对。

### `check_retry.py`

`scripts/check_retry.py` 核对模型重试的退避上限、环境解析与观测事件边界：`retry.py` 的 8 秒上限、默认 3 次与 500ms、1–10 次范围；`retry_settings_from_environment` 必须先按空白回退默认值、再按整数解析，越界收敛并标记 `adjusted`，基数负数按 0，次数与基数两处解析失败都必须标记；`retry_delay` 在网关给出 Retry-After 时夹到 0–8 秒，否则指数退避同样封顶；`retry_after_seconds` 优先 `retry-after-ms`（0.001）再 `retry-after`（1.0），跳过空值、解析失败继续、无值返回 None；`retry_start_event` 只带次数、毫秒与固定默认说明，`retry_aborted_before_attempt_event` 以 `aborted` 与固定中文说明收尾；`with_retry_outcome` 关闭来源流，首个非错误事件补成功、错误事件补失败并原样透传，待补尝试次数在循环前、`retry_end` 与补发后共三处归零。反向断言禁止模块内睡眠、直接下标读取响应头与事件夹带内容。同时核对使用指南的重试配置口径。行为侧直接调用解析与事件函数：未设置 / 空白 / 有效 / 越界 / 非整数的次数与基数、网关值优先与两端夹取、毫秒头优先 / 空值与非法值跳过 / 头去空白、开始与取消事件字段、成功 / 失败 / 取消兜底 / 不重复补发的终态补发，以及来源流在耗尽与提前关闭时的传播（126 项）。实际等待与取消行为仍需按回合执行器核对。

### `check_openai_responses.py`

`scripts/check_openai_responses.py` 固定 OpenAI Responses 适配器的流式边界：终态原因映射按 completed / in_progress / queued → stop、incomplete → length（仅 `max_output_tokens`）、failed / cancelled → error 收敛；文本与思考增量事件集合、可重试状态 `408/409/429/500/502/503/504`、网关过载标记保持原样；流内错误先采用 `errors.py` 的结构化结论，`CONTEXT_OVERFLOW` 永不重试，无结论时才回退文本标记。输入条目必须区分 `function_call_output`、`function_call` 与 `output_text`，工具调用以 `call_id` 配对、参数以 `ensure_ascii=False` 序列化，思考块不回放。用量缺失或缺输入 / 输出计数时返回 `None`，不伪造全零。单次尝试固定 30 秒超时与零 SDK 重试，工具调用标识与名称超过 256 字符即拒绝；已向调用方产出内容后不再重试，清理未确认与共享恢复预算用尽时以固定说明停止。反向断言禁止吞掉全部异常、直接 `json.loads(raw)` 与回放加密内容。检查是常量与文本扫描，真实流行为仍需按用户指南核对。

### `check_anthropic_provider.py`

`scripts/check_anthropic_provider.py` 固定 Anthropic Messages 适配器的续接与错误边界：六项停止原因映射、可重试状态含 `529`；`errors.py` 已有结构化结论时以它为准，`CONTEXT_OVERFLOW` 与明确不可重试一律不重试，SSE 200 只认结构化瞬时结论。凭据按 `ANTHROPIC_API_KEY` 优先、两项环境变量都去空白、纯空白视为未配置，缺失时以固定说明报错；请求头过滤 `x-stainless-*` 与 `user-agent`，错误文本用全部凭据脱敏。消息翻译保留文本、thinking 签名与加密块，前缀摘要不一致的思考块不回放。流内必须校验 `message_stop` 后无事件、内容块索引不重复、增量类型与活动块一致、思考签名与加密块同时受单块与总量预算、工具调用标识与名称不超过 256 字符、工具参数完整结束；用量仅在输入与输出计数都出现时上报，`refusal` 以固定错误收尾。重试规则与 OpenAI 线路一致：已产出内容后不再重试，清理未确认与共享恢复预算用尽时以固定说明停止。反向断言禁止通用异常回显原始载荷、中断兜底抛出异常与直接 `json.loads(raw)`。检查是常量与文本扫描，真实流行为仍需按用户指南核对。

### `check_session_fork.py`

`scripts/check_session_fork.py` 核对会话分叉的复制边界：`fork_thread` 必须从当前分支投影（`_active_entries`）选择前缀，只接受已结束回合；指定当前分支之外的已结束回合时用内存中的合成 leaf 投影该分支，不写指针。前缀截断于所选回合的边界序号，checkpoint 只保留覆盖所选回合或更早回合的记录，迟到修订按 owner 归属只收进被选前缀的条目；投影仍有运行中条目、未决审批或会拆开工具批次时拒绝。新会话头不继承派生字段（`lastTurn` / `branchLastTurn` / 队列投影 / 截断标记），来源标识被截断时不继承 `projectId`，并写入 `forkedFromId` / `forkedFromTurnId`。复制循环排除 `thread_info` / `queue` / `task_phase`，改写 `continuationRequestOffset`、parentId、threadId 与 approvalId（全局唯一），最后在写出前重算继承的续接边界。反向断言：分叉区域不得调用 `self.append` / `self.record_turn` / `self._append_line` 改写源日志，只能通过 `_write_new` 写新会话；两条选择路径各经过一次 `_active_entries`。检查是源码字面量与首次出现顺序扫描，不执行分叉。

### `check_fork_checkpoints.py`

`scripts/check_fork_checkpoints.py` 在临时目录构造会话，核对分叉时的上下文检查点归属过滤：`checkpoint_in_branch` 以 `throughTurnId` 在当前分支回合表中的位置为判据，只保留覆盖选中回合或更早回合的记录；复制前缀与边界后的恢复修正共用同一判据。行为侧覆盖选中回合之前与之后的检查点、未知回合、非字符串与缺失 `throughTurnId`、边界前的未知检查点在前缀裁剪中被过滤、边界后的未知检查点在恢复修正中被过滤，以及默认选中最后一个回合。脚本按顺序扫描位置表、选中位置、判据的安全读取与位置上限比较、两处调用；反向断言判据不按下标读取载荷、`turn_positions` 与 `selected_position` 的引用次数固定。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，只使用临时目录。

### `check_branch_projection.py`

`scripts/check_branch_projection.py` 核对分支投影 `_active_entries` 的条目归属规则：没有任何 leaf 记录时原样返回输入，不复制或重排；有 leaf 时逐条记下追加时的投影尾部，路径只由该尾部回溯推导，绝不读取写入方 `parentId`；leaf 目标缺失、不是字符串、未知或不是回合时按缺失处理并沿用上一个有效叶，不整段失败；条目编号重复必须立即拒绝。迟到修订按 owner 跟随所属回合，其余条目按是否在路径上保留；`attachment` / `thread_info` / `queue` 属于会话级状态跨分支保留，回合、阶段与工具批次按 `turnId` / `taskId` 归属筛选，上下文编辑按目标条目 owner、摘要检查点按 `throughTurnId` 筛选，未知类型丢弃。检查是源码字面量与顺序扫描，不执行投影。

### `check_item_ownership.py`

`scripts/check_item_ownership.py` 核对条目归属 `_item_owners` 与回合树 `_turn_tree` 的推导规则。归属按修订目标优先、仅非 `running` 工具调用回退读取 `parentId`、显式 `turnId` 优先于回退与活动回合推导；重复条目编号保留首个归属，无归属条目挂起到下一个新回合，非法 `turnId` 跳过；`running` 回合设活动归属，终态只在活动回合匹配时清空。回合树先经 `_active_entries` 校验，`known` 只收合法标识符回合，叶记录按目标映射尾部，父回合取追加时尾部且自父回合记为无，非回合条目推进尾部并记录条目尾部后返回父回合表与首次出现顺序。反向断言：归属区域只允许旧版工具调用回退读一次 `entry.get("parentId")`，不得从 `payload` 读取；回合树必须恰好校验一次投影且完全不读 `parentId`。脚本并构造 entries 直接调用两个入口（70 项）：归属覆盖显式回合、`running` 活动回合、挂起收割、跨回合修订继承、非 `running` 工具调用回退、`running` 不回退、重复编号、无归属、终态清空、非法回合号与重复回合；回合树覆盖父回合链、条目推进尾部、任务 / 批次归属、未知归属跳过与重复回合不重复入列。检查不读取会话文件或执行分支投影。

### `check_branch_list.py`

`scripts/check_branch_list.py` 核对分支列表 `list_branches` 的端点推导与分页：参数先做上限与存在性校验，游标带 `threadId` / `endpoints` scope 并校验 (位置, turnId) 形状；条目、回合树、叶状态、回合与归属必须在同一把锁内读取；用户消息预览按归属回合只取首条、空白折叠并按上限截断加省略号；端点取无子回合的回合，翻页按键过滤而非切片，下一页游标只在仍有剩余时生成且绑定最后一条；逐端点计算深度、最近分叉点（反向扫描祖先并排除自身）、分支首回合、`containsLeaf` 与 `isLeaf` 的独立判定，以及仅终态回合可选。检查是源码字面量与顺序扫描，不执行分支列表。

### `check_turn_records.py`

`scripts/check_turn_records.py` 核对回合记录 `_turns` 的阶段合并与终态边界：`task_phase` 只在 `ownerKind` 为回合、回合已存在、阶段与状态合法、尝试次数 1–1000、重启上限 0–32 时合并，恢复原因不超过 256 字符、恢复策略只接受 `manual` / `closed`；回合只在合法标识符下首次创建，`firstOrdinal` 取上一条终态记录序号加一，持久载荷不得覆盖 `firstOrdinal` / `lastOrdinal` / `boundaryOrdinal`，`lastOrdinal` 与 `updatedAt` 每次推进；首条终态记录以 `setdefault` 固定 `boundaryOrdinal` 与 `completedAt`，并在终态分支内推进「上一条终态序号」。反向断言：公开回合必须过滤三个内部字段；终态两条 `setdefault` 与序号推进的缩进必须位于终态分支内。检查同时直接调用 `SessionStore._turns` 做行为对照（76 项）：非回合条目忽略、回合编号格式（缺失 / 非字符串 / 非法字符 / 超长）与合法复杂编号、同一回合多条记录的字段合并与 `firstOrdinal` / `startedAt` 保留、`lastOrdinal` / `updatedAt` 推进、终态首次边界与 `completedAt` 不被后续覆盖、`previous_end` 推进、内部记账字段不可覆盖、`task_phase` 的归属 / 阶段 / 状态 / 尝试次数 / 重启上限 / 恢复原因 / 恢复策略边界与回合出现前跳过、threadId 收敛与缺失时间戳。

### `check_set_leaf.py`

`scripts/check_set_leaf.py` 核对分支指针 `set_leaf` 的写入路径：回合号先过标识符校验，写入在锁与索引事务内；已在目标位置时幂等返回 `changed: false` 且不写记录；目标回合必须存在且最后一条同名记录已结束；会话里不能还有未结束的回合、运行中条目或未决审批；写入前用候选条目模拟投影并要求位置与目标一致；叶记录带 `targetId` / `turnId` / `fromTurnId`，只追加一次并重建索引，成功返回 `changed: true`。反向断言：目标取 `records[-1]` 且不得出现 `records[0]`；叶记录只调用一次 `_append_line`（`entry.to_dict()` 恰好两次：候选与追加）；两种 `changed` 结果各出现一次。检查是源码字面量与顺序扫描，不执行写入。

### `check_branch_summary.py`

`scripts/check_branch_summary.py` 核对被放弃分支的推导与摘要写入：`abandoned_branch` 先读条目与回合树，目标回合必须存在（`None` 除外），以目标祖先链为界从旧叶回溯到共同祖先（不含）并反转成时间顺序，返回 `fromTurnId` / `targetTurnId` / `commonTurnId` / `abandonedTurnIds`；`append_branch_summary` 校验摘要为 1–32000 字符且非纯空白，在锁与索引事务内从最后一条叶记录反向扫描并核对请求的 `leafEntryId`，其后不得已有回合或摘要，摘要只追加一次并绑定 `leafEntryId`，先执行提交回调再重建索引。反向断言：叶记录只能反向扫描；摘要只追加一次；长度上限只出现一次。脚本并构造轻量替身直接调用 `abandoned_branch`（52 项），覆盖线性链回退一级 / 两级 / 四级、原地目标、目标为空、分叉共同祖先、无叶记录、空树、目标不存在与固定结果字段。检查不执行摘要写入。

### `check_item_projection.py`

`scripts/check_item_projection.py` 核对条目投影 `_project_items`：空编号与非法编号记录跳过；`revises` 指向已投影条目时把载荷合并进同一槽位并保留原编号与 threadId；旧记录里非 `running` 的工具调用可用 `parentId` 回退，且父项必须是已投影的工具调用；编号字段只保留字符串，非对象 `approval` 删除；同编号的新条目只保留先出现的一条，新条目是唯一追加路径。反向断言：`parentId` 只允许旧记录工具调用回退读取一次，不得从 `payload` 读取；重复编号分支必须 `continue`；修订槽位必须保留 `items[slot]["id"]`。检查同时直接调用 `SessionStore._project_items` 做行为对照（55 项）：非 item 条目忽略、缺 / 非字符串 / 空 id 跳过、基本投影与 threadId 收敛、修订合并保留原编号与未覆盖字段、修订别名链、目标不存在或非字符串时新建、同编号保留先出现、修订后同编号跳过、工具调用父条目回退（running / 子或父类型不符 / 父不存在不回退）、编号字段非字符串删除、非对象 approval 删除、payload 缺失、输入不被修改与返回独立对象。

### `check_read_item.py`

`scripts/check_read_item.py` 核对单条目读取 `read_item`：请求编号必须是 1–128 字符的字符串；读取在条目快照内进行；`revises` 链保留别名，旧记录里非 `running` 的工具调用可在已选中工具条目时回退；修订条目使用请求编号、或选中条目已有/带修订目标/带旧记录父项时以 `INVALID_RESULT_REFERENCE` 拒绝；修订记录数、别名数量与别名字节分别受三项上限约束，超限以 `RESULT_HISTORY_LIMIT` 拒绝；修订只继承 `kind` 与 `result`；失效别名移除时同步回减字节。反向断言：三项上限各只出现一次；`parentId` 只从条目读取两次（回退与冲突条件），不得从 `payload` 读取；两类错误码数量固定。检查是源码字面量与顺序扫描，不执行读取。

### `check_page_cursor.py`

`scripts/check_page_cursor.py` 核对分页游标编解码：`_page_cursor` 只写 `kind` / `scope` / `key` 三个字段，编码为 `p1_` 前缀加去掉补齐符的 urlsafe base64；`_read_page_cursor` 对空游标返回 `None`，否则校验字符串、`p1_` 前缀与 4096 字符上限，严格解码并把 `ValueError` / `UnicodeDecodeError` / `binascii.Error` / `RecursionError` 统一收敛为「游标无效」，载荷必须恰好包含三个字段、`kind` 与 `scope` 完全匹配、`key` 为列表，否则报「游标与查询范围不匹配」。反向断言：严格解码参数必须保留；四类异常都必须被捕获；两类错误各出现固定次数。脚本并直接调用 `_page_cursor` / `_read_page_cursor`（45 项），覆盖 `p1_` 前缀与无补齐符、键列表往返、scope 键序无关、`None` 透传、空字符串 / 非字符串 / 错误前缀 / 非法 base64 / 坏 JSON / 顶层非对象 / 缺字段 / 额外字段 / key 非列表 / kind 与 scope 不符 / kind 大小写 / 深层嵌套非对象 / 超长游标。检查不执行 SQL 或分页读取。

### `check_entries_snapshot.py`

`scripts/check_entries_snapshot.py` 核对会话条目快照：`open_entries_snapshot` 在写锁内确认会话存在、以二进制打开日志、`fstat` 后把可读前缀裁到最后一条完整记录（`_complete_record_limit`），任何异常都先关闭文件；`SessionEntriesSnapshot` 保存 source / size / mtime / inode 与行号，`stamp` 按 size / mtime / inode 顺序返回前缀身份；进入与迭代都拒绝已关闭快照；每次迭代回到开头、行号复位、按 `MAX_SESSION_LINE_BYTES` 与钉住的前缀字节上限逐行读取、跳过空行并解码。反向断言：前缀必须来自 `_complete_record_limit`；关闭错误出现两次；`stamp` 必须携带三项。检查同时做行为对照（75 项）：用 `io.BytesIO` 直接实例化 `SessionEntriesSnapshot`，覆盖空前缀、仅会话头、空行跳过计入行号、CRLF、前缀字节上限、重入迭代、`stamp`、关闭后进入 / 迭代拒绝、上下文管理器退出即关闭、格式无效 / 重复会话头 / 坏 JSON / 非 UTF-8 错误；并用真实临时日志与轻量替身直接调用 `SessionStore.open_entries_snapshot`，覆盖完整记录、末尾残段裁剪、空文件、纯残段、超长无边界拒绝、取长度失败时关闭文件、打开失败直接报错，以及写锁内先核对会话再打开的顺序。

### `check_compaction.py`

`scripts/check_compaction.py` 核对自动压缩策略的校验、归一化与失败契约：`compaction.py` 的六个字段与 `anthropic` / `openai` / `codex` 白名单、布尔 / 1–100 / 1–1000000 的精确类型与范围、provider 归一化（codex → openai）、model 的非空 / 200 字符 / 无空白校验与 effort 档位校验；`verified_policy` 拒绝未知字段与空对象并按字段顺序过滤；`override` 只接受三个界面字段并保留摘要线路；`from_environment` 先去空白、再按 4096 字节与重复键钩子解析、拒绝未知字段，并以固定说明报错。反向断言禁止无钩子解析与错误回显原文；同时核对技术参考与使用指南的自动压缩口径。除静态扫描外，脚本直接调用 `verified_policy` 覆盖字段边界与顺序过滤，构造 `CompactionPolicy` 覆盖默认值、拒绝、provider 归一化与 `describe`，核对 `override` 合并与白名单，并在保存与恢复 `BOSS_HARNESS_COMPACTION` 的前提下覆盖持久默认值、空值 / 空白、JSON 合并、全字段、重复键、未知字段、非对象、非法 JSON、超长与越界值，共 166 项。

### `check_ownership.py`

`scripts/check_ownership.py` 核对状态目录独占锁的获取、释放与失败顺序：`ownership.py` 必须先解析并创建私有目录，再以私有描述符打开 `.owner.lock`，使用非阻塞独占 `flock`；拿不到锁与其它文件错误都必须先释放描述符，再分别以固定可读的 `EWOULDBLOCK` 说明或原异常上报；`close()` 必须先清空字段再按局部变量关闭描述符，`__del__` 复用同一关闭路径，重复关闭不会触碰同一描述符。反向断言禁止删除锁文件、改用共享锁或无限期等待；同时核对技术参考与使用指南的占用锁口径。脚本只扫描源码，不证明运行时锁已生效。

### `check_maintenance.py`

`scripts/check_maintenance.py` 核对索引修复的清单、移动与回滚边界：`maintenance.py` 的备份目录必须位于 `repairs/` 下并以 UTC 时间戳加随机后缀命名；清单的字节数与 SHA-256 必须来自同一私有描述符，`lstat` 与 `fstat` 的 dev/ino、普通文件与归属校验失败时拒绝，摘要按 1 MiB 分块读取；修复必须先只读核对状态目录存在且非「陌生目录」，再获取占用锁、创建备份、逐个移动索引文件，移动前再次核对路径身份；清单以 `O_EXCL` 私有文件写入并 `fsync`，成功路径先同步备份目录再同步状态根目录，之后才重建索引；失败路径把新候选移入 `failed-candidate`、回滚已移动文件并按同一顺序同步目录后继续上报；`finally` 必须释放占用锁。反向断言禁止删除原始记录、`json.dump` 流式写入与无界读取；同时核对技术参考与使用指南的修复口径。脚本还在临时状态目录中执行 7 个修复场景：缺失路径与陌生目录的拒绝说明、空目录修复、含会话与事件的状态目录修复、重建前后两处失败的索引回滚，以及损坏会话进入跳过列表。成功场景核对日志字节不变、备份文件与清单摘要、会话数与事件游标。

### `check_bridge_lifecycle.py`

`scripts/check_bridge_lifecycle.py` 核对宿主工具桥的幂等清理：`BridgeLifecycle` 必须以 `RLock` 保护清理表，扫描时剔除已回收的弱引用并保留存活引用，同一对象只清理一次并直接返回；只有可弱引用的对象才登记；`close()` 优先于 `dispose()`，钩子必须在释放清理表锁之后调用；清理异常必须吞掉，日志只记录异常类型名。反向断言禁止重新抛出、记录堆栈或异常原文；同时核对技术参考的桥清理口径。脚本只扫描源码，不证明运行时桥已释放。

### `check_runtime_capacity.py`

`scripts/check_runtime_capacity.py` 核对运行时容量准入、回合归属与关闭中断口径：`owner_capacity` 必须为 `2 * capacity`，`has_capacity` 同时检查关闭标志、会话上限与 owner 上限；`check_admission` 按关闭（`-32003`）、同会话已有回合（`-32004` 带 `turnId`）、会话上限（`TURN_CONCURRENCY_LIMIT`）、owner 上限（`TURN_OWNER_LIMIT`）的顺序拒绝；`reserve` 在锁内重复准入并同时登记 `active` 与 `jobs`，`release` 与 `_retire_locked` 都用对象身份比较，回收还要求 worker 结束且 abort 完成。中断与关闭共享一次幂等 abort 认领，`prepare_interrupt` 只做取消与认领，派发由 `interrupt` 完成；`request_stop_aborts` 与 `wait_for_stop` 在锁外启动与等待，`stop` 默认两秒窗口并按取消、派发、等待顺序执行。容量通知 worker 必须是守护线程，启动失败复位状态，关闭后不再回调，回调异常不结束循环。脚本含缩进敏感断言，要求派发与等待确实位于锁外。检查是源码扫描，不启动线程或验证运行时并发行为。

### `check_shutdown.py`

`scripts/check_shutdown.py` 核对内核关闭的等待预算与中止线程所有权：`TrackedAbort` 必须只发信号（显式 callback 优先、否则回退 `request_abort`，异常收敛，`finally` 收尾），收尾必须先占锁判重、再置位 `done`、最后执行 `on_done`；启动只允许一次，线程启动失败只退休记账，绝不回退为内联中止；`join_until` 必须跳过未启动、当前线程与重复 worker，并按剩余期限 `join`。脚本同时固定 runtime / application / connections 的最多两秒共享期限、关闭时「冻结准入 → 派发取消 → 各域依次等待 → 关闭 hook 与快照」的顺序，以及技术参考与使用指南的关闭口径。脚本只扫描源码，不证明运行时线程已退出。

### `check_browser_source.py`

`scripts/check_browser_source.py` 核对 `BOSS_HARNESS_BROWSER_SOURCE` 的严格白名单 `auto` / `existing-browser` / `stored-cookie`、空值回退与规范化，要求上游参数以独立 `--browser-source` 值构造且子进程保持 `shell=False`；同时核对启动自检码、连接报告与桌面设置页的来源策略展示。脚本并直接调用 `resolve_browser_source_override`（43 项），覆盖未设置 / 空字符串 / 纯空白回落、大小写与首尾空白归一、三个合法值、环境变量生效与显式值优先、非法显式值与非法环境变量的固定错误文案，以及解析不写回环境变量。脚本不启动上游、不读取浏览器或 Cookie，也不验证上游是否支持该参数。

### `check_connection_lifecycle.py`

`scripts/check_connection_lifecycle.py` 核对连接检查的异步生命周期：`_ModelCheck` 必须保留取消事件、provider、worker 终态与中止线程字段；`start` 必须串行化 CLI / 平台检查并处理失败启动，模型检查必须以 worker、取消事件与 `_ModelCheck` 三重归属判定所有权，abort 未完成时不得退休；超时、空闲通知和关闭阶段必须按取消、请求中止、等待的顺序回收。脚本只扫描源码，不证明运行时线程已退出。

### `check_connection_report.py`

`scripts/check_connection_report.py` 核对连接报告字段投影：内核 `connections.read()` 是 `connection/read` 与 `connection/check` 的共同数据源，报告固定为 `cli` / `model` / `platform` 三卡；渲染层解析器必须收口状态、浏览器来源与认证状态枚举，并限制正文、代码、时间与文本字段长度，未知值整份拒绝而非显示空白。脚本同时核对桌面 bridge 与 `connection/check` 目标白名单。它是静态扫描，不证明运行时报告内容一定可信。

### `check_login_flow.py`

`scripts/check_login_flow.py` 核对内核扫码登录的凭证校验、命令引用与保存回读边界：`begin_login` 要求平台可用、内核未关闭且没有并发的 CLI / 平台 / 登录检查，先探测上游可用性再创建取消事件与登录 id；`cancel_login` 只接受匹配的尝试 id 与 `waiting` / `saving` 状态；`complete_login` 要求 Cookie 为 1–200 项、User-Agent 不超过 512 字符且不含控制字符、Cookie 键符合 token 语法、值不含控制字符或分号，必须携带 `wt2`，Cookie 头不超过 64 KiB，Cookie 头与 User-Agent 分别经 `shlex.quote` 进入交给上游的数据，凭证不写入登录状态或平台报告；保存任务在调用前后与写回前检查取消标记，命令经 `--curl-file -` 与 `timeout=20` 交给上游，调用后清空命令文本，成功后再以 `timeout=15` 回读本地状态并区分 `LOGIN_READBACK_FAILED` / `LOGIN_INCOMPLETE`；`_local_auth` 先报风控锁再判登录态，六处拒绝均返回 `False`。脚本含反向断言禁止 shell 拼接、凭证写入状态与旧任务清掉新槽位。检查是源码扫描，不执行登录、不读取真实 Cookie。

### `check_search_unicode.py`

`scripts/check_search_unicode.py` 同样在安装依赖前运行：Python 侧按内核 `needs_extra` 选择补表归一化路径，Node 侧导入桌面 `caseFold.ts`，对全部 Unicode 标量值按 `0x1000` 分块计算 SHA-256 摘要并比较；不一致时列出码点区间。它验证映射表与两端 Unicode 数据的组合结果，不覆盖按字素簇切分的文本级行为。Source build 在 Python 3.12 上运行一次，独立的 Python matrix job 另在 Python 3.10、3.11、3.12、3.13、3.14 上分别运行，均使用 Node 24；同一 job 还用 `python -m compileall -q harness/src scripts` 验证这些解释器能编译内核与脚本源码（不导入依赖、不联网）。全量核对报告分块差异，可加 `--block 0xN` 只比较该 0x1000 分块并逐码点列出 Python 与 Node 的结果。

### `check_search_clusters.py`

`scripts/check_search_clusters.py` 直接导入内核 `session._search_clusters` 做行为对照：空串、ASCII 大小写、组合记号、兼容字母、`ß`、谚文 jamo / 兼容 jamo / 预组合音节、半角假名与浊音符号、尾音后接 leading jamo 的逐簇输出必须保持；返回区间必须首尾相接、覆盖全文，`normalize` 参数逐簇接收原文片段，归一化结果再聚类保持幂等，普通路径与 `NFKC + casefold` 逐簇一致。脚本同时扫描 `session.py` 固定四类合并条件、默认与补表归一化分支以及两处调用点；它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，按解释器自身的 Unicode 数据验证文本级行为。

### `check_search_index.py`

`scripts/check_search_index.py` 直接导入内核 `SessionStore._search_normalized` 做行为对照：ASCII 快速路径必须只小写、不保留索引；空串、单码点非 ASCII、组合记号、组合类重排、`ß` / `İ` 多字符折叠、谚文 jamo、半角假名、扩展 jamo、补表码点与代理项的完整三元组必须保持；identity 文本返回空索引，跨簇文本的 `starts` / `ends` 必须与逐簇重建一致、长度等于归一化文本、单调且覆盖原文，折叠文本与补表逐簇拼接一致。脚本同时扫描 `session.py` 固定快速路径、identity 判定、两轮聚类遍历与 `array('I')` 紧凑索引，反向断言不直接调用 `unicodedata`、不用列表保存索引，并核对查询与正文两处调用点；它在 Source build 与 Python 3.10–3.14 矩阵中分别运行。

### `check_search_scan.py`

`scripts/check_search_scan.py` 直接导入内核 `SessionStore._search_tool_text` 做行为对照：没有工具名或名称空白时返回空串；来源编号、参数与结果摘要按固定顺序追加，参数对象按键排序且不转义非 ASCII，超过 2000 字符的参数整体省略，最终文本截到 6000 字符。脚本同时扫描 `session.py` 固定 `search_messages` 的查询 / `limit` / `include_archived` 校验、会话与文本预算、超大会话跳过、读取失败标记、逐条消息预算、角色分流、索引映射、跨分支 `onBranch` 与三处展示截断，反向断言七处 `truncated` 标记、四种循环退出、结果必须经 `_SEARCH_MATCHES` 截断且工具文本不抛错；它在 Source build 与 Python 3.10–3.14 矩阵中分别运行。

### `check_task_relation.py`

`scripts/check_task_relation.py` 直接调用 `task_ownership.py` 的六个纯函数做行为对照，固定任务归属投影与关系判定：`turn_snapshot` 按回合集合与队列关联过滤、非法状态与标识跳过、终态后 running 与 `queueId` 变化标记重复、上限后不再收新回合但已知回合仍可更新、阶段归并与恢复原因 / 策略只认固定枚举；`queue_snapshot` 按直接集合、目标回合与回执回合三条来源选中，身份字段变化与非法值标记冲突且非法值不进入投影；`user_message_refs` 按每队列条数与修订标识上限截断、从首个回合与当前运行回合推断归属、非法修订字段归一化并标记冲突；`resolve_queue_relation` 的 followUp 需要回合关联、用户消息与回执一致，steering 以目标回合与转向消息为准且回执只作复核，五类归属与冲突优先级逐一固定；`resolve_compaction_relation` 只在会话、检查点与唯一回合一致时归属；`recovery_policy` 对缺失或未知状态优先人工核对，其余按种类与状态分支。结构侧按顺序固定三个关系函数的判定优先级。它在 Source build 与 Python 3.10–3.14 矩阵中分别运行，不访问网络、模型或招聘平台。

### `check_search_snippet.py`

`scripts/check_search_snippet.py` 核对搜索片段与高亮的一致性：`SessionStore._search_snippet` 只折叠命中两侧空白，必须原样复制命中区间，预算不足时先保留命中词再收窄上下文，并保留截断省略号；桌面的 `findKernelTextRanges` / `splitKernelHighlight` 必须使用内核 casefold 归一化，`SearchDialog` 必须把 `hit.snippet` 交给该高亮路径。脚本不执行搜索，也不验证运行时命中数量。

### `check_workflows.py`

`scripts/check_workflows.py` 扫描 `.github/workflows` 下的 YAML：要求顶层 `permissions` 含 `contents: read` 且不含 `write`，且顶层之外不得再声明 `permissions`（job 级或 step 级声明同样会使检查失败）；`concurrency` 启用 `cancel-in-progress: true`，每个 `actions/checkout` 步骤带 `persist-credentials: false`，并禁止 `pull_request_target` / `workflow_run` 与非 `actions/` 的 `uses`，每个作业必须声明正整数 `timeout-minutes`；每个 `uses` 引用必须匹配 `actions/<名称>@v<主版本>`，`@main` / `@master` 等可变引用失败；工作流聚合文本还必须保留两条 `npm audit` 命令（生产 moderate、全量 critical），缺失即失败。它还收集 `scripts/check_*.py` 与工作流文本中的脚本引用，要求集合完全一致；未接入 CI 的检查脚本或引用不存在的脚本都会失败。检查是文本静态扫描，不解析完整 YAML 语义；复用工作流或动态表达式仍需人工核对。

### `check_docs_links.py`

`scripts/check_docs_links.py` 扫描根目录、`docs/`、`harness/` 与 `.github/` 下的全部 Markdown（含 `harness/README.md` 与 PR 模板）：跳过代码围栏、行内代码与 HTML 注释中的示例、外链，核对相对文件路径存在；带 `#片段` 的链接同时按 ATX 标题生成 GitHub 风格锚点（小写、去标点、空格转连字符、重复标题全局追加 `-1`、`-2`），并解码百分号编码后校验同文件与跨 Markdown 文件的页内锚点。代码围栏识别 ``` 与 ~~~，最多允许 3 个前导空格，关闭标记不得短于开启标记且不得带信息串；未闭合时以文件名失败。它还要求 `docs/README.md` 索引 `docs/` 下其余 Markdown 文件，并要求上述目录中的 Markdown 全部登记在检查清单内，未登记或登记后移出约定位置都会失败。根目录引导文档（当前为 `SETUP.md`）还必须能从 README 的「项目导航」章节与 `docs/README.md` 的根文件列表到达，导航章节缺失或入口被移除都会失败。它不检查远程 URL 是否可访问，也不处理 setext 标题或运行时生成的页面锚点。它还要求 `scripts/` 下每个 `check_*.py` 在本文档恰有一个以脚本名为标题的三级小节，小节对应的脚本也必须存在；代码围栏与 HTML 注释中的标题不计入。

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

同步 provider 通过每个请求一个后台线程桥接异步 SDK 流：队列最多 64 个事件、缓冲合计最多 4 MiB、单事件最多 2 MiB，同一进程最多 8 个在途泵；取消、超时与失败先丢弃排队事件并只交付一个终止事件，清理等待最多 1 秒。该缓冲只约束内核已接收的 SDK 事件，不包含 SDK 解码前的传输数据。

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

Anthropic 的私有续接元数据只保存签名块描述：请求前缀 digest、块顺序、长度与内容 SHA-256；单个签名最多 16 KiB，签名合计最多 96 KiB，续接载荷最多 128 KiB，正文 / 思考各最多 1 048 576 字符且块最多 4096 个。恢复时逐块校验 digest、调用 ID、回合归属与助手引用；编码失败的签名元数据降级为普通工具批次，其余字段错配按固定说明拒绝。

回合终态提交与取消接受使用同一运行锁边界。终态提交前已接受的取消以 `interrupted` 收尾，并暂停结算时已排入的后续队列；即使模型已经给出完成结果，也不会继续自动派发。已产生的文本、工具结果、审批及外部动作事实仍保留，取消不表示撤销。终态已提交并释放执行槽位后，若没有活动回合则返回未中断；旧 `turnId` 不能中断新回合。桌面停止请求携带界面正在展示的回合 id，该回合已被后续回合替代时以 `-32004` 拒绝且不取消新回合，与 `turn/steer` 的 `expectedTurnId` 同一约定；不带 `turnId` 时仍取消该会话当前活动回合（旧客户端行为）。显式 `turnId` 必须是非空、非纯空白、最多 128 字符的字符串；null、空字符串、数字、布尔值、数组或对象在设置取消信号前返回 `-32602`，闲置回合同样校验，不能退回取消当前回合。用户之后仍可显式发起新任务，已暂停的队列不会因此自动恢复。

回合最终 `finish` 阶段 checkpoint 无法确认持久化时，当前执行以 `error` 收尾，尽力追加 `phasePersistenceFailure` 修正记录，并在释放容量前暂停当前会话全部待处理队列。暂停写入也失败时，内核保留暂停责任；后续准入或领取必须先完成暂停，存储恢复不会自动执行旧 follow-up。其他会话仍可按既有 FIFO 等待顺序取得空出的容量。

## 中断回合续接

`turn/continuation/read`（能力 `explicitTurnContinuation`）是只读预检，`turn/continue` 在通过同一预检后启动一个 `continuedFromTurnId` 指向来源回合的新回合。预检只接受当前分支的最新回合，且其状态必须是 `interrupted`；未决审批、结果未知或未完成的工具调用、批次清单不完整的旧工具调用都会拒绝续接。历史边界取最后一个可验证的持久请求（`completed_tool_batch`）或唯一用户输入（`user_input`），续接只沿用到该边界为止的条目；边界之后发生模型线路切换、上下文摘要、对已包含条目的编辑或修订时预检失败。续接沿用来源回合的 provider / model / thinking / effort、maxTokens、工具策略、技能与附件、自动压缩策略与模型请求偏移，并在启动前用请求指纹复核；不重新执行已完成的工具，新写操作仍逐次审批。预检与 `turn/continue` 不改变 `0.2.0` 协议。

「最新回合」与「是否已有续接回合」按当前分支判定：放弃续接回合所在分支、切回来源回合后，来源重新成为当前分支的最新 `interrupted` 回合，可以再次续接并产生新的模型请求。`continuationId` 的去重则按整份会话日志判定：相同编号与相同来源重复提交按幂等返回已有回合（即使它在被放弃的分支上），编号重复但来源不同返回 `CONTINUATION_ID_CONFLICT`。切回后再次续接与幂等重放是两件事，客户端不应靠重试同一编号来重新执行。幂等回执（`deduplicated: true`）只说明编号已被使用，不携带已有回合的状态：若该回合以 `TURN_START_FAILED` 之类的错误状态落盘，重放同一编号得到的仍是成功形状的回执，客户端应以回合列表中的实际状态为准，不能据此认为回合已开始。

续接边界摘要与条目逐字节绑定。分叉（`SessionStore.fork_thread`）复制当前分支前缀时丢弃内核专用记录并改写审批编号，继承的 `continuationBoundaryDigest` 因此按复制后的前缀重算；边界条目未被复制时清掉摘要，预检按「持久边界不存在」拒绝（`CONTINUATION_BOUNDARY_INVALID`），而不是误报历史变化。串行复用主 runner 的场景（嵌入方未提供 provider factory）下，普通回合启动前复位 runner 的历史提供者，避免上一个续接回合钉住的历史边界泄漏到下一个回合。

rc.422 之前创建的分叉会话没有这层重算：副本里的摘要仍是源会话原始条目链的值，对其中继承的续接回合再次续接会以 `CONTINUATION_HISTORY_CHANGED` 拒绝。日志 append-only，旧记录不就地迁移，预检也无法把「旧版复制未重算」与「历史真的变化」可靠区分；处理方式是重新从源会话分叉（新分叉按复制前缀重算）或在分叉会话里新建回合。

预检失败以 `eligible: false` 与下列固定原因码返回；`turn/continue` 在启动前再次预检，失败时以同一原因码作为 RPC 错误数据。原因码集合由 `check_turn_continuation.py` 与技术参考的表格双向核对。

| 原因码 | 含义与处理 |
| --- | --- |
| `CONTINUATION_HISTORY_LIMIT` | 会话历史超过续接读取上限；超大日志不能续接，先在桌面核对会话状态。 |
| `CONTINUATION_STATE_UNAVAILABLE` | 读取会话或运行状态失败；先刷新核对，不自动重试。 |
| `CONTINUATION_NOT_LATEST` | 来源不是当前分支的最新回合；切回该回合后重新预检。 |
| `CONTINUATION_NOT_INTERRUPTED` | 来源回合不是 `interrupted`；已结束或失败的回合不能续接。 |
| `CONTINUATION_ALREADY_EXISTS` | 当前分支上已有指向来源的续接回合；直接打开该回合。 |
| `CONTINUATION_APPROVAL_PENDING` | 来源回合仍有未决审批；先处理审批。 |
| `CONTINUATION_TOOL_OUTCOME_UNKNOWN` | 来源回合含结果未知的工具操作；先核对平台状态，不续接。 |
| `CONTINUATION_TOOL_STATE_UNRESOLVED` | 工具调用仍处于运行、已批准或待审批等未完成状态。 |
| `CONTINUATION_TOOL_BATCH_INVALID` | 工具批次清单格式、前后记录或模型响应指纹不一致。 |
| `CONTINUATION_TOOL_BATCH_MISSING` | 旧工具调用缺少可核验的批次清单。 |
| `CONTINUATION_TOOL_BATCH_INCOMPLETE` | 工具批次未被证明完整持久化或缺少已确认结果。 |
| `CONTINUATION_APPROVAL_INVALID` | 来源回合的审批记录无法核验。 |
| `CONTINUATION_BOUNDARY_INVALID` | 没有可验证的请求或工具结果边界，或边界摘要无效。 |
| `CONTINUATION_STEERING_OUTSIDE_BOUNDARY` | 已投递的转向消息不在可验证边界内；新建回合继续。 |
| `CONTINUATION_HISTORY_CHANGED` | 已确认历史前缀、输入或上下文摘要发生变化。 |
| `CONTINUATION_CONTEXT_CHANGED` | 模型线路、配置、工具策略、技能或附件与来源回合不一致。 |
| `CONTINUATION_CONTEXT_UNAVAILABLE` | 技能、附件或模型配置无法安全复核。 |
| `CONTINUATION_ALREADY_COMPLETED` | 来源回合已持久化完整助手回复，无需续接。 |
| `CONTINUATION_SOURCE_UNVERIFIABLE` | 来源回合缺少续接配置摘要或配置不可用。 |
| `CONTINUATION_PROVIDER_UNAVAILABLE` | 当前内核没有可复用的模型供应商，或进程显式禁用模型调用。 |
| `CONTINUATION_REQUEST_LIMIT` | 来源回合已用完持久化的模型请求上限。 |
| `CONTINUATION_HISTORY_INVALID` | 已确认历史无法按当前协议重建。 |
| `THREAD_ARCHIVED` | 会话已归档；先恢复会话。 |
| `KERNEL_SHUTTING_DOWN` | 内核正在关闭；重启后再预检。 |
| `THREAD_BUSY` | 会话仍有运行、收尾、后续任务或回执收尾。 |
| `THREAD_REQUIRES_REVIEW` | 工具结果持久化状态需要人工核对。 |
| `QUEUE_REQUIRES_REVIEW` | 队列仍有投递状态未核对。 |
| `TURN_ADMISSION_WAITING` | 已有更早排队的任务等待并发槽位。 |

预检回执固定包含 `threadId`、`sourceTurnId`、`eligible` 与 `warning`；通过时另含 `boundary`（`user_input` / `completed_tool_batch`）与 `completedToolCalls`，失败时含 `reasonCode` 与 `reason`。桌面在渲染前整体校验回执形状，未知边界值或非法计数按不可识别处理，不显示续接按钮；提交 `turn/continue` 时生成一次性 `continuationId`，回执必须同时回带该编号与来源回合，否则按回执不一致处理。续接请求回执未知时不自动重发，先刷新核对。

## 自动压缩与溢出恢复

模型回合默认开启自动压缩：完整输入估算达到 `inputBudget` 的 80%，或预算检查拒绝请求时，尝试摘要更早的完整回合，保留近期估算 20000 token。`inputBudget` 已扣除业务输出储备和 4096 token 安全余量，阈值不重复扣减。小窗口应降低保留目标；当前运行回合始终完整保留，因此单个过大输入或工具结果仍可能无法容纳。

保留目标按 token 口径估算，但不承诺与供应商 tokenizer 一致：`_retained_usage_estimate()` 仅使用同一业务 provider/model 且请求指纹匹配的可信 `model_usage` 前缀校准消息区间，其余回合回退到 `estimate_tokens()` 的字符估算。计划只在完整、已收尾的回合边界切分，当前运行回合和已有摘要覆盖的来源不重复摘要；若切点之前只剩空回合或全部来源已被覆盖，则拒绝计划。计划中的 `estimatedRetainedTokens` 与切点选择同源，仍只是预算估算，不能代替提交前的完整请求预算校验。

启动配置 `BOSS_HARNESS_COMPACTION` 接受 JSON 对象，例如 `{"enabled":true,"triggerPercent":80,"keepRecentTokens":4000,"provider":"openai","model":"summary-model","effort":"low"}`；可省略字段，其余使用默认值。`enabled` 为布尔值，`triggerPercent` 为 1–100 整数，`keepRecentTokens` 为 1–1000000 整数；`provider` 可为 `anthropic`、`openai` 或 `codex`，`model` 是本机线路上的模型 ID，`effort` 只能使用 `none`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max`。显式 effort 必须在 `BOSS_HARNESS_MODEL_LIMITS` 中为摘要模型声明支持；未声明时拒绝开始摘要。拒绝未知字段、重复键和无效类型，错误不显示原配置；空值或只有空白视为未设置，来源不报告为 `environment`。`config/read` 返回解析后的 `autoCompaction`，摘要任务与 checkpoint 记录实际 `summaryProvider`、`summaryModel` 和 `summaryEffort`。嵌入方可传入不可变 `CompactionPolicy`；不传时才读取环境变量。

单次 `turn/start` 可通过 `autoCompaction` 部分覆盖触发策略，例如 `{"threadId":"…","input":"继续分析","autoCompaction":{"enabled":false}}`。`queue/add` 接受相同的部分覆盖字段并随队列项持久化，入队前和后续回合投递时均按 `turn/start` 的同一校验与合并规则应用。只有缺省 `autoCompaction` 才不指定覆盖；显式 null 或其他非法类型在入队前返回 `-32602`，已有请求重试也执行该校验，不改变原队列项；空对象 `{}` 仍是合法的部分覆盖。相同 `clientUserMessageId` 显式重发不同合法覆盖时以 `CLIENT_REQUEST_CONFLICT` 拒绝。覆盖仅适用于该回合，不修改会话或全局默认值；摘要的 provider/model/effort 仍使用启动时的独立摘要配置。未设置摘要配置时继续沿用当前会话模型与推理档位；可显式指定不同摘要线路或档位，模型容量、输入预算和 4096 安全余量按摘要模型计算。摘要完成后，checkpoint 仍须通过当前业务模型的完整请求预算校验才会提交。自动压缩与溢出恢复均使用实际业务回合的 provider 和请求模型查询容量、匹配 usage，不能用摘要 provider 与业务模型拼接容量键；校验包含摘要、保留尾部、system、工具与业务输出预留。失败时以 `COMPACTION_INSUFFICIENT` 暂停，不提交新 checkpoint、不派发后续业务请求。模型路线必须是本机可配置线路，要求 provider factory 创建与业务回合隔离的实例；嵌入方未提供工厂时不执行可选自动摘要，预算超限仍暂停。

自动摘要复用分段生成、来源 digest 和单次提交机制，只替换核对一致的历史前缀。当前回合的用户材料、思考、工具调用及结果、已交付与暂存 steering 保持原对象和顺序；摘要成功后、业务请求前再领取一次新 steering 并重检预算。首批与补领的转向在提交后共用最终请求指纹写入请求边界，确保中断续接可核对所有已投递转向；预算失败与请求拒绝仍按原顺序记录。每个业务请求边界最多启动一次阈值/预算摘要，因此工具返回新结果后会重新检查；超过窗口的恢复另有每回合一次上限。没有可摘要前缀但请求仍在预算内时继续，已启动摘要失败则暂停。任务通过同一压缩任务接口和通知报告进度，`reason` 为 `threshold`、`budget` 或 `overflow`，并附所属 `turnId`。自动摘要线路解析失败以 `COMPACTION_MODEL_UNAVAILABLE` 结束并暂停所属业务回合；显式推理档位不被摘要模型支持时以 `COMPACTION_EFFORT_UNSUPPORTED` 结束，两者都不会把配置错误笼统包装成 `TURN_EXECUTION_FAILED`。中断回合或取消自动摘要都会停止该回合及独立摘要流；已成功提交的 checkpoint 保留，取消后不再请求业务模型。

实际供应商窗口小于本地容量时，仅在 OpenAI 可信错误字段精确返回 `context_length_exceeded`，OpenAI-compatible llama.cpp 返回有界且精确的 `Context size has been exceeded.`，OpenAI-compatible LiteLLM 的 HTTP 400 错误消息有界且同时包含 `litellm.ContextWindowExceededError`、`Context Window exceeded for given call.` 和 `Got > Max Input Tokens`，或 Anthropic 返回类型明确且包含数字上下限的 `prompt is too long` 错误时标记 `CONTEXT_OVERFLOW`。OpenAI 与 Anthropic 的可信 HTTP 413 还接受不超过 512 字符、完整匹配 `Request body too large` 或 `payload too large` 的消息（忽略大小写，可带末尾句点），以处理代理在 token 窗口内按请求字节数拒绝的情况。当前请求未产生任何文本、思考或工具事件且未取消，才允许本回合最多一次压缩后重试；失败请求与重试都计入本回合业务模型请求上限，最后一次失败不再摘要。只继续当前请求，不重新运行已执行工具或复用旧审批。裸 HTTP 413、其他 413 消息、输出 `length`、限流、认证、连接错误、任意其他错误文字或超窗 usage 均不触发此恢复；旧 provider 没有结构化分类时保持普通失败。

供应商终态模型错误会把有界 `errorInfo` 附加到 `session/error` 并保存在 `model_error` 记录中，字段包括 provider、错误来源、可用 HTTP 状态、经过字符集与长度筛选的 provider code，以及可选 `retryable`。OpenAI 流内错误的 HTTP 状态记录为 200；缺少状态或明确分类时省略对应字段。流传输异常还可携带固定原因分类（如读取超时或连接错误）和白名单 errno；界面错误消息使用同一受控分类。此范围也覆盖 SDK 未包装的 HTTP 客户端传输异常，正文读取失败使用固定错误文案，保持原有重试策略。底层 cause 原文、cause 类型名、URL、请求正文、响应头和凭据不会进入诊断元数据。总时限错误沿用独立的明确超时消息，不伪造 SDK cause。另有 `outputObserved` 标记请求是否已向调用方输出文本、思考或工具增量。`retryable` 描述 provider 请求级错误分类，不代表整回合可以重放；现有 OpenAI 内部重试行为不变，Anthropic 不新增重试。只有上文列出的精确 `CONTEXT_OVERFLOW` 条件能触发上下文恢复；状态码或 `retryable` 不会改变审批、工具派发或回合恢复策略。错误记录不包含响应正文、请求、响应头或凭据；明确的额度耗尽 code 标记为不可重试，只有已知的临时限流/服务端错误才标记可重试，含义不明的 HTTP 429 保持未知。

凭据以 `Secret` 包装：`repr` / `str` 固定输出 `<redacted>`，对象不可 JSON 序列化，`dataclasses.asdict()` 无法取出明文；`redact_secrets` 先按调用方给出的原值替换（长度至少 6），再依次抹掉 Bearer 令牌、`sk-` 密钥与 key/token/secret/password 赋值形式，并保留可读的键名与分隔符。

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
