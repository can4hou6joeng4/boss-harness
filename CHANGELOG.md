## 0.2.0-rc.639 - 2026-11-23

- 新增 `scripts/check_community_files.py`（18 项结构、12 项行为），把社区入口的稳定事实变成 CI 不变量：`SUPPORT.md` 必须恰好各引用一次 `bug_report.yml` 与 `feature_request.yml`（引用不存在的模板或重复引用都会失败），`SECURITY.md` 保留私密报告入口、「需要单独授权」的仓库设置边界与上游职责划分，`CONTRIBUTING.md` 保留提交格式与「测试材料仅保留本地」，`CODE_OF_CONDUCT.md` 引用安全政策与贡献约定；四个文件都不得含本机绝对路径。模板重命名后支持页链接 404 不再可能。[Issue #3403](https://github.com/can4hou6joeng4/boss-harness/issues/3403)
- 工作流新增 Verify community files 步骤；技术参考增加同名小节与索引行；隔离变异探针覆盖模板缺失 / 未知 / 重复、报告渠道缺失与措辞调整。源码候选更新为 npm `0.2.0-rc.639` 和 Python `0.2.0rc639`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.638 - 2026-11-23

- 扩展 `scripts/check_readme_stability.py`（22 项结构、11 项行为）：首页候选号规则不再只认 `rc.N` 与固定的 `0.2.0-rc` 前缀，任意 `X.Y.Z-rc` 与 Python 包写法 `X.Y.ZrcN`（如 `0.2.0rc638`）都会被检出；纯 `X.Y.Z` 协议版本不受影响。此前 Python 候选写法可以绕过首页「只写稳定事实」的约定。[Issue #3401](https://github.com/can4hou6joeng4/boss-harness/issues/3401)
- 隔离变异探针覆盖两种候选写法、任意版本前缀与纯三段版本负例；技术参考同步。源码候选更新为 npm `0.2.0-rc.638` 和 Python `0.2.0rc638`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.637 - 2026-11-23

- 扩展 `scripts/check_versions.py`：从 `docs/STATUS.md` 读取最近实际预发布的 tag，要求 `CHANGELOG.md` 中版本高于该 tag 的每个条目都含本仓库 Issue 或 PR 链接，缺失时列出具体版本号；已发布及更早条目豁免，候选变更的 Issue-first 追溯不再只靠人工遵守。[Issue #3399](https://github.com/can4hou6joeng4/boss-harness/issues/3399)
- 隔离变异探针覆盖最新 / 较早候选条目缺链、状态页缺 tag、边界条目豁免与措辞调整；技术参考同步。源码候选更新为 npm `0.2.0-rc.637` 和 Python `0.2.0rc637`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.636 - 2026-11-23

- 扩展 `scripts/check_readme_stability.py`（22 项结构、9 项行为）：首页除中文稳定事实外，还必须保留 `## English overview` 章节，且章节内保留 shell 不 import 内核代码、`main` 是开发分支且源码候选不是发布、桌面从源码构建且没有独立安装包、14 个 allowlist 工具中 13 个只读加一个逐次审批动作四条英文稳定表述。中英文对发布状态与安全边界的描述不再可能单侧漂移。[Issue #3397](https://github.com/can4hou6joeng4/boss-harness/issues/3397)
- 源码候选更新为 npm `0.2.0-rc.636` 和 Python `0.2.0rc636`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.635 - 2026-11-23

- 新增 `scripts/check_status_stability.py`（22 项结构、10 项行为），把「状态页只写稳定事实」变成 CI 不变量：读取 `package.json` 当前版本，禁止 `docs/STATUS.md` 出现当前候选号（npm / Python 两种写法与 `rc.N`）或本机绝对路径；要求保留发布状态、已具备、待完成与待验收、非目标、参与方式五个章节，README / CHANGELOG / 发布约定 / 支持 / 安全 / 贡献 / 技术参考的相对链接，Issue #2351 / #2312 与 Releases 入口，已发布 tag 链接，以及「`main` 是开发分支」「不等同于已发布」「尚未发布到 npm 或 PyPI」三条稳定表述。[Issue #3395](https://github.com/can4hou6joeng4/boss-harness/issues/3395)
- 源码候选更新为 npm `0.2.0-rc.635` 和 Python `0.2.0rc635`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.634 - 2026-11-23

- 扩展 `scripts/check_docs_links.py`：指向本仓库 `blob/main/<path>` 的绝对链接不再按外链跳过，而是按仓库内路径核对存在性，带 `#片段` 的 Markdown 目标同时校验页内锚点；错误文案与相对链接统一为「文档链接不存在 / 页内锚点不存在」，输出统计新增自仓库绝对链接数量。此前 `harness/README.md` 与 PR 模板里的发布约定链接腐烂时不会被发现。[Issue #3393](https://github.com/can4hou6joeng4/boss-harness/issues/3393)
- 源码候选更新为 npm `0.2.0-rc.634` 和 Python `0.2.0rc634`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.633 - 2026-11-23

- `docs/README.md` 补充内核包说明入口 `harness/README.md`；`scripts/check_docs_links.py` 的索引规则从 `docs/*.md` 扩展到 `harness/README.md`（内核包说明，wheel 元数据正文），缺失时失败并点名具体文件。此前内核包说明在仓库内不可达，只能靠全文搜索发现；索引入口被删也不会有检查失败。[Issue #3391](https://github.com/can4hou6joeng4/boss-harness/issues/3391)
- 源码候选更新为 npm `0.2.0-rc.633` 和 Python `0.2.0rc633`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.632 - 2026-11-23

- 新增 `scripts/check_issue_forms.py`（20 项结构、16 项行为），锁定 `.github` 公开入口：两张 Issue 表单的控件类型、`id` / `attributes` 与必填校验，`config.yml` 的 `blank_issues_enabled` 与 `contact_links`（指向本仓库 `blob/main/<path>` 的链接必须能在本地找到对应文件），以及 PR 模板的 `Closes #` 与 `type(scope): 中文描述` 提示。文档改名导致联系入口腐烂或表单被改坏时，`npm run check` 与 CI 会直接失败。[Issue #3389](https://github.com/can4hou6joeng4/boss-harness/issues/3389)
- 源码候选更新为 npm `0.2.0-rc.632` 和 Python `0.2.0rc632`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.631 - 2026-11-23

- 扩展 `scripts/check_docs_links.py`：除「每个脚本恰有一个说明小节」外，还核对「构建前检查」索引表，要求表内脚本集合与 `scripts/check_*.py` 完全一致；缺项、列出不存在的脚本与重复条目分别失败并列出具体脚本名，表外正文中的脚本链接不计入，合成表格覆盖缺项 / 未知 / 重复 / 完整四种情形。新增脚本只写小节、忘记补索引时，索引表悄悄缺项的问题从此会被 `npm run check` 与 CI 拦下。[Issue #3387](https://github.com/can4hou6joeng4/boss-harness/issues/3387)
- 源码候选更新为 npm `0.2.0-rc.631` 和 Python `0.2.0rc631`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.630 - 2026-11-23

- 新增 `scripts/check_readme_stability.py`（17 项结构、7 项行为），把「首页只写稳定事实」变成 CI 不变量：README 不得出现候选号、版本号或更新说明类标题与本机绝对路径，必须保留 CHANGELOG、项目状态、发布约定、许可证、安全、支持、贡献、安装、用户指南与桌面指南等稳定链接，以及开发分支、源码构建、MIT License 与 Releases 的稳定表述。逐版本变化继续只留在 CHANGELOG 与 Release。[Issue #3385](https://github.com/can4hou6joeng4/boss-harness/issues/3385)
- 源码候选更新为 npm `0.2.0-rc.630` 和 Python `0.2.0rc630`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.629 - 2026-11-23

- 新增 `scripts/check_offline_checks.py`（28 项结构、11 项行为），用 AST 扫描全部检查脚本，禁止导入网络客户端模块、套接字连接调用与动态加载，守住「运行检查无需网络、模型凭据或招聘平台账号」的承诺；`socket.gaierror` 等错误类型与 `urllib.parse` 保持允许，行为侧用合成源码核对每条禁令都会检出。检查脚本一旦引入 `requests` 或 `socket.create_connection`，`npm run check` 与 CI 会立即失败，而不是在离线环境里超时。[Issue #3383](https://github.com/can4hou6joeng4/boss-harness/issues/3383)
- 源码候选更新为 npm `0.2.0-rc.629` 和 Python `0.2.0rc629`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.628 - 2026-11-23

- 新增 `scripts/check_notification_dispatch.py`（90 项结构、8 项行为），把内核 33 项通知与界面消费绑定为可核对的契约：内核发送集合与固定清单逐项比对，新增、消失或迁移文件都失败；每项通知必须登记精确的界面分发片段，或带源码锚点的豁免理由，并验证豁免通知确实未被渲染层引用。`item/started`、`context/edited`、`kernel/hookError`、`kernel/shutdown` 四项豁免各自以伴随事件、编辑回执、`observe=False` 发送与关闭观测为锚点。行为侧真实发送创建、重命名、归档、恢复、分支、叶移动与删除通知并核对载荷。内核新增通知会被静默丢给事件归约函数、界面停在上一次状态的问题从此有防线。[Issue #3381](https://github.com/can4hou6joeng4/boss-harness/issues/3381)
- 源码候选更新为 npm `0.2.0-rc.628` 和 Python `0.2.0rc628`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.627 - 2026-11-23

- 新增 `scripts/check_application_item_read.py`（44 项结构、23 项行为），在临时工作区真实构造 `ApplicationService`（`provider=none`），用底层引用函数算出真实摘要后覆盖条目读取入口：`thread/item/result/read` 的投影、分页与 `STALE_RESULT`（含 `currentRef`），以及未知参数 / 缺摘要 / 非工具条目拒绝；`thread/item/content/read` 的 `text` / `thinking` 读取、分页、`STALE_CONTENT`、`part` / `snapshotId` / 未知线程 / 非助手条目拒绝。引用校验若放宽，桌面会按过期视图展示「当前结果」或按自由偏移读取任意内容。[Issue #3379](https://github.com/can4hou6joeng4/boss-harness/issues/3379)
- 源码候选更新为 npm `0.2.0-rc.627` 和 Python `0.2.0rc627`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.626 - 2026-11-23

- 新增 `scripts/check_application_search_export.py`（30 项结构、34 项行为），在临时工作区真实构造 `ApplicationService`（`provider=none`），覆盖搜索与导出读取入口：`thread/search` 的命中投影、空结果、归档默认排除与 `includeArchived=true` 包含、查询 / 参数 / 布尔 / 上限拒绝；`thread/export` 的 13 项投影、Markdown / JSON / HTML 内容契约与格式 / 工具结果 / 大小 / 视图 / 未知线程 / 多余键拒绝；脱敏组验证工作区绝对路径在 markdown 与 json 导出中都被替换且 `redactions.paths >= 1`。归档过滤或导出脱敏漂移会让搜索返回已归档会话，或把本机路径写进对外分享的文档。[Issue #3377](https://github.com/can4hou6joeng4/boss-harness/issues/3377)
- 源码候选更新为 npm `0.2.0-rc.626` 和 Python `0.2.0rc626`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.625 - 2026-11-23

- 新增 `scripts/check_application_usage.py`（17 项结构、18 项行为），在临时工作区真实构造 `ApplicationService`（`provider=none`），写入 `model_usage` 记录并跨分叉核对 `thread/usage/read`：空会话投影与总量键、默认视图、参数 / 视图 / 未知线程 / 坏游标 / 上限拒绝；`log` 视图包含被放弃分支请求并返回 `cacheWaste`，`branch` 视图只聚合当前分支、附叶子投影且不返回线性缓存估计；分页续读。视图参数或聚合范围漂移会让桌面把被放弃分支请求计入当前分支，或给出误导性的缓存浪费估计。[Issue #3375](https://github.com/can4hou6joeng4/boss-harness/issues/3375)
- 源码候选更新为 npm `0.2.0-rc.625` 和 Python `0.2.0rc625`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.624 - 2026-11-23

- 新增 `scripts/check_handler_coverage.py`（13 项结构、6 项行为），把 RPC 方法表与检查覆盖变成 CI 不变量：静态解析 `ApplicationService._register` 的方法表，核对 70 个方法、64 个 handler 与六个内联路由，双向核对注册与声明一致，并要求除本脚本外每个 handler 都在 `scripts/check_*.py` 中被真实调用；行为部分构造真实服务，核对 `server._methods` 与静态表逐项一致、全部可调用，并验证握手与空线程 / 模型列表。新增 handler 忘记注册、注册了却无人覆盖，或检查脚本被删减导致覆盖回退，CI 都会失败。[Issue #3373](https://github.com/can4hou6joeng4/boss-harness/issues/3373)
- 源码候选更新为 npm `0.2.0-rc.624` 和 Python `0.2.0rc624`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.623 - 2026-11-23

- 新增 `scripts/check_application_branches.py`（29 项结构、21 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`（`provider=none`），用分支指针移动与 `append_branch_summary` 构造真实分叉，覆盖分支读取入口：`thread/branches/list` 的空投影与分叉端点投影（`isLeaf` / `containsLeaf` / `forkTurnId` / `branchTurnId` / `selectable` / 输入预览）、`limit=1` 首页与游标续读、参数 / 游标 / 上限 / 未知线程拒绝；`thread/branchSummary/read` 的 15 项投影、参数 / 多余键 / 未知线程拒绝，未知条目与普通条目都返回 -32011 与 `BRANCH_SUMMARY_NOT_FOUND`。分支端点标记或摘要读取若退化为按 id 直接查日志，桌面分支面板会显示错误位置或把普通条目当成摘要正文。[Issue #3371](https://github.com/can4hou6joeng4/boss-harness/issues/3371)
- 源码候选更新为 npm `0.2.0-rc.623` 和 Python `0.2.0rc623`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.622 - 2026-11-23

- 新增 `scripts/check_application_leaf.py`（39 项结构、29 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`（`provider=none`），覆盖分支指针入口：`thread/leaf/read` 的参数与未知线程拒绝及六项投影；`thread/leaf/set` 的参数集合、`turnId` 与 `summarize` 类型、未知线程、未知回合、未结束回合与归档会话（-32004）拒绝；移到已结束回合的 `changed=true` 投影与 `thread/leafChanged` 广播载荷、幂等移动不发事件、`summarize=true` 预检失败返回 -32013 且指针保持不动、回到起点的投影与广播。分支指针若在拒绝条件下移动或在幂等重复时广播，桌面会显示错误的分支位置或触发多余重载。[Issue #3369](https://github.com/can4hou6joeng4/boss-harness/issues/3369)
- 源码候选更新为 npm `0.2.0-rc.622` 和 Python `0.2.0rc622`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.621 - 2026-11-23

- 新增 `scripts/check_application_edit.py`（32 项结构、23 项行为），在临时工作区与状态目录中真实构造 `ApplicationService` 与 `userMessage` 条目，覆盖上下文编辑入口：`context/edit/read` 的参数 / 未知线程 / 未知条目拒绝与八项投影、归档 `canEdit=false`；`context/edit` 的参数集合与 `replacementText` 类型 / `sourceDigest` 格式校验、成功替换后的摘要变化与回读一致、旧摘要重放的乐观并发拒绝、`null` 恢复原文的排除投影与 `context/edited` 广播。编辑入口若放宽摘要比对或恢复语义，会基于过期视图覆写消息或把「恢复原文」变成空文本。[Issue #3367](https://github.com/can4hou6joeng4/boss-harness/issues/3367)
- 源码候选更新为 npm `0.2.0-rc.621` 和 Python `0.2.0rc621`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.620 - 2026-11-23

- 修复 `context/compact`：未知线程先经 `sessions.require_thread` 返回稳定的「会话不存在」，不再抛带状态目录本地路径的 `FileNotFoundError`，与其他入口的错误脱敏约定一致。
- 新增 `scripts/check_application_compaction.py`（65 项结构、30 项行为），覆盖 `context/compact/plan` 的 18 项投影与范围拒绝、`context/compact/start` 的模型格式与空闲 / 并发拒绝、`context/compact/abort` 与 `context/compact/read` 的未知任务 `COMPACTION_JOB_NOT_FOUND`、`context/compact` 的成功提交与检查点投影及重复提交拒绝。压缩入口若放宽线程存在性、参数上限或任务标识校验，会把本地路径泄漏给外壳或重复提交摘要。[Issue #3365](https://github.com/can4hou6joeng4/boss-harness/issues/3365)
- 源码候选更新为 npm `0.2.0-rc.620` 和 Python `0.2.0rc620`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.619 - 2026-11-23

- 新增 `scripts/check_application_turn.py`（34 项结构、22 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`，覆盖回合启动与续接入口：`turn/start` 的未知线程 / 空正文 / 请求编号格式 / 线路与模型不匹配 / 未知技能 / 未知附件 / 请求上限 / 压缩覆盖 / 归档会话拒绝，成功启动的返回投影、`turn/started` 广播与回合记录落库，同一请求编号的 `deduplicated` 重试与不同输入的 `CLIENT_REQUEST_CONFLICT`；`turn/continue` 的参数集合 / 格式 / 未知线程拒绝与已完成回合的 `CONTINUATION_NOT_INTERRUPTED`。启动入口若放宽线路、归档或幂等校验，会产生跨线路请求、空白回合或重复消息。[Issue #3363](https://github.com/can4hou6joeng4/boss-harness/issues/3363)
- 源码候选更新为 npm `0.2.0-rc.619` 和 Python `0.2.0rc619`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.618 - 2026-11-23

- 新增 `scripts/check_application_queue.py`（93 项结构、45 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`，覆盖队列写入、回合中断与审批入口：`queue/add` 的未知线程 / 空正文 / 未知技能 / 归档会话拒绝、`clientUserMessageId` 幂等重试、不同输入与技能组合的 `CLIENT_REQUEST_CONFLICT`；`queue/update` 对排队项生效、对已投递项拒绝；`queue/remove` 取消并回读 `cancelled`；`turn/interrupt` 无回合返回 `{"interrupted": false}`；`turn/steer` / `queue/steer` 无回合的同步拒绝；`approval/list` 的空投影与参数契约；`approval/respond` 的参数集合、布尔校验与 `APPROVAL_INVALID` / `APPROVAL_NOT_FOUND` 区分。队列写入若放宽幂等、状态或审批参数校验，会产生重复消息、改写已投递条目或误裁决。[Issue #3361](https://github.com/can4hou6joeng4/boss-harness/issues/3361)
- 源码候选更新为 npm `0.2.0-rc.618` 和 Python `0.2.0rc618`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.617 - 2026-11-23

- 新增 `scripts/check_application_continuation.py`（19 项结构、22 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`，覆盖续接、队列与关闭入口：`turn/continuation/read` 的不可续接资格、`CONTINUATION_NOT_INTERRUPTED` 与风险提示、参数 / 来源 / 未知线程拒绝；`queue/list` 的空投影、`followUp` / `steering` 条目与按状态计数；`queue/get` 的单项投影与未知标识；`thread/resume` 与 `thread/read` 逐值一致；`shutdown` 的 `stopped`、状态收敛与重复幂等。续接资格或队列计数漂移会让桌面提供不可用的续接入口或显示错误的排队状态。[Issue #3359](https://github.com/can4hou6joeng4/boss-harness/issues/3359)
- 源码候选更新为 npm `0.2.0-rc.617` 和 Python `0.2.0rc617`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.616 - 2026-11-23

- 新增 `scripts/check_application_attachments.py`（36 项结构、25 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`，覆盖附件与运行资源入口：`attachment/add` 的五项投影与工作区外 / 不存在 / 缺失路径拒绝；`attachment/read` 的整份读取、显式摘要的分块读取、未知附件 / 摘要格式 / 分块上限 / 参数集合拒绝；`runtime/resources/read` 的十项空投影与参数拒绝；`approval/list` 的空投影、线程过滤与参数 / 标识上限拒绝。附件入口若放宽工作区路径或分块摘要校验，内核可能读取工作区外文件或返回与引用不一致的内容。[Issue #3357](https://github.com/can4hou6joeng4/boss-harness/issues/3357)
- 源码候选更新为 npm `0.2.0-rc.616` 和 Python `0.2.0rc616`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.615 - 2026-11-23

- 新增 `scripts/check_application_context.py`（27 项结构、26 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`，覆盖上下文与导出入口：`context/read` 的 26 项键与预算 / 来源投影、带 `input` 的预览标记与消息数、未知线程；`context/instructions/read` 的空状态、写入后回读与参数拒绝；`thread/export` 的 Markdown / JSON / HTML 元数据、`redactions` 四类计数、凭据替换、`includeToolResults` 对比、`view=branch` 与格式 / 上限 / 参数集合拒绝。上下文与导出入口若放宽来源标记或脱敏计数，桌面会展示错误的预算状态，导出文件可能带出凭据或明文工具结果。[Issue #3355](https://github.com/can4hou6joeng4/boss-harness/issues/3355)
- 源码候选更新为 npm `0.2.0-rc.615` 和 Python `0.2.0rc615`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.614 - 2026-11-23

- 新增 `scripts/check_application_details.py`（92 项结构、62 项行为），在临时工作区与状态目录中真实构造 `ApplicationService` 并写入已完成回合与三类条目，覆盖会话详情读取入口：`thread/usage/read` 的投影与视图差异，`thread/search` 的命中结构、归档过滤与参数拒绝，`thread/reasoning/read|set` 的档位投影与未声明档位的 `-32012`，`thread/branches/list` 与 `thread/branchSummary/read` 的空投影与 `BRANCH_SUMMARY_NOT_FOUND`，`turn/list|read` 的回合与条目投影，`task/read` 的任务 locator 与 `TASK_NOT_FOUND`，`item/content/read` 与 `tool/result/read` 的摘要校验（`STALE_CONTENT` / `STALE_RESULT`）。详情入口若放宽视图、归档过滤或摘要比对，桌面会显示与引用不一致的用量、回合与正文，且无本地告警。[Issue #3353](https://github.com/can4hou6joeng4/boss-harness/issues/3353)
- 源码候选更新为 npm `0.2.0-rc.614` 和 Python `0.2.0rc614`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.613 - 2026-11-23

- 新增 `scripts/check_application_lifecycle.py`（72 项结构、42 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`，覆盖会话生命周期写入入口：`thread/archive` 的归档标记、重复归档幂等与 `thread/archived` 广播、默认列表排除与 `archived=true` 只列归档，`thread/unarchive` 的恢复标记、广播与列表回归；`thread/name/set` 的标题更新、`thread/renamed` 广播与空白 / 501 字符 / 缺失标题拒绝；`thread/model/set` 的参数集合、不可用线路与目录外模型两类 `-32013`、切换投影、`thread/model/updated` 广播、同值不广播与归档会话拒绝；`thread/fork` 的无结束回合拒绝、按 `turnId` 分支的默认值 / 标题与 `thread/created` 广播；`thread/delete` 的 `THREAD_NOT_FOUND` 数据、成功返回、删除后列表与读取、`thread/deleted` 广播与事件落库；`thread/leaf/read` 的参数集合与分支位置投影。生命周期入口若放宽归档 / 删除忙因或模型线路校验，桌面会看到已归档会话继续切换、删除后仍有残留或跨线路调用，且无本地告警。[Issue #3351](https://github.com/can4hou6joeng4/boss-harness/issues/3351)
- 源码候选更新为 npm `0.2.0-rc.613` 和 Python `0.2.0rc613`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.612 - 2026-11-23

- 新增 `scripts/check_application_writes.py`（49 项结构、41 项行为），在临时工作区与状态目录中真实构造 `ApplicationService`，覆盖应用写入入口：`config/autoCompaction/set` 的字段集合、布尔 / 比例 / 保留额度校验、default / stored 来源写盘与 `autoCompactionSource=stored`、`config/read` 反映新策略、重建服务后设置仍生效，以及 environment / explicit 来源的 `-32004` 拒绝；`skills/create` 的 id 规则、正文类型 / 空白 / 65536 字节上限 / 同名拒绝，`skills/read` 的八键与正文，`skills/write` 的参数集合、摘要格式与不一致拒绝、合法更新，`skills/delete` 的参数、摘要、目录含额外文件拒绝与合法删除；`context/instructions/write` 的参数集合、非字符串、8192 字节上限、写入 `.boss-harness/CONTEXT.md` 后读回与系统错误映射。写入入口若放宽来源保护或摘要比对，会覆盖启动参数或用户手改内容且无本地告警。[Issue #3349](https://github.com/can4hou6joeng4/boss-harness/issues/3349)
- 源码候选更新为 npm `0.2.0-rc.612` 和 Python `0.2.0rc612`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.611 - 2026-11-23

- 新增 `scripts/check_application_reads.py`（57 项结构、64 项行为），在真实构造的 `ApplicationService` 上覆盖握手之后的只读查询入口：`thread/start` 的默认投影、只读策略、标题 / 策略 / 线路 / 模型拒绝与 `thread/created` 事件；`thread/list` 的归档过滤；`thread/read` 的十个响应键、`excludeTurns` 空回合、`snapshot=true` 快照标识与 `itemCount`、布尔参数拒绝与未知线程文案；`items/list` 的空页、`limit` 边界、`snapshotId` 与游标解码 / 越界、日志与快照两页回读；`event/list` 的游标、线程过滤与 `hasMore`；`config/read` 的 20 项字段与默认上限；`tool/list` 的 14 项工具与审批标记；`model/list` 的 `none` 线路；`skills/list` 的空目录报告。只读入口若放宽参数校验或投影漂移，桌面列表、会话恢复与配置页会收到错误数据且无本地告警。[Issue #3347](https://github.com/can4hou6joeng4/boss-harness/issues/3347)
- 源码候选更新为 npm `0.2.0-rc.611` 和 Python `0.2.0rc611`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.610 - 2026-11-23

- 新增 `scripts/check_application_handshake.py`（74 项结构、100 项行为），首次在检查中真实构造 `ApplicationService`（`provider=none`，不启动上游），把内核握手状态机纳入行为对照：`_check_ready` 的放行顺序与冷启动 / 初始化阶段 / 就绪后的固定拒绝，`0.2.0` 两步就绪与 `0.1.0` 单步就绪、缺省版本、六类非字符串版本、不兼容版本的数据字段、双向声明仅在 `0.2.0` 生效；`clientInfo` 与 `capabilities` 的缺失 / 类型 / 空白 / 超长拒绝，`optOutNotificationMethods` 的列表 / 数量 / 元素校验与去重写回；26 项能力全真投影、工具桥 14 个工具与组合标识、模型桥、审批工具与期限、事件游标；`autoCompactionConfig` 按 default / stored / environment / explicit 四种来源区分；`_bridge_description` 的回调异常、非对象、可用性非布尔、不可序列化、NaN、循环引用、16 KiB 上限与深拷贝。握手若放宽顺序或把显式空版本当成不兼容，桌面会在错误的阶段发送请求；能力投影漂移会让界面与内核的可用功能不一致。[Issue #3345](https://github.com/can4hou6joeng4/boss-harness/issues/3345)
- 源码候选更新为 npm `0.2.0-rc.610` 和 Python `0.2.0rc610`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.609 - 2026-11-23

- 新增 `scripts/check_boss_cli_call.py`（51 项结构、39 项行为），在临时目录写入假 CLI 脚本驱动真实 `BossCliTool.call`，把上游进程边界纳入行为对照：参数拼接与 stdin、开始前与中途取消、总时限、16 MiB 输出上限、非 UTF-8 / 空输出 / 坏 JSON / 严格 JSON、七键信封与退出码契约、合法失败信封、`hr chat` 暂停码投影、后代持有管道的排空与不可执行二进制。取消或超时若未收敛会让回合挂起；信封契约放宽会把上游错误当数据落库；暂停码不投影会让摘要补取失败被当成列表成功。[Issue #3343](https://github.com/can4hou6joeng4/boss-harness/issues/3343)
- 源码候选更新为 npm `0.2.0-rc.609` 和 Python `0.2.0rc609`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.608 - 2026-11-23

- 新增 `scripts/check_model_types.py`（62 项结构、46 项行为），直接构造模型层类型契约并执行带逻辑的部分：`token_count` 对缺失、布尔、非整数浮点与非 ASCII 数字视为未上报；`Usage.total` 只计输入与输出；`AssistantMessage` 按块类型投影文本与工具调用；`ModelErrorInfo.event_payload()` 只保留已知事实并保留零值 / 假值；`ModelRecoveryBudget` 的 0–64 边界、预留 / 提交 / 释放、取消与耗尽语义，以及 8 / 16 线程并发下的额度不超发、不丢还。恢复额度若超发会让执行循环无限重试，归还丢失会让后续请求提前失去恢复机会。[Issue #3341](https://github.com/can4hou6joeng4/boss-harness/issues/3341)
- 源码候选更新为 npm `0.2.0-rc.608` 和 Python `0.2.0rc608`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.607 - 2026-11-23

- 新增 `scripts/check_anthropic_stream.py`（128 项结构、85 项行为），用假 `anthropic` 客户端驱动真实 `AnthropicProvider._stream_once`，把 Messages 事件到 `StreamEvent` 的流状态机纳入行为对照：文本流与初始块文本拼接、思考增量与签名差分预算、加密思考块、工具参数分片与初始快照二选一、空参数与坏 JSON、未关闭工具、用量合并与停止原因、`refusal` 固定错误、开始前与中途取消、总时限前缀、529 / 400 / 429 / 连接失败 / 未知异常与文本 / 工具字节预算的错误收敛、`messages.create` 与 `beta.messages.create` 请求路径及请求头过滤，以及重复索引 / 关闭、增量错置、无活动块、空签名增量、空加密块、服务端 fallback 块、非法工具标识与名称、签名与加密块超预算、`message_stop` 后事件、缺少 `message_stop`、工具缺思考签名等协议错误必须以「模型流处理异常（ValueError）」收敛而非抛异常。流状态机若接受错配增量或把未闭合工具写进历史，续接与工具批次匹配会永久失败。[Issue #3339](https://github.com/can4hou6joeng4/boss-harness/issues/3339)
- 源码候选更新为 npm `0.2.0-rc.607` 和 Python `0.2.0rc607`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.606 - 2026-11-23

- 新增 `scripts/check_openai_stream.py`（79 项结构、48 项行为），用假 `openai` 客户端驱动真实 `OpenAIResponsesProvider._stream_once`，把 Responses 事件到 `StreamEvent` 的流状态机纳入行为对照：文本流与完成项文本优先、撤回块过滤、空文本与拒答片段、思考分段延后分隔符、工具调用 `call_id` 标识与参数增量、`arguments.done` 权威与只补后缀、坏 JSON 与来源冲突收敛为「工具调用参数不完整」、截断与用量、缺终态 / 中止 / `response.failed` / 流内 `error` 的固定错误事件，以及身份不一致、重复标识与索引、关闭后起始、增量错置、参数事件越界、重复关闭、终态缺字段与类型不一致等协议错误必须以「模型流处理异常（ValueError）」收敛而非抛异常。流状态机若接受错配的工具身份或把撤回块写进终态消息，执行器会把结果配给错误调用或执行已撤回的工具。[Issue #3337](https://github.com/can4hou6joeng4/boss-harness/issues/3337)
- 源码候选更新为 npm `0.2.0-rc.606` 和 Python `0.2.0rc606`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.605 - 2026-11-23

- 新增 `scripts/check_connections.py`（54 项结构、94 项行为），首次实际构造 `ConnectionChecks`：静态固定 `is_idle` 持锁判定、`read()` 深拷贝与禁用覆盖、`_error()` 公开码白名单与暂停码、`_new_bridge` 弱引用身份校验、`model_calls_disabled` 约束、空闲通知在锁外与关闭默认两秒截止。行为对照用假桥与假 provider 覆盖禁用报告与强制覆盖、浏览器来源投影、登录等待标识复用、九类登录态格式校验与 64 KiB 上限、保存成功 / 读回失败 / 登录态不完整 / 保存中取消、平台风险锁与未登录阻断、本地契约与在线验证、`_error` 白名单、关闭取消与模型检查标记、非协作 worker 按截止时间返回并保留所有权，以及模型检查的成功、空响应、工具调用、错误事件、缺少 provider、请求被拒绝、准备顺序与检查中重复启动。连接检查若放宽错误码白名单或在校验前保存登录态，会把上游细节写进报告或覆盖错误身份。隔离变异探针结构 12/12、行为 16/16（其中「拒绝标记丢失」以未包装异常使检查失败）。脚本注册进构建作业与技术参考。[Issue #3335](https://github.com/can4hou6joeng4/boss-harness/issues/3335)
- 源码候选更新为 npm `0.2.0-rc.605` 和 Python `0.2.0rc605`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.604 - 2026-11-23

- 新增 `scripts/check_turn_append.py`（62 项），覆盖此前没有脚本引用的 `TurnRunner.append_user` / `append_agent` / `finish_tool_call`：静态固定消息条目的父链与 `turnId` / 元数据合并、助手完成通知的 `emit` 分支、工具结算的状态与执行事实、来源、错误码与恢复建议、重试安全推导、模型投影预算、先 `append_tool_revision` 落库再通知与通知失败包装。临时 `SessionStore` 与真实 `TurnRunner` 的行为对照（22 项）覆盖用户 / 助手条目投影、元数据覆盖回合、`emit` 开关与通知字段、成功结算、结果与模型投影、来源与时长、只读失败与写工具失败的 `disposition`、结果未知、缺省调用编号、审批持久化、通知失败上报且结果已落库。结算若按错误码猜测重试安全或通知先于落库，界面会给出错误的重试建议或丢失已执行结果。隔离变异探针结构 14/14、行为 11/11（其中「通知失败不包装」以未包装异常使检查失败）。脚本注册进构建作业与技术参考。[Issue #3333](https://github.com/can4hou6joeng4/boss-harness/issues/3333)
- 源码候选更新为 npm `0.2.0-rc.604` 和 Python `0.2.0rc604`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.603 - 2026-11-23

- 生命周期 hook 检查从 123 项结构、65 个行为场景扩展到 145 项结构、82 个行为场景，新增 `LifecycleHooks` 状态与观察送达覆盖：静态固定 `enabled` / `observes_events` / `closed` / `set_error_sink` 的读取与赋值、`HookFailure.as_dict` 六字段与失败诊断的「脱敏截断 → 锁内取 sink → 锁外调用 → 吞掉 sink 异常」顺序，反向断言失败诊断各执行一次且投影字段唯一。行为对照新增空 hooks 与无 `on_event` hook 的状态、`on_event` hook 实际收到白名单投影事件（正文与工具参数不进入）、空参数投影、关闭排空与关闭后不再送达、重复关闭安全；错误 sink 收到失败对象的字段与 `timedOut` 投影、sink 抛错不改变失败关闭结果、清空 sink 后不再调用。观察状态若与 worker 脱节或错误诊断在锁内调用宿主代码，宿主诊断会丢失或卡住内核。隔离变异探针结构 9/9、行为 8/8（其中「sink 异常不吞」与「as_dict 字段改名」以未包装异常使检查失败）。[Issue #3331](https://github.com/can4hou6joeng4/boss-harness/issues/3331)
- 源码候选更新为 npm `0.2.0-rc.603` 和 Python `0.2.0rc603`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.602 - 2026-11-23

- 新增 `scripts/check_compacted_preview.py`（69 项），覆盖此前没有脚本引用的 `ContextService.compacted_history` 与 `compacted_request`：静态固定历史预览的一次快照投影、不写记录、摘要 / 计划 / 来源 / 线程校验与摘要前缀构造；请求替换的摘要覆盖回合范围、前缀逐条比对、只以 `replace` 生成摘要前缀加实时尾部并保留其余字段。临时 `SessionStore` 两回合会话的行为对照（28 项）覆盖原始历史、预览结构与前缀、保留尾部、不写记录、摘要去空白、全量压缩仅剩摘要，预览与请求的摘要 / 计划 / 来源 / 前缀拒绝，请求其余字段保留、原请求不变，以及同文本前缀按消息内容比对。预览若绕过计划重新读取或不再逐条比对请求前缀，界面可能展示与请求不一致的摘要或静默替换实时尾部。隔离变异探针结构 12/12、行为 7/7（其中「请求计划校验关闭」以未包装异常使检查失败）。脚本注册进构建作业与技术参考。[Issue #3329](https://github.com/can4hou6joeng4/boss-harness/issues/3329)
- 源码候选更新为 npm `0.2.0-rc.602` 和 Python `0.2.0rc602`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.601 - 2026-11-23

- 新增 `scripts/check_branch_material.py`（48 项），覆盖此前没有脚本引用的 `ContextService.branch_summary_material`：静态固定完整记录读取、`abandoned_branch` 推导、空放弃列表 / 未收尾条目 / 无条目三处拒绝、条目投影的续接签名剥离与上下文编辑排除、只读头部、固定 JSON、元数据来源摘要与返回顺序，反向断言各处拒绝与摘要计算各一次且不得只取当前分支。临时 `SessionStore` 真实切换分支的行为对照（21 项）覆盖放弃回合与共同祖先、来源摘要格式 / 计算 / 确定性、空目标放弃链、同叶与未知目标拒绝、未收尾条目拒绝、无条目拒绝、排除编辑后仅保留未排除条目、全部排除拒绝、固定旧快照仍拒绝而固定新快照成功、续接签名剥离与工具执行注解。材料若放宽放弃集合、保留运行中条目或忽略排除，摘要请求会把当前分支或未完成记录当作历史材料。隔离变异探针结构 9/9、行为 10/10。脚本注册进构建作业与技术参考。[Issue #3327](https://github.com/can4hou6joeng4/boss-harness/issues/3327)
- 源码候选更新为 npm `0.2.0-rc.601` 和 Python `0.2.0rc601`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.600 - 2026-11-23

- 新增 `scripts/check_compaction_preview.py`（76 项），覆盖手动压缩的计划切点与材料冻结：静态固定 `compaction_plan` 的薄封装、`_compaction_snapshot` 的参数互斥 / 保留量范围 / 活动回合标识 / 收尾回合 / 条目归属 / 检查点回退 / 切点与候选 / 计划字段，`compaction_material` 的来源摘要校验、覆盖剔除、续接签名剥离、上一检查点收敛与只读头部，以及 `compaction_prompt` 的固定尾句。临时 `SessionStore` 行为对照（25 项）覆盖显式计划字段与确定摘要、默认保留量拒绝、`keepRecentTokens` 选择、互斥与范围错误、空会话、运行中回合、活动回合标识与切点拒绝、材料头部 / JSON 内容 / 固定计划一致、来源摘要不符拒绝、提示尾句，以及有效检查点后仅发送新增条目、上一检查点去掉 `sourceItemIds`、已覆盖切点拒绝、损坏检查点回退完整历史与回退后可重新压缩。切点若放宽到未收尾回合或已覆盖范围，摘要请求会包含未完成历史或重复发送旧条目。隔离变异探针结构 11/11、行为 8/8（其中「传入保留量被忽略」以未包装异常使检查失败）。脚本注册进构建作业与技术参考。[Issue #3325](https://github.com/can4hou6joeng4/boss-harness/issues/3325)
- 源码候选更新为 npm `0.2.0-rc.600` 和 Python `0.2.0rc600`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.599 - 2026-11-23

- 新增 `scripts/check_event_hub.py`（72 项），覆盖此前没有脚本引用的 `EventHub` 事件出口：静态固定 `_emit_locked` 的持久化 → live 投影 → publish → observe 顺序、增量键与 `item/completed` 清除、只吞 `ConnectionError` / `BrokenPipeError`，`publish_persisted` 只重播不追加，`items` 仅叠加运行中条目，`emit_until` 的截止判断与锁释放。假 server、假 hooks 与临时 `SessionStore` 行为对照（23 项）覆盖游标递增、文本 / 思考增量归并、运行条目叠加、发布字段、观察顺序、`publish` / `observe` 开关、完成事件清除与持久投影、重播不追加、连接错误吞掉与运行时错误传播、过期与有效截止。事件顺序或开关若漂移，客户端会收到乱序 / 重复事件，或观察者断开时打断回合。隔离变异探针结构与行为均检出 11/11、9/9。脚本注册进构建作业与技术参考。[Issue #3323](https://github.com/can4hou6joeng4/boss-harness/issues/3323)
- 源码候选更新为 npm `0.2.0-rc.599` 和 Python `0.2.0rc599`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.598 - 2026-11-23

- 上下文编辑检查从 135 项扩展到 159 项，新增 `ContextService.active_summary_job_id` 覆盖：静态固定读取、`_validated_checkpoint` 校验、`ValueError` 回退、空检查点回退与 `bounded_identifier` 返回，反向断言校验与有界标识各一处且不得直接索引未校验标识。临时会话行为对照（13 项）覆盖：无检查点与最新检查点缺省标识返回 `None`，有效检查点返回任务标识，固定条目快照在后续检查点变化后保持原结果；空串、129 字符与非字符串标识返回 `None`，128 字符原样返回；损坏来源摘要、空摘要、未知会话与非法会话 id 返回 `None`。任务标记若绕过校验或不再限制长度，只读用量报告会把失效摘要标成生效中任务，或把超长标识送进客户端。隔离变异探针结构与行为均检出 6/6、7/7。[Issue #3321](https://github.com/can4hou6joeng4/boss-harness/issues/3321)
- 源码候选更新为 npm `0.2.0-rc.598` 和 Python `0.2.0rc598`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.597 - 2026-11-23

- 队列状态检查从 157 项扩展到 183 项，新增 `TurnQueue.defer_capacity` 覆盖：静态固定锁、暂停结算、读取、仅 `delivering` 回队、`turnId` / `failureCode` / `executionStarted` / `inputPersisted` 四字段剥离、状态改写与一次 `_save`，反向断言状态门槛、字段集合与写回各一处且不经 `sessions.append` 直写。临时会话行为对照（11 项）覆盖：不存在项按「队列项不存在」拒绝；排队中与已投递项原样返回且不新增持久条目；投递中项回队保留 id / 正文 / 期望回合 / 客户端幂等 id / 技能并可再次领取；直接写入的投递中记录在回队后剥离四个投递字段、保留其余字段且持久化结果一致。回队若放宽状态门槛或保留投递字段，容量重试会复用失败回合身份或在已投递项上二次投递。隔离变异探针结构 10/10、行为 9/10，剔除暂停结算一项为并发防御、行为层不可达，由结构项覆盖。[Issue #3319](https://github.com/can4hou6joeng4/boss-harness/issues/3319)
- 源码候选更新为 npm `0.2.0-rc.597` 和 Python `0.2.0rc597`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.596 - 2026-11-23

- 待审批检查的过滤、分页与分组校验从 72 项扩展到 88 项，并新增 `next_recoverable_approval_deadline` 覆盖：静态固定锁与索引连接、待删除枚举与 800 上限、`NOT IN` 占位绑定、只扫描未归档会话中断回合的 `MIN(deadline)` 查询、期限列类型守卫与空结果回退，反向断言最小聚合、上限唯一、回合状态不放宽与裁决过滤。临时 `SessionStore` 行为对照（16 项）覆盖：空状态与只有运行中回合时返回 `None`，多个中断回合取最小期限，已完成回合、已裁决审批与归档会话不参与且取消归档后恢复；待删除标记会话排除且移除后恢复，待删除占位超过 800 时整次放弃并在清理后恢复；直接改写索引得到的已裁决行与文本期限列分别被裁决过滤和列类型守卫排除。期限扫描若放宽回合状态、忽略归档或待删除排除，恢复调度会为不可恢复的审批安排唤醒。隔离变异探针结构 11/11、行为 9/9。[Issue #3317](https://github.com/can4hou6joeng4/boss-harness/issues/3317)
- 源码候选更新为 npm `0.2.0-rc.596` 和 Python `0.2.0rc596`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.595 - 2026-11-23

- 条目快照检查从 75 项扩展到 115 项，新增冻结快照读取源覆盖：静态固定 `snapshot_projection` 的删除意图、缺失会话、索引同源、最多 50 回合、逐回合 UTF-8 字节累计、截断标注与损坏重建，以及 `open_snapshot_source` 的事件检查点同源、事件游标、文件打开、完整记录前缀与失败时关闭。行为对照覆盖：默认投影返回元数据与两张表内回合且不截断、`include_turns=False` 返回空回合、极小预算在首个回合前截断、51 个回合只投影 50 个、损坏回合投影重建后返回、删除意图 / 未知会话 / 源文件变化按固定文案拒绝；快照源返回事件游标 `0` 与完整日志内容，追加事件后游标递增到 `1`，末尾半写记录只固定到完整边界，损坏检查点与未知会话按固定文案拒绝。读取源若忽略删除意图、放宽预算或不再核对检查点，冻结快照会包含正在删除的会话、超预算回合或过期游标。隔离变异探针结构 11/11、行为 10/11，失败路径关闭为静态项。[Issue #3315](https://github.com/can4hou6joeng4/boss-harness/issues/3315)
- 源码候选更新为 npm `0.2.0-rc.595` 和 Python `0.2.0rc595`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.594 - 2026-11-23

- 被放弃分支检查从 52 项扩展到 72 项，新增当前分支条目读取覆盖：静态固定 `read_active_entries` 的入口投影与 `_active_entries` 的无叶直返、损坏叶指针跳过、重复编号拒绝、按追加顺序回溯 path、条目归属过滤、会话级条目保留与叶记录排除。临时 `SessionStore` 行为对照：无叶记录保持原条目顺序与全部回合；`set_leaf` 到较早回合后只保留目标分支的回合与条目，被放弃回合条目与叶记录不出现；被放弃分支上的 `thread_info` 与叶后摘要条目跨分支保留；后续损坏叶指针被忽略并沿用上一个有效叶；有叶时重复编号以「会话条目编号重复，无法投影分支」拒绝，无叶时同数据原样返回，空会话返回空列表。分支切换的保留 / 丢弃规则若漂移，界面会看到已放弃回合的条目或丢掉会话级状态。隔离变异探针结构与行为均检出 8/8。[Issue #3313](https://github.com/can4hou6joeng4/boss-harness/issues/3313)
- 源码候选更新为 npm `0.2.0-rc.594` 和 Python `0.2.0rc594`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.593 - 2026-11-23

- 回合分页检查从 76 项扩展到 115 项，新增单回合读取覆盖：静态固定 `SessionStore.get_turn` 的标识符校验、索引刷新、单行查询、缺失拒绝、滚动读取、归属过滤、投影返回与损坏重建重试，`_item_owners` 的前置 pending 队列、运行中 `active`、结束回合清理与先出现归属优先，以及 `turn/read` 处理器的取参、`project_item` 投影与响应预算核对。临时会话行为对照覆盖：前置条目与运行中条目归入第一个回合、显式 `turnId` 只留在所属回合、结束后的游离条目不出现、条目带会话 id，未知回合、非法 / 超长 / 非字符串 `turnId`、非法与不存在的会话按固定文案拒绝，`metadata_json` 损坏后重建并返回同一回合。归属规则或重建重试若漂移，回合详情会静默混入其他回合的条目或把内部错误送给界面。隔离变异探针结构 9/9、行为 7/9，另两项为处理器静态接线，由结构项覆盖。[Issue #3311](https://github.com/can4hou6joeng4/boss-harness/issues/3311)
- 源码候选更新为 npm `0.2.0-rc.593` 和 Python `0.2.0rc593`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.592 - 2026-11-23

- 会话导出隐私检查从 155 项扩展到 189 项：新增 `export_thread` 端到端对照，用临时 `SessionStore` 覆盖 JSON / Markdown / HTML 的格式、视图、媒体类型与默认文件名投影，`includeToolResults` 两态，显式凭据与路径接线（探针值不被通用模式命中）且原文不落文、脱敏计数递增，空会话全零，小上限下长会话的传输拼写预算截断与 `truncated` / 导出条目标注，非法格式、非布尔与零 / 越界上限的固定文案，以及导出前后会话目录清单不变。入口若放宽校验、丢掉脱敏接线、取消截断或写错字节数，导出会静默返回超限或未脱敏的正文。隔离变异探针结构与行为均检出 10/10。[Issue #3309](https://github.com/can4hou6joeng4/boss-harness/issues/3309)
- 源码候选更新为 npm `0.2.0-rc.592` 和 Python `0.2.0rc592`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.591 - 2026-11-23

- 会话导出 Markdown 检查从 111 项扩展到 160 项：静态固定回合状态与审批结论映射、用量行、默认文件名与自动压缩事实的拼装分支，并直接行为对照——五个已知状态、未知字符串与非字符串降级为「状态不明」，审批结论的 `None` 为「等待审批」与三个已知结论，用量行的缺省 / 零请求 / 已验证千分位 / 未上报 / 无可验证分支，默认文件名只含前缀、会话 id、视图与扩展名，压缩事实的开关、阈值、保留量、摘要线路与 effort 组合顺序。坏记录中的未知状态若不再降级，整份导出可能抛异常；用量句式漂移会错报或低估用量。隔离变异探针结构与行为均检出 13/13。[Issue #3307](https://github.com/can4hou6joeng4/boss-harness/issues/3307)
- 源码候选更新为 npm `0.2.0-rc.591` 和 Python `0.2.0rc591`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.590 - 2026-11-23

- 内核工具检查的行为场景从 73 项扩展到 81 项，业务 CLI 路径规范化从 6 项扩展到 13 项：静态固定 `resolve_binary` 的「显式参数 → `BOSS_CLI_BIN` → 并排虚拟环境 → `PATH` → 默认名」回退与 `binary_available` 的路径 / 名称分支，并直接行为对照显式优先、环境变量去空白、空白与不可执行的环境变量回退、并排候选命中与被跳过、`PATH` 回退、默认名，以及绝对路径与 `PATH` 名称的可用性判定。优先级或回退若变化，工具桥会静默执行错误的二进制或漏掉可用的并排安装。隔离变异探针结构与行为均检出 9/9。[Issue #3305](https://github.com/can4hou6joeng4/boss-harness/issues/3305)
- 源码候选更新为 npm `0.2.0-rc.590` 和 Python `0.2.0rc590`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.589 - 2026-11-23

- 工具参数检查从 30 项扩展到 65 项：静态固定 `_validate_value` 的 `anyOf`、类型、枚举、最小值、长度、格式、数组长度、元素递归与唯一性规则，并直接行为对照 22 项——字符串 / 整数 / 数组类型精确匹配、布尔不算整数、无类型规则放行、枚举边界、最小值与最小长度边界、格式命中与拒绝、数组过短 / 过长、元素递归点名下标的路径、唯一性放行与拒绝、`anyOf` 第二分支放行与全部分支拒绝，格式错误不回显原始取值。规则放宽会让非法参数直达上游 CLI，递归失效会让非法元素以整体合法的形式通过。隔离变异探针结构与行为均检出 11/11。[Issue #3303](https://github.com/can4hou6joeng4/boss-harness/issues/3303)
- 源码候选更新为 npm `0.2.0-rc.589` 和 Python `0.2.0rc589`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.588 - 2026-11-23

- 模型配置检查从 87 项扩展到 122 项：静态固定 `resolve_config` 的线路归一与 `_openai_config` 的跳过文件分支，并直接行为对照线路优先级（显式参数 > `BOSS_HARNESS_PROVIDER` > 凭据自动选择）、`codex` / `auto` 别名、未知线路固定错误码、模型覆盖顺序（命令行 > 通用变量 > 线路专属 > 默认）、Anthropic 端点与开关严格性，以及 OpenAI 完整显式配置跳过 Codex 文件、缺端点 / 缺凭据错误码、模型缺省与凭据不进入 `repr`。优先级或别名若改变，命令行与环境变量会静默解析到错误线路。隔离变异探针结构与行为均检出 11/11。[Issue #3301](https://github.com/can4hou6joeng4/boss-harness/issues/3301)
- 源码候选更新为 npm `0.2.0-rc.588` 和 Python `0.2.0rc588`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.587 - 2026-11-23

- 模型配置检查从 51 项扩展到 87 项：静态固定请求时限与输出上限的解析分支，并直接调用 `_request_timeout_seconds` / `_max_tokens` 对照缺省、纯空白、去空白、1 / 3600 边界与正整数边界，非法取值收敛到 `MODEL_REQUEST_TIMEOUT_INVALID` / `MODEL_MAX_TOKENS_INVALID` 且不回显原文；另直接对照 `_configured_model`、`_has_configured_value` 与 `has_anthropic_credential` 的空白遮蔽与空键回退规则。纯空白占位值若被当成已配置，会让模型目录列出实际不可用的线路。隔离变异探针结构检出 9/10、行为检出 9/10，合计 10/10。[Issue #3299](https://github.com/can4hou6joeng4/boss-harness/issues/3299)
- 源码候选更新为 npm `0.2.0-rc.587` 和 Python `0.2.0rc587`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.586 - 2026-11-23

- 会话导出隐私检查从 153 项扩展到 155 项：静态固定 `_wire_bytes` 的 `wire_text` 降级与 `ensure_ascii=False` 计量，并直接对照 ASCII、中文、引号、反斜杠、孤立代理项与表情符号的传输字节数。代理项不降级会让整次导出抛 `UnicodeEncodeError`，改为 ASCII 转义或非 JSON 计量则会让预算与写出字节不一致。隔离变异探针结构与行为均检出 5/5。[Issue #3297](https://github.com/can4hou6joeng4/boss-harness/issues/3297)
- 源码候选更新为 npm `0.2.0-rc.586` 和 Python `0.2.0rc586`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.585 - 2026-11-23

- 工具参数检查从 24 项扩展到 30 项：行为对照经真实注册表拒绝孤立高代理项、低代理项与空字符参数，错误文案统一点名不可传递字符，合法表情符号放行；另用临时可执行脚本验证 CLI 层：合法参数真实执行并返回成功信封，含空字符参数返回 `CLI_ARGUMENT_ERROR` 且脚本未被启动，未启动结果仍按 `not_executed` 结算并暂停回合。隔离变异探针行为检出 7/7（结构片段检出 6/7，`except ValueError` 片段由行为对照补足）。[Issue #3295](https://github.com/can4hou6joeng4/boss-harness/issues/3295)
- 源码候选更新为 npm `0.2.0-rc.585` 和 Python `0.2.0rc585`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.584 - 2026-11-23

- 会话导出隐私检查从 149 项扩展到 153 项：静态要求 `_last_path_segment` 同时剥离 `/` 与 `\`，并直接调用它覆盖 POSIX / Windows 末段、尾部分隔符、混合分隔符、裸文件名、根路径、空串与盘符根。末段提取出错会把正文误当作路径继续脱敏，或让本机路径片段进入导出文件。隔离变异探针结构与行为均检出 5/5。[Issue #3293](https://github.com/can4hou6joeng4/boss-harness/issues/3293)
- 源码候选更新为 npm `0.2.0-rc.584` 和 Python `0.2.0rc584`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.583 - 2026-11-23

- 内核工具检查的行为场景从 56 项扩展到 73 项，直接调用 `create_boss_bundle` 组装一次 `ToolBundle`：bundle id 固定为 `boss`，14 个定义按 `TOOLS` 顺序携带名称、描述与 schema 快照，仅 `boss_hr_greet` 需要审批，处理函数身份与参数校验闭包绑定逐项一致；空参数工具接受空对象、检索工具接受合法关键词并拒绝错类型；默认与带前缀的系统提示走同一 `compose_system_prompt`，`pause_on_result` / `offline_reply` 指向固定实现，`describe_bridge` 的可用 / 不可用投影字段齐全。隔离变异探针行为检出 12/12（结构片段仅覆盖审批与 schema 透传，检出 4/12，其余由组装对照拦截）。[Issue #3291](https://github.com/can4hou6joeng4/boss-harness/issues/3291)
- 源码候选更新为 npm `0.2.0-rc.583` 和 Python `0.2.0rc583`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.582 - 2026-11-23

- 生命周期 hook 检查从 112 项结构、32 个行为场景扩展到 123 项结构、65 个行为场景，新增 `_signal_mode` 的 7 条分类片段、4 条分发片段与 33 项行为对照：仅位置参数按位置传信令，普通 / 仅关键字 / `**kwargs` 按关键字传，名为 `signal` 的 `*signal` / `**signal` 与无可解析签名回退为单参数调用；经 `LifecycleHooks` 分发时回调收到跟随取消事件的 `HookCancellationSignal`，无取消事件不注入信令，`after_tool_call` 始终提供信令，缺少必需参数的写法 fail closed 为 `HOOK_ERROR`，已取消的回合不再启动回调。隔离变异探针结构与行为均检出 9/9。[Issue #3289](https://github.com/can4hou6joeng4/boss-harness/issues/3289)
- 源码候选更新为 npm `0.2.0-rc.582` 和 Python `0.2.0rc582`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.581 - 2026-11-23

- 模型错误检查从 199 项扩展到 208 项，新增 2 条函数片段与 7 项行为对照，直接调用 `_error_payload`：嵌套 `error` 为字典或对象时取内层载荷；缺少 `error` 或显式 `None` 时回退外层且保持对象身份；`0`、空串与标量载荷按原值返回，不被真值判断吞掉。隔离变异探针结构与行为均检出 5/5。[Issue #3287](https://github.com/can4hou6joeng4/boss-harness/issues/3287)
- 源码候选更新为 npm `0.2.0-rc.581` 和 Python `0.2.0rc581`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.580 - 2026-11-23

- 新增 `scripts/check_provider_config.py`，固化模型端点判定与服务端回退开关（51 项，含 33 项行为对照）：`_is_first_party_base_url` 对空值与纯空白返回官方默认，缺少 scheme 时按网络位置补全，主机名精确比较并剥掉尾根点，大小写 / 端口 / 路径 / 查询不影响结果，前缀伪装、userinfo 与畸形 IPv6 判为非官方；`_server_side_fallback` 未设置取默认、空白关闭、开关集合固定，未知取值在严格模式抛出 `MODEL_SERVER_FALLBACK_INVALID` 且不回显原文，非严格模式回退默认。工作流在 Source build 与 Python 矩阵注册该检查，`check_workflows.py` 的脚本覆盖同步为 174。隔离变异探针结构与行为分别检出 12/14、14/14，合计 14/14。[Issue #3285](https://github.com/can4hou6joeng4/boss-harness/issues/3285)
- 源码候选更新为 npm `0.2.0-rc.580` 和 Python `0.2.0rc580`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.579 - 2026-11-23

- 上下文估算检查从 249 项扩展到 259 项，新增 2 条函数片段与 8 项行为对照，直接调用 `_wire_assistant`：只降级 `TextBlock` 并保留签名思考块与工具调用块的对象身份和内容；干净文本的单块与多块消息返回原对象，发生降级时以 `replace` 生成新消息并保留 `stop_reason`。隔离变异探针结构与行为均检出 7/7。[Issue #3283](https://github.com/can4hou6joeng4/boss-harness/issues/3283)
- 源码候选更新为 npm `0.2.0-rc.579` 和 Python `0.2.0rc579`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.578 - 2026-11-23

- 用量汇总检查从 139 项扩展到 161 项，新增 22 项行为对照，直接调用 `_provenance` 与 `_job_metadata`：来源列表只接受字符串、先按 `wire_text` 降级代理项，空串、超长、重复与数量上限都不追加；分支摘要固定 `kind=branchSummary`、只取 `targetTurnId` 且 `origin=model`，其余条目按压缩任务过滤 `reason` 的 `threshold` / `budget` / `overflow` 与 `origin` 的 `user` / `model`，标识经 `bounded_identifier` 限制 128 字符并降级代理项。隔离变异探针结构与行为分别检出 10/12、12/12，合计 12/12（两处 `wire_text` 降级不在静态片段内，由行为对照拦截）。[Issue #3281](https://github.com/can4hou6joeng4/boss-harness/issues/3281)
- 源码候选更新为 npm `0.2.0-rc.578` 和 Python `0.2.0rc578`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.577 - 2026-11-23

- 上下文估算检查从 219 项扩展到 249 项，新增 9 条函数片段、2 项调用点计数与 19 项行为对照：`_budget_message` 按 `inputBudget` 精确整数、非正预算与 `system` / `tools` / `options` 固定开销超过输入预算的顺序选择「通用预算 / 容量不足 / 固定开销」三条固定文案，`ContextBudgetExceeded` 复用该文案并保留原始预算字典；`_canonical_json_text` 复用可编码字节。行为对照覆盖非整数 / 零 / 负数 / 缺字段、坏 `breakdown`、固定开销恰好用尽与超限、未列与非整数字段不计入，以及 canonical 键排序、紧凑分隔、中文不转义、代理项降级与 `NaN` 拒绝。隔离变异探针结构与行为分别检出 7/13、13/13，合计 13/13。[Issue #3279](https://github.com/can4hou6joeng4/boss-harness/issues/3279)
- 源码候选更新为 npm `0.2.0-rc.577` 和 Python `0.2.0rc577`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.576 - 2026-11-23

- 工具结果检查从 99 项行为对照扩展到 120 项，新增 8 条源码片段与 21 项错误预览 / 预算判据行为对照，直接调用 `project_error`、`_command_text` 与 `_fits`：小错误原样复制且不修改输入，`wire_size(error) <= 4096` 阈值内保留全文，超限时只保留 `code` / `message` / `recovery_action` 的 128 / 2000 / 1000 字符前缀与 `detailsOmitted`，camel 键与多余字段丢弃、非字符串按 `str` 转换、孤立代理项降级为 U+FFFD；命令文本非字符串按中文不转义 JSON 拼写，`NaN` 与不可编码对象回退空串；预算判据同时核对普通与 ASCII 转义拼写，`NaN`、不可编码对象与代理项按超限处理。隔离变异探针结构与行为分别检出 12/12、11/12，合计 12/12（4096→4097 阈值放宽在现有边界上不可观察，由结构片段拦截）。[Issue #3277](https://github.com/can4hou6joeng4/boss-harness/issues/3277)
- 源码候选更新为 npm `0.2.0-rc.576` 和 Python `0.2.0rc576`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.575 - 2026-11-23

- 新增 `scripts/check_export_timestamps.py`，固化会话导出的时间戳解析、耗时与审批期限展示（55 项，含 39 项行为对照）：`_parse_timestamp` 只接受非空字符串，`Z` 后缀改写为 `+00:00`，解析结果必须带时区，非法值与朴素时间返回 `None`；`_timestamp_duration` 两端都必须可解析且不倒序，正常差值按毫秒四舍五入；`_deadline_text` 只接受 `int` / `float`（布尔按类型排除），非有限、非正与 `10**400` / `1e300` 溢出按无期限处理，正常值输出 UTC 秒级 ISO 时间；回合头部只在耗时可用时写入 `durationMs`，审批记录只在期限可用时写入 `deadline`。工作流在 Source build 与 Python 矩阵注册该检查，`check_workflows.py` 的脚本覆盖同步为 173。[Issue #3275](https://github.com/can4hou6joeng4/boss-harness/issues/3275)
- 源码候选更新为 npm `0.2.0-rc.575` 和 Python `0.2.0rc575`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.574 - 2026-11-23

- 新增 `scripts/check_tool_bundle.py`，固化工具定义、组合与注册表的校验边界（109 项，含 78 项行为对照）：名称 1–64 字符的 `[A-Za-z0-9_-]`、描述非空白、handler 可调用、审批标记精确布尔、执行模式仅 `sequential` / `parallel` 且并行不得要求审批；结果预算只接受 8192 到 1 MiB 的精确整数；schema 注册时规范化且 `input_schema` 每次返回新副本；参数校验回调收到深拷贝，异常与非 `None` 返回统一为固定文案；组合 id 非空、不超过 128 字符且无空白，成员必须是 `ToolDefinition` 元组且不重名；注册表保留顺序、处理器只读、`read_only` 投影按精确布尔筛选，描述字段与执行模式映射一致。工作流在 Source build 与 Python 矩阵注册该检查，`check_workflows.py` 的脚本覆盖同步为 172。[Issue #3273](https://github.com/can4hou6joeng4/boss-harness/issues/3273)
- 源码候选更新为 npm `0.2.0-rc.574` 和 Python `0.2.0rc574`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.573 - 2026-11-23

- 新增 `scripts/check_application_helpers.py`，固化 `application.py` 的启动默认值与 RPC 入参边界（98 项，含 71 项行为对照）：审批期限的空值 / 空白 / 非有限 / 非正回退与显式值有效性，过期清扫 5 秒基线与 2 的幂退避封顶 60 秒，steering 模式与环境变量非法时不回显原文，分支视图与文本参数的固定错误文案，工作区内外 POSIX 相对路径，技能目录新目录优先 / 旧目录回退 / 文件占位不算目录，检查点归属的重复、满额与 128 / 129 字符边界。工作流在 Source build 与 Python 矩阵注册该检查，`check_workflows.py` 的脚本覆盖同步为 171。[Issue #3271](https://github.com/can4hou6joeng4/boss-harness/issues/3271)
- 源码候选更新为 npm `0.2.0-rc.573` 和 Python `0.2.0rc573`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.572 - 2026-11-23

- Anthropic 适配器检查从 112 项扩展到 160 项，新增 5 条源码片段与 43 项行为对照，直接调用纯辅助函数：工具参数解析对空串、非对象、`NaN` 等非法常量与深嵌套输入收敛为 `None`；状态重试覆盖上下文溢出、明确不可重试、流内 200 与 `408/409/429/500/502/503/504/529` 集合；工具结果保持中文、序列化失败回退字符串并按字符截断到 20000；消息翻译覆盖工具结果、文本、工具调用、签名 / 加密 / 无签名思考与空消息丢弃，前缀摘要匹配才回放思考、无系统提示不过滤。隔离变异探针结构与行为分别检出 20/21、21/21，合计 21/21（400 可重试变异保留原状态码片段，由行为对照拦截）。[Issue #3269](https://github.com/can4hou6joeng4/boss-harness/issues/3269)
- 源码候选更新为 npm `0.2.0-rc.572` 和 Python `0.2.0rc572`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.571 - 2026-11-23

- OpenAI Responses 检查从 107 项扩展到 175 项，新增 6 条源码片段与 62 项行为对照，直接调用解析辅助函数：`None` / 空串解析为空对象，纯空白、截断、非对象 JSON、`NaN` 等非法常量与深嵌套参数收敛为 `None`；completed / in_progress 由工具调用覆盖为 `tool_use`，incomplete 仅 `max_output_tokens` 记 `length`，其余原因与 failed / cancelled 的错误文案保持固定；用量缺失或缺输入 / 输出计数返回 `None`，字符串计数可识别，明细缺失时缓存为 0、思考为 `None`；`CONTEXT_OVERFLOW` 永不重试，结构化结论优先于文本标记，无结论时才回退；思考文本 summary 优先、全空才回退 content，消息文本仅当 text 缺失时用 refusal，预算键与 UTF-8 字节计量固定；错误消息按 `body.error.message` → `body.message` → 异常 message → 异常字符串回退。隔离变异探针结构与行为分别检出 21/21、21/21，合计 21/21。[Issue #3267](https://github.com/can4hou6joeng4/boss-harness/issues/3267)
- 源码候选更新为 npm `0.2.0-rc.571` 和 Python `0.2.0rc571`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.570 - 2026-11-23

- 队列读取检查从 44 项扩展到 50 项，新增 6 条源码片段与 13 项自动压缩行为对照：`enabled` 只接受布尔；`triggerPercent` / `keepRecentTokens` 只接受 0 到 2^53−1 的整数，布尔、负数、越界、浮点与字符串丢弃；未知字段不进入投影；清理后为空或原始值不是字典时整个 `autoCompaction` 字段按缺失处理，空字典仍保留。隔离变异探针结构与行为分别检出 7/8、7/8，合计 8/8（开启值直取在布尔守卫后语义等价，由结构片段拦截）。[Issue #3265](https://github.com/can4hou6joeng4/boss-harness/issues/3265)
- 源码候选更新为 npm `0.2.0-rc.570` 和 Python `0.2.0rc570`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.569 - 2026-11-23

- 工具参数检查从 87 项扩展到 120 项，新增 14 条源码片段与 19 项规整行为对照：anyOf 逐支尝试解码且已匹配值保持原样；空白包裹可解码，尾随内容、`NaN` 等非法常量、对象 / 数组 / null 文本与规则容器类型不符时保留原文并拒绝；数组元素与嵌套数组递归解码；未声明的根字段和对象键不做推测解码；相同与非法 JSON 文本按文本缓存；访问次数与 schema 深度预算超限即拒绝；标量原样透传。隔离变异探针结构与行为分别检出 10/10、8/10，合计 10/10（两处未检出仅改变解析次数与哨兵取值，可观察结果不变）。[Issue #3263](https://github.com/can4hou6joeng4/boss-harness/issues/3263)
- 源码候选更新为 npm `0.2.0-rc.569` 和 Python `0.2.0rc569`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.568 - 2026-11-23

- 工具结果检查从 60 项扩展到 99 项，新增 21 条源码片段与 39 项行为对照：`model_result_content` 的非法 / 越界 / 布尔预算回退默认、超限结果替换成四项引用投影且两种 JSON 拼写都在预算内、`reference_text` 决定引用摘要、itemId 空 / 129 字符 / 孤立代理项不提供读取入口而 128 字符仍可引用、超长 command 截断到预算一半并标注、不可信 `source` 让位、结果预览减半截断；`_merge_outcome` 的无结算原样返回、差异字段补齐、损坏投影拒绝与预算边界；`_unavailable_result` 的错误码 128 字符截断与摘要减半；`model_result_for_item` 的旧投影补状态、写失败 `unknown` / `unknown` 处置、读失败无处置、未执行与结果不确定处置、损坏投影重建、条目预算回退与缺失结果告知。隔离变异探针结构与行为分别检出 14/14、13/14，合计 14/14（代理项变异由最小兜底重复拦截）。[Issue #3257](https://github.com/can4hou6joeng4/boss-harness/issues/3257)
- 源码候选更新为 npm `0.2.0-rc.568` 和 Python `0.2.0rc568`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.567 - 2026-11-23

- 启动自检的构建前门禁不再比较两次实时磁盘余量，避免并发写盘造成偶发误报。最近祖先定位、采样与沿父路径推进仍由源码检查覆盖；运行时自检和低余量告警阈值不变。[Issue #3261](https://github.com/can4hou6joeng4/boss-harness/issues/3261)
- 源码候选更新为 npm `0.2.0-rc.567` 和 Python `0.2.0rc567`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.566 - 2026-11-23

- 准备聚合 `v0.2.0-rc.15` 以来已合入变化的下一轮预发布候选：以固定主干为基线，核对安装入口、兼容限制和分发包验收范围。本轮不改变运行时或 JSON-RPC 协议，候选合入不等于实际发布。[Issue #3259](https://github.com/can4hou6joeng4/boss-harness/issues/3259)
- 源码候选更新为 npm `0.2.0-rc.566` 和 Python `0.2.0rc566`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.565 - 2026-11-23

- 启动自检检查新增 17 条端点 / 目录源码片段与 30 项行为对照：`_is_loopback_host` 的 `localhost.` / `127.0.0.0/8` / `::1` / 大小写归一与 `[::1]` / `0.0.0.0` / 空串拒绝；`_insecure_base_url` 的无值 / `https` / 本机 `http`（含 IPv6 字面量）/ 无 scheme / 畸形 URL / 非回环主机判定；`_directories_overlap` 的相同、父子、反向、兄弟与含 `..` 等价路径；`_free_space` 的已存在目录与非存在嵌套路径沿最近祖先读取。隔离变异探针结构与行为分别检出 7/8、6/8，合计 8/8（两处未检出源于 `urlparse` 已做 scheme 与主机小写归一，片段仍作为静态防护保留）。[Issue #3255](https://github.com/can4hou6joeng4/boss-harness/issues/3255)
- 源码候选更新为 npm `0.2.0-rc.565` 和 Python `0.2.0rc565`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.564 - 2026-11-23

- 上下文估算检查从 192 项扩展到 219 项，新增 10 条组装顺序片段与 17 项行为对照：`messages_from_items` 的空输入、用户与助手正文、运行中 / 失败 / 空正文助手与非字符串用户正文过滤、孤立代理项降级；工具调用按 `toolBatchId` 合并与拆分、用户消息打断批次、运行中工具跳过、缺少 `toolCallId` 回退条目 id、失败工具标记、Anthropic 续接标识过滤、重复 `toolBatchAssistantItemId` 拒绝，以及工具结果中的孤立代理项降级。隔离变异探针结构与行为分别检出 4/8、7/8，合计 8/8。[Issue #3253](https://github.com/can4hou6joeng4/boss-harness/issues/3253)
- 源码候选更新为 npm `0.2.0-rc.564` 和 Python `0.2.0rc564`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.563 - 2026-11-23

- 技能上下文检查从 41 项扩展到 63 项，新增 22 项行为对照：临时目录构造 `SkillCatalog` 后，`load(None)` 与空数组早退；非列表、11 项、含重复的 12 项与非字符串元素返回「skillIds 必须是最多 10 项的字符串数组」，空字符串与未知 id 按不存在拒绝；恰好 10 项被接受，重复 id 只注入一次并保留输入顺序，单双技能正文按固定包装与空行连接，选中名称来自目录；覆写 `list()` 的摘要不一致与绝对 id 分别命中「技能文件已变化；请重新选择」与「技能路径越界」。`bounded_skill_ids` 覆盖非列表回落、非法项先跳过再计数、200 字符上限、去重保序与 10 项截断。隔离变异探针结构与行为分别检出 4/8、8/8，合计 8/8。[Issue #3251](https://github.com/can4hou6joeng4/boss-harness/issues/3251)
- 源码候选更新为 npm `0.2.0-rc.563` 和 Python `0.2.0rc563`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.562 - 2026-11-23

- 新增 `scripts/check_execution_status.py`（37 项）：直接调用 `tool_execution_status` 与 `_annotate_tool_execution`，覆盖六种已知状态的标签与 `executed` 三态、写工具与 `approval` 字段的外部写操作判定、写操作 `outcome_unknown` 的专用文案、非字符串 / 空串 / 超 40 字符状态降级、`executionState` 优先与空串回退、工具调用派生标注不改写输入。新脚本接入 Source build，检查脚本总数从 169 增至 170。隔离变异探针结构与行为分别检出 6/8、7/8，合计 8/8。[Issue #3249](https://github.com/can4hou6joeng4/boss-harness/issues/3249)
- 源码候选更新为 npm `0.2.0-rc.562` 和 Python `0.2.0rc562`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.561 - 2026-11-23

- 转向检查从 28 项扩展到 45 项，新增 17 个行为场景：`promote_to_steering` 提升排队中的后续回合后保留原 id 与输入、清空技能、透传客户端消息标识，结果为 `kind="steering"` / `status="queued"` 且队列列表只有该条；重复提升按类型拒绝；状态非排队、类型非 followUp、带技能、带自动压缩覆盖、`expectedTurnId` 为空或 129 字符、未知队列项分别返回固定文案，恰好 128 字符的 `expectedTurnId` 被接受。隔离变异探针结构与行为分别检出 4/8、8/8，合计 8/8。[Issue #3247](https://github.com/can4hou6joeng4/boss-harness/issues/3247)
- 源码候选更新为 npm `0.2.0-rc.561` 和 Python `0.2.0rc561`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.560 - 2026-11-23

- 浏览器来源检查从 43 项扩展到 48 项：部分大小写值 `Stored-Cookie` 归一为 `stored-cookie`；环境为空串时回落 null；环境为 `AUTO` 时归一为 `auto`；环境合法而显式值非法时仍以固定文案拒绝；允许值集合恰好 `auto` / `existing-browser` / `stored-cookie` 三个。隔离变异探针结构与行为分别检出 4/6、6/6，合计 6/6。[Issue #3245](https://github.com/can4hou6joeng4/boss-harness/issues/3245)
- 源码候选更新为 npm `0.2.0-rc.560` 和 Python `0.2.0rc560`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.559 - 2026-11-23

- 审批条目检查从 92 项扩展到 106 项，新增 14 个校验：`approve` 在 `running` / `approved`、`running` / `executing`、`failed` / `failed`、`completed` / `outcome_unknown` 下有效，`paused` 状态与 `running` / `pending_approval` 组合无效；`deny` 在 `running` / `not_approved` 下有效、`completed` 下无效；`expired` 在 `failed` / `not_executed` 下有效、`completed` 下无效；`turnId` 恰好 128 字符有效、129 字符无效；`deadline=1e-300` 有效；`pending_only=True` 放行已带 `expired` 裁决的待审批形态条目。隔离变异探针结构与行为分别检出 7/8、8/8，合计 8/8。[Issue #3243](https://github.com/can4hou6joeng4/boss-harness/issues/3243)
- 源码候选更新为 npm `0.2.0-rc.559` 和 Python `0.2.0rc559`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.558 - 2026-11-23

- 待审批检查从 41 项行为场景扩展到 44 项：三条待审批时 `limit=1` 只返回最新一条且截断标记为 true；删除标记会话的计数与列表一样以「会话正在删除，暂不可读取」拒绝；索引中的短 `params_digest`（3 字符）行与同一 `item_id` 的两行都按行列出、计数按行累加，列表与计数口径一致。隔离变异探针结构与行为各检出 6/6。[Issue #3241](https://github.com/can4hou6joeng4/boss-harness/issues/3241)
- 源码候选更新为 npm `0.2.0-rc.558` 和 Python `0.2.0rc558`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.557 - 2026-11-23

- 回合分页检查从 69 项扩展到 76 项，新增 7 个行为场景：相同 `first_ordinal` 的游标续页只返回游标之后的回合、序号超过全部回合时返回空页、`limit` 恰好 200 被接受；`first_ordinal=-5` 与 `turn_id=''` 属于合法列值，不触发重建并按列值排序；`metadata_json` 为非对象数组、非 JSON 文本与 `null` 三类损坏都按会话重建并返回对象。隔离变异探针结构与行为分别检出 5/6、6/6，合计 6/6。[Issue #3239](https://github.com/can4hou6joeng4/boss-harness/issues/3239)
- 源码候选更新为 npm `0.2.0-rc.557` 和 Python `0.2.0rc557`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.556 - 2026-11-23

- 回合记录检查从 76 项扩展到 83 项，新增 7 个行为场景：多个回合交错出现时各回合以「上一条已结束回合」为起点（`[0, 0, 3]`）且只有已终态回合带 `boundaryOrdinal`；running 回合不推进起点；两个回合连续终态后第三个回合起点逐个递增；终态后到达的阶段记录仍合并、持久载荷可覆盖 `startedAt` 但不改写 `updatedAt`；`_public_turn` 过滤 `firstOrdinal` / `lastOrdinal` / `boundaryOrdinal` 并保留 `turnId` / `status` / `completedAt`。隔离变异探针结构与行为分别检出 6/8、8/8，合计 8/8。[Issue #3237](https://github.com/can4hou6joeng4/boss-harness/issues/3237)
- 源码候选更新为 npm `0.2.0-rc.556` 和 Python `0.2.0rc556`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.555 - 2026-11-23

- 回合阶段检查从 135 项扩展到 147 项，新增 12 个行为场景：`attempt` 恰好 1 与 1000、`restartLimit` 恰好 0 与 32 被接受并原样写入，`recoveryReason="terminalStateRecovered"` 与 `resumePolicy="closed"` 被接受；`settle_abandoned_turn` 的归属除显式 `turnId` 外还认 running 回合上下文与首个同名回合的回溯，上下文归属的消息与待审批工具条目分别按失败与未执行结算，回合终态后新增的无归属条目不结算且保持 `running`，显式 `turnId` 优先于上下文。隔离变异探针结构与行为分别检出 6/8、8/8，合计 8/8。[Issue #3235](https://github.com/can4hou6joeng4/boss-harness/issues/3235)
- 源码候选更新为 npm `0.2.0-rc.555` 和 Python `0.2.0rc555`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.554 - 2026-11-23

- 会话元数据检查新增 9 个行为场景，用临时目录与合成条目实际执行 `update_thread`、`archive_thread` 与 `unarchive_thread`：合法 `pending_approval` 工具调用归档后审批决策为 `expired`、执行状态为 `not_executed`、错误码为 `APPROVAL_EXPIRED`，且只追加一条裁决与一条归档记录，重复归档不再结算；缺少 `approvalId` 的审批跳过结算只写归档记录；`projectId` 恰好 200 字符、`cwd` 字符串、`model` 为 null 被接受，`toolPolicy` 为 null 以「toolPolicy 必须是 readOnly 或 approval」拒绝。隔离变异探针结构与行为分别检出 7/8、8/8，合计 8/8。[Issue #3233](https://github.com/can4hou6joeng4/boss-harness/issues/3233)
- 源码候选更新为 npm `0.2.0-rc.554` 和 Python `0.2.0rc554`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.553 - 2026-11-23

- 会话日志检查新增 10 个行为场景，用临时文件与内存流实际执行 `_iter_bounded_raw_lines_from_handle`、`_iter_bounded_lines`、`_complete_record_limit` 与 `_decode_session_record`：`byte_limit` 为零返回空列表、为负以「JSONL 快照长度无效」拒绝；约 70 KiB 的单行跨 64 KiB 读取块完整产出；快照截在长行中间时残段丢弃；裸 `\r` 在默认模式保留在行内；真实 UTF-8 文件中的中文与空行按行解码；首字节换行边界返回 1；非字符串 `type` / `id` / `timestamp` 均以「格式无效」拒绝。隔离变异探针结构与行为分别检出 5/9、8/9，合计 9/9。[Issue #3231](https://github.com/can4hou6joeng4/boss-harness/issues/3231)
- 源码候选更新为 npm `0.2.0-rc.553` 和 Python `0.2.0rc553`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.552 - 2026-11-23

- 删除清理检查新增 7 个行为场景，用临时目录与合成硬链接实际执行 `_remove_private_temporaries` 与 `_remove_thread_files`：空列表不读取目标；目标为符号链接时以「无法确认的硬链接临时文件」拒绝且文件保留；列表中前一个普通文件删除成功、后一个悬空硬链接被拒绝时保持各自实际状态；会话主体、删除标记与事件日志三类临时文件分别与主文件组成硬链接对时全部清理且主文件保留。隔离变异探针结构与行为分别检出 9/9、7/9，合计 9/9。[Issue #3229](https://github.com/can4hou6joeng4/boss-harness/issues/3229)
- 源码候选更新为 npm `0.2.0-rc.552` 和 Python `0.2.0rc552`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.551 - 2026-11-23

- 删除标记检查新增 12 个行为场景，用临时目录与合成标记实际执行 `_read_delete_intent`、`_write_delete_intent`、`_pending_deletion_ids` 与重启恢复：阻塞列表忽略非法名称；恰好 1 MiB 的标记可读、超出一字节拒绝；乱序重复摘要读回为排序去重结果；损坏标记拒绝覆盖且字节不变；重开存储把未读取的 0644 标记收紧为 0600；两个合法标记中一个目标文件为硬链接时该标记保留、另一个完成删除且存储正常打开。隔离变异探针结构与行为分别检出 7/10、9/10，合计 10/10。[Issue #3227](https://github.com/can4hou6joeng4/boss-harness/issues/3227)
- 源码候选更新为 npm `0.2.0-rc.551` 和 Python `0.2.0rc551`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.550 - 2026-11-23

- 事件日志重写检查新增 13 个行为场景，用临时目录与合成事件实际执行 `_rewrite_events_for_deletion` 与 `_event_high_water`：删除标记事件在 `deletedThreadId` 不一致或额外携带 `threadId` 时拒绝且不留临时文件；日志含 `eventCursor` 为 `2**63 - 1` 的记录时以游标耗尽拒绝并保留原文件；硬链接日志拒绝且链接与内容不变；空行保留、缺尾残段丢弃且不推进删除事件游标；索引行清空后高水位仍取自增序列。隔离变异探针结构与行为分别检出 11/13、12/13，合计 13/13。[Issue #3225](https://github.com/can4hou6joeng4/boss-harness/issues/3225)
- 源码候选更新为 npm `0.2.0-rc.550` 和 Python `0.2.0rc550`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.549 - 2026-11-23

- 事件分页检查新增字节预算与索引损坏行为场景，用临时目录与合成 `SessionStore` 实际执行 `events_after`：3 MiB + 2 MiB 参数累计超预算时一页只返回首条并给出 `hasMore` 与推进后的游标、续页继续第二条，单条 5 MiB 参数首行超预算仍返回且正常收尾；方法筛选恰好 16 个通过；`params_json` 为非对象数组、`method` 为空串两类损坏均触发索引重建，并逐条校对重建后的 `eventCursor` 与游标列。隔离变异探针结构与行为分别检出 11/13、12/13，合计 13/13。[Issue #3223](https://github.com/can4hou6joeng4/boss-harness/issues/3223)
- 源码候选更新为 npm `0.2.0-rc.549` 和 Python `0.2.0rc549`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.548 - 2026-11-23

- JSON-RPC 传输检查新增 74 个行为场景，用内存流与合成帧实际执行 `_decode_json_frame`、`describe_failure` 与 `JsonRpcServer` 的写出、派发、请求响应关联与关闭路径：重复键 / `NaN` / `Infinity` / 非有限浮点 / 深度边界 / 孤立代理项拒绝，`OSError` 固定原因与路径隐藏，`ValueError` / `RpcError` / 普通异常的分类码与 `data`，响应与 stderr 的凭据脱敏，`RESPONSE_TOO_LARGE` / `RESPONSE_INVALID` 降级且 handler 只执行一次，超大 id 回退无 id，字节缓冲优先，通知白名单，关闭后请求拒绝与在途取消，计时器启动失败 fail closed，读取循环对空行、坏帧与缺 LF 帧的处理。隔离变异探针结构与行为分别检出 12/16、16/16，合计 16/16。[Issue #3221](https://github.com/can4hou6joeng4/boss-harness/issues/3221)
- 源码候选更新为 npm `0.2.0-rc.548` 和 Python `0.2.0rc548`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.547 - 2026-11-23

- 摘要发布检查新增 48 个行为场景，用临时目录与合成 `SessionStore` 实际执行 `append_checkpoint`：入口与条目类型校验、成功发布保留原记录且回调在提交后执行、尾部半条记录截到最后一个完整边界、没有完整边界时拒绝、符号链接 / 硬链接 / 待删除会话拒绝、构造条目与发布前的源变化拒绝、`os.replace` 异常按原始 / 候选 / 其他 inode 分别重抛、视为提交与 `CheckpointCommitUncertain`、提交后目录同步 / 回调 / 索引刷新失败转换为 `CheckpointCommittedError`、临时文件清理。隔离变异探针结构与行为分别检出 12/14、14/14，合计 14/14。[Issue #3219](https://github.com/can4hou6joeng4/boss-harness/issues/3219)
- 源码候选更新为 npm `0.2.0-rc.547` 和 Python `0.2.0rc547`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.546 - 2026-11-23

- 会话写入检查新增 40 个行为场景，用临时目录与合成 `SessionStore` 实际执行 `append_many` / `append` / `_write_new` / `append_attachment`：批次与上限校验、空批次早退、严格字节边界与超限文件不变、缺失结尾换行的 1 字节前缀与残段截断、单条追加、新建冲突不覆盖且清理临时名、NaN 载荷、条目与会话头单行上限、附件类型 / 摘要 / 发布器校验、发布先于引用行、发布失败不留引用、历史损坏时发布器不被调用。隔离变异探针结构与行为分别检出 12/14、14/14，合计 14/14。[Issue #3217](https://github.com/can4hou6joeng4/boss-harness/issues/3217)
- 源码候选更新为 npm `0.2.0-rc.546` 和 Python `0.2.0rc546`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.545 - 2026-11-23

- `_purge_unreferenced_attachments` 在读取目录与扫描会话前把候选收敛为 64 位小写十六进制摘要：相对越界、绝对路径、大写、短摘要、非字符串、不可哈希与非序列候选以固定文案「附件清理候选摘要格式无效」拒绝；合法候选与空清单行为不变。附件边界检查同步新增 9 个行为场景（合计 36 个），并确认附件目录外的状态库不受影响。对照 Pi 固定提交的会话管理无对应机制，差异记入 `UPSTREAM.md`。[Issue #3215](https://github.com/can4hou6joeng4/boss-harness/issues/3215)
- 源码候选更新为 npm `0.2.0-rc.545` 和 Python `0.2.0rc545`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.544 - 2026-11-23

- 附件边界检查新增 27 个行为场景，用临时目录、合成会话 JSONL 与附件对象构造真实 `SessionStore` 执行 `_purge_unreferenced_attachments` 与 `cleanup_unreferenced_attachments`：共享引用在 CRLF、重复记录与多会话下保留，未引用 / 多候选 / 重复候选对象删除，缺失对象与缺失目录静默、空候选不扫描、待删除会话跳过且标记保留，非附件记录 / 空载荷 / 非法与大写摘要不算引用，损坏会话、非对象载荷、链接与目录输入的 fail closed 文案，以及公开包装的错误传播。隔离变异探针结构与行为分别检出 7/12、12/12，合计 12/12。[Issue #3213](https://github.com/can4hou6joeng4/boss-harness/issues/3213)
- 源码候选更新为 npm `0.2.0-rc.544` 和 Python `0.2.0rc544`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.543 - 2026-11-23

- 会话分叉检查新增 57 个行为场景，以临时目录与合成 JSONL 构造真实 `SessionStore` 并执行 `fork_thread`：活动分支与指定较早回合的选择、合成叶分叉被放弃回合、运行中回合 / 未收尾条目 / 未决审批 / 拆开工具批次 / 非法续接偏移的拒绝、内核专用记录排除、`threadId` / `approvalId` / `parentId` 改写、迟到修订归属、续接边界摘要重算与删除、来源日志只读。隔离变异探针结构与行为分别检出 7/20、20/20，合计 20/20。[Issue #3211](https://github.com/can4hou6joeng4/boss-harness/issues/3211)
- 源码候选更新为 npm `0.2.0-rc.543` 和 Python `0.2.0rc543`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.542 - 2026-11-23

- 内核工具检查新增 56 个行为场景，实际执行 `validate_arguments`、`_decode_cli_envelope`、`resolve_browser_source_override`、`_executable_path`、`resolve_binary`、`tool_handlers`、`approval_required_tools` 与 `should_pause`：信封非有限数字 / 重复键 / 代理项 / 深度边界、浏览器来源规范化、可执行文件与符号链接判定、参数类型 / 枚举 / 数组 / 额外字段、审批集与暂停代码。隔离变异探针结构与行为分别检出 1/15、15/15，合计 15/15。[Issue #3209](https://github.com/can4hou6joeng4/boss-harness/issues/3209)
- 源码候选更新为 npm `0.2.0-rc.542` 和 Python `0.2.0rc542`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.541 - 2026-11-23

- 冻结快照检查新增 76 个行为场景，实际执行解码、投影、分页与存储生命周期：宽容 UTF-8、条目载荷 / id 损坏映射、行切分与残段丢弃、源读取上限与回绕、投影字段裁剪、并发构建上限、TTL 清理、分支失效墓碑、按快照 / 会话删除与关闭清理。隔离变异探针结构与行为分别检出 10/14、14/14，合计 14/14。[Issue #3207](https://github.com/can4hou6joeng4/boss-harness/issues/3207)
- 源码候选更新为 npm `0.2.0-rc.541` 和 Python `0.2.0rc541`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.540 - 2026-11-23

- 离线指令与领域提示检查新增 51 个行为场景，实际执行 `offline_reply`、`_parse_command` 与 `compose_system_prompt`：命令解析、`/search` 空参数与关键词透传、七项只读指令映射、`/candidates` 查询形状、两种降级文案、大小写敏感、只读表禁令、默认 / 自定义提示与 UTF-8 字节预算、控制字符过滤。隔离变异探针结构与行为分别检出 11/12、12/12，合计 12/12。[Issue #3205](https://github.com/can4hou6joeng4/boss-harness/issues/3205)
- 源码候选更新为 npm `0.2.0-rc.540` 和 Python `0.2.0rc540`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.539 - 2026-11-23

- 附件添加检查新增 66 个行为场景，实际执行 `AttachmentStore.add` 与配额判定：工作区路径、保留段与 `.env*` 前缀、缺失文件 / 目录 / 越界符号链接、2 MiB 与 UTF-8 边界、记录字段与对象落盘、同内容去重、空文件、字节 / 对象配额与等量上限、发布失败清理与计数回退、清理异常隔离、附件目录守卫、对象三层校验，以及数值环境变量解析。隔离变异探针结构与行为分别检出 11/12、10/12，合计 12/12。[Issue #3203](https://github.com/can4hou6joeng4/boss-harness/issues/3203)
- 源码候选更新为 npm `0.2.0-rc.539` 和 Python `0.2.0rc539`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.538 - 2026-11-23

- 附件分页读取检查新增 56 个合成行为场景，实际执行 `AttachmentStore.read_chunk` 与 `read`：完整一页与 `contentRef` 五字段、按字符分页、后续游标载荷与末页终止、`limit` 与 `sha256` 边界、`-32011` 陈旧引用、十一类无效游标、七类损坏记录、对象缺失 / 替换 / 非 UTF-8、孤立代理项名称降级与 `include_content` 开关。隔离变异探针结构与行为分别检出 11/12、12/12，合计 12/12。[Issue #3201](https://github.com/can4hou6joeng4/boss-harness/issues/3201)
- 源码候选更新为 npm `0.2.0-rc.538` 和 Python `0.2.0rc538`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.537 - 2026-11-23

- 工具桥清理检查新增 17 个合成行为场景，实际执行 `BridgeLifecycle`：`None` 早退、同一对象只清理一次、`close` / `dispose` 优先关系、无钩子安全、异常只记录类型名且不落原文、钩子在锁外可并发清理、不可弱引用对象不登记与死引用剔除。隔离变异探针结构与行为分别检出 9/9、7/9，合计 9/9。[Issue #3199](https://github.com/can4hou6joeng4/boss-harness/issues/3199)
- 源码候选更新为 npm `0.2.0-rc.537` 和 Python `0.2.0rc537`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.536 - 2026-11-23

- 模型结果读取工具检查新增 31 个行为场景，实际执行 `model_tool_specs` 与 `validate_model_result_read`：保留既有工具并追加只读工具、重名拒绝、独立参数副本、`itemId` / `sha256` / `cursor` / `limit` 边界、缺失必填 / 额外字段 / 非对象 / 空字符的固定错误，以及工具名称、schema 关键字段、64 KiB 上限与描述一致。隔离变异探针结构与行为均检出 12/12。[Issue #3197](https://github.com/can4hou6joeng4/boss-harness/issues/3197)
- 源码候选更新为 npm `0.2.0-rc.536` 和 Python `0.2.0rc536`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.535 - 2026-11-23

- 运行时容量检查新增 62 个合成行为场景，实际执行 `RuntimeManager`：双上限与关闭拒绝、预留登记、同对象释放与旧回合不释放新槽位、三种回收路径、idle 通知、回合不符拒绝、幂等中止认领与回调绑定、关闭时认领但不绑定中断、停止派发幂等、容量 worker 启动 / 唤醒 / 关闭停止，以及 `stop` 与 `wait_for_stop` 截止返回。隔离变异探针结构与行为分别检出 12/12、11/12，合计 12/12。[Issue #3195](https://github.com/can4hou6joeng4/boss-harness/issues/3195)
- 源码候选更新为 npm `0.2.0-rc.535` 和 Python `0.2.0rc535`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.534 - 2026-11-23

- 关闭检查新增 25 个真实线程场景，实际执行 `TrackedAbort` 与 `join_until`：回调优先、provider 回退、缺少钩子、回调 / 收尾异常收敛、`done` 与 `on_done` 单次、重复与并发启动只派发一次、工作线程 daemon 与名称，以及跳过 `None` / 当前线程 / 未启动 / 重复线程、按截止时间返回且不等待存活 worker。隔离变异探针结构与行为均检出 9/9。[Issue #3193](https://github.com/can4hou6joeng4/boss-harness/issues/3193)
- 源码候选更新为 npm `0.2.0-rc.534` 和 Python `0.2.0rc534`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.533 - 2026-11-23

- 占用锁检查新增 15 个临时状态目录场景，实际创建并竞争 `.owner.lock`：锁文件与目录私有权限、同进程第二个持有者非阻塞拒绝、失败实例释放描述符、首个持有者不受影响、关闭后保留锁文件并可重新获取、重复 / 未初始化关闭与析构释放。隔离变异探针结构与行为均检出 10/10。[Issue #3191](https://github.com/can4hou6joeng4/boss-harness/issues/3191)
- 源码候选更新为 npm `0.2.0-rc.533` 和 Python `0.2.0rc533`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.532 - 2026-11-23

- 索引持久化检查新增 25 个临时状态目录场景，实际创建并迁移 SQLite 索引：新建索引版本与必需表索引、文件 / 目录私有权限、外键与忙等同步 WAL、逐操作独立连接、事务提交与回滚、级联删除、唯一约束、非法 UTF-8 降级、版本 1 迁移与重复打开幂等、未来版本拒绝。隔离变异探针结构与行为分别检出 10/12、12/12，合计 12/12。[Issue #3189](https://github.com/can4hou6joeng4/boss-harness/issues/3189)
- 源码候选更新为 npm `0.2.0-rc.532` 和 Python `0.2.0rc532`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.531 - 2026-11-23

- 分支投影检查新增 15 个合成条目场景，实际执行 `_active_entries`：首 / 次分支回溯、伪造 `parentId` 忽略、跨分支保留、回合 / 阶段 / 工具批次 / 上下文编辑 / 摘要检查点归属、迟到修订、无归属条目、损坏叶沿用、缺目标空路径与重复编号拒绝。隔离变异探针合计检出 12/12。[Issue #3187](https://github.com/can4hou6joeng4/boss-harness/issues/3187)
- 源码候选更新为 npm `0.2.0-rc.531` 和 Python `0.2.0rc531`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.530 - 2026-11-23

- 会话缓存检查新增 25 个临时场景，实际执行 `read_entries` 与快照读取：完整边界写缓存、命中返回副本、追加与外部追增接续、截断 / 同尺寸 / 旧前缀非换行 / inode 替换不返回过期条目、尾残段与损坏行不推进缓存、边界判定、最近使用淘汰与快照副本。隔离变异探针合计检出 16/16。[Issue #3185](https://github.com/can4hou6joeng4/boss-harness/issues/3185)
- 源码候选更新为 npm `0.2.0-rc.530` 和 Python `0.2.0rc530`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.529 - 2026-11-23

- 请求身份检查新增 47 个临时合成场景，实际执行 `valid_client_id`、`RequestIdentity.receipt` 与 `resolve_request`：编号整串匹配、空身份短路、外部 `queue-<id>` 不能认领队列、队列 / 输入 / 回合身份冲突、转向拒绝、两轮链接收敛、重复身份歧义、持久事实冲突与失败回执字段。隔离变异探针合计检出 18/18。[Issue #3183](https://github.com/can4hou6joeng4/boss-harness/issues/3183)
- 源码候选更新为 npm `0.2.0-rc.529` 和 Python `0.2.0rc529`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.528 - 2026-11-23

- 待审批检查新增 41 个临时合成场景，实际执行共享过滤、列表分页与分组计数：已裁决 / 过期 / 未运行回合 / 归档会话排除、中断回合计入、会话过滤与跨会话分组、`limit` 边界与截断、条目 id 倒序、删除标记会话与占位超限放弃，以及直接写入索引的畸形行排除。隔离变异探针合计检出 20/20。[Issue #3181](https://github.com/can4hou6joeng4/boss-harness/issues/3181)
- 源码候选更新为 npm `0.2.0-rc.528` 和 Python `0.2.0rc528`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.527 - 2026-11-23

- 任务归属检查新增 57 个临时合成记录场景，实际执行恢复策略、自动压缩归属、队列关系、回合 / 队列快照与用户消息引用：unknown 优先、进程持有、delivered_as / targets、重复与身份冲突、阶段绑定、超限溢出与不投影正文。隔离变异探针合计检出 20/20。[Issue #3179](https://github.com/can4hou6joeng4/boss-harness/issues/3179)
- 源码候选更新为 npm `0.2.0-rc.527` 和 Python `0.2.0rc527`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.526 - 2026-11-23

- 排队投影检查新增 40 个临时合成记录场景，实际执行 `queue_record`、`queue_view_record` 与 `project_queue`：坏记录跳过、代理项降级、白名单、技能与自动压缩收敛、暂停来源、输入截断、暂停优先、终结窗口与显式计数。隔离变异探针合计检出 15/15。[Issue #3177](https://github.com/can4hou6joeng4/boss-harness/issues/3177)
- 源码候选更新为 npm `0.2.0-rc.526` 和 Python `0.2.0rc526`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.525 - 2026-11-23

- 设置持久化检查新增 32 个临时状态目录场景，实际执行深度检测、有界读取、配置加载与原子保存：损坏 / 非法 UTF-8 / 超限 / 深层配置回退、无关键保留、缺少字段 / 未知字段 / 非法值 / 不可编码 / 合并超限拒绝与临时文件清理。隔离变异探针合计检出 12/12。[Issue #3175](https://github.com/can4hou6joeng4/boss-harness/issues/3175)
- 源码候选更新为 npm `0.2.0-rc.525` 和 Python `0.2.0rc525`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.524 - 2026-11-23

- 会话日志检查新增 34 个离线行为场景，实际执行编码、严格解码、有界读取、快照边界与追加前截断：完整行与残段丢弃、单行与残段超限、快照长度恰等与不完整、CRLF、重复会话头与各类坏行。隔离变异探针合计检出 14/14。[Issue #3173](https://github.com/can4hou6joeng4/boss-harness/issues/3173)
- 源码候选更新为 npm `0.2.0-rc.524` 和 Python `0.2.0rc524`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.523 - 2026-11-23

- 摘要规划检查新增 28 个离线行为场景，实际执行 `SummaryPlanner` 的四路输出约束、字符预算公式、逐字片段与来源摘要、滚动摘要上限、预算不足与来源末尾拒绝，以及孤立代理项降级。隔离变异探针合计检出 9/9。[Issue #3171](https://github.com/can4hou6joeng4/boss-harness/issues/3171)
- 源码候选更新为 npm `0.2.0-rc.523` 和 Python `0.2.0rc523`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.522 - 2026-11-23

- 生命周期 hook 检查新增 32 个离线行为场景，执行策略与观察上下文的完整复制、只读视图、脱敏、截断、键项与深度省略、字节 / 节点 / 深度边界，以及环引用、非字符串键、代理项、非有限浮点、不支持类型与非映射顶层的拒绝。隔离变异探针合计检出 12/12。[Issue #3169](https://github.com/can4hou6joeng4/boss-harness/issues/3169)
- 源码候选更新为 npm `0.2.0-rc.522` 和 Python `0.2.0rc522`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.521 - 2026-11-23

- 索引修复检查新增 7 个临时状态场景，实际执行拒绝、成功修复、重建失败回滚与损坏会话跳过，并核对清单摘要、日志不变和事件游标。结构、行为与合计检出分别为 9/10、9/10、10/10。[Issue #3167](https://github.com/can4hou6joeng4/boss-harness/issues/3167)
- 源码候选更新为 npm `0.2.0-rc.521` 和 Python `0.2.0rc521`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.520 - 2026-11-23

- README 与安装指南为首次桌面验证给出共用的临时内核状态路径，自检通过后再用同一路径启动，并说明如何恢复平时的启动方式。[Issue #3165](https://github.com/can4hou6joeng4/boss-harness/issues/3165)
- 源码候选更新为 npm `0.2.0-rc.520` 和 Python `0.2.0rc520`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.519 - 2026-11-23

- 启动自检新增 19 个离线行为场景，覆盖运行参数的错误顺序、空白、回退警告、无效配置脱敏和终端报告结论。隔离探针检出 10/10 个模拟回归。[Issue #3163](https://github.com/can4hou6joeng4/boss-harness/issues/3163)
- 源码候选更新为 npm `0.2.0-rc.519` 和 Python `0.2.0rc519`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.518 - 2026-11-23

- 模型禁用检查新增 5 个离线启动自检场景，覆盖显式 `none`、自动回退、严格模式退出码及 OpenAI 备用线路的配置与 SDK 提示。隔离探针检出 10/10 个模拟回归。[Issue #3161](https://github.com/can4hou6joeng4/boss-harness/issues/3161)
- 源码候选更新为 npm `0.2.0-rc.518` 和 Python `0.2.0rc518`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.517 - 2026-11-23

- 工具结果信封新增 27 项离线行为检查，涵盖嵌套字段深拷贝、Unicode、恢复动作规范化、深度边界和非法输入的统一错误。隔离探针检出 12/12 个模拟回归。[Issue #3159](https://github.com/can4hou6joeng4/boss-harness/issues/3159)
- 源码候选更新为 npm `0.2.0-rc.517` 和 Python `0.2.0rc517`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.516 - 2026-11-23

- 工具结果修订检查新增 10 个离线恢复场景，核对正常追加、写前失败后重试、写后报错时复用已有结果、同 ID 冲突、日志损坏、同步失败及重试耗尽。隔离变异探针检出 12/12。[Issue #3157](https://github.com/can4hou6joeng4/boss-harness/issues/3157)
- 源码候选更新为 npm `0.2.0-rc.516` 和 Python `0.2.0rc516`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.515 - 2026-11-23

- 队列状态检查新增 29 项行为对照。检查在临时会话存储上直接调用 `TurnQueue`，覆盖新增与客户端幂等、技能去重、编辑与转移表、steering 回合匹配、暂停范围与原因保留、作用域清理及条目上限。隔离变异探针检出 17/17，技术参考同步更新。[Issue #3155](https://github.com/can4hou6joeng4/boss-harness/issues/3155)
- 源码候选更新为 npm `0.2.0-rc.515` 和 Python `0.2.0rc515`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.514 - 2026-11-23

- 回合流检查新增 10 项结果摘要与来源行为对照。`summarize_result` 的分页元数据先于正文，成功与失败路径都受 `limit` 截断，错误字段缺省与凭据脱敏保持稳定；`tool_source` 的引用格式与查询时间固定。隔离变异探针检出 11/11，技术参考同步更新。[Issue #3153](https://github.com/can4hou6joeng4/boss-harness/issues/3153)
- 源码候选更新为 npm `0.2.0-rc.514` 和 Python `0.2.0rc514`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.513 - 2026-11-23

- 工具结果检查新增 32 项分页行为对照。两条读取入口交替续读，核对 Unicode 码点偏移、规范化结果拼接、末页、`limit` 边界、过期引用、游标归属与格式。16 种模拟回归均被检出，技术参考同步更新。[Issue #3151](https://github.com/can4hou6joeng4/boss-harness/issues/3151)
- 源码候选更新为 npm `0.2.0-rc.513` 和 Python `0.2.0rc513`。[公开发布记录](https://github.com/can4hou6joeng4/boss-harness/releases)

## 0.2.0-rc.512 - 2026-11-22

- README 的中英文开发入口说明 `npm run check` 的源码核对与离线行为验证范围。技术参考集中说明本地运行条件、CI 覆盖和单项脚本入口，并保留原构建前检查锚点。文档索引、项目状态、贡献与发布约定同步链接。关联 Issue [#3149](https://github.com/can4hou6joeng4/boss-harness/issues/3149)。
- 源码候选标记为 npm `0.2.0-rc.512` 和 Python `0.2.0rc512`。最新公开预发布见 [GitHub Releases](https://github.com/can4hou6joeng4/boss-harness/releases)。

## 0.2.0-rc.511 - 2026-11-22

rc.511 源码候选为工具结果边界补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `tool_results.py` 为模型提供执行状态与重试处置，并为桌面提供内联结果和内容寻址引用。原有 `scripts/check_tool_results.py` 只做常量 AST 与源码片段扫描（5 个常量、18 项），本轮加入行为对照（28 项）：直接调用 `tool_execution_state`、`tool_disposition`、`disposition_for_state`、`result_text`、`result_reference`、`canonical_result_text`、`wire_size` 与 `project_item`，覆盖九个合法执行状态与非法值丢弃、处置字段清洗与非法枚举、状态→处置矩阵（含 failed 的写读差异）、紧凑 JSON 与标量拼写及 NaN 拒绝、引用摘要与字节 / 码点长度及 surrogatepass、规范化对孤立代理项与非有限浮点的降级、wire 预算与代理项超限、内联上限恰好 64 KiB 保留、超出后省略并生成引用、固定字段截断与不修改输入。CI 无需改动，技术参考同步说明。修复 Issue [#3147](https://github.com/can4hou6joeng4/boss-harness/issues/3147)。
- 变异验证：结构侧 limit 校验、摘要格式、STALE 引用、游标长度、游标偏移、内联阈值、nextCursor、参数白名单与模型读取上限共九种，行为侧执行状态放行非法值 / 拒绝合法值、处置保留多余字段、不确定结果判为安全、写失败判为安全、结果强制 ASCII / 放行 NaN、引用按字符计长、规范化不做降级、wire 缺帧余量、内联边界含等号或按码点计长、固定字段不截断与投影修改输入共十四种，均被检查发现（23/23）。五项本地门禁通过。版本推进到 npm `0.2.0-rc.511` / Python `0.2.0rc511`。

## 0.2.0-rc.510 - 2026-11-22

rc.510 源码候选为回合归并补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `_turns` 驱动分支列表、冻结快照、fork 边界切分与列表索引。原有 `scripts/check_turn_records.py` 只做源码片段、顺序与缩进扫描（41 项），本轮加入行为对照（76 项）：直接调用 `SessionStore._turns`，覆盖非回合条目忽略、回合编号格式（缺失 / 非字符串 / 非法字符 / 超长）与合法复杂编号、同一回合多条记录的字段合并与 `firstOrdinal` / `startedAt` 保留、`lastOrdinal` / `updatedAt` 推进、终态首次边界与 `completedAt` 不被后续覆盖、`previous_end` 推进、内部记账字段不可覆盖、`task_phase` 的归属 / 阶段 / 状态 / 尝试次数 / 重启上限 / 恢复原因 / 恢复策略边界与回合出现前跳过、threadId 收敛与缺失时间戳。CI 无需改动，技术参考同步说明。修复 Issue [#3145](https://github.com/can4hou6joeng4/boss-harness/issues/3145)。
- 变异验证：结构侧阶段分支、回合查找、归属条件、尝试 / 重启上限、回合分支、标识符、内部字段、边界首次、终态序号、首序号与恢复原因上限共十二种，行为侧跳过阶段、不记终态、覆盖边界、覆盖内部字段、终态序号偏移、不校验标识符、不校验阶段上限与 threadId 取载荷共八种，均被检查发现（20/20）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.510` / Python `0.2.0rc510`。

## 0.2.0-rc.509 - 2026-11-22

rc.509 源码候选为条目投影补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `_project_items` 决定编辑、压缩、分叉与快照按编号定位时命中哪条逻辑消息。原有 `scripts/check_item_projection.py` 只做源码片段、顺序与计数扫描（31 项），本轮加入行为对照（55 项）：直接调用 `SessionStore._project_items`，覆盖非 item 条目忽略、缺 / 非字符串 / 空 id 跳过、基本投影与 threadId 收敛、修订合并保留原编号与未覆盖字段、修订别名链、目标不存在或非字符串时新建、同编号保留先出现、修订后同编号跳过、工具调用父条目回退（running / 子或父类型不符 / 父不存在不回退）、编号字段非字符串删除、非对象 approval 删除、payload 缺失、输入不被修改与返回独立对象。CI 无需改动，技术参考同步说明。修复 Issue [#3143](https://github.com/can4hou6joeng4/boss-harness/issues/3143)。
- 变异验证：结构侧条目类型、载荷副本、空编号跳过、修订目标、回退条件、父类型、编号清理、审批清理、合并编号、追加 threadId、重复跳过与修订别名共十二种，行为侧不合并修订、不回退工具调用、保留非字符串编号、保留非对象审批、不跳过空编号、不跳过重复编号、覆盖原编号与 threadId 取载荷共八种，均被检查发现（20/20）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.509` / Python `0.2.0rc509`。

## 0.2.0-rc.508 - 2026-11-22

rc.508 源码候选为队列计数归并补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `_queue_status_counts` 决定侧边栏角标与会话列表的待处理数。原有 `scripts/check_queue_counts.py` 只做源码片段、顺序与计数扫描（20 项），本轮加入行为对照（42 项）：直接调用 `SessionStore._queue_status_counts`，覆盖空列表与非队列条目、三个活动状态计数、终止状态不计、不同 id 累加、同 id 最新状态覆盖（活动到终止、终止到活动、三次记录）、损坏记录（payload 非对象 / 缺或未知 kind / 缺或未知 status / 非字符串、空或超长 id / input 非字符串 / NaN 字段）跳过且不覆盖有效状态、额外字段不影响、返回键恰好三个与输入不被修改。CI 无需改动，技术参考同步说明。修复 Issue [#3141](https://github.com/can4hou6joeng4/boss-harness/issues/3141)。
- 变异验证：结构侧条目类型、结构校验、损坏跳过、最新覆盖、计数键、活动过滤、元数据求和与零值清除共八种，行为侧恒为零、取首个状态、不校验记录与计入终止状态共四种，均被检查发现（12/12）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.508` / Python `0.2.0rc508`。

## 0.2.0-rc.507 - 2026-11-22

rc.507 源码候选为工具参数校验补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `tool_schema.py` 是模型工具调用进入上游 CLI 前的唯一参数守卫。原有 `scripts/check_tool_schema.py` 只做源码片段、AST 与计数扫描（25 项），本轮加入行为对照（87 项）：直接调用 `canonical_schema` 与 `validated_arguments`，覆盖根必须是 Mapping 且规范化为对象、未知关键字与非法规则整体拒绝、规范化输出的键序与非 ASCII 保留、Mapping 子类、类型精确匹配（布尔不是整数 / 数值）、required 与 additionalProperties、字符串长度与 `re.search` 正则语义、anyOf、数组长度与 `uniqueItems` 的数值等价、结构化字符串仅按 schema 选中的对象 / 数组解码且失败保留原文、不可传递字符单独点名，以及非对象 / 循环 / 超深 / NaN / 元组 / 字节 / 非字符串键 / 非法 schema JSON 的拒绝与返回独立副本。CI 无需改动，技术参考同步说明。修复 Issue [#3139](https://github.com/can4hou6joeng4/boss-harness/issues/3139)。
- 变异验证：结构侧 schema / 参数字节上限、JSON / schema 深度上限、未知关键字、根对象、正则注册、节点上限、解码前缀、解码校验、最终比对与关键字集合共十二种，行为侧 schema 不校验、根数组放行、参数恒放行、布尔转整数、不解码结构化字符串、不复制参数与合并不可传递错误共七种，均被检查发现（19/19）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.507` / Python `0.2.0rc507`。

## 0.2.0-rc.506 - 2026-11-22

rc.506 源码候选为上下文编辑纯函数补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `context.py` 决定编辑记录如何进入模型上下文与展示路径。原有 `scripts/check_context_edits.py` 只做源码片段、顺序与反向断言扫描（89 项），本轮加入行为对照（137 项）：直接调用 `_public_checkpoint`、`_is_one_of`、`_context_edit`、`_context_edit_entries`、`_apply_context_edits`、`_context_edit_source_digest`、`_checkpoint_source_item_ids` 与 `context_edit_states`，覆盖检查点文本 / 整数字段白名单与 2^53-1 边界、类型收窄、合法替换 / 删除、严格报错与宽松跳过、目标先出现、payload 精确键集、纯空白与 32 000 / 32 001 字符边界、同目标后写覆盖、副本语义与 `originalInput` 剔除、删除标注、目标缺失 / 非消息 / 正文非字符串报错、来源摘要格式与敏感性、`sourceItemIds` / `sourceItemCount` 两种来源及布尔 / 负数 / 超长拒绝、展示投影宽松读取。CI 无需改动，技术参考同步说明。修复 Issue [#3137](https://github.com/can4hou6joeng4/boss-harness/issues/3137)。
- 变异验证：结构侧替换字符上限、检查点整数上限、整数类型、文本上限、严格分支、编辑映射写入、引用校验、原始输入剔除、删除空文本、编辑标注、摘要字段顺序与摘要编辑号共十二种，行为侧恒宽松、恒严格、保留原始输入、从不排除、摘要忽略编辑号、来源 id 不校验、展示用严格、白名单透传、集合转字符串与编辑恒声明共十种，均被检查发现（22/22）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.506` / Python `0.2.0rc506`。

## 0.2.0-rc.505 - 2026-11-22

rc.505 源码候选为条目快照补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `open_entries_snapshot` 与 `SessionEntriesSnapshot` 决定恢复与会话读取能看到哪些持久记录。原有 `scripts/check_entries_snapshot.py` 只做源码片段、顺序与计数扫描（43 项），本轮加入行为对照（75 项）：用 `io.BytesIO` 直接实例化快照，覆盖空前缀、仅会话头、空行跳过计入行号、CRLF、前缀字节上限、重入迭代、`stamp`、关闭后进入 / 迭代拒绝、上下文管理器退出即关闭、格式无效 / 重复会话头 / 坏 JSON / 非 UTF-8 错误；并用真实临时日志与轻量替身直接调用 `SessionStore.open_entries_snapshot`，覆盖完整记录、末尾残段裁剪、空文件、纯残段、超长无边界拒绝、取长度失败时关闭文件、打开失败直接报错，以及写锁内先核对会话再打开的顺序。CI 无需改动，技术参考同步说明。修复 Issue [#3135](https://github.com/can4hou6joeng4/boss-harness/issues/3135)。
- 变异验证：结构侧打开路径、完整记录上限、兜底捕获、错误关闭、快照构造、身份透传、关闭错误文案、前缀字节上限、跳过空行、重入回零、`stamp` 内容与签名共十二种，行为侧 `stamp` 错误、不跳过空行、不钉前缀、关闭仍可读、退出不关闭、范围用文件大小、失败不关闭、不持锁与先打开后核对共九种，均被检查发现（21/21）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.505` / Python `0.2.0rc505`。

## 0.2.0-rc.504 - 2026-11-22

rc.504 源码候选为附件上下文注入补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `resources.py` 的 `AttachmentStore.context` 把附件正文拼进当前回合。原有 `scripts/check_attachment_context.py` 只做源码片段、顺序与计数扫描（42 项），本轮加入行为对照（68 项）：用轻量替身提供 `sessions` 与 `_read_from_entries`，直接调用 `AttachmentStore.context`，覆盖 `None` / 空列表早退且不访问会话、非列表与超过 10 项、非字符串元素、恰好 10 项、去重保序与每个 id 只读一次、名称 JSON 字面量转义、空行分隔、投影剔除正文、预算等于上限通过 / 严格超出拒绝 / 跨附件累计 / 按 `bytes` 而非标签或正文长度计数，以及缺省读取会话条目与显式条目只核对会话存在。CI 无需改动，技术参考同步说明。修复 Issue [#3133](https://github.com/can4hou6joeng4/boss-harness/issues/3133)。
- 变异验证：结构侧数量上限、去重保序、空结果早退、条目来源、名称转义、来源声明、预算累计、预算严格、空行分隔、投影剔除与两处错误文案共十二种，行为侧不去重、上限放宽、元素不校验、预算含等号、预算按标签、预算按正文、无预算、预算不累计、投影保留正文、单换行拼接、名称不转义、显式也读会话、不核对会话、`None` 报错、空列表碰会话、id 裁剪与顺序反转共十七种，均被检查发现（29/29）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.504` / Python `0.2.0rc504`。

## 0.2.0-rc.503 - 2026-11-22

rc.503 源码候选为被放弃分支推导补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `abandoned_branch` 决定切换分支后展示的被放弃回合。原有 `scripts/check_branch_summary.py` 只做源码片段、顺序与反向断言扫描（42 项），本轮加入行为对照（52 项）：用轻量替身提供 `read_entries` / `_turn_tree` / `_leaf_state`，直接调用 `SessionStore.abandoned_branch`，覆盖线性链回退一级 / 两级 / 四级、原地目标、目标为空、分叉共同祖先、无叶记录、空树、目标不存在与固定结果字段。CI 无需改动，技术参考同步说明。修复 Issue [#3131](https://github.com/can4hou6joeng4/boss-harness/issues/3131)。
- 变异验证：结构侧祖先集合与回溯、时间顺序、共同祖先边界与字段、放弃字段、目标校验、叶状态、错误文案与回溯起点共十种，行为侧空放弃列表、顺序反转、共同祖先、起点字段、目标不校验与忽略祖先共六种，均被检查发现（16/16）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.503` / Python `0.2.0rc503`。

## 0.2.0-rc.502 - 2026-11-22

rc.502 源码候选为浏览器来源解析补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `tools/boss_cli.py` 的 `resolve_browser_source_override` 决定上游 CLI 的浏览器来源策略。原有 `scripts/check_browser_source.py` 只做源码片段、AST 与反向断言扫描（28 项），本轮加入行为对照（43 项）：直接调用解析函数，覆盖未设置 / 空字符串 / 纯空白回落、大小写与首尾空白归一、三个合法值、环境变量生效与显式值优先、非法显式值与非法环境变量的固定错误文案，以及解析不写回环境变量。CI 无需改动，技术参考同步说明。修复 Issue [#3129](https://github.com/can4hou6joeng4/boss-harness/issues/3129)。
- 变异验证：结构侧环境读取、去空白、空值回落、白名单、允许值集合、错误文案、上游参数、策略回落、环境变量名与解析调用共十种，行为侧忽略环境、不去空白、不转小写、空值保留、不校验、恒为空、大写返回与错误文案共八种，均被检查发现（18/18）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.502` / Python `0.2.0rc502`。

## 0.2.0-rc.501 - 2026-11-22

rc.501 源码候选为审批条目校验补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `_valid_approval_item` 决定 toolCall 记录能否进入审批索引、审批列表与持久计数。原有 `scripts/check_approval_item.py` 只做源码片段、顺序与反向断言扫描（49 项），本轮加入行为对照（92 项）：构造合法条目直接调用校验函数，覆盖展示字段去空白与 200 字符边界、工具名一致性、`approvalId` 的 32 位小写十六进制、`turnId` 标识符、精确 `dict` 参数与 `params` 一致性、`pending_only` 强制待审批、`approve` / `deny` / `expired` 三组状态组合、`deadline` 的类型 / 有限性 / 正值、描述 1000 字符上限与参数摘要不匹配。CI 无需改动，技术参考同步说明。修复 Issue [#3127](https://github.com/can4hou6joeng4/boss-harness/issues/3127)。
- 变异验证：结构侧 kind、工具名去空白与上限、id 非空、工具名一致、回合号、参数精确类型 / 一致、待审批模式与状态、三类状态集合、截止时间类型 / 正值 / 有限性、描述上限、摘要比对与四处计数共二十三种，行为侧恒真 / 恒假 / 取反、待审批模式、摘要、截止时间、描述、审批编号与工具名去空白共九种，均被检查发现（32/32）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.501` / Python `0.2.0rc501`。

## 0.2.0-rc.500 - 2026-11-22

rc.500 源码候选为条目归属与回合树补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `_item_owners` / `_turn_tree` 是分支投影、fork 前缀、分支列表与上下文读取的共同输入。原有 `scripts/check_item_ownership.py` 只做源码片段、顺序与反向断言扫描（52 项），本轮加入行为对照（70 项）：构造 entries 直接调用两个入口，归属覆盖显式回合、`running` 活动回合、挂起收割、跨回合修订继承、非 `running` 工具调用回退、`running` 不回退、重复编号、无归属、终态清空、非法回合号与重复回合；回合树覆盖父回合链、条目推进尾部、任务 / 批次归属、未知归属跳过与重复回合不重复入列。CI 无需改动，技术参考同步说明。修复 Issue [#3125](https://github.com/can4hou6joeng4/boss-harness/issues/3125)。
- 变异验证：结构侧修订字段、工具调用类型 / 状态 / 父级、显式优先、重复守卫、挂起收集、回合去重、活动回合、终态清空、parentId 唯一、投影校验、顺序去重、自引用、未知归属与任务批次类型共十六种，行为侧修订继承、工具回退、重复编号、挂起收割、回合去重、活动回合、终态清空、running 回退、顺序去重与未知归属共十种，均被检查发现（26/26）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.500` / Python `0.2.0rc500`。

## 0.2.0-rc.499 - 2026-11-22

rc.499 源码候选为分页游标编解码补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `_page_cursor` / `_read_page_cursor` 是会话列表、分支列表等分页读取共用的游标编解码。原有 `scripts/check_page_cursor.py` 只做源码片段、顺序与反向断言扫描（26 项），本轮加入行为对照（45 项）：直接调用两个函数，覆盖 `p1_` 前缀与无补齐符、键列表往返、scope 键序无关、`None` 透传、空字符串 / 非字符串 / 错误前缀 / 非法 base64 / 坏 JSON / 顶层非对象 / 缺字段 / 额外字段 / key 非列表 / kind 与 scope 不符 / kind 大小写 / 深层嵌套非对象 / 超长游标。CI 无需改动，技术参考同步说明。修复 Issue [#3123](https://github.com/can4hou6joeng4/boss-harness/issues/3123)。
- 变异验证：结构侧编码前缀、补齐符、三字段、空游标短路、长度上限、解码前缀、严格 base64 与字母表、递归错误捕获、字段集合、kind / scope / key 类型、返回、两类文案与编码字段共十七种，行为侧编码补齐 / 前缀、解码前缀、长度、额外字段、kind / scope / key 类型、大小写、错误收敛与空游标共十一种，均被检查发现（28/28）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.499` / Python `0.2.0rc499`。

## 0.2.0-rc.498 - 2026-11-22

rc.498 源码候选为时长文案补充内核侧行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session_export.py` 的 `_duration_text` 决定会话导出中的耗时文案，必须与桌面 `formatDurationMs` 保持同一口径。原有 `scripts/check_duration_parity.py` 只做源码片段、顺序与反向断言扫描（38 项），本轮加入行为对照（61 项）：直接调用 `_duration_text`，覆盖 0 / 499 / 500 / 999 / 1000 / 1499 / 1500 毫秒的取整边界、59 秒 / 60 秒 / 61 秒 / 90 秒、59 分 58 秒 / 59 分 59 秒 / 60 分 / 1 小时 / 1 小时 1 分 / 2 小时、小时分支只保留整分、负数与极大值。CI 无需改动，技术参考同步说明。修复 Issue [#3121](https://github.com/can4hou6joeng4/boss-harness/issues/3121)。
- 变异验证：结构侧内核取整、阈值、秒 / 分 / 小时文案与拆分、桌面取整、阈值与两类分支文案、回合包装共十二种，行为侧取整、半入偏差、秒阈值、分 / 小时剩余、小时用剩余秒、两类空格、负数与极大值共十种，均被检查发现（22/22）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.498` / Python `0.2.0rc498`。

## 0.2.0-rc.497 - 2026-11-22

rc.497 源码候选为审批参数摘要补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session.py` 的 `approval_parameters_digest` 决定审批参数如何规范化为 SHA-256 摘要，摘要用于 `_prepare_tool` 负载与 `_index_thread` 持久化索引的往返校验。原有 `scripts/check_approval_digest.py` 只做 AST 与源码顺序扫描（45 项），本轮加入行为对照（72 项）：直接调用摘要函数，覆盖空对象、键序稳定、嵌套键序、紧凑分隔符、非 ASCII 不转义与键排序、数字键转字符串、布尔 / 空值 / 浮点 / 大整数 / 元组转数组、不同参数不同摘要与 64 位小写十六进制；非法类型（list / None / 字符串 / dict 子类）与 NaN / Infinity / 不可序列化值 / 字节值 / 混合键 / 循环引用 / 超深嵌套 / 嵌套 NaN 统一收敛为固定错误。CI 无需改动，技术参考同步说明。修复 Issue [#3119](https://github.com/can4hou6joeng4/boss-harness/issues/3119)。
- 变异验证：结构侧精确类型、键排序、非有限数、非 ASCII、分隔符、十六进制摘要、递归错误捕获、两处错误文案、工具参数唯一、摘要就地计算、参数直接引用、负载字段集合、索引摘要与截止时间、代理第二实现共十六种，行为侧键排序、非 ASCII、分隔符、非有限数、精确类型、类型 / 递归错误捕获、拒绝非对象、摘要截断、空对象固定值、大小写、摘要算法共十二种，均被检查发现（28/28）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.497` / Python `0.2.0rc497`。

## 0.2.0-rc.496 - 2026-11-22

rc.496 源码候选为凭据包装与错误文本脱敏补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `secret.py` 的 `Secret` 与 `redact_secrets` 是凭据进入日志、错误文本与导出的最后一道网。原有 `scripts/check_secret.py` 只做常量、片段与顺序扫描（35 项），本轮加入行为对照（63 项）：直接调用 `redact_secrets`，覆盖空文本 / `None` / 纯文本、已知原值的长度下限 / 空值 / 多次替换、Bearer 大小写与长度边界、`sk-` 前缀、key/token/secret/password 的 `:` / `=` / 引号 / 下划线 / 连字符形式、短值不替换与组合文本；直接构造 `Secret`，覆盖 `get`、布尔值、`str` / `repr` 占位符、明文不出现、不可 JSON 序列化、仅槽位与拒绝额外属性。CI 无需改动，技术参考同步说明。修复 Issue [#3117](https://github.com/can4hou6joeng4/boss-harness/issues/3117)。
- 变异验证：结构侧两类长度、access_token 形态、分隔符、占位符、空值短路、原值替换、三类脱敏替换、槽位、repr / 布尔 / 取值 / str、四类反向断言与两处文档片段共二十三种，行为侧已知原值、原值长度、Bearer 前缀、sk / 赋值 / 键名、三类正则边界与五类 `Secret` 实现共十五种，均被检查发现（38/38）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.496` / Python `0.2.0rc496`。

## 0.2.0-rc.495 - 2026-11-22

rc.495 源码候选为 JSON 导出分组与严格编码补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session_export.py` 的 `_render_json` 决定回合前 / 回合内条目分组、文档字段与严格编码。原有 `scripts/check_export_json.py` 只做源码片段、顺序与反向断言扫描（45 项），本轮加入行为对照（68 项）：直接调用 `_render_json` 并解析结果，覆盖 schema、四项脱敏标记、计数写入、三类来源、回合前 / 回合内 / 无回合分组、截断与条目计数、queue、额外 `meta` 字段、中文不转义、两空格缩进与尾部换行、非 JSON 值转字符串，以及 NaN / Infinity / 深层嵌套的可读错误。CI 无需改动，技术参考同步说明。修复 Issue [#3115](https://github.com/can4hou6joeng4/boss-harness/issues/3115)。
- 变异验证：结构侧 schema 常量与引用、渲染签名、回合 / 前置列表、回合判定与追加、脱敏 / 计数 / 来源 / 分组字段、严格编码、两类降级与四类反向断言共二十四种，行为侧脱敏标记、来源、截断、条目计数、缩进、中文转义、尾部换行、schema、非 JSON 值、额外字段、分组顺序、降级错误、队列与前置字段共十四种，均被检查发现（38/38）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.495` / Python `0.2.0rc495`。

## 0.2.0-rc.494 - 2026-11-22

rc.494 源码候选为 HTML 导出转义与页面补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session_export.py` 的 `_h` 与 `_render_html` 决定导出 HTML 的转义与页面结构。原有 `scripts/check_export_html.py` 只做源码片段、顺序与反向断言扫描（59 项），本轮加入行为对照（81 项）：直接调用 `_h` 核对 `&`、`<`、`>`、双引号与单引号转义及非字符串输入；构造最小 `meta` / `units` / `counts` / `queue` 调用 `_render_html`，覆盖 doctype、CSP、referrer、页脚闭合、主体结构、恶意会话 id 与标题转义、工具结果两种提示、日志 / 当前分支视图、脱敏统计、截断与孤立条目提示、空标题回退。CI 无需改动，技术参考同步说明。修复 Issue [#3113](https://github.com/can4hou6joeng4/boss-harness/issues/3113)。
- 变异验证：结构侧转义导入与实现、会话 / 标题 / 正文 / 结果 / 工具 / 参数 / 审批 / 摘要 / 队列字段入口、CSP / referrer / 标题 / 页脚与三类反向断言共二十种，行为侧特殊字符 / 引号 / 空值、页面头尾、提示、视图、统计、截断、孤立条目与空标题共十四种，均被检查发现（34/34）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.494` / Python `0.2.0rc494`。

## 0.2.0-rc.493 - 2026-11-22

rc.493 源码候选为 Markdown 导出中和与围栏补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session_export.py` 的 `_code_text` / `_inline_text` / `_inline_code` / `_fence` 决定导出 Markdown 如何中和正文与计算代码围栏。原有 `scripts/check_export_markdown.py` 只做源码片段与顺序扫描（90 项），本轮加入行为对照（111 项）：直接调用四个纯函数，覆盖反引号替换、回车与换行归一、非字符串输入、反斜杠与九个行内定界符转义、行内代码不转义正文定界符、动态围栏取反引号与波浪线最长的加一长度、最少三个反引号、语言参数、空正文与内部换行保留。CI 无需改动，技术参考同步说明。修复 Issue [#3111](https://github.com/can4hou6joeng4/boss-harness/issues/3111)。
- 变异验证：结构侧代码文本归一、表格与波浪线转义、行内入口、围栏扫描与加一、围栏拼装、用户正文 / 结果明文 / 摘要正文 / 队列输入围栏、附件与工具字段中和、三类反向断言共二十种，行为侧代码文本、行内转义与包裹、围栏固定 / 同长 / 仅反引号 / 语言 / 默认值 / 正文共十六种，均被检查发现（36/36）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.493` / Python `0.2.0rc493`。

## 0.2.0-rc.492 - 2026-11-22

rc.492 源码候选为会话导出脱敏补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session_export.py` 的 `Redactor` 决定导出正文中凭据、环境变量、本机路径与候选人信息如何打码。原有 `scripts/check_export_privacy.py` 只做静态扫描（72 项），本轮加入行为对照（149 项）：直接构造 `Redactor` 并调用 `sensitive` / `personal` / `text` / `collect_personal`，覆盖已知与短凭据、Bearer / Cookie 头、`sk-` / JWT / `__zp_*` / 长 token / URL userinfo、环境变量赋值、已知路径尾段、含空格路径延续、通用绝对路径、Windows / UNC / file URL、单段根路径与正文斜杠词、PII 键归一化与去重、数值 / 布尔 / 长度 / 深度 / 总量边界、`finalize` 排序、邮箱 / 手机号 / 身份证 / 微信号、非文本输入、文本截断与组合管线，并核对 `_known_secrets` / `_known_paths` / `_continues_path` / `_path_end` / `_short_text` / `_status_text` / `_normalize_key`。CI 无需改动，技术参考同步说明。修复 Issue [#3109](https://github.com/can4hou6joeng4/boss-harness/issues/3109)。
- 变异验证：结构侧格式、字节上限与主进程一致性、请求白名单与默认脱敏、脱敏标记与导入、计数与长度门槛、管线顺序与组合、清理深度、安全参数与结构投影共二十五种，行为侧凭据 / 路径归一化、已知值替换与计数、文本组合与非文本输入、深度 / 布尔 / 去重 / 长度 / 总量 / 排序、环境与路径计数、路径尾段、正则与开关、环境与主目录收集、短文本 / 状态 / 归一化 / 路径边界三十九种，均被检查发现（64/64）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.492` / Python `0.2.0rc492`。

## 0.2.0-rc.491 - 2026-11-22

rc.491 源码候选为 Codex 配置路径、严格错误与 profile 补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `codex_config.py` 只读本地配置并按显式入参、环境覆盖与 `CODEX_HOME` 选择文件。原有 `scripts/check_codex_config.py` 只做静态扫描（70 项），本轮加入行为对照（114 项）：直接调用 `config_path` 覆盖优先级与去空白并确认不读取进程环境；调用 `profile_from_mapping` 覆盖缺失模型 / 端点、provider 查找、`wire_api` 缺省与大小写归一、非 `responses` 拒绝、effort / env_key 去空白与 `Secret` 包装（含不可 JSON 序列化）；用临时目录构造有效 / 缺失 / 目录 / 非法 TOML，覆盖 strict 开与关、固定错误码、错误不回显配置原文/凭据，以及 `tomllib` 不可用时的错误码。CI 无需改动，技术参考同步说明。修复 Issue [#3107](https://github.com/can4hou6joeng4/boss-harness/issues/3107)。
- 变异验证：结构侧默认路径、显式与环境判定、去空白、文件判定、错误码、解析器可用、二进制读取、解码捕获、profile 返回与归一化、协议白名单、凭据来源与包装、四类反向断言三十种，行为侧显式优先、环境去空白、忽略进程环境、覆盖空值、协议白名单与归一结果、凭据与环境变量结果、严格开关、缺失边界与凭据脱敏十二种，均被检查发现（42/42）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.491` / Python `0.2.0rc491`。

## 0.2.0-rc.490 - 2026-11-22

rc.490 源码候选为上下文估算、请求指纹与用量校准补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `context.py` 的逐条规模估算、请求指纹与成功用量校准决定上下文预算与压缩基线。原有 `scripts/check_context_estimate.py` 只做 AST 片段、顺序与计数扫描（124 项），本轮加入行为对照（192 项）：直接构造消息与 `ModelRequest`，覆盖 `_json_size` 的非 ASCII 计数、`_message_size` 的各类内容块与固定开销、`estimate_tokens` 的系统提示与向上取整、`_usage_input_tokens` 的 OpenAI / Anthropic 字段与单请求上限、`request_fingerprint` 的确定性与各字段变化、消息负载的固定角色与可选字段，以及 `_retained_usage_estimate` 的回退、锚点匹配、冲突清空、严格递增与区间校准。CI 无需改动，技术参考同步说明。修复 Issue [#3105](https://github.com/can4hou6joeng4/boss-harness/issues/3105)。
- 变异验证：结构侧 JSON 编码、固定开销、签名与脱敏计数、参数序列化、结果标识、取整与系统提示、用量字段与上限、思考配置与 SHA-256、负载字段、冲突与递增、归属与指纹复核、四舍五入与区间记录、回退与合格标记共二十八种，行为侧 JSON 非 ASCII、消息规模、估算取整、缓存计入、布尔接受、上限放宽、指纹缺字段或恒定、负载角色与可选字段、校准区间、归属、线路、合格标记、冲突与指纹复核十七种，均被检查发现（45/45）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.490` / Python `0.2.0rc490`。

## 0.2.0-rc.489 - 2026-11-22

rc.489 源码候选为自动压缩策略补充校验与归一化行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `compaction.py` 决定界面策略与环境配置如何校验、归一化与合并。原有 `scripts/check_compaction.py` 只做静态扫描（61 项），本轮加入行为对照（166 项）：直接调用 `verified_policy` 覆盖未知字段 / 空对象 / 六类字段边界与字段顺序过滤，构造 `CompactionPolicy` 覆盖默认值、范围与类型拒绝、provider 去空白 / 大小写 / codex 归一、model 与 effort 边界、`describe` 字段，核对 `override` 的合并、字段白名单与错误传播；保存并恢复 `BOSS_HARNESS_COMPACTION`，覆盖持久默认值、空值 / 空白、JSON 合并、全字段构造、重复键、未知字段、非对象、非法 JSON、超长与越界值，确认错误不回显原配置。CI 无需改动，技术参考同步说明。修复 Issue [#3103](https://github.com/can4hou6joeng4/boss-harness/issues/3103)。
- 变异验证：结构侧字段与线路集合、快照与类型判定、范围与长度、顺序与归一化、覆盖白名单、大小与重复键、异常集合、错误文案与文档片段二十四种，行为侧宽松校验、字段逆序、失败码、策略构造、描述字段、覆盖白名单、持久设置、环境默认值、线路保留与错误回显十种，均被检查发现（34/34）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.489` / Python `0.2.0rc489`。

## 0.2.0-rc.488 - 2026-11-22

rc.488 源码候选为回合请求上限补充环境解析行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `turn_limits.py` 只接受精确整数，环境变量先去空白再按两位十进制文本判定。原有 `scripts/check_turn_limits.py` 只做静态扫描（24 项），本轮加入行为对照（59 项）：直接调用 `model_request_limit` 覆盖 1 / 64 边界、自定义 ceiling 与布尔 / 浮点 / 字符串 / None 的拒绝及错误文案；保存并恢复 `BOSS_HARNESS_MAX_MODEL_REQUESTS`，覆盖未设置、空值 / 空白、首尾空白、前导零、超长、符号 / 小数 / 字母、越界值与错误不回显原值。CI 无需改动，技术参考同步说明。修复 Issue [#3101](https://github.com/can4hou6joeng4/boss-harness/issues/3101)。
- 变异验证：结构侧常量、精确整数判定、文本长度与形态、去空白、链式异常、复用上限校验、错误文案、空值分支、默认值、异常捕获、比较方向与文档片段十五种，行为侧布尔接受、忽略 ceiling、越界接受、字符串接受、错误文案、环境去空白、前导零、错误默认值、越界接受、回显原值与零值接受十一种，均被检查发现（26/26）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.488` / Python `0.2.0rc488`。

## 0.2.0-rc.487 - 2026-11-22

rc.487 源码候选为用量汇总补充校验与缓存估算行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `usage.py` 只让类型、范围与 provider 语义都可验证的记录计入合计，并对来源、摘要任务与缓存未命中做有界汇总。原有 `scripts/check_usage.py` 只做静态片段扫描（66 项），本轮在脚本内加入行为对照（139 项）：直接构造用量记录，覆盖 `verify_usage` 的七类原因、OpenAI / Anthropic 归一化与边界、`bounded_identifier` 长度与代理项降级、`summarize_usage` 的回合桶、未验证原因、摘要任务、来源去重与上限、压缩策略、任务元数据与截断、活动任务标记，以及缓存未命中的噪声下限、前缀缩短、连续累计、无效记录不重置基线、checkpoint / 分支摘要重置与分支视图不估算。CI 无需改动，技术参考同步说明。修复 Issue [#3099](https://github.com/can4hou6joeng4/boss-harness/issues/3099)。
- 变异验证：结构侧请求上限、原因文本、线路语义、来源上限与去重、未命中取较小值、噪声下限、任务截断、活动任务、原因白名单、费用不可用、标识长度、全零判定与文档片段二十三种，行为侧缓存写上报、原因映射、全零接受、未知 provider、标识长度、压缩策略、活动任务、任务截断、任务元数据、缓存累计、来源列表、未上报计数、摘要合计、分支摘要元数据、非法策略、分支过滤与检查点重置十七种，均被检查发现（40/40）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.487` / Python `0.2.0rc487`。

## 0.2.0-rc.486 - 2026-11-22

rc.486 源码候选为 Anthropic 私有续接元数据补充构造与恢复行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `continuation.py` 只保存签名块的描述而不是重复正文：请求前缀 digest 绑定模型可见前缀，构造与恢复都必须拒绝超限签名、重复引用、跨回合批次与被编辑的助手消息。原有 `scripts/check_continuation.py` 只做静态片段与顺序扫描（119 项），本轮在脚本内加入行为对照（189 项）：直接构造消息与持久条目，覆盖前缀 digest 的排序 / 非 ASCII、正文 / 思考 / 隐藏块描述、单签名 / 合计 / 描述块 / 载荷上限、普通批次与失败结算、恢复的字段与 digest / 调用 ID / 助手引用 / 回合归属 / 尾随内容，以及编码失败降级为普通批次。CI 无需改动，技术参考同步说明。修复 Issue [#3097](https://github.com/can4hou6joeng4/boss-harness/issues/3097)。
- 变异验证：结构侧预算常量与字段名、摘要排序与分隔、调用收集、签名判定、版本与 ID 投影、描述与合计上限、批次降级、恢复字段集合、调用前缀、助手引用、块结构、内容 digest 与长度、末尾偏移、反向断言与技术参考片段五十八种，行为侧前缀摘要恒定、构造恒空、构造版本错、批次恒空、恢复被跳过、错误被吞掉、摘要不排序七种，均被检查发现（65/65）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.486` / Python `0.2.0rc486`。

## 0.2.0-rc.485 - 2026-11-22

rc.485 源码候选为模型流泵补充计费与终止行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `stream_pump.py` 把异步 SDK 生产器桥接为同步迭代器：入队前按字节与结构计费，取消、超时与失败只交付一个终止事件，后台线程在固定名额与固定等待内收尾。原有 `scripts/check_stream_pump.py` 只做静态片段与顺序扫描（103 项），本轮在脚本内加入行为对照（151 项）：直接调用 `_text_size` / `_event_size` 覆盖 UTF-8 分块、代理项替换、标量 / 容器 / 对象 / Pydantic 额外字段、循环与共享引用、深度与节点哨兵；并构造真实 `AsyncStreamPump` 覆盖顺序交付、完成停止、取消与超时终态、单事件超限与容量拒绝；同时补文本分块顺序、字典与列表开销计数、取消防线计数与发布顺序断言。CI 无需改动，技术参考同步说明。修复 Issue [#3095](https://github.com/can4hou6joeng4/boss-harness/issues/3095)。
- 变异验证：结构侧缓冲 / 单事件 / 节点 / 在途泵 / 清理常量、分块与编码、文本判据与哨兵、深度与节点边界、标量与容器计费、Pydantic 槽位、发布配额与入队、超时与取消防线、执行与收尾顺序、反向断言与技术参考片段七十四种，行为侧文本计费恒零、事件计费恒零、泵顺序反转、完成不停止、发布不计尺寸、泵构造失败六种，均被检查发现（80/80）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.485` / Python `0.2.0rc485`。

## 0.2.0-rc.484 - 2026-11-22

rc.484 源码候选为模型错误分类补充溢出、重试与传输诊断的行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `errors.py` 是可信 provider 错误边界：只接受精确 OpenAI code、有界 llama.cpp / LiteLLM 文本、Anthropic 带数字的 prompt 拒绝与 HTTP 413 代理正文拒绝作为上下文溢出；配额耗尽不可重试、裸 429 未知；传输诊断只输出固定标签与白名单 errno。原有 `scripts/check_errors.py` 只做静态片段与顺序扫描（101 项），本轮在脚本内加入行为对照（199 项）：覆盖来源校验、provider code 白名单与回退、智谱 1308 的字符串 / 整数 / 浮点边界、重试提示的配额优先与认证状态、四条文本匹配的空白与长度边界、两家 provider 的溢出组合与显式 `retryable` 覆盖、传输因果链 / errno 白名单 / 抑制上下文 / 固定诊断文案。CI 无需改动，技术参考同步说明。修复 Issue [#3093](https://github.com/can4hou6joeng4/boss-harness/issues/3093)。
- 变异验证：结构侧正则与长度上限、配额 / 临时状态集合、SDK 家族、MRO 映射、errno 白名单、DNS 命名空间、因果链来源与抑制、状态范围、code 字段顺序、智谱 code、重试优先级、四组首次出现顺序、五条反向断言与技术参考片段五十种，行为侧来源恒有效、provider code 恒空、智谱配额恒否、重试提示恒未知、溢出来源恒是、四条文本匹配恒是或恒否、两家 provider 恒空、传输诊断恒未知、固定文案恒空十二种，均被检查发现（62/62）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.484` / Python `0.2.0rc484`。

## 0.2.0-rc.483 - 2026-11-22

rc.483 源码候选为模型重试补充解析、退避与观测事件的行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `retry.py` 只决定重试的等待时长与次数：环境变量去空白后按整数解析并在 1–10 次与非负基数内收敛，两处解析失败都标记 `adjusted`；网关 Retry-After 的毫秒头优先于秒头，两者与指数退避均封顶 8 秒；观测事件只带次数、毫秒与错误说明，`with_retry_outcome` 在首个非错误事件补成功终态、错误事件补失败并原样透传，已有 `retry_end` 不重复补发，待补次数共三处归零。原有 `scripts/check_retry.py` 只做静态片段与顺序扫描（82 项），本轮在脚本内加入行为对照（126 项）：覆盖未设置 / 空白 / 有效 / 越界 / 非整数的次数与基数、网关值优先与两端夹取、毫秒头优先 / 空值与非法值跳过 / 头去空白、开始与取消事件字段、成功 / 失败 / 取消兜底 / 不重复补发 / 连续开始取后者、来源流耗尽与提前关闭的关闭传播；并补两处解析失败标记与三处待补归零的计数断言。CI 无需改动，技术参考同步说明。修复 Issue [#3091](https://github.com/can4hou6joeng4/boss-harness/issues/3091)。
- 变异验证：结构侧上限与默认值常量、环境来源、空白判断、整数解析、解析回退、次数 / 基数收敛、调整标记、毫秒换算、网关夹取、指数封顶、响应对象属性、响应头顺序与空值跳过、头去空白、解析继续、毫秒取整、取消文案、待补初始、失败原因与说明、透传底层、关闭调用、四组首次出现顺序、三条反向断言与用户指南片段三十三种，行为侧环境解析恒默认、退避无封顶、响应头秒优先、开始事件零延迟、不补终态事件、取消事件次数偏移六种，均被检查发现（39/39）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.483` / Python `0.2.0rc483`。

## 0.2.0-rc.482 - 2026-11-22

rc.482 源码候选为模型容量配置补充解析与错误收敛的行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `capabilities.py` 解析 `BOSS_HARNESS_MODEL_LIMITS`：64 KiB / 128 项内只接受三种 provider、两个必需字段与七档推理数组，容量关系自洽，任何错误收敛为固定说明且不回显原配置。原有 `scripts/check_capabilities.py` 只做静态片段与顺序扫描（75 项），本轮在脚本内加入行为对照（132 项）：覆盖容量关系与布尔拒绝、来源与估算标记、推理档位白名单 / 去重 / 元组类型、描述投影、覆盖命中与大小写、默认容量复用、覆盖表只读与构造校验、未设置 / 空白 / 有效配置、二十种非法配置的固定错误消息与常量钩子；并补强 `_reject_constant` 必须直接拒绝非有限数值的结构断言。CI 无需改动，技术参考同步说明。修复 Issue [#3089](https://github.com/can4hou6joeng4/boss-harness/issues/3089)。
- 变异验证：结构侧 JSON 字节与项数上限、provider 集合、字段白名单、推理档位、容量下限与输出关系、估算标记、档位去重、模型名空白、重复键、常量钩子、覆盖表项数与只读、环境来源、空白配置、字节判据、两处解析钩子、顶层项数、分隔符、字段白名单、档位数组、异常收敛、无钩子解析、错误回显、丢弃解析器上下文与技术参考片段二十八种，行为侧容量关系不校验、错误回显配置、不回退默认容量、模型名空白放行四种，均被检查发现（32/32）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.482` / Python `0.2.0rc482`。

## 0.2.0-rc.481 - 2026-11-22

rc.481 源码候选为输出字节预算与分块补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `output_budget.py` 在分配前限制保留的文本、思考与工具参数：码点预检后编码复检、紧凑 JSON 逐字符计费、响应文本合计 1 MiB、诊断截断不拆 UTF-8 字符、事件按 32 KiB 分块。原有 `scripts/check_output_budget.py` 只做静态片段与顺序扫描（84 项），本轮在脚本内加入行为对照（124 项）：覆盖尺寸预检与非法 Unicode、逐次计费与本地 / 总量上限、快照的紧凑编码与转义、代理项 / 非文本键 / 非 JSON 值 / 深度 / 节点 / 整数位长拒绝、`reconcile` 高水位、响应文本的分隔符拼接与完整响应取最大、诊断截断不拆字符、分块对齐与重组。CI 无需改动，技术参考同步说明。修复 Issue [#3087](https://github.com/can4hou6joeng4/boss-harness/issues/3087)。
- 变异验证：结构侧三项上限、码点预检、编码尺寸、编码异常、非法 Unicode 文案、逐次计费、总量判据、条目累计、快照额度、布尔分支、整数位长、对象键检查、两处文案、紧凑编码、结构上限、分隔符计费、完整响应取最大、授权尺寸判据、省略号、替换字符、分块下限与边界、非有限数值与技术参考片段二十六种，行为侧尺寸不预检、计费不查上限、诊断不截断、按字符分块四种，均被检查发现（30/30）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.481` / Python `0.2.0rc481`。

## 0.2.0-rc.480 - 2026-11-22

rc.480 源码候选为条目正文补充传输降级与分页的行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `item_content.py` 负责损坏记录的传输降级与正文分页：孤立代理项替换为 U+FFFD、非有限浮点与超深结构降级、摘要按传输文本分块计算、超长正文省略并附引用，分页游标绑定线程 / 条目 / 字段 / 摘要 / 快照。原有 `scripts/check_item_content.py` 只做静态片段扫描（28 项），本轮在脚本内加入行为对照（77 项）：覆盖代理项替换与长度不变、递归清理与键替换、深度与 `inf` / `nan` 占位、引用字段与分块摘要一致、内联清理与旧引用清除、超长省略、分页往返与末页、`limit` 边界、摘要 / 快照格式、过期引用错误码、游标跨线程 / 条目 / 字段 / 摘要与格式拒绝。CI 无需改动，技术参考同步说明。修复 Issue [#3085](https://github.com/can4hou6joeng4/boss-harness/issues/3085)。
- 变异验证：结构侧内联阈值、默认 / 最大分页、深度上限与占位、替换字符、代理项快路径与替换条件、非有限浮点、深度降级、摘要分块与传输文本、内联字节阈值、省略标记、引用投影、`limit` 类型检查、摘要 / 快照格式、游标长度与归属元组、偏移越界、游标字段、过期错误码、内联清理、游标载荷与桌面指南二十七种，行为侧代理项不替换、递归清理删除、引用字节数放宽、超长正文不省略、分页上限放宽、游标归属忽略六种，均被检查发现（33/33）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.480` / Python `0.2.0rc480`。

## 0.2.0-rc.479 - 2026-11-22

rc.479 源码候选为私有状态文件与目录补充权限行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `private_files.py` 是凭据与招聘状态文件的本地保密边界：逐组件以 `O_NOFOLLOW` 打开目录、比对 dev / inode、拒绝非当前用户所有的路径、清除 macOS 扩展 ACL，并把文件收紧到 0o600。原有 `scripts/check_private_files.py` 只做静态片段、调用点与直接写盘扫描（43 项），本轮在脚本内加入临时目录行为对照（64 项）：覆盖路径解析与符号链接环、根目录拒绝、两层目录创建与 0o700、已有目录不改权限、末级与父目录可写拒绝、只读核对不创建路径、文件创建 0o600 与读取收紧、只读打开不创建、符号链接与目录打开拒绝、收紧拒绝符号链接与目录。CI 无需改动，技术参考同步说明。修复 Issue [#3083](https://github.com/can4hou6joeng4/boss-harness/issues/3083)。
- 变异验证：结构侧目录函数默认权限改动、只读核对签名与创建参数改动、目录打开删除 `O_NOFOLLOW`、文件打开默认值改动、目录与文件 fchmod 放宽、所有权检查删除、dev / inode 比对删除、ACL 清除调用删除、根目录文案改动、末级可写判据删除、七个状态模块的调用点删除（八处）、状态模块直接写盘、修复顺序颠倒、状态标志收窄、修复顺序片段重复二十五种，行为侧读取不收紧权限、只读也创建文件、收紧不检查类型、只读核对会创建路径、新建目录不收紧、路径环不报目录错误六种，均被检查发现（31/31）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.479` / Python `0.2.0rc479`。

## 0.2.0-rc.478 - 2026-11-22

rc.478 源码候选为工作区常驻说明补充读取与写入的行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `WorkspaceInstructions` 按首选 `.boss-harness/CONTEXT.md`、旧 `.boss-cli/CONTEXT.md` 的固定顺序加载，读取拒绝符号链接、目录与读取期间被替换的文件，超限与解码失败映射为 `too_large` / `unreadable`；保存只写首选路径，经临时文件、文件与目录 fsync、`os.replace` 原子替换并保留已有权限。原有 `scripts/check_workspace_instructions.py` 只做静态片段扫描（30 项），本轮在脚本内加入临时目录行为对照（66 项）：覆盖空工作区、旧路径兼容、首选优先与 BOM / 空白归一、仅空白视为空、超限与非法编码的状态映射、符号链接与目录候选固定首选不回落、读取上限加一字节、原子写入无临时残留、新文件与覆盖写入的权限、空白正文回执、类型与上限拒绝、符号链接写入与目录占位拒绝、提示块三态文案。CI 无需改动，技术参考同步说明。修复 Issue [#3081](https://github.com/can4hou6joeng4/boss-harness/issues/3081)。
- 变异验证：结构侧上限改动、首选 / 旧路径互换、普通文件检查删除、`O_NOFOLLOW` 删除、dev / inode 比对删除、读取上限加一删除、候选顺序颠倒、缺失候选不跳过、未知存在性回落、提示措辞改动、权限声明删除、编码改动、写入上限检查删除、目标类型检查删除、临时文件前缀删除、文件 fsync 删除、原子替换改动、目录 fsync 删除、工作区 fsync 删除、面板片段删除、编辑器入口删除、指南章节删除、直接写目标文件二十五种，行为侧读取跟随符号链接、读取少读一字节、候选顺序颠倒、加载不去空白、写入跟随符号链接、空白回执报已加载、提示块返回空七种，均被检查发现（32/32）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.478` / Python `0.2.0rc478`。

## 0.2.0-rc.477 - 2026-11-22

rc.477 源码候选固定子进程输出捕获的溢出与收尾口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BoundedProcessOutput` 用三个 daemon 线程读取 stdout / stderr 并向 stdin 写入：读取在共享字节上限处设置 `overflow` 并停止，任一操作抛异常设置 `failed`，线程全部结束后设置 `done`；`join` 只做有界等待，`alive` 报告是否仍有已启动且存活的线程，`close_unstarted` 只关闭尚未启动线程对应的管道。新增 `scripts/check_process_io.py`（53 项）：结构侧固定 64 KiB 分块、读取循环的双重溢出检查、累计与拼接、异常标记、剩余计数与完成标记、stdin 编码写入与冲刷、断管容忍、`join` / `alive` / `close_unstarted` 的线程状态判据；行为侧用本地 Python 子进程与自定义流覆盖 stdout / stderr 聚合、stdin 往返、跨块与单块溢出、读取异常置失败、断管容忍、超时后仍存活并在释放后收尾、未启动管道关闭。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3079](https://github.com/can4hou6joeng4/boss-harness/issues/3079)。
- 变异验证：结构侧分块上限改动、读取循环放行、空块退出删除、锁内溢出检查删除、上限比较改动、溢出不置位、累计删除、拼接删除、失败标记放宽、剩余计数删除、完成标记删除、编码改动、冲刷删除、断管捕获改动、启动判据删除、存活判据放宽、未启动判据反转、剩余基数改动十八种，行为侧上限放行、溢出不置位、失败标记删除、完成标记删除、冲刷删除、标准输入关闭删除、断管捕获改动、存活判据恒假、未启动关闭删除九种，均被检查发现（27/27）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.477` / Python `0.2.0rc477`。

## 0.2.0-rc.476 - 2026-11-22

rc.476 源码候选为请求策略补充拒绝与上下文变换的行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `request_policy.py` 是模型请求的准入边界：`history_units` 按用户输入切分历史，`_unit_view` 只投影脱敏摘要，`transform_request_context` 按 hook 结果丢弃整单元、取消优先、拒绝时抛出脱敏的 `ModelRequestRejected`，`check_model_request` 重写任务归属并在 `turn` 请求上先变换再询问 `before_request`，`record_model_rejection` 每个错误只写一条 `model_error`。原有 `scripts/check_request_policy.py` 只做片段、计数与文档扫描，本轮在脚本内加入行为对照（55 项）：覆盖历史单元的空输入 / 无用户消息 / 中途用户消息切分，单元摘要的 1000 字符截断、密钥脱敏、工具名 64 条上限与字符计数，变换的单元不足、无结果、空丢弃、取消优先、丢弃指定单元与拒绝脱敏，请求检查的归属重写、取消短路、回合专属变换与前后上下文白名单，拒绝载荷的固定字段与身份白名单，以及记录的单次写入与幂等。CI 无需改动，技术参考同步说明。修复 Issue [#3077](https://github.com/can4hou6joeng4/boss-harness/issues/3077)。
- 变异验证：结构侧拒绝白名单删除、拒绝来源改动、拒绝标记改动、单元截断删除、工具名上限删除、单元不足判据改动、变换取消判据删除、丢弃集合改动、归属重写删除、请求取消判据删除、回合判据放宽、请求拒绝判据删除、记录幂等删除、记录标志删除、变换拒绝脱敏删除十五种，行为侧中途用户消息删除、末尾切片改动、单元截断删除、工具名上限删除、工具计数收窄、单元不足判据改动、变换取消判据删除、空丢弃放行、丢弃方向反转、归属重写删除、请求取消判据删除、回合判据放宽、记录幂等删除十三种，均被检查发现（28/28）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.476` / Python `0.2.0rc476`。

## 0.2.0-rc.475 - 2026-11-22

rc.475 源码候选为重复调用提醒补充行为对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `LoopGuard` 在回合内观察连续同名同参的工具调用，第 3、5 次生成一条不含参数的用户提醒；参数不可安全序列化或超过 64 KiB 时放弃观察并清空计数。原有 `scripts/check_loop_guard.py` 只做常量、片段与 `agent.py` 调用时机的静态扫描，本轮在脚本内加入行为对照（66 项）：直接构造 `LoopGuard` 覆盖第 3、5 次提醒与其余次数静默、参数与工具名变化重置计数、键序与嵌套顺序归一、`reset` 清空、NaN / 混合键 / 循环引用与超长参数放弃观察并清空旧计数、提醒不含参数、工具名截断 64 字符与上限、实例隔离；并补强规范化参数整段序列化、payload 摘要与 `self.reset()` 的结构片段。CI 无需改动，技术参考同步说明。修复 Issue [#3075](https://github.com/can4hou6joeng4/boss-harness/issues/3075)。
- 变异验证：结构侧阈值改动、提醒上限改动、参数上限改动、规范序列化删除、键序删除、分隔符改动、序列化异常收窄、摘要长度检查删除、工具名摘要删除、摘要比较反转、计数不增、阈值放行、工具名不截断、文案超限放行、重置清空删除、放弃观察不重置十六种，行为侧键序删除、工具名删除、长度上限删除、非数值放行、摘要比较反转、计数不增、阈值放行、放弃不重置、工具名不截断、计数重置删除、重置清空删除十一种，均被检查发现（27/27）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.475` / Python `0.2.0rc475`。

## 0.2.0-rc.474 - 2026-11-22

rc.474 源码候选固定任务归属投影与关系判定的行为口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `task_ownership.py` 是 `task/read` 的只读投影层：`turn_snapshot` 按查询集合与队列关联过滤、标记重复回合与队列身份变化，`queue_snapshot` 投影队列身份并标记冲突，`user_message_refs` 只投影用户消息身份事实，`resolve_queue_relation` / `resolve_compaction_relation` 用多重证据判定归属，`recovery_policy` 给出恢复策略。新增 `scripts/check_task_relation.py`（104 项）：行为侧直接调用六个纯函数，覆盖回合过滤与上限、终态后 running 重复、queueId 身份变化、阶段归并与策略枚举、队列三条选中来源与身份冲突、用户消息每队列与修订上限、推断回合、followUp 与 steering 的五类归属及冲突优先级、压缩任务的会话 / 检查点 / 唯一回合判据、恢复策略的未知优先与各状态分支；结构侧按顺序固定三个关系函数的判定优先级。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3073](https://github.com/can4hou6joeng4/boss-harness/issues/3073)。
- 变异验证：结构侧冲突条件删除、重复回合检查删除、followUp 分支删除、steering 分支删除、转向目标改动、回合关联收窄、检查点冲突删除、重复回合放行、唯一匹配删除、未知状态优先删除、进程持有删除、人工中断策略删除、关闭策略删除、队列分支删除、排队分支删除十五种，行为侧终态后运行判据删除、队列身份判据删除、回合上限删除、策略判据放行、身份字段收窄、队列上限删除、回执编号校验删除、每队列上限删除、修订上限放宽、身份冲突删除、唯一匹配放宽、未知状态优先删除十二种，均被检查发现（27/27）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.474` / Python `0.2.0rc474`。

## 0.2.0-rc.473 - 2026-11-22

rc.473 源码候选固定启动恢复的阶段收尾、条目结算与回合中断口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.recover()` 是启动恢复入口：遍历全部会话（含归档），跳过无法读取的损坏会话且不阻断其他会话；按每个任务最新的 `task_phase` 归并，已终态回合补 `terminalStateRecovered` / `closed` 收尾，未终态回合写 `processExit` / `manual` 中断；再把仍为 `running` 的条目或失效审批按 `_abandoned_item_payload` 结算为失败修订，并把受影响回合改为 `interrupted`。新增 `scripts/check_recovery.py`（69 项）：结构侧切片 `recover`，按顺序断言归档遍历、损坏跳过、最新阶段归并、两种收尾、两条阶段记录、条目结算与回合中断，反向断言原因与错误码文案、调用次数及审批截止时间判据固定；行为侧在临时目录构造 `SessionStore`，覆盖 running 回合与阶段的中断收尾、已终态回合只补终态收尾、已收尾阶段幂等、运行中条目结算、已完成条目与未知回合跳过、损坏会话不阻断其他会话、归档会话同样恢复。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3071](https://github.com/can4hou6joeng4/boss-harness/issues/3071)。
- 变异验证：结构侧归档遍历关闭、损坏会话改抛出、终态状态改中断、终态原因改退出、终态策略改人工、幂等跳过删除、运行阶段记录删除、收尾记录删除、条目过滤删除、审批截止检查删除、条目追加删除、回合中断删除、阶段归并删除、尝试钳制改动、错误码改动十五种，行为侧归档遍历关闭、终态原因改退出、终态策略改人工、幂等跳过删除、运行阶段记录删除、收尾记录删除、条目过滤删除、回合中断删除、条目不追加、损坏会话改抛出十种，均被检查发现（25/25）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.473` / Python `0.2.0rc473`。

## 0.2.0-rc.472 - 2026-11-22

rc.472 源码候选固定分叉时的上下文检查点归属过滤。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `fork_thread` 的 `checkpoint_in_branch` 以 `throughTurnId` 在当前分支回合表中的位置为判据，只复制覆盖选中回合或更早回合的上下文检查点；复制前缀与边界后的恢复修正共用同一判据，未知回合与非字符串标识被过滤。新增 `scripts/check_fork_checkpoints.py`（20 项）：在临时目录构造会话做行为对照，覆盖两回合前缀裁剪、边界前后的检查点、未知 / 非字符串 / 缺失 `throughTurnId`、恢复修正中的归属过滤与默认回合分叉；源码按顺序扫描位置表、选中位置、安全读取与两处调用。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3069](https://github.com/can4hou6joeng4/boss-harness/issues/3069)。
- 变异验证：结构侧判据改小于、判据恒真、未知回合放行、载荷改下标、标识改下标、判据不比较位置、位置表反向、前缀过滤删除、恢复修正删除九种，行为侧判据改小于、判据恒真、判据恒假、位置表反向、前缀过滤放行、恢复修正放行六种，均被检查发现（15/15）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.472` / Python `0.2.0rc472`。

## 0.2.0-rc.471 - 2026-11-22

rc.471 源码候选固定会话日志精确读取原语的定位、短读与拼接边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_read_exactly_at` 是快照校验、事件重写与检查点发布共用的精确读取原语：描述符按 `SEEK_SET` 定位到给定偏移，循环读取直到取满请求长度；空块抛「会话日志读取不完整」，绝不返回部分数据；同一描述符上的多次调用按各自偏移重新定位。新增 `scripts/check_exact_read.py`（35 项）：结构侧按顺序断言定位、循环、空块拒绝、按实际字节递减与拼接返回；行为侧打开真实临时文件，覆盖中段与跨换行读取、整文件、零长度、读取后位置、两次调用复位、越界与超长读取的 `OSError`、空文件与失败后复用。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3067](https://github.com/can4hou6joeng4/boss-harness/issues/3067)。
- 变异验证：结构侧定位改相对、定位删除、循环改单次、空块检查删除、空块改跳出、递减改减一、返回改列表、读取长度加一、短读文案改动、追加改插入、预读插入十一种，行为侧定位改相对、定位删除、空块改跳出、递减改减一、返回改列表、读取长度加一六种，均被检查发现（17/17）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.471` / Python `0.2.0rc471`。

## 0.2.0-rc.470 - 2026-11-22

rc.470 源码候选固定删除会话时修复备份的清理与清单重写口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore._purge_repair_backups` 在删除会话时清理索引修复留下的备份：`repairs/` 目录与递归发现的 `state.sqlite3`、`-wal` / `-shm` sidecar 都必须是当前用户拥有的私有普通文件；数据库版本不得高于 `SCHEMA_VERSION`，在事务内只删除该会话的 events / turns / threads 行，`VACUUM` 后截断 WAL；存在 `manifest.json` 时过滤两个 sidecar 条目、按实际文件更新数据库条目的 bytes 与 sha256，以独占临时文件加 `os.replace` 发布并刷新目录。新增 `scripts/check_repair_backup.py`（126 项）：在临时目录构造 `SessionStore` 与备份目录做行为对照，覆盖无备份目录、目录不可信、多备份目录与嵌套目录、目标会话删除与其他会话保留、空库与恰好当前版本、较新版本拒绝且不改行、数据库与 sidecar 的硬链接 / 符号链接拒绝、清单损坏与非 UTF-8 与格式无效、清单过滤与摘要更新、清单缺失不创建、数据库与清单权限收紧；sidecar 用例用 WAL 模式并保持连接，避免 SQLite 提前清理。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3065](https://github.com/can4hou6joeng4/boss-harness/issues/3065)。
- 变异验证：结构侧目录所有者放行、目录类型放行、数据库所有者放行、数据库链接计数放行、版本守卫删除、表守卫恒真、提交改回滚、`VACUUM` 删除、WAL 结果放行、sidecar 所有者放行、sidecar 链接计数放行、清单捕获收窄、清单格式检查删除、sidecar 过滤收窄、清单大小不更新、清单摘要不更新、临时文件非独占、临时文件不清理、原子替换删除、清单删除插入、只处理第一份、版本比较改大于等于、回合删除删除、数据库权限不收紧、清单权限不收紧、WAL 原因文案改动二十六种，行为侧目录类型放行、数据库链接计数放行、版本守卫删除、版本比较改大于等于、事件删除放行、回合删除删除、sidecar 链接计数放行、sidecar 过滤收窄、清单大小不更新、清单摘要不更新、原子替换删除、数据库权限不收紧、只处理第一份十三种，均被检查发现（39/39）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.470` / Python `0.2.0rc470`。

## 0.2.0-rc.469 - 2026-11-22

rc.469 源码候选固定分支摘要合法性校验的固定原因、上限与判定顺序。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `branch_summary_issue` 是上下文注入与导出共用的分支摘要校验：正文必须是非空字符串且不超过 32000 字符，`targetTurnId` 缺省或以参考分支位置表为准，`abandonedTurnIds` 必须是 1–200 条、单条 ≤128 字符、总长 ≤4096 字符的字符串列表，`sourceTextDigest` 与 `summaryJobId` / `fromTurnId` 只在提供时有界；六类中文原因按固定顺序返回第一条且不改写载荷。新增 `scripts/check_summary_issue.py`（82 项）：结构侧切片顶层函数按顺序断言六类原因、上限常量与辅助标识顺序；行为侧覆盖合法载荷、目标回合在 / 不在位置表、正文恰好与超限、列表条数与单条长度及总长边界、来源摘要与辅助标识边界、七组多错误优先级、载荷不被改写，内核意外类型异常折算为检查失败原因。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3063](https://github.com/can4hou6joeng4/boss-harness/issues/3063)。
- 变异验证：类型检查删除、空正文删除、上限改等号、目标回合删除、空列表放行、条数硬编码、元素长度删除、总长删除、来源摘要删除、辅助标识顺序交换、两处文案改动、载荷改写插入、来源摘要块前移，以及类型放行、空正文放行、上限加一、目标回合放行、空列表放行、条数加一、元素长度删除、元素长度加一、总长删除、来源摘要放行、辅助标识放行、载荷改写与五组判定顺序重排三十一种改动均被检查发现（31/31）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.469` / Python `0.2.0rc469`。

## 0.2.0-rc.468 - 2026-11-22

rc.468 源码候选固定删除会话时私有文件清理的所有者、链接计数与目标确认口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore._remove_private_temporaries` / `_remove_thread_files` 是删除链路的文件清理边界：临时文件必须是当前用户拥有的普通文件，链接计数为 2 时必须确认目标文件也是同一 inode 的私有普通文件，其余链接计数一律暂停；删除前收紧权限、删除后刷新目录。`_remove_thread_files` 先清理会话临时文件、删除标记临时文件与事件日志临时文件三类残留，再删除链接计数为 1 的会话主体，主体缺失直接返回。新增 `scripts/check_delete_cleanup.py`（59 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖普通与缺失临时文件、独占硬链接临时文件与权限收紧、目标缺失 / 不同 inode / 三重链接 / 符号链接 / 目录拒绝、会话主体删除与三类临时文件清理、重复清理，以及硬链接与符号链接主体拒绝；源码扫描固定所有者、普通文件、链接计数、同一 inode、权限收紧与刷新目录。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3061](https://github.com/can4hou6joeng4/boss-harness/issues/3061)。
- 变异验证：不校验所有者、非普通文件放行、链接计数判断错位、目标缺失放行、目标所有者放行、目标链接计数放宽、不核对同一 inode、其他链接计数放行、不收紧权限、不删除文件、不刷新目录、遗漏事件临时文件、主体不看链接计数、主体不看所有者、主体不刷新目录、主体不删除，以及信任双重链接、符号链接被删除、临时文件不清理、只删主体不清理临时、只清理临时不删主体、硬链接主体被强删二十二种改动均被检查发现（22/22）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.468` / Python `0.2.0rc468`。

## 0.2.0-rc.467 - 2026-11-22

rc.467 源码候选固定删除会话时事件日志重写的校验、游标与原子发布口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore._rewrite_events_for_deletion` 是删除链路里最复杂的一环：源日志必须是私有普通文件、打开后设备与 inode 与可见路径一致、写入后复核九元组签名；逐行校验事件帧、游标与事件编号唯一、会话编号合法，只丢弃目标会话的事件，匹配恢复标记的删除事件必须恰好一条且形态正确，缺失时按高水位加一生成；临时文件独占创建并以硬链接或替换发布。`_event_high_water` 取索引最大游标与自增序列较大者，`_previous_deletion_event` 跳过损坏行并按会话匹配。新增 `scripts/check_event_rewrite.py`（117 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖删除重写保留其他会话与无会话事件、游标自增、重复删除幂等、预置删除事件复用、冲突拒绝、损坏 / 重复游标 / 重复事件 / 非法帧 / 非法会话编号拒绝、符号链接拒绝、缺失日志新建，以及高水位与旧事件查找的两类损坏跳过；源码扫描固定校验顺序、去重集合、签名复核与发布分支，反向断言三类变化拒绝、硬链接与替换各一次。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3059](https://github.com/can4hou6joeng4/boss-harness/issues/3059)。
- 变异验证：会话编号缺失放行、普通文件检查收窄、可见性不复核、临时名无随机后缀、临时文件不独占、高水位恒零、空行被丢弃、解码错误不包装、非对象放行、帧字段不校验、游标与编号不校验、重复游标放行、重复事件放行、高水位不更新、冲突不拒绝、其他会话事件保留、重复删除事件阈值放宽、游标耗尽不拒绝、新游标跳号、删除事件方法变化、不补换行、不刷新输出、不落盘、签名不复核、硬链接改替换、临时文件不清理、目录不刷新、缺事件不报错、忽略自增序列、损坏行不跳过、匹配任意会话，以及旧删除事件恒空、旧删除事件不区分会话、高水位恒零、删除事件缺游标、删除不返回事件三十六种改动均被检查发现（36/36）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.467` / Python `0.2.0rc467`。

## 0.2.0-rc.466 - 2026-11-22

rc.466 源码候选固定回合分页的游标、排序与损坏守卫口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.list_turns` 是回合列表的分页入口：游标绑定 `{"threadId"}` 范围，键是 `(first_ordinal, turn_id)` 的整数加标识符，查询用同一双列比较并 `ORDER BY first_ordinal,turn_id`，多取一行判定下一页；读取前刷新会话索引，索引行的 `first_ordinal` 必须是整数、`turn_id` 必须是字符串，损坏时按会话重建；`_turn_metadata` 只解码投影 JSON，非对象按索引损坏处理且信号携带会话 id。新增 `scripts/check_turn_page.py`（69 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖升序分页与续页、相同序号 tie、空页、游标范围与种类绑定、十类非法游标键、入参与会话边界、三类索引损坏后的重建；源码扫描固定游标种类、双列比较、多取一行、索引刷新与两处守卫，反向断言单会话读取不带跳过集合、损坏信号读 `thread_id` 而非条目 id。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3057](https://github.com/can4hou6joeng4/boss-harness/issues/3057)。
- 变异验证：移除 limit 校验、移除会话格式校验、范围为空、游标种类变化、序号类型放宽、负序号放行、回合标识符不校验、游标退回单列、排序改降序、不多取一行、不刷新索引、序号类型不守卫、回合编号不守卫、游标无条件返回、重建携带跳过集合、解码信号改普通错误、信号读取条目编号、重复解析、非对象放行，以及 limit 放行零与超限、返回顺序改降序、游标恒返回、游标键改回合编号、损坏行不重建、非对象投影放行、游标不绑定范围二十六种改动均被检查发现（26/26）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.466` / Python `0.2.0rc466`。

## 0.2.0-rc.465 - 2026-11-22

rc.465 源码候选固定回合阶段检查点与失败回合收尾的字段、枚举与幂等口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.record_task_phase` 只记录有界的阶段观察：任务编号标识符、五个阶段、`_TERMINAL` 加 `running` 的状态、`attempt` 1–1000、`restartLimit` 0–32、恢复原因与恢复策略的枚举和长度，可选键只在提供时进入载荷；`_abandoned_item_payload` 是启动恢复与在线结算共用的终态修订规则：剥离身份字段、状态恒为 `failed` 并指向原条目、待决审批结算为 `expired`、工具调用按执行状态区分「未执行」与「结果不确定」；`settle_abandoned_turn` 在锁内结算属于该回合的 `running` 条目与待决审批并返回条目数。新增 `scripts/check_turn_phase.py`（135 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖阶段记录的固定与可选字段、十九类非法入参、全部阶段与状态枚举、失败回合的消息与工具条目结算、四种「未执行」与三类「结果不确定」、待决审批结算与字段保留、其他回合与已终态隔离、多条逐条结算与重复调用幂等；源码扫描固定三个阶段方法的字段、枚举、顺序与计数，反向断言阶段记录恰好一条、在线结算只有两处跳过。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3055](https://github.com/can4hou6joeng4/boss-harness/issues/3055)。
- 变异验证：移除任务编号校验、阶段任意放行、状态任意放行、尝试上限放宽、尝试类型放宽、重启负值放行、可选文本上限放宽、恢复原因枚举收窄、恢复策略枚举收窄、归属改为任务、恢复原因恒写、恢复策略恒写、记录类型改为条目、不剥离会话编号、状态改为 error、审批改为拒绝、工具分支改为消息、未执行集合收窄、未执行摘要不覆盖、移除锁、移除会话确认、移除归属判断、计数加倍、错误码改为进程恢复，以及任务编号校验放行、最小记录带可选键、恢复原因不写入、尝试恒为一、结算其他回合、结算已终态条目、结算计数恒零、失败条目重复结算、终态状态改为 error、审批不结算、执行状态恒不确定、消息条目带工具字段三十六种改动均被检查发现（36/36）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.465` / Python `0.2.0rc465`。

## 0.2.0-rc.464 - 2026-11-22

rc.464 源码候选固定会话列表分页的筛选、游标与损坏行隔离口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.list_threads_page` 是桌面会话列表的分页入口：`archived` / `projectId` 绑进分页游标范围，双列游标 `(updated_at, id)` 与 `ORDER BY updated_at DESC,id DESC` 一致，待删除标记在 SQL 内过滤，损坏投影行从候选窗口之外继续取行且不吃掉翻页余量，`nextCursor` 只在确有下一页时返回；`_thread_metadata` 把投影行的结构损坏转成内部重建信号，超长标题与项目编号截断并标记而不是拒绝。新增 `scripts/check_thread_page.py`（117 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖倒序分页与续页、相同时间按编号 tie、恰好一页与空库、归档 / 项目筛选、游标范围绑定与七类非法游标、`limit` 与筛选入参边界、待删除过滤、损坏行跳过与 lookahead、超长截断、投影损坏重建、`updated_at` 被改写为 BLOB 后重建；源码扫描固定入参校验顺序、参数绑定、双列游标、`skip` 重建重试与 `nextCursor` 条件，反向断言排序恰好一处、项目筛选走参数绑定、日期解析在 `try` 内。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3053](https://github.com/can4hou6joeng4/boss-harness/issues/3053)。
- 变异验证：移除 limit 校验、放宽 archived 类型、移除项目编号上限、scope 忽略项目、游标种类变化、项目编号拼接进 SQL、游标编号不校验、游标日期不校验、游标退回单列、排序改升序、待删除不过滤、跳过集合失效、时间列不校验、翻页判定改大于等于、游标无条件返回、重建不带跳过集合、会话编号不核对、必需字段不校验、项目编号改为拒绝、标题改为拒绝、返回时改写编号，以及 limit 放行零与超限、默认包含归档、归档参数被忽略、项目参数被忽略、返回顺序改升序、游标恒返回、待删除出现在分页、待删除出现在旧列表、不可读会话不登记、超长字段不截断、损坏行不重建、游标不绑定范围三十三种改动均被检查发现（33/33）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.464` / Python `0.2.0rc464`。

## 0.2.0-rc.463 - 2026-11-22

rc.463 源码候选固定会话元数据更新与归档的字段、上限与幂等口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore._validate_changes` / `update_thread` / `archive_thread` / `unarchive_thread` 决定会话元数据如何进入日志：`project_id` 规范化、七字段白名单、`toolPolicy` / `reasoningEffort` 枚举、`title` / `projectId` / `provider` / `cwd` / `model` 校验，空更新不写记录，归档在锁内结算未裁决审批并幂等。新增 `scripts/check_thread_meta.py`（94 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖空更新、标题与项目更新、规范化与重复拒绝、身份字段、各类上限与类型、不可序列化值、不存在会话，以及归档 / 恢复的幂等与记录数；源码扫描固定规范化、白名单、逐字段校验与写入门槛；反向断言白名单恰好七字段、规范化先于白名单、序列化校验在逐字段校验之后。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3051](https://github.com/can4hou6joeng4/boss-harness/issues/3051)。
- 变异验证：入参复制、规范化、重复拒绝、旧键弹出、白名单字段、白名单判断、遍历方式、工具策略、推理档位、标题上限、`provider` 空白、项目编号上限、`cwd` 类型、`model` 类型、序列化校验、空更新、更新校验、更新写入、归档总写、审批结算、归档标记、归档锁、恢复总写、恢复标记、别名，以及空更新写记录、标题放行、工具策略放行、未知字段放行、归档非幂等、恢复非幂等三十一种改动均被检查发现（31/31）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.463` / Python `0.2.0rc463`。

## 0.2.0-rc.462 - 2026-11-22

rc.462 源码候选固定内核事件回放的游标分页、筛选与索引重建。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.events_after` / `_event_rows` / `_event_page_entries` 是事件回放的分页入口：查询取 `limit + 1` 行判定 `hasMore`，按 `params_json` 原始字节预算逐行读取且首行超预算也返回，索引行必须与自身游标、`method` 列一致，损坏时从 `events.jsonl` 重建并重试一次；`append_event` 负责保护字段、方法名与参数校验、落盘与索引同步。新增 `scripts/check_event_page.py`（111 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖追加帧、游标分页与续页、空页、`threadId` / `methods` 筛选、无效入参、删除标记过滤、索引损坏重建、`latest_event_cursor` 与重启后剔除已删除会话并追加 `thread/deleted`；源码扫描固定 `limit + 1`、预算与四类索引损坏与落盘顺序；反向断言只在条数与字节两处截断。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3049](https://github.com/can4hou6joeng4/boss-harness/issues/3049)。
- 变异验证：limit 上限、多取一行、重建、待删除过滤、首行预算、条数截断、游标一致性、页内截断、方法名校验、可序列化校验、单行上限、事件编号、帧游标、时间戳、落盘、索引参数更新，以及忽略分页、`hasMore` 恒假、`nextCursor` 恒零、不过滤删除、忽略方法筛选、忽略会话筛选、帧缺编号、帧游标恒定、删除事件缺字段、不重建二十六种改动均被检查发现（26/26）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.462` / Python `0.2.0rc462`。

## 0.2.0-rc.461 - 2026-11-22

rc.461 源码候选固定会话删除标记的校验、原子发布与重启恢复。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `.delete-<threadId>.json` 标记是「会话删除后暂不可操作」的持久边界：`_read_delete_intent` 校验文件名、大小、JSON 形状与四个字段；`_write_delete_intent` 用独占临时文件加硬链接发布，已存在时读回而不覆盖；`_pending_deletion_ids` 只按名称列出阻塞会话；`_recover_deletions` 在启动时完成合法标记、保留损坏标记。新增 `scripts/check_delete_intent.py`（102 项）：在临时目录构造 `SessionStore` 做行为对照，覆盖写入四键、摘要去重排序、事件编号形状、`0600` 权限、临时文件清理、读回与阻塞列表；十种损坏标记全部拒绝，重启后保留并继续阻塞，合法标记重启后完成删除并保留其他会话。源码扫描固定校验顺序、独占发布、名称枚举与恢复保留语义；反向断言不使用 `os.replace`、阻塞列表不读取内容、移除标记后才刷新目录。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3047](https://github.com/can4hou6joeng4/boss-harness/issues/3047)。
- 变异验证：文件名、大小限制、解码、版本、会话、摘要类型、摘要正则、事件编号、额外字段、摘要排序、已存在读回、临时文件独占、硬链接发布、落盘、临时清理、目录刷新、阻塞列表内容与跳过、恢复保留、恢复完成、完成删除顺序、初始化收紧，以及摘要排序、临时残留、权限、不持久标记、重复写覆盖、阻塞、事件编号、文件名、完成删除保留文件三十一种改动均被检查发现（31/31）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.461` / Python `0.2.0rc461`。

## 0.2.0-rc.460 - 2026-11-22

rc.460 源码候选固定消息搜索的扫描、预算与截断口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.search_messages` 是有界全文搜索入口：会话数 / 文本预算、超大会话跳过、读取失败标记、逐条消息预算、工具调用文本投影、跨分支命中标记与三处展示截断都在这里；`_search_tool_text` 决定工具调用以什么文本进入搜索。新增 `scripts/check_search_scan.py`（104 项）：行为对照覆盖空工具名、来源编号、参数排序与不转义、不可序列化参数、2000 字符参数上限、摘要与 6000 字符文本上限；源码扫描固定查询 / `limit` / `include_archived` 校验、预算与跳过分支、读取失败标记、角色分流、索引映射、`onBranch`、结果截断与工具字段顺序。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3045](https://github.com/can4hou6joeng4/boss-harness/issues/3045)。
- 变异验证：查询上限、空查询早退、`limit` 范围、归档类型校验、会话预算、超大会话跳过、读取失败标记、消息预算、单条截断、展示上限、分支标记、`onBranch` 条件、索引映射、片段起点、结果截断、工具名早退、参数排序与转义、参数上限、摘要类型、文本上限、来源去空格，以及空工具名、工具名去空格、来源、参数排序、参数转义、参数上限、摘要、文本上限、拼接顺序、文本尾巴三十二种改动均被检查发现（32/32）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.460` / Python `0.2.0rc460`。

## 0.2.0-rc.459 - 2026-11-22

rc.459 源码候选固定搜索归一化入口的字符索引映射与 identity 判定。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore._search_normalized` 把文本按组合簇归一化，并在需要时返回每个归一化字符对应的原文起止索引；`search_messages` 依赖该索引把命中映射回原文片段，现有检查只对照聚类与单码点映射。新增 `scripts/check_search_index.py`（71 项）：ASCII 快速路径只小写且不保留索引，空串、单码点非 ASCII、组合记号、组合类重排、`ß` / `İ` 多字符折叠、谚文 jamo、半角假名、扩展 jamo、补表码点与代理项二十组完整三元组对照；identity 文本返回空索引；跨簇文本的 `starts` / `ends` 长度等于归一化文本、单调覆盖原文、与逐簇重建一致；折叠文本与补表逐簇拼接一致，无补表文本与默认分支一致。源码侧固定快速路径、identity 判定、两轮聚类遍历、`array('I')` 紧凑索引与两处调用点；反向断言不直接调用 `unicodedata`、不用列表保存索引。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3043](https://github.com/can4hou6joeng4/boss-harness/issues/3043)。
- 变异验证：ASCII 不折叠或保留索引、identity 初值或置假变化、判定缺少码点数或折叠长度、不跳过空片段、第二轮回退默认归一化、索引不按折叠长度展开、索引用列表、identity 出口返回索引、补表禁用、绕过聚类归一化、调用点改变、空片段写入截断、早退失效，以及 ASCII 不折叠、ASCII 保留索引、空串产生索引、identity 恒假、identity 恒真、索引少一项、索引偏移、补表不折叠、折叠文本加尾巴、补表路径替换字符二十七种改动均被检查发现（27/27）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.459` / Python `0.2.0rc459`。

## 0.2.0-rc.458 - 2026-11-22

rc.458 源码候选固定搜索的跨码点聚类与归一化对照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `session._search_clusters` 把基字符与组合记号、谚文 jamo、半角假名浊音符号、`GRAPHEME_V_EXTRA` 相邻码点并入同一簇，再按 `NFKC + casefold`（或补表的 `search_normalize`）产出片段，调用方依赖返回的原文区间建立映射；现有 `check_search_unicode.py` 只对照单码点归一化。新增 `scripts/check_search_clusters.py`（50 项）：空串、ASCII 大小写、组合记号、兼容字母、`ß`、谚文 jamo / 兼容 jamo / 预组合音节、半角假名与浊音符号、独立浊音符号、尾音后接 leading jamo 十六组行为对照；返回区间首尾相接、覆盖全文、`normalize` 回调逐簇接收原文片段、归一化结果再聚类保持幂等、普通路径与 `NFKC + casefold` 逐簇一致；源码扫描固定四类合并条件、默认与补表归一化分支以及两处调用点。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3041](https://github.com/can4hou6joeng4/boss-harness/issues/3041)。
- 变异验证：每簇起点提前、循环前移错误、不并入组合记号、不并入谚文 jamo、半角浊音集合改名、不并入扩展 V 码点、默认归一化缺少 NFKC、补表分支变化、调用点减少、聚类签名变化，以及空串产出空簇、ASCII 不折叠、组合记号不合并、谚文不合并、半角浊音不合并、忽略补表归一化、区间起点偏移、簇片段为空、幂等破坏、片段未折叠二十种改动均被检查发现（20/20）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.458` / Python `0.2.0rc458`。

## 0.2.0-rc.457 - 2026-11-22

rc.457 源码候选固定技能 frontmatter 解析与列表投影的截断口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SkillCatalog._fields` / `_descriptor` 决定技能名称与描述如何进入菜单投影。新增 `scripts/check_skill_descriptor.py`（44 项）：BOM 去除、起始与结束 `---` 整行判定、只解析两者之间、字段白名单、包裹引号去除；名称回退技能 id、描述缺省空串、投影五字段、200 / 500 字符截断与两个标记、先截断再标记、未超限不写标记。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3039](https://github.com/can4hou6joeng4/boss-harness/issues/3039)。
- 变异验证：不去 BOM、起始或结束行判定放宽、结束行查找范围变化、字段白名单或锚定放宽、引号去除缺失或方式变化、名称不回退、描述缺省移除、投影缺字段、名称上限或截断长度变化、两个标记缺失、先标记后截断、多出标记、结束行改前缀匹配二十种改动均被检查发现（20/20）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.457` / Python `0.2.0rc457`。

## 0.2.0-rc.456 - 2026-11-22

rc.456 源码候选固定技能创建、替换与删除的独占、原子与摘要口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SkillCatalog.create` / `replace` / `delete` 与 `_write_atomic` / `_ensure_directory` / `_existing_id` / `_require_directory` 决定技能文件的写入与删除，现有检查没有固定这条链路。新增 `scripts/check_skill_write.py`（151 项）：id 与正文校验、按需目录创建、`mkdir` 独占与失败回退、技能目录 / 根 / 父目录 fsync 顺序、`.SKILL-*.tmp` 临时文件、fsync 与 `chmod 0644`、`os.replace` 原子发布、失败清理、替换与删除的摘要格式与当前摘要校验、删除仅限 `["SKILL.md"]` 且先 unlink 后 rmdir、目录名单层与控制字符规则。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3037](https://github.com/can4hou6joeng4/boss-harness/issues/3037)。
- 变异验证：id 规则或目录名限制放宽、目录可覆盖、重复消息变化、失败不回退、两处目录 fsync 缺失、新建摘要或错误类型变化、绕过原子写入、临时名前缀变化、不 fsync、权限放宽、非原子发布、目录不刷新、失败不清理、替换与删除跳过校验或放宽摘要、替换不核对摘要、删除允许其他文件、先 rmdir、回执缺摘要、目录辅助接受符号链接三十一种改动均被检查发现（31/31）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.456` / Python `0.2.0rc456`。

## 0.2.0-rc.455 - 2026-11-22

rc.455 源码候选固定技能目录枚举的有界窗口与截断口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SkillCatalog.scan` / `_candidate_paths` / `_problem_reason` 决定技能目录如何进入 `skills` 与 `problems` 以及三个截断标记，现有 `check_skills.py` 只核对类存在。新增 `scripts/check_skill_catalog.py`（110 项）：根符号链接拒绝、缺失根与缺失目录早退、非目录与扫描失败报错、`follow_symlinks=False`、字典序窗口与 `dropped`、窗口翻倍不超过 `MAX_SKILL_SCAN_ENTRIES`、代理项 id 转 `repr`、超长 id 截断、`_read_bounded` 失败归类、`_descriptor` 投影、`exhausted` / `fulfilled` 终止条件、三种截断标记与问题清单截断；`_problem_reason` 覆盖缺失、两处不可读、两处超限、非 UTF-8 与兜底；`list()` 只投影扫描结果。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3035](https://github.com/can4hou6joeng4/boss-harness/issues/3035)。
- 变异验证：根符号链接不拒绝、缺失根或目录不早退、非目录不拒绝、跟随符号链接、不记录丢弃、替换条件放宽、候选不排序、枚举完毕判定错误、截断条件或标记缺失、候选截断恒假、窗口不翻倍、终止条件缺少扫描上限、代理项不转 repr、超长 id 不截断、读取失败不归类、描述投影缺失、问题清单不截断、原因归类缺失或放宽、原因兜底变化、列表不经扫描、扫描签名变化二十六种改动均被检查发现（26/26）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.455` / Python `0.2.0rc455`。

## 0.2.0-rc.454 - 2026-11-22

rc.454 源码候选固定技能上下文注入的数量、路径与摘要口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SkillCatalog.load` 把选中技能正文注入当前回合提示词，现有 `check_skills.py` 只核对类存在与不使用目录枚举。新增 `scripts/check_skill_context.py`（41 项）：10 项上限与字符串元素、去重保序、两处空结果早退、每次调用重建目录映射、存在性校验、固定 `SKILL.md` 路径与越界检查、`_read_bounded` 单次读取与大小限制错误、摘要一致性、`<skill name={json.dumps(id)}>` 包装与空行分隔、选中记录来自目录；反向断言摘要校验后才记录选中与追加正文。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3033](https://github.com/can4hou6joeng4/boss-harness/issues/3033)。
- 变异验证：ids 上限或类型放宽、不去重、空数组或 `None` 不早退、目录映射不重建、选中记录来自用户输入、路径不固定或不核对越界、正文读取两次或无界读取、摘要不核对或来源字段变化、变化消息变化、名称不转义或改为 ASCII 转义、开始 / 结束标签变化、分隔符变化、选中或正文先于摘要校验、空数组返回非空、存在性不校验二十三种改动均被检查发现（23/23）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.454` / Python `0.2.0rc454`。

## 0.2.0-rc.453 - 2026-11-22

rc.453 源码候选固定附件上下文注入的数量、去重与预算口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `AttachmentStore.context` 把选中附件正文拼进当前回合提示词，现有检查没有固定这条注入链路。新增 `scripts/check_attachment_context.py`（42 项）：10 项上限与字符串元素、去重保序、`None` 与空数组早退、缺省读取条目与显式传入时的会话核对、名称 JSON 转义与来源声明、按附件字节累计并严格大于 2 MiB 拒绝、预算通过后追加附件与文本、空行分隔、投影剔除 `content`；反向断言预算不计标签、正文只读取一次、会话条目只读取一次。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3031](https://github.com/can4hou6joeng4/boss-harness/issues/3031)。
- 变异验证：ids 上限或类型放宽、不去重、空数组或 `None` 不早退、缺省不读取条目、显式条目不核对会话、名称不转义或改为 ASCII 转义、标签不声明来源、正文读取两次、预算按标签长度或不累计、允许等值、错误消息变化、附件或文本先于预算追加、分隔符变化、投影保留正文或整条复制、去重改为排序、会话条目读取两次、投影键名变化二十四种改动均被检查发现（24/24）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.453` / Python `0.2.0rc453`。

## 0.2.0-rc.452 - 2026-11-22

rc.452 源码候选固定附件分页读取的游标绑定与解码口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `AttachmentStore.read_chunk` / `_attachment_from_entries` / `_read_from_entries` 与 `_attachment_cursor_offset` / `_stale_attachment` / `_decode_attachment_text` 决定附件的分页读取，现有 `check_attachments.py` 只覆盖常量与请求字段。新增 `scripts/check_attachment_read.py`（103 项）：`limit` 严格范围、记录摘要 / 名称 / 字节校验、按记录读取对象、`sha256` 匹配与 `STALE_ATTACHMENT`（`-32011`、`currentRef`）、游标前缀 / 长度 / 四元组 / 严格偏移 / base64url 严格解码与五类异常、`min` 截断、仅未读完生成游标、紧凑 JSON 与无填充编码、`wire_text` 与 `contentRef` 字段；反向断言读取入口经条目投影、记录复制、`include_content` 关闭时不读对象、记录损坏两处判定、解码错误转为产品错误。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3029](https://github.com/can4hou6joeng4/boss-harness/issues/3029)。
- 变异验证：limit 下限或类型放宽、对象字节数来源变化、摘要变化不返回陈旧引用、游标长度不绑定文本、分页不截断、默认游标非空、总是生成游标、载荷三元组、非紧凑 JSON、保留填充、前缀变化、正文不降级、contentRef 长度变化、游标前缀或长度上限放宽、base64 宽松、载荷长度放宽、偏移允许等值、异常集合缩小、游标消息变化、第二处损坏判定放宽、摘要格式不校验、名称或字节范围上限放宽、查找不按 id、名称不降级、解码不捕获、错误码变化、读取入口触碰对象、`include_content` 恒真、记录不复制三十二种改动均被检查发现（32/32）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.452` / Python `0.2.0rc452`。

## 0.2.0-rc.451 - 2026-11-22

rc.451 源码候选固定附件添加的发布与配额口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `AttachmentStore.add` / `_publish_object` / `_read_object` / `_storage_usage` 决定附件从工作区读入、配额判定与原子落盘，现有 `check_attachments.py` 只覆盖配额常量、读取分页与清理片段。新增 `scripts/check_attachment_add.py`（103 项）：允许根与保留目录、扩展名集合、`O_NOFOLLOW` 非阻塞打开、普通文件与 2 MiB + 1 上限、UTF-8 与 SHA-256、附件名降级、发布查重与两项配额（严格大于）、`tmp-` 临时名、独占创建、fsync、`os.replace`、先记账后回调、finally 清理、失败清理未引用对象并仅在清理成功时回退计数、重新抛出原异常；反向断言读取的三层损坏判定、未移交描述符关闭、`_storage_usage` 不重扫目录、`mark_published` 只置一次、清理失败不影响原异常。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3027](https://github.com/can4hou6joeng4/boss-harness/issues/3027)。
- 变异验证：路径不再限定允许根、后缀不受限、允许环境文件、添加或读取时跟随符号链接、上限 + 1 丢失、不校验 UTF-8、附件名不降级、发布标记可重复置位、失败不清理、清理失败也回退、字节回退缺失、失败不重抛、发布不查重、两项配额改为允许等值、临时名缺前缀、不独占创建、不 fsync、非原子发布、不记账、回调先于记账、临时文件不清理、最终摘要不判损坏、未移交描述符不关闭、读取不复核摘要、配额快照重扫目录、缺少配额异常类型二十八种改动均被检查发现（28/28）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.451` / Python `0.2.0rc451`。

## 0.2.0-rc.450 - 2026-11-22

rc.450 源码候选固定会话读取缓存与增量解析口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.read_entries` / `read_entries_snapshot` 与缓存辅助函数决定每次读取是否复用已解析条目，现有检查只覆盖快照生命周期与分支投影。新增 `scripts/check_entries_cache.py`（108 项）：三元组缓存命中、副本返回、同一 inode 与严格更短的增量条件、旧前缀末尾换行、全量与增量的读取范围与行号、`_line_boundary` 的空文件与换行判定、快照锁外解码后的 stamp 复核、先移除再插入与最久未用淘汰；反向断言读取路径不直接操作缓存、两处副本、快照缺失或损坏不缓存。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3025](https://github.com/can4hou6joeng4/boss-harness/issues/3025)。
- 变异验证：缓存命中与结果返回内部列表、读取直接清空缓存、半条记录或空文件也缓存、边界不检查大小、快照不复核或异常按当前 stamp 缓存、快照不查缓存、命中不比较 stamp 或不移到末尾、增量不要求同一 inode 或允许同长、不核对末尾换行、返回空前缀、全量从末尾读取或不设限、全量行号偏移、增量从头或读全文件、行号不接续、缓存不淘汰或淘汰最近使用、不登记行数、先插入后移除二十五种改动均被检查发现（25/25）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.450` / Python `0.2.0rc450`。

## 0.2.0-rc.449 - 2026-11-22

rc.449 源码候选固定摘要 checkpoint 的原子发布口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.append_checkpoint` 把整份会话日志复制为候选文件、截到完整记录边界后追加 `context_checkpoint` 并以 `os.replace` 发布，现有检查只覆盖批量追加与附件引用。新增 `scripts/check_checkpoint_publish.py`（110 项）：双回调校验、九字段双重签名、条目只构造一次、`.checkpoint.tmp` 独占创建、1 MiB 分块与 `complete_end` 截断、`0600` / gid / fsync、三方签名、`os.replace` 后的四类身份判断、目录 fsync → 回调 → 索引顺序、已提交异常转换与 finally 清理；反向断言提交点唯一、不走追加路径、两类异常保持 `RuntimeError`。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3023](https://github.com/can4hou6joeng4/boss-harness/issues/3023)。
- 变异验证：回调校验放宽、单链接放宽、打开签名不核对、条目类型放宽、条目构造两次、改走追加路径、复制块缩小、不记录边界、残段不截断、无边界也接受、候选后缀变化、不独占创建、权限放宽、不 fsync、复制后 / 候选 / 发布前三方签名不核对、原始 inode 不重抛、候选不视为已提交、成功分支不核对、目录不 fsync、不调用回调、不刷新索引、提交后异常不转换、finally 不清理、清理失败不吞、两类异常基类变化二十八种改动均被检查发现（28/28）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.449` / Python `0.2.0rc449`。

## 0.2.0-rc.448 - 2026-11-22

rc.448 源码候选固定服务端请求的锁边界与响应降级。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 内核发起的审批等客户端请求由 `JsonRpcServer.request` / `cancel_request` / `close` / `_receive_response` 管理，现有 `check_rpc.py` 只做全文片段扫描。新增 `scripts/check_rpc_pending.py`（112 项）：pending 注册先于写出、写出失败取消并重抛、计时器守护与 fail closed、取消 / 接收锁内只 `pop`、`Future` 完成与计时器取消失在锁外、关闭锁内快照后锁外取消、`RESPONSE_TOO_LARGE` / `RESPONSE_INVALID` 的两层无 id 回退、三类回复只在有 id 时发出、handler 只运行一次、诊断先于错误响应；反向断言锁只加一次与 `ServerRequest` 冻结形状。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3021](https://github.com/can4hou6joeng4/boss-harness/issues/3021)。
- 变异验证：不登记 pending、关闭检查放宽、写出失败不取消 / 不重抛、计时器非守护或启动失败不取消、取消锁内解包或不查完成、取消不报告成功、关闭锁内逐个取消或不取消、响应不查完成或错误当结果、结果 / 错误不互斥、两层降级缺失、成功帧与错误帧不降级、handler 运行两次、诊断丢失、响应消息不先处理、`ServerRequest` 非冻结、params 错误不带 id、无 id 也回复、快照不复制二十五种改动均被检查发现（25/25）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.448` / Python `0.2.0rc448`。

## 0.2.0-rc.447 - 2026-11-22

rc.447 源码候选固定工具结果修订的恢复口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore.append_tool_revision` 是工具结果从不确定失败恢复的唯一入口，现有检查只覆盖分页与引用边界。新增 `scripts/check_tool_revision.py`（55 项）：条目格式、首次事务与写前 / 写后索引刷新、`inspect_and_sync` 的 conflict / invalid / durable / present_uncertain / absent 五种结果、`range(2)` 至多一轮重试、durable 与唯一重试的索引刷新、异常路径二次核对与不确定标记、最终异常附带最后一次错误；反向断言恢复路径不引用 handler 或审批、追加机会恰为两次、持久化错误重新抛出、异常类型保持 `OSError`。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3019](https://github.com/can4hou6joeng4/boss-harness/issues/3019)。
- 变异验证：条目校验放宽、内容不同当作一致、冲突报告 absent、损坏异常弱化、durable 不 fsync、不确定当作 durable、缺失不返回 absent、重试轮数放宽、首次写前不刷新、首次报告为恢复、durable 与唯一重试不刷新、两条路径不拒绝不确定结果、不确定继续重试、耗尽不抛错、持久化错误被吞、两处异常不捕获、二次核对不打标、二次核对不返回、恢复不按 id 或只比类型、首次不返回 False、异常基类改变、恢复引用 handler 二十六种改动均被检查发现（26/26）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.447` / Python `0.2.0rc447`。

## 0.2.0-rc.446 - 2026-11-22

rc.446 源码候选固定会话批量追加、新建发布与附件引用顺序。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SessionStore` 的 JSONL 写入顺序决定并发可见性与崩溃恢复，现有 `check_session_log.py` 只覆盖编码 / 解码 / 快照，`check_attachments.py` 只覆盖清理片段。新增 `scripts/check_session_batch.py`（99 项）：`append_many` 的批次校验、空批早退、整批编码先于事务、缺失末尾换行的 1 字节前缀、严格大于的上限与 `SessionSizeLimitExceeded`、写前 / 写后各一次索引刷新；`append` 的单条事务顺序；`_write_new` 的整卷编码、`.tmp` 临时名、fsync 后 `os.link` 发布与临时名清理；`append_attachment` 的历史校验 → 发布内容 → fsync 附件目录 → 写引用行；清理入口的锁与事务、引用扫描与临时名匹配。反向断言调用次数、编码不得进入事务、不得覆盖发布、不得绕过引用扫描。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3017](https://github.com/can4hou6joeng4/boss-harness/issues/3017)。
- 变异验证：批次类型与上限类型放宽、空批不早退、编码改惰性生成器、缺失换行不计前缀、上限含等于、超限异常弱化、批量写前 / 写后不刷新、逐行改列表推导、批量与单条互相委托、单条写前不刷新、新建不 fsync、覆盖发布、临时名后缀变化、不清理发布临时名、头编码缺上限、附件先发布后校验、不 fsync 目录、摘要不校验、重复写引用、清理脱锁、不扫描引用、临时清理匹配放宽、不删除、不 fsync 二十七种改动均被检查发现（27/27）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.446` / Python `0.2.0rc446`。

## 0.2.0-rc.445 - 2026-11-22

rc.445 源码候选固定队列新增、编辑、状态转移与暂停结算口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `TurnQueue` 的 `add` / `update_input` / `transition` / `claim` / `pause` / `settle_pauses` 是持久队列状态机，现有检查只覆盖 `promote_to_steering` 与桌面动作。新增 `scripts/check_queue_state.py`（128 项）：新增校验与客户端幂等、技能去重与转向限制、条目 `>=` / 字节 `>` 上限与 `QUEUE_LIMIT`、编辑按替换字节重算、转移表、steering 回合归属、暂停来源优先级与一次写回；反向断言投递中不回退、`pausedReason` 条件与作用域清理。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3015](https://github.com/can4hou6joeng4/boss-harness/issues/3015)。
- 变异验证：kind 放宽、客户端 id 正则放宽、技能不去重与数量放宽、转向允许技能、幂等不比对技能 / 覆盖、条目与字节上限放宽、新增状态改已投递、编辑不查状态与不重算字节、投递中回退、暂停继续投递、领取不校验回合、暂停覆盖原因、结算不按 kind 优先、`pausedReason` 总是写入、不写回、作用域不清理、返回空列表、统计漏掉投递中二十二种改动均被检查发现（22/22）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.445` / Python `0.2.0rc445`。

## 0.2.0-rc.444 - 2026-11-22

rc.444 源码候选固定上下文规模估算、请求指纹与成功用量校准口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `context.py` 的规模估算与用量校准直接决定压缩触发与上下文溢出恢复，现有检查只覆盖编辑路径与写工具集合。新增 `scripts/check_context_estimate.py`（124 项）：逐类型规模累加与每条 32 字符开销、向上取整的字符估算、provider 用量字段与 `MAX_REQUEST_TOKENS` 上限、请求指纹字段与 SHA-256、消息负载块字段、校准的 eligible / 前缀 / 冲突清空 / 严格递增 / 四舍五入与区间记录；反向断言不复制参数、不跳过 owners 校验。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3013](https://github.com/can4hou6joeng4/boss-harness/issues/3013)。
- 变异验证：用户正文、思考签名、脱敏数据、工具调用 id、工具结果 id 与每条开销不计、参数转义、估算遗漏系统提示与向下取整、OpenAI 混入缓存字段、负用量与上限放行、指纹遗漏 provider / thinking 与改用 SHA-1、负载遗漏 `prefixDigest` / `isError`、fallback 向下取整、锚点不要求 eligible、冲突不清空、非递增接受、不校验归属、前缀指纹不复核、四舍五入与增量换算错误二十五种改动均被检查发现（25/25）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.444` / Python `0.2.0rc444`。

## 0.2.0-rc.443 - 2026-11-21

rc.443 源码候选固定内核扫码登录的凭证校验、命令引用与保存回读边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 内核登录流程此前只有桌面侧检查：`begin_login` / `cancel_login` / `complete_login` / `_save_login` / `_local_auth` 的凭证格式、`shlex.quote` 引用、64 KiB 上限、保存后回读与取消归属没有专门守卫。新增 `scripts/check_login_flow.py`（131 项）：官方 Cookie 与 User-Agent 校验、`wt2` 必需、两处逐项引用、请求编号核对、`--curl-file -` 与固定超时、三档保存结果、槽位按取消标记比较、风控锁优先；反向断言凭证不写入状态、不经过 shell。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3011](https://github.com/can4hou6joeng4/boss-harness/issues/3011)。
- 变异验证：Cookie 与 User-Agent 上限放宽、控制字符与键格式不校验、不要求 `wt2`、64 KiB 上限取消、两处不引用、请求编号与等待状态不核对、保存前不查取消、命令文本不清空、回读改用原始结果、不要求已登录、错误码改写、槽位不比较、风控锁与未登录放行、凭证写入状态、平台忙与可用性不检查、取消不比对尝试 id 二十二种改动均被检查发现（22/22）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.443` / Python `0.2.0rc443`。

## 0.2.0-rc.442 - 2026-11-21

rc.442 源码候选固定运行时容量准入、回合归属与关闭中断口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `RuntimeManager` 的并发上限、owner 容量、槽位回收与 abort 认领只有部分关闭顺序检查，准入、预留、释放与容量通知 worker 没有专门守卫。新增 `scripts/check_runtime_capacity.py`（121 项）：`owner_capacity` 翻倍、`has_capacity` 双上限、`check_admission` 四类错误与顺序、`reserve` 锁内重复准入与双注册、`release` / `_retire_locked` 身份比较、幂等 abort 认领、锁外派发与等待、两秒停止窗口、容量通知 worker 的守护线程与关闭检查；反向断言单个 `closed` 写入、缩进敏感的锁外 `start` / `join` 与回调异常吞噬。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3009](https://github.com/can4hou6joeng4/boss-harness/issues/3009)。
- 变异验证：owner 容量不翻倍、可用容量不排除关闭、关闭错误码改写、两处上限改为严格大于、预留不重复准入、槽位不登记、释放 / 回收不比较身份、回收不等待 abort、认领不幂等、停止派发与等待移入锁内、停止窗口放宽、关闭不置标志与不唤醒、worker 非守护、启动失败不复位、不检查关闭、不吞回调异常、回收失败也唤醒、中断准备直接派发、中断不派发、可用容量用会话上限二十四种改动均被检查发现（24/24）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.442` / Python `0.2.0rc442`。

## 0.2.0-rc.441 - 2026-11-21

rc.441 源码候选固定待审批分页与计数的共享过滤口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_pending_approvals_where` 是两个读取路径共用的过滤条件，列表另有 `limit + 1` 截断与损坏行跳过，计数不受列表上限影响；现有检查只固定了回读字段。新增 `scripts/check_pending_approvals.py`（72 项）：删除占位 800 上限、三表连接、未裁决与活跃回合、七个类型守卫、六个非空守卫、期限范围与参数绑定、稳定排序、多取一行、截断判定、损坏行跳过、按会话分组计数；反向断言两处读取共用条件、计数无 `LIMIT`、摘要只回显工具名。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3007](https://github.com/can4hou6joeng4/boss-harness/issues/3007)。
- 变异验证：删除占位上限放宽、不再放弃读取、归档 / 回合状态放宽、期限下限与上限放宽、类型与非空守卫缺失、删除会话直接拼 SQL、参数不绑定、列表上限放宽与不校验、截断判定改 `>=`、不多取一行、排序不稳定、损坏行不跳过、截止时间不要求有限、摘要回显摘要值、计数加上限与返回原始值、计数不再共用条件二十二种改动均被检查发现（22/22）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.441` / Python `0.2.0rc441`。

## 0.2.0-rc.440 - 2026-11-21

rc.440 源码候选固定审批参数摘要的规范化与负载一致口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `approval_parameters_digest` 的规范化参数一旦变化，重启前后摘要不一致，已持久化的待审批会被 `_valid_approval_item` 判为无效而消失；现有检查没有固定摘要、负载与索引往返。新增 `scripts/check_approval_digest.py`（45 项）：精确 `dict` 判断、`sort_keys` / `ensure_ascii` / 紧凑分隔符 / `allow_nan` / SHA-256、`_prepare_tool` 七字段负载与同名参数、`start_tool_call` 参数写入、`_index_thread` 持久化与 `pending_approvals` 回读；AST 核对负载键集合与摘要调用，反向断言禁止第二份摘要实现与可选读取。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3005](https://github.com/can4hou6joeng4/boss-harness/issues/3005)。
- 变异验证：类型放宽为 `isinstance`、转义非 ASCII、去掉稳定键序、允许非有限数、分隔符带空格、不捕获递归错误、摘要改用 SHA-1、索引可选读取摘要、索引不转截止时间、回读读错列、参数写入 / 审批参数 / 服务端请求参数改为拷贝、描述回显参数、摘要改用拷贝参数、审批编号改用短 id、`consequential` 放宽、截止时间固定、调用时拷贝参数、负载增加字段、代理自带哈希实现二十一种改动均被检查发现（21/21）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.440` / Python `0.2.0rc440`。

## 0.2.0-rc.439 - 2026-11-21

rc.439 源码候选固定审批条目的展示与状态校验口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_valid_approval_item` 决定一条 `toolCall` 记录能否进入审批索引、`approval/list` 与持久计数；现有 `check_approval.py` 只固定了两个调用点与 `pending_only` 参数，没有固定函数内部边界。新增 `scripts/check_approval_item.py`（49 项）：`kind` / `approval` 对象 / `decision` 枚举 / `approvalId` 与 `turnId` 格式 / 展示字段去空白与 200 字符上限 / `params` 与 `toolArguments` 一致 / `status` 与 `executionState` 随 `decision` 收紧 / 截止时间有限正数 / 描述 1000 字符 / `paramsDigest` 比对；反向断言要求九处拒绝分支、参数与摘要各只比对一次、精确 `dict` 类型判断与全部五处关键字调用。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3003](https://github.com/can4hou6joeng4/boss-harness/issues/3003)。
- 变异验证：非 `toolCall` 放行、`decision` 枚举放宽、`approvalId` 不校验格式、工具名不去空白、展示上限放宽、条目 id 上限取消、工具名一致性取消、`turnId` 不校验、`params` 不一致也放行、待决状态只查 `executionState`、三类裁决终态放宽、截止时间不要求正数、描述上限取消、摘要不比对、调用点改位置参数十七种改动均被检查发现（17/17）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.439` / Python `0.2.0rc439`。

## 0.2.0-rc.438 - 2026-11-21

rc.438 源码候选固定队列计数与列表元数据口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 侧边栏角标与会话列表的「待你处理」来自 `_queue_status_counts` 与 `_index_thread` 写入的 `queueActiveItems` / `queueCounts`；现有检查只固定了调用行与头部字段排除，没有固定归并规则与元数据口径。新增 `scripts/check_queue_counts.py`（20 项）：只读 `queue` 条目、经 `queue_record` 过滤、按 id 覆盖为最新状态、三个计数键、只统计活动状态并累加；元数据由三项求和、非零写入、零值清除。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#3001](https://github.com/can4hou6joeng4/boss-harness/issues/3001)。
- 变异验证：损坏记录也覆盖状态、首个状态优先、计数键遗漏 `paused`、不再过滤活动状态、计数不累加、求和改为条目数、零队列不清除、非零不写入、遍历状态键九种改动均被检查发现（9/9）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.438` / Python `0.2.0rc438`。

## 0.2.0-rc.437 - 2026-11-21

rc.437 源码候选固定条目快照的前缀与重入读取边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `open_entries_snapshot` 与 `SessionEntriesSnapshot` 是冻结快照、单条目读取与导出的读取基础：前缀必须裁到最后一条完整记录、出错关闭文件、已关闭快照拒绝进入与迭代、每次迭代回到开头并按前缀字节上限读取；`check_session_log.py` 只覆盖 `_complete_record_limit`，没有固定快照生命周期。新增 `scripts/check_entries_snapshot.py`（43 项）逐条固定，并用反向断言要求前缀来自 `_complete_record_limit`、关闭错误出现两次、`stamp` 携带三项身份。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2999](https://github.com/can4hou6joeng4/boss-harness/issues/2999)。
- 变异验证：文本模式打开、不裁剪完整记录、出错不关闭、`stamp` 顺序变化、`close` 不关闭、迭代不回到开头、行号不复位、字节上限丢失、迭代 / 进入不检查关闭、不跳过空行、`stamp` 丢失 inode 十二种改动均被检查发现（12/12）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.437` / Python `0.2.0rc437`。

## 0.2.0-rc.436 - 2026-11-21

rc.436 源码候选固定分页游标的编码与范围校验边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_page_cursor` / `_read_page_cursor` 是所有分页读取共用的游标编解码，现有检查只固定了各列表「调用这个函数」，没有固定编解码本身。新增 `scripts/check_page_cursor.py`（26 项）：编码只写 `kind` / `scope` / `key`、`p1_` 前缀与去掉补齐符的 urlsafe base64；解码校验空游标、前缀与 4096 上限、严格 base64、四类异常统一报「游标无效」、字段集合 / `kind` / `scope` / `key` 类型与范围不符报错。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2997](https://github.com/can4hou6joeng4/boss-harness/issues/2997)。
- 变异验证：前缀不再校验、长度上限去掉、base64 改为宽松解码、不捕获递归错误、载荷允许额外字段、`kind` 不校验、`scope` 不校验、`key` 不要求列表、无效游标错误信息拆分、编码丢失 `scope` 十种改动均被检查发现（10/10）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.436` / Python `0.2.0rc436`。

## 0.2.0-rc.435 - 2026-11-21

rc.435 源码候选固定单条目读取的别名与身份冲突边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `read_item` 是模型工具结果与界面详情的单条目读取路径，`revises` 链上的别名需要三项上限保护，身份冲突与失效别名回减决定读取是否可信；`check_model_tools.py` 只覆盖错误映射，没有固定这些边界。新增 `scripts/check_read_item.py`（52 项）：请求编号形状、快照读取、修订目标与旧记录回退、身份冲突、修订记录 / 别名数量 / 别名字节三项上限、只继承 `kind` / `result`、选中冲突条件、别名移除与字节回减、两类错误码。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2995](https://github.com/can4hou6joeng4/boss-harness/issues/2995)。
- 变异验证：编号上限放宽、身份冲突不再拒绝、修订记录上限放宽、别名长度上限去掉、别名数量上限放宽、字节上限去掉、回退不要求已选中、回退不要求工具调用、选择冲突去掉修订目标、失效别名不移除、字节不回减、修订不继承结果、回退改从 `payload` 读 `parentId` 十三种改动均被检查发现（13/13）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.435` / Python `0.2.0rc435`。

## 0.2.0-rc.434 - 2026-11-21

rc.434 源码候选固定条目投影的编号收敛与修订合并。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_project_items` 把日志里的 item 记录合并成逻辑条目，编辑、压缩、分叉、快照与条目读取都按编号定位；`check_snapshot_store.py` 只固定了快照构建里的同类规则，没有固定投影本身。新增 `scripts/check_item_projection.py`（31 项）：空编号跳过、`revises` 目标优先、非 `running` 工具调用回退且父项必须是工具调用、编号字段与非对象审批清理、修订合并保留原编号、重复编号保留先出现、新条目唯一追加路径；反向禁止从 `payload` 读 `parentId`。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2993](https://github.com/can4hou6joeng4/boss-harness/issues/2993)。
- 变异验证：空编号不跳过、修订目标不优先、回退去掉 running 判断、回退不检查父项类型、不清理编号字段、不清理审批、修订覆盖原编号、重复编号不跳过、新条目合并顺序变化、回退改从 `payload` 读 `parentId`、修订不更新别名、修订不合并载荷十二种改动均被检查发现（12/12）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.434` / Python `0.2.0rc434`。

## 0.2.0-rc.433 - 2026-11-21

rc.433 源码候选固定被放弃分支的推导与摘要写入绑定。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 切换分支后，「被放弃分支摘要」必须绑定到刚切走的分支：`abandoned_branch` 以目标祖先链为界回溯旧叶并反转成时间顺序；`append_branch_summary` 只允许在请求摘要的叶记录仍是最后一条、且其后没有新回合或摘要时写入。现有检查覆盖了 `set_leaf` 与 fork，但没有覆盖这两条路径。新增 `scripts/check_branch_summary.py`（42 项）逐条固定目标存在性、祖先链、反转、长度与去空白、反向扫描与 id 绑定、其后条目检查、只追加一次与回调顺序。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2991](https://github.com/can4hou6joeng4/boss-harness/issues/2991)。
- 变异验证：目标不校验、祖先链漏目标、放弃列表不反转、长度上限放宽、允许空白摘要、不核对叶记录 id、不检查切换后条目、摘要不绑定叶记录、回调移到索引之后、共同祖先改用旧叶、摘要类型写成叶记录、正向扫描、摘要追加两次十三种改动均被检查发现（13/13）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.433` / Python `0.2.0rc433`。

## 0.2.0-rc.432 - 2026-11-21

rc.432 源码候选固定分支指针写入的目标校验与幂等规则。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `set_leaf` 是唯一写持久 leaf 记录的入口，之后的分支读取、`fork_thread` 与续接预检都以它选择分支；`check_branch_pagination.py` 与 `check_branch_switch.py` 覆盖桌面读取与提示，没有固定写入路径。新增 `scripts/check_set_leaf.py`（38 项）：回合号标识符校验、锁与索引事务、已在目标位置时幂等返回 `changed: false`、目标取最后一条已结束回合记录、会话无未结束回合 / 未收尾条目 / 未决审批、候选模拟一致性、叶记录 `targetId` / `turnId` / `fromTurnId`、只追加一次并重建索引。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2989](https://github.com/can4hou6joeng4/boss-harness/issues/2989)。
- 变异验证：目标放宽到运行中、未结束回合不再拦截、未收尾条目不再拦截、删除幂等、删除候选一致性、缺 `fromTurnId`、`parentId` 改为回合号、追加两次、目标取首条记录、追加后不重建索引、幂等谎报已变更、去掉标识符校验、缺 `targetId` 十三种改动均被检查发现（13/13）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.432` / Python `0.2.0rc432`。

## 0.2.0-rc.431 - 2026-11-21

rc.431 源码候选固定回合记录 `_turns` 的阶段合并与终态边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_turns` 把条目日志归并成回合表，驱动分支列表、冻结快照、fork 边界切分与列表索引；`check_session_log.py` 只覆盖日志读取，没有固定归并规则：阶段合并的前置条件与范围、恢复原因长度与恢复策略枚举、`firstOrdinal` 取上一条终态序号加一、持久载荷不得覆盖内部记账字段、首条终态记录的 `boundaryOrdinal` / `completedAt` 与「上一条终态序号」推进。新增 `scripts/check_turn_records.py`（41 项）逐条固定，并用缩进扫描要求终态记账位于终态分支内；反向要求公开回合过滤内部字段。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2987](https://github.com/can4hou6joeng4/boss-harness/issues/2987)。
- 变异验证：终态边界被覆盖、完成时间被覆盖、序号推进提前到任意回合、载荷可覆盖内部字段、尝试次数允许为零、阶段归属不要求 `ownerKind`、恢复原因长度放宽、恢复策略丢弃 `closed`、首回合序号改用当前条目序号、内部字段集合丢失 `boundaryOrdinal`、公开回合不过滤、更新时间不推进、终态判定放宽到非运行中十三种改动均被检查发现（13/13）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.431` / Python `0.2.0rc431`。

## 0.2.0-rc.430 - 2026-11-21

rc.430 源码候选固定分支列表的端点推导与分页规则。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `list_branches` 是界面「分支」弹窗的数据来源，`check_branch_pagination.py` 只固定桌面逐页位置一致与重读，没有固定内核端点推导：同一把锁内读取、首个用户消息预览与截断、无子回合端点、`(位置, turnId)` 游标过滤、下一页游标条件、深度与最近分叉点、`containsLeaf` / `isLeaf` 独立判定与仅终态可选。新增 `scripts/check_branch_list.py`（47 项）逐条固定，并反向要求翻页不得用切片截断、预览上限比较与切片各出现一次。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2985](https://github.com/can4hou6joeng4/boss-harness/issues/2985)。
- 变异验证：预览改成最后一条、预览不再截断、翻页过滤改成切片、下一页游标无条件生成、分叉点改用正向扫描、`containsLeaf` 改用 `isLeaf`、可选性放宽到运行中、读取移出锁、游标 scope 变化、游标类型不校验、子回合映射反向、路径不再反转十二种改动均被检查发现（12/12）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.430` / Python `0.2.0rc430`。

## 0.2.0-rc.429 - 2026-11-21

rc.429 源码候选固定条目归属与回合树投影的推导规则。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_item_owners` 与 `_turn_tree` 是分支与历史判定的共同输入，但 rc.427 / rc.428 只固定了 fork 复制与 `_active_entries` 投影本身，没有固定这两个推导函数：修订目标优先、非 `running` 工具调用回退、显式 `turnId` 优先级、重复编号保留首个归属、挂起条目收割、活动回合清空，以及父回合链、自父回合、首次出现顺序与条目尾部。新增 `scripts/check_item_ownership.py`（52 项）逐条固定，并反向要求归属区域只允许回退读取一次 `parentId`、回合树恰好校验一次投影且不读 `parentId`。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2983](https://github.com/can4hou6joeng4/boss-harness/issues/2983)。
- 变异验证：修订目标不再优先、`running` 工具调用也回退、显式 `turnId` 不再优先、重复编号覆盖首个归属、重复回合号也收割挂起、`running` 不设活动归属、终态无条件清空、回合树跳过投影校验、回合树读取 `parentId`、自父回合不置空、非回合条目不推进尾部、叶记录不映射尾部、回退改从 `payload` 读 `parentId` 十三种改动均被检查发现（13/13）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.429` / Python `0.2.0rc429`。

## 0.2.0-rc.428 - 2026-11-21

rc.428 源码候选固定分支投影 `_active_entries` 的条目归属规则。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `_active_entries` 决定所有分支读取、续接预检、fork 与模型回合看到的条目集合，但 rc.427 只固定了 fork 对它的调用次数，投影自身规则没有静态检查：无叶记录原样返回、路径按追加时尾部推导（不信任写入方 `parentId`）、损坏叶指针按缺失处理、重复编号拒绝、迟到修订跟随所属回合、`attachment` / `thread_info` / `queue` 跨分支保留，以及回合 / 阶段 / 工具批次 / 上下文编辑 / 摘要检查点的归属筛选。新增 `scripts/check_branch_projection.py`（26 项）逐条固定这些规则，并反向禁止投影区域读取 `parentId`、要求损坏叶指针走 `continue` 而非 `raise`。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2981](https://github.com/can4hou6joeng4/boss-harness/issues/2981)。
- 变异验证：无叶投影改为复制重排、损坏叶指针改为整段失败、重复编号改为容忍、路径推导改为信任 `parentId`、分支无关集合丢失 `attachment`、摘要检查点不再按归属筛选、迟到修订不再跟随所属回合、阶段归属规则丢失 `task_phase` 八种改动均被检查发现（8/8）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.428` / Python `0.2.0rc428`。

## 0.2.0-rc.427 - 2026-11-21

rc.427 源码候选为会话分叉的复制规则补上固定检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `fork_thread` 是会话正确性的核心路径：只复制当前分支、排除内核专用记录（`thread_info` / `queue` / `task_phase`）、按 owner 归属迟到修订、拒绝拆开工具批次、改写 parentId / threadId / approvalId / `continuationRequestOffset`、重算继承的续接边界摘要，并且只写新会话、不改源日志。rc.422 只固定了边界摘要重算一项，其余规则没有静态检查。新增 `scripts/check_session_fork.py`（35 项）：固定分支选择与前缀裁剪、新会话头的字段排除、复制循环的排除与改写及其顺序，并反向禁止分叉区域调用源日志写入接口、要求两条选择路径各经过一次 `_active_entries`。CI 接入该脚本，技术参考补充说明小节。修复 Issue [#2979](https://github.com/can4hou6joeng4/boss-harness/issues/2979)。
- 变异验证：漏排除 task_phase、不重写 approvalId、不重写 parentId、去掉批次拆分检查、分叉内改写源日志、删除边界重算、合成 leaf 路径不走投影七种改动均被检查发现（7/7）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.427` / Python `0.2.0rc427`。

## 0.2.0-rc.426 - 2026-11-21

rc.426 源码候选固定删除会话时共享附件清理的安全边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 附件按内容摘要寻址，分叉会话与源会话共享同一附件文件；删除会话后的清理必须扫描全部会话引用、只删除不再被引用的对象，并对目录与文件 fail closed。这条路径是安全关键点，但 `check_attachments.py` 只覆盖读取分页与存储配额。现在脚本固定删除路径：引用扫描遍历全部会话、跳过待删除会话、只删除「候选减引用」、空候选提前返回，附件目录 / 会话文件 / 附件文件三处不可信时拒绝，两处单链接检查各出现一次；`_finish_deletion` 必须先移除会话文件再清理附件，顺序颠倒会留下残留。修复 Issue [#2977](https://github.com/can4hou6joeng4/boss-harness/issues/2977)。
- 变异验证：删除集合改成全部候选、跳过引用扫描、放宽单链接检查、调换清理顺序、去掉空候选早退五种改动均被检查发现（5/5）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.426` / Python `0.2.0rc426`。

## 0.2.0-rc.425 - 2026-11-21

rc.425 源码候选对齐 Python classifiers 与 CI 矩阵。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- CI 的 Python 矩阵为 3.10–3.14 并在每个版本上执行搜索归一化与源码编译，但 `harness/pyproject.toml` 的 classifiers 只声明到 3.12，PyPI / wheel 元数据会少报已实测的支持版本。现在补齐 `3.13` 与 `3.14`；`check_versions.py` 从 `.github/workflows/build.yml` 读取 Python 矩阵，要求 classifiers 的 Python 版本集合与矩阵完全一致，任一方向缺失都会失败。修复 Issue [#2975](https://github.com/can4hou6joeng4/boss-harness/issues/2975)。
- 变异验证：删除 3.14 classifier、CI 矩阵新增 3.15、矩阵片段改名三种改动均被检查发现（3/3）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.425` / Python `0.2.0rc425`。

## 0.2.0-rc.424 - 2026-11-21

rc.424 源码候选补全安装指南的导航入口。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SETUP.md` 是面向新用户的「让编码 Agent 协助安装」入口，但 README 的「项目导航」表与 `docs/README.md` 的根文件列表都没有它；`check_docs_links.py` 的索引检查只覆盖 `docs/*.md`，这类根文档入口缺口不会被现有检查发现。现在两个导航都加入 SETUP.md，检查脚本新增根文档导航断言：README 的「项目导航」章节与 `docs/README.md` 必须链接 SETUP.md，导航章节缺失或入口被移除都会失败。修复 Issue [#2973](https://github.com/can4hou6joeng4/boss-harness/issues/2973)。
- 变异验证：移除 README 导航行、移除文档索引链接、改写 README 导航章节标题三种改动均被检查发现（3/3）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.424` / Python `0.2.0rc424`。

## 0.2.0-rc.423 - 2026-11-21

rc.423 源码候选记录旧分叉会话的续接兼容边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- rc.422 只在新建分叉时重算继承的续接边界摘要；之前创建的分叉会话里，摘要仍是源会话原始条目链的值。对这类会话中继承的续接回合再次续接时，预检会以 `CONTINUATION_HISTORY_CHANGED` 拒绝，原因码指向「历史已变化」，用户会误以为会话被篡改。日志 append-only，旧记录不就地迁移，预检也无法把「旧版复制未重算」与「历史真的变化」可靠区分。现在技术参考说明这一口径与处理方式（重新从源会话分叉或新建回合），用户指南的「继续中断回合」补充核对步骤，STATUS「待完成与待验收」记录迁移缺口。修复 Issue [#2971](https://github.com/can4hou6joeng4/boss-harness/issues/2971)。
- 对照探针（离线，不入库）：用 rc.421 源码（`92963cbf` 的 `harness/src`）创建带回合阶段记录与继承边界的会话并 fork，确认旧版保留摘要、分叉前缀重算后不一致；再用 rc.422 源码启动真实内核（`provider=none`）读取预检——源会话停在 `CONTINUATION_SOURCE_UNVERIFIABLE`，旧分叉会话返回 `CONTINUATION_HISTORY_CHANGED`，与文档描述一致。
- `scripts/check_turn_continuation.py` 从 111 项扩展到 114 项，固定技术参考、用户指南与 STATUS 的新片段；32 项逐个还原的变异全部被发现（含此前 29 项回归）。不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.423` / Python `0.2.0rc423`。

## 0.2.0-rc.422 - 2026-11-21

rc.422 源码候选修复中断回合续接的两处边界缺陷。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 分叉会话的续接预检误报历史变化：`fork_thread` 复制当前分支前缀时会丢弃 `thread_info` / `queue` / `task_phase` 并改写审批编号，但继承的 `continuationBoundaryDigest` 原样保留。来源会话的边界摘要绑定原始条目链，分叉前缀的条目集合与编号已不同，预检因此以 `CONTINUATION_HISTORY_CHANGED` 拒绝一个实际未变的历史（离线探针：源摘要 `2e2bcdce32a91ff5` 与分叉前缀 `ad6a9dbae3523c3f` 不一致；真实内核 `provider=none` 探针：来源会话停在 `CONTINUATION_SOURCE_UNVERIFIABLE`，分叉会话却报 `CONTINUATION_HISTORY_CHANGED`）。现在摘要收敛到 `session.continuation_entries_digest` 单点计算，`fork_thread` 在写出新会话前按复制后的前缀重算继承边界；边界条目未被复制时清除摘要，让预检按「持久边界不存在」拒绝而不是误报历史变化。修复 Issue [#2969](https://github.com/can4hou6joeng4/boss-harness/issues/2969)。
- 串行复用主 runner 时历史边界泄漏：嵌入方未提供 provider factory 时 `_runner_for` 复用 `self.runner`，续接回合给 runner 设置的 `history_provider` 会留给下一个普通回合。现在 `_on_turn_start` 在取用 runner 后、设置模型请求上限前调用 `_reset_runner_history`，把历史提供者复位为会话历史。同一 Issue。
- 技术参考补充两段机制说明：幂等回执（`deduplicated: true`）只说明编号已被使用、不携带既有回合状态（既有回合若以 `TURN_START_FAILED` 之类的错误状态落盘，重放仍得到成功形状的回执，应以回合列表中的实际状态为准）；分叉重算与串行复位的边界。UPSTREAM 记录核对 Pi 固定 commit 的分叉文档复制语义与本项目条目链摘要的差异。
- `scripts/check_turn_continuation.py` 从 86 项扩展到 111 项：摘要单点计算与委托、`fork_thread` 在复制循环之后且 `_write_new` 之前重算一次继承边界、边界缺失清除摘要、复位方法与会话历史的绑定、`_on_turn_start` 的调用位置与次数，以及文档新段落；29 项逐个还原的变异全部被发现（含 rc.419 的 18 项回归）。
- 对照探针（离线，不入库）：分叉摘要探针在修复前后分别得到上述不一致 / 一致结论；真实内核 `provider=none` 探针确认修复后分叉与来源会话停在同一个预检阶段；独立构造 `ApplicationService` 与 fake runner 验证复位方法与调用位置。未在真实窗口中验证界面，未调用真实模型、招聘平台或招聘 CLI。版本推进到 npm `0.2.0-rc.422` / Python `0.2.0rc422`。

## 0.2.0-rc.421 - 2026-11-21

rc.421 源码候选让 README 英文概览与中文文档的已具备能力口径一致。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 的 English overview 在 Execution 条目里只写了 branch-aware session state，没有写 rc.419 新增文档的中断回合续接；Safety boundary 也没有写业务 CLI 的浏览器来源可按进程覆盖（`BOSS_HARNESS_BROWSER_SOURCE`，STATUS 已具备里已有）。现在 Execution 补充 explicit turn continuation behind a read-only precheck（已完成的工具不重跑、新写操作仍需逐次审批），Safety boundary 补充浏览器来源覆盖与「模型和工作台渲染进程都拿不到平台 Cookie」的同一句边界。修复 Issue [#2967](https://github.com/can4hou6joeng4/boss-harness/issues/2967)。
- 不改变内核、桌面与协议行为；五项本地门禁通过。版本推进到 npm `0.2.0-rc.421` / Python `0.2.0rc421`。

## 0.2.0-rc.420 - 2026-11-21

rc.420 源码候选把会话内分支与中断回合续接补进 README 能力地图。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 的「能力地图」没有会话内分支与中断回合续接条目：分支只作为「长会话可追溯」一行的附带描述，续接完全不可见，首页无法看出这两条与长会话直接相关的路径。现在能力地图新增「换一条路继续会话」：分支可切回任意已结束回合、被放弃分支摘要默认关闭、中断回合经只读预检后续接、已完成工具不重跑、新写操作仍逐次审批。`docs/STATUS.md` 的「已具备 → 会话」条目同步补充分支摘要、按当前分支的末回合状态与中断回合续接。修复 Issue [#2965](https://github.com/can4hou6joeng4/boss-harness/issues/2965)。
- 不改变内核、桌面与协议行为；文档链接与五项本地门禁通过。版本推进到 npm `0.2.0-rc.420` / Python `0.2.0rc420`。

## 0.2.0-rc.419 - 2026-11-21

rc.419 源码候选补上中断回合续接的用户说明、完整原因码表与固定检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 「继续中断回合」（`turn/continuation/read` 预检与 `turn/continue`）是桌面已有能力，但用户指南与桌面指南没有说明：何时出现「此回合已中断」、预检核对什么、续接会不会重新执行旧工具、被拒绝时原因码是什么意思。用户看到原因码只能猜测是否安全。现在用户指南新增「继续中断回合」一节并列入快速导航，桌面指南补充对应条目：预检只读、检查点落在用户输入或已完成的工具批次之前、续接沿用来源回合的模型 / 技能 / 附件 / 工具策略并抛出新请求、已完成工具不重跑、新写操作仍逐次审批、`none` 线路与归档会话等拒绝条件，以及回执未知时不自动重发。技术参考新增机制说明与 28 个原因码表，并固定按当前分支判定最新回合与已有续接：放弃续接回合所在分支、切回来源回合后可以再次续接（会再发起一次模型请求），`continuationId` 去重仍按整份日志判定。修复 Issue [#2961](https://github.com/can4hou6joeng4/boss-harness/issues/2961)。
- 新增 `scripts/check_turn_continuation.py`（86 项）：原因码集合与技术参考表格双向一致；运行状态门禁顺序、按当前分支读取、最新回合与已有续接判定、`turn/continue` 的整份日志去重与 `CONTINUATION_ID_CONFLICT`、只读回执字段、桌面入口条件（当前分支中断回合、`explicitTurnContinuation`、未归档）、回执形状校验与按钮禁用（提交中、回执未知、运行中）；18 项逐个还原的变异全部被发现。CI 接入该脚本。
- 对照探针（离线，不入库）：以 `provider=none` 启动真实内核进程，经 stdio 读取预检与续接回执。叶在 t1 时读取 t2 得到 `CONTINUATION_NOT_LATEST`，新编号续接被同一原因码拒绝，而相同来源与编号按幂等返回被放弃分支上的 t3（`deduplicated: true`）；切回 t2 后 t3 不再阻止预检，新编号能走到后续检查（合成回合没有持久请求边界，按既有规则以 `CONTINUATION_BOUNDARY_INVALID` 结束）；编号不变而来源改为 t1 返回 `CONTINUATION_ID_CONFLICT`；叶移到 t3 后 t2 再次不是最新回合。完整可续接回合的端到端路径沿用此前占位模型流探针的结论，本次未重跑；界面渲染未在真实窗口中验证。同步用户指南、桌面指南与技术参考。版本推进到 npm `0.2.0-rc.419` / Python `0.2.0rc419`。

## 0.2.0-rc.418 - 2026-11-21

rc.418 源码候选让跨会话搜索的跨分支命中可见、可解释。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 跨会话搜索在完整日志上检索，会话区在支持分支时读取当前分支视图。被放弃分支上的消息出现在结果里，点击后会话区找不到目标条目，只在下一次消息变化后静默放弃定位：界面看起来「什么都没发生」，也没有说明要先切回该分支。现在内核为含位置记录的会话在命中上给出 `onBranch`（是否在当前位置的分支上；分支无法投影时省略字段，搜索结果照常返回），搜索弹窗对 `onBranch === false` 的命中标注「其他分支」，并把该事实随打开动作传给会话区；会话区在历史未读尽时继续等待定位，列表就绪仍找不到才显示可关闭的说明（已确认在其他分支 / 可能在其他分支或尚未载入），不再静默放弃。修复 Issue [#2962](https://github.com/can4hou6joeng4/boss-harness/issues/2962)。
- `check_thread_search_result.py` 从 45 项扩展到 81 项：内核按当前位置投影并逐条标记、投影失败时省略字段、客户端只接受显式布尔、标签只在确认其他分支时显示、事实传递与会话区说明的等待 / 放弃条件；15 项逐个还原的变异全部被发现。对照探针（离线，不入库）：同一份源码在独立临时目录建立未分支、叶在 t1（放弃 t2）、叶在会话开头与条目编号重复四种会话——旧版所有命中都不带字段，修改版按位置给出 `onBranch`，叶在会话开头时全部为 false，编号重复时省略字段且搜索不失败；桌面端用真实校验模块跑 6 种字段形态，旧版丢掉字段，修改版保留布尔并整体拒绝字符串 / null / 数字。搜索弹窗标签与会话区说明的渲染未在真实窗口中验证。
- 同步技术参考、桌面指南与上游记录。版本推进到 npm `0.2.0-rc.418` / Python `0.2.0rc418`。

## 0.2.0-rc.417 - 2026-11-21

rc.417 源码候选让升级前已切换过分支位置的会话在首次启动时带上当前分支末回合。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 会话索引只在会话文件的大小或修改时间变化后重建。rc.416 为切换过位置的会话追加了 `branchLastTurn`，但升级前已经切换过位置的会话文件没有变化，索引里仍是旧投影：升级后会话列表与日志视图都不带这个字段，侧栏状态、失败标记与继续目标继续按日志末回合计算，直到这条会话下一次写入。现在内核在 `checkpoints` 表记录投影内容版本，启动时比对一次：版本缺失或不同就让含位置记录的会话失效，由随后的刷新按现有流程重建。未切换过位置的会话不重建；索引结构版本不变，旧版本仍能打开同一状态目录；日志暂时读不出的会话保持失效，可读后补上；重建中途退出时下次启动继续。修复 Issue [#2959](https://github.com/can4hou6joeng4/boss-harness/issues/2959)。
- 挑选会话时按字节查找位置记录的类型标记，不解析日志：200 个会话、39 MiB 日志的本机实测，全部未切换过位置时升级启动中位数 0.07 秒（平时 0.03 秒），全部切换过位置时 0.46 秒，只发生一次。工具数据里出现同样片段的会话会多重建一次，结果不变。
- `check_persistence.py` 从 51 项扩展到 88 项：版本记录的读取与写回、失效范围限定到具体会话、读取失败与文件丢失的分支、字节扫描的两种写法与跨块尾部、启动顺序、失效只在构造时调用一次、版本不并入索引结构迁移；15 项逐个还原的变异全部被发现。对照探针用 rc.415 源码建立索引，再分别由 rc.416 与修改版打开同一状态目录（每步一个进程）：rc.416 不重建、字段缺失；修改版首次打开即带上字段且只重建命中的会话，第二次打开不再扫描，原位损坏的日志修复后补上，rc.415 仍能打开，版本记录被改成旧值或无效值时重做一次，刷新前退出后下次继续，全新目录只写版本记录。另以 `provider=none` 启动真实内核进程经 stdio 读取 `thread/list` 与 `thread/read` 确认；字节扫描 20 个边界用例通过。剩余限制：升级后又降级到不带该字段的版本并写入过已分支会话，再升级时该会话要到下一次写入才重新带上字段（探针已复现），缺省时桌面端按 `lastTurn` 处理。同步技术参考、桌面指南、协议注释与上游记录。版本推进到 npm `0.2.0-rc.417` / Python `0.2.0rc417`。

## 0.2.0-rc.416 - 2026-11-21

rc.416 源码候选让会话摘要按当前分支的末回合报告状态。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 会话列表里的 `lastTurn` 是日志中最后写入的回合。会话切换过分支位置后，这个回合可能属于已放弃的分支，而侧栏状态、「上次回合未完成」标记与会话区的继续提示都取自它：切离被中断的回合后侧栏仍显示「已中断」并对那个回合发起继续检查；从更早的位置开出新分支再切回被中断的回合，侧栏显示空闲，也不再检查这个回合能否继续。现在内核为切换过位置的会话另报 `branchLastTurn`（当前分支末回合，位于会话开头时为 `null`），`lastTurn` 保持不变，未感知分支的客户端行为不变。该字段只由本会话条目推导：会话头或会话信息记录带来的同名值被清掉，分支无法投影时不写字段也不影响列表，分叉出的会话不继承；分支视图读取中两个字段取自同一次读取。桌面端有该字段时按它计算状态、失败标记与继续目标，并按与 `lastTurn` 相同的规则校验；收到位置变化通知后刷新会话列表并重做继续检查。索引只在会话文件变化后重建，升级前已切换过位置的会话要到下一次写入后才带上该字段。修复 Issue [#2957](https://github.com/can4hou6joeng4/boss-harness/issues/2957)。
- `check_thread_list.py` 从 45 项扩展到 92 项：末回合校验函数恰好用于两个字段、两处摘要映射都经 `summaryTurnOf` 且不得直接读取任一字段、位置变化通知刷新列表、协议类型、内核索引的推导顺序与分叉排除、分支视图辅助函数的两处调用；12 项逐个还原的变异全部被发现。`check_branch_pagination.py` 随分支视图写法调整为 124 项。从 rc.415 提交导出真实源码与修改版执行同一组探针：真实会话存储上逐步切换位置（未分支、切走、新分支、切回、回到开头、分叉）；外部改写会话头与会话信息记录伪造该字段（旧版原样透出伪造值，修改版清除或按位置重算）；以 `provider=none` 启动真实内核进程经 stdio 读取 `thread/list`、`thread/read` 的日志 / 分支 / 冻结快照视图；桌面端用真实列表校验、列表映射函数体与通知语句跑 12 个摘要场景（未分支、字段缺省与运行中两边一致，4 种畸形字段修改版整体拒绝）。继续提示只验证到「对哪个回合发起检查」：探针里的中断回合没有工具边界，内核按既有规则回报不可继续，未覆盖可继续回合的完整流程；侧栏与提示渲染未在真实窗口中验证。同步技术参考、桌面指南与上游记录。版本推进到 npm `0.2.0-rc.416` / Python `0.2.0rc416`。

## 0.2.0-rc.415 - 2026-11-21

rc.415 源码候选让切换分支位置后的整理计划失效。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 「会话上下文」面板的整理计划按会话保存，面板关闭后仍在；面板在回合开始 / 结束、会话更新与压缩完成时清除计划，但不处理 `thread/leafChanged`。切换分支位置后再打开面板，预算会重读，切换前的计划却原样显示；计划请求在途时发生切换，回执也照常写入。在同一条分支上回退到计划截止回合之后的位置时，截止回合与来源摘要不变，内核会接受这份计划并开始压缩，界面展示的保留范围与估算却是旧位置的。现在目标会话的 `thread/leafChanged` 清除计划、结束计划读取态并作废在途的计划请求，面板打开时重读预算；回合运行标记不变，其他会话的通知不影响本会话。压缩范围本身一直由内核按截止回合与来源摘要校验，这次修正的是展示与过期计划的可用性。修复 Issue [#2955](https://github.com/can4hou6joeng4/boss-harness/issues/2955)。
- `check_branch_pagination.py` 扩展到 123 项：整理计划失效清单的内容、只定义与使用各一次、缺少位置变化的旧清单不再出现、计划请求按修订号作废，以及内核位置切换通知保持唯一。从 rc.414 提交导出真实通知回调与修改版执行同一探针（11 个场景）：位置切换后旧版保留计划且不重读、在途请求未作废，修改版清除计划、推进修订号并在面板打开时重读；面板关闭时只清除不读取；回合运行标记不变；原有四种通知与无关通知两边行为相同。另用真实内核确认：6 个回合、计划截止第 2 回合，回退到第 3 回合后保留条目从 8 变为 2、估算保留 token 从 1752 变为 438，来源摘要不变且旧计划通过来源校验。面板渲染未在真实窗口中验证。同步技术参考与桌面指南。版本推进到 npm `0.2.0-rc.415` / Python `0.2.0rc415`。

## 0.2.0-rc.414 - 2026-11-21

rc.414 源码候选让分支列表在回合开始时重读。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 回合开始时内核先写入运行中的回合、再发出 `turn/started`：当前位置已是新回合，分支端点也换成这个未结束的回合。分支读取只在 `thread/leafChanged`、`turn/completed`、`thread/updated`、`context/compacted` 时重读，漏了 `turn/started`；弹窗打开期间有回合开始（排队消息自动投递、继续中断的回合，或固定在非活动会话时该会话开始运行）时，整个回合运行期间仍把上一个回合标成「当前位置」，端点列表也停在开始前。现在目标会话的 `turn/started` 同样触发一次重读，其他会话的不触发；每次回合开始多一轮分支读取。运行期间切换仍被界面阻断、内核也会拒绝，这次只修正展示。修复 Issue [#2953](https://github.com/can4hou6joeng4/boss-harness/issues/2953)。
- `check_branch_pagination.py` 扩展到 116 项：重读触发清单的内容、只定义与使用各一次、缺少回合开始的旧清单不再出现，以及内核两处回合开始通知都晚于运行中回合的写入。从 rc.413 提交导出真实通知回调与修改版执行同一探针（15 个场景）：目标会话回合开始时旧版不重读、修改版重读一次；其他会话、内核不支持分支、缺少会话标识、无关通知与删除通知两边都不重读，原有四种通知两边行为相同。另用真实会话存储确认回合记录为运行中后当前位置、分支回合页与端点都已指向新回合。弹窗渲染未在真实窗口中验证。同步技术参考与桌面指南。版本推进到 npm `0.2.0-rc.414` / Python `0.2.0rc414`。

## 0.2.0-rc.413 - 2026-11-21

rc.413 源码候选让分支读取在位置变化后自行重读一次，并标注读取失败时仍在展示的旧列表。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 分支端点与当前分支回合逐页核对位置（rc.409）后，发现不一致只提示「已放弃；请刷新后重试」。位置变化通常是一次性的（切换了分支或开始了新回合），紧接着重读就能得到一致的列表；活动会话会被 `thread/leafChanged` 触发重读，固定在非活动会话的分支弹窗没有这条路径，一次变化就停在错误上。现在两处核对（逐页比较与旧内核的端点复核）只上报结果，由一处决定：只读重读一遍，一致就照常展示，仍不一致才提示「已重读一次……请稍后刷新」。重读只有一次，不循环、不延时；过期判定不变，重读期间被更新的刷新或断连取代时不写入也不报错。位置稳定时请求数不变。
- 读取失败（位置变化或其他读取错误）只更新错误提示，上次成功读取的端点、回合与「当前位置」标记仍留在弹窗里、按钮可点，界面没有说明它们是旧结果。现在已成功读取过的弹窗在错误提示下方注明：下方仍是上次成功读取的列表，当前位置标记与可切换目标可能已变化，刷新成功后再据此操作。切换仍由内核按目标回合校验，摘要与轮询行为不变。修复 Issue [#2951](https://github.com/can4hou6joeng4/boss-harness/issues/2951)。
- `check_branch_pagination.py` 扩展到 110 项：读取函数恰好调用两次且第二次只在第一次不一致时发生、之间没有循环与延时、过期退出先于提示、提示只有一处，以及弹窗旧列表提示的位置与条件。从 rc.412 提交导出真实 hook 源码与修改版执行同一探针（6 个场景）：一次性变化时旧版报错、修改版多读一遍后展示一致列表；持续变化时修改版重读一次后报错并保留旧列表；旧内核翻页复核发现变化同样重读一次；重读被取代时不写入；位置稳定的单页与多页读取两边结果与请求数相同。弹窗提示是 JSX，仅由静态检查覆盖，未在真实窗口中验证。同步技术参考与桌面指南。版本推进到 npm `0.2.0-rc.413` / Python `0.2.0rc413`。

## 0.2.0-rc.412 - 2026-11-20

rc.412 源码候选避免「当前分支」用量翻页期间混用两条分支。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 「会话用量」的「当前分支」视图按页读取 `thread/usage/read`，内核每次请求都按当下的位置重新计算当前分支的回合；合计与摘要任务取自第一页，回合总数取自最后一页。翻页期间位置变化时，后面的页来自另一条分支；两条分支有用量记录的回合数相同时既不重复、条目数也与声明一致，现有校验发现不了，弹窗与「复制 CSV」给出第一条分支的合计和由两条分支拼成的明细。内核在分支视图的每一页都返回与该页同源的 `branch`，桌面端此前没有读取。现在逐页记录 `branch.leafTurnId`，读完先比较位置，不一致就放弃本次结果并提示刷新；`branch` 归属其他会话或形状无法识别时按响应无效处理。不增加请求；「全部记录」视图不读取位置，旧内核不返回 `branch` 时行为不变。修复 Issue [#2949](https://github.com/can4hou6joeng4/boss-harness/issues/2949)。
- `check_branch_pagination.py` 扩展到 86 项：用量逐页记录与比较、位置只在分支视图读取一次、比较先于条目校验、不增加请求，以及内核用量页的位置与回合同源。从 rc.411 提交导出真实 hook 源码与修改版执行同一探针（7 个场景）：翻页期间位置变化时旧版返回混用的明细与旧合计，修改版放弃并提示；位置稳定、单页、空会话、旧内核与「全部记录」视图两边结果逐项相同，请求数不变。同步技术参考与桌面指南。版本推进到 npm `0.2.0-rc.412` / Python `0.2.0rc412`。

## 0.2.0-rc.411 - 2026-11-20

rc.411 源码候选让 `thread/read` 分支视图的各项出自同一份条目快照。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `thread/read` / `thread/resume` 的非快照分支视图在一次响应里读取四次会话：条目快照生成 `items`，随后 `branch_last_turn`、`list_branch_turns` 与 `read_leaf` 各自重新读取条目，分别生成 `thread.lastTurn`、`turns` 与 `branch`。处理器只持有事件锁，位置切换与回合写入不经过它：期间位置变化时，同一响应里的消息属于旧分支，末回合、回合列表与位置却属于新分支。现在这三个读取接受调用方已读到的条目快照，处理器把同一份快照传给它们；`excludeTurns` 时 `branch` 与 `lastTurn` 同样与 `items` 同源。每次分支视图读取少解码或投影三遍会话条目。日志视图、冻结快照、`thread/turns/list` 与 `thread/leaf/read` 不变，协议字段不增不减。修复 Issue [#2947](https://github.com/can4hou6joeng4/boss-harness/issues/2947)，rc.410 记录的未处理项随之关闭。
- 边界：回合的成员与位置取自快照，回合元数据（状态、时间）仍取自投影索引，可能比快照新；这与其他按时间点读取的接口一致。
- `check_branch_pagination.py` 扩展到 67 项：三个读取的快照参数、带快照时不重新读取条目、处理器内四项的同源步骤与顺序，以及不带快照的旧调用不再出现。从 rc.410 提交导出真实内核源码与修改版执行同一探针：在条目快照返回后插入一次位置切换，旧版响应的消息为旧分支而末回合、回合与位置为新分支（含 `excludeTurns`），修改版四项一致；位置稳定与日志视图两边逐项相同。同步技术参考与上游吸收记录。版本推进到 npm `0.2.0-rc.411` / Python `0.2.0rc411`。

## 0.2.0-rc.410 - 2026-11-20

rc.410 源码候选让分支视图回合页的 `turns` 与 `branch` 出自同一次读取。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `thread/turns/list` 带 `view=branch` 时，内核先在 `list_branch_turns` 里加锁读取条目、算出当前分支回合并取页，释放锁后再调用 `read_leaf` 重新读取条目计算 `branch`。两次读取之间发生 `thread/leaf/set` 或写入新回合时，同一响应里的 `turns` 属于旧位置，`branch.leafTurnId` 却是新位置；rc.409 起桌面端按每页的 `branch` 判断读取期间位置是否变化，会因此漏判或误判。现在 `list_branch_turns` 在同一次持锁读取里用同一份条目算出回合集合与 `branch`，处理器直接返回它；每次分支视图翻页少读一遍会话条目。`branch` 的字段与 `thread/leaf/read` 相同，游标、排序、页大小、索引重建重试、日志视图与 `thread/read` 的分支回合不变，协议字段不增不减。修复 Issue [#2945](https://github.com/can4hou6joeng4/boss-harness/issues/2945)，rc.409 记录的同页不一致边界随之消除。
- 未处理：`thread/read` 的分支视图仍分别读取条目快照、分支回合与 `branch`，同类不一致仍可能出现在该响应内。
- `check_branch_pagination.py` 扩展到 50 项：内核回合集合与位置同源、持锁步骤顺序、只读取一次条目且不调用 `read_leaf`，以及处理器按字段返回、不另行读取位置。从 rc.409 提交导出真实内核源码与修改版执行同一探针：在回合读取返回后插入一次位置切换，旧版响应的回合为旧位置而 `branch` 为新位置，修改版两者一致；位置稳定、翻页游标、日志视图与 `thread/read` 的分支回合两边逐项相同。同步技术参考与上游吸收记录。版本推进到 npm `0.2.0-rc.410` / Python `0.2.0rc410`。

## 0.2.0-rc.409 - 2026-11-20

rc.409 源码候选逐页核对分支读取时的当前位置。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- rc.408 只在翻页时用端点复核一次，仍有两处缺口：端点与回合即使各只有一页也是两次请求，期间位置变化时面板用旧位置标注、却展示按新位置计算的回合；多页读取期间切走又切回时首尾位置相同，复核通过。内核的分支视图回合页本就带有 `branch`、端点页带有 `leafTurnId`，桌面端此前只取端点第一页。现在按请求顺序记录每一页报告的位置，全部一致才写入状态；不一致就放弃并提示「当前位置已改变（切换了分支或开始了新回合）」。单页读取同样生效，回合页带位置时不再额外请求端点（多页读取比 rc.408 少一次请求）；旧内核回合页缺少位置时保留翻页后的端点复核。`branch` 归属其他会话或形状无法识别时按响应无效处理。修复 Issue [#2943](https://github.com/can4hou6joeng4/boss-harness/issues/2943)。
- 已知边界：内核处理单次 `thread/turns/list` 时，回合集合与响应里的 `branch` 分两次加锁读取，两者之间的位置变化仍可能让同一页的回合与报告位置不一致；旧内核的切走又切回同样无法识别。
- `check_branch_pagination.py` 扩展到 35 项：逐页记录与比较、位置解析的三种结果、回退复核的触发条件与唯一位置、步骤顺序、发现变化后立即返回，以及反向断言只在翻页时复核的旧实现不再出现。从 rc.408 提交导出真实源码与修改版执行同一探针（8 个场景）：单页位置变化与多页切走切回两种情况旧版写入不一致列表，修改版放弃并提示；位置稳定、空会话与旧内核单页两边结果一致；旧内核多页漂移两边都经端点复核放弃。同步技术参考与桌面指南。版本推进到 npm `0.2.0-rc.409` / Python `0.2.0rc409`。

## 0.2.0-rc.408 - 2026-11-20

rc.408 源码候选避免分支列表翻页期间混用两条分支。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 分支端点与当前分支回合分多次读取，内核每次请求都按当下的 leaf 重新计算「当前分支回合」：翻页期间位置被切换时，后一页来自另一条分支，拼接后既不会出现重复回合，也不会被现有查重发现。现在 `readPagedItems` 回报实际请求页数，分支面板在任一侧多于 1 页时用端点复核当前位置；与首次端点的 `leafTurnId` 不一致就放弃本次结果，提示「分支在读取期间发生变化……请刷新后重试」，不再读取摘要或写入旧 leaf 与端点。单页读取不增加请求。复核只比较读取前后的位置：期间切走又切回原位置的情况仍无法识别。修复 Issue [#2941](https://github.com/can4hou6joeng4/boss-harness/issues/2941)。
- 新增 `check_branch_pagination.py`（14 项）：固定页数统计的返回值、位置复核触发条件与放弃文案，以及复核位于两段列表拼接之后、摘要读取之前，放弃后不再写入状态。接入 CI 与技术参考。从 rc.407 提交导出真实 `pagedRead` 与 hook 源码，与修改版执行同一探针：翻页期间位置由一条分支切到另一条时，旧版写入由两条分支拼成的回合列表并保留旧 leaf，修改版放弃结果并给出提示；位置未变与单页读取两边结果一致，单页读取请求数不变。同步桌面指南。版本推进到 npm `0.2.0-rc.408` / Python `0.2.0rc408`。

## 0.2.0-rc.407 - 2026-11-20

rc.407 源码候选区分「分支已切换」与「切换结果未确认」。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `switchTo` 在提交 `thread/leaf/set` 之前就置 `attempted`，并把重新读取会话放在同一个 `try` 里：内核已确认切换、重读却失败时，提示仍是「切换结果尚未确认……不会自动重试」，旧代码还会在 catch 里再调用一次重读并把异常抛出。现在重读有独立的就近 `catch`，只提示「分支已切换，但重新读取会话失败……分支位置以内核为准」，返回失败但不再重试或抛出；未提交、明确拒绝与回执未知三类文案不变。修复 Issue [#2939](https://github.com/can4hou6joeng4/boss-harness/issues/2939)。
- 新增 `check_branch_switch.py`（19 项）：固定队列核对 → 提交标记 → 回执校验 → 重读的顺序、已确认重读失败的专用文案，以及三类失败文案的分支关系与未确认文案的范围。接入 CI 与技术参考。从 rc.406 提交导出真实 hook 源码与修改版执行同一探针：旧版重读失败时向上抛出并提示未确认，修改版只提示分支已切换，其余场景两边一致。同步桌面指南。版本推进到 npm `0.2.0-rc.407` / Python `0.2.0rc407`。

## 0.2.0-rc.406 - 2026-11-20

rc.406 源码候选在发送被明确拒绝时写回自动压缩覆盖。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `take` 在请求发出前移除该会话的已应用覆盖并复位表单。直接发送被内核明确拒绝时回合没有启动，覆盖却不会写回；排队发送的 `queueFollowUp` 抛出时同样已消耗。用户设置的触发阈值与保留目标因此在一次失败后消失，表单已复位，提示只讲发送失败。现在直接发送在明确拒绝分支恢复本次取出的覆盖；排队发送只在明确拒绝时恢复一次后继续抛出原错误。恢复只对取出时的同一份覆盖生效：期间重新应用、清除或再次取用都不恢复，避免旧回执覆盖新设置；回执未知与成功仍保持已消耗。修复 Issue [#2937](https://github.com/can4hou6joeng4/boss-harness/issues/2937)。
- 新增 `check_compaction_override.py`（25 项）：固定取出先登记后移除、恢复只写覆盖与表单、恢复的范围守卫，以及直接发送「取出 → 发送 → 判定拒绝 → 恢复」的顺序、排队发送仅明确拒绝恢复一次并继续抛出。接入 CI 与技术参考。从 rc.405 提交导出真实 hook 源码与修改版执行同一探针：旧版 6 项中 5 项失败（缺少恢复函数与各恢复条件），修改版 6 项全部通过。同步桌面指南。版本推进到 npm `0.2.0-rc.406` / Python `0.2.0rc406`。

## 0.2.0-rc.405 - 2026-11-20

rc.405 源码候选修正删除通知字段，让删除时的 hook 状态遗忘真正生效。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 内核 `thread/deleted` 通知的参数是 `deletedThreadId`、`eventId` 与 `eventCursor`（恢复标记冲突时明确拒绝带 `threadId` 的记录），协议也只声明 `deletedThreadId`；rc.401–rc.404 新增的上下文面板、分支、推理档位与自动压缩草稿删除处理都读 `params.threadId`，取不到即返回，遗忘逻辑从未执行。因此那几版描述的清理在上次修正前仍是空操作：两个 hook 的 1.5 秒 / 2 秒轮询会继续读取已删除会话，推理档位与压缩草稿也不会释放。现在四个 hook 都只读 `deletedThreadId`，与主界面和 replay 侧一致；推理档位的删除分支移到通用 id 提取之前，避免再次不可达。修复 Issue [#2935](https://github.com/can4hou6joeng4/boss-harness/issues/2935)。
- `check_deleted_thread_state.py` 增至 125 项，固定四个 hook 读取 `deletedThreadId`，并附反向断言禁止删除分支读取通用 `threadId`。从 rc.404 提交导出真实 hook 源码与修改版按真实通知形状执行同一探针：旧版 8 项中 7 项失败（四个 hook 都未触发遗忘，自动压缩还接受了通用 `threadId`），修改版 8 项全部通过。同步技术参考。版本推进到 npm `0.2.0-rc.405` / Python `0.2.0rc405`。

## 0.2.0-rc.404 - 2026-11-20

rc.404 源码候选让删除后迟到的分支切换回执失效。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- rc.401 起分支弹窗会随 `thread/deleted` 遗忘会话，但 `switchTo` 的回执归属判定只比较连接代际：删除途中发出的 `thread/leaf/set` 回执返回后仍会调用 `onSwitched`，重新读取一个已删除的会话，失败原因还可能以提示形式出现。现在切换入口与回执判定都要求会话未被遗忘，已删除会话不再发起切换，迟到的回执不重读、不写状态、不刷新，也不关闭窗口；其他会话的切换行为不变。修复 Issue [#2933](https://github.com/can4hou6joeng4/boss-harness/issues/2933)。
- `check_deleted_thread_state.py` 增至 122 项，固定切换入口的遗忘拦截、回执判定包含遗忘检查，以及调用 `onSwitched` 之前必须先过归属判定。从 rc.403 提交导出真实 hook 源码与修改版执行同一探针：旧版 6 项中 2 项失败（已删除会话的回执仍被当作有效、入口未拦截），修改版 6 项全部通过。同步桌面指南与技术参考。版本推进到 npm `0.2.0-rc.404` / Python `0.2.0rc404`。

## 0.2.0-rc.403 - 2026-11-20

rc.403 源码候选让自动压缩草稿与覆盖随删除遗忘。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `useAutoCompaction` 按会话保存未应用草稿、已应用但未发送的覆盖与手动改动标记，都不处理 `thread/deleted`：删除会话后这些条目保留到应用退出；删除回执未确认时列表按约定保留条目，重新打开该会话会看到删除前的草稿或覆盖，像是仍然有效的设置，实际发送只会失败。现在删除通知移除该会话的三项记录，删除的正是当前会话时表单回到默认占位值并清除旧错误，同时作废在途默认值读取；覆盖先复制再删除，其他会话不受影响。修复 Issue [#2931](https://github.com/can4hou6joeng4/boss-harness/issues/2931)。
- `check_deleted_thread_state.py` 增至 119 项，固定删除通知的字段校验、三项记录的移除、当前会话的表单复位与覆盖的复制后删除。从 rc.402 提交导出真实 hook 源码与修改版执行同一探针：旧版 5 项全部失败（没有删除通知处理），修改版 5 项全部通过。同步桌面指南与技术参考。版本推进到 npm `0.2.0-rc.403` / Python `0.2.0rc403`。

## 0.2.0-rc.402 - 2026-11-20

rc.402 源码候选让推理档位状态随删除遗忘。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `useSessionReasoning` 按会话保存推理档位的读取结果、在途保存锁与失败原因，但不处理 `thread/deleted`：被删除会话的条目一直留在应用生命周期内，删除时在途的 `thread/reasoning/read` 与 `thread/reasoning/set` 回执返回后仍会写回。现在收到删除通知即移除该会话的状态并递增读取版本，读取归属判定与回执写回都要求会话未被遗忘，删除后不再发起读取；其他会话的读取、保存与提示不变。断连时与其他连接内记录一起重置。修复 Issue [#2929](https://github.com/can4hou6joeng4/boss-harness/issues/2929)。
- `check_deleted_thread_state.py` 增至 108 项，固定删除通知先于方法白名单、遗忘不经 `update`、读取归属包含遗忘判定与保存回执的核对。从 rc.401 提交导出真实 hook 源码与修改版执行同一探针：旧版 10 项中 2 项失败（缺少遗忘回调、迟到回执重建状态），修改版 10 项全部通过。同步桌面指南与技术参考。版本推进到 npm `0.2.0-rc.402` / Python `0.2.0rc402`。

## 0.2.0-rc.401 - 2026-11-20

rc.401 源码候选让上下文面板与分支弹窗在删除会话后停止轮询。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 两个 hook 都不处理 `thread/deleted`：被删除会话若停在「开始压缩回执未知」「lifecycleActive 为真」或「摘要任务 running」，1.5 秒与 2 秒的定时器会一直对已不存在的会话读取，删除时在途的计划、开始、取消与切换回执返回后还会把状态写回。现在收到删除通知即记录该会话 id 并移除它的面板状态，`update` 与 `refresh` 对已删除会话不再写状态或发起读取，迟到的回执无法重建状态或重新开始轮询；分支弹窗固定目标被删除时一并解除固定，其他会话不受影响。断连重连时按连接内记录重置。修复 Issue [#2927](https://github.com/can4hou6joeng4/boss-harness/issues/2927)。
- 新增 `deletedThreadState.ts` 的 `withoutThread`；`check_deleted_thread_state.py` 增至 94 项，固定两个 hook 的删除分支先于通用会话分支处理并直接返回、遗忘不经 `update`、定时器仍只遍历状态表。从 rc.400 提交导出真实 hook 源码与修改版执行同一探针：旧版 8 项全部失败（模块与遗忘回调缺席、迟到回执重建状态、轮询仍读取被删除会话），修改版 8 项全部通过。同步桌面指南与技术参考。版本推进到 npm `0.2.0-rc.401` / Python `0.2.0rc401`。

## 0.2.0-rc.400 - 2026-11-20

rc.400 源码候选在删除会话时收起固定在该会话的弹窗。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 上下文面板、用量、导出、分支与回退弹窗在打开时固定目标会话。删除回执未确认时列表按约定保留，随后内核广播 `thread/deleted`，主界面移除列表项并退出当前会话，但这些弹窗此前仍保持打开：上下文面板继续对已删除会话刷新并报错，其余弹窗的操作只会得到会话不存在的失败。现在删除通知与删除回执都会逐一判定并收起固定在被删除会话上的弹窗，固定在其他会话的弹窗不受影响。修复 Issue [#2925](https://github.com/can4hou6joeng4/boss-harness/issues/2925)。
- 新增 `deletedDialogTarget.ts` 的 `detachedTarget`，五类目标共用同一判定；`check_deleted_thread_state.py` 增至 56 项，固定回调对五个固定目标逐一判定、禁止无条件清空，并固定两条删除路径的调用顺序。从 rc.399 提交导出真实主界面源码与修改版执行同一探针：旧版 7 项全部失败（模块与回调缺席），修改版 7 项全部通过，包括「删除目标会话收起五个弹窗、删除其他会话不收起」。同步桌面指南与技术参考。版本推进到 npm `0.2.0-rc.400` / Python `0.2.0rc400`。

## 0.2.0-rc.399 - 2026-11-20

rc.399 源码候选让参数错误点名具体原因，模型可以自行修复。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- rc.398 起含空字符或孤立代理项的字符串参数会在审批前被拒绝，但错误文案仍是通用的「工具参数不符合已注册的 schema」：模型不知道要删掉哪种字符，用同样写法重试必然再次失败。现在这类错误返回「工具参数包含无法作为命令行参数传递的字符（如空字符或孤立代理项），请去掉后重试」，其他类型、取值或必填不符仍保持通用文案，不泄露 schema 细节。修复 Issue [#2923](https://github.com/can4hou6joeng4/boss-harness/issues/2923)。
- `check_tool_arguments.py` 增至 24 项，固定两种错误文案的分流与点名字符类别的文案；从 rc.398 提交导出真实源码与修改版执行同一探针，旧版 12 项中 6 项失败（含 4 项空字符放行与通用文案），修改版全部通过。同步桌面指南、使用指南与技术参考。版本推进到 npm `0.2.0-rc.399` / Python `0.2.0rc399`。

## 0.2.0-rc.398 - 2026-11-20

rc.398 源码候选在审批之前拒绝无法作为命令行参数传递的工具参数。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 字符串工具参数（含对象键）携带 `\u0000` 时，注册表原先照常放行：需逐次批准的 `boss_hr_greet` 会先弹出审批卡，批准后 `Popen` 才以 `embedded null byte` 失败，并被记为「已派发、可能已生效」，回合暂停要求核对平台状态——实际什么都没发出。现在 `tool_schema.py` 在参数快照阶段一并拒绝空字符与孤立代理项，参数错误在审批之前返回。修复 Issue [#2921](https://github.com/can4hou6joeng4/boss-harness/issues/2921)。
- `tools/boss_cli.py` 在 `Popen` 因参数无法编码而抛 `ValueError` 时返回独立的 `CLI_ARGUMENT_ERROR`，与「可执行文件缺失」的 `CLI_ERROR` 分开；`agent.py` 把该错误码结算为 `not_executed` 并暂停回合，不再进入「已派发、结果不确定」集合。其他已派发失败仍按 `outcome_unknown` 处理。
- 新增 `check_tool_arguments.py`：除固定三层实现位置外，用真实注册表与执行器跑一遍空字符拒绝、正常参数放行、未启动结算与已派发失败的对照，共 18 项；接入 CI 与技术参考，静态检查增至 116 个。从 rc.397 提交导出真实源码与修改版执行同一探针：旧版 12 项中 6 项失败（4 项空字符放行、直接调用抛 `ValueError`、未启动被记为 `outcome_unknown`），修改版 12 项全部通过。同步桌面指南、使用指南与技术参考，并记录与 Pi 固定提交的对照结论。版本推进到 npm `0.2.0-rc.398` / Python `0.2.0rc398`。

## 0.2.0-rc.397 - 2026-11-20

rc.397 源码候选阻止删除后的迟到审批回执重建界面状态。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- rc.394 虽已移除删除会话的审批状态，自动批准的迟到失败 / 未确认回执仍会重建状态与审批卡；手动批准的成功回执也会重新创建消息缓存。两条路径现在都在发送前固定状态实例，回执到达后用 `approvalSubmissionIsCurrent` 只读核对归属，删除或替换后不再更新消息、提示、记住集合或发起恢复读取；切换会话、删除其他会话仍正常结算。保留真实回执语义，不撤销已受理审批或工具操作。修复 Issue [#2919](https://github.com/can4hou6joeng4/boss-harness/issues/2919)。
- 从真实 rc.396 与修改版 `App.tsx` 提取回调并加载各自的审批状态模块，各执行 24 种离线延迟回执场景：旧版删除或替换后 6 次消息缓存重建、4 次恢复读取，修复版均为 0。扩展既有删除状态检查至 42 项，同步桌面指南、技术参考与上游阅读记录。版本推进到 npm `0.2.0-rc.397` / Python `0.2.0rc397`。

## 0.2.0-rc.396 - 2026-11-20

rc.396 源码候选让删除被拒的提示区分占用原因。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 内核以 `THREAD_BUSY` 拒绝删除时会带 `data.reason`（运行中回合、摘要任务、队列投递或后台清理）。桌面此前忽略该字段，一律提示「停止当前回合并清空队列」；遇到摘要或投递时按提示操作并不会让删除成功。现在按原因给出对应的下一步，缺失或未知原因回退到不针对具体原因的兜底文案；查表使用 `Map`，特殊键名不会命中原型链。修复 Issue [#2917](https://github.com/can4hou6joeng4/boss-harness/issues/2917)。
- `check_delete_thread_error.py` 增至 37 项，固定四种提示互不相同、兜底文案与方括号查表禁令；使用指南补一句提示会说明占用原因。真实 rc.395 模块对照：旧版 3 项、新版 16 项断言通过。不新增 RPC 或平台调用。版本推进到 npm `0.2.0-rc.396` / Python `0.2.0rc396`。

## 0.2.0-rc.395 - 2026-11-20

rc.395 源码候选为两处桌面修复补上构建前静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `check_harness_events.py`（33 项）：固定 `toolCall/completed` 的终态清理——错误码与恢复建议只接受字符串、缺失时删除旧值，结果摘要回退顺序与内联 / 引用 / 省略三路投影互斥，运行中文案映射与自动批准的高风险门槛。此前 rc.390 的修复只由一次性离线探针验证。关联 Issue [#2915](https://github.com/can4hou6joeng4/boss-harness/issues/2915)。
- 新增 `check_harness_replica.py`（26 项）：固定删除通知的记号登记与按会话清理顺序，`ingest` / `apply` / `current` / `resume` 四处守卫，以及连接重置依次清空世代、条目版本与删除记号。两个脚本接入 CI 工作流与技术参考，静态检查增至 115 个；只新增检查，不改变运行时行为。版本推进到 npm `0.2.0-rc.395` / Python `0.2.0rc395`。

## 0.2.0-rc.394 - 2026-11-20

rc.394 源码候选补齐删除会话后的在途读取与审批状态清理。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 删除前发出的 `queue/list` 若晚到，其票据仍是最新一代，会把队列投影重新写回刚清掉的缓存，并再次尝试更新侧栏徽标。现在删除通知与删除回执都先让该会话的在途队列读取失效，迟到的结果不再写回，其他会话照常提交。修复 Issue [#2913](https://github.com/can4hou6joeng4/boss-harness/issues/2913)。
- 审批提交状态按会话保存在模块表中，此前在删除后不回收，迟到回执仍会写入。新增 `forgetApprovalSubmission`，两条删除路径都调用；遗忘后再次取用得到全新状态，其他会话保留。对真实 rc.393 模块执行同一探针：旧版 10 项、新版 16 项断言通过。扩展 `check_deleted_thread_state.py` 至 29 项，同步桌面指南、上游阅读记录与技术参考；不新增 RPC 或平台调用。版本推进到 npm `0.2.0-rc.394` / Python `0.2.0rc394`。

## 0.2.0-rc.393 - 2026-11-20

rc.393 源码候选修正删除会话后仍停留在已删除视图的问题。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 内核在 `thread/delete` 回执之前广播 `thread/deleted`。回执丢失、超时或形状不符时，桌面按约定保留列表并提示核对，但通知已移除侧栏条目；此前当前视图不会离开该会话，消息仍可阅读、输入区仍可发送。现在删除通知到达时，若被删除的正是当前会话就立即回到首页，与确认删除后的表现一致。修复 Issue [#2911](https://github.com/can4hou6joeng4/boss-harness/issues/2911)。
- 删除通知与删除回执共用 `forgetDeletedThread`：按会话遗忘消息缓存、队列投影、失败提示、条目版本、回合标识与记住的审批，并清后台完成标记；其他会话不受影响，重复通知幂等。新增 `check_deleted_thread_state.py` 固定两条路径，静态检查增至 113 个。对真实 rc.392 源码与修改版执行同一探针：旧版 7 项源码断言、新版 7 项源码断言与 18 项模块行为断言通过。同步桌面指南、上游阅读记录与技术参考；不新增 RPC 或平台调用。版本推进到 npm `0.2.0-rc.393` / Python `0.2.0rc393`。

## 0.2.0-rc.392 - 2026-11-20

rc.392 源码候选更新项目状态页的发布记录。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 项目状态页此前仍把「已发布资产的独立复核」列为待验收。现在写明 2026-11-20 对 `v0.2.0-rc.15` 的核对范围：远程 annotated tag、Release 正文与 schema 1 清单指向同一提交，下载的 wheel、sdist 与清单哈希和 `SHA256SUMS.txt` 一致；同时说明这次核对不是第三方审计，也没有重建该版本或重做桌面验收。关联 Issue [#2909](https://github.com/can4hou6joeng4/boss-harness/issues/2909)。
- 状态页新增下一次发布的滚动准备记录与未发送社区介绍草稿的入口，并把待验收项改为尚未建立的独立 release PR 与未启用的注册表渠道；独立安装包、真实模型与招聘平台的待验收边界保持不变。同步 English summary；README 不改。仅调整文档与版本元数据，没有创建 tag、Release 或上传资产。版本推进到 npm `0.2.0-rc.392` / Python `0.2.0rc392`。

## 0.2.0-rc.391 - 2026-11-20

rc.391 源码候选阻止删除会话后的迟到恢复结果重新写回。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `HarnessReplica` 收到 `thread/deleted` 后，使目标会话的恢复代次失效，清除在途恢复、游标、失败记录与条目版本，丢弃缓冲事件；当前连接内后续恢复与增量不再交付，连接重置清除删除记录，其他会话不受影响。此前删除通知后的迟到页面仍会交付旧快照与缓冲增量，实时大正文的迟到错误也会留下过时提示。修复 Issue [#2907](https://github.com/can4hou6joeng4/boss-harness/issues/2907)。
- 对真实 rc.390 源码与修改版执行同一离线探针，覆盖三个读取阶段的迟到成功 / 失败、缓冲事件、其他会话与连接重置：旧版 26 项基线断言及修复版 62 项断言通过。同步桌面指南与上游阅读记录；不新增 RPC 或平台调用。版本推进到 npm `0.2.0-rc.391` / Python `0.2.0rc391`。

## 0.2.0-rc.390 - 2026-11-20

rc.390 源码候选补齐实时工具卡的恢复建议。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 实时 `toolCall/completed` 此前遗漏内核已投影的 `error.recovery_action`，导致工具卡、消息复制与详情查找缺少建议，重新读取历史后才出现。现在映射到与历史相同的 `recoveryAction`，只接受字符串；新的完成结果未带合法建议时清除旧值，避免显示上一次的建议。修复 Issue [#2905](https://github.com/can4hou6joeng4/boss-harness/issues/2905)。
- 用导出的 rc.389 源码与修改后的源码执行同一组 27 项离线断言，覆盖实时与历史映射、复制、详情查找、畸形输入及旧值清理。同步桌面交互指南；不新增 RPC、工具调用或自动重试。版本推进到 npm `0.2.0-rc.390` / Python `0.2.0rc390`。

## 0.2.0-rc.389 - 2026-11-20

rc.389 源码候选让审批高风险标记在缺省或畸形时统一按必须逐次确认处理。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 桌面端此前有三处各自约定 `consequential` 的默认值：实时 `approval/requested` 归并按 `true`；会话快照、裁决与完成通知恢复审批卡的 `toApproval` 丢弃非布尔值，卡片显示「本次会话记住选择」且复选框可勾选；自动批准的内联条件用 `!params.consequential`，缺省、`null`、`0` 与空字符串都拦不住已记住工具的自动批准。现在新增共享判定 `approvalConsequential`，只有明确的布尔 `false` 才算可记住；事件归并、`toApproval`、受理后写入记住集合与新抽出的 `autoApprovalTarget` 都使用它，自动批准同时要求审批标识与工具名是非空字符串。内核对每次审批都发出 `true`，正常使用下行为不变；本项只收敛持久记录被改动或内核不符合协议时的默认值。修复 Issue [#2903](https://github.com/can4hou6joeng4/boss-harness/issues/2903)。
- 新增 `scripts/check_approval_remember.py`（61 项），固定共享判定与四处接入、自动批准的放行顺序、记住集合只在受理后写入，并按标记名出现次数做绊线。接入 CI 并在技术参考补同名小节，使用指南补一句默认值说明；检查脚本增至 112 个。版本推进到 npm `0.2.0-rc.389` / Python `0.2.0rc389`。

## 0.2.0-rc.388 - 2026-11-20

rc.388 源码候选固定侧栏队列徽标的分类优先级与增量校正。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_queue_badge.py`，固定三类状态逐项累计、待处理总数回退、「内核持久计数 → 完整投影 → 本地增量 → 只保留总数」的取用顺序、增量只在已知计数与旧总数一致时应用且结果非负并与新总数一致，以及补丁只改目标会话、数值未变返回 `null`；反向断言完整投影必须排除截断、未变化不得返回新数组、分类必须与新的待处理总数核对。修复 Issue [#2900](https://github.com/can4hou6joeng4/boss-harness/issues/2900)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 111 个。版本推进到 npm `0.2.0-rc.388` / Python `0.2.0rc388`。不改变运行时行为，只固定既有徽标契约。

## 0.2.0-rc.387 - 2026-11-20

rc.387 源码候选固定首页草稿的填充意图与技能并入。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_home_draft.py`，固定正文 / 附件 / 技能 / 读取附件 / 提交中五类「有未发送内容」、模板在读取或提交中先确认、「同文、无附件、无技能」才直接应用，以及技能入口已选或达 10 项时原样返回；反向断言读取或提交期间不得直接应用、技能上限必须包含第 10 项、重复技能不得追加。修复 Issue [#2898](https://github.com/can4hou6joeng4/boss-harness/issues/2898)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 110 个。版本推进到 npm `0.2.0-rc.387` / Python `0.2.0rc387`。不改变运行时行为，只固定既有草稿填充契约。

## 0.2.0-rc.386 - 2026-11-20

rc.386 源码候选固定剪贴板写入结果与迟到回执。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_clipboard_copy.py`，固定写入成功才显示「已复制」、失败原因只取错误消息并按 80 字符截断且不含正文、版本令牌丢弃迟到回执、计时器与卸载 / 重置清空反馈；反向断言失败原因不得拼接正文、迟到回执不得恢复提示、版本令牌必须在卸载与重置时推进。修复 Issue [#2896](https://github.com/can4hou6joeng4/boss-harness/issues/2896)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 109 个。版本推进到 npm `0.2.0-rc.386` / Python `0.2.0rc386`。不改变运行时行为，只固定既有复制反馈契约。

## 0.2.0-rc.385 - 2026-11-20

rc.385 源码候选固定暂停队列项的重试条件与原因文案。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_queue_retry.py`，固定 `followUp` + `paused` + 未去重的重试条件、`TURN_START_FAILED` 的 `inputPersisted === false`、三类暂停原因的三档文案顺序、转向消息早退与未知原因的保守出口；反向断言去重与输入已写入最先拦截、`TURN_START_FAILED` 只出现两次。修复 Issue [#2892](https://github.com/can4hou6joeng4/boss-harness/issues/2892)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 108 个。版本推进到 npm `0.2.0-rc.385` / Python `0.2.0rc385`。不改变运行时行为，只固定既有重试与文案契约。

## 0.2.0-rc.384 - 2026-11-20

rc.384 源码候选固定旧显示名称迁移的筛选与上限。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_alias_migration.py`，固定只遍历当前会话列表并按会话去重、非字符串 / 空白 / 同名别名只删除、名称按码点计数并受 500 与单次 50 条上限约束；反向断言不得遍历别名键、不得按 UTF-16 码元判长、空白或同名别名不得发起写入。修复 Issue [#2890](https://github.com/can4hou6joeng4/boss-harness/issues/2890)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 107 个。版本推进到 npm `0.2.0-rc.384` / Python `0.2.0rc384`。不改变运行时行为，只固定既有迁移契约。

## 0.2.0-rc.383 - 2026-11-20

rc.383 源码候选固定 `session/error` 通知的形状校验与单行摘要。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_session_error_notice.py`，固定会话标识上限、正文空白折叠与 600 码点 `safeSlice` 截断、缺省正文回退通用文案、非字符串正文整条丢弃，以及结果只含两个字段；反向断言不得按 UTF-16 码元切正文、空白正文必须回退、多余字段不得进入结果。修复 Issue [#2888](https://github.com/can4hou6joeng4/boss-harness/issues/2888)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 106 个。版本推进到 npm `0.2.0-rc.383` / Python `0.2.0rc383`。不改变运行时行为，只固定既有通知契约。

## 0.2.0-rc.382 - 2026-11-20

rc.382 源码候选固定删除会话失败的原因码与未确认措辞。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_delete_thread_error.py`，固定原因码只在 `rpcError === true` 且 `data.code` 为字符串时读取、`THREAD_BUSY` → `failed`、`THREAD_DELETE_INCOMPLETE` / `THREAD_NOT_FOUND` → `incomplete`、其他原因 → `unknown` 并带原始错误文本；反向断言原因码只允许三种、不得说成已删除、未知原因必须带原始错误文本。修复 Issue [#2887](https://github.com/can4hou6joeng4/boss-harness/issues/2887)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 105 个。版本推进到 npm `0.2.0-rc.382` / Python `0.2.0rc382`。不改变运行时行为，只固定既有删除失败契约。

## 0.2.0-rc.381 - 2026-11-20

rc.381 源码候选固定在途请求标记的推进与作废。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_attempt_token.py`，固定标记初值为 0、`startAttempt` 与 `invalidateAttempts` 都递增、`startAttempt` 返回新标记、`attemptCurrent` 严格相等；反向断言开始与作废都必须推进标记、开始提交不得重置标记、比较不得放宽。修复 Issue [#2885](https://github.com/can4hou6joeng4/boss-harness/issues/2885)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 104 个。版本推进到 npm `0.2.0-rc.381` / Python `0.2.0rc381`。不改变运行时行为，只固定在途请求标记契约。

## 0.2.0-rc.380 - 2026-11-20

rc.380 源码候选固定队列读取的代数票据与失效语义。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_queue_read_guard.py`，固定按会话维护代数、领票先推进再快照、`commit` 只在仍为最新一代时写入、`invalidate` 只推进代数、缺失会话从 0 起算；反向断言写入必须经过当前代检查、失效不得删除代数记录、缺失会话不得使用负值起点。修复 Issue [#2884](https://github.com/can4hou6joeng4/boss-harness/issues/2884)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 103 个。版本推进到 npm `0.2.0-rc.380` / Python `0.2.0rc380`。不改变运行时行为，只固定既有并发读取契约。

## 0.2.0-rc.379 - 2026-11-20

rc.379 源码候选固定单飞读取的尾随补跑与取消。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_single_flight.py`，固定取消与 `canRun` 入口守卫、在途只置尾随标记、同步抛错转为已解决 Promise、`catch().finally()` 收尾释放与尾随复检，以及 `cancel` 同时清除两个标记；反向断言单飞标记只能在收尾释放、尾随标记只在补跑与取消时清除、不得用延时轮询代替尾随补跑。修复 Issue [#2882](https://github.com/can4hou6joeng4/boss-harness/issues/2882)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 102 个。版本推进到 npm `0.2.0-rc.379` / Python `0.2.0rc379`。不改变运行时行为，只固定既有刷新与取消契约。

## 0.2.0-rc.378 - 2026-11-20

rc.378 源码候选固定主题偏好的解析、合成与写回。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_theme_preference.py`，固定 `system` / `light` / `dark` 三态联合类型、非字符串与空白大小写折叠、无法识别时回退 `system`、`resolveDarkTheme` 的真假分支与跟随系统、`serializeThemePreference` 只保留黑白两态；反向断言不得跳过空白折叠、不得原样写回未知值、回退不得落到固定外观。修复 Issue [#2881](https://github.com/can4hou6joeng4/boss-harness/issues/2881)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 101 个。版本推进到 npm `0.2.0-rc.378` / Python `0.2.0rc378`。不改变运行时行为，只固定既有主题契约。

## 0.2.0-rc.377 - 2026-11-20

rc.377 源码候选固定界面偏好导出文件的导入校验。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_preferences_file.py`，固定 64 KiB 字节上限、版本与两种作用域、旧作用域按旧前缀读取、五个偏好键的字符串枚举与「任一已知键非法就整体拒绝」，以及导出只写白名单键；反向断言不得导出别名或项目名、旧作用域不得按新前缀读取、不得跳过非法已知键、不得展开偏好对象。修复 Issue [#2879](https://github.com/can4hou6joeng4/boss-harness/issues/2879)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 100 个。版本推进到 npm `0.2.0-rc.377` / Python `0.2.0rc377`。不改变运行时行为，只固定既有导入导出契约。

## 0.2.0-rc.376 - 2026-11-20

rc.376 源码候选固定界面时间格式与会话排序键的严格解析。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_time_format.py`，固定两位补零、`formatLocalDateTime` / `formatLocalClock` 的非法时间空串回退、ISO 包装的严格解析，以及 `sessionUpdatedAt` 的 `?? 0` 排序键；反向断言不得跟随系统区域、排序键不得使用宽松 `Date.parse`、两个格式化函数都必须判 `NaN`。修复 Issue [#2877](https://github.com/can4hou6joeng4/boss-harness/issues/2877)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 99 个。版本推进到 npm `0.2.0-rc.376` / Python `0.2.0rc376`。不改变运行时行为，只固定既有格式与排序契约。

## 0.2.0-rc.375 - 2026-11-20

rc.375 源码候选固定新建会话与首条消息的四种结果。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_session_start.py`，固定四种状态、`createdSession` 的「失败之外都有会话」、发送结果的 `true` / `"uncertain"` / `false` 映射，以及主界面与快速提问提示的分支；反向断言 `unconfirmed` 不得按失败处理、「未能创建会话」只出现在快速提问的失败分支。修复 Issue [#2875](https://github.com/can4hou6joeng4/boss-harness/issues/2875)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 98 个。版本推进到 npm `0.2.0-rc.375` / Python `0.2.0rc375`。不改变运行时行为，只固定既有结果契约。

## 0.2.0-rc.374 - 2026-11-20

rc.374 源码候选固定会话列表回执的逐项校验与去重。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_thread_list.py`，固定标识与标题时间上限、`archived` 与 `toolPolicy` 枚举、`optionalText` 的缺省 / 非法区分、`lastTurn` 的恢复目标与状态白名单，以及 `uniqueThreadIds` 的集合大小比较；反向断言非法可选字段不得当作缺省、重复 id 不得放行、三项可选文本必须同时校验。修复 Issue [#2873](https://github.com/can4hou6joeng4/boss-harness/issues/2873)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 97 个。版本推进到 npm `0.2.0-rc.374` / Python `0.2.0rc374`。不改变运行时行为，只固定既有回执契约。

## 0.2.0-rc.373 - 2026-11-20

rc.373 源码候选固定界面偏好的旧命名空间迁移。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_ui_storage.py`，固定先收集旧键再写入、前缀替换、新键存在时跳过、值非空才写入与整体异常回退；反向断言不得删除旧键、不得让旧值覆盖新键、迁移必须捕获异常。修复 Issue [#2871](https://github.com/can4hou6joeng4/boss-harness/issues/2871)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 96 个。版本推进到 npm `0.2.0-rc.373` / Python `0.2.0rc373`。不改变运行时行为，只固定既有迁移契约。

## 0.2.0-rc.372 - 2026-11-20

rc.372 源码候选固定最近打开会话的存储解析与回退。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_last_session.py`，固定严格解析（空白、超长与 `id !== raw`）、命名空间键、读写异常回退与 `null` 删除键；反向断言损坏记录不得恢复、读写都要捕获异常、清空不得写入空字符串。修复 Issue [#2869](https://github.com/can4hou6joeng4/boss-harness/issues/2869)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 95 个。版本推进到 npm `0.2.0-rc.372` / Python `0.2.0rc372`。不改变运行时行为，只固定既有存储契约。

## 0.2.0-rc.371 - 2026-11-20

rc.371 源码候选固定发送失败与结果未确认的措辞边界。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_send_failure.py`，固定内核拒绝写「发送失败」、不确定情况写「提交结果尚未确认」、两条主提示的下一步说明与复核提示的主因复用；反向断言两种来源不得对调、复核提示不得重复读取说明。修复 Issue [#2867](https://github.com/can4hou6joeng4/boss-harness/issues/2867)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 94 个。版本推进到 npm `0.2.0-rc.371` / Python `0.2.0rc371`。不改变运行时行为，只固定既有措辞契约。

## 0.2.0-rc.370 - 2026-11-20

rc.370 源码候选固定用量范围单选组的方向键循环。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_usage_view_keys.py`，固定左右与上下方向键的 ±1 映射、其他按键返回 `null`、`indexOf` 越界保护与非负取模循环；反向断言不得只处理左右键、取模前必须补齐长度、未知视图不得回退首项。修复 Issue [#2865](https://github.com/can4hou6joeng4/boss-harness/issues/2865)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 93 个。版本推进到 npm `0.2.0-rc.370` / Python `0.2.0rc370`。不改变运行时行为，只固定既有键盘契约。

## 0.2.0-rc.369 - 2026-11-20

rc.369 源码候选固定侧栏提示的序号重播与清空语义。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_sidebar_notice.py`，固定每次回执自增 `seq`、清空只清文案且空态返回原对象、2600ms 停留，以及侧栏组件按 `notice.seq` 作 key 并保留 `role="status"`；反向断言相同文案不得复用对象、清空不得重置序号、组件不得改用文案作 key。修复 Issue [#2862](https://github.com/can4hou6joeng4/boss-harness/issues/2862)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 92 个。版本推进到 npm `0.2.0-rc.369` / Python `0.2.0rc369`。不改变运行时行为，只固定既有回执契约。

## 0.2.0-rc.368 - 2026-11-20

rc.368 源码候选固定通知分组标题的拼接与截断。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_notification_labels.py`，固定空白折叠、8 位回退、项目与标题去重、归档后缀、120 上限的长度判断与 `safeSlice` 截断；反向断言不得按 UTF-16 码元截断、长度判断不得忽略后缀。修复 Issue [#2860](https://github.com/can4hou6joeng4/boss-harness/issues/2860)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 91 个。版本推进到 npm `0.2.0-rc.368` / Python `0.2.0rc368`。不改变运行时行为，只固定既有标题契约。

## 0.2.0-rc.367 - 2026-11-20

rc.367 源码候选固定任务队列状态与暂停原因的文案分支。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_queue_status.py`，固定五种通用标签、暂停原因四条分支的顺序、关联去重说明、暂停说明的前置空判定与 `retryAvailable` 的适用范围；反向断言非暂停项先返回 `null`、暂停标签不得覆盖具体来源、`retryAvailable` 不得作为独立分支。修复 Issue [#2858](https://github.com/can4hou6joeng4/boss-harness/issues/2858)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 90 个。版本推进到 npm `0.2.0-rc.367` / Python `0.2.0rc367`。不改变运行时行为，只固定既有文案契约。

## 0.2.0-rc.366 - 2026-11-20

rc.366 源码候选固定会话索引健康度的读数与文案。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_session_index_health.py`，固定安全整数校验、零计数与列出 id 的矛盾判定、id 去重与 20 条截断，以及「未报告 / N 个无法读取 / 正常」三态文案；反向断言未报告不得写成正常、去重必须先查再入列、计数不得放宽为普通整数。修复 Issue [#2856](https://github.com/can4hou6joeng4/boss-harness/issues/2856)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 89 个。版本推进到 npm `0.2.0-rc.366` / Python `0.2.0rc366`。不改变运行时行为，只固定既有读数契约。

## 0.2.0-rc.365 - 2026-11-20

rc.365 源码候选固定模型线路切换的在途锁与回执令牌。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_model_switch.py`，固定 `begin` 的在途拒绝与令牌自增、结算前核对令牌、按会话复用实例与匿名预览的本地实例；反向断言在途不得交出令牌、迟到回执不得越过核对、实例不得每次新建。修复 Issue [#2854](https://github.com/can4hou6joeng4/boss-harness/issues/2854)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 88 个。版本推进到 npm `0.2.0-rc.365` / Python `0.2.0rc365`。不改变运行时行为，只固定既有在途锁契约。

## 0.2.0-rc.364 - 2026-11-20

rc.364 源码候选固定搜索回执的形状校验与上限。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_thread_search_result.py`，固定标识与标题片段的长度上限、角色白名单、`SEARCH_MATCH_LIMIT = 200`、`truncated` 只接受布尔或缺省，以及任一命中非法时整体拒绝；反向断言角色先校验再断言类型、截断标记只取显式 `true`、单条非法不得跳过。修复 Issue [#2851](https://github.com/can4hou6joeng4/boss-harness/issues/2851)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 87 个。版本推进到 npm `0.2.0-rc.364` / Python `0.2.0rc364`。不改变运行时行为，只固定既有回执契约。

## 0.2.0-rc.363 - 2026-11-20

rc.363 源码候选固定会话内查找沿用选中文本的放行条件。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_find_seed.py`，固定可编辑控件、非字符串、空选择、多行与 120 码点上限的判定顺序，以及 `isEditableTarget` 的标签与 `isContentEditable` 检查；反向断言不得按 UTF-16 码元判长、多行校验不得先于 `trim()`。修复 Issue [#2850](https://github.com/can4hou6joeng4/boss-harness/issues/2850)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 86 个。版本推进到 npm `0.2.0-rc.363` / Python `0.2.0rc363`。不改变运行时行为，只固定既有放行契约。

## 0.2.0-rc.362 - 2026-11-20

rc.362 源码候选固定会话内查找状态行的计数单位与分支。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_find_status.py`，固定空查询回退、位次夹取与 1 起始显示、只有 `capped === true` 追加高亮上限说明、零命中时的详情提示与最终结论，并反向断言向下取整、详情提示只出现一次、上限引用常量。修复 Issue [#2849](https://github.com/can4hou6joeng4/boss-harness/issues/2849)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 85 个。版本推进到 npm `0.2.0-rc.362` / Python `0.2.0rc362`。不改变运行时行为，只固定既有状态行契约。

## 0.2.0-rc.361 - 2026-11-20

rc.361 源码候选固定会话内查找的游标位点与循环跳转。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_find_step.py`，固定每条匹配消息至少一处位点、游标夹取、段内前进、跨消息循环（含反向进入末尾）与全局序号累加，并反向断言向下取整、非负取模与逐条累加。修复 Issue [#2847](https://github.com/can4hou6joeng4/boss-harness/issues/2847)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 84 个。版本推进到 npm `0.2.0-rc.361` / Python `0.2.0rc361`。不改变运行时行为，只固定既有查找游标契约。

## 0.2.0-rc.360 - 2026-11-20

rc.360 源码候选固定搜索结果的顺序与命中定位意图。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_search_options.py`，固定消息命中在前、会话结果在后，`message:` / `session:` 键与去重，缺行跳过，角色标签三分支，以及只有工具命中展开工具块、关键词 `trim()`。修复 Issue [#2845](https://github.com/can4hou6joeng4/boss-harness/issues/2845)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 83 个。版本推进到 npm `0.2.0-rc.360` / Python `0.2.0rc360`。不改变运行时行为，只固定既有结果顺序与定位契约。

## 0.2.0-rc.359 - 2026-11-20

rc.359 源码候选让搜索空态的最短字符数提示引用常量，并固定状态行与空态的分支。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 搜索空态提示「输入至少 N 个字符可同时搜索消息内容」改为引用 `MESSAGE_SEARCH_MIN_LENGTH`，不再写死 2；运行时输出不变。修复 Issue [#2843](https://github.com/can4hou6joeng4/boss-harness/issues/2843)。
- 新增 `scripts/check_search_status.py`（38 项），固定状态行与空态的分支顺序、截断说法、完整结论只在最后分支出现、失败与过长不宣称没有命中，以及最短 / 最长字符数引用常量。接入 CI 并在技术参考补同名小节；检查脚本增至 82 个。版本推进到 npm `0.2.0-rc.359` / Python `0.2.0rc359`。

## 0.2.0-rc.358 - 2026-11-20

rc.358 源码候选固定会话内查找的高亮区间与折叠块语义。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_find_highlight.py`，固定 200 个区间上限、归一化文本扫描与偏移映射、同一次字素展开的重叠合并（取最大结束位置）、片段拆分顺序、关闭 `<details>` 的排除与 `summary` 例外，以及 `includeFolded` 语义。修复 Issue [#2841](https://github.com/can4hou6joeng4/boss-harness/issues/2841)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 81 个。版本推进到 npm `0.2.0-rc.358` / Python `0.2.0rc358`。不改变运行时行为，只固定既有查找契约。

## 0.2.0-rc.357 - 2026-11-20

rc.357 源码候选固定消息搜索的批次失效与内核响应校验。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_message_search.py`，固定批次与当前查询 / 归档范围不一致时返回空结果、非数组回退、命中逐项校验（非空 `threadId` / `itemId`、`threadTitle` 与 `snippet` 字符串、`role` 白名单含 `tool`）、按可见会话过滤与 `truncated === true`，以及 `liveMessageSearchState` 的四条分支。修复 Issue [#2839](https://github.com/can4hou6joeng4/boss-harness/issues/2839)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 80 个。版本推进到 npm `0.2.0-rc.357` / Python `0.2.0rc357`。不改变运行时行为，只固定既有响应校验与状态契约。

## 0.2.0-rc.356 - 2026-11-20

rc.356 源码候选固定会话行的归档过滤、关键词与排序。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_search_rows.py`，固定归档默认排除、按会话 id 去重顺序、标题与项目名拼接后的整串 NFKC 小写、关键词全部命中（`every`）与更新时间降序，并跨文件核对高亮使用的 `searchText` 为同一归一化口径。修复 Issue [#2837](https://github.com/can4hou6joeng4/boss-harness/issues/2837)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 79 个。版本推进到 npm `0.2.0-rc.356` / Python `0.2.0rc356`。不改变运行时行为，只固定既有过滤与排序契约。

## 0.2.0-rc.355 - 2026-11-20

rc.355 源码候选固定会话标题的项目前缀剥离与码点截断。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_session_title.py`，固定「招聘项目：」前缀剥离、折叠空白与 `trim()` 顺序、按 Unicode 码点判定与截断、空标题回退「新会话」，以及 `compactTitle` 的非正上限回退与省略号；反向断言不得用 `slice` / `substring` 直接截断，并核对默认上限不超过内核的 `MAX_THREAD_TITLE_CHARS`。修复 Issue [#2835](https://github.com/can4hou6joeng4/boss-harness/issues/2835)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 78 个。版本推进到 npm `0.2.0-rc.355` / Python `0.2.0rc355`。不改变运行时行为，只固定既有标题契约。

## 0.2.0-rc.354 - 2026-11-20

rc.354 源码候选收敛最近搜索的阈值来源并固定本地存储回退。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `RECENT_SEARCH_MIN_LENGTH` 改为引用 `MESSAGE_SEARCH_MIN_LENGTH`，不再与搜索弹窗的消息搜索阈值各写一份；运行时取值保持 2，历史记录行为不变。修复 Issue [#2833](https://github.com/can4hou6joeng4/boss-harness/issues/2833)。
- 新增 `scripts/check_recent_search.py`，固定最短 / 最长字符数来自 `searchStatus`、去重按 NFKC 小写、上限 5、损坏 JSON 与非数组回退为空、写入失败仍返回当前列表，并反向断言不得重新写死阈值。接入 CI 并在技术参考补同名小节；检查脚本增至 77 个。版本推进到 npm `0.2.0-rc.354` / Python `0.2.0rc354`。

## 0.2.0-rc.353 - 2026-11-20

rc.353 源码候选固定用量 CSV 导出的公式防护与转义契约。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_usage_report.py`，固定「复制 CSV」的公式前缀单引号、RFC 4180 引号与双引号翻倍、16 列表头与行序、CRLF 行尾、未上报不写成 0、原因键原型链防护与 `usageJobSource` 分支，并反向断言不得直接返回原文、不得绕过自有属性检查或增加费用列。修复 Issue [#2831](https://github.com/can4hou6joeng4/boss-harness/issues/2831)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 76 个。版本推进到 npm `0.2.0-rc.353` / Python `0.2.0rc353`。不改变运行时行为，只固定既有导出契约。

## 0.2.0-rc.352 - 2026-11-20

rc.352 源码候选说明导出弹窗的桥接缺失并固定关键行为。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 导出弹窗在内核已连接但当前桌面外壳没有 `exportSession` 时显示「当前桌面外壳不支持会话导出，请更新桌面端后重试。」，不再只把保存按钮灰掉而不说明原因。修复 Issue [#2829](https://github.com/can4hou6joeng4/boss-harness/issues/2829)。
- 新增 `scripts/check_export_dialog.py`，固定目标会话在打开时固定、切换目标使旧回执失效、保存期间锁定选项与关闭、明文导出需二次确认、请求字段与保存 / 取消 / 失败 / 截断 / 权限回执，并反向断言不得发送未确认明文或绕过 `requestClose`。接入 CI 并在技术参考补同名小节；检查脚本增至 75 个。版本推进到 npm `0.2.0-rc.352` / Python `0.2.0rc352`。

## 0.2.0-rc.351 - 2026-11-20

rc.351 源码候选收敛旧内核回退路径的本地 Markdown 导出标题。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `exportMarkdown` 先把标题的连续空白折叠为单个空格、去除首尾空白，用共享 `safeSlice` 限制 200 个字符，空标题回退为「当前会话」，标题不再能把换行或超长内容带进 `#` 标题行。正文、段落、列表与工具复制文本保持原顺序。修复 Issue [#2827](https://github.com/can4hou6joeng4/boss-harness/issues/2827)。
- 新增 `scripts/check_local_export.py`，固定标题收敛、拼装顺序与工具文本复用，并反向断言标题不得直接进入模板或绕过共享截断。接入 CI 并在技术参考补同名小节；检查脚本增至 74 个。版本推进到 npm `0.2.0-rc.351` / Python `0.2.0rc351`。

## 0.2.0-rc.350 - 2026-11-20

rc.350 源码候选固定 JSON 导出的 schema 标识并写入文档。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 扩充 `scripts/check_export_json.py`：固定 `EXPORT_SCHEMA = "boss-harness-session-export/1"` 与 `meta` 对常量的引用，校验 schema 仍为「名称/整数版本」形式，禁止在 `meta` 另写 schema 字面量。检查增至 45 项。修复 Issue [#2825](https://github.com/can4hou6joeng4/boss-harness/issues/2825)。
- 桌面指南写明 JSON 的 `schema` 字段与版本含义，技术参考同步核对范围；检查脚本仍为 73 个。版本推进到 npm `0.2.0-rc.350` / Python `0.2.0rc350`。不改变运行时行为，只固定既有导出契约。

## 0.2.0-rc.349 - 2026-11-20

rc.349 源码候选为会话导出 JSON 的分组结构与严格编码补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_export_json.py`：固定回合前条目进入 `beforeFirstTurn`、后续条目追加到最近回合 `entries` 的分组顺序；核对 `meta`、四项脱敏标记与计数、三类来源、截断与字节预算字段；固定 `ensure_ascii=False`、`indent=2`、`default=str`、`allow_nan=False` 以及过深嵌套 / 非有限数值的可读降级。反向断言不得允许 NaN / Infinity、不得改用 ASCII 转义或绕过参数直接编码。修复 Issue [#2823](https://github.com/can4hou6joeng4/boss-harness/issues/2823)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 73 个。版本推进到 npm `0.2.0-rc.349` / Python `0.2.0rc349`。不改变运行时行为，不生成或解析导出文件。

## 0.2.0-rc.348 - 2026-11-20

rc.348 源码候选修复 Markdown 导出单行元数据的行内定界符转义。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 拆分 `_code_text` 与 `_inline_text`：前者只处理反引号、回车与换行，供行内代码与 HTML 文本使用；后者在此基础上把 `\`、`[`、`]`、`<`、`>`、`*`、`_`、`~`、`|` 转义为字面字符。会话标题、工具来源、恢复建议与工具参数 JSON 等单行元数据不再能把链接、图片、原生 HTML 或强调带进渲染结果。修复 Issue [#2821](https://github.com/can4hou6joeng4/boss-harness/issues/2821)。
- HTML 导出的摘要任务行改用 `_code_text`，避免把 Markdown 反斜杠写进页面；JSON 导出不变。`check_export_markdown.py` 增至 90 项并补反向断言，检查脚本仍为 72 个。版本推进到 npm `0.2.0-rc.348` / Python `0.2.0rc348`。

## 0.2.0-rc.347 - 2026-11-20

rc.347 源码候选为会话导出 Markdown 的定界与代码围栏补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_export_markdown.py`：固定 `_inline_text` 的反引号 / 回车 / 换行替换、`_inline_code` 的行内代码包裹，以及 `_fence` 按正文最长反引号或波浪线动态加长（最少三个）的围栏算法；覆盖回合元数据、用户输入、模型输出、工具调用、结果明文、摘要、文档头与队列字段的中和入口。反向断言围栏不退回固定三个反引号或波浪线、正文不再经 `_inline_text`。修复 Issue [#2819](https://github.com/can4hou6joeng4/boss-harness/issues/2819)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 72 个。版本推进到 npm `0.2.0-rc.347` / Python `0.2.0rc347`。不改变运行时行为，不渲染或打开导出文件。

## 0.2.0-rc.346 - 2026-11-20

rc.346 源码候选为会话导出 HTML 的转义与页面约束补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_export_html.py`：固定会话元数据、回合、用户与模型正文、附件、工具调用、审批、结果、摘要与队列字段的 `_h(` 转义入口，结果明文只在 `included` 分支写入，文档头保留 charset / viewport / CSP / referrer；反向断言页面不含脚本、事件属性、帧、`javascript:`、`src=` 或 `href=`。修复 Issue [#2817](https://github.com/can4hou6joeng4/boss-harness/issues/2817)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 71 个。版本推进到 npm `0.2.0-rc.346` / Python `0.2.0rc346`。不改变运行时行为，不生成或打开导出文件。

## 0.2.0-rc.345 - 2026-11-20

rc.345 源码候选为导出与界面的时长文案补上双端一致检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_duration_parity.py`：同时扫描内核 `session_export._duration_text` 与共享 `formatDurationMs`，固定毫秒取整方式、秒 / 分 / 小时的阈值与文案、剩余秒与剩余分分支，以及四个中文标签在两侧同时存在；核对内核导出至少四处调用 `_duration_text`、桌面通知共用 `formatDurationMs`，反向断言不得改用其它取整方式。修复 Issue [#2815](https://github.com/can4hou6joeng4/boss-harness/issues/2815)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 70 个。版本推进到 npm `0.2.0-rc.345` / Python `0.2.0rc345`。不改变运行时行为，不执行导出或发布动作。

## 0.2.0-rc.344 - 2026-11-20

rc.344 源码候选补齐桌面持续工作的用户文档。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 能力表新增「在桌面里持续工作」，概括窗口状态恢复、渲染进程崩溃后的有限自动重载与诊断页、后台审批与较久回合通知；桌面交互指南的「界面偏好与恢复」补窗口状态说明，包括保存时机、最小可见判定、工作区收敛与损坏状态整体忽略。修复 Issue [#2813](https://github.com/can4hou6joeng4/boss-harness/issues/2813)。
- 不改变运行时行为；版本推进到 npm `0.2.0-rc.344` / Python `0.2.0rc344`，不执行发布动作。

## 0.2.0-rc.343 - 2026-11-20

rc.343 源码候选为跨包共享的时间、截断与定位工具补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_shared_utils.py`：固定解释器与线路选择的去空白规则，ISO 正则、月份天数、闰年与字段范围校验及 `Date` 调用顺序，相对时间与时长文案的分支，`safeSlice` 的有限值 / 正数 / 高代理项判定，`codePointLength` 的代理对步进，`truncate`、`stripIpcErrorWrapper` 与定位转发的缓存 / 微任务交付 / 清除顺序。反向断言时长四舍五入、截断避开代理对、定位转发交付前清除待回放。修复 Issue [#2811](https://github.com/can4hou6joeng4/boss-harness/issues/2811)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 69 个。版本推进到 npm `0.2.0-rc.343` / Python `0.2.0rc343`。不改变运行时行为，不执行时间格式化或发布动作。

## 0.2.0-rc.342 - 2026-11-20

rc.342 源码候选为桌面启动接管、单实例与退出确认补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_lifecycle.py`：固定退出确认的文案、按钮顺序、默认 / 取消按钮与单次弹框，选择「继续运行」或「停止并退出」后的路径，以及确认后清理登录、自检与 Host 的顺序；固定旧目录接管的空目录判定、非空放弃、删除失败放弃与改名失败保留；固定应用名、接管时机、窗口工厂与单实例锁顺序。反向断言默认按钮不落在「停止并退出」，接管不递归删除或复制。修复 Issue [#2809](https://github.com/can4hou6joeng4/boss-harness/issues/2809)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 68 个。版本推进到 npm `0.2.0-rc.342` / Python `0.2.0rc342`。不改变运行时行为，不弹确认框或改用户目录。

## 0.2.0-rc.341 - 2026-11-20

rc.341 源码候选为渲染层崩溃恢复与静态诊断页补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_renderer_recovery.py`：固定自动重载上限与滚动窗口、六个已知原因的自有属性查表、未知原因与退出码校验、恢复参数的逐项校验与历史过滤、忽略 / 重载 / 报告顺序；固定 `ERR_ABORTED` 与当前导航判定；固定诊断页的 300 字符截断、孤立代理项修复、HTML 实体转义、CSP 与 data URL 编码，并反向断言无脚本无外链；同时核对 `window.ts` 的一次性失败标记、崩溃决策顺序与竞态守卫。修复 Issue [#2807](https://github.com/can4hou6joeng4/boss-harness/issues/2807)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 67 个。版本推进到 npm `0.2.0-rc.341` / Python `0.2.0rc341`。不改变运行时行为，不启动渲染进程或执行发布动作。

## 0.2.0-rc.340 - 2026-11-20

rc.340 源码候选为窗口状态的解析、恢复与原子保存补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_window_state.py`：固定窗口尺寸上下限与最小可见阈值，状态 JSON 的整体校验与安全整数要求，重叠判定与最大工作区收敛、位置钳制与最大化保留；保存用进程号 / 时间戳 / 计数器命名的独占临时文件、`0600` 与 `wx`、`EEXIST` 不清理、改名失败清理，以及防抖保存、关闭补存与 `getNormalBounds()` 边界；同时核对 `index.ts` 的状态路径、工作区来源与跟踪调用。修复 Issue [#2805](https://github.com/can4hou6joeng4/boss-harness/issues/2805)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 66 个。版本推进到 npm `0.2.0-rc.340` / Python `0.2.0rc340`。不改变运行时行为，不创建窗口或执行发布动作。

## 0.2.0-rc.339 - 2026-11-20

rc.339 源码候选为桌面通知的内容、去重与点击定位补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_notifications.py`：固定审批通知的字段上限、摘要折叠与回退、会话与条目 id 成对出现、同一审批只提醒一次；固定回合通知的 20 秒门槛、状态标签、时长校验与开始时间淘汰；固定通知保留队列的重排与关闭 / 失败释放、徽标 0–999 的整数范围、前台不打扰、点击聚焦与双 id 定位、测试通知固定文案；反向断言通知正文不携带会话标题或记录参数。修复 Issue [#2803](https://github.com/can4hou6joeng4/boss-harness/issues/2803)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 65 个。版本推进到 npm `0.2.0-rc.339` / Python `0.2.0rc339`。不改变运行时行为，不发送系统通知，不执行发布动作。

## 0.2.0-rc.338 - 2026-11-20

rc.338 源码候选为会话导出的原子写入与失败诊断补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_export_write.py`：固定临时文件与目标同目录、独占创建、`O_NOFOLLOW` 回退与 `0600`，写入 → 刷新 → 收紧权限 → 关闭 → 复核目标身份 → 原子替换的顺序，`ENOENT` / `ELOOP` / 符号链接处理，失败后的临时文件清理与 `permissionError` 降级，保存对话框覆盖确认，以及诊断只保留 errno、回执只回文件名。修复 Issue [#2801](https://github.com/can4hou6joeng4/boss-harness/issues/2801)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 64 个。版本推进到 npm `0.2.0-rc.338` / Python `0.2.0rc338`。不改变运行时行为，不执行写入或发布动作。

## 0.2.0-rc.337 - 2026-11-20

rc.337 源码候选为平台登录补上域名、Cookie 与回执检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_login_security.py`：固定官方登录 URL 的协议、内嵌凭据、端口与主机名，验证页判定失败关闭，扫码就绪顺序，登录视图边界与上下文；Cookie 只接受官方登录域并按 host-only / 路径 / 域长度选择更具体者，同值去重、真正歧义失败与无原型输出；主进程与渲染层共享登录状态、阶段、身份与字段上限；失败诊断保留原因码并经 `safeSlice` 截断。修复 Issue [#2799](https://github.com/can4hou6joeng4/boss-harness/issues/2799)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 63 个。版本推进到 npm `0.2.0-rc.337` / Python `0.2.0rc337`。不改变运行时行为，不执行登录或发布动作。

## 0.2.0-rc.336 - 2026-11-20

rc.336 源码候选补齐上游招聘 CLI 的安装入口。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 使用指南「上游 CLI 设置」新增上游仓库链接与 `uv tool install boss-agent-cli` / `boss doctor` 安装诊断入口，说明登录、平台认证与网络边界由上游维护；README 从源码启动入口加同一链接。修复 Issue [#2797](https://github.com/can4hou6joeng4/boss-harness/issues/2797)。
- 版本推进到 npm `0.2.0-rc.336` / Python `0.2.0rc336`。不改变运行时行为，不执行安装、发布或平台操作。

## 0.2.0-rc.335 - 2026-11-20

rc.335 源码候选为会话日志的编码、严格解码与有界快照补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_session_log.py`：固定单行 32 MiB、线程 / 标识 / 事件 / 附件摘要格式、UTF-8 编码与换行、重复键 / 非法常量 / 非有限浮点 / 孤立代理项拒绝、会话头只允许第 1 行、必需字段与 payload 形状、64 KiB 分块与快照长度校验、末尾残段截断与 `fsync`、快照逐行严格解码。修复 Issue [#2795](https://github.com/can4hou6joeng4/boss-harness/issues/2795)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 62 个。版本推进到 npm `0.2.0-rc.335` / Python `0.2.0rc335`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.334 - 2026-11-20

rc.334 源码候选为上下文编辑与摘要检查点补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_context_edits.py`：固定编辑记录负载键、目标必须已出现、替换文本 32 000 字符 / 128 KiB 上限、模型路径严格拒绝与展示路径单处宽松读取、`originalInput` 剥离与 `contextEdit` 标注；编辑入口在写入锁内校验现状、来源摘要与不可编辑原因，先构造并校验响应再落盘；检查点字段白名单与安全整数、摘要长度与规范 SHA-256、来源回合与条目完整性、运行中条目拒绝和原始记录一致性。修复 Issue [#2793](https://github.com/can4hou6joeng4/boss-harness/issues/2793)。
- 接入 CI 并在技术参考补同名小节；检查脚本增至 61 个。版本推进到 npm `0.2.0-rc.334` / Python `0.2.0rc334`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.333 - 2026-11-20

rc.333 源码候选把首页快速开始拆成「安装已发布的内核」与「从源码启动桌面」两个入口。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 快速开始分列两个入口：内核入口从 GitHub Releases 下载 wheel，在独立虚拟环境核对 `--version` 与 `--help`；桌面入口保留源码命令与 `SETUP.md` 助手入口。首页不写入具体发布版本号，逐版本变化仍由 CHANGELOG 与 Releases 承载。修复 Issue [#2791](https://github.com/can4hou6joeng4/boss-harness/issues/2791)。
- 在 `UPSTREAM.md` 记录三个参考项目默认分支固定提交的安装入口结构；不复制文档文本或命令，不引入依赖。版本推进到 npm `0.2.0-rc.333` / Python `0.2.0rc333`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.332 - 2026-11-20

rc.332 源码候选为回合循环与流式终态补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_turn_stream.py`：固定 13 个通知名、`MAX_TOOL_ROUNDS` 与 300 秒审批默认值、请求偏移校验、恢复预算与循环守卫；工具批次上限先于续接与长度截断，截断与续接失败都不执行工具，四个固定错误码保持原样；重试事件成对且早于回合终态、输出预算计入与最终复核、`CONTEXT_OVERFLOW` 恢复资格、用量条目资格、终态 `failed` / `completed` 判定、摘要分页顺序与失败脱敏、模型结果默认字节上限。反向断言禁止中断时标成完成、`redact_secrets(str(exc))` 与未定义恢复标记。修复 Issue [#2789](https://github.com/can4hou6joeng4/boss-harness/issues/2789)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 60 个。版本推进到 npm `0.2.0-rc.332` / Python `0.2.0rc332`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.331 - 2026-11-20

rc.331 源码候选为 Node 宿主的连接代际与审批路由补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_host_connection.py`：固定连接状态集合与 `willRetry` 公式、初始化共享飞行与代际递增、断开先确认传输层已失败、初始化回执形状与 `initialized` 通知、`approval/respond` 的布尔裁决与代际归属、持久审批释放客户端待答槽位、`reconnect` 重置恢复预算、断开事件固定 `outcome: unknown` 与 `automaticReplay: false`；固定自动重连的 `supportsReconnect` 前提、次数上限与退避封顶、计时器 `unref()`；固定审批请求字段校验与重复 id 拒绝、300 秒默认期限、损坏期限回退、过去时间过期、2,147,483,647 毫秒计时上限与四条撤销路径。反向断言禁止 `String(params.status)`、自动重放与跳过审批清理。修复 Issue [#2787](https://github.com/can4hou6joeng4/boss-harness/issues/2787)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 59 个。版本推进到 npm `0.2.0-rc.331` / Python `0.2.0rc331`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.330 - 2026-11-20

rc.330 源码候选为 Node 侧进程传输客户端补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_client_transport.py`：固定 `shell: false` 与三条 pipe、8 MiB 单帧与 16 MiB 输入队列、30 秒请求超时与结果未知不自动重试、超时移除未发送帧、严格 UTF-8 解码与坏帧固定诊断、超限帧失败并 `dispose`；固定 result / error 二选一与非法错误帧 `-32603`、服务器请求 id 校验与 256 条待答上限、`-32601` / `-32603` 回包、失败清空四类状态并发出 `harness/disconnected`、`stdin.end` → `SIGTERM` → `SIGKILL` 关闭顺序。反向断言禁止 `shell: true`、继承 stdio、`console.*` 与诊断夹带帧内容。修复 Issue [#2785](https://github.com/can4hou6joeng4/boss-harness/issues/2785)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 58 个。版本推进到 npm `0.2.0-rc.330` / Python `0.2.0rc330`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.329 - 2026-11-20

rc.329 源码候选为 Anthropic Messages 适配器补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_anthropic_provider.py`：固定六项停止原因映射、含 `529` 的可重试状态、结构化结论优先与 `CONTEXT_OVERFLOW` 永不重试；固定凭据去空白与 `ANTHROPIC_API_KEY` 优先、纯空白视为未配置、请求头过滤与全凭据脱敏；固定 `message_stop` 后无事件、内容块索引与增量类型校验、思考签名单块 / 总量预算、工具标识 256 字符上限、工具参数完整结束与用量仅在双计数出现时上报；固定已产出内容后不再重试、清理未确认与共享恢复预算两条停止分支。反向断言禁止通用异常回显原始载荷、中断兜底抛出异常与直接解析原始参数。修复 Issue [#2783](https://github.com/can4hou6joeng4/boss-harness/issues/2783)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 57 个。版本推进到 npm `0.2.0-rc.329` / Python `0.2.0rc329`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.328 - 2026-11-20

rc.328 源码候选为 OpenAI Responses 适配器补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_openai_responses.py`：固定终态原因映射与顺序、文本 / 思考增量事件、可重试状态与网关过载标记；流内错误优先采用结构化结论且 `CONTEXT_OVERFLOW` 永不重试；固定输入条目形状与 `call_id` 配对、思考块不回放、用量缺失不伪造全零、空串 / 非法常量 / 非对象参数收敛；固定单次尝试 30 秒超时与零 SDK 重试、已产出内容后不再重试、清理未确认与共享恢复预算两条停止分支、工具调用标识 256 字符上限。反向断言禁止吞掉全部异常、直接解析原始参数与回放加密内容。修复 Issue [#2781](https://github.com/can4hou6joeng4/boss-harness/issues/2781)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 56 个。版本推进到 npm `0.2.0-rc.328` / Python `0.2.0rc328`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.327 - 2026-11-20

rc.327 源码候选为离线指令与默认领域提示补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_domain_tools.py`：固定七个只读指令的名称、工具与标题，`/search` 先拒绝空参数再调用 `boss_search`，`/candidates` 仅在有关键词时携带 `query`，以及业务 CLI 缺席与未配置模型两种降级文案；反向断言禁止把 `/search` 做成表项、指令表包含写工具或默认关键词。固定默认身份、`SYSTEM_PROMPT` 组合、14 个领域工具说明中的关键条目与审批 / 不自动重试 / 分页规则；`compose_system_prompt` 必须只替换身份、保留领域规则，并维持 16 KiB UTF-8 字节预算与控制字符拒绝。修复 Issue [#2779](https://github.com/can4hou6joeng4/boss-harness/issues/2779)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 55 个。版本推进到 npm `0.2.0-rc.327` / Python `0.2.0rc327`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.326 - 2026-11-20

rc.326 源码候选为模型可见的结果读取工具补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_model_tools.py`：固定 `read_session_tool_result` 的四字段模式与顺序、两个必需字段、禁止额外字段、`sha256` 仅 64 位小写十六进制、`limit` 引用共享字符常量；固定读取流程（参数校验 → 会话查找 → 缺失拒绝 → 条目形状 → 规范化正文 → 有界分段）与 64 KiB 整份载荷上限；固定三段错误映射顺序、`currentRef` 透传与固定错误码；反向断言禁止整份回灌、复制字符常量、允许额外字段。修复 Issue [#2777](https://github.com/can4hou6joeng4/boss-harness/issues/2777)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 54 个。版本推进到 npm `0.2.0-rc.326` / Python `0.2.0rc326`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.325 - 2026-11-20

rc.325 源码候选为模型重试配置与观测事件补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_retry.py`：固定 8 秒退避上限、默认 3 次与 500ms、1–10 次范围与空白 / 非整数 / 越界收敛；固定 Retry-After 优先且与指数退避同时封顶、毫秒头优先于秒头、空值与解析失败跳过；固定 `retry_start` / `retry_end` 的字段与失败 / 成功补发语义；反向断言禁止模块内睡眠、下标读取响应头与事件夹带内容。修复 Issue [#2775](https://github.com/can4hou6joeng4/boss-harness/issues/2775)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 53 个。版本推进到 npm `0.2.0-rc.325` / Python `0.2.0rc325`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.324 - 2026-11-20

rc.324 源码候选为 Codex 本地配置读数补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_codex_config.py`：固定显式入参 / `BOSS_HARNESS_CODEX_CONFIG` / `CODEX_HOME` / 默认路径的优先级、非普通文件与不可读及 TOML 语法错误的固定码、Python 3.10 缺 `tomllib` 的 `MODEL_CODEX_TOML_UNAVAILABLE`、profile 的模型 / provider / 端点要求、`wire_api` 去空白转小写与仅接受 `responses`、`Secret` 包装与 `env_key` 仅记录名称；反向断言禁止文本模式读取、写入与配置原文回显。修复 Issue [#2773](https://github.com/can4hou6joeng4/boss-harness/issues/2773)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 52 个。版本推进到 npm `0.2.0-rc.324` / Python `0.2.0rc324`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.323 - 2026-11-20

rc.323 源码候选为模型容量配置补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_capabilities.py`：固定 64 KiB / 128 项预算、三种 provider、两个必需字段与一个可选字段、七档推理集合；固定窗口大于 4096 且输出不超过窗口、只读覆盖表、重复键与非有限常量拒绝、逐项字段白名单与固定错误说明；反向断言禁止无钩子解析、原配置回显与可变覆盖表。修复 Issue [#2771](https://github.com/can4hou6joeng4/boss-harness/issues/2771)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 51 个。版本推进到 npm `0.2.0-rc.323` / Python `0.2.0rc323`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.322 - 2026-11-20

rc.322 源码候选为凭据包装与错误文本脱敏补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_secret.py`：固定三种凭据形态与 `<redacted>` 占位符、`Secret` 的槽位 / 非 dataclass / repr 与 str 共用占位符、`redact_secrets` 的空值短路、长度至少 6 的原值替换、Bearer 前缀保留与赋值形式键名保留；反向断言禁止 dataclass、明文 repr、第四种形态与改变占位符。修复 Issue [#2769](https://github.com/can4hou6joeng4/boss-harness/issues/2769)。
- 在技术参考补充凭据包装口径；接入 CI 的 Source build 与同名小节；检查脚本增至 50 个。版本推进到 npm `0.2.0-rc.322` / Python `0.2.0rc322`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.321 - 2026-11-20

rc.321 源码候选为 Anthropic 私有续接元数据补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_continuation.py`：固定 16 KiB 单项签名 / 96 KiB 签名合计 / 128 KiB 载荷 / 1 048 576 字符与 4096 块预算、前缀与内容 SHA-256、六字段精确匹配、调用 ID 连续前缀、助手引用与回合归属，拒绝被上下文编辑的助手消息与不可持久调用之后的内容；编码失败降级为普通工具批次。修复 Issue [#2767](https://github.com/can4hou6joeng4/boss-harness/issues/2767)。
- 在技术参考补充续接元数据口径；接入 CI 的 Source build 与同名小节；检查脚本增至 49 个。版本推进到 npm `0.2.0-rc.321` / Python `0.2.0rc321`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.320 - 2026-11-20

rc.320 源码候选为模型错误分类补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_errors.py`：固定配额 / 临时错误码与状态集合、LiteLLM 2048 与代理 512 字符上限、四条精确文本模式；溢出组合只接受 OpenAI 精确 code、有界 llama.cpp 文本、HTTP 400 的 LiteLLM 窗口拒绝、Anthropic 类型明确且带数字上限的 prompt 拒绝与 HTTP 413 的有界代理正文拒绝；固定配额不可重试、临时错误可重试、400/401/403 不可重试、未知 429 保持未知；传输诊断逐层去重并只输出白名单 errno；反向断言禁止宽松类型判定、`search` 代替完整匹配、放开 413 状态与异常原文。修复 Issue [#2765](https://github.com/can4hou6joeng4/boss-harness/issues/2765)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 48 个。版本推进到 npm `0.2.0-rc.320` / Python `0.2.0rc320`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.319 - 2026-11-20

rc.319 源码候选为异步模型流泵补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_stream_pump.py`：固定 64 个缓冲事件、4 MiB 合计缓冲、2 MiB 单事件、32768 个节点、8 个在途泵与 1 秒清理等待；固定入队前计费、终止事件独立槽位、先丢弃排队事件再取消任务、异步生成器 → 事件循环 → 名额 → 完成位的收尾顺序；反向断言禁止非 daemon 线程、严格编码计费、无超时 join。修复 Issue [#2763](https://github.com/can4hou6joeng4/boss-harness/issues/2763)。
- 在技术参考补充同步 provider 的流缓冲口径；接入 CI 的 Source build 与同名小节；检查脚本增至 47 个。版本推进到 npm `0.2.0-rc.319` / Python `0.2.0rc319`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.318 - 2026-11-20

rc.318 源码候选为模型输出的字节预算补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_output_budget.py`：固定工具参数、响应工具参数与文本 / 思考三项 1 MiB 上限、码点预检 → 编码 → 字节上限的顺序、紧凑 JSON 逐字符计费、64 层 / 32768 节点结构与整数位长预判、`bounded_error` 不拆 UTF-8 字符、`utf8_chunks` 最少 4 字节分块；反向断言禁止 NaN 序列化、ASCII 转义与无选项编码。修复 Issue [#2760](https://github.com/can4hou6joeng4/boss-harness/issues/2760)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 46 个。版本推进到 npm `0.2.0-rc.318` / Python `0.2.0rc318`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.317 - 2026-11-20

rc.317 源码候选为 JSON-RPC 边界补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_rpc.py`：固定 8 MiB 帧上限与 64 层 JSON 深度、重复键 / 非有限数值 / 孤立代理项拒绝、`surrogateescape` stdin、带文件名 `OSError` 的固定中文原因与 errno 名称、`redact_secrets(describe_failure(exc))` 脱敏、服务端请求计时器启动失败 fail closed、`-32010` / `-32603` 响应降级与编码失败不重跑 handler；反向断言禁止无钩子解析与 stdout 诊断。修复 Issue [#2759](https://github.com/can4hou6joeng4/boss-harness/issues/2759)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 45 个。版本推进到 npm `0.2.0-rc.317` / Python `0.2.0rc317`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.316 - 2026-11-20

rc.316 源码候选为回合模型请求上限补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_turn_limits.py`：固定默认 6 次与最大 64 次、精确整数与 1–宿主上限范围（拒绝布尔）、环境变量去空白与空值默认、最多两位十进制文本判定、转换失败与格式错误统一固定说明；反向断言禁止错误回显原值。修复 Issue [#2757](https://github.com/can4hou6joeng4/boss-harness/issues/2757)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 44 个。版本推进到 npm `0.2.0-rc.316` / Python `0.2.0rc316`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.315 - 2026-11-20

rc.315 源码候选为自动压缩策略补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_compaction.py`：固定六个字段与 provider 白名单、布尔 / 1–100 / 1–1000000 的精确类型与范围、codex → openai 归一化、model 与 effort 校验、`verified_policy` 的未知字段拒绝与字段顺序、`override` 只接受三个界面字段、`from_environment` 的空白处理 / 4096 字节上限 / 重复键钩子 / 未知字段拒绝与固定错误文本；反向断言禁止无钩子解析与错误回显原文。修复 Issue [#2755](https://github.com/can4hou6joeng4/boss-harness/issues/2755)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 43 个。版本推进到 npm `0.2.0-rc.315` / Python `0.2.0rc315`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.314 - 2026-11-20

rc.314 源码候选为状态目录独占锁补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_ownership.py`：固定 `.owner.lock` 的非阻塞独占 `flock`、两种失败分支先释放描述符再上报、固定 `EWOULDBLOCK` 说明、`close()` 先清字段再关描述符与 `__del__` 幂等复用；反向断言禁止删除锁文件、共享锁与无限期等待。修复 Issue [#2753](https://github.com/can4hou6joeng4/boss-harness/issues/2753)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 42 个。版本推进到 npm `0.2.0-rc.314` / Python `0.2.0rc314`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.313 - 2026-11-20

rc.313 源码候选为冻结快照存储补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_snapshot_store.py`：固定十项预算常量、快照库文本的宽容解码与条目损坏校验、构建取消、重复 id 与修订目标顺序、磁盘预算、临时文件原子发布与目录同步、缓存淘汰、叶失效墓碑与读取预算；反向断言禁止严格 `utf-8` 解码、裸 `unlink`、目录外删除与 NaN 序列化。修复 Issue [#2751](https://github.com/can4hou6joeng4/boss-harness/issues/2751)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 41 个。版本推进到 npm `0.2.0-rc.313` / Python `0.2.0rc313`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.312 - 2026-11-20

rc.312 源码候选为索引修复的清单与回滚补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_maintenance.py`：固定备份目录命名、清单的私有描述符与 dev/ino 复核、1 MiB 分块摘要、状态目录前置核对与占用锁顺序、移动前身份复核、`O_EXCL` 清单写入与 `fsync`、成功与失败路径的目录同步顺序、`failed-candidate` 与回滚、`finally` 释放占用锁；反向断言禁止删除原始记录、`json.dump` 流式写入与无界读取。修复 Issue [#2749](https://github.com/can4hou6joeng4/boss-harness/issues/2749)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 40 个。版本推进到 npm `0.2.0-rc.312` / Python `0.2.0rc312`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.311 - 2026-11-20

rc.311 源码候选为宿主工具桥的幂等清理补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_bridge_lifecycle.py`：固定 `BridgeLifecycle` 的 `RLock` 清理表、弱引用去重与死引用剔除、同一对象只清理一次、仅登记可弱引用对象、`close()` 优先与 `dispose()` 回退、锁外调用钩子，以及只记录异常类型名的清理日志；反向断言禁止重新抛出、记录堆栈或异常原文。修复 Issue [#2747](https://github.com/can4hou6joeng4/boss-harness/issues/2747)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 39 个。版本推进到 npm `0.2.0-rc.311` / Python `0.2.0rc311`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.310 - 2026-11-20

rc.310 源码候选为内核关闭的等待预算与中止线程所有权补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_shutdown.py`：固定 `TrackedAbort` 的只发信号语义（callback 优先、`request_abort` 回退、异常收敛、`finally` 收尾）、幂等收尾顺序（占锁判重 → 置位 → `done.set()` → `on_done()`）、一次性启动与线程启动失败只退休记账（绝不回退为内联 abort）、`join_until` 跳过未启动 / 当前线程 / 重复 worker 并以剩余期限 join；同时固定 runtime / application / connections 的最多两秒共享期限与「先取消派发、再各域等待」的关闭顺序。修复 Issue [#2745](https://github.com/can4hou6joeng4/boss-harness/issues/2745)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 38 个。版本推进到 npm `0.2.0-rc.310` / Python `0.2.0rc310`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.309 - 2026-11-20

rc.309 源码候选为自动压缩设置的持久化补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_settings.py`：固定 `config.json` 的 256 KiB / 深度 64 上限、基于私有描述符的 `S_ISREG` 读取与「上限 + 1 字节」判定、宽泛异常收敛为默认值、三个自动压缩字段完整性、拒绝覆盖不可读配置、`ensure_ascii=False` 与编码 / 超限错误、临时文件 + `fsync` + `os.replace` + 目录同步与异常清理；反向断言禁止 `read_text` / `write_text`。修复 Issue [#2743](https://github.com/can4hou6joeng4/boss-harness/issues/2743)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 37 个。版本推进到 npm `0.2.0-rc.309` / Python `0.2.0rc309`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.308 - 2026-11-20

rc.308 源码候选为 SQLite 投影索引补上静态检查，并加固顺序断言的首次出现语义。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_persistence.py`：固定 `SCHEMA_VERSION = 2`、`utf-8` 宽容解码（拒绝严格 `decode("utf-8")`）、1 → 2 迁移顺序与 `user_version` 写入、旧索引 `indexed_size=-1` 失效标记、私有目录与 WAL / SHM 权限、表结构主键与级联约束、逐操作连接与 `foreign_keys` / `busy_timeout` / `synchronous=FULL`、事务提交回滚与事件索引。修复 Issue [#2741](https://github.com/can4hou6joeng4/boss-harness/issues/2741)。
- 同时加固 `check_queue_view.py`、`check_task_ownership.py`、`check_usage.py`、`check_summary.py` 的 `_ordered`：此前按子序列匹配，提前插入的重复片段会被跳过；现在要求每个片段的首次出现位置严格递增。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 36 个。版本推进到 npm `0.2.0-rc.308` / Python `0.2.0rc308`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.307 - 2026-11-20

rc.307 源码候选为生命周期 hook 补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_hooks.py`：固定 30 秒 / 250ms 超时、256 事件队列、16 在途回调、观察上下文与策略上下文的字节 / 节点 / 深度上限、`HookDecision` 与 `ContextTransform` 校验、`_safe_value` 的截断与脱敏、`freeze_policy_context` 的环检测与代理项拒绝、事件投影白名单、取消优先于关闭与容量的顺序、策略与请求的 fail-closed 拒绝映射、`transform_context` 的当前单元保护、`after_tool_call` 只读契约与关闭期限；反向断言策略上下文不得走观察脱敏路径、事件投影不得直接使用原始参数。修复 Issue [#2739](https://github.com/can4hou6joeng4/boss-harness/issues/2739)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 35 个。版本推进到 npm `0.2.0-rc.307` / Python `0.2.0rc307`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.306 - 2026-11-20

rc.306 源码候选为摘要规划补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_summary.py`：固定 8 192 输出上限与 32 次请求上限、摘要器与分支摘要的执行状态 / 授权措辞、`wire_text` 降级与 SHA-256 来源摘要、4096 余量与 32 000 字符滚动预算、`ContextBudgetExceeded` 与超限拒绝、`tools=()` / `thinking=None` / `ensure_ascii=False`、逐字 `start:end` 切片与二分切分；反向断言来源不得从头截断。修复 Issue [#2737](https://github.com/can4hou6joeng4/boss-harness/issues/2737)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 34 个。版本推进到 npm `0.2.0-rc.306` / Python `0.2.0rc306`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.305 - 2026-11-20

rc.305 源码候选为工具结果信封补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_toolkit.py`：固定 `ToolResult` 七个字段与默认值、`snapshot_result` 的 JSON-only 值判定（拒绝 tuple / set / 非有限浮点 / 自定义对象）、64 层深度、错误信封的 `code` / `message` 校验、`recovery_action` 的 null 规范化与非字符串拒绝、`ensure_ascii=False` 的 JSON 往返深拷贝与统一 `ValueError` 收敛；反向断言禁止整份展开宿主返回值与 `ensure_ascii=True`。修复 Issue [#2735](https://github.com/can4hou6joeng4/boss-harness/issues/2735)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 33 个。版本推进到 npm `0.2.0-rc.305` / Python `0.2.0rc305`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.304 - 2026-11-20

rc.304 源码候选为 provider 用量汇总补上静态检查，并加固数值常量的整行锚定。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_usage.py`：固定 50 000 000 单次请求上限、两线路缓存语义与 `_REPORTED` 能力表、七类未验证原因与 `unreportedRequests` 只来自 `missing`、8 / 64 / 200 来源上限、50 条摘要任务窗口、`CACHE_MISS_FLOOR = 1024` 的日志视图估算、分支视图不报告 `cacheWaste`，以及费用恒为 `None` 的反向断言。修复 Issue [#2733](https://github.com/can4hou6joeng4/boss-harness/issues/2733)。
- 同时把 `check_queue_view.py` 与 `check_task_ownership.py` 的数值常量改为整行锚定：此前 `200` 改成 `2000`、`8` 改成 `800` 之类的后缀扩展会因前缀相同而通过静态检查。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 32 个。版本推进到 npm `0.2.0-rc.304` / Python `0.2.0rc304`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.303 - 2026-11-20

rc.303 源码候选为任务读取的所有权与恢复策略补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_task_ownership.py`：固定标识符整串匹配 `[A-Za-z0-9][A-Za-z0-9_-]{0,127}` 与 257 项快照上限、五个任务阶段与两类恢复枚举、`attempt` / `restartLimit` 范围、`_QUEUE_IDENTITY_FIELDS` 多快照冲突比对、`delivered_as` / `targets` 的多重证据条件、摘要关系的 `independent` 与 checkpoint 判定，以及 `recovery_policy` 对 `unknown` / 缺失状态的 `manual_review` 优先分支。反向断言标识符不得改用 `search`、用户消息引用不得投影正文。修复 Issue [#2731](https://github.com/can4hou6joeng4/boss-harness/issues/2731)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 31 个。版本推进到 npm `0.2.0-rc.303` / Python `0.2.0rc303`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.302 - 2026-11-20

rc.302 源码候选为队列读取投影补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_queue_view.py`：固定待处理项 200、已终结窗口 50、正文预览 600 字符、可选字符串与队列 id 200、技能 10 项与 2^53−1 安全整数上限；核对 `_QUEUE_VIEW_FIELDS` 逐字段白名单且禁止整份透传、`queue_record` 的 `kind` / `status` / `id` 校验与 `wire_value` 降级、`queue_view_record` 的可选字段收敛与暂停来源枚举、`project_queue` 的暂停优先排序、`inputTruncated` 标注与分类计数来源。修复 Issue [#2729](https://github.com/can4hou6joeng4/boss-harness/issues/2729)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 30 个。版本推进到 npm `0.2.0-rc.302` / Python `0.2.0rc302`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.301 - 2026-11-20

rc.301 源码候选为模型请求策略补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_request_policy.py`：固定拒绝载荷的七个上下文字段、`requestRejected` / `outputObserved` / `contextRecoveryEligible` 标记与 `request_policy` 来源、1 000 字符预览与 64 个工具名上限、两处拒绝原因的 `redact_secrets`、`model_error` 的 `recorded` 去重、整单元丢弃与最终请求的任务身份绑定。修复 Issue [#2727](https://github.com/can4hou6joeng4/boss-harness/issues/2727)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 29 个。版本推进到 npm `0.2.0-rc.301` / Python `0.2.0rc301`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.300 - 2026-11-20

rc.300 源码候选为请求身份补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_request_identity.py`：固定 `clientUserMessageId` 的 1–128 字符整串匹配、无效格式拒绝、持久链接的类型校验与两轮收敛、`queue_record` 共用契约、`CLIENT_REQUEST_CONFLICT` / `CLIENT_REQUEST_AMBIGUOUS` / `REQUEST_REQUIRES_REVIEW` 三类拒绝、UTF-8 输入摘要与持久事实一致性。修复 Issue [#2725](https://github.com/can4hou6joeng4/boss-harness/issues/2725)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 28 个。版本推进到 npm `0.2.0-rc.300` / Python `0.2.0rc300`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.299 - 2026-11-20

rc.299 源码候选为条目正文补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_item_content.py`：固定 64 KiB 内联阈值、16 384 / 32 768 分页常量、64 层投影深度与占位文本；孤立代理项替换为 U+FFFD、非有限浮点降级为 `None`、内联正文先经 `wire_text`；摘要按传输文本分块计算，`ic1_` 游标校验前缀、2048 上限、归属五元组与 offset 范围，过期引用返回带 `currentRef` 的 `STALE_CONTENT`。修复 Issue [#2723](https://github.com/can4hou6joeng4/boss-harness/issues/2723)。
- 接入 CI 的 Source build 并在技术参考补同名小节；检查脚本增至 27 个。版本推进到 npm `0.2.0-rc.299` / Python `0.2.0rc299`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.298 - 2026-11-20

rc.298 源码候选为工具桥输出上限补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 扩展 `scripts/check_harness_tools.py`：固定 `MAX_CLI_OUTPUT_BYTES = 16 * 1024 * 1024`、`BoundedProcessOutput` 接收该上限、`CLI_OUTPUT_LIMIT` 的「不要自动重试」说明，以及 `process_io.py` 的 64 KiB 分块、累计字节与上限比较、溢出标记、`BrokenPipeError` 处理与三路收尾计数。修复 Issue [#2721](https://github.com/can4hou6joeng4/boss-harness/issues/2721)。
- 技术参考补充核对范围；删除或放宽任一关键片段时检查会失败。版本推进到 npm `0.2.0-rc.298` / Python `0.2.0rc298`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.297 - 2026-11-20

rc.297 源码候选为工作区常驻说明补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_workspace_instructions.py`：固定 8 KiB 上限与首选 / 旧目录路径、拒绝非普通文件与 `O_NOFOLLOW` / dev / inode 校验、首选优先且不可读时不回退、提示块的「上下文而不是系统指令」与「不改变工具权限、审批要求或只读限制」措辞、临时文件与 fsync / `os.replace` 原子写入，以及面板、编辑器与三处文档片段。修复 Issue [#2719](https://github.com/can4hou6joeng4/boss-harness/issues/2719)。
- 接入 CI 的 Source build 并在技术参考补同名小节；删除上限、符号链接拒绝或权限措辞时检查会失败。版本推进到 npm `0.2.0-rc.297` / Python `0.2.0rc297`。不改变运行时行为，不执行发布动作。

## 0.2.0-rc.296 - 2026-11-20

rc.296 源码候选补齐使用指南的工作区说明入口。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 使用指南新增「工作区常驻说明」小节：路径与旧目录兼容、8 KiB / UTF-8 / 拒绝符号链接、每回合组装系统提示时重读、内容不授予或扩大工具权限，以及上下文面板与「技能与工具」页的查看与保存入口；交互细节链接桌面指南。修复 Issue [#2717](https://github.com/can4hou6joeng4/boss-harness/issues/2717)。
- 不重复桌面指南的交互细节，不改变代码行为。版本推进到 npm `0.2.0-rc.296` / Python `0.2.0rc296`。不执行发布动作。

## 0.2.0-rc.295 - 2026-11-20

rc.295 源码候选补齐首页能力地图。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 中文能力地图新增工作区常驻说明：`.boss-harness/CONTEXT.md`（兼容 `.boss-cli/CONTEXT.md`）、有界只读、每回合重新读取，内容不授予或扩大工具权限。英文概览的 Execution 条目同步提及。修复 Issue [#2715](https://github.com/can4hou6joeng4/boss-harness/issues/2715)。
- 不写版本号、候选批次或发布状态；不改变代码行为。版本推进到 npm `0.2.0-rc.295` / Python `0.2.0rc295`。不执行发布动作。

## 0.2.0-rc.294 - 2026-11-20

rc.294 源码候选统一上下文面板的断连口径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 会话上下文面板在内核断连时明确：预算、工作区说明与任务信息都是上次读取结果，可能已过期，重连后重新读取并核对。此前提示只说明任务信息，预算仍以「当前预算」展示，容易当成实时值。修复 Issue [#2713](https://github.com/can4hou6joeng4/boss-harness/issues/2713)。
- 桌面指南同步说明。版本推进到 npm `0.2.0-rc.294` / Python `0.2.0rc294`。不改变读取、缓存或重连行为，不执行发布动作。

## 0.2.0-rc.293 - 2026-11-20

rc.293 源码候选修正设置页的窗口提示状态。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 设置 →「上下文」进入刷新（分区切换、重连、重新读取）时先清空上下文窗口状态，读取成功后再写入；断连、读取失败或读取期间不再显示「当前模型的上下文窗口」提示，也不把上一轮的窗口当成当前模型。修复 Issue [#2710](https://github.com/can4hou6joeng4/boss-harness/issues/2710)。
- `scripts/check_context_keep.py` 增加「先清空、再按连接状态提前退出」的顺序断言；删除清空行或把清空移到提前退出之后都会使检查失败。
- 使用指南与桌面指南补充断连与重读期间不提示的说明。版本推进到 npm `0.2.0-rc.293` / Python `0.2.0rc293`。不改变内核接受范围或提示判定，不执行发布动作。

## 0.2.0-rc.292 - 2026-11-20

rc.292 源码候选补齐状态页的能力清单。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `docs/STATUS.md` 的「已具备」补充工作区常驻说明与业务 CLI 浏览器来源覆盖：前者有界、只读、每回合重新读取且不授予工具权限；后者只在启动阶段校验取值，不读取浏览器或 Cookie。措辞与使用指南、技术参考一致。[Issue #2708](https://github.com/can4hou6joeng4/boss-harness/issues/2708)
- 不改变版本声明、待完成范围或任何代码行为。版本推进到 npm `0.2.0-rc.292` / Python `0.2.0rc292`。不执行发布动作。

## 0.2.0-rc.291 - 2026-11-20

rc.291 源码候选为保留目标提示补上静态检查。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_context_keep.py`：判定函数 `keepTargetReachesLimit` 只能在 `compactionSettings.ts` 定义一次，保留目标与上限必须是正整数；会话上下文面板两处提示必须先确认预算已读取，设置页必须从内核能力投影取得窗口；使用指南与桌面指南的说明片段一并核对。脚本接入 `.github/workflows/build.yml`，技术参考补充说明小节。[Issue #2706](https://github.com/can4hou6joeng4/boss-harness/issues/2706)
- 在干净副本中删除设置页提示、把判定放宽到接受 0，脚本分别以退出码 2 拒绝。不改变运行时行为。版本推进到 npm `0.2.0-rc.291` / Python `0.2.0rc291`。不执行发布动作。

## 0.2.0-rc.290 - 2026-11-20

rc.290 源码候选把保留目标提示补到设置页。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 「设置 → 上下文」读取内核默认值时一并取得当前模型的上下文窗口；保留目标不低于该窗口时提示自动压缩通常没有更早的可压缩内容，压缩后也可能仍超出窗口。此前只有会话上下文面板有同类提示，而持久默认值在这个页面修改。[Issue #2704](https://github.com/can4hou6joeng4/boss-harness/issues/2704)
- 窗口缺失、非正整数或保留目标非正时不提示。判定与上下文面板共用一个纯函数，离线核验边界。不改变保存范围、压缩计划或内核行为。版本推进到 npm `0.2.0-rc.290` / Python `0.2.0rc290`。不执行发布动作。

## 0.2.0-rc.289 - 2026-11-20

rc.289 源码候选为上下文面板补充保留目标与输入预算不一致时的提示。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 自动压缩覆盖或手动规划的「近期保留目标」不低于当前模型输入预算时，上下文面板说明压缩后仍可能超出预算、达到阈值时通常没有更早的可压缩内容，并建议调低保留目标或新建会话。此前这种设置会静默地不产生摘要，直到溢出恢复也找不到可压缩内容。[Issue #2702](https://github.com/can4hou6joeng4/boss-harness/issues/2702)
- 判定逻辑放在渲染层纯函数中并离线核验边界：保留目标为 0、非整数、预算为 0 或非整数时不提示；相等时提示。不改变内核接受范围、压缩计划或自动压缩行为。版本推进到 npm `0.2.0-rc.289` / Python `0.2.0rc289`。不执行发布动作。

## 0.2.0-rc.288 - 2026-11-20

rc.288 源码候选修正审批期限与重试配置的空白判定。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_HARNESS_APPROVAL_TIMEOUT`、`BOSS_HARNESS_RETRY_ATTEMPTS`、`BOSS_HARNESS_RETRY_BASE_MS` 只含空白时按未设置处理，与其余环境变量口径一致；此前会被当成显式无效值，自检报 `APPROVAL_TIMEOUT_DEFAULTED` 或 `RETRY_CONFIG_DEFAULTED` 警告。生效值不变，都是默认值。[Issue #2700](https://github.com/can4hou6joeng4/boss-harness/issues/2700)
- 对 rc.287 离线对比：三个变量的纯空白取值由「无效并告警」改为「视为未设置」；空字符串、合法数字、非数字、非有限值、非正数与越界取值的结论保持一致。同步静态检查与文档。版本推进到 npm `0.2.0-rc.288` / Python `0.2.0rc288`。不执行发布动作。

## 0.2.0-rc.287 - 2026-11-20

rc.287 源码候选修复退出应用后手动配置自检进程残留的问题。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 确认退出应用时结束仍在运行的手动配置自检进程，尚未启动的不再启动；此前只有启动失败后的自动自检会被取消，卡住的手动自检会在应用退出后继续留在系统里。取消退出不影响在途自检，连续点击共用同一份结论的行为不变。[Issue #2698](https://github.com/can4hou6joeng4/boss-harness/issues/2698)
- 用不会自行结束的替身进程离线对比：按 rc.286 的调用方式，宿主退出后替身仍在运行；改动后已结束。同步静态检查与文档。版本推进到 npm `0.2.0-rc.287` / Python `0.2.0rc287`。不执行发布动作。

## 0.2.0-rc.286 - 2026-11-20

rc.286 源码候选修复 Python 3.10 上可选 Codex 配置阻断启动的问题。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 需要读取 Codex TOML 而当前解释器缺少解析器时，返回 `MODEL_CODEX_TOML_UNAVAILABLE`。OpenAI 若只是目录中的可选线路，会被跳过，默认线路照常启动；若明确选择该线路，启动和自检给出同一诊断码。完整显式 OpenAI 配置仍无需读取该文件。[Issue #2696](https://github.com/can4hou6joeng4/boss-harness/issues/2696)
- 用真实 Python 3.10 与 3.11 离线对比 rc.285：自动线路从启动退出 1 改为正常握手，独立摘要解析从未处理异常改为 `COMPACTION_MODEL_UNAVAILABLE`；3.11 解析合成 TOML 和 3.10 解析完整显式配置均保持可用。同步静态检查与文档。版本推进到 npm `0.2.0-rc.286` / Python `0.2.0rc286`。不执行发布动作。

## 0.2.0-rc.285 - 2026-11-20

rc.285 源码候选修正独立 Anthropic 摘要线路的可用性提示。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `context/read` 对另选的 Anthropic 摘要线路复用现有凭据判定：缺少非空环境凭据时返回 `summaryAvailable: false`，让桌面在开始前明确提示不可用；查看预算和整理计划不受影响。复用会话线路、独立 OpenAI 线路和实际摘要请求行为不变。[Issue #2694](https://github.com/can4hou6joeng4/boss-harness/issues/2694)
- 八种离线配置对比 rc.284：缺少凭据与纯空白两例不再误报，其余六例不变；空闲读取、输入预览和模拟活跃回合预算读取表现一致，未构造供应商或新增模型配置解析。同步静态检查与文档。版本推进到 npm `0.2.0-rc.285` / Python `0.2.0rc285`。不执行发布动作。

## 0.2.0-rc.284 - 2026-11-20

rc.284 源码候选修复桌面自动选择不可执行的虚拟环境解释器。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `.venv/bin/python` 仅在目标为普通文件且可执行时才作为桌面内核和自检的默认解释器，否则回退 PATH 上的 `python3`。显式 `BOSS_HARNESS_PYTHON` 优先级不变，也不会因路径无效而静默回退。[Issue #2692](https://github.com/can4hou6joeng4/boss-harness/issues/2692)
- 八例离线探针对比 rc.283：仅无执行权限的普通文件及指向它的符号链接由采用变为回退，其余六例不变。同步静态检查和解释器文档。版本推进到 npm `0.2.0-rc.284` / Python `0.2.0rc284`。不执行发布动作。

## 0.2.0-rc.283 - 2026-11-20

rc.283 源码候选统一快速开始和安装指南里的首次自检。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 首次自检显式选择 `--provider none`，与首次桌面启动使用同一线路；安装招聘 CLI 与平台登录留到需要招聘工具时。隔离安装探针验证：即使 shell 中的模型线路无效，新的首次自检也会按预期报告 `MODEL_DISABLED`，同时继续检查其他运行参数。启动行为不变。[Issue #2690](https://github.com/can4hou6joeng4/boss-harness/issues/2690)
- 版本推进到 npm `0.2.0-rc.283` / Python `0.2.0rc283`。不执行发布动作。

## 0.2.0-rc.282 - 2026-11-20

rc.282 源码候选统一回合模型请求数和附件存储上限的空白处理。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_HARNESS_MAX_MODEL_REQUESTS`、`BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_BYTES` 与 `BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_OBJECTS` 先去除首尾空白再校验。空值或只有空白时分别使用 6 次、512 MiB 和 4096 个对象的默认上限，不再因空占位行阻断启动；非空非法值仍明确失败。[Issue #2688](https://github.com/can4hou6joeng4/boss-harness/issues/2688)
- 十三例离线探针对比 rc.281：六例空白或带首尾空白的合法取值由拒绝改为生效，另外七例保持原结果；同一环境下自检「运行参数」由 `MAX_MODEL_REQUESTS_INVALID` 变为 `RUNTIME_OPTIONS_VALID`。新增静态守卫，在副本中分别还原两处旧写法均被拒绝。版本推进到 npm `0.2.0-rc.282` / Python `0.2.0rc282`。不执行发布动作。

## 0.2.0-rc.281 - 2026-11-20

rc.281 源码候选让两个 JSON 启动配置把空值或只有空白按未设置处理。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `ModelCatalog.from_environment` 与 `CompactionPolicy.from_environment` 在 JSON 解析前把空值或只有空白的 `BOSS_HARNESS_MODEL_LIMITS` / `BOSS_HARNESS_COMPACTION` 按未设置处理，使用内置默认；`autoCompactionSource` 也不再把空白占位行报告为 `environment`。此前 `.env` 空占位行会让「运行参数」自检报 `MODEL_LIMITS_INVALID` / `COMPACTION_CONFIG_INVALID`，内核构造随之失败。[Issue #2686](https://github.com/can4hou6joeng4/boss-harness/issues/2686)
- `check_startup_diagnostics.py` 新增 9 项守卫（空白判定先于 JSON 解析、来源判定不按变量是否存在），注入旧写法即失败。十一例解析探针对比 rc.280：仅两个空白取值共四例由 `ValueError` 变为内置默认，`{}`、带空白的合法 JSON、`null` 与无关键不变；同一环境下 `--check` 的「运行参数」结论由 `MODEL_LIMITS_INVALID` 错误变为 `RUNTIME_OPTIONS_VALID`。全部检查通过。版本推进到 npm `0.2.0-rc.281` / Python `0.2.0rc281`。不执行发布动作。

## 0.2.0-rc.280 - 2026-11-20

rc.280 源码候选让模型目录与摘要线路解析共用同一条 Anthropic 凭据规则。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `provider.py` 新增 `has_anthropic_credential`，自动线路判断、`_discover_model_configs` 与 `_compaction_model_config` 共用「两项凭据去除首尾空白后都为空即未配置」的判定。此前两处用原始真值判断：`ANTHROPIC_API_KEY` 只有空白时目录仍列出实际不可用的 anthropic 线路，摘要解析也通过，直到构造供应商才失败。[Issue #2684](https://github.com/can4hou6joeng4/boss-harness/issues/2684)
- `check_model_disable.py` 的守卫由 108 项增至 115 项，并禁止 `application.py` 直接读取凭据变量；注入旧写法即失败。七例探针（目录发现与摘要解析各三至四例）对比 rc.279：仅「纯空白 API_KEY」两例改变——目录由 `['anthropic', 'none']` 变为 `['none']`，摘要由解析出 anthropic 线路变为 `RpcError COMPACTION_MODEL_UNAVAILABLE`；有真实凭据与无凭据的其余各例一致。全部检查通过。版本推进到 npm `0.2.0-rc.280` / Python `0.2.0rc280`。不执行发布动作。

## 0.2.0-rc.279 - 2026-11-20

rc.279 源码候选让 Anthropic 凭据去除首尾空白后再交给 SDK。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `AnthropicProvider` 先对 `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` 去除首尾空白，只在非空时显式传给 SDK，并对 SDK 解析出的密钥与认证头同样去空白。此前粘贴密钥常见的尾随空格或换行会原样进入 `Authorization` 头导致认证失败；`ANTHROPIC_API_KEY` 只有空白时还会按 SDK 优先级遮蔽真实 `ANTHROPIC_AUTH_TOKEN`。[Issue #2682](https://github.com/can4hou6joeng4/boss-harness/issues/2682)
- `check_model_disable.py` 新增 10 项片段与 1 项禁止裸构造的守卫；恢复旧写法即失败。六例凭据探针（已安装 SDK、不联网）对比 rc.278：四种带空白与纯空白的组合由原样透传或 ValueError 遮蔽变为按去空白后的非空凭据构造，纯空白两项仍明确报「未配置可用凭据」，其余结果不变。全部检查通过。版本推进到 npm `0.2.0-rc.279` / Python `0.2.0rc279`。不执行发布动作。

## 0.2.0-rc.278 - 2026-11-20

rc.278 源码候选让桌面只把普通文件当作虚拟环境解释器。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 桌面主进程改用 `pythonFile.ts` 的 `isRegularFile` 判断 `.venv/bin/python` 是否可用：目录、断链与其他类型按不可用处理，回退 PATH 上的 `python3`。此前用 `existsSync`，残留目录会被当作解释器，内核与自检都以权限错误启动失败，界面只提示「未能启动 Python 解释器」；文件、指向文件的符号链接与缺失路径行为不变。[Issue #2680](https://github.com/can4hou6joeng4/boss-harness/issues/2680)
- `choosePythonInterpreter` 的第三个参数改名为 `venvUsable`，明确由调用方按文件类型判定。四例路径探针在 Node 24 下直接导入共享源码与新模块：仅目录一例由采用变为 `python3`，普通文件、断链与指向文件的符号链接结果不变。`check_desktop_security.py` 新增 4 项守卫（新模块判定片段、引入语句与禁止 `existsSync(venvPython)`），注入旧写法即失败。全部检查通过。版本推进到 npm `0.2.0-rc.278` / Python `0.2.0rc278`。不执行发布动作。

## 0.2.0-rc.277 - 2026-11-20

rc.277 源码候选让环境变量里的 `auto` 与命令行默认值同义。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `resolve_config` 在大小写与空白归一后把 `BOSS_HARNESS_PROVIDER=auto` 视为自动选择，与省略该变量一致；显式传入 `provider="auto"` 同样处理。此前复制的命令行写法会让启动与自检以 `MODEL_PROVIDER_UNKNOWN` 失败。真正拼错的值仍明确失败，`none`、`anthropic`、`openai`、`codex` 行为不变。[Issue #2678](https://github.com/can4hou6joeng4/boss-harness/issues/2678)
- 入口 `_requested_provider` 与 `resolve_config` 保持同一归一化口径。`check_model_disable.py` 新增 3 项守卫：`auto` 归一化片段、先归一再校验的顺序，以及入口的同一口径；恢复旧写法即失败。九例解析探针对比 rc.276 源码：四种 `auto` 写法由报错变为自动选择（有凭据时为 anthropic），其余五例一致；同一环境下 `--check` 从错误 `MODEL_PROVIDER_UNKNOWN` 变为警告 `MODEL_NOT_CONFIGURED`。全部检查通过。版本推进到 npm `0.2.0-rc.277` / Python `0.2.0rc277`。不执行发布动作。

## 0.2.0-rc.276 - 2026-11-20

rc.276 源码候选让业务 CLI 路径与数据目录共用同一套空白规范化。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `resolve_binary` 对 `BOSS_CLI_BIN` 与显式参数都去除首尾空白后再检查可执行性。此前带空白的有效路径直接查找失败并被跳过：本机没有其他来源时自检误报 `BOSS_CLI_UNAVAILABLE`，有其他来源时误报 `BOSS_CLI_BIN_IGNORED`，实际启动也改用另一份二进制。精确路径、空字符串、纯空白与不存在路径的行为不变。[Issue #2676](https://github.com/can4hou6joeng4/boss-harness/issues/2676)
- `check_harness_tools.py` 新增 6 项路径规范化守卫，恢复未去除空白的旧写法即失败。六例解析探针对比 rc.275 源码：环境变量与显式参数各一例带空白的有效路径由回退变为按去空白后的值采用，其余四例一致；同一环境下 `--check` 的「业务 CLI」结论由 `BOSS_CLI_UNAVAILABLE` 变为 `BOSS_CLI_FOUND`。全部检查通过。版本推进到 npm `0.2.0-rc.276` / Python `0.2.0rc276`。不执行发布动作。

## 0.2.0-rc.275 - 2026-11-20

rc.275 源码候选让桌面把空白的线路变量按默认 `openai` 处理。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 桌面主进程经 `@boss-harness/shared` 的 `chooseProviderOverride` 决定传给内核的 `BOSS_HARNESS_PROVIDER`：去除首尾空白后为空时使用默认 `openai`，非空时使用去空白后的值。此前用 `??` 直接读取，空字符串或纯空白会原样传给内核，内核按自动模式回退 `none`，桌面默认 OpenAI 线路被一行 `.env` 占位静默停用；`anthropic`、`none`、`codex` 与带空白的有效值行为不变。[Issue #2674](https://github.com/can4hou6joeng4/boss-harness/issues/2674)
- `check_desktop_security.py` 新增 5 项线路选择守卫：共享函数的三段写法、主进程的唯一调用点，以及禁止 `??` 直接读取。八例取值探针在 Node 24 下直接导入共享源码：未设置、空字符串与两种纯空白均得到 `openai`，带空白的 `anthropic` 按去空白处理，其余有效值不变。全部检查通过。版本推进到 npm `0.2.0-rc.275` / Python `0.2.0rc275`。不执行发布动作。

## 0.2.0-rc.274 - 2026-11-20

rc.274 源码候选让自动线路判断忽略只有空白的 Anthropic 凭据。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 未显式指定 provider 时，`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` 去除首尾空白后为空视为未配置，自动回退 `none`。此前只有空白的占位值被当作真实凭据，实际启动会构造 Anthropic 线路，而同一份配置的 `--check` 报 `MODEL_CONFIG_INCOMPLETE` 错误并建议配置凭据，两处结论互相矛盾；首个模型请求才会以认证失败告终。显式 `BOSS_HARNESS_PROVIDER=anthropic` / `none` 与带空白的真实凭据行为不变。[Issue #2672](https://github.com/can4hou6joeng4/boss-harness/issues/2672)
- `check_model_disable.py` 新增 4 项凭据规则守卫，恢复未去除空白的旧判定即失败。十例解析探针对比 rc.273 源码：三种纯空白凭据从 `anthropic` 变为 `none`，其余七例一致；同一环境下 `--check` 从错误 `MODEL_CONFIG_INCOMPLETE` 变为警告 `MODEL_NOT_CONFIGURED`，与实际确定性启动一致。全部检查通过。版本推进到 npm `0.2.0-rc.274` / Python `0.2.0rc274`。不执行发布动作。

## 0.2.0-rc.273 - 2026-11-19

rc.273 源码候选让桌面的 Python 解释器选择忽略空白取值。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 桌面主进程经 `@boss-harness/shared` 的 `choosePythonInterpreter` 选择解释器：`BOSS_HARNESS_PYTHON` 去除首尾空白后为空时按未设置处理，回退 `.venv/bin/python`，不存在则回退 `python3`；带首尾空白的路径按去空白后的值使用。此前用 `??` 直接读取，空字符串或空白会原样传给 `spawn` 并同步抛出 `ERR_INVALID_ARG_VALUE`，带空白的路径也会查找失败，整个桌面不可用且提示不指向解释器配置；内核与自检共用这一结论不变。未设置与有效路径的行为不变。[Issue #2670](https://github.com/can4hou6joeng4/boss-harness/issues/2670)
- `check_desktop_security.py` 新增 5 项解释器选择守卫：共享函数的三段写法、主进程的唯一调用点，以及禁止 `??` 直接读取。六例取值探针在 Node 24 下直接导入共享源码：未设置、空字符串与空白回退 `.venv`，缺少 `.venv` 时回退 `python3`，带空白的路径按去空白后的值使用，有效路径不变。全部检查通过。版本推进到 npm `0.2.0-rc.273` / Python `0.2.0rc273`。不执行发布动作。

## 0.2.0-rc.272 - 2026-11-19

rc.272 源码候选修正用户指南中与内核行为矛盾的运行参数说明。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 「其他运行参数」一节不再声称「使用默认值」或「收敛」的配置不在本地配置自检范围内：该句与同表的 `RETRY_CONFIG_DEFAULTED` / `APPROVAL_TIMEOUT_DEFAULTED` 警告列、检查项表以及内核 `_runtime_check` 的实际输出矛盾。改写为：审批期限与两项重试配置的无效取值不会让启动失败，自检以对应警告说明已回退或收敛。[Issue #2668](https://github.com/can4hou6joeng4/boss-harness/issues/2668)
- `check_startup_diagnostics.py` 新增 3 项守卫：恢复旧表述、或删除更正后的说明都会以非零退出码失败。本次仅改文档与守卫，协议与内核行为不变；全部检查通过。版本推进到 npm `0.2.0-rc.272` / Python `0.2.0rc272`。不执行发布动作。

## 0.2.0-rc.271 - 2026-11-19

rc.271 源码候选让 `BOSS_HARNESS_MAX_TOKENS` 的空白取值与空字符串一致。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_HARNESS_MAX_TOKENS` 去除首尾空白后为空时使用默认输出上限。此前空字符串视为未设置、只有空白却报 `MODEL_MAX_TOKENS_INVALID`；脚本或 `.env` 里的空格占位行会让启动失败，与同组 `BOSS_HARNESS_MODEL_REQUEST_TIMEOUT_SECONDS`、重试与审批期限变量的口径不一致。未设置、空字符串、合法正整数（含带首尾空白的写法）、`0`、负数与非数字的行为不变。[Issue #2666](https://github.com/can4hou6joeng4/boss-harness/issues/2666)
- `check_startup_diagnostics.py` 新增 4 项输出上限守卫，恢复未规范化读取即失败。七例解析探针对比 rc.270 源码：仅纯空白一例改变，其余六例一致。全部检查通过。版本推进到 npm `0.2.0-rc.271` / Python `0.2.0rc271`。不执行发布动作。

## 0.2.0-rc.270 - 2026-11-19

rc.270 源码候选让空白的默认状态目录变量按未设置处理。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_HARNESS_DIR` 或旧变量 `BOSS_CLI_HARNESS_DIR` 只有空白时，默认状态目录不再取名字是空白的路径：两个变量都去除首尾空白后判断，空白视为未设置并继续回退（旧变量、默认目录），有效取值不被改写。此前空白的新变量会跳过有效的旧变量，入口的空值校验以退出码 2 结束，提示却点名用户没有设置的 `--state-dir`，`--check` 也完全不可用，无法用自检定位。[Issue #2664](https://github.com/can4hou6joeng4/boss-harness/issues/2664)
- `check_startup_diagnostics.py` 新增 5 项默认状态目录守卫，恢复旧的 `or` 链即失败。六例子进程探针对比 rc.269 源码：两种变量取空白的三例从「退出码 2、错误提示」改为正常回退（其中新变量空白、旧变量在仓库内的一例正确报告 `STATE_DIRECTORY_IN_REPO`），其余三例一致。全部检查通过。版本推进到 npm `0.2.0-rc.270` / Python `0.2.0rc270`。不执行发布动作。

## 0.2.0-rc.269 - 2026-11-19

rc.269 源码候选让业务 CLI 数据目录与自检使用同一个规范化后的路径。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 工具桥读取 `BOSS_CLI_DATA_DIR`（或构造参数）时去除首尾空白，空值或仅含空白视为未设置、不传 `--data-dir`。此前只有空白的值会以 `--data-dir "   "` 原样传给上游，带首尾空白的路径也连空白一起传：上游实际使用的相对路径与 `--check` 去空白后核对的目录不同，仓库归属与重叠结论可能各说各话。[Issue #2662](https://github.com/can4hou6joeng4/boss-harness/issues/2662)
- `check_harness_tools.py` 新增 3 项数据目录规范化防护，恢复原样传参的写法即失败。四例取值探针对比 rc.268 源码：未设置与空字符串不变，仅空白改为不传参，带首尾空白的路径按去空白后的值传参。全部检查通过。版本推进到 npm `0.2.0-rc.269` / Python `0.2.0rc269`。不执行发布动作。

## 0.2.0-rc.268 - 2026-11-19

rc.268 源码候选让 `--check` 从被检查目录自身判断仓库归属。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `STATE_DIRECTORY_IN_REPO` 与 `BOSS_CLI_DATA_DIR_IN_REPO` 改为从状态目录、业务 CLI 数据目录各自向上查找 Git 仓库，工作目录在哪里不影响结论，提示文字改为「位于 Git 仓库内」。此前两项检查都只看当前工作目录所在的仓库：从仓库外启动自检、把 `--state-dir` 或 `BOSS_CLI_DATA_DIR` 指向另一个仓库内的目录时，两项都报通过，会话记录、工具结果、附件与登录态可能被提交进那个仓库而没有任何提示。[Issue #2660](https://github.com/can4hou6joeng4/boss-harness/issues/2660)
- `check_startup_diagnostics.py` 新增 2 项仓库归属守卫：两处检查都必须从目标目录自身向上查找，出现按当前工作目录判断的写法即以非零退出码失败。八例子进程探针（四种位置组合 × 状态目录与数据目录）对比 rc.267 源码：目标在另一仓库内的两例改为警告，其余六例一致。全部检查通过。版本推进到 npm `0.2.0-rc.268` / Python `0.2.0rc268`。不执行发布动作。

## 0.2.0-rc.267 - 2026-11-19

rc.267 源码候选按优先级选择首个非空模型值。最新公开预发布为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 依次检查 `--model`、`BOSS_HARNESS_MODEL` 和线路专属变量（`BOSS_HARNESS_OPENAI_MODEL` / `BOSS_HARNESS_ANTHROPIC_MODEL`），每项去除首尾空白后为空就继续检查下一项。OpenAI 线路在缺少显式配置时仍可用 Codex 配置补齐。此前空白的 `--model` 会覆盖有效的通用模型变量，纯空白的通用变量也会遮蔽线路专属模型，导致意外使用默认模型或读取不需要的 Codex 文件。正常启动和自检现在使用同一套规则。[Issue #2658](https://github.com/can4hou6joeng4/boss-harness/issues/2658)
- `check_model_disable.py` 新增模型值优先级检查。55 个离线场景覆盖两条线路的启动与自检，以及自动回退提示。rc.266 有 20 个场景不符合预期，修复后全部通过。源码版本推进到 npm `0.2.0-rc.267` / Python `0.2.0rc267`。

## 0.2.0-rc.266 - 2026-11-19

rc.266 源码候选让空的 `--state-dir` 不再把状态文件写进当前工作目录。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `--state-dir` 的值为空或只有空白时，自检、索引修复与正常启动现在都在执行任何动作前以退出码 2 结束，stderr 给出固定说明（省略该参数即使用默认状态目录），不创建任何文件。此前空字符串被当作当前工作目录：正常启动把占用锁、索引、`sessions/` 与附件目录直接写进工作目录，索引修复也在其中写入，只有空白的值则创建一个名字是空白的目录，而自检都报 `STATE_DIRECTORY_VALID`；这种取值常见于脚本中引用了未设置的变量。显式 `--state-dir .`、相对路径、绝对路径与省略参数的行为不变；环境变量为空时仍视为未设置。[Issue #2656](https://github.com/can4hou6joeng4/boss-harness/issues/2656)
- `check_startup_diagnostics.py` 的参数前置校验由 4 项增至 6 项，要求该校验位于自检与索引修复分支之前；删除校验的注入探针以退出码 2 失败。二十一例子进程探针（七种取值 × 启动、自检、修复）对比 rc.265 源码：空字符串与纯空白的六例改为前置拒绝且工作目录无新建条目，其余十五例的退出码、输出与新建条目数一致。全部检查通过。版本推进到 npm `0.2.0-rc.266` / Python `0.2.0rc266`。不执行发布动作。

## 0.2.0-rc.265 - 2026-11-19

rc.265 源码候选让索引修复不再往与内核无关的目录写入状态文件。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `boss-harness --repair-state` 指向存在、非空、但不含任何内核状态标志（占用锁、`sessions`、`state.sqlite3`）的目录时，现在不创建任何文件，以退出码 2 结束，stderr 给出固定说明并提示核对 `--state-dir` 或 `BOSS_HARNESS_DIR`，不回显路径。此前命令会在该目录中创建占用锁、空索引、`sessions/` 与备份目录并报告 `"repaired": true`；路径少写一级落到父目录时，其他目录被写入内核文件而真正的状态目录未被触碰。空目录、已使用的状态目录、索引文件已丢失的状态目录与只有 `sessions` 的目录仍可修复，输出不变。[Issue #2654](https://github.com/can4hou6joeng4/boss-harness/issues/2654)
- `check_private_files.py` 的修复前置核对由 5 项增至 9 项：新判断必须位于存在性核对之后、占用锁之前，标志集合固定。两类注入探针（把判断移到占用锁之后、放宽标志集合）均以退出码 2 失败。九例子进程探针对比 rc.264 源码：无关非空目录与只含隐藏文件的目录由新建 5 个条目并返回 0 变为不新建、返回 2；空目录、已用状态目录、索引丢失、仅 `sessions`、路径是文件、路径不存在、目录不可列七例的退出码、输出与新建条目数一致。全部检查通过。版本推进到 npm `0.2.0-rc.265` / Python `0.2.0rc265`。不执行发布动作。

## 0.2.0-rc.264 - 2026-11-19

rc.264 源码候选让索引修复不再在不存在的路径上新建状态目录。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `boss-harness --repair-state` 指向不存在的状态目录时，现在不创建任何文件或目录，以退出码 2 结束，stderr 给出固定说明并提示核对 `--state-dir` 或 `BOSS_HARNESS_DIR`，不回显路径。此前命令会逐级创建该路径，生成占用锁、空索引、`sessions/` 与备份目录，并输出 `"repaired": true` 与退出码 0；路径拼写错误或在另一个工作目录下使用相对路径时，看起来修复成功，真正需要修复的目录却未被触碰。状态目录存在时（含没有索引文件的空目录）行为与输出不变；正常启动仍按原规则创建缺失的状态目录。[Issue #2652](https://github.com/can4hou6joeng4/boss-harness/issues/2652)
- `check_private_files.py` 新增五项顺序核对：存在性核对必须先于占用锁与备份目录的创建；两类注入探针（把核对移到占用锁之后、删除核对）均以退出码 2 失败。六例子进程探针对比 rc.263 源码：绝对与相对两种缺失路径由新建 6 / 5 个条目并返回 0 变为不新建、返回 2；空目录、已使用的目录、路径是文件、父目录无权限四例的退出码、输出与新建条目数一致。实现中曾把父目录无权限误判为缺失，探针发现后收窄为只识别 `FileNotFoundError`。全部检查通过。版本推进到 npm `0.2.0-rc.264` / Python `0.2.0rc264`。不执行发布动作。

## 0.2.0-rc.263 - 2026-11-19

rc.263 源码候选让不受支持的 `--listen` 在自检与索引修复中也先失败。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 内核当前只支持 `--listen stdio://`。传入其他端点时，`--check`、`--repair-state` 与正常启动现在都在执行任何动作前以退出码 2 结束，stderr 给出同一条固定说明；自检不输出报告，索引修复不创建备份。此前只有正常启动校验该参数：相同参数下自检照常通过而启动必然失败，索引修复则带着无效参数继续改动状态目录。固定说明不再回显传入的端点值。默认值与显式 `stdio://` 的行为不变，桌面的启动与自检调用不受影响。[Issue #2650](https://github.com/can4hou6joeng4/boss-harness/issues/2650)
- `check_startup_diagnostics.py` 新增四项核对：端点校验与固定说明必须各出现一次，且位于自检与索引修复分支之前；把校验移回原位置的注入探针以退出码 2 失败。十二例子进程探针（三种端点 × 四种模式）对比 rc.262 源码：无效端点的自检两例与索引修复一例由继续执行变为退出码 2 且无报告、无备份，正常启动一例仅说明文字变化；受支持端点的八例退出码、输出字节数与备份结果一致。全部检查通过。版本推进到 npm `0.2.0-rc.263` / Python `0.2.0rc263`。不执行发布动作。

## 0.2.0-rc.262 - 2026-11-19

rc.262 源码候选让模型线路构造失败的 stderr 经过凭据脱敏。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 命令行启动时配置解析与模型线路构造的兜底分支此前把异常原文直接写到 stderr；原文若带有 `Bearer …`、`sk-…`、`api_key=…` 形态的文本或本地文件路径会被原样打印。现在入口的索引修复失败、启动失败、模型线路构造兜底与浏览器来源配置失败四处输出统一经过 `_failure_text`：带文件名的 `OSError` 改为固定中文原因，其余文本抹掉凭据形态。不含凭据形态与路径的说明文字不变，退出码仍为 2；具名 `ModelConfigError` 与缺包提示不变。脱敏按形态识别，不保证覆盖所有凭据格式。[Issue #2648](https://github.com/can4hou6joeng4/boss-harness/issues/2648)
- `check_protocol.py` 的错误脱敏守卫由 18 项增至 21 项，并禁止入口再出现把异常原文直接写到 stderr 的行；三类注入探针（兜底分支改回原文、辅助函数去掉脱敏、新增未脱敏输出行）均以退出码 2 失败。进程内探针用占位值替换线路构造函数，对比 rc.261 源码：`Bearer`、`sk-`、`api_key=` 与带文件名的 `OSError` 四例由原样回显变为脱敏或固定原因，普通说明一例输出不变。本机虚拟环境没有模型 SDK，未用真实 SDK 异常验证。全部检查通过。版本推进到 npm `0.2.0-rc.262` / Python `0.2.0rc262`。不执行发布动作。

## 0.2.0-rc.261 - 2026-11-19

rc.261 源码候选让本地配置自检提示状态目录位于仓库内。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 状态目录路径条件通过，且解析后等于或位于当前 git 工作区内时，`stateDirectory` 检查返回警告 `STATE_DIRECTORY_IN_REPO`，建议把 `--state-dir` 或 `BOSS_HARNESS_DIR` 移到仓库外；只读路径、不输出实际路径，警告不阻止启动。此前自检报通过，会话记录、工具结果与附件落在仓库中不会提示。路径条件失败时既有错误码仍优先；多个状态目录警告同时成立时按 `STATE_DIRECTORY_IN_REPO`、`STATE_DIRECTORY_TILDE`、`LEGACY_STATE_ENV_PRESENT`、`STATE_DIRECTORY_LOW_SPACE` 的顺序只报一个，因此仓库内的字面 `~` 路径与旧变量指向仓库内的情况现在先报本警告。[Issue #2646](https://github.com/can4hou6joeng4/boss-harness/issues/2646)
- `check_startup_diagnostics.py` 的警告顺序守卫新增上述三组先后关系；`SETUP.md` 检查结果表与使用指南同步。十一例子进程探针对比 rc.260 源码：仓库内绝对路径、相对路径、等于仓库根、子目录启动、环境变量指向仓库内由通过变为警告，仓库内字面 `~` 与旧变量两例改报本警告；仓库外、非 git 目录（含字面 `~`）与路径条件失败四例结果一致；自检未创建目录、输出不含实际路径。全部检查通过。版本推进到 npm `0.2.0-rc.261` / Python `0.2.0rc261`。不执行发布动作。

## 0.2.0-rc.260 - 2026-11-19

rc.260 源码候选让本地配置自检对 `--state-dir` 中的字面 `~` 也给出提示。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 实际使用的状态目录路径以字面 `~` 开头时，无论来自 `--state-dir` 还是环境变量，自检在路径条件通过的前提下报 `STATE_DIRECTORY_TILDE` 警告；说明与建议改为同时适用于两种来源。此前只识别环境变量形式：带引号或经不展开 `~` 的启动器传入 `--state-dir '~/…'` 时自检报通过，而正常启动会在工作目录下创建名为 `~` 的目录并把会话写入其中。正常启动行为不变，仍不展开 `~`。[Issue #2644](https://github.com/can4hou6joeng4/boss-harness/issues/2644)
- 八例子进程探针对比 rc.259 源码：`--state-dir` 为 `~/x` 与 `~` 由通过变为警告；两种环境变量形式仍为同一警告，仅说明文字变化；显式绝对路径加残留环境变量、普通绝对路径、中间含 `~` 的相对路径与路径条件失败（仍优先报 `STATE_DIRECTORY_NOT_DIRECTORY`）四例结果一致；自检未创建目录、输出不含实际路径。全部检查通过。版本推进到 npm `0.2.0-rc.260` / Python `0.2.0rc260`。不执行发布动作。

## 0.2.0-rc.259 - 2026-11-19

rc.259 源码候选让启动与索引修复失败的 stderr 不再回显系统错误原文与目录名。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 命令行启动失败与 `--repair-state` 失败遇到带文件名的 `OSError` 时，失败行改用与 JSON-RPC 错误相同的固定中文原因与 errno 名称（如「本地文件权限不足（EACCES），操作未完成。」）。此前输出英文系统错误原文并带出状态目录路径中的某一级名称（如 `[Errno 13] Permission denied: '<目录名>'`）。新增登记 `ENOTDIR`（路径中有一级不是目录）与 `ENOENT`（本地文件或目录不存在）两种原因，RPC 错误响应同样生效。退出码仍为 2，启动失败后的自检提示行不变，`ValueError` 的固定中文说明不变。[Issue #2642](https://github.com/can4hou6joeng4/boss-harness/issues/2642)
- `check_protocol.py` 的错误脱敏守卫扩展到入口两处失败输出与新增的两种 errno，由 14 项增至 18 项；三类注入探针（两处输出各改回异常原文、删除 `ENOTDIR` 登记）均以退出码 2 失败。子进程探针对比 rc.258 源码：状态目录为文件、父目录无权限、父目录只读三种情况在启动与修复两条路径下，新输出不含目录名；符号链接环的固定说明与正常修复输出不变。全部检查通过。版本推进到 npm `0.2.0-rc.259` / Python `0.2.0rc259`。不执行发布动作。

## 0.2.0-rc.258 - 2026-11-19

rc.258 源码候选把自检严格模式的退出码语义固化为静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_startup_diagnostics.py` 新增对 `__main__.py` 的核对：`--strict` 参数定义、与 `--check` 的绑定报错、报告先输出、错误优先返回 2、再按 `warning` 状态返回 1 的片段必须各出现一次且保持顺序；使用指南必须保留三种退出码的说明。此前 rc.257 的行为只有一次性探针。[Issue #2640](https://github.com/can4hou6joeng4/boss-harness/issues/2640)
- 四类注入探针确认守卫有效：删除绑定报错、把警告退出码改为 0、调换错误与警告的判断顺序、删除指南说明都会以退出码 2 失败并点名原因；未修改时守卫通过，读取路径由 8 条增至 9 条。不改变内核行为、协议与桌面界面。全部检查通过。版本推进到 npm `0.2.0-rc.258` / Python `0.2.0rc258`。不执行发布动作。

## 0.2.0-rc.257 - 2026-11-19

rc.257 源码候选让脚本可以把本地配置自检的警告视为未通过。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `boss-harness --check` 新增 `--strict`：存在错误仍返回退出码 2，没有错误但有警告返回 1，全部通过返回 0；只影响退出码，JSON 与文本报告内容、`ok` 字段含义不变，桌面主进程不使用该参数。`--strict` 只能与 `--check` 一起使用，单独使用时参数解析报错。显式 `--provider none` 本身产生 `MODEL_DISABLED` 警告，严格模式下返回 1。此前退出码不区分「通过」与「通过但有警告」，脚本只能自行解析报告。[Issue #2638](https://github.com/can4hou6joeng4/boss-harness/issues/2638)
- 子进程探针在仅警告与有错误两种真实环境、JSON 与文本两种格式下对比 rc.256 源码：不带 `--strict` 时退出码与输出逐字节一致，带 `--strict` 时输出不变、仅警告环境的退出码由 0 变为 1。本机虚拟环境没有模型 SDK，无法构造全部通过的真实环境，该分支用进程内替换报告的探针覆盖（三种报告 × 三种参数组合）。全部检查通过。版本推进到 npm `0.2.0-rc.257` / Python `0.2.0rc257`。不执行发布动作。

## 0.2.0-rc.256 - 2026-11-19

rc.256 源码候选补齐安装指南的检查码表并防止其与内核漂移。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `SETUP.md` 的检查结果表新增 `BOSS_CLI_DATA_DIR_IN_REPO` 与 `BOSS_CLI_DATA_DIR_OVERLAP` 两个业务 CLI 数据目录警告及处理建议。`check_startup_diagnostics.py` 新增对该表的核对：表内检查码必须由内核实际产出，`PREFIX_*` 通配至少匹配一个内核检查码，表不得缺失、为空或重复。此前该表只靠人工维护，内核改名或删除检查码后会静默残留。[Issue #2636](https://github.com/can4hou6joeng4/boss-harness/issues/2636)
- 四类注入探针确认守卫有效：写入不存在的检查码、无匹配的通配、改掉表头、重复检查码都会以退出码 2 失败并点名原因；未修改时守卫通过，读取路径由 7 条增至 8 条。不改变自检行为、协议与桌面界面。全部检查通过。版本推进到 npm `0.2.0-rc.256` / Python `0.2.0rc256`。不执行发布动作。

## 0.2.0-rc.255 - 2026-11-19

rc.255 源码候选让本地配置自检提示业务 CLI 数据目录位于仓库内。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 业务 CLI 可执行文件可用且数据目录与内核状态目录不重叠时，若 `BOSS_CLI_DATA_DIR` 解析后等于或位于当前 git 工作区内，`bossCli` 检查返回警告 `BOSS_CLI_DATA_DIR_IN_REPO`，建议把数据目录移到仓库外；只读路径、不输出实际路径，以 `~` 开头的值不展开也不参与判断，警告不阻止启动。此前只核对数据目录与状态目录是否重叠，登录态与平台缓存落在仓库中不会提示。[Issue #2634](https://github.com/can4hou6joeng4/boss-harness/issues/2634)
- 八例探针覆盖绝对路径、相对路径、等于仓库根、子目录启动、工作区外、非 git 目录、字面 `~` 与未设置，只有前四种报 `BOSS_CLI_DATA_DIR_IN_REPO`；数据目录同时与状态目录重叠时仍优先报 `BOSS_CLI_DATA_DIR_OVERLAP`，输出均不含实际路径。全部检查通过。版本推进到 npm `0.2.0-rc.255` / Python `0.2.0rc255`。不执行发布动作。

## 0.2.0-rc.254 - 2026-11-19

rc.254 源码候选把错误响应不回显本地路径固化为静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_protocol.py` 新增第十一类不变量：`rpc.py` 必须定义 `describe_failure` 并保留 `OSError` / 文件名判定、`errno.errorcode` 与通用说明；七个 errno（`ENOSPC`、`EDQUOT`、`EACCES`、`EPERM`、`EROFS`、`EMFILE`、`ENFILE`）的原因必须登记；未捕获异常的分发处必须调用 `redact_secrets(describe_failure(exc))`，不得再直接使用 `redact_secrets(str(exc))`。此前 rc.253 的行为只有一次性探针。[Issue #2632](https://github.com/can4hou6joeng4/boss-harness/issues/2632)
- 三类注入探针确认守卫有效：删除文件名判定、改回 `str(exc)`、删掉 `ENOSPC` 分支都会以退出码 2 失败并点名缺失内容；未修改源码时守卫通过，输出新增 14 项错误脱敏防护。全部检查通过。版本推进到 npm `0.2.0-rc.254` / Python `0.2.0rc254`。不执行发布动作。

## 0.2.0-rc.253 - 2026-11-19

rc.253 源码候选让 JSON-RPC 错误响应不再回显本地文件路径。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 未捕获异常的错误消息此前直接使用 `str(exc)` 脱敏后返回；带文件名的 `OSError` 会拼出本机绝对路径，磁盘写满、权限不足或只读文件系统导致会话 / 附件写入失败时，桌面提示可能显示该路径。现在这类错误改写为固定中文原因（`ENOSPC` 磁盘空间不足、`EDQUOT` 配额不足、`EACCES` 权限不足、`EPERM` 被拒绝、`EROFS` 只读、`EMFILE` / `ENFILE` 文件过多），附 errno 名称并去掉文件名；其他 errno 使用通用说明。无文件名的 `OSError`、`ValueError` 与 `RpcError` 的消息、错误码与 data 保持不变。[Issue #2630](https://github.com/can4hou6joeng4/boss-harness/issues/2630)
- 探针覆盖七种登记 errno、未知 errno、无文件名 `OSError`、`ValueError` 与 `RpcError`；再以子进程启动真实 `JsonRpcServer`，让处理器抛出带 `/Users/...` 路径的 `ENOSPC`，响应与 stderr 都不含该路径，`RpcError` 的错误码、消息与 data 不变。全部检查通过。版本推进到 npm `0.2.0-rc.253` / Python `0.2.0rc253`。不执行发布动作。

## 0.2.0-rc.252 - 2026-11-19

rc.252 源码候选增加供编码 Agent 与用户协作安装的本地指南。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增根目录 `SETUP.md`：按「核对工具链 → 安装内核与桌面依赖 → 运行 `--check` → 以 `none` 启动桌面 → 交由用户配置模型与平台登录 → 收尾核对」的顺序编写，每步给出可复制命令、预期结果与常见检查码对照；给 Agent 的约定要求一次只问一个问题、执行前说明影响、不读写凭据、不执行平台写操作、不调用真实模型试探、不修改用户 shell 配置。[Issue #2628](https://github.com/can4hou6joeng4/boss-harness/issues/2628)
- README 安装段落与贡献指南增加指向；`check_docs_links.py` 把 `SETUP.md` 纳入登记、相对链接与页内锚点核对，当前覆盖 17 篇 Markdown、214 个链接与 116 个页内锚点。全部检查通过。版本推进到 npm `0.2.0-rc.252` / Python `0.2.0rc252`。不执行发布动作。

## 0.2.0-rc.251 - 2026-11-19

rc.251 源码候选让本地配置自检在状态目录剩余空间不足时给出警告。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `stateDirectory` 检查在路径条件通过后读取状态目录或最近存在祖先所在文件系统的剩余空间；低于 512 MiB 时报 `STATE_DIRECTORY_LOW_SPACE` 警告并建议释放空间，不输出本机路径或确切字节，也不阻止启动。此前自检明确不核对磁盘空间，会话、索引与附件可能在中途写入失败。[Issue #2626](https://github.com/can4hou6joeng4/boss-harness/issues/2626)
- 无法读取文件系统信息、路径条件失败或无法定位已有祖先时保持原有检查码与结论；警告不改变报告 `ok` 与退出码 0。以 rc.250 合并提交导出的源码为基线，正常环境下两版 `stateDirectory` 的状态、检查码与说明一致，提示文案只移除已被覆盖的「未核对磁盘空间」；进程内替换 `shutil.disk_usage` 覆盖低于阈值、恰为阈值、读取失败三例，前例报警告、后两例保持通过，低空间下总体结论仍为通过并计入警告数。全部检查通过。版本推进到 npm `0.2.0-rc.251` / Python `0.2.0rc251`。不执行发布动作。

## 0.2.0-rc.250 - 2026-11-19

rc.250 源码候选把手动自检通道的进程执行边界固化为静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_desktop_security.py` 新增 `harness:startup-check` 处理器核对：箭头函数只声明 `event` 参数，目标取自模块级 `startupCheckTarget`，缺失时返回固定的 `spawn` 不可用结论，以 `manualStartupCheck ??=` 共用在途请求，先等 `diagnostics?.settled()` 再 `runStartupCheck(target)`；preload 与 `bridge.ts` 的 `runStartupCheck` 必须无参数，preload 只能以单个通道实参调用，渲染层调用点不得传参。此前只核对通道名配对与 `trustedSender` 入口。[Issue #2624](https://github.com/can4hou6joeng4/boss-harness/issues/2624)
- 六类注入探针确认守卫有效：给处理器加参数、改用渲染层传入的目标、删除在途去重、删除等待自动自检、给 preload 调用加实参、给渲染层调用加实参，都会以退出码 2 失败并点名文件与缺失内容；未修改源码时守卫通过，输出 175 项桌面防护核对。全部检查通过。版本推进到 npm `0.2.0-rc.250` / Python `0.2.0rc250`。不执行发布动作。

## 0.2.0-rc.249 - 2026-11-19

rc.249 源码候选把手动自检结论与内核文本结论的一致性固化为静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_startup_diagnostics.py` 从 `render_text` 的结论赋值提取中文片段，要求桌面 `startupConclusion` 全部包含；并核对缺失或不可用报告返回空串、错误与警告分别按 `error` / `warning` 状态计数；设置页必须使用该函数并展示「自检结论」「运行于」，复制时把不可用固定说明作为诊断内容。终端结论与设置页结论各写一份，此前只有一次性探针核对。[Issue #2622](https://github.com/can4hou6joeng4/boss-harness/issues/2622)
- 四类注入探针确认守卫有效：删除桌面结论片段、改设置页文案、改桌面计数条件、改内核结论文案都会以退出码 2 失败并点名文件与缺失内容；未修改源码时守卫通过，输出 342 项文本核对。全部检查通过。版本推进到 npm `0.2.0-rc.249` / Python `0.2.0rc249`。不执行发布动作。

## 0.2.0-rc.248 - 2026-11-19

rc.248 源码候选让启动自检核对推理强度与模型容量声明。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_HARNESS_MODEL_LIMITS` 为当前 provider/model 声明了非空 `reasoningEfforts`，而生效的 `BOSS_HARNESS_EFFORT` 属于全局七档、却不在声明范围内时，模型检查记为警告 `MODEL_EFFORT_UNSUPPORTED`，说明与容量声明不符、不会阻止启动但模型请求可能失败；不输出声明的档位或配置值。会话级推理强度本来会按声明拒绝，配置级此前没有提醒。[Issue #2620](https://github.com/can4hou6joeng4/boss-harness/issues/2620)
- 未声明档位、模型没有容量覆盖、未配置强度或强度属于声明范围时保持原有结果；容量配置本身无效时仍由运行参数检查报 `MODEL_LIMITS_INVALID`，不由模型检查抢先给出另一种结论。全局七档之外的取值仍使用原有说明。
- 以 rc.247 合并提交导出的源码为基线，十一个场景独立进程对比：声明包含、声明为空、无覆盖、其他模型、全局无效档位、未配置强度与 Anthropic 两例共九例逐字节一致；OpenAI 与 Anthropic 各一例声明不含当前强度时变为警告，退出码仍为 0；无效容量配置两版都以 `MODEL_LIMITS_INVALID` 和退出码 2 结束，模型检查保持通过。全部检查通过。版本推进到 npm `0.2.0-rc.248` / Python `0.2.0rc248`。不执行发布动作。

## 0.2.0-rc.247 - 2026-11-19

rc.247 源码候选让启动自检提示状态目录中的 `~` 不会展开。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_HARNESS_DIR` 或旧变量 `BOSS_CLI_HARNESS_DIR` 去除首尾空白后以 `~` 开头，且本次检查使用的正是该字面路径时，`stateDirectory` 检查记为警告 `STATE_DIRECTORY_TILDE`，说明内核按启动工作目录解析、不展开 `~`，建议改用绝对路径；不输出实际路径。桌面从仓库根启动时此前会在这里创建字面 `~` 目录。[Issue #2618](https://github.com/can4hou6joeng4/boss-harness/issues/2618)
- 显式 `--state-dir` 指向其他路径时不因残留环境变量报警；未设置、空值、非 `~` 开头或路径条件失败时保持原有结果，路径错误仍优先。旧变量本身以 `~` 开头时显示 `~` 警告而不是迁移提示。
- 以 rc.246 合并提交导出的源码为基线，十一个场景独立进程对比：未设置、绝对路径、相对路径、空值、显式覆盖与文件占位六例逐字节一致；四种 `~` 写法变为警告，退出码仍为 0；文件占位场景仍优先报告 `STATE_DIRECTORY_NOT_DIRECTORY` 并以 2 退出。报告不包含实际路径。全部检查通过。版本推进到 npm `0.2.0-rc.247` / Python `0.2.0rc247`。不执行发布动作。

## 0.2.0-rc.246 - 2026-11-19

rc.246 源码候选让手动配置自检结果显示总体结论与运行时间。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 设置页手动运行本地配置自检后，结果区显示与 `boss-harness --check --format text` 同口径的总体结论（「通过」「通过，N 项警告」「发现 N 个错误、M 项警告」）与本机运行时刻「运行于 HH:mm:ss」；结果到达时才记录时刻，新结果替换旧时间，结果不持久化，重新进入页面不显示虚构时间。不可用结果继续显示固定说明且不显示结论。[Issue #2616](https://github.com/can4hou6joeng4/boss-harness/issues/2616)
- 「复制结果」标题包含运行时刻与结论；不可用结果把界面上的固定说明一并复制。复制仍只含界面已展示字段。
- 以 rc.245 合并提交导出的源码为基线做纯函数探针：连接视图解析、自检行排序与复制文本逐例一致；新增结论行在通过、警告、错误、不可用与缺失九例上与内核文本结论一致。全部检查通过。版本推进到 npm `0.2.0-rc.246` / Python `0.2.0rc246`。不执行发布动作。

## 0.2.0-rc.245 - 2026-11-19

rc.245 源码候选让启动自检提示无效的推理强度与思考模式。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_HARNESS_EFFORT` 非空且不属于 `none` / `minimal` / `low` / `medium` / `high` / `xhigh` / `max` 时，模型检查记为警告 `MODEL_EFFORT_UNSUPPORTED`，说明无效值不阻止启动但模型请求可能失败，提示中列出可用取值而不回显原值。此前这类拼写错误要到回合内首个模型请求才暴露。[Issue #2614](https://github.com/can4hou6joeng4/boss-harness/issues/2614)
- Anthropic 线路下 `BOSS_HARNESS_THINKING` 非空且不是 `summarized` 时记为警告 `MODEL_THINKING_IGNORED`，说明该取值已被忽略；OpenAI 与 none 线路不因这个无关变量报警。检查顺序保持 SDK 缺失、端点明文风险、推理强度、思考模式，命中前面条件时仍优先报告。
- 以 rc.244 合并提交导出的源码为基线，十四个场景独立进程对比：未设置、`high` / `xhigh` 两个有效档位、空白取值、OpenAI 线路无效思考模式与 Anthropic 已识别或空白的思考模式七例逐字节一致；无效推理强度与 Anthropic 无效思考模式四例由 `MODEL_CONFIG_VALID` 变为对应警告，退出码仍为 0；SDK 缺失、端点明文风险与显式 `none` 三例仍优先报告原检查码，退出码不变。全部检查通过。版本推进到 npm `0.2.0-rc.245` / Python `0.2.0rc245`。不执行发布动作。

## 0.2.0-rc.244 - 2026-11-19

rc.244 源码候选让设置页可随时运行本地配置自检。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 「设置 → 模型与连接」新增「本地配置自检」行：可在任意连接状态运行与启动失败自检相同的只读命令，解释器、工作目录与环境沿用应用启动时的选择，渲染层不传参数；连续点击共用同一份在途结论，启动失败自检未结束时先等它退出，同一时刻只保留一个自检进程。运行中按钮禁用并显示进度；结果按「错误 → 警告 → 通过」列出名称、说明与检查码，报告带版本字段时显示内核、协议与 Python 版本，协议不一致时同样提示，超时、进程启动失败或输出不合规沿用固定说明；结果可复制为纯文本，新结论作废旧回执。[Issue #2612](https://github.com/can4hou6joeng4/boss-harness/issues/2612)
- 新增主进程通道 `harness:startup-check` 经 `trustedSender` 校验后返回固定字段结论，preload 只暴露无参数的 `runStartupCheck()`；桌面安全与启动自检静态守卫通过。以 rc.243 合并提交导出的源码为基线，纯函数探针逐例比较：连接视图解析、自检行排序、复制文本与不可用说明在重构前后一致；手动结果新增的报告版本行、协议不一致提示与旧组件内联表达式在报告、警告、不可用与缺失各例上一致。界面真实点击不在离线探针范围内，未运行 Electron 或真实模型。全部检查通过。版本推进到 npm `0.2.0-rc.244` / Python `0.2.0rc244`。不执行发布动作。

## 0.2.0-rc.243 - 2026-11-19

rc.243 源码候选让启动自检警告明文模型端点。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 显式模型端点写成 `http://` 且主机不是 `localhost`、`127.*` 或 `::1` 时，`--check` 的模型检查记为警告 `MODEL_ENDPOINT_INSECURE`，提示凭据可能以明文传输并建议改用 HTTPS；不输出端点、主机或路径，不发起请求，不构造 SDK。`https://`、本机回环、未写 scheme 与无法解析的端点保持原有结果；SDK 缺失、凭据缺失等错误仍优先报告。OpenAI Responses 与 Anthropic 线路共用该判断。使用指南与技术参考同步。[Issue #2610](https://github.com/can4hou6joeng4/boss-harness/issues/2610)
- 以 rc.242 合并提交导出的源码为基线，八个 OpenAI 场景独立进程对比：HTTPS、`127.0.0.1`、`localhost`、`::1`、未写 scheme 与畸形 IPv6 六例逐字节一致；远程 HTTP 与大写带根点主机两例变为警告，退出码仍为 0。补充 Anthropic 远程 HTTP 场景同样变为警告，SDK 缺失时两版均优先报告错误并以 2 退出。全部检查通过。版本推进到 npm `0.2.0-rc.243` / Python `0.2.0rc243`。不执行发布动作。

## 0.2.0-rc.242 - 2026-11-19

rc.242 源码候选让启动自检提示已弃用的状态目录变量。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `BOSS_CLI_HARNESS_DIR` 显式非空时，`--check` 的 `stateDirectory` 检查在路径条件通过的前提下记为警告 `LEGACY_STATE_ENV_PRESENT`，说明旧变量仍兼容、两者同时设置时以 `BOSS_HARNESS_DIR` 为准并建议迁移；未设置、仅设置新变量或旧变量为空时保持通过，路径条件失败时仍优先报告原有错误码。不创建目录、不读取目录内容、不输出路径。使用指南与技术参考同步。[Issue #2608](https://github.com/can4hou6joeng4/boss-harness/issues/2608)
- 以 rc.241 合并提交导出的源码为基线，六个场景独立进程对比：未设置、仅新变量、旧变量为空三例逐字节一致；仅旧变量与新旧同时设置两例由 `STATE_DIRECTORY_VALID` 变为警告，退出码仍为 0；旧变量加不可用路径仍优先报告 `STATE_DIRECTORY_NOT_DIRECTORY` 并以 2 退出。全部检查通过。版本推进到 npm `0.2.0-rc.242` / Python `0.2.0rc242`。不执行发布动作。

## 0.2.0-rc.241 - 2026-11-19

rc.241 源码候选固化文本自检结论与警告优先级的静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_startup_diagnostics.py` 用 AST 要求 `render_text` 的错误结论分支引用 `warnings`，防止「错误与警告并存时同时显示警告数量」被重构回退；并要求 `_runtime_check` 先报 `APPROVAL_TIMEOUT_DEFAULTED` 再报 `RETRY_CONFIG_DEFAULTED`、`_cli_check` 先报 `BOSS_CLI_UNAVAILABLE` 再报 `BOSS_CLI_BIN_IGNORED`，与使用指南写明的优先级一致。[Issue #2606](https://github.com/can4hou6joeng4/boss-harness/issues/2606)
- 在临时副本分别删除警告计数、调换两组警告顺序，守卫均以退出码 2 失败并点名原因；未修改副本通过（294 项）。`docs/STATUS.md` 的桌面自检描述补充错误与警告分列。全部检查通过。版本推进到 npm `0.2.0-rc.241` / Python `0.2.0rc241`。不执行发布动作。

## 0.2.0-rc.240 - 2026-11-19

rc.240 源码候选让文本自检在错误时同时显示警告数量。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `--check --format text` 的结论行在存在错误且有警告时改为「发现 N 个错误、M 项警告」，与同屏逐项状态一致；有错误无警告、仅警告、全部通过与空报告的文案不变，JSON 输出与退出码不变。使用指南与技术参考同步。[Issue #2604](https://github.com/can4hou6joeng4/boss-harness/issues/2604)
- README 快速开始在安装步骤后提示先运行 `.venv/bin/boss-harness --check` 核对本地配置，并注明该步骤不调用模型、不执行招聘 CLI。
- 以 rc.239 合并提交导出的源码为基线，六个报告场景独立进程对比：空报告、全部通过、仅警告、仅错误四例逐字节一致；一个错误加两项警告与两个错误加一项警告两例结论行变化。全部检查通过。版本推进到 npm `0.2.0-rc.240` / Python `0.2.0rc240`。不执行发布动作。

## 0.2.0-rc.239 - 2026-11-19

rc.239 源码候选让桌面启动失败提示条列出内核自检警告。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 自检没有错误但有警告时，桌面提示条在「未发现错误」之后列出各项警告的检查项名称、说明与检查码，并注明警告可能不影响启动；此前这些警告在桌面链路中完全不可见。无警告、存在错误与自检不可用三类文案保持逐字节不变，警告列表只使用已解析并校验的报告字段。[Issue #2602](https://github.com/can4hou6joeng4/boss-harness/issues/2602)
- 以 rc.238 合并提交导出的源码为基线，同一转译纯函数探针覆盖六个场景：无自检结论、无错误无警告、仅错误加警告、自检超时四例逐字节一致；一项警告与两项警告两例新增警告列表。桌面交互指南同步。全部检查通过。版本推进到 npm `0.2.0-rc.239` / Python `0.2.0rc239`。不执行发布动作。

## 0.2.0-rc.238 - 2026-11-19

rc.238 源码候选让启动自检暴露被忽略的 `BOSS_CLI_BIN`。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 显式设置 `BOSS_CLI_BIN` 却因目录、断链或不可执行被跳过、回退到并排虚拟环境或 PATH 时，`--check` 的 `bossCli` 检查记为警告 `BOSS_CLI_BIN_IGNORED`，说明已改用其他来源并提示核对路径与执行权限；只说明来源变化，不输出实际路径。最终没有可用 CLI 时仍优先报告 `BOSS_CLI_UNAVAILABLE`。未设置、空值与已采用的显式路径保持 `BOSS_CLI_FOUND`。使用指南与技术参考同步。[Issue #2600](https://github.com/can4hou6joeng4/boss-harness/issues/2600)
- 以 rc.237 合并提交导出的源码为基线，七个场景独立进程对比：未设置、有效显式路径、空值、仅显式路径可用、显式值无效且无其他来源五例逐字节一致；显式值无效与显式值为目录两例由 `BOSS_CLI_FOUND` 变为 `BOSS_CLI_BIN_IGNORED` 警告，退出码仍为 0。七例的 `resolve_binary()` 实际路径与来源逐项一致。静态守卫在补文档前以退出码 2 报缺少新检查码，补文档后通过（291 项）。全部检查通过。版本推进到 npm `0.2.0-rc.238` / Python `0.2.0rc238`。不执行发布动作。

## 0.2.0-rc.237 - 2026-11-19

rc.237 源码候选让启动自检暴露无效的模型重试配置。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 模型重试配置由 `retry_settings_from_environment` 统一解析，启动与 `--check` 共用，返回生效次数、基础退避与显式值是否原样生效：不是整数时回退默认值，`BOSS_HARNESS_RETRY_ATTEMPTS` 超出 1–10、`BOSS_HARNESS_RETRY_BASE_MS` 为负时收敛到边界；自检在审批期限有效时把「运行参数」记为警告 `RETRY_CONFIG_DEFAULTED`，说明实际处理方式，不输出原始值。未设置、空值与有效值保持通过，启动行为与退出码不变。使用指南与技术参考同步。[Issue #2598](https://github.com/can4hou6joeng4/boss-harness/issues/2598)
- 以 rc.236 合并提交导出的源码为基线，十个场景独立进程对比：未设置、空值、有效值三例仅提示补充「模型重试」措辞，状态、检查码与说明一致；两类非整数、两类越界/负数与两者同时无效共六例由 `RUNTIME_OPTIONS_VALID` 变为 `RETRY_CONFIG_DEFAULTED` 警告，退出码仍为 0；审批期限与重试同时无效时仍优先报告 `APPROVAL_TIMEOUT_DEFAULTED`。十例的 `retry_settings()` 实际次数与退避逐项一致。静态守卫在补文档前以退出码 2 报缺少新检查码，补文档后通过（285 项）。全部检查通过。版本推进到 npm `0.2.0-rc.237` / Python `0.2.0rc237`。不执行发布动作。

## 0.2.0-rc.236 - 2026-11-19

rc.236 源码候选让启动自检暴露无效的审批期限配置。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 审批期限由 `approval_timeout_from_environment` 统一解析，启动与 `--check` 共用：显式值不是数字、非有限值或不大于 0 时，启动仍回退默认 300 秒，自检在其余运行参数有效时把「运行参数」记为警告 `APPROVAL_TIMEOUT_DEFAULTED`，说明已回退默认值；未设置、空字符串与有效正数保持通过。只读取环境变量，不输出原始值。使用指南与技术参考同步。[Issue #2596](https://github.com/can4hou6joeng4/boss-harness/issues/2596)
- 以 rc.235 合并提交导出的源码为基线，七个场景独立进程对比：未设置、空字符串、有效 `120.5` 三例仅通过提示补充「审批期限」措辞，状态、检查码与说明一致；`abc`、`0`、`nan` 与纯空白四例由 `RUNTIME_OPTIONS_VALID` 变为 `APPROVAL_TIMEOUT_DEFAULTED` 警告，退出码仍为 0；七例的 `_approval_timeout()` 实际值与基线逐项一致（300 / 300 / 120.5 / 300 / 300 / 300 / 300）。在临时副本删除使用指南中的新检查码，静态守卫以退出码 2 失败。全部检查通过。版本推进到 npm `0.2.0-rc.236` / Python `0.2.0rc236`。不执行发布动作。

## 0.2.0-rc.235 - 2026-11-19

rc.235 源码候选让启动自检提示业务 CLI 数据目录与内核状态目录重叠。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 业务 CLI 可执行文件存在时，`--check` 将 `BOSS_CLI_DATA_DIR` 与状态目录解析后比较；相同或互相包含时 `bossCli` 检查记为警告 `BOSS_CLI_DATA_DIR_OVERLAP`，建议分别配置。只读路径，不创建目录、不执行 CLI、不输出完整路径；CLI 不可用时仍优先报告 `BOSS_CLI_UNAVAILABLE`。使用指南与技术参考同步。[Issue #2594](https://github.com/can4hou6joeng4/boss-harness/issues/2594)
- 以 rc.234 合并提交导出的源码为基线，七个场景独立进程对比：未设置、独立目录、CLI 不可用三例逐字节一致；相同、子目录、父目录与含 `..` 路径四例由 `BOSS_CLI_FOUND` 变为重叠警告，检查状态、说明与建议一致。文本与 JSON 输出均带新检查码；全部检查通过。版本推进到 npm `0.2.0-rc.235` / Python `0.2.0rc235`。不执行发布动作。

## 0.2.0-rc.234 - 2026-11-19

rc.234 源码候选让文本自检显示中文检查项名称。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `--check --format text` 每项标题改用内核 `_CHECK_TITLES` 的固定中文名称（如「模型配置（MODEL_DISABLED）」）；未登记名称仍回退内部名称。`--check` 帮助改为「输出脱敏报告（默认 JSON）」。`check_startup_diagnostics.py` 要求内核标题表与桌面 `CHECK_TITLES` 键值一致，标题文本也通过长度与控制字符校验。[Issue #2592](https://github.com/can4hou6joeng4/boss-harness/issues/2592)
- 以 rc.233 合并提交导出的源码为基线：默认 JSON 逐字节一致；文本输出仅五项标题行变化，其余逐字节一致；未登记名称回退探针通过。在临时副本分别改动内核与桌面标题，门禁均以退出码 2 失败。技术参考同步说明。全部检查通过。版本推进到 npm `0.2.0-rc.234` / Python `0.2.0rc234`。不执行发布动作。

## 0.2.0-rc.233 - 2026-11-19

rc.233 源码候选同步自检文本输出的技术参考并锁定渲染边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_startup_diagnostics.py` 用 AST 核对 `render_text`：只能按固定字段读取报告与检查项，不得访问环境、文件、进程或直接打印；`_STATUS_TEXT` 必须覆盖 ok / warning / error，并保留「说明」「建议」结构。技术参考同步说明默认 JSON 与 `--format text` 的分工、`_unconfigured_hint` 的三条常量与缺包分支；harness README 提及文本模式。[Issue #2590](https://github.com/can4hou6joeng4/boss-harness/issues/2590)
- 在临时副本注入三类违规（`os.environ`、未登记的报告字段、缺失状态标签），脚本均以退出码 2 失败并点名原因；未修改副本通过（255 项）。全部检查通过。版本推进到 npm `0.2.0-rc.233` / Python `0.2.0rc233`。不执行发布动作。

## 0.2.0-rc.232 - 2026-11-19

rc.232 源码候选为启动自检增加终端可读文本输出。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `--check` 新增 `--format text`：输出总体结论（含错误 / 警告计数）、内核 / 协议 / Python 版本，以及逐项状态、检查码、说明和建议；只使用自检报告字段，不读取环境或新增诊断。默认 JSON 与退出码不变，非 `--check` 使用该参数会明确报错。README 与使用指南同步说明，使用指南的恢复描述补上安装依赖后重新连接。[Issue #2588](https://github.com/can4hou6joeng4/boss-harness/issues/2588)
- 以 rc.231 合并提交导出的源码为基线：默认 `--check` 的 JSON 逐字节一致（1458 字节）；基线不认识 `--format text` 并以 2 退出，当前在显式 `none` 场景输出五项检查并以 0 退出；浏览器来源无效时两种格式都以 2 退出。全部检查通过。版本推进到 npm `0.2.0-rc.232` / Python `0.2.0rc232`。不执行发布动作。

## 0.2.0-rc.231 - 2026-11-19

rc.231 源码候选修正混合错误时的恢复建议。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 桌面提示条仅在自检报告的全部错误均为 `MODEL_SDK_UNAVAILABLE` 时，把安装内核依赖作为恢复建议；与其他错误并存时回到通用建议，逐条安装与修正提示仍由自检摘要列出。[Issue #2586](https://github.com/can4hou6joeng4/boss-harness/issues/2586)
- 以 rc.230 合并提交导出的源码为基线，同一转译纯函数探针覆盖十个场景：单个 / 全部 SDK 错误、仅其他错误、仅警告、无错误与 spawn / exit / 超时逐字节一致；SDK 与状态目录、SDK 与配置不完整两种混合错误由安装建议变为通用建议。桌面交互指南同步说明。全部检查通过。版本推进到 npm `0.2.0-rc.231` / Python `0.2.0rc231`。不执行发布动作。

## 0.2.0-rc.230 - 2026-11-19

rc.230 源码候选让自动回退提示核对 OpenAI 线路的模型 SDK。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 自动回退为 none 时，警告建议仅在 OpenAI 配置可解析且 `openai` 包可发现时点名该线路；配置可解析但缺少 `openai` 包时改为提示先安装内核依赖，不再建议用户切到自检自己会判定为不可用的线路。检查状态、检查码、说明与退出码不变。[Issue #2584](https://github.com/can4hou6joeng4/boss-harness/issues/2584)
- 以 rc.229 合并提交导出的源码为基线：伪造 `openai` 包存在（包内 `raise RuntimeError`，未被导入）与配置不可解析两例逐字节一致；缺包一例的建议由点名可用线路变为安装提示。`check_model_disable.py` 与 `check_startup_diagnostics.py` 登记第三条提示常量（82 项 / 240 项）。使用指南与技术参考同步说明。全部检查通过。版本推进到 npm `0.2.0-rc.230` / Python `0.2.0rc230`。不执行发布动作。

## 0.2.0-rc.229 - 2026-11-19

rc.229 源码候选让启动自检报告默认线路缺少模型 SDK。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `--check` 在模型配置可解析且凭据齐全后，用 `importlib.util.find_spec` 只发现默认线路所需的 `anthropic` / `openai` 包；缺失时报告 `MODEL_SDK_UNAVAILABLE`、退出码 `2`，建议按安装步骤安装内核依赖。只发现模块、不导入 SDK、不核对版本；显式 `none`、自动回退与配置不完整的分支不变。桌面提示条在报告点名该检查码时，恢复建议改为安装内核依赖后可重新连接。[Issue #2582](https://github.com/can4hou6joeng4/boss-harness/issues/2582)
- 以 rc.228 合并提交导出的源码为基线：Anthropic / OpenAI 缺 SDK 两例由 `MODEL_CONFIG_VALID`（退出码 0）变为 `MODEL_SDK_UNAVAILABLE`（退出码 2）；显式 `none`、自动回退、Anthropic 缺凭据与伪造 SDK 存在四例逐项一致，且伪造包内 `raise RuntimeError` 未被导入。同一转译纯函数探针覆盖四种恢复场景，只有 SDK 缺失的建议变化。使用指南与桌面交互指南同步说明。全部检查通过。版本推进到 npm `0.2.0-rc.229` / Python `0.2.0rc229`。不执行发布动作。

## 0.2.0-rc.228 - 2026-11-19

rc.228 源码候选在缺少内核依赖时给出安装提示。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 普通启动捕获 `ModuleNotFoundError` 时，stderr 点名缺失模块并给出 `uv pip install --python .venv/bin/python -e ./harness`，退出码仍为 `2`；`ModelConfigError` 与其它异常的既有文案不变。桌面自检报告没有错误项时，恢复建议先提示核对内核依赖是否已安装。[Issue #2580](https://github.com/can4hou6joeng4/boss-harness/issues/2580)
- 以 rc.227 合并提交导出的源码为基线：缺少 `anthropic` 包的启动提示由通用「模型配置不可用」变为安装提示；模型配置错误与深嵌套 Codex 配置的通用异常 stderr 逐字节一致。同一转译纯函数探针覆盖六种恢复场景，只有无错误报告（含仅警告）的建议变化。使用指南与桌面交互指南同步说明。全部检查通过。版本推进到 npm `0.2.0-rc.228` / Python `0.2.0rc228`。不执行发布动作。

## 0.2.0-rc.227 - 2026-11-19

rc.227 源码候选让启动失败提示标注检查项与检查码。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 桌面提示条的启动自检错误摘要为每条错误标注中文检查项名称与固定检查码，多个错误仍全部显示；未发现错误、仅有警告与自检不可用原因的文案不变。设置明细与「复制自检结果」保持不变。[Issue #2578](https://github.com/can4hou6joeng4/boss-harness/issues/2578)
- 用同一份转译后的纯函数探针对比主干与修改：两项错误场景新增「模型配置」「运行参数」与两个检查码，仅警告、未发现错误与超时三种场景逐字节一致。桌面交互指南同步说明。`npm run check`、`typecheck`、`build` 全部通过。版本推进到 npm `0.2.0-rc.227` / Python `0.2.0rc227`。不执行发布动作。

## 0.2.0-rc.226 - 2026-11-19

rc.226 源码候选让不完整模型配置的提示按线路给出凭据变量。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- Anthropic 线路缺少模型 id 或凭据时，`--check` 的 `MODEL_CONFIG_INCOMPLETE` 建议只说明非空模型 id 与 `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`，不再附带 OpenAI / Codex 说明；OpenAI 线路保留端点与有效 Codex profile 的建议。检查码、状态与退出码不变。[Issue #2576](https://github.com/can4hou6joeng4/boss-harness/issues/2576)
- 以 rc.225 合并提交导出的源码为基线，同一入口探针覆盖无凭据自动回退、显式 `none`、OpenAI 缺端点、Anthropic 缺凭据、运行参数无效与浏览器来源无效六个场景：只有 Anthropic 缺凭据的建议发生变化，其余检查项与退出码逐项一致。使用指南同步说明。`npm run check` 全部通过。版本推进到 npm `0.2.0-rc.226` / Python `0.2.0rc226`。不执行发布动作。

## 0.2.0-rc.225 - 2026-11-19

rc.225 源码候选核对自检运行参数顺序与应用启动顺序。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_startup_diagnostics.py` 按源码顺序收集 `ApplicationService.__init__` 中以 `from_environment` 结尾的读取调用，要求与 `_RUNTIME_OPTIONS` 的加载函数逐项一致。构造函数新增未登记读取，或自检表、启动读取被重排时失败，使 `--check` 报告的第一个错误与实际启动保持一致。[Issue #2574](https://github.com/can4hou6joeng4/boss-harness/issues/2574)
- 在临时副本注入自检表重排、启动新增读取与启动读取重排，脚本均以退出码 2 失败；复原后基线通过。技术参考同步更新；`npm run check` 全部通过。版本推进到 npm `0.2.0-rc.225` / Python `0.2.0rc225`。不执行发布动作。

## 0.2.0-rc.224 - 2026-11-19

rc.224 源码候选核对启动自检项名称、桌面标签与文档顺序。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_startup_diagnostics.py` 从 `startup_report()` 的检查列表解析内核实际输出顺序与名称，要求桌面 `connectionNotice.ts` 的 `CHECK_TITLES` 键按同一顺序一致，中文标签与使用指南「检查项」表格的行按同一顺序一致；内核新增、重命名或重排检查项而桌面或文档未跟进时失败。[Issue #2572](https://github.com/can4hou6joeng4/boss-harness/issues/2572)
- 在临时副本注入桌面缺标签、错序、错标签、内核合法重命名、文档错序与缺表头，脚本均以退出码 2 失败；复原后基线通过。技术参考同步更新；`npm run check` 全部通过。版本推进到 npm `0.2.0-rc.224` / Python `0.2.0rc224`。不执行发布动作。

## 0.2.0-rc.223 - 2026-11-19

rc.223 源码候选让启动自检守卫同时核对使用指南的检查码表。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `check_startup_diagnostics.py` 解析 `docs/USER_GUIDE.md` 的模型配置错误、目录错误与运行参数三张表：模型配置错误码与 `_DIAGNOSTICS` 键、目录错误码与 `_state_check` 的错误码、运行参数错误码与 `_RUNTIME_OPTIONS` 分别双向一致；同时确认内核可能输出的全部检查码（含模型配置诊断与运行参数动态来源）都出现在使用指南中。[Issue #2570](https://github.com/can4hou6joeng4/boss-harness/issues/2570)
- 在临时副本注入模型表删码、目录表残留码、主表缺少基础码与表头变化，脚本均以退出码 2 失败；复原后基线通过。技术参考同步更新；`npm run check` 全部通过。版本推进到 npm `0.2.0-rc.223` / Python `0.2.0rc223`。不执行发布动作。

## 0.2.0-rc.222 - 2026-11-19

rc.222 源码候选为启动自检文本与桌面解析上限增加静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_startup_diagnostics.py`：用 AST 核对 `startup_check.py` 每个 `_check(...)` 的名称、检查码、状态、文本长度（按桌面 UTF-16 码元计数）与控制字符，动态文本只允许来自已登记来源；核对 `_RUNTIME_OPTIONS`、`_DIAGNOSTICS`、`ModelConfigErrorCode` 与两条回退提示常量的一致性，并以文本片段核对桌面 `startupCheck.ts` 的解析防护与 `StartupCheckEntry` 协议字段。[Issue #2568](https://github.com/can4hou6joeng4/boss-harness/issues/2568)
- 在临时副本分别注入超长建议、小写检查码、未登记动态来源、诊断码集合不一致、桌面上限收紧与协议状态字段漂移，脚本均以退出码 2 失败；复原后基线与仓库检查通过。`Source build` 与技术参考同步登记。全部检查通过。版本推进到 npm `0.2.0-rc.222` / Python `0.2.0rc222`。不执行发布动作。

## 0.2.0-rc.221 - 2026-11-19

rc.221 源码候选修复自动回退提示中断自检的回归。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- rc.220 的自动回退提示会解析一次 OpenAI 线路；深嵌套的 Codex TOML 触发 `tomllib` 的 `RecursionError`，而提示函数只捕获 `OSError` / `TypeError` / `ValueError`，`--check` 以 Python 回溯退出且没有 JSON 输出。现在与启动配置解析一致，普通异常一律退回通用提示，中断与退出仍不捕获。以 rc.220 合并提交导出的源码为基线，同一深嵌套配置下基线 exit 1 且 stderr 有回溯；修复后 exit 0、输出 `MODEL_NOT_CONFIGURED` 与通用提示。显式 `openai`（`MODEL_CONFIG_INVALID`）、显式 `none`、正常 OpenAI 线路与无配置四种场景两侧一致。[Issue #2566](https://github.com/can4hou6joeng4/boss-harness/issues/2566)
- `check_model_disable.py` 断言捕获类型；全部检查通过。版本推进到 npm `0.2.0-rc.221` / Python `0.2.0rc221`。不执行发布动作。

## 0.2.0-rc.220 - 2026-11-19

rc.220 源码候选让自动回退 `none` 的自检提示点名已配置的 OpenAI 线路。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `--check` 自动模式回退 `none` 且本机存在可解析的 OpenAI 线路（Codex 配置或显式 `BOSS_HARNESS_OPENAI_*`）时，模型卡片的建议改为说明该线路并给出 `--provider openai`（桌面用 `BOSS_HARNESS_PROVIDER=openai`）的启动方式；解析失败、缺凭据或配置损坏仍保持原通用建议，显式 `none` 与无线路的结论不变。命令行 `--model` 与正常启动一样参与解析；自检仍不构造客户端、不联网，也不输出配置值。[Issue #2564](https://github.com/can4hou6joeng4/boss-harness/issues/2564)
- 真实入口探针覆盖自动线路可用、仅端点与凭据、Codex 配置缺模型、缺凭据、TOML 损坏、无配置与显式 `none` 七种场景：只有前两种可解析 OpenAI 线路的场景使用新提示，其余与基线一致。`check_model_disable.py` 新增对应断言。全部检查通过。版本推进到 npm `0.2.0-rc.220` / Python `0.2.0rc220`。不执行发布动作。

## 0.2.0-rc.219 - 2026-11-19

rc.219 源码候选整理桌面安全守卫的参考文档。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `docs/TECHNICAL_REFERENCE.md` 的 `check_desktop_security.py` 小节由单段改为按主题分组的列表：窗口隔离、权限与导航、preload 桥接、桥接类型、渲染层入口、进程边界、子进程、IPC 通道、发送方校验、外链与会话恢复。拆分前后 125 个代码跨度一一对应，未增删约束；最长段落由 3452 字符降到 559 字符。[Issue #2562](https://github.com/can4hou6joeng4/boss-harness/issues/2562)
- rc.208 条目中的 `ContextManager._compaction_snapshot()` 更正为 `ContextService._compaction_snapshot()`，与内核源码一致。全部检查通过。版本推进到 npm `0.2.0-rc.219` / Python `0.2.0rc219`。不执行发布动作。

## 0.2.0-rc.218 - 2026-11-19

rc.218 源码候选让线路不可用时的排队消息当场拒绝。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `queue/add` 为新建队列项解析会话线路，与 `turn/start` 共用同一校验：显式 `none` 下记录在真实线路上的旧会话、线路选择未定或线路不属于会话时，返回相同错误码与提示，不再先入队再以通用 `TURN_START_FAILED` 暂停。既有队列项的幂等返回与编辑、重试不变，`none` 线路会话仍可排队。[Issue #2560](https://github.com/can4hou6joeng4/boss-harness/issues/2560)
- 以 rc.217 合并提交为基线，同一真实入口离线探针对比修改前后：基线入队后暂停且只有 `queue/updated`，改动后当场返回 `MODEL_PROVIDER_UNAVAILABLE`、队列为空、无通知；`none` 线路会话与重复请求的幂等路径两种源码一致。全部检查通过。版本推进到 npm `0.2.0-rc.218` / Python `0.2.0rc218`。不执行发布动作。

## 0.2.0-rc.217 - 2026-11-19

rc.217 源码候选补齐首次试跑和启动故障诊断的步骤。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 说明从无模型试跑转到模型线路时如何重启。支持页及缺陷模板引导用户提供实际故障配置的自检结果；在临时目录通过真实 `--check` 入口确认覆盖 provider 会将 `MODEL_PROVIDER_UNKNOWN` 改成 `MODEL_DISABLED`。[Issue #2558](https://github.com/can4hou6joeng4/boss-harness/issues/2558)
- 全部检查通过。版本推进到 npm `0.2.0-rc.217` / Python `0.2.0rc217`。不执行发布动作。

## 0.2.0-rc.216 - 2026-11-19

rc.216 源码候选修正握手报告中的供应商选项。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `initialize.modelBridge` 在 `none` 与 `openai` 线路返回 `thinking: null` 和 `serverSideFallback: false`。Anthropic 继续返回生效选项；模型请求、配置解析和续接仍使用既有规则。TypeScript 协议类型补充两项已有字段。[Issue #2556](https://github.com/can4hou6joeng4/boss-harness/issues/2556)
- 同一离线探针对比 rc.215 与新源码的八个启动场景，五个 `none` 场景的误报消失，三个 Anthropic 或 OpenAI 对照的模型握手回执逐字段一致。全部检查通过。版本推进到 npm `0.2.0-rc.216` / Python `0.2.0rc216`。不执行发布动作。

## 0.2.0-rc.215 - 2026-11-19

rc.215 源码候选让连接检查区分显式禁用模型和默认线路回退。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `connection/read` 在进程以显式 `none` 启动时返回 `MODEL_DISABLED` 和重启提示。有招聘平台能力的工具组合同时提示 CLI 仍可运行。默认线路为 `none` 的两种情况均直接返回模型检查报告，自动回退沿用默认线路说明。[Issue #2554](https://github.com/can4hou6joeng4/boss-harness/issues/2554)
- 桌面「模型服务」卡片在状态行显示诊断码和重启提示；报告尚未读取或内核较旧时，从握手标志显示提示。静态守卫覆盖开关传递、构造约束、诊断码和检查线程的启动边界。
- 同一离线探针对比 rc.214 和新源码的八种启动场景。直接构造连接检查补测无平台能力的工具组合与非法线路，并用真实内核回执核对渲染层解析和提示。未做 Electron 窗口目视核对。全部检查通过。版本推进到 npm `0.2.0-rc.215` / Python `0.2.0rc215`。不执行发布动作。

## 0.2.0-rc.214 - 2026-11-19

rc.214 源码候选把进程级模型禁用状态暴露给客户端并让桌面区分「显式禁用」与「未配置」。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 握手 `initialize.modelBridge` 与 `config/read` 新增 `modelCallsDisabled` 字段：显式 `none` 启动时为 `true`，自动回退与真实默认线路为 `false`，两处取值恒一致。[Issue #2552](https://github.com/can4hou6joeng4/boss-harness/issues/2552)
- 桌面据此说明原因。显式 `none` 下 `model/list` 仍返回可选的 `none · none`，模型菜单并不为空，因此「进程以 none 线路启动，不调用模型；需要模型时改用具体 provider 重新启动」作为附注显示在选项之后；目录为空时同一句顶替「没有可用的本机模型线路」，预览模式不显示。连接设置「模型服务」卡片的描述行在显式禁用时点名原因，不再与「未配置默认线路」共用文案；「运行状态」概览新增「模型调用」一项，按 `config/read` 显示「已由进程禁用」「未被进程禁用」或「未提供」。握手缺该字段时（旧内核）模型菜单保持上一次取值，不把缺失当成新事实。
- 协议类型 `InitializeResponse.modelBridge` 与 `ConfigReadResponse` 补可选字段与注释；宿主状态 `modelBridge` 原样透传，主进程无需改动。菜单提示的取舍收进 `modelMenuHints` 纯函数，说明文案由模型菜单与连接设置共用同一常量。
- 以主干 rc.213 源码为基线的八场景离线探针（真实入口进程、占位凭据）核对修改前后：显式 none 的四种写法（`BOSS_HARNESS_PROVIDER=none`、大写 `NONE`、`--provider none`、`--provider none` 压过 `BOSS_HARNESS_PROVIDER=anthropic`）改动后两处字段均为 `true`；`--provider anthropic` 压过 `BOSS_HARNESS_PROVIDER=none`、真实默认线路与自动回退（有 OpenAI 显式端点 / 无任何凭据）为 `false`；每个场景两处取值一致，基线上字段不出现。渲染层的解析与提示函数由工作树源码转译后，以这八个场景的真实内核响应核对：四种显式 none 场景在 `none · none` 之后附注说明、卡片与概览点名，其余四个场景不显示；换成 rc.213 内核的响应时不显示说明、概览为「未提供」。未做 Electron 窗口目视核对。全部检查通过。版本推进到 npm `0.2.0-rc.214` / Python `0.2.0rc214`。不执行发布动作。

## 0.2.0-rc.213 - 2026-11-19

rc.213 源码候选把显式 `none` 收紧为禁用模型调用的进程级开关。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 此前显式 `none`（`--provider none` 或 `BOSS_HARNESS_PROVIDER=none`）只把默认线路设为 `none`：环境另有凭据时 `model/list` 仍列出其他线路并可在会话内选用，真实线路上的旧会话、续接与摘要仍会发起模型请求，而文档与 `--check` 的 `MODEL_DISABLED` 都描述为「已显式禁用模型调用」。[Issue #2550](https://github.com/can4hou6joeng4/boss-harness/issues/2550)
- 现在显式 `none` 是进程级开关：模型目录只保留 `none · none`，摘要线路不再独立解析，`summaryAvailable` 为 `false`；旧会话读上下文、发回合或续接以既有错误码拒绝并说明恢复办法，仍可切到 `none` 线路使用只读指令。自动回退得到的 `none` 语义不变，其他已配置线路仍可选；`--provider` 高于环境变量；`none` 线路自身的回合与招聘 CLI 调用不变。
- 行为影响：以显式 `none` 启动后不能再靠会话内切换使用其他线路，需改用具体 provider 重新启动；真实线路上的旧会话需在对应线路进程内继续，或在本进程切到 `none` 线路使用只读指令。桌面只经环境变量传线路，同一约束适用。
- `--provider` 帮助与 `MODEL_DISABLED` 处理建议按新语义改写；入口以 `_requested_provider` 单点归一化命令行与环境变量，启动自检与正式启动共用同一判定。`model_calls_disabled` 构造参数要求默认线路为 `none` 且不注入 provider 实例。
- 新增静态守卫 `check_model_disable.py`：模型供应商工厂在内核只经 `_provider_for` 调用、`build_provider` 只允许入口调用、provider 实例只在 `models/provider.py` 构造，并核对目录、摘要、续接与入口防护的先后顺序。
- 以主干 rc.212 源码为基线的 14 场景离线探针（替身模型端点与替身 CLI）核对修改前后：显式 none 的环境变量 / 命令行 / 大小写混写 / 优先级、无凭据、旧会话、续接、摘要线路、自动回退、真实默认线路与 `none` 线路自身回合全部符合预期，改动后零模型请求；显式 none 重启后旧会话排队消息与 `thread/fork` 未单独覆盖。使用指南与技术参考说明显式与自动回退的区别，`UPSTREAM.md` 记录与 Pi 模型目录职责的对照。全部检查通过。版本推进到 npm `0.2.0-rc.213` / Python `0.2.0rc213`。不执行发布动作。

## 0.2.0-rc.212 - 2026-11-19

rc.212 源码候选修正无模型线路在连接设置中被称为「离线」的问题。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 进程默认线路为 `none` 时，「设置 → 模型与连接」的「模型服务」卡片摘要由「当前为离线运行配置」改为「默认模型线路不调用模型；招聘 CLI 仍可运行并可能访问平台」，徽标由「离线配置」改为「未启用」。嵌入方未启用平台能力时，摘要只写「默认模型线路不调用模型」，不声称招聘 CLI 可用；此时「本机 CLI」与「BOSS 直聘账号」卡片的徽标同样显示「未启用」。[Issue #2548](https://github.com/can4hou6joeng4/boss-harness/issues/2548)
- 摘要限定为「默认模型线路」：卡片只描述进程默认线路，例如本机另有 Anthropic 凭据时，`model/list` 仍会列出该线路。使用指南的 `none` 说明补充这张卡片的呈现方式。
- 不改变协议字段、状态枚举、卡片的 `provider` / `model` 取值或连接检查行为。以主干源码为基线的离线探针核对了修改前后的三张卡片，全部检查通过。版本推进到 npm `0.2.0-rc.212` / Python `0.2.0rc212`。不执行发布动作。

## 0.2.0-rc.211 - 2026-11-19

rc.211 源码候选整理仓库首页与文档分工，不改变运行时行为。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 只保留定位、入口、启动步骤、安全边界与文档导航：不再枚举检查脚本与逐批修复细节，也不写具体版本号；已发布版本以 Releases 为准，逐版本变化只写在本文件。从首页移出的 `BOSS_HARNESS_STEERING_MODE` 与持久附件存储上限由使用指南的「其他运行参数」承接。[Issue #2546](https://github.com/can4hou6joeng4/boss-harness/issues/2546)
- 各检查脚本的核对范围只在技术参考的「构建前静态检查」维护一份，每个脚本一个同名小节；`scripts/check_docs_links.py` 新增守卫，要求脚本与小节一一对应。贡献约定、交付说明与状态页改为链接到该节。新增 `npm run check`，按文件名顺序运行全部静态检查，遇到第一个失败即停止并沿用其退出码。
- 贡献约定与交付说明把版本节奏写成两层：源码候选号随每个合入的交付 PR 递增并写入本文件，实际预发布聚合自上次发布以来的全部源码候选且需要单独授权。`UPSTREAM.md` 的 rc.210 小节移回文件标题之下；工具桥写作「以 argv 子进程调用 `boss-agent-cli`」，`none` 线路统一写作「不调用模型，仍可调用招聘 CLI，不等于离线」，`boss-harness --provider` 的帮助文案同步。
- 补做 rc.210 的离线核对：合入时的合成探针走的是首批领取路径，基线也不是 rc.209 源码。现以 rc.208、rc.209、rc.210 三份内核源码运行同一探针，让转向只由补领批次领取并在模型请求中途停止回合：rc.208 的续接请求不含该转向，rc.209 以 `CONTINUATION_STEERING_OUTSIDE_BOUNDARY` 拒绝续接，rc.210 在转向之后补写请求边界并带着该转向续接；rc.210 条目与 `UPSTREAM.md` 的验证表述据此更正。
- 不改变协议、工具权限或会话格式；守卫负向探针 11 例符合预期，全部检查通过。版本推进到 npm `0.2.0-rc.211` / Python `0.2.0rc211`。不执行发布动作。

## 0.2.0-rc.210 - 2026-11-19

rc.210 源码候选修复自动摘要期间补领转向缺少请求边界的问题。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `TurnRunner.run()` 汇总首批与摘要后补领的转向批次，提交后按最终请求指纹补写请求边界；中断续接不会把已投递的补领转向判为边界之外。[Issue #2544](https://github.com/can4hou6joeng4/boss-harness/issues/2544)
- 预算失败、压缩错误与请求拒绝仍保留原记录顺序；新增 `scripts/check_catchup_boundary.py` 与 CI 守卫。负向守卫验证旧条件会失败，全部检查通过；只有补领批次这条路径的修复前后对比在 rc.211 以 rc.209 源码为基线补做，见 rc.211 条目。版本推进到 npm `0.2.0-rc.210` / Python `0.2.0rc210`。不执行发布动作。

## 0.2.0-rc.209 - 2026-11-19

rc.209 源码候选修复中断续接可能丢失已投递转向消息的问题。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 转向提交后立即写入包含转向文本的 `context_budget` 与新的请求指纹，续接预检发现仍位于可验证边界之外的已投递转向消息时，明确返回 `CONTINUATION_STEERING_OUTSIDE_BOUNDARY`，不再静默丢输入。[Issue #2542](https://github.com/can4hou6joeng4/boss-harness/issues/2542)
- 离线合成探针覆盖预算同步与越界拒绝，修复前后行为均已验证；全部检查通过。版本推进到 npm `0.2.0-rc.209` / Python `0.2.0rc209`。不执行发布动作。

## 0.2.0-rc.208 - 2026-11-18

rc.208 源码候选统一自动压缩切点与回执的保留长度估算。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `ContextService._compaction_snapshot()` 让切点扫描与 `estimatedRetainedTokens` 共用同一可见尾部估算：已校准消息按用量增量、未校准消息按字符估算，排除的上下文编辑不再产生空消息开销；摘要来源集合与条目计数仍按原始记录计算。[Issue #2540](https://github.com/can4hou6joeng4/boss-harness/issues/2540)
- 离线合成探针覆盖旧用量锚点与排除消息场景，修复前后偏差与一致性均已验证；全部检查通过。版本推进到 npm `0.2.0-rc.208` / Python `0.2.0rc208`。不执行发布动作。

## 0.2.0-rc.207 - 2026-11-18

rc.207 源码候选澄清自动压缩保留目标的估算口径与边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 使用指南与技术参考明确 `keepRecentTokens` 是 token 口径的预算估算而非精确 tokenizer 结果：可信 `model_usage` 前缀优先校准，否则按字符保守估算；切点只落在完整回合边界，当前运行回合及已被摘要覆盖的来源不重复摘要。[Issue #2538](https://github.com/can4hou6joeng4/boss-harness/issues/2538)
- 不改变运行时行为或工具权限；文档链接与版本一致性检查通过。版本推进到 npm `0.2.0-rc.207` / Python `0.2.0rc207`。不执行发布动作。

## 0.2.0-rc.206 - 2026-11-18

rc.206 源码候选为搜索片段与桌面高亮增加专项静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_search_snippet.py` 并接入 CI：核对命中区间原样保留、两侧空白折叠、预算不足时优先保留命中词，以及桌面内核归一化高亮与 `hit.snippet` 调用链，共 24 项防护。[Issue #2536](https://github.com/can4hou6joeng4/boss-harness/issues/2536)
- 负向探针覆盖命中折叠、预算归零与高亮标记移除；全部检查通过。版本推进到 npm `0.2.0-rc.206` / Python `0.2.0rc206`。不执行发布动作。

## 0.2.0-rc.205 - 2026-11-18

rc.205 源码候选为审批裁决路径增加专项静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_approval.py` 并接入 CI：核对审批字段白名单、活动 runner 归属与持久回调、会话层重复决策 / 归档 / 过期 / owner 约束以及启动过期回收，共 47 项防护。[Issue #2534](https://github.com/can4hou6joeng4/boss-harness/issues/2534)
- 负向探针覆盖字段校验、active turn owner 与过期判定变异；全部检查通过。版本推进到 npm `0.2.0-rc.205` / Python `0.2.0rc205`。不执行发布动作。

## 0.2.0-rc.204 - 2026-11-18

rc.204 源码候选为连接报告字段投影增加专项静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_connection_report.py` 并接入 CI：核对内核报告源、`connection/read` / `connection/check` 路径、协议字段与渲染层白名单（状态、浏览器来源、认证状态与有界文本）共 51 项防护。[Issue #2532](https://github.com/can4hou6joeng4/boss-harness/issues/2532)
- 负向探针覆盖认证状态白名单、三卡完整性与报告读取路径变异；全部检查通过。版本推进到 npm `0.2.0-rc.204` / Python `0.2.0rc204`。不执行发布动作。

## 0.2.0-rc.203 - 2026-11-18

rc.203 源码候选补齐专项守卫的技术参考。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `docs/TECHNICAL_REFERENCE.md` 增补 `queue/steer`、循环提醒、浏览器来源与连接生命周期四份静态守卫的核对对象、关键不变量与扫描局限，贡献者可据此判断每项检查能保证什么。[Issue #2530](https://github.com/can4hou6joeng4/boss-harness/issues/2530)
- 不新增运行时行为或工具权限；版本推进到 npm `0.2.0-rc.203` / Python `0.2.0rc203`。不执行发布动作。

## 0.2.0-rc.202 - 2026-11-18

rc.202 源码候选为连接检查生命周期增加专项静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_connection_lifecycle.py` 并接入 CI：核对模型检查的取消 / 中止线程所有权、超时与状态迁移、CLI / 平台桥接释放、空闲回收与关闭等待顺序，共 50 项防护。[Issue #2528](https://github.com/can4hou6joeng4/boss-harness/issues/2528)
- 负向探针覆盖归属判断弱化、终态提前退休与关闭等待删除；全部检查通过。版本推进到 npm `0.2.0-rc.202` / Python `0.2.0rc202`。不执行发布动作。

## 0.2.0-rc.201 - 2026-11-18

rc.201 源码候选为浏览器来源覆盖增加专项静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_browser_source.py` 并接入 CI：核对 `BOSS_HARNESS_BROWSER_SOURCE` 的严格白名单、规范化与空值回退、`--browser-source` 参数构造、启动自检码、连接报告与桌面展示共 27 项防护。[Issue #2526](https://github.com/can4hou6joeng4/boss-harness/issues/2526)
- 负向探针覆盖空值回退、规范化、参数传递与连接报告投影；全部检查通过。版本推进到 npm `0.2.0-rc.201` / Python `0.2.0rc201`。不执行发布动作。

## 0.2.0-rc.200 - 2026-11-18

rc.200 源码候选为重复同参工具调用提醒增加专项静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_loop_guard.py` 并接入 CI：核对提醒阈值、规范化 SHA-256 摘要、参数上限与回退、纯内存状态，以及 `agent.py` 在工具结果后且有下一次模型请求时才注入的边界，共 32 项防护。[Issue #2524](https://github.com/can4hou6joeng4/boss-harness/issues/2524)
- 负向探针覆盖阈值改写、提醒越界与观察位置漂移；全部检查通过。版本推进到 npm `0.2.0-rc.200` / Python `0.2.0rc200`。不执行发布动作。

## 0.2.0-rc.199 - 2026-11-18

rc.199 源码候选为 rc.198 的 `queue/steer` 增加专项静态守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_queue_steer.py` 并接入 CI：核对 `_save` 原子转换、active turn / `expectedTurnId` 守卫、覆盖选项拒绝、协议 / 主进程白名单 / 桌面按钮边界，共 28 项防护。[Issue #2522](https://github.com/can4hou6joeng4/boss-harness/issues/2522)
- 负向探针覆盖状态、技能与回合守卫失效及非持久转换；全部检查通过。版本推进到 npm `0.2.0-rc.199` / Python `0.2.0rc199`。不执行发布动作。

## 0.2.0-rc.198 - 2026-11-18

rc.198 源码候选支持把排队消息原子转为当前回合。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `queue/steer` 与 `queueSteer` 能力：只在当前回合存在且 `expectedTurnId` 匹配时，把 `queued` 的 follow-up 在同一条队列记录上改为 steering，保留 id / 正文 / 请求编号，不产生重复队列项。[Issue #2520](https://github.com/can4hou6joeng4/boss-harness/issues/2520)
- 带 `skillIds` 或自动压缩覆盖的项明确拒绝；桌面队列面板增加「转为当前回合」按钮，无运行回合、断连或批量操作时禁用并说明原因。
- 状态机探针覆盖成功转换、错误回合、覆盖选项拒绝与注入落库；全部检查通过。版本推进到 npm `0.2.0-rc.198` / Python `0.2.0rc198`。不执行发布动作。

## 0.2.0-rc.197 - 2026-11-18

rc.197 源码候选加固版本元数据校验。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_versions.py` 的 `tool.hatch.build.targets.wheel` 读取改为逐层类型判断；嵌套配置被改成字符串或列表时返回受控的 `ValueError`，不再抛 `AttributeError`。[Issue #2518](https://github.com/can4hou6joeng4/boss-harness/issues/2518)
- 负向探针覆盖 `build` 与 `targets` 非映射及合法配置对照；全部检查通过。版本推进到 npm `0.2.0-rc.197` / Python `0.2.0rc197`。不执行发布动作。

## 0.2.0-rc.196 - 2026-11-18

rc.196 源码候选增加重复同参工具调用提醒。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `loop_guard.py`：只在单次回合内存中观察连续同名同参调用，第 3、5 次命中时追加一条合成用户提醒；不阻断执行、不新增 RPC / 工具 / 协议 / 持久化条目，并在 steering 注入、超大或不可序列化参数时重置。[Issue #2516](https://github.com/can4hou6joeng4/boss-harness/issues/2516)
- 假 provider / 假 handler 行为探针核对第 4、5 次请求各见 1 条提醒、不同参数与 steering 重置、6 次工具调用均实际执行；README、技术参考、状态说明与发布约定同步。版本推进到 npm `0.2.0-rc.196` / Python `0.2.0rc196`。不执行发布动作。

## 0.2.0-rc.195 - 2026-11-18

rc.195 文档候选刷新项目定位与社区介绍草稿。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 增加「项目定位」：执行 / 平台动作 / 会话证据 / 资源隐私四条边界，以及适合与不适合的使用范围。[Issue #2514](https://github.com/can4hou6joeng4/boss-harness/issues/2514)
- 更新滚动推广草稿到当前 14 项工程检查与 rc 事实；仍不向任何社区发送。版本推进到 npm `0.2.0-rc.195` / Python `0.2.0rc195`。

## 0.2.0-rc.194 - 2026-11-18

rc.194 源码候选核对包发布元数据与私有边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_versions.py` 扩展包元数据核对：根包描述 / 仓库 / issues / Node 版本、全部工作区 `private` 与非空描述、Python readme / requires-python / keywords / project.urls / 入口脚本 / hatchling wheel 路径。[Issue #2512](https://github.com/can4hou6joeng4/boss-harness/issues/2512)
- 补齐 `@boss-harness/*` 三个内部包的描述；负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.194` / Python `0.2.0rc194`。不执行发布动作。

## 0.2.0-rc.193 - 2026-11-18

rc.193 源码候选核对发布资产清单守卫。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_release_assets.py`：核对清单 schema、保留名、身份 / 摘要校验链、安全读取与 CI 构建步骤原样保留（2 个常量、46 项防护）。[Issue #2510](https://github.com/can4hou6joeng4/boss-harness/issues/2510)
- CI 接入后覆盖 14 个检查脚本；五个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.193` / Python `0.2.0rc193`。本轮不执行任何发布动作。

## 0.2.0-rc.192 - 2026-11-18

rc.192 源码候选核对工具参数 schema 与注册表投影边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_tool_schema.py`：核对 8 个预算常量、关键字 / 类型白名单、结构化字符串解码与最终校验顺序，以及 `tool_bundle.py` 的名称 / 执行模式 / 预算 / 注册与只读投影边界。[Issue #2508](https://github.com/can4hou6joeng4/boss-harness/issues/2508)
- CI 接入后覆盖 13 个检查脚本；六个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.192` / Python `0.2.0rc192`。

## 0.2.0-rc.191 - 2026-11-18

rc.191 源码候选核对会话导出工具数据边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_export_privacy.py` 新增 26 项工具投影核对：默认安全参数白名单、40 个参数 / 64 字符键名上限、`MAX_SCRUB_DEPTH = 64`、个人信息收集来源、完整结果与结构摘要双分支，以及按转义字节二分截断的导出预算。[Issue #2506](https://github.com/can4hou6joeng4/boss-harness/issues/2506)
- 五个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.191` / Python `0.2.0rc191`。

## 0.2.0-rc.190 - 2026-11-18

rc.190 源码候选核对会话导出脱敏管线顺序。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_export_privacy.py` 新增 39 项管线核对：已知凭据 / 路径值优先、`redact_secrets`、token / 环境赋值 / 路径规则的顺序、个人信息按长度降序打码，以及 `text()` 的双重脱敏。[Issue #2504](https://github.com/can4hou6joeng4/boss-harness/issues/2504)
- 六个负向探针（删除上游脱敏、路径脱敏、个人信息打码、排序、改写敏感环境规则）均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.190` / Python `0.2.0rc190`。

## 0.2.0-rc.189 - 2026-11-18

rc.189 源码候选核对工具结果分页与引用边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_tool_results.py`：核对内联 64 KiB / 单页 1 MiB、默认 16,384 / 最大 32,768 码点、模型 8,192 码点及其关系；核对 RPC 字段白名单、摘要与游标归属、`STALE_RESULT` 恢复信息与模型工具 schema 边界。[Issue #2502](https://github.com/can4hou6joeng4/boss-harness/issues/2502)
- CI 接入后覆盖 12 个检查脚本；六个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.189` / Python `0.2.0rc189`。

## 0.2.0-rc.188 - 2026-11-18

rc.188 文档候选重排 README 的 CI 检查说明。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README「开发与验证」把数百字的单行检查说明拆成导语、四组列表（版本与发布元数据、协议与传输、内核工具与本地资源、工作流 / 搜索 / 文档）和可复制的逐项命令，保留全部检查事实。[Issue #2500](https://github.com/can4hou6joeng4/boss-harness/issues/2500)
- 不改变任何检查脚本或 CI 行为；文档链接检查通过；版本推进到 npm `0.2.0-rc.188` / Python `0.2.0rc188`。

## 0.2.0-rc.187 - 2026-11-18

rc.187 源码候选核对附件读取分页与存储配额。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_attachments.py`：核对存储默认值 / 上限、`DEFAULT_READ_CHARS = 16,384` 与 `MAX_READ_CHARS = 32,768`、`attachment/read` 请求字段白名单、单页预算守卫与 `RESPONSE_TOO_LARGE` 恢复信息，以及两个配额环境变量名。[Issue #2498](https://github.com/can4hou6joeng4/boss-harness/issues/2498)
- CI 接入后覆盖 11 个检查脚本；放大默认分段、删除单页守卫与改写环境变量名三个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.187` / Python `0.2.0rc187`。

## 0.2.0-rc.186 - 2026-11-18

rc.186 源码候选核对桌面会话恢复边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 新增恢复边界核对：`harnessReplica.ts` 的 4 个分页 / 正文预算常量，以及 10 项内容引用校验（编码、SHA-256、线程 / 条目 / 快照标识、`part`、字符与字节关系、4 倍上限与 16 MiB 上限）；桌面防护计数达到 161。[Issue #2496](https://github.com/can4hou6joeng4/boss-harness/issues/2496)
- 删除 4 倍字节关系、抬高 16 MiB 上限与放大正文分页预算三个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.186` / Python `0.2.0rc186`。

## 0.2.0-rc.185 - 2026-11-18

rc.185 源码候选核对会话导出上限的双端一致。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_export_privacy.py` 解析主进程 `security.ts` 的 `EXPORT_MAX_BYTES`，要求与内核 `MAX_EXPORT_BYTES` 相等，并保留按 UTF-8 字节数核对导出正文长度的判定。[Issue #2494](https://github.com/can4hou6joeng4/boss-harness/issues/2494)
- 改动主进程副本与删除长度判定两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.185` / Python `0.2.0rc185`。

## 0.2.0-rc.184 - 2026-11-18

rc.184 源码候选核对工作区技能加载边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_skills.py`：核对技能常量关系与帧上限、`O_NOFOLLOW` / `O_NONBLOCK` / inode 校验 / 有界读取、`os.scandir` 与根目录符号链接拒绝、名称 / 描述 / 问题清单截断，并禁止 `SkillCatalog` 使用 `glob` / `rglob` / `iterdir` 枚举技能。[Issue #2492](https://github.com/can4hou6joeng4/boss-harness/issues/2492)
- CI 接入后覆盖 10 个检查脚本；移除 `O_NOFOLLOW`、删除名称截断、改用 `rglob`、缩小扫描上限与抬高单文件上限五个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.184` / Python `0.2.0rc184`。

## 0.2.0-rc.183 - 2026-11-18

rc.183 源码候选固定内核私有状态文件边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_private_files.py`：核对 `private_files.py` 的 `0o700` / `0o600` 模式、`O_NOFOLLOW`、uid / inode 校验与 ACL 清理，7 个状态模块的关键调用点，并禁止这些模块直接 `open(..., "w"/"a")`、`write_text(` 或 `write_bytes(` 写盘。[Issue #2490](https://github.com/can4hou6joeng4/boss-harness/issues/2490)
- CI 接入后覆盖 9 个检查脚本；放宽文件模式、删除启动核对与注入 `write_text` 三个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.183` / Python `0.2.0rc183`。

## 0.2.0-rc.182 - 2026-11-18

rc.182 源码候选核对发布元数据与 LICENSE 的 MIT 声明。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_versions.py` 核对根包与全部 npm 工作区的 `license` 为 MIT，`pyproject.toml` 的 `project.license` 为 MIT 且 `license-files` 恰为 `["LICENSE"]`，并核对 `LICENSE` 以 `MIT License` 开头且包含许可正文。[Issue #2488](https://github.com/can4hou6joeng4/boss-harness/issues/2488)
- 改动工作区许可证、删除 `license-files`、改写 `LICENSE` 首行三个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.182` / Python `0.2.0rc182`。

## 0.2.0-rc.181 - 2026-11-18

rc.181 源码候选核对内核与 app-client 的传输上限。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_protocol.py` 解析内核 `rpc.py` 的 `MAX_FRAME_BYTES`，要求 app-client 的 `maxFrameBytes` 默认值与它相等且字面量唯一，`maxQueuedBytes` 默认值不小于帧上限。[Issue #2486](https://github.com/can4hou6joeng4/boss-harness/issues/2486)
- 改动客户端帧上限、队列上限与内核常量三个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.181` / Python `0.2.0rc181`。

## 0.2.0-rc.180 - 2026-11-18

rc.180 源码候选限制桌面与 app-client 的子进程 API。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求主进程与 app-client 的 `node:child_process` 只允许具名导入 `spawn` 与类型，且不得调用 `exec` / `execFile` / `execSync` / `execFileSync` / `spawnSync` / `fork`；桌面防护计数达到 147。[Issue #2484](https://github.com/can4hou6joeng4/boss-harness/issues/2484)
- 注入 `exec` 具名导入、默认导入与 `execSync` 调用三个负向探针均触发对应错误；README、技术参考、状态说明与发布约定同步；版本推进到 npm `0.2.0-rc.180` / Python `0.2.0rc180`。

## 0.2.0-rc.179 - 2026-11-18

rc.179 源码候选核对会话导出字节上限。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_export_privacy.py` 解析三个字节常量，要求 `MIN_EXPORT_BYTES ≤ DEFAULT_EXPORT_BYTES ≤ MAX_EXPORT_BYTES` 且最大值低于 1 MiB 传输单页上限。[Issue #2482](https://github.com/can4hou6joeng4/boss-harness/issues/2482)
- 最大值抬到 2 MiB、默认值抬到最大值之上两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.179` / Python `0.2.0rc179`。

## 0.2.0-rc.178 - 2026-11-18

rc.178 源码候选新增会话导出默认脱敏核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_export_privacy.py`：核对 `EXPORT_FORMATS` 为 markdown / json / html、`thread/export` 请求字段白名单与 `includeToolResults` 默认 `False`、四个脱敏标记与 `redact_secrets(` 保留，且 `session_export.py` 不包含写盘 API。[Issue #2480](https://github.com/can4hou6joeng4/boss-harness/issues/2480)
- CI 增加导出隐私核对步骤，工作流检查覆盖 8 个脚本；默认值改为 `True` 与修改脱敏标记两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.178` / Python `0.2.0rc178`。

## 0.2.0-rc.177 - 2026-11-18

rc.177 文档候选对齐 README 英文概览与桌面能力。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 英文 Desktop 条目与中文能力地图补充持久队列的重试 / 撤回与完整输入核对、工作区技能管理、自动压缩策略设置，与 STATUS 已实现范围一致。[Issue #2478](https://github.com/can4hou6joeng4/boss-harness/issues/2478)
- 文档链接检查通过；版本推进到 npm `0.2.0-rc.177` / Python `0.2.0rc177`。

## 0.2.0-rc.176 - 2026-11-18

rc.176 源码候选固定工具子进程不开 shell。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `tools/boss_cli.py` 的 `Popen` 显式设置 `shell=False`；`scripts/check_harness_tools.py` 扫描 `harness/src/boss_harness` 下的 Python 源码，禁止 `shell=True`、`create_subprocess_shell`、`os.system` 与 `os.popen`。[Issue #2476](https://github.com/can4hou6joeng4/boss-harness/issues/2476)
- 注入 `os.system` 与删除显式 `shell=False` 两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.176` / Python `0.2.0rc176`。

## 0.2.0-rc.175 - 2026-11-18

rc.175 源码候选固定 app-client 的内核子进程不开 shell。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `packages/app-client/src/index.ts` 的 `spawn` 显式设置 `shell: false`；`scripts/check_desktop_security.py` 要求 app-client 只有该文件出现 `spawn(`，桌面防护计数达到 133。[Issue #2474](https://github.com/can4hou6joeng4/boss-harness/issues/2474)
- 删除显式设置与在 `host.ts` 新增 `spawn` 两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.175` / Python `0.2.0rc175`。

## 0.2.0-rc.174 - 2026-11-18

rc.174 源码候选限定子进程启动不开 shell。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `startupCheck.ts` 的 `spawn` 显式设置 `shell: false`；`scripts/check_desktop_security.py` 要求主进程只有该文件出现 `spawn(`，且必须包含 `shell: false`，桌面防护计数达到 131。[Issue #2472](https://github.com/can4hou6joeng4/boss-harness/issues/2472)
- 删除显式设置与在其他主进程文件新增 `spawn` 两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.174` / Python `0.2.0rc174`。

## 0.2.0-rc.173 - 2026-11-18

rc.173 源码候选核对工具组合沿用审批标记。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_harness_tools.py` 要求 `tools/bundle.py` 从 `TOOLS` 与 `approval_required_tools()` 投影名称、描述、schema 与 `requires_approval`，不得在组合层改写审批标记。[Issue #2470](https://github.com/can4hou6joeng4/boss-harness/issues/2470)
- 固定 `requires_approval=False` 与清空遍历来源两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.173` / Python `0.2.0rc173`。

## 0.2.0-rc.172 - 2026-11-18

rc.172 源码候选核对写工具集合一致性。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_harness_tools.py` 解析 `context.py` 的 `_WRITE_TOOLS`、`write_tools` 默认值与 `tool_results.py` 的 `LEGACY_WRITE_TOOLS`，要求三处均恰为 `boss_hr_greet`。[Issue #2468](https://github.com/can4hou6joeng4/boss-harness/issues/2468)
- 给默认值与 `LEGACY_WRITE_TOOLS` 各增加一个工具的两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.172` / Python `0.2.0rc172`。

## 0.2.0-rc.171 - 2026-11-18

rc.171 源码候选新增内核默认工具允许清单核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_harness_tools.py`，以标准库 AST 解析 `TOOLS` 元组：14 个唯一工具名、13 个只读工具、仅 `boss_hr_greet` 需批准，且每个 `input_schema` 为 `type: object`、`additionalProperties: false`、`required` 只引用已声明属性。[Issue #2466](https://github.com/can4hou6joeng4/boss-harness/issues/2466)
- CI 增加工具清单核对步骤，工作流检查覆盖 7 个脚本；改名工具与去掉批准标记两个负向探针均触发对应错误；README、技术参考、发布约定与 STATUS 同步；版本推进到 npm `0.2.0-rc.171` / Python `0.2.0rc171`。

## 0.2.0-rc.170 - 2026-11-18

rc.170 源码候选固定 IPC 通道为双引号字符串字面量。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `ipcRenderer.invoke` / `on` / `removeListener` 与 `ipcMain.handle` 的首个参数为双引号字符串字面量，模板字符串或变量不再绕过通道集合核对；桌面防护计数达到 129。[Issue #2464](https://github.com/can4hou6joeng4/boss-harness/issues/2464)
- 模板字符串与变量传参两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.170` / Python `0.2.0rc170`。

## 0.2.0-rc.169 - 2026-11-18

rc.169 源码候选限制 preload 的进程能力面。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `apps/desktop/src/preload` 不得出现 `process.env`、`process.exit`、`process.argv` 或 `process.cwd`，避免环境变量、启动参数或工作目录经桥接泄漏，或由 preload 主动退出进程；桌面防护计数达到 125。[Issue #2462](https://github.com/can4hou6joeng4/boss-harness/issues/2462)
- 环境变量与启动参数两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.169` / Python `0.2.0rc169`。

## 0.2.0-rc.168 - 2026-11-18

rc.168 源码候选核对工作流触发器与作业超时。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_workflows.py` 禁止 `pull_request_target` 与 `workflow_run` 触发器，并要求每个作业声明正整数 `timeout-minutes`。[Issue #2460](https://github.com/can4hou6joeng4/boss-harness/issues/2460)
- `workflow_run` 注入与删除 `timeout-minutes` 两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.168` / Python `0.2.0rc168`。

## 0.2.0-rc.167 - 2026-11-18

rc.167 源码候选禁止渲染层入口嵌入与远程资源。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `index.html` 不得包含 `iframe` / `webview` / `object` / `embed`，且 `src` / `href` / `action` 不得引用远程或协议相对 URL；桌面防护计数达到 121。[Issue #2458](https://github.com/can4hou6joeng4/boss-harness/issues/2458)
- 嵌入元素与远程样式两个负向探针均触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.167` / Python `0.2.0rc167`。

## 0.2.0-rc.166 - 2026-11-18

rc.166 源码候选限制主进程的脚本执行与调试器入口。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `apps/desktop/src/main` 不得出现 `executeJavaScript` 或 `debugger`，避免绕过桥接注入脚本或挂载调试器；桌面防护计数达到 119。[Issue #2456](https://github.com/can4hou6joeng4/boss-harness/issues/2456)
- 两个负向探针分别触发对应错误；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.166` / Python `0.2.0rc166`。

## 0.2.0-rc.165 - 2026-11-18

rc.165 源码候选核对主进程与 preload 的 IPC 角色符号。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `apps/desktop/src/main` 不得出现 `ipcRenderer`，`apps/desktop/src/preload` 不得出现 `ipcMain`；桌面防护计数达到 117。[Issue #2454](https://github.com/can4hou6joeng4/boss-harness/issues/2454)
- 两个方向的负向探针均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.165` / Python `0.2.0rc165`。

## 0.2.0-rc.164 - 2026-11-18

rc.164 源码候选要求 IPC 处理器先校验发送方再工作。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求每个 `ipcMain.handle` 主体剥离大括号后以 `trustedSender(event)` 开头；桌面防护计数达到 115。[Issue #2452](https://github.com/can4hou6joeng4/boss-harness/issues/2452)
- 把 `session-export:save` 的校验移到参数解析之后的负向探针触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.164` / Python `0.2.0rc164`。

## 0.2.0-rc.163 - 2026-11-18

rc.163 源码候选核对会话导出保存对话框属性。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 的 `session-export:save` 不变量新增 `createDirectory` 与 `showOverwriteConfirmation` 两个片段；桌面防护计数达到 108。[Issue #2450](https://github.com/can4hou6joeng4/boss-harness/issues/2450)
- 两个负向探针分别删除对应属性均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.163` / Python `0.2.0rc163`。

## 0.2.0-rc.162 - 2026-11-18

rc.162 源码候选限定 `shell.openExternal` 唯一调用点。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 统计主进程中的 `shell.openExternal(`，要求只出现在 `window.ts` 且恰好一次；桌面防护计数达到 106。[Issue #2448](https://github.com/can4hou6joeng4/boss-harness/issues/2448)
- 在 `harness.ts` 新增调用与 `window.ts` 重复调用两个负向探针均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.162` / Python `0.2.0rc162`。

## 0.2.0-rc.161 - 2026-11-18

rc.161 源码候选核对渲染层外部链接判定函数。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 取出 `RichMarkdown.tsx` 的 `externalTarget`，要求保留 `EXTERNAL_SCHEMES.includes(` 与 `new URL(url).protocol`；桌面防护计数达到 105。[Issue #2446](https://github.com/can4hou6joeng4/boss-harness/issues/2446)
- 删除协议集合判定与 URL 解析两个负向探针均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.161` / Python `0.2.0rc161`。

## 0.2.0-rc.160 - 2026-11-18

rc.160 源码候选核对 CHANGELOG 条目日期。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_versions.py` 解析每个版本条目的 ISO 日期，要求合法且不晚于上一条，同日允许多个候选。[Issue #2444](https://github.com/can4hou6joeng4/boss-harness/issues/2444)
- 非法日期与晚于上一条的日期两个负向探针均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.160` / Python `0.2.0rc160`。

## 0.2.0-rc.159 - 2026-11-18

rc.159 源码候选核对渲染层入口模块脚本。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `index.html` 恰好包含一个 `<script>`，必须 `type="module"` 且 `src` 以 `./src/` 开头；桌面防护计数达到 103。[Issue #2442](https://github.com/can4hou6joeng4/boss-harness/issues/2442)
- 缺 `type="module"`、远程 `src` 与第二个脚本三个负向探针均触发对应失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.159` / Python `0.2.0rc159`。

## 0.2.0-rc.158 - 2026-11-18

rc.158 源码候选禁止渲染层使用动态代码执行。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 的渲染层边界新增 `eval(` 与 `new Function(` 两条规则，命中即失败；桌面防护计数达到 100。[Issue #2440](https://github.com/can4hou6joeng4/boss-harness/issues/2440)
- 两个负向探针分别触发对应失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.158` / Python `0.2.0rc158`。

## 0.2.0-rc.157 - 2026-11-18

rc.157 源码候选核对 CHANGELOG 版本链严格递减。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_versions.py` 收集全部 `## <版本> - <日期>` 标题，按 `(major, minor, patch, rc)` 要求严格递减且首条等于源码版本。[Issue #2438](https://github.com/can4hou6joeng4/boss-harness/issues/2438)
- 重复版本与乱序条目两个负向探针均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.157` / Python `0.2.0rc157`。

## 0.2.0-rc.156 - 2026-11-18

rc.156 源码候选要求工作流保留依赖审计命令。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_workflows.py` 在工作流聚合文本中要求同时出现 `npm audit --audit-level=moderate --omit=dev` 与 `npm audit --audit-level=critical`，删除任一步骤都会失败。[Issue #2436](https://github.com/can4hou6joeng4/boss-harness/issues/2436)
- 两条命令各做负向探针均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.156` / Python `0.2.0rc156`。

## 0.2.0-rc.155 - 2026-11-18

rc.155 源码候选刷新英文概览与工程检查描述。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 英文概览的 Desktop 条目覆盖单一 `boss` 桥接、渲染层仅经 `window.boss` 与仅本地来源 CSP；`docs/STATUS.md` 的工程检查条目列出桌面安全与 CI 工作流安全的具体守卫范围。[Issue #2434](https://github.com/can4hou6joeng4/boss-harness/issues/2434)
- 文档刷新不改变运行行为；版本推进到 npm `0.2.0-rc.155` / Python `0.2.0rc155`。

## 0.2.0-rc.154 - 2026-11-18

rc.154 源码候选禁止渲染层 CSP 引用远程来源。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 CSP 任何指令的 token 不得含 `://`，`img-src`、`style-src` 等不能再加入远程主机。[Issue #2432](https://github.com/can4hou6joeng4/boss-harness/issues/2432)
- 远程图片与远程样式两个负向探针均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.154` / Python `0.2.0rc154`。

## 0.2.0-rc.153 - 2026-11-18

rc.153 源码候选核对主进程与渲染层的导入方向。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 扫描 `apps/desktop/src/main` 的导入，出现 `../renderer` 路径即失败；扫描 preload 的导入，出现 `../main` 路径即失败。[Issue #2430](https://github.com/can4hou6joeng4/boss-harness/issues/2430)
- 两个方向各做负向探针均触发对应失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.153` / Python `0.2.0rc153`。

## 0.2.0-rc.152 - 2026-11-18

rc.152 源码候选要求工作流 action 引用固定到主版本。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_workflows.py` 要求每个 `uses` 引用匹配 `actions/<名称>@v<主版本>`，`@main`、`@master`、无版本后缀或预发布标签都会失败。[Issue #2428](https://github.com/can4hou6joeng4/boss-harness/issues/2428)
- 四类负向探针分别触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.152` / Python `0.2.0rc152`。

## 0.2.0-rc.151 - 2026-11-18

rc.151 源码候选核对会话导出处理器不变量。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 取出 `session-export:save` 处理器主体，要求保留受信发送方校验、`validateSessionExportRequest(payload)`、`validateThreadExportResponse(response, request)`、`writeSessionExport(choice.filePath, exported.content)` 与 `basename(choice.filePath)` 返回。[Issue #2426](https://github.com/can4hou6joeng4/boss-harness/issues/2426)
- 四类负向探针分别触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.151` / Python `0.2.0rc151`。

## 0.2.0-rc.150 - 2026-11-18

rc.150 源码候选核对 preload 暴露调用与导入来源。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 preload 恰好一次调用 `contextBridge.exposeInMainWorld("boss", api)`，非相对导入只允许 `electron` 与 `@boss-harness/protocol`、`shared`、`app-client`。[Issue #2424](https://github.com/can4hou6joeng4/boss-harness/issues/2424)
- 负向探针增加第二个全局、改动全局名、导入 `node:fs` 与直接暴露 `ipcRenderer` 均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.150` / Python `0.2.0rc150`。

## 0.2.0-rc.149 - 2026-11-18

rc.149 源码候选禁止渲染层直接写入 HTML。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 的渲染层边界增加三条规则：`dangerouslySetInnerHTML`、`innerHTML`、`outerHTML` / `insertAdjacentHTML`，命中即失败。[Issue #2422](https://github.com/can4hou6joeng4/boss-harness/issues/2422)
- 三类负向探针分别触发对应失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.149` / Python `0.2.0rc149`。

## 0.2.0-rc.148 - 2026-11-18

rc.148 源码候选核对渲染层 CSP 与内联脚本。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 解析渲染层入口 `index.html` 的 CSP meta，要求 `default-src` 与 `script-src` 恰为 `'self'`，任何指令不得含 `'unsafe-eval'` 或 `*`，且不得出现无 `src` 的内联脚本。[Issue #2420](https://github.com/can4hou6joeng4/boss-harness/issues/2420)
- 负向探针删除 meta、放宽 `default-src` / `script-src`、加入 `'unsafe-eval'` 与内联脚本均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.148` / Python `0.2.0rc148`。

## 0.2.0-rc.147 - 2026-11-18

rc.147 源码候选禁止渲染层直接导入 Electron 与 Node 模块。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 的渲染层边界检查扩展为四条规则：`ipcRenderer`、`from "electron"` / `import("electron")`、CommonJS `require(`、`from "node:*"` / `import("node:*")`，命中即失败。[Issue #2418](https://github.com/can4hou6joeng4/boss-harness/issues/2418)
- 四类负向探针分别触发对应失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.147` / Python `0.2.0rc147`。

## 0.2.0-rc.146 - 2026-11-18

rc.146 源码候选禁止渲染层直接引用 `ipcRenderer`。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 扫描 `apps/desktop/src/renderer` 下的 `.ts` / `.tsx`，出现 `ipcRenderer` 即失败；渲染层只能经 `window.boss` 使用桥接 API。[Issue #2416](https://github.com/can4hou6joeng4/boss-harness/issues/2416)
- 负向探针在 `env.d.ts` 临时加入该标识符触发失败；`docs/STATUS.md` 启动自检条目补「结果复制」；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.146` / Python `0.2.0rc146`。

## 0.2.0-rc.145 - 2026-11-18

rc.145 源码候选固定主窗口权限判定实现。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 取出 `permissionPolicy.ts` 的 `allowsMainWindowPermission`，要求保留 `Boolean(requestingUrl)`、`MAIN_WINDOW_PERMISSIONS.has(permission)` 与 `isTrustedRendererUrl(requestingUrl!` 三项判定。[Issue #2414](https://github.com/can4hou6joeng4/boss-harness/issues/2414)
- 负向探针分别删除三项判定均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.145` / Python `0.2.0rc145`。

## 0.2.0-rc.144 - 2026-11-18

rc.144 源码候选固定来源判定函数的关键实现。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 取出 `security.ts` 的 `isTrustedRendererUrl` 与 `isOfficialLoginUrl`，要求保留开发来源 / 路径比较、`file:` 入口比较，以及 `https:`、拒绝 userinfo、443 端口、`zhipin.com` 精确主机与子域后缀。[Issue #2412](https://github.com/can4hou6joeng4/boss-harness/issues/2412)
- 负向探针删除后缀限制、端口限制与文件比较均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.144` / Python `0.2.0rc144`。

## 0.2.0-rc.143 - 2026-11-18

rc.143 源码候选核对检查脚本全部接入 CI。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_workflows.py` 收集 `scripts/check_*.py` 与工作流中的脚本引用，要求集合完全一致；未接入 CI 的检查脚本或引用不存在的脚本都会失败并列出差异。[Issue #2410](https://github.com/can4hou6joeng4/boss-harness/issues/2410)
- 输出增加检查脚本覆盖数量；负向探针新增临时脚本、替换工作流引用均触发失败。README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.143` / Python `0.2.0rc143`。

## 0.2.0-rc.142 - 2026-11-18

rc.142 源码候选让文档检查覆盖全部约定位置的 Markdown。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_docs_links.py` 加入 `harness/README.md` 与 `.github/PULL_REQUEST_TEMPLATE.md`，并扫描根目录、`docs/`、`harness/`、`.github/` 下的 Markdown，要求全部登记；未登记或登记后移出约定位置都会失败。[Issue #2408](https://github.com/can4hou6joeng4/boss-harness/issues/2408)
- 输出增加检查覆盖篇数；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.142` / Python `0.2.0rc142`。

## 0.2.0-rc.141 - 2026-11-18

rc.141 源码候选核对受信发送方判定。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 取出 `harness.ts` 的 `trustedSender` 主体，要求校验窗口成员关系、`event.senderFrame === event.sender.mainFrame`、`event.senderFrame.url` 与 `isTrustedRendererUrl(`，并至少两处 `throw new Error(`。[Issue #2406](https://github.com/can4hou6joeng4/boss-harness/issues/2406)
- 负向探针删除主框架比较、来源判定与抛出均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.141` / Python `0.2.0rc141`。

## 0.2.0-rc.140 - 2026-11-18

rc.140 源码候选核对 IPC 通道与发送方校验。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 解析 preload 的 `ipcRenderer.invoke` / `on` 与主进程 `ipcMain.handle`、`send` / `sendWhenLoaded` 通道，要求 invoke 与 handle、订阅与发送集合完全一致，同一通道不得重复注册。[Issue #2404](https://github.com/can4hou6joeng4/boss-harness/issues/2404)
- 每个 `ipcMain.handle` 处理器主体必须在入口调用 `trustedSender(event)`；负向探针改通道名、删发送方与移除校验均触发失败。README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.140` / Python `0.2.0rc140`。

## 0.2.0-rc.139 - 2026-11-18

rc.139 源码候选统一 preload 暴露面的类型来源。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `apps/desktop/src/preload/bridge.ts`，集中定义 `BossBridge` 与 `DesktopHarnessStatus`；preload 的 `api` 标注该类型，渲染层 `env.d.ts` 直接声明 `boss: BossBridge`，不再复制方法列表。[Issue #2402](https://github.com/can4hou6joeng4/boss-harness/issues/2402)
- `scripts/check_desktop_security.py` 要求共享类型文件存在、preload 与声明侧引用同一类型，回退到手工列表时失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.139` / Python `0.2.0rc139`。

## 0.2.0-rc.138 - 2026-11-18

rc.138 源码候选支持复制启动自检结果。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 启动自检区域新增「复制自检结果」，复制标题、版本信息、协议不一致提示、逐项状态/说明/检查码与处理建议；只使用界面已展示的静态字段，不包含 stderr、异常原文、端点、凭据、本机路径或会话内容。[Issue #2400](https://github.com/can4hou6joeng4/boss-harness/issues/2400)
- 写入成功与失败都有回执；新的自检结论会作废旧回执，迟到结果不覆盖当前报告。用户指南与桌面指南同步；版本推进到 npm `0.2.0-rc.138` / Python `0.2.0rc138`。

## 0.2.0-rc.137 - 2026-11-18

rc.137 源码候选核对外部链接协议白名单双端一致。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 解析渲染层 `EXTERNAL_SCHEMES` 与主进程 `isAllowedExternalUrl` 的协议列表，要求非空且集合一致；并核对 `openExternal` 先经 `isAllowedExternalUrl` 判定再调用 `shell.openExternal`，`setWindowOpenHandler` 调用该封装。[Issue #2398](https://github.com/can4hou6joeng4/boss-harness/issues/2398)
- 负向探针在任一侧增删协议或移除守卫时均触发失败；README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.137` / Python `0.2.0rc137`。

## 0.2.0-rc.136 - 2026-11-18

rc.136 源码候选把导航与卸载拦截处理器纳入桌面静态安全检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求主窗口注册 `will-navigate` / `will-frame-navigate` 并调用 `isTrustedRendererUrl` 后阻止，登录视图注册 `will-navigate` / `will-frame-navigate` / `will-redirect` / `will-prevent-unload` 并调用 `isOfficialLoginUrl` 或阻止卸载；删除或放行处理器会使检查失败。[Issue #2396](https://github.com/can4hou6joeng4/boss-harness/issues/2396)
- README、技术参考与发布约定同步覆盖范围；版本推进到 npm `0.2.0-rc.136` / Python `0.2.0rc136`。

## 0.2.0-rc.135 - 2026-11-18

rc.135 源码候选在启动自检中提示协议版本不一致。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 「设置 → 模型与连接」在自检报告带 `protocolVersion` 且与桌面协议常量不一致时，并列显示内核报告值与桌面支持值，并提示二者可能来自不同构建；一致或字段缺失时不显示。[Issue #2394](https://github.com/can4hou6joeng4/boss-harness/issues/2394)
- 用户指南、桌面指南、技术参考与状态页同步；版本推进到 npm `0.2.0-rc.135` / Python `0.2.0rc135`。

## 0.2.0-rc.134 - 2026-11-18

rc.134 源码候选同步启动自检版本展示的公开说明。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `docs/STATUS.md` 的桌面能力加入启动失败自检的内核、协议与 Python 版本展示；`docs/DESKTOP_GUIDE.md` 同步说明版本字段与缺失时回退。[Issue #2392](https://github.com/can4hou6joeng4/boss-harness/issues/2392)
- 版本推进到 npm `0.2.0-rc.134` / Python `0.2.0rc134`。

## 0.2.0-rc.133 - 2026-11-18

rc.133 源码候选将 preload 桥接纳入桌面静态安全检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 preload 经 `contextBridge.exposeInMainWorld` 暴露 API，并拒绝直接暴露 `ipcRenderer`。[Issue #2390](https://github.com/can4hou6joeng4/boss-harness/issues/2390)
- README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.133` / Python `0.2.0rc133`。

## 0.2.0-rc.132 - 2026-11-18

rc.132 源码候选让文档检查忽略 HTML 注释。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_docs_links.py` 在提取链接与标题前移除跨行 `<!-- ... -->` 注释，注释中的示例链接与标题不再参与校验。[Issue #2388](https://github.com/can4hou6joeng4/boss-harness/issues/2388)
- 技术参考补充该覆盖边界；版本推进到 npm `0.2.0-rc.132` / Python `0.2.0rc132`。

## 0.2.0-rc.131 - 2026-11-18

rc.131 源码候选在启动自检摘要中补充 Python 版本。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `StartupDiagnosis` 报告分支增加可选 `pythonVersion`；主进程解析器与渲染层沿用单行有界校验，不合规时整份报告作废。[Issue #2386](https://github.com/can4hou6joeng4/boss-harness/issues/2386)
- 设置页自检摘要显示「内核 … · 协议 … · Python …」，便于识别解释器版本或虚拟环境问题。
- 用户指南与技术参考同步；版本推进到 npm `0.2.0-rc.131` / Python `0.2.0rc131`。

## 0.2.0-rc.130 - 2026-11-18

rc.130 源码候选在桌面启动自检中展示内核与协议版本。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `StartupDiagnosis` 报告分支增加可选 `version` / `protocolVersion`；主进程解析器对两者做有界单行校验，不合规时整份报告作废。[Issue #2384](https://github.com/can4hou6joeng4/boss-harness/issues/2384)
- 「设置 → 模型与连接」在自检明细前显示「自检报告：内核 … · 协议 …」；旧内核缺少字段时不显示。
- 用户指南与技术参考同步；版本推进到 npm `0.2.0-rc.130` / Python `0.2.0rc130`。

## 0.2.0-rc.129 - 2026-11-18

rc.129 源码候选核对工作区源码的协议包依赖声明。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_protocol.py` 扫描根 `package.json` 声明的所有工作区，源码导入 `@boss-harness/*` 时必须在该工作区的 `dependencies` 或 `devDependencies` 中声明，避免独立打包时运行时缺包。[Issue #2382](https://github.com/can4hou6joeng4/boss-harness/issues/2382)
- 技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.129` / Python `0.2.0rc129`。

## 0.2.0-rc.128 - 2026-11-18

rc.128 源码候选核对桌面权限处理器的实际语义。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `window.ts` 的两个权限处理器都调用 `allowsMainWindowPermission`，并要求 `platformLogin.ts` 的请求处理器调用 `callback(false)`、检查处理器返回 `false`。[Issue #2380](https://github.com/can4hou6joeng4/boss-harness/issues/2380)
- README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.128` / Python `0.2.0rc128`。

## 0.2.0-rc.127 - 2026-11-18

rc.127 源码候选补上桌面权限来源与登录会话隔离的静态核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 要求 `permissionPolicy.ts` 调用 `isTrustedRendererUrl` 核对权限请求来源，并要求 `platformLogin.ts` 使用 `session.fromPartition(` 且不得使用默认会话。[Issue #2378](https://github.com/can4hou6joeng4/boss-harness/issues/2378)
- README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.127` / Python `0.2.0rc127`。

## 0.2.0-rc.126 - 2026-11-18

rc.126 源码候选为桌面权限与导航防护增加静态核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_desktop_security.py` 新增强制核对：主窗口权限白名单恰为 `clipboard-sanitized-write`；主窗口与平台登录视图都注册权限请求 / 检查处理器、`setWindowOpenHandler` 返回 `deny`、`will-attach-webview` 调用 `preventDefault`。[Issue #2376](https://github.com/can4hou6joeng4/boss-harness/issues/2376)
- README、技术参考与发布约定同步；版本推进到 npm `0.2.0-rc.126` / Python `0.2.0rc126`。

## 0.2.0-rc.125 - 2026-11-18

rc.125 源码候选收紧 CI 工作流权限的静态检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_workflows.py` 只允许顶层 `permissions`：job 或 step 中另写的 `permissions` 一律使检查失败，避免私有 job 级写权限绕过 `contents: read` 约定。[Issue #2374](https://github.com/can4hou6joeng4/boss-harness/issues/2374)
- README、技术参考与发布约定同步说明；版本推进到 npm `0.2.0-rc.125` / Python `0.2.0rc125`。

## 0.2.0-rc.124 - 2026-11-18

rc.124 源码候选修正公开状态页对桌面能力的描述。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `docs/STATUS.md` 将已落地的任务队列面板、技能选择器 / 工作区技能管理与自动压缩策略设置移入「已具备」，待完成列表只保留真实未落地或待验收事项。[Issue #2372](https://github.com/can4hou6joeng4/boss-harness/issues/2372)
- 候选版本号同步为 npm `0.2.0-rc.124` / Python `0.2.0rc124`。

## 0.2.0-rc.123 - 2026-11-18

rc.123 源码候选补齐本地自检报告的用户与技术说明。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 使用指南增加自检报告顶层字段表：区分源码版本、协议版本与 Python 版本，并说明 `ok` 与 `checks` 的一致性。[Issue #2370](https://github.com/can4hou6joeng4/boss-harness/issues/2370)
- 技术参考新增「启动自检报告」章节，记录桌面解析器的固定字段、限制与不覆盖范围，并加入快速导航。
- 候选版本号同步为 npm `0.2.0-rc.123` / Python `0.2.0rc123`。

## 0.2.0-rc.122 - 2026-11-18

rc.122 源码候选让宿主默认协议版本引用唯一常量。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `packages/app-client/src/host.ts` 的 initialize 默认 `protocolVersion` 改为引用 `PROTOCOL_VERSION`，不再写死 `"0.2.0"`。[Issue #2368](https://github.com/can4hou6joeng4/boss-harness/issues/2368)
- `scripts/check_protocol.py` 增加静态检查：宿主与桌面源码中的 `protocolVersion ?? "…"` 默认值必须引用常量，重复字面量会使检查失败。
- 候选版本号和使用指南同步为 npm `0.2.0-rc.122` / Python `0.2.0rc122`。

## 0.2.0-rc.121 - 2026-11-18

rc.121 源码候选补充状态页的英文与支持入口。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `docs/STATUS.md` 顶部增加英文摘要并链接 README 的 English overview；README 的 English overview 增加状态页入口，SUPPORT 的文档表加入状态页。[Issue #2366](https://github.com/can4hou6joeng4/boss-harness/issues/2366)
- 候选版本号和使用指南同步为 npm `0.2.0-rc.121` / Python `0.2.0rc121`。

## 0.2.0-rc.120 - 2026-11-18

rc.120 源码候选增加公开项目状态页。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `docs/STATUS.md`，汇总源码候选与实际发布的区别、已具备能力、待完成与待验收范围、非目标及参与入口；docs 索引与 README 导航加入该页，文档检查纳入该文件。[Issue #2364](https://github.com/can4hou6joeng4/boss-harness/issues/2364)
- 候选版本号和使用指南同步为 npm `0.2.0-rc.120` / Python `0.2.0rc120`。

## 0.2.0-rc.119 - 2026-11-18

rc.119 源码候选为 CI 工作流增加静态安全检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_workflows.py`：核对 `.github/workflows` 的 `contents: read` 权限、无 `write`、`cancel-in-progress: true`、checkout `persist-credentials: false`，并禁止 `pull_request_target` 与非 `actions/` 的 `uses`。[Issue #2362](https://github.com/can4hou6joeng4/boss-harness/issues/2362)
- Source build 增加该检查；README、CONTRIBUTING、技术参考与发布约定同步。
- 候选版本号和使用指南同步为 npm `0.2.0-rc.119` / Python `0.2.0rc119`。

## 0.2.0-rc.118 - 2026-11-18

rc.118 源码候选在本地自检报告中加入协议版本。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `boss-harness --check` 的 JSON 报告增加 `protocolVersion`，直接引用内核唯一的 `PROTOCOL_VERSION`；`schemaVersion: 1`、`ok` 与 `checks` 结构不变。[Issue #2360](https://github.com/can4hou6joeng4/boss-harness/issues/2360)
- 使用指南同步报告字段；候选版本号和使用指南同步为 npm `0.2.0-rc.118` / Python `0.2.0rc118`。

## 0.2.0-rc.117 - 2026-11-18

rc.117 源码候选收紧 CI checkout 的凭据存储。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- Source build 与 Python matrix 的 `actions/checkout` 都设置 `persist-credentials: false`，不再把工作流令牌写入 `.git/config`；工作流仍只有 `contents: read` 权限。[Issue #2358](https://github.com/can4hou6joeng4/boss-harness/issues/2358)
- 候选版本号和使用指南同步为 npm `0.2.0-rc.117` / Python `0.2.0rc117`。

## 0.2.0-rc.116 - 2026-11-18

rc.116 源码候选为桌面窗口安全配置增加静态回归检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_desktop_security.py`：核对主窗口与平台登录视图的 `webPreferences` 隔离、沙箱、Node 集成、Web 安全、登录视图 `devTools` 等 17 项布尔值，并拒绝未登记文件。[Issue #2356](https://github.com/can4hou6joeng4/boss-harness/issues/2356)
- Source build 增加该检查；README、CONTRIBUTING、技术参考与发布约定同步。
- 候选版本号和使用指南同步为 npm `0.2.0-rc.116` / Python `0.2.0rc116`。

## 0.2.0-rc.115 - 2026-11-18

rc.115 源码候选补充贡献流程的 PR 标题与关闭关联约定。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `.github/PULL_REQUEST_TEMPLATE.md` 提醒标题使用 `type(scope): 中文描述`，正文用单独一行 `Closes #N` 关联 Issue；squash 合并后 PR 标题会成为主干提交主题。[Issue #2354](https://github.com/can4hou6joeng4/boss-harness/issues/2354)
- CONTRIBUTING 的提交和 PR 小节同步关闭关键字要求。
- 候选版本号和使用指南同步为 npm `0.2.0-rc.115` / Python `0.2.0rc115`。

## 0.2.0-rc.114 - 2026-11-18

rc.114 源码候选加固文档检查的围栏与锚点边界。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_docs_links.py` 改用共享围栏解析：识别 ``` 与 ~~~、最多 3 个前导空格，关闭标记不得短于开启标记且不得带信息串；未闭合时以文件名报错并退出码 2。[Issue #2352](https://github.com/can4hou6joeng4/boss-harness/issues/2352)
- 标题锚点改为全局去重，重复标题依次追加 `-1`、`-2`，与 GitHub 对字面 `-1` 标题的处理一致；现有 141 个链接、63 个页内锚点仍通过。
- 技术参考同步检查范围。候选版本号和使用指南同步为 npm `0.2.0-rc.114` / Python `0.2.0rc114`。

## 0.2.0-rc.113 - 2026-11-18

rc.113 源码候选把文档检查扩展到页内锚点。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_docs_links.py` 按 GitHub 风格从 ATX 标题生成锚点，解码百分号编码并校验同文件与跨 Markdown 文件的页内锚点，重复标题追加 `-1` 后缀；当前 141 个链接、63 个页内锚点与 4 篇文档索引通过。[Issue #2349](https://github.com/can4hou6joeng4/boss-harness/issues/2349)
- 外链、代码块、行内代码以及非 Markdown 目标不参与锚点匹配；失败时列出文件与目标并以退出码 2 结束。
- README、CONTRIBUTING、发布约定与技术参考同步检查范围。候选版本号和使用指南同步为 npm `0.2.0-rc.113` / Python `0.2.0rc113`。

## 0.2.0-rc.112 - 2026-11-18

rc.112 源码候选修正只读工具表述并扩展文档检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- README 与使用指南把只读会话的工具描述改为「13 个只读工具（含能力发现）和 1 个只读内核结果分段读取工具」，与注册表一致。[Issue #2347](https://github.com/can4hou6joeng4/boss-harness/issues/2347)
- `scripts/check_docs_links.py` 纳入 `CHANGELOG.md` 与 `docs/changelog-rc15-details.md`，并核对 `docs/README.md` 索引覆盖 `docs/` 下其余 Markdown 文件；当前 93 个链接、4 篇文档索引通过。
- 技术参考、发布约定与 README 同步检查范围。候选版本号和使用指南同步为 npm `0.2.0-rc.112` / Python `0.2.0rc112`。

## 0.2.0-rc.111 - 2026-11-18

rc.111 源码候选把 Python 矩阵扩展到源码编译。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 原 `Search normalization` 矩阵 job 改名为 `Python <版本>`，在 Python 3.10–3.14 上除运行 `check_search_unicode.py` 外，再执行 `python -m compileall -q harness/src scripts`，验证源码语法兼容。[Issue #2345](https://github.com/can4hou6joeng4/boss-harness/issues/2345)
- README、CONTRIBUTING、发布约定与技术参考同步矩阵范围。候选版本号和使用指南同步为 npm `0.2.0-rc.111` / Python `0.2.0rc111`。

## 0.2.0-rc.110 - 2026-11-18

rc.110 源码候选把桌面方法字面量纳入协议核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_protocol.py` 扫描 `apps/desktop/src` 中含 `/` 的 `method` 比较与对象字段字面量，要求全部出现在 `ClientMethods` 或 `ServerNotifications`；当前 53 个方法名通过。[Issue #2343](https://github.com/can4hou6joeng4/boss-harness/issues/2343)
- 技术参考的不变量清单更新为七类；发布约定补充桌面方法字面量范围。候选版本号和使用指南同步为 npm `0.2.0-rc.110` / Python `0.2.0rc110`。

## 0.2.0-rc.109 - 2026-11-18

rc.109 源码候选加入用户文档相对链接核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_docs_links.py`：扫描 README、贡献与发布约定、安全与支持文档及 docs 下的用户文档，跳过代码块、行内代码、外链与纯锚点，核对相对文件路径存在；断链时列出文件与目标并以退出码 2 失败。[Issue #2341](https://github.com/can4hou6joeng4/boss-harness/issues/2341)
- CI 在安装依赖前运行该检查；CONTRIBUTING、README、发布约定与技术参考记录入口和边界。候选版本号和使用指南同步为 npm `0.2.0-rc.109` / Python `0.2.0rc109`。

## 0.2.0-rc.108 - 2026-11-18

rc.108 源码候选为搜索归一化核对加入分块诊断。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_search_unicode.py` 新增 `--block 0xN`：只比较指定 0x1000 分块，逐码点列出 Python 与 Node 的结果并统计不一致数量；全量失败时提示首个不一致分块。[Issue #2339](https://github.com/can4hou6joeng4/boss-harness/issues/2339)
- 技术参考记录诊断用法。候选版本号和使用指南同步为 npm `0.2.0-rc.108` / Python `0.2.0rc108`。

## 0.2.0-rc.107 - 2026-11-18

rc.107 源码候选把双端归一化核对扩展到全部受支持 Python 版本。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `Search normalization` CI job，在 Python 3.10、3.11、3.12、3.13、3.14 上分别以 Node 24 运行 `scripts/check_search_unicode.py`；本机另在 3.11 与 3.14 上验证通过。[Issue #2337](https://github.com/can4hou6joeng4/boss-harness/issues/2337)
- README、CONTRIBUTING、发布约定与技术参考记录跨版本覆盖范围。候选版本号和使用指南同步为 npm `0.2.0-rc.107` / Python `0.2.0rc107`。

## 0.2.0-rc.106 - 2026-11-18

rc.106 源码候选加入双端搜索归一化的全码点核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_search_unicode.py`：Python 侧按 `needs_extra` 选择补表路径，Node 侧导入桌面 `caseFold.ts`，对全部 Unicode 标量值按 0x1000 分块比较 SHA-256 摘要；不一致时列出码点区间并以退出码 2 失败。[Issue #2335](https://github.com/can4hou6joeng4/boss-harness/issues/2335)
- CI 在安装依赖前运行该检查；CONTRIBUTING、README、发布约定与技术参考补充入口和覆盖范围。候选版本号和使用指南同步为 npm `0.2.0-rc.106` / Python `0.2.0rc106`。

## 0.2.0-rc.105 - 2026-11-18

rc.105 源码候选补齐宿主通知与未使用协议常量的核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_protocol.py` 扫描 `packages/app-client` 的 `method` 字面量，要求宿主通知全部登记在 `ServerNotifications`；该常量中没有内核静态发送、宿主发送或 `DYNAMIC_KERNEL_NOTIFICATIONS` 登记的条目时失败。[Issue #2333](https://github.com/can4hou6joeng4/boss-harness/issues/2333)
- 技术参考改为六类静态不变量；README 与发布约定补充宿主通知范围。候选版本号和使用指南同步为 npm `0.2.0-rc.105` / Python `0.2.0rc105`。

## 0.2.0-rc.104 - 2026-11-18

rc.104 源码候选把变更记录纳入版本核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_versions.py` 读取 `CHANGELOG.md` 的第一个二级标题，要求与根包版本一致；不一致或缺少条目时以退出码 2 失败。[Issue #2331](https://github.com/can4hou6joeng4/boss-harness/issues/2331)
- README 与发布约定说明检查范围。候选版本号和使用指南同步为 npm `0.2.0-rc.104` / Python `0.2.0rc104`。

## 0.2.0-rc.103 - 2026-11-18

rc.103 源码候选修正 `shutdown` 的连接语义说明。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 协议注释与技术参考改为：`shutdown` 停止内核服务并返回 `{ "stopped": true }`，连接仍然可读，进程在 stdin 关闭后退出；不再声称响应后关闭连接。[Issue #2329](https://github.com/can4hou6joeng4/boss-harness/issues/2329)
- 候选版本号和使用指南同步为 npm `0.2.0-rc.103` / Python `0.2.0rc103`。

## 0.2.0-rc.102 - 2026-11-18

rc.102 源码候选补齐贡献指南的本地检查命令。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `CONTRIBUTING.md` 的本地验证命令加入 `scripts/check_versions.py` 与 `scripts/check_protocol.py`，与 CI 的构建前检查一致。[Issue #2327](https://github.com/can4hou6joeng4/boss-harness/issues/2327)
- 候选版本号和使用指南同步为 npm `0.2.0-rc.102` / Python `0.2.0rc102`。

## 0.2.0-rc.101 - 2026-11-18

rc.101 源码候选在技术参考记录构建前协议核对范围。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `docs/TECHNICAL_REFERENCE.md` 新增「构建前协议核对」，列出方法、通知、能力、桌面白名单与协议版本五类不变量，并说明静态扫描不覆盖动态方法名。[Issue #2325](https://github.com/can4hou6joeng4/boss-harness/issues/2325)
- 候选版本号和使用指南同步为 npm `0.2.0-rc.101` / Python `0.2.0rc101`。

## 0.2.0-rc.100 - 2026-11-18

rc.100 源码候选加入握手能力字段核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_protocol.py` 用 AST 提取内核 `on_initialize` 的 `capabilities` 键，并与 `InitializeResponse.capabilities` 的布尔字段双向比对。[Issue #2323](https://github.com/can4hou6joeng4/boss-harness/issues/2323)
- README 与发布约定说明检查范围。候选版本号和使用指南同步为 npm `0.2.0-rc.100` / Python `0.2.0rc100`。

## 0.2.0-rc.99 - 2026-11-18

rc.99 源码候选统一内核协议版本来源。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `harness/src/boss_harness/protocol.py`；`application.py` 与 `session_export.py` 共用 `PROTOCOL_VERSION`，导出元数据不再硬编码 `0.2.0`。[Issue #2321](https://github.com/can4hou6joeng4/boss-harness/issues/2321)
- `scripts/check_protocol.py` 核对内核与协议包常量，并拒绝在 `application.py` / `session_export.py` 重复定义。候选版本号和使用指南同步为 npm `0.2.0-rc.99` / Python `0.2.0rc99`。

## 0.2.0-rc.98 - 2026-11-18

rc.98 源码候选把桌面方法白名单纳入协议检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_protocol.py` 核对 `RENDERER_METHODS`、`THREAD_METHODS` 与 `ClientMethods`：白名单不得含协议外方法，仅主进程方法须在脚本中显式登记，线程方法必须是渲染层方法的子集。[Issue #2319](https://github.com/can4hou6joeng4/boss-harness/issues/2319)
- README 与发布约定说明检查范围。候选版本号和使用指南同步为 npm `0.2.0-rc.98` / Python `0.2.0rc98`。

## 0.2.0-rc.97 - 2026-11-18

rc.97 源码候选加入协议常量自动核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- 新增 `scripts/check_protocol.py`：比对内核 `_register()` 与 `ClientMethods`，并要求字面量通知与服务端请求都出现在 `ServerNotifications` / `ServerRequests`。Source build 在安装依赖前运行。[Issue #2317](https://github.com/can4hou6joeng4/boss-harness/issues/2317)
- 补齐 `ClientMethods.shutdown`；技术参考说明它不要求完成握手，调用后返回 `{ "stopped": true }`。候选版本号和使用指南同步为 npm `0.2.0-rc.97` / Python `0.2.0rc97`。

## 0.2.0-rc.96 - 2026-11-18

rc.96 源码候选把使用指南纳入构建前版本核对。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `scripts/check_versions.py` 要求 `docs/USER_GUIDE.md` 出现与包版本一致的 `npm <版本> / Python <版本>` 片段；缺失或不一致时退出码 2 并指出文件。[Issue #2315](https://github.com/can4hou6joeng4/boss-harness/issues/2315)
- README 与发布约定说明检查范围。候选版本号和使用指南同步为 npm `0.2.0-rc.96` / Python `0.2.0rc96`。

## 0.2.0-rc.95 - 2026-11-18

rc.95 源码候选补齐平台登录的协议方法常量。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- `ClientMethods` 增加 `platform/login/start`、`platform/login/read`、`platform/login/complete` 与 `platform/login/cancel`；桌面主进程改用常量调用，不改变 RPC 行为。[Issue #2313](https://github.com/can4hou6joeng4/boss-harness/issues/2313)
- 技术参考说明这些方法仅由宿主主进程使用，`complete` 携带的官方登录态不写入会话或日志。候选版本号和使用指南同步为 npm `0.2.0-rc.95` / Python `0.2.0rc95`。

## 0.2.0-rc.94 - 2026-11-18

rc.94 源码候选加入构建前版本检查。公开下载仍对应最新预发布 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)。

- Source build 在 `npm ci` 前核对根包、工作区、锁文件与 Python 内核版本。资产清单、隔离安装的包元数据与 CLI 显示版本使用同一个核对结果。[Issue #2308](https://github.com/can4hou6joeng4/boss-harness/issues/2308) · [PR #2309](https://github.com/can4hou6joeng4/boss-harness/pull/2309)
- README 与发布约定说明本地版本检查入口。候选版本号和使用指南同步为 npm `0.2.0-rc.94` / Python `0.2.0rc94`。[Issue #2310](https://github.com/can4hou6joeng4/boss-harness/issues/2310)

## 0.2.0-rc.93 - 2026-11-18

本节汇总第九十三个候选版本的源码与交付内容。相对 rc.92，本候选补齐关闭生命周期通知的协议常量与说明。rc.16 至 rc.93 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- `ServerNotifications` 增加 `kernelShutdown: "kernel/shutdown"`；技术参考说明它仅在宿主注入事件观察 hook、且关闭期限仍有余量时发送，客户端不得依赖它判断进程已退出（#2304、#2305）。
- 同步 npm / Python 版本到 `0.2.0-rc.93` / `0.2.0rc93`（#2306）。

升级注意：不改变 JSON-RPC 协议版本、工具数量、审批要求、内核发送时机、会话持久化格式或存储键；rc.92 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2304](https://github.com/can4hou6joeng4/boss-harness/issues/2304)：补齐 `kernel/shutdown` 生命周期通知的协议常量与说明。
- [Issue #2306](https://github.com/can4hou6joeng4/boss-harness/issues/2306)：准备 rc.93 源码候选并同步版本来源。

## 0.2.0-rc.92 - 2026-11-18

本节汇总第九十二个候选版本的源码与交付内容。相对 rc.91，本候选在技术参考中补全工具参数 schema 子集与校验边界。rc.16 至 rc.92 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 技术参考记录注册期接受的受限 JSON Schema 关键字、注册时拒绝的 `$ref` / `oneOf` / `allOf`，以及 schema 128 KiB、参数 1 MiB、JSON 深度 64、节点 32768、嵌套 schema 32 层等上限（#2300、#2301）。
- 说明运行期只校验、不填 `default`、不做隐式标量转换，并记录必填字符串的非空白声明约定与 `tool/list` 共用规范化 schema 的行为。
- 同步 npm / Python 版本到 `0.2.0-rc.92` / `0.2.0rc92`（#2302）。

升级注意：不改变 JSON-RPC 协议版本、工具数量、审批要求、会话持久化格式或存储键；rc.91 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2300](https://github.com/can4hou6joeng4/boss-harness/issues/2300)：补充工具参数 schema 子集与校验边界。
- [Issue #2302](https://github.com/can4hou6joeng4/boss-harness/issues/2302)：准备 rc.92 源码候选并同步版本来源。

## 0.2.0-rc.91 - 2026-11-18

本节汇总第九十一个候选版本的源码与交付内容。相对 rc.90，本候选统一招聘工具必填字符串参数的公开 schema 与执行校验。rc.16 至 rc.91 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- `boss_detail`、`boss_hr_jobs_detail`、`boss_hr_recommendations`、`boss_hr_resume`、`boss_hr_greet` 的必填字符串参数在 `input_schema` 中声明 `minLength: 1` 与 `pattern: \S`，与内核执行前的空白检查一致；`tool/list` 与模型请求不再接受执行时必然失败的空白值（#2295、#2296）。
- 同步 npm / Python 版本到 `0.2.0-rc.91` / `0.2.0rc91`（#2297）。

升级注意：不改变 JSON-RPC 协议版本、工具数量、审批要求、会话持久化格式或存储键；通过 `tool/list` 读取的 schema 对必填字符串更严格，rc.90 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2295](https://github.com/can4hou6joeng4/boss-harness/issues/2295)：统一必填字符串参数的空白约束。
- [Issue #2297](https://github.com/can4hou6joeng4/boss-harness/issues/2297)：准备 rc.91 源码候选并同步版本来源。

## 0.2.0-rc.90 - 2026-11-18

本节汇总第九十个候选版本的源码与交付内容。相对 rc.89，本候选在技术参考中补充服务端通知清单。rc.16 至 rc.90 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 技术参考按回合、流式内容、工具与审批、会话、队列、上下文和宿主连接分组列出 34 个 `ServerNotifications` 方法，说明 `toolCall/executing` 的可选性及双向审批使用 `item/tool/requestApproval` 服务端请求（#2290、#2291）。
- 同步 npm / Python 版本到 `0.2.0-rc.90` / `0.2.0rc90`（#2292）。

升级注意：不改变 JSON-RPC 协议版本、工具权限、会话持久化格式或存储键；rc.89 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2290](https://github.com/can4hou6joeng4/boss-harness/issues/2290)：补充服务端通知清单与兼容边界。
- [Issue #2292](https://github.com/can4hou6joeng4/boss-harness/issues/2292)：准备 rc.90 源码候选并同步版本来源。

## 0.2.0-rc.89 - 2026-11-18

本节汇总第八十九个候选版本的源码与交付内容。相对 rc.88，本候选补齐内核实际发送的 `toolCall/executing` 协议通知常量。rc.16 至 rc.89 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- `ServerNotifications` 增加 `toolCallExecuting: "toolCall/executing"`，与内核实际派发点及桌面消费的字符串一致；第三方客户端可按类型订阅工具开始执行的通知（#2285、#2286）。
- 同步 npm / Python 版本到 `0.2.0-rc.89` / `0.2.0rc89`（#2287）。

升级注意：不改变 JSON-RPC 协议版本、工具权限、会话持久化格式或存储键；rc.88 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2285](https://github.com/can4hou6joeng4/boss-harness/issues/2285)：补齐 `toolCall/executing` 通知常量。
- [Issue #2287](https://github.com/can4hou6joeng4/boss-harness/issues/2287)：准备 rc.89 源码候选并同步版本来源。

## 0.2.0-rc.88 - 2026-11-18

本节汇总第八十八个候选版本的源码与交付内容。相对 rc.87，本候选在 README 稳定能力地图中补充会话用量与按预算恢复说明。rc.16 至 rc.88 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- README 能力地图补充会话用量统计 / CSV 与按响应预算分页的会话恢复说明，不在项目概览中累积逐版本发布记录（#2280、#2281）。
- 同步 npm / Python 版本到 `0.2.0-rc.88` / `0.2.0rc88`（#2282）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.87 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2280](https://github.com/can4hou6joeng4/boss-harness/issues/2280)：补充 README 用量与持久化能力概览。
- [Issue #2282](https://github.com/can4hou6joeng4/boss-harness/issues/2282)：准备 rc.88 源码候选并同步版本来源。

## 0.2.0-rc.87 - 2026-11-18

本节汇总第八十七个候选版本的源码与交付内容。rc.86 与 rc.87 之间的后台差分探针曾报告搜索归一化大量不一致；复核确认探针把原始码点数组与归一化文本直接比较，属于无效比较。使用当前 main 的桌面 `kernelSearchText` 与内核 `search_normalize` 重新对照，三组 90,000 条语料均为 0 mismatches。rc.16 至 rc.87 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 复核搜索归一化差分语料：三组共 90,000 条输入在桌面与内核当前实现中结果一致；此前告警来自探针比较形式不同，不是源码回退（#2276）。
- 汇总 rc.84 至 rc.86 已合入的用量触发标注、响应预算分页、会话分页游标与空标识读取边界修复。
- 同步 npm / Python 版本到 `0.2.0-rc.87` / `0.2.0rc87`（#2276）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.86 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2276](https://github.com/can4hou6joeng4/boss-harness/issues/2276)：准备 rc.87 源码候选并复核搜索归一化一致性。

## 0.2.0-rc.86 - 2026-11-18

本节汇总第八十六个候选版本的源码与交付内容。相对 rc.85，本候选修正会话列表分页和空条目标识的读取边界。rc.16 至 rc.86 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 会话列表在跳过无法重建的会话后仍按有效记录保留 lookahead 与游标，后续健康会话不会因损坏行吃掉候选窗口而永久不可见（#2267、#2268）。
- 顶层条目 id 为空字符串时，普通投影与冻结快照构建一致跳过；快照分页继续要求非空、唯一 id，避免普通读取成功但快照恢复失败（#2269、#2270）。
- 技术参考同步会话分页与空标识边界（#2271、#2272）。
- 同步 npm / Python 版本到 `0.2.0-rc.86` / `0.2.0rc86`（#2273）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.85 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2267](https://github.com/can4hou6joeng4/boss-harness/issues/2267)：跳过损坏会话后保持分页游标正确。
- [Issue #2269](https://github.com/can4hou6joeng4/boss-harness/issues/2269)：统一空条目标识的读取契约。
- [Issue #2271](https://github.com/can4hou6joeng4/boss-harness/issues/2271)：会话列表分页与空条目边界说明。
- [Issue #2273](https://github.com/can4hou6joeng4/boss-harness/issues/2273)：准备 rc.86 源码候选并同步版本来源。

## 0.2.0-rc.85 - 2026-11-18

本节汇总第八十五个候选版本的源码与交付内容。相对 rc.84，本候选修正摘要任务触发方式标注，并让用量分页遵守响应预算。rc.16 至 rc.85 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 压缩任务按 `reason` 是否存在区分自动与手动；`origin` 只表示摘要作者，桌面明细、CSV 与内核会话导出不再把手动压缩误标为自动（#2260、#2261）。
- 用量分页按约 1 MiB 响应预算增量缩减本页条目数，游标绑定实际返回条数；超预算恢复提示改为用量专属信息（#2262、#2263）。
- 技术参考与协议注释同步摘要任务字段语义与用量分页边界（#2261、#2263）。
- 同步 npm / Python 版本到 `0.2.0-rc.85` / `0.2.0rc85`（#2264）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.84 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2260](https://github.com/can4hou6joeng4/boss-harness/issues/2260)：摘要任务按触发原因区分手动与自动。
- [Issue #2262](https://github.com/can4hou6joeng4/boss-harness/issues/2262)：用量页超预算时缩小分页。
- [Issue #2264](https://github.com/can4hou6joeng4/boss-harness/issues/2264)：准备 rc.85 源码候选并同步版本来源。

## 0.2.0-rc.84 - 2026-11-18

本节汇总第八十四个候选版本的源码与交付内容。相对 rc.83，本候选对齐桌面摘要任务明细的本地兜底截断方向。rc.16 至 rc.84 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 桌面 `summaryJobsOf` 保留最近 50 条摘要任务明细，与内核 `[-MAX_SUMMARY_JOBS:]` 语义一致；兼容实现返回超量明细时不再展示最旧任务（#2253、#2254）。
- 技术参考明确摘要任务明细的首份取值、最近记录保留方向与计数基准（#2255、#2256）。
- 同步 npm / Python 版本到 `0.2.0-rc.84` / `0.2.0rc84`（#2257）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.83 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2253](https://github.com/can4hou6joeng4/boss-harness/issues/2253)：摘要任务明细按最近记录截断。
- [Issue #2255](https://github.com/can4hou6joeng4/boss-harness/issues/2255)：明确摘要任务明细截断方向。
- [Issue #2257](https://github.com/can4hou6joeng4/boss-harness/issues/2257)：准备 rc.84 源码候选并同步版本来源。

## 0.2.0-rc.83 - 2026-11-18

本节汇总第八十三个候选版本的源码与交付内容。相对 rc.82，本候选对齐桌面用量原因汇总、码点计数与 CSV 导出字段。rc.16 至 rc.83 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 桌面用量原因键保留原文，超过展示上限时汇总为“其他”，原因合计始终等于未计入请求（#2246、#2249）。
- 标识、技能 id 与压缩策略 model 按 Unicode 码点计数，补充平面标识不再让整页用量失败；来源文本不再静默截断（#2246、#2249）。
- `unreportedRequests` 与 reason `missing` 一致，旧内核缺失时由原因表补齐；CSV 摘要任务无元数据时回退显示 `jobId`（#2247、#2248、#2249）。
- 内核契约同步上述边界（#2249）。
- 同步 npm / Python 版本到 `0.2.0-rc.83` / `0.2.0rc83`（#2250）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.82 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2246](https://github.com/can4hou6joeng4/boss-harness/issues/2246)：对齐用量原因合计与码点计数。
- [Issue #2247](https://github.com/can4hou6joeng4/boss-harness/issues/2247)：用 missing 原因补齐未上报请求。
- [Issue #2248](https://github.com/can4hou6joeng4/boss-harness/issues/2248)：CSV 摘要任务回退显示 jobId。
- [Issue #2250](https://github.com/can4hou6joeng4/boss-harness/issues/2250)：准备 rc.83 源码候选并同步版本来源。

## 0.2.0-rc.82 - 2026-11-18

本节汇总第八十二个候选版本的源码与交付内容。相对 rc.81，本候选对齐桌面用量回合标识字符集规则。rc.16 至 rc.82 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 桌面回合用量标识改为非空、≤128 字符的有界文本，与内核一致；含空格的历史标识不再让整页用量汇总失败（#2240、#2242）。
- 内核契约同步标识字符集边界（#2241、#2242）。
- 同步 npm / Python 版本到 `0.2.0-rc.82` / `0.2.0rc82`（#2243）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.81 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2240](https://github.com/can4hou6joeng4/boss-harness/issues/2240)：对齐桌面用量回合标识规则。
- [Issue #2243](https://github.com/can4hou6joeng4/boss-harness/issues/2243)：准备 rc.82 源码候选并同步版本来源。

## 0.2.0-rc.81 - 2026-11-18

本节汇总第八十一个候选版本的源码与交付内容。相对 rc.80，本候选补齐搜索规范合成门控，并将长组合串归一化改为线性路径。rc.16 至 rc.81 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 规范分解键及其部件、Kirat Rai GCB=V 序列进入补表门控，规范等价文本跨端取得同一搜索键（#2234、#2236）。
- 内核字素切分合并相邻 Kirat Rai V；组合类排序改为 starter 间稳定分桶，合成改为单遍扫描，长组合串不再退化成二次复杂度（#2236）。
- 内核契约同步门控与复杂度边界（#2235、#2236）。
- 同步 npm / Python 版本到 `0.2.0-rc.81` / `0.2.0rc81`（#2237）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.80 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2234](https://github.com/can4hou6joeng4/boss-harness/issues/2234)：补齐规范合成门控与字素簇边界。
- [Issue #2237](https://github.com/can4hou6joeng4/boss-harness/issues/2237)：准备 rc.81 源码候选并同步版本来源。

## 0.2.0-rc.80 - 2026-11-18

本节汇总第八十个候选版本的源码与交付内容。相对 rc.79，本候选修正冻结快照与普通读取在修订载荷、编辑标识和恢复方法名上的差异。rc.16 至 rc.80 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 修订载荷在合并前按普通投影规则清理，避免非法编号字段或 `approval` 覆盖原条目合法值（#2226、#2228）。
- 冻结快照分页与 `edit_state` 接受空字符串编辑标识，与普通展示投影一致（#2226、#2228）。
- 分支快照超限拒绝的 `recoveryMethod` 统一为 `thread/resume`（#2227、#2228）。
- 内核契约同步上述边界（#2229、#2230）。
- 同步 npm / Python 版本到 `0.2.0-rc.80` / `0.2.0rc80`（#2231）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.79 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2226](https://github.com/can4hou6joeng4/boss-harness/issues/2226)：对齐修订载荷清理与空编辑标识。
- [Issue #2227](https://github.com/can4hou6joeng4/boss-harness/issues/2227)：统一快照超限恢复方法名。
- [Issue #2231](https://github.com/can4hou6joeng4/boss-harness/issues/2231)：准备 rc.80 源码候选并同步版本来源。

## 0.2.0-rc.79 - 2026-11-18

本节汇总第七十九个候选版本的源码与交付内容。相对 rc.78，本候选对齐搜索 Unicode 17 规范分解与合成，并让冻结快照按普通读取规则清理无效编号字段。rc.16 至 rc.79 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 含补表码点的搜索先 NFKD 全分解，按桌面 Unicode 17 组合类稳定排序并逐对合成，补齐新增规范分解与合成对；跨端 9 万条差分语料全部一致（#2214、#2215）。
- 冻结快照对非字符串编号字段按缺失处理，避免修订误合并造成自洽但少条目的分页结果（#2218、#2219）。
- 用户指南与内核契约同步上述边界（#2216、#2217、#2220、#2221）。
- 同步 npm / Python 版本到 `0.2.0-rc.79` / `0.2.0rc79`（#2222）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.78 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2214](https://github.com/can4hou6joeng4/boss-harness/issues/2214)：对齐 Unicode17 规范分解与合成。
- [Issue #2218](https://github.com/can4hou6joeng4/boss-harness/issues/2218)：清理冻结快照中的无效编号字段。
- [Issue #2222](https://github.com/can4hou6joeng4/boss-harness/issues/2222)：准备 rc.79 源码候选并同步版本来源。

## 0.2.0-rc.78 - 2026-11-18

本节汇总第七十八个候选版本的源码与交付内容。相对 rc.77，本候选修复摘要任务活跃标记的标识规范化。rc.16 至 rc.78 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 摘要任务活跃标记与用量标识使用同一有界规范化，损坏 checkpoint 不再丢失 `active` 标记（#2205、#2206）。
- 内核契约同步说明该标识规则（#2208）。
- 同步 npm / Python 版本到 `0.2.0-rc.78` / `0.2.0rc78`（#2209）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.77 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2205](https://github.com/can4hou6joeng4/boss-harness/issues/2205)：对齐摘要任务活跃标记与降级标识。
- [Issue #2209](https://github.com/can4hou6joeng4/boss-harness/issues/2209)：准备 rc.78 源码候选并同步版本来源。

## 0.2.0-rc.77 - 2026-11-18

本节汇总第七十七个候选版本的源码与交付内容。相对 rc.76，本候选补齐用量来源的残留降级，并对齐搜索归一化与工具结果投影边界。rc.16 至 rc.77 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 压缩策略来源中的非法文本按会话读取规则降级，损坏的 model 不再让用量响应无法编码（#2194、#2195）。
- 内核搜索字素簇与规范排序对齐桌面 Unicode 17，特殊组合文字的命中与高亮不再分叉（#2196、#2197）。
- 损坏工具记录的模型结果投影始终守住预算，不生成不可读引用，小结果内联不因孤立代理项误判超限（#2198、#2199）。
- 用户指南与内核契约同步说明上述边界（#2200）。
- 同步 npm / Python 版本到 `0.2.0-rc.77` / `0.2.0rc77`（#2202）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.76 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2194](https://github.com/can4hou6joeng4/boss-harness/issues/2194)：降级压缩策略来源中的非法文本。
- [Issue #2196](https://github.com/can4hou6joeng4/boss-harness/issues/2196)：对齐字素组合记号与规范排序。
- [Issue #2198](https://github.com/can4hou6joeng4/boss-harness/issues/2198)：约束损坏记录的模型结果投影预算。
- [Issue #2202](https://github.com/can4hou6joeng4/boss-harness/issues/2202)：准备 rc.77 源码候选并同步版本来源。

## 0.2.0-rc.76 - 2026-11-18

本节汇总第七十六个候选版本的源码与交付内容。相对 rc.75，本候选让单条损坏的用量来源记录不再遮住整份只读用量。rc.16 至 rc.76 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 用量来源与回合编号沿用会话读取的文本降级规则，损坏记录不再让用量面板或只读导出整体失败（#2187、#2188）。
- 用户指南与内核契约同步说明用量来源的有界化边界（#2190）。
- 同步 npm / Python 版本到 `0.2.0-rc.76` / `0.2.0rc76`（#2191）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.75 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2187](https://github.com/can4hou6joeng4/boss-harness/issues/2187)：限制用量来源字段的非法文本。
- [Issue #2191](https://github.com/can4hou6joeng4/boss-harness/issues/2191)：准备 rc.76 源码候选并同步版本来源。

## 0.2.0-rc.75 - 2026-11-18

本节汇总第七十五个候选版本的源码与交付内容。相对 rc.74，本候选新增一次恢复的共享正文分页预算，并收敛摘要面板无法确定任务时的本地界面状态。rc.16 至 rc.75 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 一次桌面会话恢复新增共享正文分页总预算，异常内核无法用大量小字段放大往返次数；超预算明确失败且不展示部分正文（#2178、#2179）。
- 摘要面板处理未知开始、终态详情不可读与连续核对失败，收敛本地运行状态并解除界面锁；内核仍是任务与并发权威（#2180、#2181）。
- 用户指南、桌面指南与内核契约同步说明上述恢复预算和面板释放边界（#2182）。
- 同步 npm / Python 版本到 `0.2.0-rc.75` / `0.2.0rc75`（#2184）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.74 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2178](https://github.com/can4hou6joeng4/boss-harness/issues/2178)：为一次会话恢复设置共享正文分页预算。
- [Issue #2180](https://github.com/can4hou6joeng4/boss-harness/issues/2180)：收敛摘要面板未知开始与释放状态。
- [Issue #2182](https://github.com/can4hou6joeng4/boss-harness/issues/2182)：记录恢复总预算与摘要面板释放边界。
- [Issue #2184](https://github.com/can4hou6joeng4/boss-harness/issues/2184)：准备 rc.75 源码候选并同步版本来源。

## 0.2.0-rc.74 - 2026-11-18

本节汇总第七十四个候选版本的源码与交付内容。相对 rc.73，本候选收紧大正文恢复分页预算并修正摘要取消失败分类。rc.16 至 rc.74 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 大正文恢复加入有限分页预算，异常内核用超小分段时明确失败，不展示部分正文（#2169、#2170）。
- 摘要任务不存在时，取消回执收敛本地 running 状态并说明不会重放；其他失败仍按回执未知处理（#2171、#2172）。
- 用户指南、桌面指南与内核契约同步说明这两类边界。
- 同步 npm / Python 版本到 `0.2.0-rc.74` / `0.2.0rc74`（#2175）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.73 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2169](https://github.com/can4hou6joeng4/boss-harness/issues/2169)：限制大正文恢复分页预算。
- [Issue #2171](https://github.com/can4hou6joeng4/boss-harness/issues/2171)：识别摘要任务已不存在的取消回执。
- [Issue #2175](https://github.com/can4hou6joeng4/boss-harness/issues/2175)：准备 rc.74 源码候选并同步版本来源。

## 0.2.0-rc.73 - 2026-11-18

本节汇总第七十三个候选版本的源码与交付内容。相对 rc.72，本候选打通陈旧引用错误通道并补齐契约说明。rc.16 至 rc.73 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 桌面结果/正文读取保留结构化 `RPC` 错误并统一解包，合法 `currentRef` 的核对提示真正可达；非法引用仍按通用错误展示（#2160、#2161）。
- 内核契约同步说明错误通道边界。
- 同步 npm / Python 版本到 `0.2.0-rc.73` / `0.2.0rc73`（#2166）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.72 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2160](https://github.com/can4hou6joeng4/boss-harness/issues/2160)：打通陈旧引用错误通道。
- [Issue #2166](https://github.com/can4hou6joeng4/boss-harness/issues/2166)：准备 rc.73 源码候选并同步版本来源。

## 0.2.0-rc.72 - 2026-11-18

本节汇总第七十二个候选版本的源码与交付内容。相对 rc.71，本候选补齐桌面陈旧正文引用提示。rc.16 至 rc.72 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 桌面恢复识别 `STALE_CONTENT` 且含合法 `currentRef` 的错误，提示重新打开会话并核对当前引用；非法引用数据仍按通用错误展示（#2154、#2155）。
- 桌面指南同步说明陈旧正文引用提示边界。
- 同步 npm / Python 版本到 `0.2.0-rc.72` / `0.2.0rc72`（#2157）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.71 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2154](https://github.com/can4hou6joeng4/boss-harness/issues/2154)：明确大正文陈旧内容引用提示。
- [Issue #2157](https://github.com/can4hou6joeng4/boss-harness/issues/2157)：准备 rc.72 源码候选并同步版本来源。

## 0.2.0-rc.71 - 2026-11-18

本节汇总第七十一个候选版本的源码与交付内容。相对 rc.70，本候选补齐桌面陈旧结果引用提示。rc.16 至 rc.71 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 桌面分段读取识别 `STALE_RESULT / currentRef` 并提示重新核对当前引用；非法引用数据仍按通用错误处理，不自动改写引用或继续拼接旧分段（#2148、#2149）。
- 桌面指南与 CHANGELOG 同步说明该提示边界（#2150）。
- 同步 npm / Python 版本到 `0.2.0-rc.71` / `0.2.0rc71`（#2151）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.70 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2148](https://github.com/can4hou6joeng4/boss-harness/issues/2148)：识别桌面陈旧结果引用提示。
- [Issue #2151](https://github.com/can4hou6joeng4/boss-harness/issues/2151)：准备 rc.71 源码候选并同步版本来源。

# 变更记录

## 0.2.0-rc.70 - 2026-11-18

本节汇总第七十个候选版本的源码与交付内容。相对 rc.69，本候选统一历史模型结果投影与分块读取的摘要口径，并同步桌面与契约说明。rc.16 至 rc.70 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 投影与两条分块读取路径共享规范化结果文本；深度超限、非有限浮点等旧记录的结果引用可直接读取，不再首次返回 `STALE_RESULT`（#2140、#2141）。
- 桌面指南与内核契约同步说明引用和分段读取使用同一版本，过期引用按 `currentRef` 重新核对（#2142、#2143）。
- 同步 npm / Python 版本到 `0.2.0-rc.70` / `0.2.0rc70`（#2144）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.69 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2140](https://github.com/can4hou6joeng4/boss-harness/issues/2140)：统一历史结果引用与分块读取摘要。
- [Issue #2144](https://github.com/can4hou6joeng4/boss-harness/issues/2144)：准备 rc.70 源码候选并同步版本来源。

## 0.2.0-rc.69 - 2026-11-18

本节汇总第六十九个候选版本的源码与交付内容。相对 rc.68，本候选修正旧失败条目的重试提示，并补齐工具状态、压缩配置错误与来源时间的用户说明。rc.16 至 rc.69 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 旧失败历史条目按工具名识别写工具，不能确认时不再输出可安全重试提示（#2132、#2133）。
- 使用指南区分工具卡状态标签与模型可见结果字段，说明结果不确定时先核对平台状态（#2127、#2128、#2131）。
- 文档索引补充结果状态契约入口；自动压缩线路不可用时明确说明暂停语义与错误码（#2129、#2134、#2135）。
- 工具来源时间注明为该次工具调用的事实快照，缓存命中不保证每次都访问平台（#2136）。
- 同步 npm / Python 版本到 `0.2.0-rc.69` / `0.2.0rc69`（#2137）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.68 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2127](https://github.com/can4hou6joeng4/boss-harness/issues/2127)：说明工具结果状态与重试提示。
- [Issue #2132](https://github.com/can4hou6joeng4/boss-harness/issues/2132)：按工具名判定旧失败重试提示。
- [Issue #2134](https://github.com/can4hou6joeng4/boss-harness/issues/2134)：说明自动压缩配置失败的暂停语义。
- [Issue #2137](https://github.com/can4hou6joeng4/boss-harness/issues/2137)：准备 rc.69 源码候选并同步版本来源。

## 0.2.0-rc.68 - 2026-11-18

本节汇总第六十八个候选版本的源码与交付内容。相对 rc.67，本候选向模型暴露工具执行状态与重试安全提示，并修正隔离构建、结果引用与压缩错误映射。rc.16 至 rc.68 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 工具结果显示 `executionState` 与 `disposition`，区分未派发、结果不确定、失败与只读 / 写工具的重试安全提示；历史回放和持久化失败路径同步修正（#2123、#2124）。
- 三类陈旧引用错误返回当前摘要，客户端无需猜测新版本引用（#2121、#2122）。
- 摘要线路配置失败在压缩回合中映射为明确错误；隔离归档构建不再因缺少 `.git` 而失败；README 只读会话工具数量与实现对齐（#2115、#2117、#2119）。
- 同步 npm / Python 版本到 `0.2.0-rc.68` / `0.2.0rc68`（#2125）；使用指南补充结果状态与重试提示的用户说明（#2127）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.67 源码无需迁移。模型可见结果新增可选字段，旧客户端忽略即可；协议与内核仍为 `0.2.0`。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2115](https://github.com/can4hou6joeng4/boss-harness/issues/2115)：隔离归档构建允许生成发布清单。
- [Issue #2117](https://github.com/can4hou6joeng4/boss-harness/issues/2117)：修正只读会话工具数量。
- [Issue #2119](https://github.com/can4hou6joeng4/boss-harness/issues/2119)：压缩配置失败映射为明确错误。
- [Issue #2121](https://github.com/can4hou6joeng4/boss-harness/issues/2121)：陈旧引用错误返回当前摘要。
- [Issue #2123](https://github.com/can4hou6joeng4/boss-harness/issues/2123)：工具结果暴露执行状态与重试提示。
- [Issue #2125](https://github.com/can4hou6joeng4/boss-harness/issues/2125)：准备 rc.68 源码候选并同步版本来源。

## 0.2.0-rc.67 - 2026-11-18

本节汇总第六十七个候选版本的源码与交付内容。相对 rc.66，本候选把发布清单的 `sourceCommit` 绑定到实际可解析的源码提交，并记录 CI 触发 ref。rc.16 至 rc.67 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 发布清单脚本用 `git rev-parse --verify` 确认 `--commit` 可解析，避免任意十六进制串伪装成来源提交（#2106、#2111）。
- 可选的 `--source-ref` 记录实际触发来源；CI 传入 `$GITHUB_REF`，发布文档说明 PR 临时 merge ref 的可复现范围与稳定发布要求（#2106、#2111）。
- 同步 npm / Python 版本到 `0.2.0-rc.67` / `0.2.0rc67`（#2112）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.66 源码无需迁移。发布清单 schemaVersion 仍为 `2`；无 Git 的离线构建仍只校验提交格式，不能声称已验证提交存在。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2106](https://github.com/can4hou6joeng4/boss-harness/issues/2106)：绑定发布清单来源提交与构建 ref。
- [Issue #2112](https://github.com/can4hou6joeng4/boss-harness/issues/2112)：准备 rc.67 源码候选并同步所有版本来源。

## 0.2.0-rc.66 - 2026-11-18

本节汇总第六十六个候选版本的源码与交付内容。相对 rc.65，本候选补齐发布资产身份与清单契约校验，并修正隔离构建文档。rc.16 至 rc.66 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 发布资产校验覆盖 wheel / sdist 文件名、sdist 根目录、内部 `pyproject.toml` 的包名与版本、源版本一致性，以及大小写不敏感的保留名冲突；CI 生成清单后校验摘要（#2102、#2104）。
- 隔离构建文档使用 `set -euo pipefail`、显式进入 `git archive` 目录并断言关键文件；补全 rc.15 与 schemaVersion 2 的清单字段差异（#2103、#2105）。
- 修正 rc.65 变更记录中把 PR #2097 标成 Issue 的链接（#2100、#2101）。
- 非法 METADATA 版本改为返回 `release-assets:` 可读错误，不再抛出未处理异常（#2107、#2108）。
- 同步 npm / Python 版本到 `0.2.0-rc.66` / `0.2.0rc66`（#2109）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.65 源码无需迁移。发布清单的 schemaVersion 仍为 `2`，`SHA256SUMS.txt` 仍覆盖清单自身。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2100](https://github.com/can4hou6joeng4/boss-harness/issues/2100)：修正 rc.65 版本准备链接。
- [Issue #2102](https://github.com/can4hou6joeng4/boss-harness/issues/2102)：完整校验发布资产身份与清单契约。
- [Issue #2103](https://github.com/can4hou6joeng4/boss-harness/issues/2103)：修正隔离构建命令与清单字段说明。
- [Issue #2107](https://github.com/can4hou6joeng4/boss-harness/issues/2107)：非法元数据版本返回可读错误。
- [Issue #2109](https://github.com/can4hou6joeng4/boss-harness/issues/2109)：准备 rc.66 源码候选并同步所有版本来源。

## 0.2.0-rc.65 - 2026-11-18

本节汇总第六十五个候选版本的源码与交付内容。相对 rc.64，本候选补齐发布资产归属、安装版本、清单契约与构建来源校验。rc.16 至 rc.65 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 版本元数据校验复用 SHA-256 同一文件描述符，避免哈希与校验对象不一致（#2089、#2092）。
- 发布资产按 `pyproject.toml` 核对 wheel / sdist 的 Name 与内部版本，CI 隔离安装后核对 dist-info 版本（#2090、#2094）。
- 发布清单提升到 `schemaVersion: 2`，`SHA256SUMS.txt` 覆盖清单；发布构建固定从 `git archive` 隔离目录取源码（#2095–#2097）。
- 修正 RELEASING 的版本归一与构建说明；同步 npm / Python 版本到 `0.2.0-rc.65` / `0.2.0rc65`（#2091、#2093、#2098）。

升级注意：不改变 JSON-RPC 协议、工具权限、会话持久化格式或存储键；rc.64 源码无需迁移。构建产物 `build-info.json` 的 schemaVersion 从 `1` 提升到 `2`，按该字段分流的发布核对工具需要更新；`SHA256SUMS.txt` 现包含清单自身摘要。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2089](https://github.com/can4hou6joeng4/boss-harness/issues/2089)：修复发布资产版本校验的 TOCTOU。
- [Issue #2090](https://github.com/can4hou6joeng4/boss-harness/issues/2090)：校验发布资产名称与安装版本。
- [Issue #2091](https://github.com/can4hou6joeng4/boss-harness/issues/2091)：修正版本归一与构建说明。
- [Issue #2095](https://github.com/can4hou6joeng4/boss-harness/issues/2095)：统一发布清单契约与摘要覆盖。
- [Issue #2096](https://github.com/can4hou6joeng4/boss-harness/issues/2096)：发布构建只使用已跟踪源码。
- [PR #2098](https://github.com/can4hou6joeng4/boss-harness/pull/2098)：准备 rc.65 源码候选并同步所有版本来源。

## 0.2.0-rc.64 - 2026-11-18

本节汇总第六十四个候选版本的源码与交付内容。相对 rc.63，本候选仅补齐首页开发验证命令与构建依赖说明。rc.16 至 rc.64 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- README「开发与验证」补齐 `uv venv` 与 `packaging`，CONTRIBUTING 的本地构建依赖同步（#2085、#2086）。
- 同步 npm / Python 版本到 `0.2.0-rc.64` / `0.2.0rc64`（#2087）。

升级注意：不改变协议、工具权限、持久化格式或存储键；rc.63 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2085](https://github.com/can4hou6joeng4/boss-harness/issues/2085)：补齐开发构建前置命令。
- [Issue #2087](https://github.com/can4hou6joeng4/boss-harness/issues/2087)：准备 rc.64 源码候选并同步所有版本来源。

## 0.2.0-rc.63 - 2026-11-18

本节汇总第六十三个候选版本的源码与交付内容。相对 rc.62，本候选仅明确包注册表的实际分发状态，不改变发布流程或产物。rc.16 至 rc.63 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- RELEASING 明确 npm / PyPI 当前未实际发布，仅作为需单独授权的可选渠道；GitHub Releases 是实际发布资产的权威入口（#2081、#2082）。
- 同步 npm / Python 版本到 `0.2.0-rc.63` / `0.2.0rc63`（#2083）。

升级注意：不改变协议、工具权限、持久化格式或存储键；rc.62 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2081](https://github.com/can4hou6joeng4/boss-harness/issues/2081)：明确注册表分发状态。
- [Issue #2083](https://github.com/can4hou6joeng4/boss-harness/issues/2083)：准备 rc.63 源码候选并同步所有版本来源。

## 0.2.0-rc.62 - 2026-11-18

本节汇总第六十二个候选版本的源码与交付内容。相对 rc.61，本候选仅补齐浏览器来源、工具结果读取与 CLI 信封校验的文档口径。rc.16 至 rc.62 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 浏览器来源环境变量的取值规范化规则写入使用指南与技术参考（#2073、#2074）。
- 技术参考补充模型侧与桌面/RPC 侧工具结果读取预算不同的职责边界（#2075、#2076）。
- 合并技术参考中重复的 `boss-agent-cli --json` 校验说明，避免后续单处修改造成契约冲突（#2077、#2078）。
- 同步 npm / Python 版本到 `0.2.0-rc.62` / `0.2.0rc62`（#2079）。

升级注意：不改变协议、工具权限、持久化格式或存储键；rc.61 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2073](https://github.com/can4hou6joeng4/boss-harness/issues/2073)：说明浏览器来源取值规范化。
- [Issue #2075](https://github.com/can4hou6joeng4/boss-harness/issues/2075)：说明工具结果读取边界。
- [Issue #2077](https://github.com/can4hou6joeng4/boss-harness/issues/2077)：合并重复的 CLI JSON 校验说明。
- [Issue #2079](https://github.com/can4hou6joeng4/boss-harness/issues/2079)：准备 rc.62 源码候选并同步所有版本来源。

## 0.2.0-rc.61 - 2026-11-18

本节汇总第六十一个候选版本的源码与交付内容。相对 rc.60，本候选修正仓库状态与用户文档口径，并加强发布资产的版本与目录归属校验。rc.16 至 rc.61 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 仓库状态文档改为公开仓库与公开 Issue 入口；MIT 许可证与远程仓库不再列为待确定项，历史回合中的旧状态标为当时快照（#2065、#2066）。
- 只读会话明确包含 13 个只读招聘工具和 1 个只读内核结果分段读取工具；草稿持久化说明补充首页项目与历史调取前原稿（#2067、#2068）。
- 发布资产清单按 PEP 440 归一版本，逐一核对 wheel / sdist 元数据并拒绝输出目录外文件；构建流程安装 packaging，RELEASING 要求先清空重建 `dist/python`（#2069、#2070）。
- 同步 npm / Python 版本到 `0.2.0-rc.61` / `0.2.0rc61`（#2071）。

升级注意：不改变协议、工具权限、持久化格式或存储键；rc.60 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2065](https://github.com/can4hou6joeng4/boss-harness/issues/2065)：更新仓库可见性与许可证状态文档。
- [Issue #2067](https://github.com/can4hou6joeng4/boss-harness/issues/2067)：修正工具数与草稿恢复范围文档。
- [Issue #2069](https://github.com/can4hou6joeng4/boss-harness/issues/2069)：校验发布资产版本与目录归属。
- [Issue #2071](https://github.com/can4hou6joeng4/boss-harness/issues/2071)：准备 rc.61 源码候选并同步所有版本来源。

## 0.2.0-rc.60 - 2026-11-18

本节汇总第六十个候选版本的源码与交付内容。相对 rc.59，本候选同步缺陷报告模板的版本示例，并把发布脚本与表单示例改为稳定占位，避免每轮候选追改。rc.16 至 rc.60 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 缺陷报告模板的版本示例同步到当前候选，并在 RELEASING 的版本同步步骤明确检查社区模板（#2059、#2060）。
- 发布资产脚本和缺陷模板改用稳定版本占位，RELEASING 明确稳定示例不随候选号修改（#2061、#2062）。
- 同步 npm / Python 版本到 `0.2.0-rc.60` / `0.2.0rc60`（#2063）。

升级注意：不改变协议、工具权限、持久化格式或存储键；rc.59 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2059](https://github.com/can4hou6joeng4/boss-harness/issues/2059)：同步缺陷报告模板版本示例。
- [Issue #2061](https://github.com/can4hou6joeng4/boss-harness/issues/2061)：改用稳定的版本示例文案。
- [Issue #2063](https://github.com/can4hou6joeng4/boss-harness/issues/2063)：准备 rc.60 源码候选并同步所有版本来源。

## 0.2.0-rc.59 - 2026-11-18

本节汇总第五十九个候选版本的源码与交付内容。相对 rc.58，本候选统一业务 CLI 可用性检查，并同步发布脚本示例与摘要 checkpoint 文档。rc.16 至 rc.59 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 连接检查与工具可用性报告复用同一套可执行路径判定：普通文件与有效符号链接可用，目录、断链和不可执行文件不可用；不带路径的命令名仍由 PATH 查找，不执行业务 CLI（#2051、#2052）。
- 发布资产脚本的帮助与错误提示同步到当前 Python 版本示例，不改变版本校验或资产计算（#2053、#2054）。
- 技术参考同步摘要 checkpoint 的目录项同步保证，与当前内核实现一致（#2055、#2056）。
- 同步 npm / Python 版本到 `0.2.0-rc.59` / `0.2.0rc59`（#2057）。

升级注意：不改变协议、工具权限、持久化格式或存储键；rc.58 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2051](https://github.com/can4hou6joeng4/boss-harness/issues/2051)：统一 `resolve_binary()` 与 `binary_available()` 的业务 CLI 路径判定。
- [Issue #2053](https://github.com/can4hou6joeng4/boss-harness/issues/2053)：更新发布资产脚本的版本示例。
- [Issue #2055](https://github.com/can4hou6joeng4/boss-harness/issues/2055)：更新摘要 checkpoint 持久化文档口径。
- [Issue #2057](https://github.com/can4hou6joeng4/boss-harness/issues/2057)：准备 rc.59 源码候选并同步所有版本来源。

## 0.2.0-rc.58 - 2026-11-18

本节汇总第五十八个候选版本的源码与交付内容。相对 rc.57，本候选修正浏览器来源空白值处理、业务 CLI 可执行文件查找，并整理大型历史变更记录。rc.16 至 rc.58 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- `BOSS_HARNESS_BROWSER_SOURCE` 为空或仅含空白时按未设置处理，不再让模板填充的空白阻断内核启动（#2043、#2044）。
- 业务 CLI 查找跳过目录、断链和不可执行候选，同时保留对正常可执行符号链接的支持；显式路径、环境变量、并排安装与 PATH 的优先级不变（#2045 / #2046、#2047 / #2048）。
- 将 rc.15 的 558 KB 逐项探针与验证日志移至独立归档，CHANGELOG 保留用户可读概览与兼容变化，并在文档索引中提供归档入口（#2038、#2041）。
- 同步 npm / Python 版本到 `0.2.0-rc.58` / `0.2.0rc58`（#2049）。

升级注意：不改变协议、工具权限、持久化格式或存储键；rc.57 源码无需迁移。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2043](https://github.com/can4hou6joeng4/boss-harness/issues/2043)：浏览器来源空白值不再触发 `BROWSER_SOURCE_INVALID`。
- [Issue #2045](https://github.com/can4hou6joeng4/boss-harness/issues/2045)：CLI 可执行文件查找核对候选类型与执行权限，避免无效并排安装遮住 PATH。
- [Issue #2047](https://github.com/can4hou6joeng4/boss-harness/issues/2047)：保留 Python 虚拟环境中有效的可执行符号链接，修正上一项的过严校验。
- [Issue #2038](https://github.com/can4hou6joeng4/boss-harness/issues/2038)：ARCHIVE rc.15 详细验证记录并保持 CHANGELOG 可读。
- [Issue #2049](https://github.com/can4hou6joeng4/boss-harness/issues/2049)：准备 rc.58 源码候选并同步所有版本来源。

## 0.2.0-rc.57 - 2026-11-18

本节汇总第五十七个候选版本的源码与交付内容。相对 rc.56，本候选只整理项目首页、文档与仓库元数据，不改变协议、工具权限、持久化格式或运行时行为。rc.16 至 rc.57 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

- 首页不再承载逐批修复计数与候选自检细节；版本状态压缩为稳定说明，新增可执行的快速开始与桌面交互指南入口（#2030、#2031）。
- 统一 README、CONTRIBUTING、RELEASING 与内核包的构建 / 安装口径，删除未发布 PyPI 安装示例，清理使用指南与技术参考中的候选期措辞（#2032、#2033）。
- 补齐根包 repository / homepage / bugs 元数据与完整描述；桌面根目录探测改以 npm workspaces 清单为准，删除过期的 pnpm 工作区声明（#2034、#2035）。
- 增加行为准则、支持与问题分流及文档索引，Issue 模板链接支持入口（#2036、#2037）。
- 同步 npm / Python 版本到 `0.2.0-rc.57` / `0.2.0rc57`（#2039）。

升级注意：仅文档、元数据与版本来源变化；已安装的 rc.56 源码无需迁移，协议与内核仍为 `0.2.0`。交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist；桌面从源码构建，尚无独立签名安装包，真实模型与招聘平台验收仍未执行。候选准备不代表已创建 tag、Release、资产上传或注册表发布。

### 变更

- [Issue #2030](https://github.com/can4hou6joeng4/boss-harness/issues/2030)：README 从逐批发布流水账收敛为项目入口页，新增桌面交互指南，发布流程不再要求向首页追加近期进展。
- [Issue #2032](https://github.com/can4hou6joeng4/boss-harness/issues/2032)：统一 uv / .venv 构建命令，修正配置优先级指针与内核包安装说明；候选状态只保留在变更记录与 Release。
- [Issue #2034](https://github.com/can4hou6joeng4/boss-harness/issues/2034)：补齐 npm 仓库元数据，根目录探测不再依赖 pnpm 工作区文件。
- [Issue #2036](https://github.com/can4hou6joeng4/boss-harness/issues/2036)：补齐行为准则、支持分流和文档索引，明确安全报告与社区参与渠道。
- [Issue #2039](https://github.com/can4hou6joeng4/boss-harness/issues/2039)：准备 rc.57 源码候选并同步所有版本来源。

## 0.2.0-rc.56 - 2026-11-16 起持续汇总

本节汇总第五十六个候选版本的源码与交付内容；rc.16 至 rc.56 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.55，本次包含 151 项修复、1 项界面改进与 1 项打包元数据改进：技能标签查询命中原型链（#1585、#1586）；队列元数据少于可见明细（#1587、#1588）；审批按会话计数少于可见条目（#1591、#1592）；用量请求计数与验证分类合计矛盾（#1595、#1596）；会话冻结快照条目数不完整（#1599、#1600）；会话条目缺少标识或重复（#1603、#1604）；用量回合重复或数量不一致（#1607、#1608）；导出已导出回合数超过声明总数（#1611、#1612）；未截断审批计数大于可见条目（#1615、#1616）；运行资源计数超过容量（#1619、#1620）；会话索引计数为零却列出不可读 id（#1623、#1624）；摘要任务引用未校验形状（#1627、#1628）；分支摘要标记条目未校验形状（#1631、#1632）；分支端点与回合分页条目未校验形状（#1635、#1636）；会话列表条目未校验形状（#1639、#1640）；技能目录条目未校验形状（#1643、#1644）；模型列表条目未校验形状（#1647、#1648）；工具清单条目未校验形状（#1651、#1652）；连接检查回执未校验形状（#1655、#1656）；恢复快照未校验会话身份（#1659、#1660）；会话写操作回执未校验形状（#1663、#1664）；技能与工具页展示工具执行模式（#1667、#1668）；登录状态回执未校验形状（#1671、#1672）；设置页登录状态同样未校验形状（#1675、#1676）；主进程登录回执未校验形状（#1679、#1680）；跨会话搜索命中未校验形状（#1683、#1684）；会话错误通知正文未校验形状（#1687、#1688）；上下文预算回执未校验形状（#1691、#1692）；工作区说明状态与字节数未校验（#1695、#1696）；上下文整理计划回执未校验形状（#1699、#1700）；上下文编辑不可编辑原因未校验形状（#1702、#1703）；摘要任务展示字段未校验形状（#1705、#1706）；畸形队列标识中断任务读取（#1708、#1709）；冻结快照非对象条目按损坏处理（#1711、#1712）；附件对象非 UTF-8 时按内容损坏处理（#1714、#1715）；续接预检回执未校验展示字段（#1717、#1718）；回合载荷伪造分支边界序号（#1720、#1721）；StrictMode 重跑副作用后批量队列操作卡在 0/N（#1723、#1724）；投影索引的损坏路径阻断内核启动（#1726、#1727）；分页快照的回合投影元数据被改写为非字符串时按损坏投影重建索引（#1729、#1730）；压缩任务恢复不再解析持久投影里的游标数字（#1732、#1733）；断连时三个读取 effect 提前返回不复位读取态（#1735、#1736）；附件摘要非字符串时按损坏记录处理（#1738、#1739）；附件添加路径必须是普通文件（#1740、#1741）；超长技能目录名按未加载项上报（#1743、#1744）；技能目录不可读时按读取失败报错（#1746、#1747）；工作区说明首选路径不可读时如实上报（#1749、#1750）；用量弹窗拒绝重复的摘要任务标识（#1752、#1753）；技能正文回执校验形状与归属（#1755、#1756）；技能新建与修改回执校验归属（#1758、#1759）；内核包补齐包描述、关键词、分类器与项目链接（#1765、#1766）；推理设置回执校验提示与轮询字段（#1768、#1769）；分支摘要任务复用完整形状校验（#1771、#1772）；工作区说明保存回执用于展示真实状态（#1774、#1775）；审批撤销只认字符串回合状态（#1777、#1778）；事件卡片标识只接受字符串（#1780、#1781）；回合标识只接受字符串（#1783、#1784）；快照编辑状态标识只接受字符串（#1786、#1787）；导出路径降级孤立代理项（#1789、#1790）；索引库文本列非法 UTF-8 按替换字符解码（#1792、#1793）；分支摘要读取取到同 id 的错误记录（#1795、#1796）；事件索引行缺少游标仍被接受（#1798、#1799）；分支回合分页未校验投影列类型（#1801、#1802）；队列身份匹配未校验持久状态（#1804、#1805）；压缩任务恢复事件缺少必读字段（#1807、#1808）；上下文编辑排除工具批次助手后历史投影永久失败（#1810、#1811）；中断结算的工具结果丢失持久摘要（#1815、#1816）；超深嵌套工具参数让会话读取与导出返回内部错误（#1817、#1818）；空回合锚定的分支摘要让自动压缩前缀比对恒失败（#1819、#1820）；内核伪造的断开通知让宿主销毁健康进程（#1822、#1823）；畸形审批超时配置让审批请求静默判为过期（#1824、#1825）；超长请求 id 的错误回包逃逸成主进程致命错误（#1826、#1827）；缺登录尝试编号的回执锁死登录状态机（#1828、#1829）；内核伪造的连接状态清空回合跟踪与界面状态（#1830、#1831）；重复条目编号让编辑误伤或让历史永久失败（#1832、#1833）；恢复增量字段未校验让内核启动退出（#1835、#1836）；队列只读投影保留未知或超长字段（#1837、#1838）；近限长请求 id 的协议错误帧逃逸（#1839、#1840）；畸形审批截止时间被当作已过期（#1841、#1842）；条目完成通知跨会话撤销审批（#1843、#1844）；队列单项回执未收敛损坏可选字段（#1845、#1846）；损坏上下文编辑让展示路径整段失败（#1847、#1848）；损坏叶指针让分支投影整体失败（#1849、#1850）；损坏审批索引列让待审批列表返回内部错误（#1851、#1852）；畸形回包被丢弃后空等超时（#1853、#1854）；内核无任务记录时压缩入口永久锁死（#1855、#1856）；分支摘要终态回执不可解析锁死分支（#1858、#1859）；投影索引缺 id 或游标列被改写退化为内部错误（#1860、#1861）；快照条目缺 id 抛 KeyError（#1862、#1863）；损坏审批索引行卡死过期结算（#1864、#1865）；事件方法列被改写为 BLOB（#1866、#1867）；畸形待决审批让归档失败并留下伪裁决（#1868、#1869）；旧终态任务引用让「开始结果待核对」永不收敛（#1870、#1871）；摘要详情持续无法核对锁死压缩入口（#1872、#1873）；自动压缩线路字段畸形让整页崩溃（#1874、#1875）；投影与源日志双损坏阻断内核启动（#1876、#1877）；错误帧无法编码时内核退出（#1878、#1879）；持久审批裁决后未释放宿主路由与待答槽位（#1880、#1881）；合法上游错误的恢复动作为 null 时被判无效（#1884、#1885）；工作区符号链接环让内核启动退出（#1886、#1887）；恢复快照线路字段畸形让整页崩溃（#1888、#1889）；投影时间与标题字段类型损坏让列表无法编码（#1890、#1892）；导出超大整数期限溢出与标识脱敏缺口（#1891、#1893）；配置文件深层嵌套或孤立代理项让自动压缩设置保存返回内部错误（#1896、#1899）；分支摘要辅助字段无长度上限让压缩后仍超预算（#1897、#1900）；缺失结果的错误码未限制长度突破模型结果预算（#1898、#1901）；启动恢复无界累加流式增量，超长恢复条目让内核整体启动失败（#1904、#1907）；steering 队列项缺少预期回合时领取崩溃（#1905、#1906）；损坏检查点的来源摘要无格式校验，注入历史后永久超预算（#1910、#1913）；损坏的用量基线伪造出 10^12 token 预算（#1911、#1914）；检查点未知字段让 context/read 永久超帧（#1912、#1915）；工具批次的助手引用悬空时降级为普通批次，分支不再永久失败（#1918、#1919）；Anthropic 流式增量与活动块类型错置时被静默接受，错置文本落库让分支永久失败（#1922、#1924）；工具调用缺失、空值或重复标识在截断路径落库后让历史永久对不上工具批次（#1923、#1925）；OpenAI 输出项索引跨类型复用让工具调用被静默丢弃（#1928、#1933）；杂散文本增量被落库成助手消息（#1929、#1933）；工具调用标识缺少长度上限导致回合未捕获失败（#1930、#1933）；协议输出未固定 UTF-8，非 UTF-8 stdout 下零字节回包或内核退出（#1931、#1932）；会话导出对深嵌套持久字段、路径标点截断与审批字段未脱敏（#1936、#1937）；被跳过的工具调用落库前未净化非可编码参数，未执行结算被击穿（#1938、#1939）；过期审批清扫对损坏会话 20 Hz 空转且计数与列表不一致（#1942、#1943）；压缩任务恢复载荷无界且终态通知失败时内核整体退出（#1946、#1950）；技能根目录为符号链接时越过工作区读取（#1947、#1951）；分支摘要辅助标识缺少长度校验，9 MiB 字段进入公开投影（#1948、#1951）；压缩恢复只比较摘要任务标识，投影判为无效的检查点仍被当作已提交（#1949、#1950）；旧内核分支视图兼容路径漏掉线路字段与条目数组校验，畸形快照让整个应用落入错误边界（#1955、#1957）；Markdown 行内与围栏正则对超长合法单行平方级回溯，渲染主线程冻结（#1956、#1957）；内核状态回执的线路字段未校验，畸形 provider 在渲染期让整个应用落入错误边界（#1960、#1962）；草稿存储与标签查询把外部字符串当普通对象键，`__proto__` 草稿丢失、失败码与账号状态显示函数源码（#1961、#1962）；恢复循环写回超限阻断内核启动，超长队列正文让 queue/get 永久超帧（#1965、#1966）；事件页在存储锁内解析全部索引行，大事件回放占用数 GiB（#1969、#1970）；工具结果分块读取每页重复全文摘要，翻页成本随结果大小平方增长（#1971、#1972）；冻结快照触达磁盘预算时抛出 sqlite3 内部错误，队列载荷绕过条目预算（#1975、#1977）；重复条目 id 在冻结快照中产生两条记录，内容读取取到旧修订（#1976、#1977）；附件配额扫描每次重设全部对象权限，填满配额的成本平方增长（#1979、#1981）；非分页 thread/read 与条目列表把同一份 rollout 解码两遍（#1973、#1984）；分支快照把整份前缀解码成完整条目列表（#1978、#1987）；读取投影在会话写锁内解码整份日志（#1973、#1988）；无追加时重复读取仍整份解码（#1973、#1989）；条目追加仍全量解码既有前缀（#1973、#1991）；锁外快照把崩溃残段计入固定范围，截断追加后读取失败或包含新记录（#1993、#1994）；自动压缩设置保存成功但缺少目录 fsync，崩溃后可能回退旧配置（#1996、#1997）；索引修复把数据库移入备份后未同步目录，崩溃后备份与根目录可能只落盘一半（#1999、#2000）；会话导出检查目标与替换之间文件被改为链接或换成其他 inode 时静默覆盖新目标（#2002、#2003）；内核设置读取先在路径上查大小再按路径读取，两次解析之间配置被替换可绕过 256 KiB 上限（#2005、#2006）；索引修复失败回滚移动库文件后未同步目录项，掉电后回滚可能部分落盘（#2008、#2009）；索引修复清单的大小与摘要分步读取，可能来自不同版本并移动被替换的 inode（#2011、#2012）；工作区说明保存替换文件后未同步目录项，掉电后新说明或新目录可能丢失（#2014、#2015）；技能写入替换 `SKILL.md` 后未同步目录项，掉电后新技能或新正文可能丢失（#2017、#2018）；快照元数据入口未沿用分支叶失效校验，其他读取已报错时仍返回旧快照路径与条目数（#2020、#2021）。构建审计对不进入产物的开发依赖按 moderate 阻断，上游尚无修复版的构建工具公告使所有源码 PR 无法合入（#2022、#2023）。冻结快照发布后未同步快照目录项，掉电后缓存可能指向不存在的文件（#2025、#2026）；摘要检查点提交后未同步会话目录项，成功回执后掉电可能回到旧 inode（#2027、#2028）。同时把根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本同步为 npm `0.2.0-rc.56` / Python `0.2.0rc56`（#1589）。rc.55 已准备的 5 项修复与更早候选内容继续适用。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

升级注意：不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.55 源码无需迁移。rc.55 未实际发布，rc.56 聚合其 5 项交付与更早候选内容。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。

### 变更

- [Issue #1589](https://github.com/can4hou6joeng4/boss-harness/issues/1589)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.56` / Python `0.2.0rc56`；将 rc.55 之后 151 项修复、1 项界面改进与 1 项打包元数据改进归入本候选，同步 README 近期进展与版本表、使用指南的候选状态、技术参考中的候选引用与 Issue 表单示例版本。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1896](https://github.com/can4hou6joeng4/boss-harness/issues/1896)：配置文件与自动压缩设置无关的深层嵌套或孤立代理项让保存返回内部错误。`_read_object()` 使用 C 解析器可读出约 1000 层合法嵌套，`save_auto_compaction()` 却用带 `indent=2` 的纯 Python 编码器抛 `RecursionError`；转义写入的孤立代理项又让 `payload.encode("utf-8")` 抛 `UnicodeEncodeError`，两者都映射为 `-32603`。现在 `_read_object()` 迭代检测嵌套深度（上限 64），超限按不可读配置处理；`json.dumps`、UTF-8 编码与大小上限统一捕获，失败返回既有中文 `ValueError`，读取回退默认值。探针覆盖 1000 层嵌套、孤立代理项与正常配置：修复前分别得到 `-32603` 与 codec 错误，修复后可读并保留正常保存。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1897](https://github.com/can4hou6joeng4/boss-harness/issues/1897)：分支摘要的辅助字段没有长度上限，压缩后历史仍永久超出上下文预算。`branch_summary_issue()` 只校验摘要正文，`abandonedTurnIds` 只检查元素是字符串，`sourceTextDigest` 完全不校验；`_branch_summary_scan()` 又把它们直接拼进每回合注入的消息。一条 2 MB 的来源摘要让压缩后的历史仍有约 200 万字符，`targetTurnId=None` 的摘要不随压缩排除，之后每回合的 `prepare` / `check` 都报「上下文估算超过输入预算」。现在限制被放弃回合数量（200）、单项长度（128）与总长度（4096），来源摘要允许缺省但最多 128 字符；损坏摘要按既有路径跳过并给出 issue 原因。探针：修复前压缩后 `chars: 2000279`、`check` 失败，修复后摘要注入为 0、`chars: 126`、`check: ok`；10 项边界断言通过，正常 64 字符摘要逐字节不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1898](https://github.com/can4hou6joeng4/boss-harness/issues/1898)：缺失结果的工具投影未限制错误码长度，单条即突破模型结果预算。恢复出的 `toolCall` 条目可能只有 `resultSummary` 与 `errorCode` 而没有 `result`；`_unavailable_result()` 原样写入错误码，`_fits()` 失败后只缩短预览，最终仍返回超预算 JSON。三条 10 万字符错误码的条目让上下文注入约 30 万字符，`context` 校验报「上下文估算超过输入预算」。现在错误码与展示路径一致截到 128 字符，最终兜底再用 `_fits()` 校验，仍放不下时丢弃错误码、保留状态与 `resultUnavailable`。探针：修复前每条 100,057 字节、三条超预算，修复后每条 215 字节、`check: ok`；10 项边界断言在修复前 7 项失败、修复后全部通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1928](https://github.com/can4hou6joeng4/boss-harness/issues/1928)：OpenAI Responses 流没有「一个 `output_index` 只属于一个输出项」的所有权校验。一个已完成的 `function_call` 占用 index 0 后，同一 index 的 `message` 起始/完成事件被接受并覆盖 `blocks[0]`；终态 `response.completed` 仍把该 index 映射给工具调用，但终态处理不重建块，最终 `AssistantMessage` 只剩 `TextBlock`，`stop_reason` 为 `stop`，工具从未执行而回合正常完成；终态输出项类型与流事件不一致时也未拒绝。现在 added/done 阶段要求同一 index 只声明一种输出项类型、关闭后不可再起始或关闭，终态 `output` 逐项核对类型与流事件一致。探针：修复前跨类型复用后 `tool calls: []`、回合 `completed`、执行器 0 次；修复后 21/21，畸形流在解析阶段以 `error` 返回，合法三输出项流与纯增量兼容流逐事件不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1929](https://github.com/can4hou6joeng4/boss-harness/issues/1929)：OpenAI 文本 / 思考增量不绑定活动输出项。工具调用完成后指向同一 index 的 `response.output_text.delta` 被接受并累积；提供商终态消息正确地只保留 `ToolCallBlock`，但 `TurnRunner._stream_round` 在终态无 `TextBlock` 时用流式累积文本作为助手正文，落库为带 `toolBatchId` 的 `agentMessage`，下一回合历史投影把它当模型真实输出。现在文本增量只接受活动中的 `message` 项、思考增量只接受活动中的 `reasoning` 项，块关闭后拒绝；未声明 added 的纯增量流保持兼容。探针：修复前落库 `agentMessage('stray streamed text', completed, toolBatchId=…)` 且工具执行 1 次；修复后 21/21，杂散文本不落库、历史与终态响应一致。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1930](https://github.com/can4hou6joeng4/boss-harness/issues/1930)：OpenAI `function_call` 的 `call_id` 与名称只校验非空与批内唯一，没有 256 字符上限，而 `record_tool_batch` 对调用 id 有同一上限。257 字符 id 通过提供商后在批次记录处抛 `ValueError("工具批次调用清单无效")`，从 `runner.run` 逃逸为未捕获异常，错误层级与 Anthropic 线路不一致；带文本的响应还会先落库助手条目。现在提供商入口要求 `call_id` 与名称非空且长度 ≤256。探针：修复前提供商 `done ids: [257]` 后回合抛错；修复后 21/21，超限流在解析阶段拒绝、不产出工具调用、不落库。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1931](https://github.com/can4hou6joeng4/boss-harness/issues/1931)：`JsonRpcServer._write()` 把 JSON 文本直接写入 `sys.stdout`，内核从不把协议输出固定为 UTF-8；stdout 编码跟随 locale / `PYTHONIOENCODING`，桌面启动内核时未设置而 `--check` 自检却显式设置。非 UTF-8 stdout 下，含中文的成功响应编码失败、降级帧再次失败并被静默丢弃，客户端收到零字节后 `outcome unknown`，但变更已落库；`serve_forever` 自身的协议错误帧同样失败，`UnicodeEncodeError` 从读取循环逃逸，内核带 traceback 退出。现在 `_write()` 生成 UTF-8 字节并在存在 `buffer` 时直接写字节，绕过文本层编码与换行转换；stdin 固定按 UTF-8 + surrogateescape 解码；协议错误帧统一走 `_protocol_error()`，无法编码也不终止读取循环。探针：ASCII stdout 下中文结果从 0 字节变为可严格 UTF-8 解析；真实内核 `PYTHONIOENCODING=ascii` 时修复前 `thread/start` 无回包、坏帧退出码 1，修复后 7/7 通过。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1965](https://github.com/can4hou6joeng4/boss-harness/issues/1965)：`TurnQueue.recover()` 只把读取包在 `except (OSError, ValueError)` 内，循环中的 `transition()` 与 `_associate_request()` 写回不受保护。合法读入的近 32 MiB 队列记录在 `status` 从 `queued` 改为 `delivered` 后多 2 字节，`_encode_session_line()` 抛 `ValueError`，异常从 `ApplicationService.__init__` 逃逸，内核每次启动都以退出码 2 结束，`--repair-state` 也不修复会话日志。同时 `queue/get` 原样返回完整 `input`，9 MiB 的合法持久记录让响应超过 8 MiB 帧上限、每次调用都返回 `-32010`，而 `queue/list` 仍显示截断预览。现在恢复循环的写回与读取同样按线程 best-effort：写回失败只跳过该会话剩余项目，已写回状态保留、其它会话照常启动；`queue/get` 对超过 100,000 字符（与 `queue/add` / `queue/update` 同一上限）的正文截断并置 `inputTruncated: true`，两处硬编码上限收敛为 `MAX_QUEUE_INPUT_CHARS`。探针：修复前构造恰好 32 MiB 的合法队列记录后 `recover raised ValueError : 会话日志单行超过大小限制` 且重复调用同样失败，修复后 `recover ok`、第二次同样正常；9 MiB 正文从 `-32010` 变为 100,000 字符 + `inputTruncated`。正常队列记录与完整正文逐项不变，15 个回归探针全部通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1969](https://github.com/can4hou6joeng4/boss-harness/issues/1969)：`SessionStore.events_after()` 在存储锁内 `fetchall(limit+1)` 后逐行 `json.loads`，一页最多 1000 条、单条可接近 8 MiB，最坏在锁内解码数 GiB；页字节预算 `MAX_PAGE_BYTES` 在解析完成后才检查，拦不住解码本身。事件日志被较大工具输出填充后，`event/list` 与启动时的三处回放循环会长时间阻塞所有会话读写并可能耗尽内存。现在 `_event_rows()` 按 `params_json` 原始字节预算（4 MiB）逐行读取，达到预算即停止并置 `hasMore`，由调用方既有的 `while True` + `hasMore` 循环续读；首行即使超过预算也照常返回，保证 `nextCursor` 总能推进。探针：200 条 256 KiB 事件翻页取回全部，单页解析最多 3,842 KiB、共 14 页；单页峰值内存从 100.2 MiB 降到 7.5 MiB，耗时 63 ms 降到 6 ms。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1971](https://github.com/can4hou6joeng4/boss-harness/issues/1971)：`tool/result/read` 每翻一页对完整结果做三次全量遍历：`read_result_chunk` 里 `result_text` 与 `result_reference` 各一次，进入 `read_result_text_chunk` 后 `result_reference` 再算一遍全文 `sha256`；结果 N 字节、每页 32 KiB 时总成本平方增长。现在 `read_result_chunk` 把已校验的引用直接传给分块函数，每页只做一次全文摘要；`read_result_text_chunk` 的 `reference` 参数可选，`model_tools.py` 等其它调用方行为不变，传入引用与请求摘要不一致时仍报 `STALE_RESULT`。探针：200 KB 结果 7 页，全文哈希从 14 次降到 7 次，分页拼接逐字符一致，错误摘要与引用不一致均报 `-32011`。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1975](https://github.com/can4hou6joeng4/boss-harness/issues/1975)：`SnapshotBuilder.__init__` 把 `PRAGMA max_page_count` 恰好设为 `MAX_SNAPSHOT_BYTES // page_size`，而预算检查在每条记录插入后才执行。达到页上限的那次 INSERT 由 SQLite 先抛 `sqlite3.OperationalError("database or disk is full")`，`build()` 清理后原样重抛，RPC 层映射为 `-32603`，事后页数检查与可读错误不可达；`item_bytes` 又只统计 `items` 表，`queue_items` 的 payload 完全绕过条目预算。大会话的 `thread/resume snapshot=true` / `thread/read snapshot=true` 因此返回内部错误。现在页数上限留一页余量并捕获 `sqlite3.OperationalError`，转为可读 `ValueError`；队列 payload 也计入条目存储预算，更新时按旧值扣减。探针：缩小预算后修复前 `OperationalError`，修复后 `ValueError("冻结快照写入失败…")`；32 KiB 条目预算下 10 条 8 KiB 队列记录修复前快照成功、修复后报「超过快照条目存储上限」；正常快照逐项不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1976](https://github.com/can4hou6joeng4/boss-harness/issues/1976)：`SnapshotBuilder._entry` 只按 `revises` / `parentId` 查找修订目标，目标为空时直接插入新行，仅更新 `aliases` 指向。两条相同 `id` 的持久 `item` 记录（外部改写或异常写入）因此写入两行：`items/list` 返回两条同 id、不同正文的条目，而 `snapshots.item()` 的 `WHERE item_id=?` 取第一行，`item/content/read` 拿到旧修订；`edits` 的 LEFT JOIN 还会把同一编辑挂到两条重复行上。现在与 `session.py` 的 `_project_items` 对齐：`entry_id` 已存在且不是修订记录时跳过后续记录，分页与内容读取落到同一修订。探针：修复前分页 `["a","a"]`、`item("a")` 返回 first，修复后只保留一条；正常修订链、工具调用完成记录与独立条目逐项不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1979](https://github.com/can4hou6joeng4/boss-harness/issues/1979)：`AttachmentStore._storage_usage()` 每次 `attachment/add` 都遍历全部附件文件并逐个`restrict_private_file()`（lstat + open + ACL 清理 + fchmod）。配额默认 4096 个对象时单次扫描约 0.30 s，填满配额累计约 20 分钟；`add` 经由 `SessionStore.append_attachment` 在会话写锁与索引事务内执行，期间所有请求与会话写停摆。现在启动时全量校验一次并统计，运行期按发布与失败清理增量维护 `used_bytes` / `used_objects`；配额检查仍校验附件目录本身，新对象由发布路径的 `open_private_file` 收紧权限，读取路径仍按需收紧。探针：500 个对象时单次配额扫描从 37.31 ms / 500 次 restrict 降到 5.52 ms / 0 次；发布后计数递增、重复添加同一内容不重复计数、发布回调失败时对象已记账；新对象权限仍为 `0600`。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1973](https://github.com/can4hou6joeng4/boss-harness/issues/1973)：`thread/read` 的非分页路径与 `thread/items/list` 先调用 `SessionStore.read_entries()` 读取整份 rollout，随后 `EventHub.items(thread_id)` 在未传 `entries` 时再次调用 `read_items()` 与 `read_entries()`，同一份会话文件在会话写锁内被完整解码两遍，大会话的读取耗时翻倍并延长其他请求的等待。现在两个入口都显式传入已读条目，分支视图仍先过滤活动条目再投影（[PR #1984](https://github.com/can4hou6joeng4/boss-harness/pull/1984)）。探针 5 条消息的会话 `read_entries` 调用从 2 次降到 1 次，复用与内部再读两种路径的投影结果逐项一致。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1978](https://github.com/can4hou6joeng4/boss-harness/issues/1978)：`view=branch` 的冻结快照在构建前用 `read_source_entries()` 把整份前缀解码成完整 `list[dict]`，代理实测常驻内存约为源大小的 6.2 倍，1 GiB 源仅条目就需要约 6 GiB，叠加投影副本易被 OOM 杀掉；此前的源大小上限只是把窗口压到 256 MiB（[PR #1987](https://github.com/can4hou6joeng4/boss-harness/pull/1987)）。现在新增 `read_projection_entries()`：第一遍仍逐行解码，但只保留分支投影读取的字段（条目 id、类型、父引用与各类判定键，回合记录保留完整载荷以生成公共回合页），条目正文与工具结果不再物化；第二遍由 `SnapshotBuilder.build` 流式读取原始文件写入快照。探针 19 条混合会话（含回合、工具批次、上下文编辑与检查点、task_phase、叶切换）的 `keepIds`、`leaf`、`leafEntryId`、`lastTurn`、`turns`、`turnsTooLarge` 与完整读取逐字段一致，重复条目编号仍按同一可读错误拒绝，无叶会话 `keepIds` 为 None；端到端 `thread/read snapshot=true view=branch` 与 `thread/items/list view=branch` 只返回活动分支条目，日志视图仍含全部条目；36.69 MB / 5 万条记录的源，完整读取峰值 70.4 MB 对轻量投影 28.3 MB（约 2.5 倍降幅）。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1973](https://github.com/can4hou6joeng4/boss-harness/issues/1973)：`SessionStore.read_entries()` 在持有存储写锁的整段时间里逐行解码整份会话日志，大会话下一次列表读取、线程读取或恢复会阻塞所有会话的读写；`open_entries_snapshot()` 已提供锁内固定前缀、锁外扫描的能力，但读取投影路径未使用（[PR #1988](https://github.com/can4hou6joeng4/boss-harness/pull/1988)）。现在新增 `read_entries_snapshot()`：锁内固定文件前缀（inode、大小与 mtime），锁外逐行解码，返回条目与打开时刻的前缀一致；`application.py` 的 10 个展示与读取投影入口（线程读取、条目列表、用量、导出、上下文读取、压缩计划、续接预检与事件转发读取）改用该方法，会话内部写路径仍使用锁内 `read_entries()`。探针 3,000 条记录的会话两种读取结果逐项一致；把每行解码放慢到 0.2 ms 后，另一线程获取存储锁的等待时间从 812 ms 降到 0 ms；条目列表（含翻页拼接）、线程读取（日志与分支视图）、用量、导出与压缩计划的应用层探针与改动前契约一致。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1973](https://github.com/can4hou6joeng4/boss-harness/issues/1973)：`read_entries()` 与 `read_entries_snapshot()` 每次调用都重新解码整份会话日志，列表翻页、线程读取、用量、导出与恢复对同一未变化的会话反复读取时重复付出 CPU（[PR #1989](https://github.com/can4hou6joeng4/boss-harness/pull/1989)）。现在按 `(文件大小, mtime_ns)` 绑定一个有界条目缓存（最近使用的 4 个会话）：锁内读取命中即返回浅拷贝；快照读取先在锁内查缓存，未命中则固定前缀、锁外解码，并只在锁内确认文件仍是同一前缀后才缓存，解码期间发生追加时丢弃，避免以新文件的身份返回旧前缀；删除会话时清理对应缓存，外部追加改变文件大小后缓存自然失效。探针 3,000 条会话首次读取解码 3,001 条记录（含会话头）、再次读取 0 次；`append` 经索引刷新缓存后紧随读取不再解码；`read_entries_snapshot` 复用锁内读取的缓存、快照解码后再次读取命中缓存；依次读取 5 个会话后最早会话被淘汰并重新解码；删除会话清理缓存；绕过 `append` 的外部追加按大小变化重新解码。锁外解码、应用层读取路径、分支快照端到端与条目列表单次投影探针回归通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1973](https://github.com/can4hou6joeng4/boss-harness/issues/1973)：`append` 每次写入都让索引刷新读取整份会话日志，条目缓存只在文件未变化时命中，追加后仍全量解码，长期会话的写入成本随回合数平方增长（[PR #1991](https://github.com/can4hou6joeng4/boss-harness/pull/1991)）。现在条目缓存记录 `(大小, mtime_ns, inode)` 与已读行数，追加时若缓存来自同一 inode、前缀严格更短且旧前缀末尾在当前文件上仍是换行边界，则从旧偏移只解码新增行并拼接缓存；外部截断重写或新 inode 替换文件按全量重新解码；只有前缀末尾是换行（无半写残段）时才缓存，残段读取丢弃残段并保留既有条目，写入端截掉残段后从旧边界继续增量。探针 3,000 条会话外部追加 1 行后只解码 1 行（此前 3,002 行），增量结果与全新 `SessionStore` 全量重建逐项一致；`append` 的索引刷新只解码 1 行；残段不产生新条目、截掉后只解码新行、新增损坏行按文件行号报错；新 inode 替换与截断到会话头均全量解码且结果正确。5,000 条会话连续 20 次 `append` 的中位耗时从 43.96 ms 降到 8.11 ms（约 5.4 倍）。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1993](https://github.com/can4hou6joeng4/boss-harness/issues/1993)：为缩短写锁等待，条目快照与冻结快照改为在锁内固定文件长度、在锁外解码；但固定范围仍包含崩溃残留的无换行残段，下一次追加会先截掉残段再写入完整记录，截断后文件短于固定范围，条目快照抛「会话日志快照读取不完整」，而快照构建器在 EOF 静默结束，把 pin 之后追加的记录当成固定前缀（[PR #1994](https://github.com/can4hou6joeng4/boss-harness/pull/1994)）。现在打开两个快照时把固定范围收敛到最后一个换行边界内：正常尾部长度不变；含残段时在单行上限窗口内向前找边界，之后追加对残段的截断只改写边界之外的字节；窗口内仍无边界时按追加端同一可读错误拒绝。探针 50 条条目 + 约 48 KB 残段，pin 后再截断追加：修复前条目快照报读取不完整、投影源返回 51 条，修复后两者都只返回 50 条且固定范围等于完整前缀；含残段时 `read_entries_snapshot` 不写缓存，缓存门槛与 `read_entries` 的换行边界一致；正常尾部仍只覆盖 pin 时前缀。条目缓存、增量追加、锁外解码、分支快照端到端、分支投影扫描与应用层快照读取探针回归通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1996](https://github.com/can4hou6joeng4/boss-harness/issues/1996)：自动压缩设置保存只对临时文件 `fsync`，`os.replace` 后没有对状态目录 `fsync`；`os.replace` 只保证新名称对运行中的进程可见，目录项要等目录 `fsync` 之后才落盘（[PR #1997](https://github.com/can4hou6joeng4/boss-harness/pull/1997)）。保存返回成功后掉电或崩溃，`config.json` 可能回退旧内容甚至缺失，`config/autoCompaction/set` 显示的已保存设置静默失效。现在替换成功后对状态目录执行 `fsync`（`O_RDONLY | O_DIRECTORY` 打开后 `fsync` 再关闭），与 `session._fsync_directory` 及会话追加、附件发布、索引修复备份的持久边界一致；目录 `fsync` 失败按现有可读错误传播。探针记录 `os.fsync` 目标：修复前首次与覆盖保存都只有文件 `fsync`（`[False]`），修复后为 `[False, True]`，内容可正常读回；缺字段与不可读配置仍在写盘前拒绝，不创建或覆盖 `config.json`，损坏配置读回 `None`。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #2025](https://github.com/can4hou6joeng4/boss-harness/issues/2025)：`SnapshotStore.create()` 用 `os.replace()` 发布 SQLite 快照后没有同步 `resume-snapshots` 目录项；快照写入使用 `PRAGMA synchronous=OFF`，成功回执后掉电可能只保留旧目录项（[PR #2026](https://github.com/can4hou6joeng4/boss-harness/pull/2026)）。现在发布后同步父目录，`fsync` 失败走既有异常清理，不会返回成功。探针验证正常发布只同步一次、失败不留成功快照。`compileall` 通过，协议仍为 `0.2.0`。
- [Issue #2027](https://github.com/can4hou6joeng4/boss-harness/issues/2027)：`SessionStore.append_checkpoint()` 替换会话日志后没有同步会话目录项，已回报成功的摘要检查点在掉电后可能丢失（[PR #2028](https://github.com/can4hou6joeng4/boss-harness/pull/2028)）。现在在写事务内、确认替换目标身份后同步会话目录；同步失败沿用 `CheckpointCommittedError` 语义避免重复提交。探针验证成功与失败路径，`compileall` 通过，协议仍为 `0.2.0`。
- [Issue #2022](https://github.com/can4hou6joeng4/boss-harness/issues/2022)：源码构建把整个依赖树按 moderate 审计，`picomatch` 公告 GHSA-fc5q-39xc-vjpf 在已发布版本中均无修复版，Vite 6.3+ 又都经 `tinyglobby` / `fdir` 传递引入；降到 6.2.7 会命中更多 Vite 自身公告，导致必需检查长期失败（[PR #2023](https://github.com/can4hou6joeng4/boss-harness/pull/2023)）。现在将 Vite 锁到 6.4.6，并按产物范围分层审计：生产依赖树按 moderate 阻断，不进入桌面产物的开发依赖按 critical 阻断。本地验证生产树零告警、开发树无 critical、类型检查与源码构建全部通过；协议与产物接口不变。
- [Issue #2020](https://github.com/can4hou6joeng4/boss-harness/issues/2020)：`SnapshotStore.metadata()` 只做了快照过期修剪与会话归属检查，没有走 `page()` / `item()` / `edit_state()` / `queue()` 共用的 `_metadata_locked()`；分支叶切换使快照失效后，其他读取都返回 `SNAPSHOT_LEAF_CHANGED`，元数据仍返回路径和条目数，调用方会把失效快照当成当前快照（[PR #2021](https://github.com/can4hou6joeng4/boss-harness/pull/2021)）。现在元数据入口复用同一校验，失效快照得到一致的错误码；普通快照、错误会话与不存在快照的行为不变。探针比较五路读取错误码及普通分支 / 日志快照元数据，全部通过；`compileall` 通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #2017](https://github.com/can4hou6joeng4/boss-harness/issues/2017)：`SkillCatalog._write_atomic()` 把正文写到临时文件、`fsync` 后 `os.replace()` 覆盖 `SKILL.md`，没有同步技能目录；首次创建技能时新建的目录也没有同步技能根目录与工作区父目录，创建 / 修改回执成功后掉电可能让新技能或新正文丢失（[PR #2018](https://github.com/can4hou6joeng4/boss-harness/pull/2018)）。现在每次替换后同步技能目录；首次新建上级目录时再按内层到外层同步。临时文件清理、权限与摘要校验不变。探针验证首次创建的三层目录同步、覆盖修改只同步技能目录，内容及回执不变；`compileall` 通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #2014](https://github.com/can4hou6joeng4/boss-harness/issues/2014)：`WorkspaceInstructions.write_text()` 把正文写入临时文件并 `fsync` 后 `os.replace()` 覆盖 `.boss-harness/CONTEXT.md`，没有同步说明目录；首次保存用 `os.mkdir()` 创建目录时也没有同步工作区。回执报告 `status: loaded` 后立即掉电可能让新说明丢失、旧说明复活或整个目录回退（[PR #2015](https://github.com/can4hou6joeng4/boss-harness/pull/2015)）。现在替换后同步说明目录，首次新建目录时再同步工作区，顺序为先子目录后父目录；错误路径与临时文件清理不变。探针验证首次保存与覆盖保存的目录同步目标、文件内容和回执，`compileall` 与模块导入通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #2011](https://github.com/can4hou6joeng4/boss-harness/issues/2011)：`repair_index()` 备份库文件时先 `source.stat().st_size` 写清单，再按路径重新打开计算摘要，最后 `os.replace()` 移动文件；清单的大小与摘要可能来自不同版本，路径在校验后替换时还会把新 inode 移入备份，用户按清单核对备份会得到错误结论（[PR #2012](https://github.com/can4hou6joeng4/boss-harness/pull/2012)）。现在新增 `_manifest_entry()`：先由 `restrict_private_file` 固定普通文件与权限，同一描述符核对 dev/ino 后读取大小与摘要，并在移动前再次核对路径仍是校验过的 inode；校验后替换抛可读错误并进入既有回滚路径。探针覆盖正常备份清单一致性、校验后 inode 替换拒绝，以及成功 / 回滚目录 fsync 与失败回滚回归，全部通过；`compileall` 通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #2008](https://github.com/can4hou6joeng4/boss-harness/issues/2008)：`repair_index()` 成功路径在写清单后同步备份目录与状态根目录，但失败回滚把原库文件移回根目录、把新候选移入 `failed-candidate/` 后没有目录 `fsync`；掉电后回滚移动可能部分落盘，根目录缺少库文件而备份仍有副本，或失败候选目录的移动丢失（[PR #2009](https://github.com/can4hou6joeng4/boss-harness/pull/2009)）。现在回滚完成移动后依次同步 `failed-candidate`（确有候选移入时）、备份目录与状态根目录，顺序与成功路径一致，保证崩溃时最多留下重复副本；同步失败仍走原异常路径。探针在索引重建抛错时记录 `os.fsync` 目标，验证三个目录按序同步、原库文件回到根目录、候选移入失败目录；成功路径、既有探针与 `compileall` 回归通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #2005](https://github.com/can4hou6joeng4/boss-harness/issues/2005)：`settings._read_object()` 先用 `path.stat().st_size` 判断 256 KiB 上限，再用 `path.read_text()` 按路径读取整份配置；两次解析之间配置可被截断或替换，大小判断与实际内容不来自同一文件状态，超预算内容可进入内存并被合并进下一次保存（[PR #2006](https://github.com/can4hou6joeng4/boss-harness/pull/2006)）。现在用 `open_private_file(..., O_RDONLY)` 打开一次，在同一描述符上确认普通文件并分块读取至多 `上限 + 1` 字节，多读的一字节直接按不可读处理；符号链接、非普通文件与缺失文件沿用既有不可读或默认行为。探针覆盖正常配置、恰好上限、超限、同 inode 缩小、符号链接、目录、保存读回与拒绝覆盖共 9 项断言，全部通过；设置目录 fsync 与 `compileall` 回归通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #2002](https://github.com/can4hou6joeng4/boss-harness/issues/2002)：会话导出在写入前用 `lstat` 排除符号链接，临时文件写入、刷新并关闭后才 `rename` 覆盖目标；这段时间内目标若被替换为符号链接或其他文件，旧实现仍替换该路径并向界面报告保存成功，用户随后按原路径打开的是另一份文件（[PR #2003](https://github.com/can4hou6joeng4/boss-harness/pull/2003)）。现在把首次 `lstat` 的 dev/ino 与可用的创建 / 状态变更时间作为目标身份，关闭临时文件后再次核对：身份变化、目标删除或变成符号链接时抛 `targetChanged`，只清理临时文件而不动目标，并由错误映射给出「所选文件在保存期间发生变化，请确认后重试」；首次保存的 `null` 身份仍允许覆盖创建。探针覆盖写入期间换成链接、换成另一普通文件、删除目标、首次保存、预置链接与正常覆盖共 18 项断言，全部通过；`npm run typecheck`、`npm run build` 通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1999](https://github.com/can4hou6joeng4/boss-harness/issues/1999)：`--repair-state` 把 `state.sqlite3*` 移入备份后只 `fsync` 了 `manifest.json` 文件，没有对备份目录与状态根目录执行目录 `fsync`；目录项要等目录 `fsync` 之后才落盘（[PR #2000](https://github.com/can4hou6joeng4/boss-harness/pull/2000)）。修复返回成功、打印 `backupPath` 后掉电或崩溃，根目录可能残留部分库文件、备份缺少另一些文件，或清单指向未持久存在的备份，手工恢复与下次启动都受影响。现在清单写入并 `fsync` 后依次同步备份目录与状态根目录：先备份后根目录保证崩溃时最多留下重复副本，不会出现根目录已删而备份缺失；目录 `fsync` 失败走既有回滚路径，把已移动文件移回根目录并原样抛出。探针记录 `os.open` / `os.fsync` 目标：修复前只有清单文件被同步（3 项失败），修复后依次为清单文件、备份目录、状态根目录；备份含三个库文件与清单，摘要字段不变；让索引重建抛错时，已移动的库文件仍被移回根目录。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1960](https://github.com/can4hou6joeng4/boss-harness/issues/1960)：`initialize` 回执只校验 `serverName`/`protocolVersion`，`modelBridge` 原样经 `host.status()`、IPC 与 `harnessStatus()` 写入 `App` 的默认线路；渲染期 `sessionProvider?.toLowerCase()` 对对象、数组或数字抛 `TypeError`，整个界面落入应用级错误边界，重连后再次白屏。同时 `findHighlight.keywordRanges()` 对每个空白关键词各调用一次 `searchTextWithMap(text)`，搜索框不设长度上限，超长查询在每次击键的渲染里重复整串字素切分与 NFKC。现在 `harnessStatus()` 校验 `modelBridge`（普通对象、`provider`/`model` 为 ≤200 字符串、`driven` 为布尔），畸形时按缺失处理；`running` 非布尔时整份回执按不可识别返回「未运行」；`App` 渲染期对 `sessionProvider` 做类型收窄；关键词标注只归一化一次文本，超过 200 codepoint 的查询不再标注（与消息搜索上限一致）。探针：修复前 6 种畸形 `modelBridge` 全部被接受、5 种畸形状态原样返回，4,800 字符 × 90 关键词耗时 1,361 ms；修复后 40,062 项断言全部通过，同一输入 16 ms，合法回执与正常查询逐字不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1961](https://github.com/can4hou6joeng4/boss-harness/issues/1961)：三处用外部字符串作普通对象键。`parseComposerDraftStore()` 以 `{}` 累加 localStorage 的会话键，`JSON.parse` 保留的 `"__proto__"` 键经 `Object.entries` 枚举后触发原型 setter：该会话草稿被静默丢弃、结果对象原型被替换；`ConnectionSettings` 的 `AUTH_LABELS[authState]` 与 `BranchSummaryNotice` 的 `FAILURES[job.code]` 在值被改写为 `"constructor"`/`"toString"` 时命中原型成员，`??` 与 `||` 不回退，账号行显示 `function Object() { [native code] }` 并吞掉真实失败原因。现在草稿解析与保存的累加器改为 `Object.create(null)`；`connectionReport` 把 `authState` 按内核枚举 `complete/partial/broken/missing/unknown` 校验，非法值让整份回执按不可读处理；失败码查询改用 `Object.prototype.hasOwnProperty.call`。探针：修复前 `__proto__` 草稿丢失且 `Object.getPrototypeOf(result.sessions).text === "x"`，修复后作为自有键保留、原型恒为 `Object.prototype`；正常标签与草稿恢复逐项不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1955](https://github.com/can4hou6joeng4/boss-harness/issues/1955)：`HarnessReplica.branchSnapshot()` 在旧内核（声明 `sessionBranchViews`、未声明 `sessionBranchSnapshots`）路径上的最终校验只核对 `view === "branch"` 与 `thread.id`。`thread.provider`/`thread.model` 被改写为数字、对象或超长字符串时原样写入会话状态，渲染期 `provider.toLowerCase()` 抛 `TypeError`，整个应用落入应用级错误边界；`items` 不是数组时 `for...of` 抛出的 `TypeError` 被伪装成「读取会话内容失败」。现在与 `thread/resume` 普通路径同一契约：`assertSnapshotRouteFields(snapshot.thread)` 并要求 `items` 为数组，`RESPONSE_TOO_LARGE` 降级路径同样经过校验。探针：修复前 `provider: 42` 的分支快照被接受并触发 `onSnapshot`，修复后 23/23 按该会话恢复失败处理、下一次正常恢复成功；合法快照与降级路径逐项不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1956](https://github.com/can4hou6joeng4/boss-harness/issues/1956)：`RichMarkdown` 的行内 token 正则（链接、行内代码、粗体三个分支）与 `markdownBlocks` 的 `BACKTICK_OPENING_FENCE` 的 `(.*?)` 在合法超长单行上平方级回溯：40,000 个 `[` 耗时 2.4 秒，40,000 个反引号加 `!` 耗时 12.5 秒，100k 时分钟级，全部在渲染主线程执行。现在围栏改为按反引号串前进、每个串只检查一次尾部；行内解析为 `]`、反引号与 `*` 缓存下一个出现位置，起点只前进不后退。探针：60,037 项差分与旧正则逐 token 一致（各 30,000 条随机行、固定样例与围栏切分端到端），200k 最坏输入分别 1.9/2.0/1.0 毫秒。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1946](https://github.com/can4hou6joeng4/boss-harness/issues/1946)：压缩任务恢复把检查点事件里的 `result` 与任意标量原样放回内存任务并回写事件日志。单条事件接近 8 MiB 上限时，终态通知的 `emit` 抛 `ValueError("事件日志单行超过大小限制")`，异常从 `ApplicationService.__init__` 逃出，内核启动失败（退出码 2）。现在恢复只保留有界标量：`code`/`message`/`reason`/`turnId`/`fromTurnId`/`targetTurnId`/`firstKeptItemId`/`summaryProvider`/`summaryModel`/`summaryEffort` 各有长度上限，整数字段限制 0 到 2^53-1，`abandonedTurnIds` 最多 200 项、单项 128 字符、合计 4096，`result` 等无可靠来源的大对象直接丢弃；终态 `emit` 包 `try/except`，写不进事件日志时保留内存终态并改用 `COMPACTION_RESTORE_NOTICE_FAILED`，不再让恢复通知拖垮启动。探针：修复前 `restore raised ValueError : 事件日志单行超过大小限制`，修复后恢复完成、新终态事件 540 字节且 `result` 已裁剪；正常任务的字段逐项保留。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1947](https://github.com/can4hou6joeng4/boss-harness/issues/1947)：`SkillCatalog.__init__` 只解析根路径，不检查根目录本身是否为符号链接；工作区的 `.boss-cli/skills` 指向工作区外时，`list()`/`read()`/`load()` 照常越过边界读取外部 `SKILL.md`。现在初始化记录根目录是否为符号链接，`_candidate_paths()` 在枚举前拒绝并抛可读 `ValueError("技能目录不能是符号链接；请改为工作区内的普通目录")`；普通目录的既有行为（子目录不跟随符号链接、`SKILL.md` 的 `O_NOFOLLOW` 与 dev/ino 比对、新建时的 lstat 拒绝）不变。探针：修复前 list/read/load 返回 `OUTSIDE-WORKSPACE-CONTENT`，修复后统一按不可读目录上报；普通技能目录的 list/read/load 逐项不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1948](https://github.com/can4hou6joeng4/boss-harness/issues/1948)：`branch_summary_issue()` 只校验摘要正文与弃用回合，不校验 `summaryJobId`/`fromTurnId` 的形状；把 9 MiB 字符串写进辅助标识后，`context/read` 的 `branchSummaries` 投影原样回显，响应超过 8 MiB 帧预算。现在 `branch_summary_issue()` 要求这两个字段缺失或为 ≤128 字符的字符串，`ContextService.read()` 的投影把 `entryId`/`targetTurnId`/`fromTurnId`/`summaryJobId` 收敛为 ≤128 字符或 `None`。探针：修复前 `result bytes: 9437634`、`summaryJobId` 9 MiB，修复后 405 字节且超长标识整体按损坏摘要拒绝；合法摘要的投影元数据逐项不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1949](https://github.com/can4hou6joeng4/boss-harness/issues/1949)：`_restore_compaction_jobs()` 只比较检查点事件与任务的 `summaryJobId`，不看该检查点在投影里是否有效；字段被改写坏的检查点会让恢复把任务标成 `COMPACTION_RECOVERED_COMMIT`（摘要已提交），与 `context/read` 的 `checkpointIssue` 矛盾。现在改用 `_checkpoint_committed()`，调用 `ContextService.read(thread_id, entries=entries)` 检查投影后真正生效的 `checkpoint` 或 `branchSummaries`；投影判为无效的检查点不再被当作已提交，任务按 `COMPACTION_INTERRUPTED` 失败。探针：修复前 `('completed', 'COMPACTION_RECOVERED_COMMIT', '摘要检查点已提交…')`，修复后 `('failed', 'COMPACTION_INTERRUPTED', …)`，与 `checkpointIssue` 一致。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1936](https://github.com/can4hou6joeng4/boss-harness/issues/1936)：会话导出对深嵌套持久字段、路径标点截断与审批字段未脱敏。`_render_json` 对条目 `status`/`toolName`/`executionState` 被改写成的深层嵌套结构抛 `RecursionError`，用户只得到 `-32603`；`_PATH_SEGMENT` 与已知前缀 `tail` 排除 `()`/`[]`/`'`，`/Users/a/客户A (机密)/合同.pdf`、`[2024]/resume.pdf`、`O'Brien/resume.pdf` 只遮到标点前，UNC 路径完全未识别，`redactions.paths` 计数却照常增长；`approval.decision`/`decidedAt` 原样导出，被改写成凭据或路径时三格式全部泄漏且 `redactions.secrets=0`。现在 JSON 编码失败降级为可读 `ValueError`，短标量经 `_short_text`/`_status_text` 收敛，`tool_execution_status()` 只接受有界状态字符串；路径段与前缀尾段允许括号、方括号与撇号并新增 UNC 分支，已知前缀按多段吞并，延续判定只认分隔符、`name.ext` 与大写同级目录（`/etc` 后的纯中文正文不再误吞）；`decision` 仅接受枚举否则 `unknown`，`decidedAt` 限长 64 并走 `redactor.sensitive`。探针：修复前三格式均有泄漏与 `deep.json` 递归失败，修复后 `leaks=[]`、`deep.json` 正常导出、15 个回归探针全部通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1942](https://github.com/can4hou6joeng4/boss-harness/issues/1942)：过期审批清扫对损坏会话空转，且计数与列表不一致。`_approval_expiry_loop` 逐项 `expire_approval()` 失败后 `continue`，而 `next_recoverable_approval_deadline()` 仍从陈旧索引返回同一个过去的 deadline，`max(0.05, 负数)` 让线程以 20 Hz 永久重试；会话日志损坏时每轮还会从文件头读到坏行，I/O 随日志增大线性上升。同时 `pending_approvals()` 有逐行 Python 校验，`pending_approval_counts()` 只靠 SQL `typeof` 守卫，空字符串列与 `+Inf` deadline 能通过后者：列表为空而徽标计数为 1，`+Inf` 行既不进入列表也不过期，徽标无法清除。现在抽出 `_approval_expiry_delay()` 按连续失败次数退避（1s、2s、4s…封顶 60s），失败表随 id 离开过期集合而清理；共享 WHERE 增补非空列与 `deadline BETWEEN 0 AND 1e15` 守卫，列表与计数始终一致。探针 13/13：健康路径延迟不变、四档退避与封顶、空列/`+Inf`/负 deadline 在列表与计数中同时消失、行恢复后同时重现；正常审批的列表/计数/裁决逐项不变，15 个回归探针全部通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1938](https://github.com/can4hou6joeng4/boss-harness/issues/1938)：被跳过的工具调用落库前未净化非可编码参数。`_skip_calls` 用 `dict(call.arguments)` 直接调 `start_tool_call`，不经 `validated_arguments` 也不经 `wire_value`；它覆盖 `stop_reason == "length"` 整批、串行暂停/取消后的剩余与并行批次未 prepare 的尾部，这些调用从不经过 `_prepare_tool`。模型参数里的 JSON 转义孤立代理项（`"\ud800"`）与 `1e999`（解码为 `inf`）都能通过 provider 的 `parse_constant`，落库时分别抛 `UnicodeEncodeError` 与 `ValueError`，`NOT_EXECUTED` 结算被击穿成通用回合失败；无效参数路径虽用 `wire_value` 净化，但 `wire_value` 当时不处理非有限浮点，`1e999` 仍原样落库。现在 `wire_value` 把 `inf`/`-inf`/`nan` 降级为 `None`（与孤立代理项、深度截断同层），`_skip_calls` 落库前应用 `wire_value`。探针：修复前 0 条落库并抛 `ValueError: Out of range float values`，修复后 2 条落库为 `not_executed` + `NOT_EXECUTED`；15 项断言通过，15 个回归探针与 5 个模型/协议探针不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1922](https://github.com/can4hou6joeng4/boss-harness/issues/1922)：Anthropic 流式解析只按 `delta.type` 分派，不校验增量与活动块的对应关系。`text_delta` / `thinking_delta` 指向不属于该类型的块时仍被拼进对应缓冲区；`content_block_stop` 又把任意有缓冲区的非 thinking 块当作 `text_end` 发出；已关闭块的迟到增量也被接受。错置文本会写入助手消息，却不进入续接描述符，落库后 `context.history` 每回合都报 `Anthropic continuation does not match its assistant response`，分支永久失败。现在 `text_delta` 仅接受活动中的 `text` 块、`thinking_delta` 仅接受活动中的 `thinking` 块，块关闭后拒绝；`content_block_stop` 仅对 `text` / `thinking` 发出对应结束事件，其他类型有缓冲区按损坏拒绝。探针：修复前 9/14，错置文本落库且回合为 `blocked`；修复后 14/14，畸形流在解析阶段以 `error` 返回，无文本落库，历史保持可读；合法 thinking / text / tool_use 流逐事件不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1923](https://github.com/can4hou6joeng4/boss-harness/issues/1923)：Anthropic `tool_use` 起始块用 `str(getattr(block, "id", "") or "")` 归一，缺失与空串 id 都记为空字符串；`name` 同样缺少校验，重复 id 也被静默接受。`stop_reason` 截断（`max_tokens`）时 `_skip_calls` 会把空 id 落库，续接描述符记录 `toolCallIds: [""]`，而工具条目回退使用自身 item id，恢复时 `Anthropic continuation no longer matches its tool batch` 永久失败；空名称还会恢复出上游必然拒绝的 assistant 消息。现在 `tool_use` 入口要求 id 为非空字符串、长度 ≤256 且同响应唯一，name 为非空字符串、长度 ≤256。探针：修复前 6/22，空 id 落库后历史永久失配；修复后 22/22，七类畸形块在解析阶段拒绝，无工具条目落库，合法双工具流的批次与续接正常。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1918](https://github.com/can4hou6joeng4/boss-harness/issues/1918)：工具批次的助手引用悬空让分支每个后续回合永久失败。`assistant_from_tool_batch()` 在 `toolBatchAssistantItemId` 找不到对应助手、或被重复编号遮蔽后解析到非 `agentMessage` 时抛 `ValueError`，`messages_from_items()` 不做降级，`TurnRunner.run` 在发模型请求前就失败；普通重试与自动压缩都无法恢复。现在引用缺失或被遮蔽时降级为无文本工具批次，工具调用与结果保留；助手存在但 `turnId` / `toolBatchId` / 状态真不一致时仍按既有 `ValueError` 报错。探针：修复前悬空引用与遮蔽均抛错，修复后降级且保留调用 id；真实批次错配仍拒绝。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1910](https://github.com/can4hou6joeng4/boss-harness/issues/1910)：损坏的检查点 `sourceDigest` 无格式校验，注入历史后会话永久超预算。`_validated_checkpoint()` 只要求来源摘要是非空字符串，`_history_projection()` 又把它原样拼进模型可见的摘要前缀；2 MB 的 digest 让历史约 200 万字符，`prepare` 永久抛 `ContextBudgetExceeded`，检查点覆盖全部条目时 `compaction_plan` 又分别以 `NoCompactionSource` 拒绝。现在 `sourceDigest` 按事件路径同一口径校验为 64 位小写十六进制，损坏检查点走既有回退：完整历史进入上下文、返回 `checkpointIssue`、压缩入口恢复。探针：修复前 `chars 2000056`、`prepare` 失败，修复后 `withinBudget: true`、`prepare` 与压缩计划均成功；正常摘要公开字段不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1911](https://github.com/can4hou6joeng4/boss-harness/issues/1911)：损坏的 `model_usage` 基线绕过用量校验，伪造出 10^12 token 预算。`context._usage_input_tokens()` 只检查非负 `int`，没有上限，也未复用 `usage.verify_usage` 的 `MAX_REQUEST_TOKENS`；保留匹配请求指纹、仅把 `usage.input` 改为 `10**12` 的记录会被当作可信基线，`_apply_usage()` 直接令估算等于该值；`_retained_usage_estimate()` 使用同一辅助函数，压缩校准同样受影响。现在单请求 token 上限（50,000,000）统一约束基线，超限记录按不可用跳过并回退字符估算。探针：修复前 1e12 token 且 `prepare` 失败，修复后回退正常估算；正常基线与边界值不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1912](https://github.com/can4hou6joeng4/boss-harness/issues/1912)：检查点未知字段被 `context/read` 原样回显，9 MB 字段永久超帧。公开检查点直接复制 payload 中除 `sourceItemCount` 外的所有键；追加 9 MB 未知字段后响应超过 8 MiB 帧预算，RPC 返回 `-32010 RESPONSE_TOO_LARGE`，检查点覆盖全部条目时压缩计划又拒绝。现在只投影内核写入的已知字段，未知键丢弃，字符串逐项限长、整数只接受 0 到 2^53-1，损坏的已知字段按缺失处理。探针：修复前响应 9,000,523 字节且读取失败，修复后小于 100 KB 并正常返回；正常摘要任务元数据逐项保留。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1904](https://github.com/can4hou6joeng4/boss-harness/issues/1904)：启动恢复无界累加流式增量，超长恢复条目让内核整体启动失败。`_restore_partial_streams()` 对每个 `running` 的 `agentMessage` 逐条累加 `agentMessage/delta` 与 `agentThinking/delta`，再把完整文本一次性写成 `revises` 条目。单条事件受 8 MiB 限制，五条各 7 MiB 的合法增量之和超过会话单行上限 32 MiB，`SessionStore.append` 抛 `ValueError`；异常发生在 `ApplicationService.__init__`，整个内核启动失败。现在恢复文本合计限制为 1,000,000 字符，单条恢复写入仍失败时只跳过该项，其他条目与会话继续启动。探针：修复前 5 × 7 MiB 增量重启抛「会话日志单行超过大小限制」，修复后启动成功并截到 100 万字符；正常小段增量逐字节恢复，文本与思考共用同一上限。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1905](https://github.com/can4hou6joeng4/boss-harness/issues/1905)：steering 队列项缺少 `expectedTurnId` 时领取崩溃。`queue_record` 允许该字段缺省，`TurnQueue.claim` 却直接下标访问；`KeyError` 从 `_stage_steering` 进入回合执行路径，该项保持 `queued`，线程内每个新回合都再次失败，steering 永不投递。现在只领取 `expectedTurnId` 为字符串且等于当前回合的 steering 项，缺失或非字符串按不可领取跳过。探针：修复前 `KeyError: 'expectedTurnId'`，修复后缺字段记录保持 `queued`、正常 steering 与 followUp 领取不变；6 项边界断言与 1,139 例矩阵回归通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1891](https://github.com/can4hou6joeng4/boss-harness/issues/1891)：会话导出在三个边界上静默失败或泄漏。`_deadline_text()` 在 `try` 之外执行 `float(value)`，审批期限被写成 `10**400` 这类超大整数时抛 `OverflowError`，markdown / json / html 三种导出全部变成 `-32603`；现在溢出与非有限值一样按无期限处理。导出把 `summaryJobId` / 摘要任务 `jobId` / `turnId` / `throughTurnId` 与回合头原样写入文档，这些标识来自持久记录、可被改写成本机路径或敏感值，绕过默认脱敏且不计入 `redactions`；现在与正文一样经过 `redactor.sensitive`，路径与敏感值被替换并计数。`_render_json()` 未使用 `allow_nan=False`，任何非有限数值都会静默产出严格解析器拒绝的 JSON；现在无法编码时返回可读中文错误。离线探针覆盖三种格式与 400 位整数期限、路径型标识：修复前三种格式均在期限处失败，修复后全部成功且导出可严格解析。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1890](https://github.com/can4hou6joeng4/boss-harness/issues/1890)：`_thread_metadata` 只校验投影行 `metadata_json` 的对象形状与 `id`，不校验协议字段类型。外部把 `threads.metadata_json.createdAt` 改成 `NaN`（源日志与 size/mtime 不变）后重启内核仍原样读出，`thread/list` 的响应帧在 `json.dumps(allow_nan=False)` 处失败，整个列表降级为 `RESPONSE_INVALID`；对象 `title` / 对象 `sessionId` / 对象 `projectId` 则让桌面按条目拒绝整份列表。现在投影要求 `createdAt` 与 `title` 为字符串、`sessionId` 与 `projectId` 缺省、null 或字符串，否则按索引损坏走既有按会话重建，`_index_thread` 从源日志恢复并把字段归一为合法值。离线探针覆盖 NaN 时间与三种对象字段：修复前列表无法严格编码且字段原样返回，修复后重建为合法值、健康会话不受影响。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1888](https://github.com/can4hou6joeng4/boss-harness/issues/1888)：`thread/resume` 快照的 `assertThreadSnapshot` 只校验 `thread.id`、`snapshotId` 与 `items`，冻结分支路径也只核对 `view/branch/threadId/snapshotId`，`thread.provider` / `thread.model` 原样放行；而 `thread/list` 的 `threadSummaryOf` 对同一字段要求缺省、null 或有界字符串。会话元数据被改写后，列表刷新虽然拒绝该条目但保留旧行，点击后 resume 回执被接受，对象写进 `activeSession.provider`，下一次渲染执行 `sessionProvider?.toLowerCase()` 抛 `TypeError`，整个应用被错误边界替换。现在新增 `assertSnapshotRouteFields()`，普通与冻结分支两个快照入口都要求线路字段缺省、null 或最多 200 字符的字符串。离线探针 11 项断言：修复前对象 / 数组 / 数字 / 布尔 / 201 字符值被接受，修复后全部拒绝，合法值与 id 归属校验不变。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1886](https://github.com/can4hou6joeng4/boss-harness/issues/1886)：工作区可由外部仓库决定，可能包含符号链接环（如 `.boss-harness/skills -> skills` 自环）。Python 3.12 的 `Path.resolve()` 检测到环时抛 `RuntimeError`：`SkillCatalog.__init__` 在 `ApplicationService` 构造期抛错，`__main__` 只捕获 `(OSError, ValueError)`，内核带回溯退出，桌面无法连接；`AttachmentStore.add()` 对穿过环的工作区路径同样抛错，被映射为 `-32603`。现在新增 `_resolved_or_absolute()`，解析失败时退回绝对路径，后续目录枚举与文件打开仍走既有 `OSError` 处理：`skills/list` 返回可读「无法读取技能目录」，`attachment/add` 返回可读 `-32602`。真实内核探针：修复前环工作区下进程退出（握手 BrokenPipe），修复后 `initialize` → `initialized` → `skills/list`（-32602）→ `thread/list` 全部正常；正常技能与附件读取结果不变，5 个既有探针 43 项断言通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1884](https://github.com/can4hou6joeng4/boss-harness/issues/1884)：固定上游 `boss-agent-cli@bdc7034` 的 v1 错误信封允许 `recovery_action` 为 `null`（`JOB_NOT_FOUND`、`ALREADY_GREETED`、`GREET_LIMIT`、`RESUME_NOT_FOUND` 等直接登记为 None；search 平台错误不传恢复动作时也是 null），而 `toolkit.snapshot_result()` 只接受字符串，把合法回执判为无效 `ToolResult`。真实平台错误码、消息与 details 被替换为「工具处理器返回了无效 ToolResult」，`RATE_LIMITED` / `ACCOUNT_RISK` 等暂停码在快照后不再触发 `should_pause`，回合越过平台风控继续执行。现在 `null` 按字段缺失处理并从错误对象移除，非字符串、非 null 的值仍被拒绝。离线探针 10 项断言：修复前 null 被拒且 RATE_LIMITED 快照后不再暂停，修复后全部通过，字符串恢复动作原样保留。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1880](https://github.com/can4hou6joeng4/boss-harness/issues/1880)：持久审批（`capabilities.durableApprovals`）经 `approval/respond` 裁决后，内核只在本进程表中静默取消对应的 server request，不向客户端发帧；宿主此前只转发裁决，既不清审批路由与截止计时器，也没有从客户端待答集合移除 `server-...` id，而这些 id 计入 256 条待答上限。同一回合大量审批会让计数越过上限，客户端以 "too many pending server requests" 断开健康内核并重连，丢掉运行中的回合；到期或回合终态时还会向已取消的请求写出无收益的 -32001。现在 `HarnessClient.forgetServerRequest()` 只释放本地待答槽位、不写帧；宿主在 durable 裁决成功后清理路由与计时器并释放槽位，`toolCall/completed` 与 `approval/decided` 通知也按会话与条目 / 审批 id 撤销对应路由。离线探针模拟两批共 400 条持久审批：修复前约第 257 条时触发待答上限断连，修复后全部送达且连接保持就绪。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1878](https://github.com/can4hou6joeng4/boss-harness/issues/1878)：`JsonRpcServer._dispatch` 的处理函数异常分支只捕获 `FrameTooLargeError`。错误帧在 `json.dumps(allow_nan=False)`（NaN/Infinity、不可序列化 data、深嵌套）或 UTF-8 编码（孤立代理项）处失败时，异常从 `serve_forever` 的捕获范围之外逃逸，内核进程带 traceback 退出，正在运行的回合与同进程内其它会话一起丢失。索引 `threads.metadata_json` 的裸 `json.loads` 不校验代理项，旧记录里的 `model` 可经 `_thread_route` 进入 `RpcError.data`，构成可达触发。现在异常分支与成功分支一致：诊断行失败不影响响应，超限帧走既有回退，其余编码失败降级为有界 `RESPONSE_INVALID`；`_respond_too_large` 与 params 校验分支也补齐文本 id 含代理项时的无 id 回退。离线探针 15 项断言通过（修复前 8 项异常逃逸），普通 `ValueError` 仍按 -32602 返回原消息。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1876](https://github.com/can4hou6joeng4/boss-harness/issues/1876)：会话索引 `_with_repaired_index` 触发重建时，若该会话源日志同时不可读，`_repair_thread_index` 抛出的 `ValueError` 会从 `list_threads` 直接逃逸；启动恢复 `_restore_partial_streams`、`SessionStore.recover` 与 `TurnQueue.recover` 都未捕获，内核每次启动都以「启动失败」退出，所有会话不可用。`_refresh_threads` 本已按文件隔离坏日志，这个组合绕过了既有约定。现在 `_with_repaired_index` 接受可选的跳过集合：`list_threads` 与 `list_threads_page` 在重建失败时把该会话记入 `unreadable_threads` 并从结果中跳过，健康会话照常列出；单会话读取仍抛可读 `ValueError`，指出具体损坏行。离线探针覆盖投影与日志双损坏：修复前列表与分页整体失败且内核退出码 2，修复后健康会话可见、损坏会话进入诊断集合、内核 `initialize` → `initialized` → `thread/list` 正常。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1874](https://github.com/can4hou6joeng4/boss-harness/issues/1874)：`useAutoCompaction` 的默认值解析只校验 `enabled`/`triggerPercent`/`keepRecentTokens`，随后把 `config/read` 回执对象原样作为策略返回；`ContextPanel` 把 `provider`/`model`/`effort` 直接作为 React 子节点渲染，对象或数组不会走 `??` 回退，渲染期抛「Objects are not valid as a React child」。面板位于应用级错误边界之外，整个桌面界面被错误页替换，重试后再打开面板又会重新崩溃；同一回执的另一消费方 `cockpitData` 早已做文本校验。现在解析时重建契约对象：线路字段只接受收敛后的非空文本（≤200 字符），其余按未提供处理；核心字段不合法整体按缺失处理，并丢弃透传的额外字段。离线探针 18 项断言通过，含修复前对象透传导致渲染抛错的复现。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1872](https://github.com/can4hou6joeng4/boss-harness/issues/1872)：`useContextPanel.refresh()` 先按 `context/read.compactionJob` 的引用写入 `lifecycleActive: true`，详情读取失败时只写 `error`，从不复位该值。渲染进程重载后错过 `context/compactionStarted`、且详情回执持续无法解析时，状态永久停在 `{ lifecycleActive: true, job: undefined }`：计划、开始与保留目标被 `blocked` 挡住，取消按钮只在 `job` 存在时渲染，分支切换被 `compacting` 拒绝，1.5 秒轮询也永不停止。现在连续 3 次无法核对运行中摘要详情后，把 `lifecycleActive` 降级为未知并给出说明（内核仍会拒绝并发压缩，`start` 会收到明确拒绝）；任一成功解析、引用不再 active 或连接断开时清零计数，单次瞬断不解锁。离线探针 10 项断言通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1870](https://github.com/can4hou6joeng4/boss-harness/issues/1870)：`useContextPanel` 的「开始结果未知」只在 `context/read.compactionJob === null` 时清理；内核在无活动任务时回退到该会话最近一条终态任务，引用通常非 null，而旧 jobId 或来源不同让 `applyJob` 的归属判定恒为 false，`discoveryStopped` 也不置位，`unknownStart` 就此永久残留，计划与开始按钮永久禁用且没有恢复入口。现在终态引用存在 `unknownStart` 时收敛为可读说明并清除该状态、恢复发现轮询；仍为 `running` 的任务（可能属于其它来源）保持原状，不猜归属。离线探针 9 项断言通过，并与既有 `missingJobPatch` 保持互补。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1868](https://github.com/can4hou6joeng4/boss-harness/issues/1868)：`archive_thread` 只按 `executionState == 'pending_approval'`、`approval` 是对象、无 `decision` 就调用 `_append_approval_decision`，绕过 `decide_approval`、索引重建与启动恢复都会先做的 `_valid_approval_item` 校验。缺顶层 `toolName` 的畸形待决审批会让 `thread/archive` 抛 `KeyError`（-32603）；修订已先落盘，于是留下 `decision=expired` 的伪裁决，而归档标记没有写入。现在归档前使用同一校验：畸形记录跳过、不写伪裁决，归档照常完成；合法待决审批仍结算为 `expired`。离线探针 4 项断言通过（修复前 3 项失败）。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1866](https://github.com/can4hou6joeng4/boss-harness/issues/1866)：`_event_page_entries` 校验了 `params_json` 与游标一致，但没有校验 `events.method` 的类型。外部把该列改写成 BLOB 后，坏值原样进入返回帧，`on_event_list` 的 `wire_size` / `json.dumps` 抛 `TypeError`；`events_after` 只捕获 `ValueError`，重建重试不可达，`thread/event/list` 与启动时的事件回放持续 -32603。现在 `method` 必须是非空字符串，否则按索引损坏抛可读 `ValueError`，由既有重建路径从 `events.jsonl` 恢复。离线探针 4 项断言通过（修复前 method 为 bytes 且页面不可序列化）。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1864](https://github.com/can4hou6joeng4/boss-harness/issues/1864)：`expired_pending_approvals` 与 `next_recoverable_approval_deadline` 没有复用 `_pending_approvals_where` 的 typeof 守卫。某行 `approval_id`/`item_id` 被外部改写成 BLOB 后仍进入过期结果集，`decide_approval` 抛 `APPROVAL_INVALID`，`expire_approval` 原样上抛；过期循环把整批放在同一个 `try` 里，5 秒后按同一顺序重取，坏行（deadline 最早）仍排首位 → 该行之后全部过期审批永不结算，重启也无效。现在两条过期查询补齐类型守卫，过期循环按审批逐项隔离异常。离线探针 7 项断言通过（修复前 BLOB 行进入结果、整批抛错、二次读取仍返回坏值）。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1862](https://github.com/can4hou6joeng4/boss-harness/issues/1862)：快照库 `_decode_item` 只校验解码结果是非数组对象，不校验协议必需的 `id`。外部改写或半写状态留下无 `id` 行后，`project_item` 与 `read_item_content`（在 sha256 比较之前）直接读 `item["id"]`，`KeyError` 经 RPC 映射为 -32603，整页 `thread/items/list` 与 `item/content/read` 永久内部错误，绕过既有的「会话快照已损坏」可读路径。现在 `SnapshotStore.page()` 与 `SnapshotStore.item()` 两个读取出口校验条目 `id` 为非空文本，损坏时抛既有可读 `ValueError`；`_decode_item` 对空对象的既有契约保持不变。离线探针 8 项断言通过（修复前 4 项失败）。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1860](https://github.com/can4hou6joeng4/boss-harness/issues/1860)：会话索引投影读取只校验 `metadata_json` 能解码成对象，不校验协议必需的 `id`，也不校验分页游标列类型。缺 `id` 时 `list_threads` 返回无 `id` 的会话对象，`search_messages` 与启动恢复读 `thread["id"]` 抛 `KeyError`（-32603），一条坏行即可让内核每次启动失败；`threads.updated_at` 或 `turns.first_ordinal` 被写成 BLOB 时，分页游标 `json.dumps` 抛 `TypeError`，绕过只捕获 `_IndexedMetadataError` 的重建路径。现在 `_thread_metadata` 校验投影 `id` 与主键一致，`list_threads_page` 与 `list_turns` 在构造游标前校验列类型（对齐 #1802 在分支回合分页的守卫），损坏时走既有按会话重建。离线探针 5 项断言通过（修复前 3 项失败）。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1858](https://github.com/can4hou6joeng4/boss-harness/issues/1858)：`useSessionBranches` 在 `context/read.compactionJob` 给出同一任务的终态引用（`active: false`）后，仍退回缓存的 `running` 任务去读详情；详情回执无法解析、归属不一致或持续返回非 -32011 错误时，`applyJob` 不会命中，清理分支只识别 -32011，缓存的 `running` 原样保留，2 秒轮询对同一坏回执无限重试，分支切换与发送新消息被永久挡住。现在新增 `unreadableJobSettlement` 纯函数与 `settleUnreadableJob`：终态引用下不可解析的详情按已结束结算并给出可读说明，轮询连续 3 次解析失败同样结算；运行中的任务与非终态引用保持原状。离线探针 9 项断言通过，`probe-branch-pages` 与 `probe-branch-summaries` 回归通过。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1585](https://github.com/can4hou6joeng4/boss-harness/issues/1585)：会话区与重试路径把消息的 `turnId` 直接当作普通对象的键查询本回合技能；未命中 `constructor`、`hasOwnProperty` 等原型成员时得到继承函数而不是 `undefined`，会话区随后对函数调用 `.map`，整段消息落入错误边界。现在新增 `turnSkillIdsFor()`，只认映射自己的条目，缺失或形状不符一律返回空数组，会话标签与重试请求共用该查询。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1587](https://github.com/can4hou6joeng4/boss-harness/issues/1587)：`queue/list` 与 `thread/resume` 的队列元数据此前只要求待处理数不超过持久总数、分类合计等于待处理数，没有要求待处理数不少于已载入的待处理条目、每个分类不少于同状态的可见条目；异常响应因此能在 3 条待处理记录上方显示「1 项待处理」，或显示「排队 0」同时列出排队消息。现在矛盾元数据按缺失处理，面板与徽标回退到可见计数；合法截断响应逐字段保留。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1591](https://github.com/can4hou6joeng4/boss-harness/issues/1591)：`approval/list` 的按会话计数此前只校验每项非负、合计不小于已返回条目，没有要求每个有可见审批的会话都出现且计数不少于可见条数；异常响应可以让侧栏会话徽标显示 1，而通知面板同一会话下列出 3 条待审批，甚至把仍有审批的会话移出「待你处理」。现在可见会话缺失或计数偏小时整组计数与总数按缺失处理，铃铛回退到已返回条目并保留「至少 N」语义；合法响应逐字段保留。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1595](https://github.com/can4hou6joeng4/boss-harness/issues/1595)：会话用量的 `bucketOf()` 此前只校验各计数为非负安全整数，没有要求 `verifiedRequests + unverifiedRequests === requests`，也没有要求 `unverifiedReasons` 合计等于 `unverifiedRequests`；异常响应会让面板显示「请求 10 次（计入 2 次，不计入 1 次）」而剩余 7 次没有分类，或让未计入原因合计大于未验证请求数。现在两项不变量任一不满足即整体拒绝该 bucket，回合明细、摘要任务与 CSV 导出不再扩散矛盾数字；原因展示仍最多 20 项，但合计校验覆盖全部键。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1599](https://github.com/can4hou6joeng4/boss-harness/issues/1599)：会话恢复此前忽略冻结快照返回的 `itemCount`；`thread/items/list` 提前结束时，少读的消息、工具调用与审批卡会被当成完整历史展示，事件重放又从快照游标之后开始，缺失条目不会补回。现在 `itemCount` 必须是非负安全整数，分页结束后的实际条目数必须与它一致，少读或多读都整体失败且不发布部分快照；普通与分支冻结快照共用校验，旧内核缺省 `itemCount` 时保持原行为。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1603](https://github.com/can4hou6joeng4/boss-harness/issues/1603)：会话条目分页此前不校验条目形状与唯一性；缺少 `id` 的条目会进入快照后被消息映射静默丢弃，重复 `id` 会让同一消息、审批卡或工具卡渲染两次，并让本地状态合并与重试目标无法区分。现在每个条目必须是带非空、最长 200 字符字符串 `id` 的对象，同一轮恢复内 `id` 必须唯一，同页或跨页重复都整体失败且不发布部分快照；`itemCount` 校验与旧内核兼容路径不变。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1607](https://github.com/can4hou6joeng4/boss-harness/issues/1607)：会话用量分页此前不校验回合标识唯一性与总数；同一 `turnId` 跨页重复会让同一回合展示两次并被重复计入列表，`nextCursor: null` 提前结束时界面仍按第一页显示「N 个回合有记录」却只有 M 行，且没有截断提示。现在分页读完后同一 `turnId` 只能出现一次，未截断时累计条目数必须等于最后一页声明的 `turnCount`，任一不满足即整体报错且不展示部分数据；面板计数改用最后一页，避免分页期间并发新增回合造成列表行数多于声明；达到页数上限的截断读取只校验已读部分不重复。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1611](https://github.com/can4hou6joeng4/boss-harness/issues/1611)：会话导出回执此前只要求 `turnCount` 与 `exportedTurnCount` 是非负安全整数，没有要求已导出回合数不超过视图声明总数；矛盾回执会让弹窗显示「10 / 5 个回合」。现在主进程 `validateThreadExportResponse` 与渲染层回执校验都拒绝 `exportedTurnCount > turnCount`，矛盾回执按无法识别的导出结果处理且不写盘；合法完整、截断与取消回执不受影响。只改主进程与渲染层，不新增 RPC、不改变协议或版本号。
- [Issue #1615](https://github.com/can4hou6joeng4/boss-harness/issues/1615)：`approval/list` 的按会话持久计数在 `truncated: false` 时只要求覆盖已返回条目，没有要求与可见条目完全一致；一条审批因缺少 `deadline` 等字段被丢弃后，面板只列出 2 条，铃铛与侧栏仍按持久计数显示 3 项且不提示还有未展示条目，重复 `approvalId` 去重后同理。现在未截断时合计与每个可见会话的计数必须与可用条目完全一致，偏大或分布不符即丢弃整组计数并把列表标记为截断，徽标回到「至少 N 项待审批」；内核截断且计数覆盖可见条目、旧内核缺省计数与完全一致的合法响应保持不变。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1619](https://github.com/can4hou6joeng4/boss-harness/issues/1619)：`runtime/resources/read` 的渲染层读取器只校验计数为非负整数且覆盖已返回明细，没有校验容量不变量；矛盾快照会让驾驶舱显示「并发业务回合 5 / 2」「保留回合 10 / 2」，或让运行中 owner 数少于保留回合数而掩盖记录缺口。现在 `activeTurnCount` 不得超过 `turnCapacity`、`retainedTurnCount` 不得超过 `maxRetainedTurns`、`ownerCount` 不得少于 `retainedTurnCount`，任一不满足即整体报错且资源卡显示读取失败；计数等于容量、全零与截断明细等合法快照不受影响。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1623](https://github.com/can4hou6joeng4/boss-harness/issues/1623)：`config/read` 的会话索引健康度在 `unreadableThreadCount: 0` 时直接返回「正常」，不检查同一响应中的 `unreadableThreadIds`；计数为零却列出不可读 id 的矛盾响应会让设置页显示「会话索引：正常」，损坏的会话文件没有任何提示。现在计数为零且明细包含至少一个合法 id 时视为矛盾响应、显示「未报告」；明细缺失、为空或全部非法仍显示「正常」，正计数的去重、上限与过滤保持不变。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1627](https://github.com/can4hou6joeng4/boss-harness/issues/1627)：`context/read.compactionJob` 的摘要任务引用此前被渲染层直接读取 `active` 与 `jobId`，没有校验形状；引用缺少 `jobId` 却带 `active: true` 时，上下文面板把占用状态写死，每 1.5 秒轮询同一响应，计划与开始按钮被永久阻断，也没有任务可核对或取消。现在新增 `compactionReferenceOf()`：`null` 与缺省原样保留，对象必须带合法 `jobId`（`[A-Za-z0-9_-]{1,128}`）、已知 `status` 与布尔 `active`，否则整体拒绝并由读取路径显示失败；上下文面板与分支面板共用该校验。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1631](https://github.com/can4hou6joeng4/boss-harness/issues/1631)：`context/read.branchSummaries` 此前只检查是否为数组，条目直接进入会话区状态；会话区渲染期读取 `targetTurnId` 定位摘要标记，标记组件再读取 `abandonedTurnIds.length` 与 `characters`，一条 `null`、缺字段或非数组条目会让整段会话区落入错误边界，重复 `entryId` 还会让多个标记共用同一 key 与正文读取目标。现在新增 `branchSummariesOf()`：逐项校验 `entryId`（非空、最长 200 字符、同一响应内唯一）、三个引用字段（字符串或 `null`，缺省按 `null` 兼容旧内核）、`abandonedTurnIds`（最多 1000 项的字符串数组）与 `characters`（非负安全整数）；非法条目丢弃并计数，面板提示「有 N 条摘要标记无法识别，已隐藏」，合法条目继续展示，分支端点与切换不受影响。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1635](https://github.com/can4hou6joeng4/boss-harness/issues/1635)：分支弹窗读取 `thread/branches/list` 与分支视图的 `thread/turns/list` 时只校验 `threadId`、`view` 与数组本身，条目直接进入状态；端点含 `null`、字符串或缺 `turnId` 的条目时，渲染期读取 `endpoint.turnId` 会抛错，而弹窗位于应用级错误边界内，整个界面被替换为错误页，缺 `turnId` 还会把非法切换目标发给内核；回合列表用 `filter` 静默丢弃其他会话的条目，列表少于内核声明且没有截断提示；重复 `turnId` 让两行共用 key。现在新增 `branchEndpointOf()`、`branchTurnOf()` 与 `uniqueTurnIds()`：端点校验锚定 id、状态、深度、布尔标记与可选文本，回合要求 `threadId` 等于当前会话且状态已知，分页合并后 `turnId` 必须唯一，首例的 `branched` / `leafTurnId` / `turnCount` 同时校验；任一不满足即整体报错并显示「读取分支失败」，保留上一次成功状态，不崩溃、不静默少行、不发出非法切换目标。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1639](https://github.com/can4hou6joeng4/boss-harness/issues/1639)：`listThreads` 分页读取 `thread/list` 时只校验 `response.threads` 是数组，条目直接映射为侧栏会话；`null` 或字符串条目在映射期抛错，缺 `id` 会被 `sessionRows` 的按 id 去重静默吞掉，跨页重复 `id` 让多个会话共用同一选择 / 重命名 / 删除目标，缺 `title` 显示 `undefined`，非字符串 `lastTurn.turnId` 会作为恢复目标继续传递。现在新增 `threadSummaryOf()` 与 `uniqueThreadIds()`：逐项校验对象形状、`id`（非空、最长 200 字符）、`title`（最长 500）、`updatedAt`、`archived`、`provider` / `model` / `reasoningEffort` 与 `lastTurn` 的 `turnId`、状态及可选错误码 / 恢复策略，分页合并后 `id` 必须唯一；任一不满足即整体报错，侧栏保留上一次成功列表，不展示部分可疑数据。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1643](https://github.com/can4hou6joeng4/boss-harness/issues/1643)：`listSkills` 读取 `skills/list` 时只校验 `response.skills` 是数组，条目直接传给「技能与工具」页；同一响应里的 `problems` 已有逐项校验，`skills` 没有。`null` 或字符串条目会让 `filterSkills()` 在读取 `id` / `name` / `description` 前抛错，`resolveSkillFocus()` 同样抛错，技能页渲染失败；缺 `id` 或重复 `id` 让选中项、`find()` 与读取正文的 `expectedDigest` 指向错误条目，编辑与删除可能作用在另一项上；`digest` 缺失会让读取、写入与删除请求带空摘要，`bytes` 非数值让大小显示为 NaN。现在新增 `skillDescriptorOf()` 与 `uniqueSkillIds()`：逐项校验对象形状、`id`（非空、最长 200 字符、目录内唯一）、`name`（最长 200）、`description`（最长 2000）、`digest`（非空、最长 128）、`bytes`（非负安全整数）与两个截断标记；任一不满足即整体报错并保留上一次成功目录。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1647](https://github.com/can4hou6joeng4/boss-harness/issues/1647)：`configuredModels` 读取 `model/list` 时只校验 `response.models` 是数组，条目直接进入输入区模型菜单与驾驶舱；`null` 条目让 Composer 的 `models.filter(model => model.configured && model.available)` 在渲染期抛错，`provider` / `id` 非字符串让 `model.provider.slice(0, 1)` 抛错，缺 id 或重复 `provider:id` 让菜单项共用 key 并把空目标发给内核，`configured` / `available` 非布尔时未配置或不可用的线路被当成可选，畸形 `capabilities` 让上下文窗口显示为 `NaN`。现在新增 `modelDescriptorOf()` 与 `uniqueModelKeys()`：逐项校验 `id`（非空、最长 200 字符）、`provider`（非空、最长 100）、两个布尔标记，以及出现时的 `capabilities`（非负安全整数上下文窗口与输出上限、字符串来源、布尔估算标记、最多 16 项的字符串推理档位），同一列表内 `provider:id` 必须唯一；任一不满足即整体报错，调用方保留旧选项并提示。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1651](https://github.com/can4hou6joeng4/boss-harness/issues/1651)：`listTools` 读取 `tool/list` 时只校验 `response.tools` 是数组，条目直接传给「技能与工具」页与驾驶舱；`null` 或非对象条目让 `tools.map(tool => tool.name)` 在渲染期抛错并落入应用级错误边界，缺 `name` 或重复 `name` 让 React key 冲突、清单行错配，`readOnly` / `requiresApproval` 非布尔时按 truthy 显示「只读 / 需要授权」，与实际权限不符，畸形 `inputSchema` 让协议数据不可用。现在新增 `toolDescriptorOf()` 与 `uniqueToolNames()`：逐项校验 `name`（非空、最长 200 字符、清单内唯一）、`description`（字符串）、两个布尔标记、`inputSchema`（非数组对象），以及出现时的 `maxModelResultBytes`（非负安全整数）与 `executionMode`（`sequential` / `parallel`）；任一不满足即整体报错，调用方保留旧清单并显示读取失败。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1655](https://github.com/can4hou6joeng4/boss-harness/issues/1655)：`connectionReport` 读取 `connection/check` 与 `connection/read` 时把回执直接返回，设置页假定 `cli`、`model`、`platform` 三张卡片都存在并读取 `state`、`summary`、`authState`、`browserSourcePolicy`、`checkedAt`。缺卡片或卡片为 `null` 时 `Object.values(report).some(check => check.state === "checking")` 与 `report.platform.authState` 在渲染期抛 `TypeError`，设置页落入错误边界；未知 `state` 让徽标显示空白，未知 `browserSourcePolicy` 显示空来源，非字符串 `checkedAt` / `summary` 让时间行与诊断结论渲染出非预期内容。现在新增 `connectionReportOf()`：三张卡片必须同时存在，`state` 为已知六态、`summary` 为字符串（最长 4096），`checkedAt` / `code` 缺省或 `string | null`（最长 64 / 120），`provider` / `model` / `authState` / `binarySource` 出现时为字符串（最长 200），`browserSourcePolicy` 为四个已知值、`requestRejected` 为布尔；任一不满足即整体报错，诊断入口沿用既有 `catch` 显示「无法读取连接检查结果」。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1659](https://github.com/can4hou6joeng4/boss-harness/issues/1659)：恢复流程的普通 `thread/resume` 路径直接使用回执的 `thread`、`snapshotId` 与 `items`，分支快照路径两处都要求 `thread.id` 等于请求会话，普通路径没有同样的身份校验。回执属于另一个会话时，`onSnapshot` 按快照自身的 `thread.id` 写缓存、队列投影与运行状态，调用方随后用该快照的 `provider` / `model` 更新当前选中会话的线路——用户在会话 A 看到会话 B 的消息归属与模型线路；`thread` 缺失时 `snapshot.thread.id` 抛 `TypeError` 被吞成通用失败文案；畸形 `snapshotId` 直接用于条目分页请求。现在新增 `assertThreadSnapshot()` 与 `threadSnapshotOf()`：快照必须是对象、`thread` 为对象且 `id` 等于请求会话、`snapshotId` 缺省或 32 位小写十六进制、`items` 为数组；普通 `thread/resume` 路径与 0.1 兼容的 `thread/read` 路径在消费前调用，不合法即按恢复失败处理并保留明确原因。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1663](https://github.com/can4hou6joeng4/boss-harness/issues/1663)：`startThread`、`forkThread` 与 `setThreadReasoning` 对 `thread/start`、`thread/fork`、`thread/reasoning/set` 的回执只校验 `thread.id` 是非空字符串，随后直接读取 `title`、`updatedAt`、`toolPolicy`、`provider`、`model` 与 `lastTurn` 写入侧栏与当前会话；同一文件的 `thread/list` 条目已由 `threadSummaryOf` 逐项校验，写操作回执没有复用。`thread/fork` 会读取源会话的持久记录：源标题损坏为对象时回执被直接插入侧栏并选中，渲染期抛错落入应用级错误边界；未知 `toolPolicy` 绕过 `?? "approval"` 回退进入条目，审批策略展示与实际不符；畸形 `lastTurn` 让运行中与中断标记错置。现在 `threadSummaryOf` 补充 `toolPolicy` 校验（缺省或 `readOnly` / `approval`），三个写操作回执统一复用它，缺 `title` / `updatedAt`、非字符串线路字段或畸形 `lastTurn` 按各自既有错误文案整体拒绝。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1667](https://github.com/can4hou6joeng4/boss-harness/issues/1667)：内核 `tool/list` 已返回 `executionMode`，驾驶舱工具清单对串行工具显示「串行」徽标，但「技能与工具」页只显示「只读 / 需要授权」，同一份内核数据在两个页面呈现不一致，用户无法判断哪些工具串行执行。现在工具行在 `executionMode` 存在时追加 `· 串行` 或 `· 并行`，字段缺省时保持原有文案；文案与驾驶舱一致。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1671](https://github.com/can4hou6joeng4/boss-harness/issues/1671)：`usePlatformLogin` 的四个写入点（`onPlatformLogin` 广播、初始 `status` 读取、`open` 与 `cancel` 回执）都把主进程回执直接写入界面状态，未校验 `state`、`summary`、`code`、`phase`、`identity`、`threadId` / `browserId` 与 `browser` 四个布尔字段。`AppShell` 直接读取 `status.threadId`，引导卡片直接渲染 `status.summary` / `status.code`：`status` 缺失时整个会话壳渲染抛错，未知 `state` 在 `visibleIn` 里按「登录进行中」处理并让引导条常驻且没有可用的取消路径，`code` 或 `summary` 为非字符串对象时 React 渲染直接抛错。现在新增 `platformLoginStatusOf()` 逐项校验并只保留协议字段；四个写入点在无法识别时保留上一次有效状态并给出可见原因，`open` 的非法回执按失败处理并复用 `fallbackLoginStatus`，`cancel` 的非法回执按「取消结果未确认」提示并保留分栏与取消入口。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1675](https://github.com/can4hou6joeng4/boss-harness/issues/1675)：设置对话框的「连接」分区有独立的登录状态订阅，`onPlatformLogin` 广播与初始 `platformLogin("status")` 读取仍直接 `setLogin`，账号行直接渲染 `login.summary` / `login.code`；这两个字段为非字符串对象时设置对话框渲染抛错，未知 `state` 又让 `loginBusy` 为 `false`，而 `state !== "idle"` 仍展示 summary，界面把「正在登录」当成可重新登录。现在两处读取都经 `platformLoginStatusOf()` 校验，无法识别时保留上一次有效状态并在账号行显示原因；新增 `loginSettled()`（`succeeded` / `blocked` / `failed` / `cancelled`）与既有 `loginActive()` 对称，广播只在终态时重读连接检查，`loginBusy` 改用 `loginActive()`。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1679](https://github.com/can4hou6joeng4/boss-harness/issues/1679)：主进程 `PlatformLogin` 与内核 `platform/login/*` 之间没有形状校验，`platform/login/start`、`complete` 与 `read` 的回执经 `update()` 直接写入 `this.status`，而 `update()` 不做任何检查：缺 `state` / `summary` 或未知 `state` 会让占用判定与 `cancel()` 的 `active` 判定同时失效——用户点「取消」后内核请求已发出，界面却不会出现「已取消」；`read()` 广播的非法值又会被渲染层整体拒绝，主进程与界面脱节。现在新增 `loginAttemptOf()` 与 `attemptIdOf()`：`start` 回执无法识别时按 `LOGIN_OPEN_FAILED` 失败处理并只对合法 `id` 补发取消，`complete` 回执无法识别时按 `LOGIN_SAVE_FAILED` 处理并取消内核 attempt，`read` 回执无法识别时以 `LOGIN_READBACK_INVALID` 独立结束，不再误写成连接中断。只改主进程，不改变 RPC、协议或版本号。
- [Issue #1683](https://github.com/can4hou6joeng4/boss-harness/issues/1683)：跨会话搜索只检查 `thread/search` 回执的 `matches` 是数组，条目字段直接进入搜索弹窗：`threadId` / `itemId` 被拼进选项 key 与定位意图，`snippet` 交给关键词高亮做归一化与切片。`snippet` 为非字符串对象时渲染期抛错，搜索弹窗进入错误边界；标识为对象或空串时选项 key 退化为 `[object Object]`，「打开并定位消息」失效；未知 `role` 把工具命中显示成「助手」并丢失展开工具块的意图；条目数也没有上限。现在新增 `threadSearchResultOf()`：`matches` 必须为数组且不超过 200 条，逐项要求 `threadId` / `itemId` 非空 ≤200、`threadTitle` 字符串 ≤4096、`role` 属 `user` / `agent` / `tool`、`snippet` 字符串 ≤4096，`truncated` 缺省按 `false`、存在时必须为布尔；任一不符整体拒绝，弹窗沿用既有错误态。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1687](https://github.com/can4hou6joeng4/boss-harness/issues/1687)：`App.tsx` 处理 `session/error` 通知时直接读取 `event.params.message` 并写入提示条，没有形状校验。`message` 为对象或数组时会被原样交给 `<span>{error}</span>`，React 渲染期抛 `Objects are not valid as a React child`，整屏落入应用级错误边界；`threadId` 也只靠真值判断，非字符串会进入错误缓存与提示归属记录。现在新增 `sessionErrorNoticeOf()`：`threadId` 必须是非空、最长 200 字符的字符串；`message` 缺省或为 `null` 时回退通用文案，是字符串时折叠空白并按 600 字符上限截断（代理对不切开），其余类型整条通知丢弃并保留上一次有效提示。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1691](https://github.com/can4hou6joeng4/boss-harness/issues/1691)：上下文面板读取 `context/read` 后只比较 `budget.threadId`，其余字段直接进入面板状态。`systemPromptInfo.sections` 为非数组真值或条目为 `null` 时，面板渲染期读取 `.map` / `section.title` 抛 `TypeError`，整个界面落入应用级错误边界；`branchSummaryIssues` 为非数组真值且 `branchSummaryIssueCount` 为正数时 `.slice` 同样抛错；未知工作区说明状态、非对象用量与畸形检查点也没有约束。现在新增 `contextReadOf()`：`threadId` 必须等于当前会话，`requestSource` 属已知三态，七个计数为非负安全整数，四个文本字段限长，三个布尔字段为布尔，`usage` / `checkpoint` 为对象或 `null`，任一不符整体拒绝并保留上一次成功状态；工作区说明、系统提示分段（逐项过滤、最多 64 段）、分支摘要问题条目（逐项过滤、最多 20 条、总数不得少于可见条数）与派生出字段逐项收敛，`compactionJob` 复用 `compactionReferenceOf()`。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1695](https://github.com/can4hou6joeng4/boss-harness/issues/1695)：工作区说明的两个读取入口（「技能与工具」页与上下文面板编辑器）只要求 `status` 为字符串，`STATUS_TEXT[未知状态]` 得到 `undefined`，状态行显示成空白；`bytes` 未校验，非法值经 `toLocaleString` 显示成 `NaN` 或 `[object Object]`；编辑器读取完全不校验 `status` 与 `bytes`。现在新增 `workspaceInstructionStatusOf()` 与 `workspaceInstructionBytesOf()`：状态只接受 `loaded` / `empty` / `too_large` / `unreadable`，字节数只接受 `null` 或非负安全整数，两个入口同时要求 `limitBytes` 为非负安全整数；无法识别时按既有错误文案提示，不再把未知状态显示成空白或把坏计数渲染成错乱文本。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1699](https://github.com/can4hou6joeng4/boss-harness/issues/1699)：`context/compact/plan` 的回执此前只核对 `threadId`、`keepRecentTokens`、`selection`、`sourceDigest` 与 `throughTurnId` 是否存在，其余字段直接进入上下文面板。面板渲染计划时直接访问 `plan.retainedTurnIds.length`、把 `sourceItemCount` / `retainedItemCount` / `estimatedRetainedTokens` 交给 `toLocaleString`，并把 `firstItemId` / `lastItemId` / `firstKeptItemId` 作为 React 子节点；缺字段会抛 `TypeError`，对象字段会让 React 拒绝渲染，整个面板落入应用级错误边界。现在新增 `contextPlanOf()`：身份、来源摘要、回合边界、条目数、保留回合、首个保留条目与保留校准字段逐项校验；`retainedTurnIds` 必须是非空字符串数组且不重复，`firstKeptItemId` 只允许 `null` 或合法 id 并与 `retainedItemCount` 一致，`retentionUsageApplied` 为真时锚点计数必须大于零；面板不渲染的 `sourceItemIds` / `digestVersion` / `checkpointDigest` 出现时校验一致性、缺失时保持旧内核兼容。非法回执按「无法生成整理计划」显示原因，不再写入状态进入渲染。只改渲染层，不改变 RPC、协议或版本号。

- [Issue #1702](https://github.com/can4hou6joeng4/boss-harness/issues/1702)：上下文编辑弹窗把 `context/edit/read` 回执的 `reason` 直接作为状态说明与警告正文渲染，原 `validate` 只校验身份、来源摘要、正文与布尔标记，遗漏了这一可选字段：对象或数组让 React 抛“Objects are not valid as a React child”，整个弹窗落入应用级错误边界；超长字符串没有上限，会铺满弹窗；数字与布尔被静默显示成原因文本。现在新增 `contextEditOf()`，读取与提交后的回读共用同一入口：`threadId` / `itemId` 必须与请求一致且长度合法，`sourceDigest` 必须是 64 位小写 hex，`originalText` 与 `currentText` 逐项限长，`canEdit` / `excluded` 必须为布尔，非法整体拒绝并沿用既有提示；`reason` 只接受字符串，`null`、缺失与纯空白按「没有原因」处理，过长截断到 4096 字符且不切开代理对，对象、数组、数字与布尔一律拒绝；未知字段丢弃，不进入渲染状态。只改渲染层，不改变 RPC、协议或版本号。

- [Issue #1705](https://github.com/can4hou6joeng4/boss-harness/issues/1705)：摘要任务通知与回执经 `isContextJob()` 判定后直接写入上下文面板，该判定只校验身份、来源摘要、状态与 `kind`，其余展示字段原样进入 `ContextPanel`：`totalCharacters` / `processedCharacters` / `modelRequestCount` 为 `null` 时 `toLocaleString` 抛 `TypeError`，为对象时显示成 `[object Object]`；`message` / `summaryProvider` / `summaryModel` / `summaryEffort` 为对象或数组时作为 React 子节点渲染抛错，整个界面落入应用级错误边界；未知 `reason` 被当成自动摘要，触发原因行显示空白且取消入口消失；`turnId` / `code` 为对象时经模板字符串显示成 `[object Object]`。现在新增 `contextJobOf()` 取代 `isContextJob()`：身份、64 位小写来源摘要、状态与 `kind` 非法时返回 `null`，通知按不适用丢弃、回执按归属不一致处理；`reason` 只接受 `threshold` / `budget` / `overflow`，文本字段限长且不切开代理对，五个进度计数只接受非负安全整数，`requestRejected` 为布尔，分支摘要的 `abandonedTurnIds` 逐项校验并限制条目数；缺失或 `null` 的可选字段按旧内核未提供处理，未知字段与面板不渲染的 `result` 历史快照不进入状态。三个回执入口与通知入口共用同一校验。只改渲染层，不改变 RPC、协议或版本号。

- [Issue #1708](https://github.com/can4hou6joeng4/boss-harness/issues/1708)：`task/read` 的 `kind: turn` 路径先调用 `turn_snapshot(entries, turn_ids={task_id})`，筛选条目时把 `payload.get("queueId")` 直接用于集合成员测试。持久记录中的 `queueId` 若不是字符串（数组、对象等），`not in set` 抛 `TypeError: unhashable type: 'list'`，整个读取返回 `-32603` 内部错误，任务详情面板无法打开；同一函数后续写入 `queueId` 时已有 `isinstance(str)` 与格式校验，筛选处缺少同样的防护。现在成员测试前先要求队列标识是字符串：非字符串按「不在查询集合内」处理，不再参与集合运算；`queue_ids=None` 时仍按回合身份筛选，`turn_ids=None` 时不过滤，合法标识的归属筛选、重复与冲突标记、条目上限及阶段合并路径保持不变。只改内核，不改变 RPC、协议或版本号。

- [Issue #1711](https://github.com/can4hou6joeng4/boss-harness/issues/1711)：`SnapshotStore._read_item()`、`page()` 与 `item()` 直接返回 `json.loads()` 的结果，只捕获解析异常，没有要求解码结果是对象。快照库属于持久数据：条目 `payload` 若被损坏或改写为 JSON 数组、字符串或 `null`，`json.loads()` 正常返回非对象，随后 `project_item()` 的 `item.items()`、`read_item_content()` 的 `.get` 以及 `_entry()` 的旧条目合并都抛 `AttributeError`，逃逸成 `-32603` 内部错误，而不是既有的「会话快照已损坏；请重新打开会话」提示。现在新增统一解码入口 `_decode_item()`：载荷必须是字符串，解码结果必须是非数组对象，否则按快照损坏抛出既有 `ValueError`；三处读取共用该入口，`page` 保留先按字节预算跳过再解码的顺序，BLOB 列值同样按损坏处理。只改内核，不改变 RPC、协议或版本号。

- [Issue #1714](https://github.com/can4hou6joeng4/boss-harness/issues/1714)：`AttachmentStore.read_chunk()` 与 `_read_from_entries()` 在 `_read_object()` 校验摘要与长度后直接调用 `data.decode("utf-8")`，没有捕获解码失败。附件对象与持久记录可被外部改写（记录中的 `digest` 与对象内容同时替换时仍能通过摘要校验），内容不是 UTF-8 时抛 `UnicodeDecodeError`；它不属于 `ValueError`，逃逸成 `-32603` 内部错误，消息还含随内容变化的字节位置。现在新增 `_decode_attachment_text()`：解码失败统一转换为「附件内容不是 UTF-8 文本；请重新添加」的 `ValueError`，`attachment/read`、分段读取与上下文注入三条路径共用；合法 UTF-8（含中文、BOM 与补充平面字符）、空内容与字符长度口径保持原样。只改内核，不改变 RPC、协议或版本号。

- [Issue #1717](https://github.com/can4hou6joeng4/boss-harness/issues/1717)：`App.tsx` 读取 `turn/continuation/read` 后只核对 `threadId` 与 `sourceTurnId`，其余字段直接进入 `continuationCheck.response` 并交给会话区渲染。`warning` / `reason` 为对象或数组时作为 React 子节点抛错，整个会话区落入应用级错误边界；`eligible` 非布尔时按 truthy 显示「继续中断回合」按钮；未知 `boundary` 一律显示成「已完成的工具批次」；`completedToolCalls` 对象经模板字符串显示成 `[object Object]`；`reasonCode` 没有上限。现在新增 `continuationReadOf()`：身份必须与请求一致且长度合法，`eligible` 必须为布尔，`warning` 必须为字符串并限长；`boundary` 只接受 `user_input` / `completed_tool_batch`，`completedToolCalls` 只接受非负安全整数，`reason` / `reasonCode` 去空白、限长且不切开代理对；缺失或 `null` 的可选字段按旧内核未提供处理，未知字段丢弃，非法回执按既有预检失败路径提示。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1720](https://github.com/can4hou6joeng4/boss-harness/issues/1720)：持久化 `turn` 记录的载荷此前会被 `_turns()` 整体合并进内部回合对象，只有 `firstOrdinal` / `lastOrdinal` 被还原，`boundaryOrdinal` 可以被同名键覆盖；首条终态记录合并后该值直接留在内部对象上，`fork_thread()` 的边界切片拿到字符串会抛 `TypeError`（JSON-RPC `-32603` 内部错误），拿到负整数则静默移动切片、生成边界错误的分支。现在三个顺序记账字段收进 `_TURN_INTERNAL_FIELDS`，合并载荷时跳过同名键，`_public_turn()` 复用同一集合；边界序号只由记录顺序决定，损坏载荷按正常边界分支。离线探针覆盖正常记录、字符串与负整数载荷：分支都包含完整消息，内部边界仍为整数，公开回合不携带顺序字段。不改变 RPC、协议或持久化格式。
- [Issue #1723](https://github.com/can4hou6joeng4/boss-harness/issues/1723)：`QueuePanel` 的存活标记只在 effect cleanup 里置为 `false`，setup 不恢复；React 18 开发构建的 `StrictMode` 执行 `setup → cleanup → setup` 后标记永久为 `false`，批量重新排队 / 批量撤回的进度停在 `0/N`，循环结束后跳过 `setBatch(null)`（批量撤回还跳过 `setRemoveTargets(null)`），刷新、编辑、单条与批量按钮全部永久禁用，撤回确认框也无法关闭，实际队列操作可能已经完成。现在与 `Composer`、`BranchSummaryNotice` 一致，在 setup 中恢复 `alive.current = true`；真实卸载仍停止后续批量请求。`npm run typecheck`、`npm run build` 通过。生产打包的 React 不双调用 effect，本次修复针对开发构建与热更新路径。不改变 RPC、协议或版本号。
- [Issue #1726](https://github.com/can4hou6joeng4/boss-harness/issues/1726)：`_refresh_threads()` 清理陈旧投影行时直接对 `threads.rollout_path` 调用 `Path()`。该列虽声明为 TEXT，SQLite 非 STRICT 表允许存入 BLOB 或整数；一条外部改写或损坏的行会让 `SessionStore.__init__` 抛 `TypeError`，内核启动失败，运行中的 `thread/list` 与维护路径同样返回 `-32603`。现在只有字符串路径参与状态目录判断：源日志已不存在的非字符串路径按陈旧投影清理，字符串路径在状态目录之外的行保持原行为，源日志存在但不可读的会话仍保留上次投影。离线探针覆盖 BLOB 路径、外部字符串路径与正常会话：重开存储不再抛错，损坏行被清理，正常会话仍可列出与读取。不改变 RPC、协议或持久化格式。

- [Issue #1729](https://github.com/can4hou6joeng4/boss-harness/issues/1729)：`snapshot_projection()` 在计入回合字节预算时直接对 `turns.metadata_json` 调用 `.encode()`，早于 `_turn_metadata()` 的类型处理。该列虽声明为 TEXT，SQLite 非 STRICT 表允许存入 BLOB 或整数；一条被外部改写的投影行会让 `.encode()` 抛 `AttributeError: 'bytes' object has no attribute 'encode'`，而 `_with_repaired_index()` 只捕获 `_IndexedMetadataError`，异常逃逸到 RPC 层变成 `-32603`，`thread/resume snapshot=true` 的分页快照直接失败。现在读取投影列先校验类型，非字符串交给既有 `_IndexedMetadataError` → `_repair_thread_index` 重建路径；重建后快照正常返回，源日志不变。离线探针覆盖 BLOB 元数据：重开后快照返回正确会话与回合、`truncated` 为 `false`、投影列重建回字符串、源日志条目不变。不改变 RPC、协议或持久化格式。

- [Issue #1732](https://github.com/can4hou6joeng4/boss-harness/issues/1732)：`_restore_compaction_jobs()` 从事件索引恢复压缩任务时直接执行 `int(params.get("eventCursor", "0"))`。事件索引 `events.params_json` 是从 `events.jsonl` 派生的投影列，可被外部改写；`events.jsonl` 指纹未变时不会重建，`_event_page_entries()` 只校验 `params` 是对象，改写后的对象游标抛 `TypeError`，`ApplicationService.__init__` 失败，内核无法启动。该游标写入 `job["_eventCursor"]` 后在存入 `_compaction_jobs` 前就被 `pop`，没有任何读取方。现在移除这段未被读取的游标记账与该行的 `int()` 解析，恢复只依赖事件记录顺序；离线探针覆盖正常事件与改写为对象游标的投影，启动流程不抛错，任务仍按 `COMPACTION_INTERRUPTED` 恢复并广播失败终态。不改变 RPC、协议或持久化格式。

- [Issue #1735](https://github.com/can4hou6joeng4/boss-harness/issues/1735)：`WorkspaceInstructionsEditor`、`WorkspaceInstructionsSection` 与 `useAutoCompaction` 的读取 effect 在依赖变化时先执行清理（`active` / `cancelled` 失效），再在断连分支提前返回，跳过 `.finally` 的读取态复位。内核在读取回执返回前退出或断开后，编辑器页头持续显示「正在读取…」并隐藏已读路径与状态，上下文面板的「内核默认」也一直停在读取中，与断连提示矛盾，直到重连才恢复。现在三个提前返回分支先复位对应读取态再返回；断连期间显示未连接/尚未读取，重连后照常重新读取。`npm run typecheck`、`npm run build` 通过。不改变 RPC、协议或文案。

- [Issue #1738](https://github.com/can4hou6joeng4/boss-harness/issues/1738)：`_attachment_from_entries()` 用 `str(item.get("digest", ""))` 做 64 位十六进制校验，却把原始值继续传下去。持久记录里的 `digest` 是整数（`10**63` 的十进制正好 64 位并匹配正则）时，`_read_object()` 的 `self.root / digest` 抛 `TypeError`，`attachment/read`、分块读取与上下文注入都变成 `-32603`；`append_attachment()` 的同一 `str()` 校验也接受非字符串摘要。现在两处都要求摘要本身是字符串并匹配 64 位十六进制，读取侧对不属于会话的 id 与损坏摘要给出不同提示；离线探针覆盖整数摘要的三种读取路径均按「附件记录已损坏」拒绝，合法附件仍可添加、读取与注入。不改变 RPC、协议或持久化格式。
- [Issue #1740](https://github.com/can4hou6joeng4/boss-harness/issues/1740)：`AttachmentStore.add()` 在扩展名与路径检查后直接 `source.open("rb")`，没有普通文件校验，也没有把 `OSError` 映射成可读错误。与允许扩展名同名的目录让 `IsADirectoryError` 逃逸成 `-32603`；同名 FIFO 会让单线程 RPC 派发永久阻塞，整个内核无响应。现在用 `O_RDONLY | O_NONBLOCK | O_NOFOLLOW` 打开，按描述符 `fstat` 要求普通文件后再读取，打不开或类型不符统一按可读 `ValueError` 拒绝；离线探针覆盖目录、FIFO（10 秒保护，未阻塞）与缺失路径，普通 UTF-8 文本附件行为不变。不改变 RPC、协议或持久化格式。

- [Issue #1743](https://github.com/can4hou6joeng4/boss-harness/issues/1743)：技能扫描的 `_descriptor()` 直接以目录名作为 `id`，没有长度上限。201–255 字符的 ASCII 目录名可以包含合法 `SKILL.md` 并进入 `skills` 列表，而桌面 `skillDescriptorOf()` 与内核 `_existing_id()` 都把 id 限制为 200 字符：桌面会拒绝整份列表、技能页不可用，该技能也无法读取、改写或删除。现在 `scan()` 在读取正文前拒绝超过 200 字符的目录名，按未加载项上报（id 截断到 200、原因说明上限）；离线探针覆盖正常技能、恰好 200 字符与 201 字符目录，列表只含 ≤200 的 id，超长目录进入 problems，正常技能仍可读取。不改变 RPC、协议或持久化格式。

- [Issue #1746](https://github.com/can4hou6joeng4/boss-harness/issues/1746)：`SkillCatalog._candidate_paths()` 用 `is_dir()` 判断根目录并吞掉 `scandir` 的 `OSError`，权限不足、根路径被普通文件占位时返回空清单且不带任何 problems / truncated 标记，界面显示「当前工作区没有技能」，与真正的空工作区无法区分。现在缺失的根目录仍按首次使用返回空清单；`stat` 失败、存在但不是目录、`scandir` 报 `OSError` 时抛可读 `ValueError`，走既有读取失败路径，不新增 RPC 或协议字段。离线探针覆盖缺失根目录、普通文件占位、`chmod 000` 与恢复权限后的正常枚举与读取。不改变 RPC、协议或持久化格式。

- [Issue #1749](https://github.com/can4hou6joeng4/boss-harness/issues/1749)：`WorkspaceInstructions._candidate()` 先 `lstat` 再要求 `S_ISREG`，首选 `.boss-harness/CONTEXT.md` 存在但是符号链接、目录或父路径被普通文件占位时会静默跳过并回落到 `.boss-cli/CONTEXT.md`；legacy 也不存在时 `describe()` 返回 `None`、编辑器读取返回 `status: "empty"`，界面显示「空」而不是「不可读」，且写入端对同一符号链接会报错，两端口径不一致。现在 `lstat` 成功即固定该候选，由既有 `_read_regular` 读取路径按 `unreadable` 上报首选路径，提示块沿用既有「需为普通 UTF-8 文件且不是符号链接」文案；首选缺失时仍回落 legacy，两者都缺失时仍返回空。离线探针覆盖 legacy 回落、首选优先、符号链接、目录、父路径占位、legacy 符号链接与两者缺失共 19 项断言。不改变 RPC、协议或持久化格式。

- [Issue #1752](https://github.com/can4hou6joeng4/boss-harness/issues/1752)：`summaryJobsOf()` 逐项校验摘要任务形状与总数，却不检查 `jobId` 是否重复；`UsageDialog` 用 `jobId` 作为表格行 key，重复标识会让行错置或复用错误状态。现在与 `verifyUsageTurns()` 同一口径，页内重复 `jobId` 按「格式无法识别」拒绝，弹窗显示读取失败而不是重复行；跨页重复但页内唯一时仍正常展示与导出。离线探针用 esbuild 打包后执行 7 项断言。不改变 RPC、协议或持久化格式。

- [Issue #1755](https://github.com/can4hou6joeng4/boss-harness/issues/1755)：`WorkspaceSkills` 读取技能正文时只检查 `content` / `id` / `bytes` / `digest` 的 `typeof`，`NaN` 或负数字节数会显示成「NaN 字节」，非法 `limitBytes` 会显示成 `[object Object]`，错配 `id` 的快照只能靠展示层隐藏且没有读取失败提示。现在新增 `skillReadOf()`，复用 `skillDescriptorOf()` 校验基础字段，并要求正文是字符串、`limitBytes` 是安全正整数、`id` 等于请求的技能；`root` 合法时保留、非法时丢弃，未知字段不进入规范化结果。不合格回执显示「内核返回的技能正文无法识别」。离线探针 15 项断言覆盖合法回执、`NaN` / 负数 / 零 / 字符串上限、对象正文、错配 id、空摘要、空与数组回执。不改变 RPC、协议或持久化格式。

- [Issue #1758](https://github.com/can4hou6joeng4/boss-harness/issues/1758)：`CreateSkillDialog` 与 `EditSkillDialog` 对写操作回执只检查 `id` / `name` / `bytes` 的 `typeof`，错配 `id` 会提示「已创建 / 已保存技能 <错误 id>」，`NaN` 字节数或缺失摘要的回执也被当成成功。现在两个对话框都复用 `skillDescriptorOf()` 校验完整形状，并要求回执 `id` 等于提交的技能 id，否则提示「无法识别」并建议刷新目录。类型检查与构建通过。不改变 RPC、协议或持久化格式。

- [Issue #1765](https://github.com/can4hou6joeng4/boss-harness/issues/1765)：内核 `pyproject.toml` 只有名称、版本、描述与依赖，缺少 `readme`、`keywords`、`classifiers` 与项目链接，`harness/` 也没有 README；构建出的 wheel / sdist 元数据里没有仓库、Issue 与变更记录入口，若发布到包索引，项目页缺少介绍正文。现在新增 `harness/README.md` 作为包描述，补齐四个 `Project-URL`、关键词与八个分类器；本地构建核对 wheel `METADATA` 含四条链接、`Keywords`、`Classifier` 与 Markdown 正文，sdist 含 `README.md`、`LICENSE` 与 `pyproject.toml`，双产物隔离安装后 `--check --provider none` 均 5 项通过。不改变 RPC、协议或持久化格式。

- [Issue #1768](https://github.com/can4hou6joeng4/boss-harness/issues/1768)：`useSessionReasoning.load()` 读取 `thread/reasoning/read` 时只校验 `threadId`、`availableEfforts` 与 `effort`，`supported` / `summaryActive` / `model` / `configuredEffort` / `capabilitySource` / `capabilityIsEstimate` 直接写入会话状态；`supported` 为真值字符串时模型菜单把有效档位标成「不在当前模型支持列表中」，`summaryActive` 为真值字符串时摘要占用判定持续成立、每秒重读同一响应。现在新增 `reasoningReadOf()` 按协议校验全部字段并要求会话归属，未知字段丢弃；`load()` 无法识别时沿用「无法读取会话推理设置」提示且不写状态。离线探针 19 项断言，类型检查与构建通过。不改变 RPC、协议或持久化格式。

- [Issue #1771](https://github.com/can4hou6joeng4/boss-harness/issues/1771)：`useSessionBranches` 的 `isBranchJob()` 只检查 `kind`、`threadId`、`jobId` 与 `status`，同一任务通道的 `contextJobOf()` 已逐项校验展示字段但分支路径没有复用；对象类型的 `totalCharacters` / `modelRequestCount` 会让提示卡显示 `[object Object]`，`code` / `message` 非字符串时失败说明失真，`abandonedTurnIds` 含非字符串仍进入状态。现在新增 `branchJobOf()` 复用完整校验并要求会话归属，畸形载荷按「不适用」丢弃且不中断通知回调；通知、读取、轮询、切换与取消五处统一使用。离线探针 16 项断言，类型检查与构建通过。不改变 RPC、协议或持久化格式。

- [Issue #1774](https://github.com/can4hou6joeng4/boss-harness/issues/1774)：`WorkspaceInstructionsEditor` 保存工作区说明后完全忽略 `context/instructions/write` 回执，用本地 payload 与读取时的首选路径合成状态并提示「已保存 N 字节，下一回合生效」；正文的空白判定与内核不一致时会给出相反的注入提示，真实路径、字节数与上限也不会进入界面。现在新增 `workspaceInstructionWriteOf()` 校验收据（状态仅 `loaded` / `empty`、字节数非负、上限为正、路径非空且不超过 4096 字符），保存成功后按回执更新路径、状态与字节数并提示真实结果；回执无法识别时提示重新读取确认且不把草稿标记为已保存。离线探针 21 项断言，类型检查与构建通过。不改变 RPC、协议或持久化格式。

- [Issue #1777](https://github.com/can4hou6joeng4/boss-harness/issues/1777)：`HarnessHostConnection.#expireFinishedApprovals()` 用 `String(params.status)` 判断回合终态，数组等非字符串值会被转成合法状态（`String(["completed"]) === "completed"`），畸形 `thread/updated` 通知会提前撤销挂起的审批：host 对服务端审批请求回 `-32001` 并从路由表删除，界面审批卡仍显示等待，用户随后点「批准」得到「approval is no longer pending」，招聘动作无法执行。现在只有 `status` 本身是字符串且属于 `completed` / `interrupted` / `blocked` / `error` 时才按回合终态撤销；`completedItem` 的 `itemId` 严格相等判断不变。离线探针（host + 假内核）覆盖数组、对象、数字与数组四种畸形状态后审批仍可批准、拒绝正常送达、合法终态仍撤销，11 项断言，类型检查与构建通过。不改变 RPC、协议或持久化格式。

- [Issue #1780](https://github.com/can4hou6joeng4/boss-harness/issues/1780)：`reduceHarnessEvent()` 直接把 `params.itemId` / `params.approvalId` 当卡片标识，没有类型校验。`itemId` 是对象时 `findIndex` 用引用比较永远匹配不到已有卡片，同一工具调用的每条通知都会追加新条目；列表 key 退化成 `[object Object]`，React 报重复 key 并复用错误卡片；对象 `approvalId` 经模板字符串后，不同审批共用同一张 `approval-[object Object]` 卡。现在只接受非空字符串标识，没有合法标识的事件按「无法定位」忽略，`approval/requested` 写入卡片的是校验后的 `approvalId`；与同文件 `toMessage()` 对快照条目的既有处理一致。离线探针 11 项断言，类型检查与构建通过。不改变 RPC、协议或持久化格式。

- [Issue #1783](https://github.com/can4hou6joeng4/boss-harness/issues/1783)：渲染层三处把事件 / 快照 / 回执里的回合标识直接写进 `turnIds`（`turn/started`、`thread/resume` 快照的 `activeTurnId`、续接回执的 `turnId`），都只做真值判断；`reduceHarnessEvent()` 也把 `params.turnId` 直接写进新建卡片。对象等畸形值写入后，事件归属守卫 `turnIds.current.get(id) !== params.turnId` 对每个正常字符串 `turnId` 都为真，整回合除 userMessage 外的事件被静默丢弃，界面停在「运行中」而聊天区不再更新；同一坏值还会被当作 `expectedTurnId` 发给停止 / 转向，对象 `turnId` 进入卡片后分支入口渲染成 `[object Object]` 并把对象当作目标回合发给内核、用量弹窗把对象当成回合键。现在新增 `turnIdOf()`，三处入口与事件投影只接受非空字符串，畸形快照 `activeTurnId` 按缺失处理、不误标运行中，续接回执的对象 `turnId` 按「回执与请求不一致」进入既有核对路径。修复前探针 2 项断言复现缺陷，修复后 18 项断言通过，类型检查与构建通过。不改变 RPC、协议或持久化格式。

- [Issue #1786](https://github.com/can4hou6joeng4/boss-harness/issues/1786)：`SnapshotStore.page()` 把冻结快照 `edits` 表的 `entry_id` / `excluded` 原样拼进响应，没有类型校验。快照库属于持久数据，可能被外部改写或损坏，SQLite 的列亲和性也不阻止写入 BLOB。`entry_id` 被改写为 BLOB 时 `contextEdit.entryId` 变成 `bytes`，`wire_size()` 只捕获 `UnicodeEncodeError`，`json.dumps(bytes)` 的 `TypeError` 逃逸成 `-32603`，`thread/items/list` 整页读取失败；`excluded` 被改写为文本时 `bool("0")` 为真，条目被误标成已从上下文排除。现在 `page()` 只在 `entry_id` 是非空字符串且 `excluded` 是 0 / 1 时返回编辑状态，损坏行按「没有编辑状态」处理，条目照常返回；`edit_state()` 使用同一契约。离线探针构建含上下文编辑记录的真实快照库并篡改编辑列，7 项断言通过（修复前 BLOB 标识断言失败），`py_compile` 通过。不改变 RPC、协议或持久化格式。

- [Issue #1789](https://github.com/can4hou6joeng4/boss-harness/issues/1789)：`thread/export` 的预算计算（`_wire_bytes()`）、返回字节数和 `content` 校验都直接调用 `str.encode("utf-8")`。会话日志由 `json.loads` 解码，JSON 转义序列 `\ud800` 会产生孤立 Unicode 代理项字符串；被外部改写或由旧版本写入的记录含这类值时，任何一处编码都会抛 `UnicodeEncodeError`，导出请求整体返回 `-32603`，用户拿不到文档，也无法从界面判断是哪条记录损坏。即使绕过字节计算，含代理项的 `content` 按 `ensure_ascii=False` 编码响应帧同样失败。这与 `item_content.wire_text` 的既有约定不一致：条目投影与工具结果读取都把代理项降级为 U+FFFD，只有导出路径漏掉。现在 `_wire_bytes()` 与 `export_thread()` 返回前统一经过 `wire_text()`，markdown / json / html 三种格式下畸形文本按 U+FFFD 降级、`bytes` 与 `content.encode("utf-8")` 一致；正常文本逐字节不变。离线探针 10 项断言通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。

- [Issue #1792](https://github.com/can4hou6joeng4/boss-harness/issues/1792)：会话索引 `state.sqlite3` 与冻结快照库的 TEXT 列由 Python `sqlite3` 默认严格解码，列里只要有一个非法 UTF-8 字节（外部改写或磁盘损坏）就抛 `sqlite3.OperationalError: Could not decode to UTF-8 column`。该异常不是 `ValueError`，因此绕过既有的损坏处理：`threads.rollout_path` 损坏时 `SessionStore.__init__` 的 `_refresh_threads()` 查询即失败，内核无法启动；`threads.metadata_json` 损坏时 `thread/list` 在 `fetchall()` 抛错，`_with_repaired_index()` 只捕获 `_IndexedMetadataError`，本应触发的重建路径永远到不了，请求返回 `-32603`；冻结快照的 `page()` / `item()` / `queue()` 同样在解码阶段失败，绕过 `_decode_item()` 与 `queue_record()` 的「会话快照已损坏」处理。现在 `PersistenceIndex.connection()` 与快照读取连接使用宽容 `text_factory`，非法 UTF-8 按 U+FFFD 解码：损坏的 `metadata_json` 进入既有重建路径，损坏条目仍抛可读的「会话快照已损坏」，队列投影继续跳过损坏记录，合法文本行为不变。离线探针 5 项断言通过（修复前启动与列表路径均复现 `sqlite3.OperationalError`），既有快照编辑与导出探针回归通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。

- [Issue #1795](https://github.com/can4hou6joeng4/boss-harness/issues/1795)：会话没有 `leaf` 记录时（从未切换分支）`_active_entries()` 不拒绝重复条目 id。同一 id 同时出现在普通 `item` 与 `branch_summary` 记录上时，`context/read` 的 `branchSummaries` 按 `branch_summary` 记录列出该 `entryId`，而 `thread/branchSummary/read` 却按 id 在线性扫描里取第一条同 id 记录（普通 `item`），随后 `payload["summary"]` 抛 `KeyError`（非字符串 `summary` 时为 `AttributeError`），`rpc.py` 将两者映射为 `-32603`，回执正文只有 `"summary"`；同一份数据在 `context/read` 能列出、点开却是内部错误。现在 `_branch_summary_scan()` 在结果中携带通过 `branch_summary_issue` 校验的 `payload` 与记录时间，读取接口直接使用该记录，不再二次按 id 定位；id 只存在于普通条目时仍返回既有 `-32011 BRANCH_SUMMARY_NOT_FOUND`，`context/read` 投影仍只含既有六个字段。离线端到端探针 10 项断言通过（修复前 `thread/branchSummary/read` 返回 `{"code": -32603, "message": "'summary'"}`），既有会话扫描、导出编码、快照编辑与索引库解码探针回归通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。

- [Issue #1798](https://github.com/can4hou6joeng4/boss-harness/issues/1798)：`events` 是 `events.jsonl` 的派生索引，`events_after()` 在 `size:mtime_ns` 指纹一致时不重建；而 `_event_page_entries()` 只校验 `params_json` 能解析且为对象。某行被外部改写为不含 `eventCursor` 的合法对象时该行仍通过校验，`event/list` 读取 `event["params"]["eventCursor"]` 抛 `KeyError('eventCursor')`，回执 `-32603`，已有的「索引损坏 → 重建 → 重试一次」路径永远不可达。现在 `_event_page_entries()` 要求 `params_json` 的 `eventCursor` 与该行 `cursor` 列一致，缺失或被改写时按索引损坏抛 `ValueError`，由 `events_after()` 重建后使用日志中的事件；正常行行为不变。离线端到端探针 5 项断言通过（修复前 `event/list` 返回 `{"code": -32603, "message": "'eventCursor'"}`），分支摘要、导出编码、快照编辑、索引库解码与会话扫描探针回归通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。

- [Issue #1801](https://github.com/can4hou6joeng4/boss-harness/issues/1801)：`turns` 是会话日志的派生投影，SQLite 的列亲和性不会阻止外部把 `first_ordinal` 改写成文本。`list_branch_turns()` 用它和分页游标的整数比较 `(row["first_ordinal"], row["turn_id"]) <= (key[0], key[1])`，抛 `TypeError('<=... 'str' and 'int')`；该比较位于 `_with_repaired_index()` 内，但只有 `_IndexedMetadataError` 会触发重建，`TypeError` 直接冒泡成 `-32603`，`thread/turns/list` 的分支视图整页失败，重建路径不可达。现在读取投影行后先要求 `first_ordinal` 为整数、`turn_id` 为文本，不一致按索引损坏抛内部信号，由既有重建路径从会话日志恢复行类型后重试；类型校验放在成员判断之前，非文本 `turn_id` 不会让回合从分页里静默消失。离线端到端探针 5 项断言通过（修复前带游标请求返回 `{"code": -32603, "message": "'<=' not supported between instances of 'str' and 'int'"}`），分支摘要、事件索引、导出编码、快照编辑、索引库解码、只读 RPC 畸形数据扫描与会话扫描探针回归通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。

- [Issue #1804](https://github.com/can4hou6joeng4/boss-harness/issues/1804)：`resolve_request()` 用原始持久 payload 建立队列身份映射，只要求 `id` 是字符串；而 `queue_record()` 要求 `id/kind/status/input` 全部合法，`queue/list` 与快照会过滤掉残缺记录。一条缺 `status` 的队列记录在界面上不可见、无法核对或删除，但命中身份后 `queue/add` 读取 `item["status"]` 抛 `KeyError('status')`，`turn/start` 在读取 `current["status"]` 时同样失败，均返回 `-32603`，该 `clientUserMessageId` 的提交被永久阻断。现在身份映射复用 `queue_record()` 的同一结构契约，缺失或非法记录按缺失处理，与列表、计数和快照保持一致；正常记录的匹配、幂等与冲突判定不变。离线端到端探针 6 项断言通过（修复前 `queue/add` 与 `turn/start` 均返回 `{"code": -32603, "message": "'status'"}`），既有探针全部回归通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。

- [Issue #1807](https://github.com/can4hou6joeng4/boss-harness/issues/1807)：`_restore_compaction_jobs()` 只校验事件参数里的 `jobId` 与 `threadId`，随后把整份参数注册为摘要任务。缺 `throughTurnId`/`sourceDigest` 的 `context/compactionStarted` 会让恢复阶段的 `_compaction_public()` 抛 `KeyError`，内核在 `ApplicationService.__init__` 直接退出、无法启动；残缺的终态记录则让 `context/compact/read|abort` 在读取 `status`/`throughTurnId` 时抛 `KeyError`，返回 `-32603`。事件是派生数据，现在恢复前按读取契约校验：启动/进度事件的状态必须是 `running`，终态事件必须是终态枚举，`throughTurnId` 必须存在且为 `null` 或字符串，`sourceDigest` 必须是 64 位小写十六进制；不满足的记录按缺失处理跳过，正常载荷与恢复行为不变。离线端到端探针 6 项断言通过（修复前内核启动即退出并报 `KeyError: 'throughTurnId'`），队列状态、分支回合顺序列、分支摘要、事件索引、导出编码、快照编辑、索引库解码、只读 RPC 扫描与会话扫描探针回归通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。
- [Issue #1810](https://github.com/can4hou6joeng4/boss-harness/issues/1810)：`context/edit` 允许把被工具批次引用的助手消息排除（`replacementText` 为 `null`），而 `_history_projection()` 按排除语义移除该助手条目后，引用它的工具调用项仍保留；`messages_from_items()` 恢复批次时找不到所属助手，抛 `ValueError("Tool batch assistant item is missing or inconsistent")`，`context/read` 与之后每个回合的模型请求都永久失败，用户也无法从排除状态恢复。现在 `context_edit_read()` 把被 `toolBatchAssistantItemId` 引用的助手条目与 Anthropic 续接条目一样标为不可编辑并说明原因，提交路径因既有 `canEdit` 检查同步拒绝；新增 `_visible_items()` 统一投影可见条目口径——排除仍生效（正文不再进入请求），但被工具批次或续接引用的助手条目保留在投影里供批次恢复，旧版本写入的同类排除记录改按「无文本的助手工具调用 + 工具结果」投影，不再让会话失败。压缩计划的保留/选中与分支摘要分段共用同一口径。离线端到端探针 8 项断言通过（修复前 `context/read` 返回 `-32602` 且排除提交成功），压缩恢复、队列状态、分支回合顺序列、分支摘要重复 id、事件索引、导出编码、快照编辑、索引库解码、只读 RPC 扫描与会话扫描探针回归通过，`py_compile` 通过。不改变 RPC、协议或持久化格式。
- [Issue #1813](https://github.com/can4hou6joeng4/boss-harness/issues/1813)：候选版本沿用小版本号迭代，但 README 的版本与交付状态表没有说明预发布序号不设位数上限，读者容易误以为序号到 `rc.99` 封顶。现在补充候选序号规则：`0.2.0-rc.101`（npm）与 `0.2.0rc101`（Python）同样有效，跨过两位后继续按同一规则递增；`scripts/release_assets.py` 的版本校验正则与桌面版本展示都按不透明字符串处理，不需要改动。不改变版本号、发布脚本或运行时行为。
- [Issue #1815](https://github.com/can4hou6joeng4/boss-harness/issues/1815)：进程中断后由启动恢复结算的 `toolCall`，以及恢复会话里被拒绝或审批失效的 `toolCall`，持久记录只有 `resultSummary` 与 `errorCode`、没有 `result`。`model_result_for_item()` 对这些记录调用 `model_result_content({})`，空对象在预算内直接早返回 `"{}"`，摘要被丢弃，模型只看到空结果，无法区分「未执行」「被拒绝」「结果不确定」，可能把写操作当成空结果重试。现在新增 `_unavailable_result()`，输出 `resultUnavailable: true`、`errorCode` 与 `resultPreview`（持久摘要），受同一 `modelResultLimitBytes` 预算约束，摘要超限时减半截断；有 `result` 的记录与既有 `modelResult` 快速路径不变。离线探针 10 项断言通过（修复前返回 `"{}"`），全部回归探针与 `py_compile` 通过。不改变持久化格式、RPC 或协议。
- [Issue #1817](https://github.com/can4hou6joeng4/boss-harness/issues/1817)：持久 `toolCall` 的 `toolArguments`、`result` 或审批参数含约 990 层以上嵌套时，条目投影 `wire_value()` 与导出清理 `_scrub_json()` 的纯 Python 递归抛 `RecursionError`，被映射为 `-32603`：`thread/read`、`thread/items/list`、`context/read` 与 `thread/export includeToolResults=true` 全部失败，重建内核后依旧；正常来源是模型输出——参数解析的 `json.loads` 没有深度上限，schema 校验判定 `INVALID_PARAM` 后原始参数仍写入记录。现在投影与导出按 64 层上限（与工具参数 schema 的 `_MAX_JSON_DEPTH` 一致）把超深子树截断为占位文本，正常数据逐值不变；校验失败的模型参数在落库前按同一上限净化，正常路径不再产生无法投影的记录。离线探针 7 项断言通过（修复前 1200 层输入直接 `RecursionError`），全部回归探针与 `py_compile` 通过。不改变持久化格式、RPC 或协议。
- [Issue #1819](https://github.com/can4hou6joeng4/boss-harness/issues/1819)：`compacted_request()` 用 `selected` 里 item 的 `turnId` 过滤分支摘要；空回合（续接或准入失败留下的零条目回合）没有任何 item，锚定在它上面的摘要被整体丢弃，而常规历史投影仍会在之后第一个可见回合前注入该摘要，前缀比对恒失败，自动压缩每次都抛「模型请求前缀与压缩来源不一致」，无法再压缩历史。现在摘要覆盖范围按回合顺序计算（`turns[:through_index + 1]`），空回合同样计入；找不到目标回合位置时回退到原有 item 口径。离线探针 4 项断言通过（修复前前缀比对失败），全部回归探针与 `py_compile` 通过。不改变压缩计划、持久化格式、RPC 或协议。
- [Issue #1822](https://github.com/can4hou6joeng4/boss-harness/issues/1822)：`HarnessHostConnection` 在通知分发里看到 `method === "harness/disconnected"` 就直接进入断开路径（`#disconnected` → `#retire` → `HarnessClient.dispose()`），不核对来源。内核（Python 侧）从不发送这个通知，真实断开只由 `HarnessClient.#fail` 在进程退出、输入输出管道关闭、帧超限或 dispose 时合成（先置失败再发帧）。一帧内核同名通知（误发或外部注入）会让宿主销毁仍在工作的进程（stdin.end → 2.5 秒 SIGTERM → 1 秒 SIGKILL）、清空审批路由、丢掉运行中回合并自动重连；修复前探针还观测到后续请求报 `harness client disposed`。现在只有已失败客户端（`connection.exited`）合成的断开帧才进入 `#disconnected`，其余同名通知丢弃。离线探针 8 项断言通过（伪造通知后宿主保持 `ready`、generation 不变、内核继续服务请求；真实退出仍报告断开）。不改变 RPC、协议或持久化格式。
- [Issue #1824](https://github.com/can4hou6joeng4/boss-harness/issues/1824)：初始化回执只校验 `serverName` 与 `protocolVersion`，`approval.timeoutSeconds` 未校验就参与审批截止时间计算。字符串、NaN、负数或其它非正有限数让 deadline 变成 NaN 或过去时间，宿主立即回 `-32001 Approval expired`，审批从未展示给用户，审批型工具被内核记为未执行；`??` 只兜底 `null`/`undefined`，对错误类型无效。现在只接受正有限数，其余按默认 300 秒处理，缺失与合法值行为不变。离线探针 8 项断言通过（畸形值下宿主仍发出 `approval/requested`、接受用户批准、内核收到 `{approved:true}`）；修复前探针无审批通知且回包为 `-32001`。不改变 RPC、协议或持久化格式。
- [Issue #1826](https://github.com/can4hou6joeng4/boss-harness/issues/1826)：`HarnessClient.#onLine` 的两处错误回包（无监听器回 `-32601`、监听器抛错回 `-32603`）直接调用 `respondError`。内核帧的 id 没有长度上限，回包原样带回同一 id，可能超过 `maxFrameBytes` 让 `#enqueue` 抛 `harness frame exceeds byte limit`；异常从 `child.stdout` 的 `data` 回调逃逸，Node 按未捕获异常终止 Electron 主进程。现在新增 `#rejectServerRequest`，错误回包失败只记录诊断 `failed to answer server request`，不再向上抛。离线探针在 `maxFrameBytes=512`、450 字符 id 下覆盖两个分支（修复前直接崩溃），回包超限后连接仍可服务请求。不改变 RPC、协议或持久化格式。
- [Issue #1828](https://github.com/can4hou6joeng4/boss-harness/issues/1828)：`PlatformLogin.open()` 遇到进行中状态（`opening`/`waiting`/`saving`）但缺少 `id` 的登录回执时，先把状态写入状态机再关闭浏览器，状态仍停在 waiting/saving；此后 `open()` 因父窗口已为空抛 `another thread owns this login`，`control(cancel)` 因 parent 不匹配被忽略，扫码登录永久不可用，只能重启应用。现在缺 id 的进行中回执按 `LOGIN_OPEN_FAILED` 失败结束，占用判定只在仍持有父窗口时生效，覆盖其它异常路径留下的残留状态。离线探针（electron 桩）8 项断言通过（修复前第一次 `open()` 停在 `waiting`、第二次抛占用）。不改变 RPC、协议或持久化格式。
- [Issue #1830](https://github.com/can4hou6joeng4/boss-harness/issues/1830)：主进程只用一个通知流接收宿主事件与内核通知，`forgetTurnsOnDisconnect` 与 `withStartupDiagnosis` 对任何 `harness/connectionStatus` 生效。内核从不发送该通知，一帧伪造的非 ready 状态就会清空 `turnStartedAt`（运行中回合的退出确认失效）、触发启动自检并原样转发给窗口显示已断开。现在 `HarnessHostConnection` 新增 `onStatus` 专用通道（`#broadcastStatus` 同时投递给普通监听者以保持兼容），主进程的连接状态处理只订阅该通道，普通流中的内核同名帧丢弃。离线探针 8 项断言通过（伪造帧不进入状态通道、宿主保持 `ready`、真实退出仍报告 `disconnected`）。不改变 RPC、协议或持久化格式。
- [Issue #1832](https://github.com/can4hou6joeng4/boss-harness/issues/1832)：持久条目编号重复时，`_project_items` 与 `_item_owners` 都按 id 建索引。同回合重复让 `_apply_context_edits` 一次编辑同时改写用户消息与助手消息（`context_edit_read` 只展示第一条），注入伪造的助手回复；跨回合重复让 `_item_owners` 后者覆盖前者，`_compaction_items` 的归属检查恒抛「回合条目的来源归属不一致」，`context/read`、`context/history` 与之后每个回合的历史构建永久失败。现在两处一致保留先出现的记录：投影跳过后续同编号实体条目，归属只记录第一次的值。离线探针 8 项断言通过（修复前 3 项失败），14 个回归探针与 `py_compile` 通过。不改变 RPC、协议或持久化格式。
- [Issue #1835](https://github.com/can4hou6joeng4/boss-harness/issues/1835)：`_restore_partial_streams` 回放 `agentMessage/delta` 与 `agentThinking/delta` 时不校验增量字段。事件日志可被外部改写：`itemId` 是数组（不可哈希）、`delta` 不是文本时抛 `TypeError`，从 `ApplicationService.__init__` 逃逸，内核每次启动都退出。现在损坏增量跳过，其余增量与其他会话照常恢复。离线探针 2 项断言通过，回归探针与 `py_compile` 通过。不改变 RPC、协议或持久化格式。
- [Issue #1837](https://github.com/can4hou6joeng4/boss-harness/issues/1837)：`queue_view_record` 此前只删除已知的畸形可选字段，未知字段原样保留。一条带 1MB 未知字段的暂停记录让 `queue/list`、`thread/read` 与 `thread/resume` 的投影超过响应预算，整次读取返回 -32010 且无法通过取消恢复。现在只读投影按协议字段白名单构造，可选字符串与技能标识限制长度，合法字段（`pausedReason`、`skillIds`、`autoCompaction`）仍原样保留。离线探针 13 项断言通过。不改变 RPC、协议或持久化格式。
- [Issue #1839](https://github.com/can4hou6joeng4/boss-harness/issues/1839)：`JsonRpcServer._dispatch` 的 `params` 非对象 -32602 回包位于 handler 捕获范围之外。请求 id 本身接近帧上限时错误帧同样超限，`FrameTooLargeError` 从 `serve_forever` 逃逸，内核因一帧坏请求直接退出。现在回退为不带 id 的协议错误，与 `_respond_too_large` 的既有处理一致。离线探针 6 项断言通过。不改变 RPC、协议或持久化格式。
- [Issue #1841](https://github.com/can4hou6joeng4/boss-harness/issues/1841)：宿主审批路由对回执中的 `deadline` 直接 `Date.parse` 或乘法换算。无法解析的时间串与非有限数字让截止时间变成 NaN 或过去时间，审批被静默回成 -32001，内核把工具记为未执行。现在畸形值按缺失处理，退回初始化回执的默认期限；明确的过去时间仍按过期处理。离线探针 5 项断言通过。只改 app-client，不改变 RPC、协议或版本号。
- [Issue #1843](https://github.com/can4hou6joeng4/boss-harness/issues/1843)：`#expireFinishedApprovals` 对 `item/completed` 只比较 `itemId`，另一个会话的同名条目会撤销本会话仍在等待的审批，内核随后收到 -32001，用户从未做决定。现在条目与回合一样按会话作用域撤销，旧内核不带 `threadId` 时保持原匹配。离线探针 5 项断言通过。只改 app-client，不改变 RPC、协议或版本号。
- [Issue #1845](https://github.com/can4hou6joeng4/boss-harness/issues/1845)：`queue/get`、`queue/update`、`queue/remove` 与 `queue/add`、`turn/steer` 的幂等命中路径返回运行时完整记录，未经过 `queue_view_record`。外部改写留下的畸形可选字段（`skillIds` 非数组、`turnId` 非字符串、未知字段等）让桌面 `isQueueItem` 整份拒绝，用户无法读取、编辑或撤回该条消息。现在五处回执共用只读投影，完整正文不截断。离线探针 11 项断言通过。不改变 RPC、协议或持久化格式。
- [Issue #1847](https://github.com/can4hou6joeng4/boss-harness/issues/1847)：`thread/read`、`thread/items/list` 与快照构建无条件使用严格契约读取 `context_edit` 条目。一条带多余键、目标不存在或替换文本超限的编辑记录让这些展示路径整段返回 -32602，用户无法查看历史或分页读取快照。现在展示投影逐条跳过损坏记录并按原文显示，快照构建同样跳过；模型上下文路径（`_apply_context_edits`、`context_edit_read`）保持严格拒绝。离线探针 17 项断言通过。不改变 RPC、协议或持久化格式。
- [Issue #1849](https://github.com/can4hou6joeng4/boss-harness/issues/1849)：`SessionStore._active_entries` 遇到损坏的 leaf 记录（`targetId` 非字符串、指向未知条目或非 turn 条目）直接抛错，`thread/read`（`view=branch`）、`thread/items/list`、`thread/branches/list`、`thread/export`、`context/read`、`thread/fork` 与所有模型回合一起返回 -32602。现在损坏指针按缺失处理，继续使用上一个有效叶；合法叶切换与被放弃分支排除语义不变。离线探针 28 项断言通过。不改变 RPC、协议或持久化格式。
- [Issue #1851](https://github.com/can4hou6joeng4/boss-harness/issues/1851)：`pending_approvals` 原样返回索引列。外部改写把 `approvals.deadline` 变成 BLOB 时 JSON 序列化抛 `TypeError`，`approval/list` 返回 -32603 与 `RESPONSE_INVALID`；持久计数仍统计该行，界面出现「有 1 个待审批但列表为空」。现在共享过滤条件加入 `typeof` 守卫，投影逐行校验字符串列与有限数字，列表与计数一致跳过损坏行。离线探针 8 项断言通过。不改变 RPC、协议或持久化格式。
- [Issue #1853](https://github.com/can4hou6joeng4/boss-harness/issues/1853)：`HarnessClient.#onLine` 对三种畸形响应（`result` 与 `error` 同时存在、都缺失、`error` 形状非法）直接丢弃，不删除 pending 项也不清除定时器。请求空等到 30 秒超时才以「outcome unknown」失败，调用方无法区分内核崩溃与坏帧。现在已存在的请求立即以 `HarnessRpcError`（-32603）结算。离线探针 10 项断言通过。只改 app-client，不改变 RPC、协议或版本号。
- [Issue #1855](https://github.com/can4hou6joeng4/boss-harness/issues/1855)：手动压缩开始请求回执未知时面板保留 `unknownStart`；内核重启后 `context/read` 明确返回无任务记录，refresh 只设置 `discoveryStopped` 并保留该状态。轮询随即停止，计划与开始按钮被永久禁用，用户没有恢复入口。现在明确无任务时清除未知开始状态并允许重新生成计划；本地仍有运行中的摘要任务时继续按不可用处理。离线探针 14 项断言通过。只改渲染层，不改变 RPC、协议或版本号。

## 0.2.0-rc.55 - 2026-11-16

本节汇总第五十五个候选版本的源码与交付内容；rc.16 至 rc.55 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.54，本次包含 5 项修复：运行资源计数与截断推导（#1571、#1572）；驾驶舱队列摘要采用持久分类计数（#1575、#1576）；摘要任务明细截断与计数一致性（#1577、#1578）；重连后的尾随刷新归属（#1579、#1580）；拒绝成环的分页游标（#1581、#1582）。同时把根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本同步为 npm `0.2.0-rc.55` / Python `0.2.0rc55`（#1583）。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

升级注意：不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.54 源码无需迁移。rc.54 已准备的 5 项交付与更早候选内容继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。

### 变更

- [Issue #1583](https://github.com/can4hou6joeng4/boss-harness/issues/1583)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.55` / Python `0.2.0rc55`；将 rc.54 之后 5 项修复归入本候选，同步 README 近期进展与版本表、使用指南的候选状态、技术参考中的候选引用与 Issue 表单示例版本。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1571](https://github.com/can4hou6joeng4/boss-harness/issues/1571)：`runtime/resources/read` 的渲染层读取器此前只按 `ownersTruncated` / `waitersTruncated` 判断截断，计数大于已返回明细但标记缺失或误报 `false` 时，驾驶舱会显示「运行中 owner 5」却只列出 1 行且没有「可见 N」提示；计数小于明细时标题数字还会比实际行数少。现在计数大于明细即按截断处理，计数小于明细视为矛盾响应整体报错；完整快照与显式截断行为不变。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1575](https://github.com/can4hou6joeng4/boss-harness/issues/1575)：驾驶舱的队列摘要此前只按已载入条目重算分类，忽略 `queue/list` 已返回的持久分类计数；队列超过投影上限时，暂停项会被低估，分类合计与待处理总数矛盾，也与队列面板、侧栏徽标使用的数字不一致。现在摘要优先采用与待处理总数对齐的持久分类，旧内核缺省分类或分类合计不一致时才退回按可见项统计并保留「分类按可见项计数」提示。只改渲染层与文档，不改变 RPC、协议或版本号。
- [Issue #1577](https://github.com/can4hou6joeng4/boss-harness/issues/1577)：会话用量面板与 CSV 的「摘要任务明细」此前直接信任内核截断标记，并静默执行 50 条本地展示上限；计数大于已返回明细而标记缺失或误报 `false` 时，标题仍显示完整总数却没有「仅显示最近 N 个」，用户会把部分明细当成全部，计数小于明细时也不拒绝。现在计数小于已接收明细视为矛盾响应整体报错，计数大于已展示明细（含本地上限）时强制标记截断，旧内核缺省计数按已接收明细数作为总数。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1579](https://github.com/can4hou6joeng4/boss-harness/issues/1579)：上下文面板的读取航班收尾此前只对 `readFlights` 做归属检查，却无条件删除 `refreshAgain` 尾随刷新标记；断连清空两个注册表后，旧连接发起的读取若在新连接的新读取进行期间才落地，会吞掉新读取登记的刷新请求，重连后面板可能持续显示变化前的预算 / 摘要任务状态，直到下一个事件或手动刷新。现在只有仍持有该会话读取槽位的航班才能清理槽位并消费刷新标记，旧 epoch 的迟到读取不再影响新连接的补读。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1581](https://github.com/can4hou6joeng4/boss-harness/issues/1581)：渲染层的公共分页、会话条目恢复、事件重放与回合技能分页此前只拒绝「游标原地不动」，返回 `A → B → A` 的环状游标时每一步都与上一页不同，检查全部通过，界面会重复拼接已读过的页：侧栏会话、分支端点与会话用量出现重复行，会话恢复还会反复请求同一批页直到页数上限，事件重放会重复应用同一批事件。现在单轮分页登记所有已使用的游标，下一个游标与任一已见游标相同即整体失败；合法单向翻页与正常结束行为不变。只改渲染层，不改变 RPC、协议或版本号。

## 0.2.0-rc.54 - 2026-11-16

本节汇总第五十四个候选版本的源码与交付内容；rc.16 至 rc.54 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.53，本次包含 5 项交付：恢复快照队列元数据与列表共用校验（#1559、#1560）；截断投影不误判未载入项（#1561、#1562）；缺标识审批不可提交（#1563、#1564）；会话队列分类计数统一校验（#1565、#1566）；技术参考与使用指南补记边界（#1567、#1568）。同时把根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本同步为 npm `0.2.0-rc.54` / Python `0.2.0rc54`（#1569）。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

升级注意：不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.53 源码无需迁移。rc.53 已准备的 5 项交付与更早候选内容继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。

### 变更

- [Issue #1569](https://github.com/can4hou6joeng4/boss-harness/issues/1569)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.54` / Python `0.2.0rc54`；将 rc.53 之后 5 项交付归入本候选，同步 README 近期进展与版本表、使用指南的候选状态、技术参考中的候选引用与 Issue 表单示例版本。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1559](https://github.com/can4hou6joeng4/boss-harness/issues/1559)：`thread/resume` 快照此前只按 `typeof === "number"` 接收队列元数据，`NaN`、负数、小数或 `activeItems > totalItems` 会写进 `queueCache` 与队列面板，界面出现「共 NaN 项」「-1 项待处理」。现在恢复路径与 `queue/list` 共用同一组元数据校验：非法总数、待处理数、分类计数与截断标记按缺失处理，`counts` 与待处理总数不一致时整体丢弃；`queue/list` 行为不变。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1561](https://github.com/can4hou6joeng4/boss-harness/issues/1561)：`queue/list` 与 `thread/resume` 的队列元数据已知 `totalItems` / `activeItems` 大于已载入规模时，`truncated` 缺失或误报为 `false` 会让同一页面在驾驶舱、队列面板与提交核对中得到矛盾结论，未载入的消息被判为「不存在」。现在共用校验在投影必然不完整时强制截断，提交核对返回「无法确认」，队列面板显示未载入提示；完整投影行为不变。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1563](https://github.com/can4hou6joeng4/boss-harness/issues/1563)：真实内核来源的审批缺少 `approvalId` 时，审批卡仍可点击，处理函数把无标识审批当成示例模式卡片，只改本地状态并显示「已批准 / 已拒绝」，内核从未收到裁决，刷新后又回到待审批。现在 `approvalBlockReason` 区分模式与标识：真实模式下缺少有效标识返回新的阻塞原因，渲染与处理函数共用该判定，按钮禁用并提示刷新会话核对；示例模式的无标识卡片保持本地演示行为。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1565](https://github.com/can4hou6joeng4/boss-harness/issues/1565)：`thread/list` 的会话行先校验 `queueActiveItems`，却用原始值校验 `queueCounts`；字符串、负数或 `NaN` 总数会跳过一致性检查，分类计数仍进入侧栏，`sessionNeedsAttention` 可能把会话列入「待你处理」而队列徽标不显示。现在 `queueMapping` 提供 `threadQueueCountsOf`，待处理总数无效时分类整体丢弃，会话列表与推理设置回执共用；`queueStatusCountsOf` 要求传入已校验的总数。只改渲染层，不改变 RPC、协议或版本号。
- [Issue #1567](https://github.com/can4hou6joeng4/boss-harness/issues/1567)：技术参考与使用指南补记 rc.53 之后四项渲染层修正的行为边界：`queue/list` 与 `thread/resume` 共用元数据校验；总数或待处理数大于已载入项时按截断处理，截断标记缺失或误报为 `false` 不改变结论；分类计数必须与已接受的待处理总数一致，会话行分类计数以总数有效为前提；真实审批缺少有效标识时不可提交。只改文档，不改变源码、RPC、协议或版本号。

## 0.2.0-rc.53 - 2026-11-16

本节汇总第五十三个候选版本的源码与交付内容；rc.16 至 rc.53 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.52，本次包含 5 项交付：Source build 增加 wheel / sdist 隔离安装、版本断言与 `--check` 自检（#1547、#1548）；README 与队列徽标说明同步（#1549、#1550）；增加 Issue 表单与安全政策入口（#1551、#1552）；重新排队兜底投影计入已撤回记录（#1553、#1554）；审批字段展示约束对齐内核与桌面（#1555、#1556）。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

升级注意：不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.52 源码无需迁移。rc.52 已准备的 5 项修复与更早候选内容继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1557](https://github.com/can4hou6joeng4/boss-harness/issues/1557)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.53` / Python `0.2.0rc53`；将 rc.52 之后 5 项交付归入本候选，同步 README 近期进展与版本表、使用指南的候选状态、技术要求中的候选引用与 Issue 表单示例版本。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1547](https://github.com/can4hou6joeng4/boss-harness/issues/1547)：`.github/workflows/build.yml` 原先只构建 wheel / sdist、生成清单并上传，产物不可安装或入口损坏时 Source build 仍然通过。现在构建后把 wheel 与 sdist 分别安装到全新 venv，断言 `boss_harness.__version__` 与 `harness/pyproject.toml` 一致，并用私有临时状态目录执行 `boss-harness --check --provider none`，非 0 即失败；不启动 Electron、不调用模型或招聘平台，缺少业务 CLI 只产生警告。
- [Issue #1549](https://github.com/can4hou6joeng4/boss-harness/issues/1549)：README 的 CI 说明与 `QueueBadge.counts` 注释落后于实际行为。现在 CI 说明列出 wheel / sdist 隔离安装与启动自检；徽标注释说明截断投影也可能携带内核持久分类，待处理数大于 0 时优先使用。只改文档与注释，不改变运行时行为。
- [Issue #1551](https://github.com/can4hou6joeng4/boss-harness/issues/1551)：仓库原先没有 Issue 表单，外部反馈缺少版本、安装方式、平台、复现步骤与验证范围，安全漏洞也可能进入公开 Issue。新增缺陷与功能建议表单及 `config.yml`，必填可复现信息并提示脱敏，提供安全政策、使用指南与技术参考入口；不改变源码、RPC、协议或版本号。
- [Issue #1553](https://github.com/can4hou6joeng4/boss-harness/issues/1553)：重新排队已受理但队列刷新失败时，`queueRetryPage` 对成功撤回的旧项按 0 增量计算持久总数；内核 `queue/remove` 只把旧项标记为 `cancelled`，记录仍计入 `totalItems`，新项又新增一条，截断队列因此少显示 1 项（5 而非 6），多次重试持续漂移。现在只要内核总数已知，重新排队统一按新项加 1，成功撤回不再扣减；本地条目、待处理数与分类计数不变。只改渲染层兜底投影，不改变 RPC、协议或版本号。
- [Issue #1555](https://github.com/can4hou6joeng4/boss-harness/issues/1555)：内核审批校验只要求 `toolName` 是字符串、不校验条目 id，桌面却要求两者去空白后非空且不超过 200 字符；损坏的待审批会进入索引、`pending_approvals` 与 `pending_approval_counts`，却被渲染层丢弃。两条待审批中一条工具名为空时，铃铛显示 2 项而通知面板只有 1 条可处理。现在 `_valid_approval_item` 对工具名与条目 id 使用与桌面展示一致的约束，索引、列表与持久计数都不再包含无法展示的条目；既有缓存索引在会话变化或运行 `--repair-state` 重建后收敛。不新增 RPC 方法，不改变持久化格式或权限，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.52 - 2026-11-16

本节汇总第五十二个候选版本的源码与交付内容；rc.16 至 rc.52 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.51，本次包含 5 项修复：截断队列投影下侧栏保留暂停分类并在本地操作后校正（#1535、#1537）；队列投影返回持久分类计数（#1539）；审批列表返回按会话持久计数（#1541）；驾驶舱显示待审批持久总数（#1543）。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

升级注意：不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.51 源码无需迁移。rc.51 已准备的 5 项变更与更早候选内容继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1535](https://github.com/can4hou6joeng4/boss-harness/issues/1535)：截断队列投影下侧栏徽标会丢失暂停计数。228 个待处理项（128 排队 + 100 暂停）时，`queue/list` 投影只返回 100 暂停 + 100 排队并标记截断，`queueBadgeOf` 只给出待处理总数，`patchQueueBadge` 因此把会话行已有的 `queueCounts` 清成 `undefined`，侧栏的暂停徽标与「待你处理」分组在下次 `thread/list` 刷新前消失。现在截断投影且待处理总数未变时保留上一次分类计数；总数变化或拿到完整计数时仍按新值更新。只改渲染层徽标合并逻辑与说明，不改变 RPC、内核投影、协议或版本号。
- [Issue #1537](https://github.com/can4hou6joeng4/boss-harness/issues/1537)：`#1536` 只覆盖待处理总数不变的截断刷新；本地入队、撤回暂停项或重新排队仍会改变总数，`queueBadgeOf` 只返回新的待处理总数，`patchQueueBadge` 随即清空会话行的 `queueCounts`，暂停徽标与「待你处理」分组再次消失。现在 `patchQueuePage` / `queueRetryPage` 在截断投影上记录已载入条目的分类增量，徽标合并时在已知计数与旧总数一致的前提下应用增量，并要求结果非负且分类之和等于新的待处理总数，否则只保留总数。不改变 RPC、内核投影、协议或版本号。
- [Issue #1539](https://github.com/can4hou6joeng4/boss-harness/issues/1539)：内核事件导致的投递同样会改变待处理总数，但截断投影没有本地增量可依：228 个待处理项（128 排队 + 100 暂停）投递一条后，`queue/list` 只返回 100 暂停 + 99 排队且不带分类，侧栏 `queueCounts` 再次被清空，暂停徽标与「待你处理」分组反复消失。现在 `project_queue` 按全部有效持久记录返回分类计数，快照路径按完整记录流计数；`queue/list` 附可选 `counts`，`thread/read` / `thread/resume` 附可选 `queueCounts`。渲染层校验三个计数为非负安全整数且之和等于待处理总数，徽标优先使用持久分类，本地操作按已载入条目增量校正；旧内核缺省时沿用既有回退。不新增 RPC 方法，不改变持久化格式或权限，协议仍为 `0.2.0`。
- [Issue #1541](https://github.com/can4hou6joeng4/boss-harness/issues/1541)：`approval/list` 默认只返回前 100 条待审批，侧栏「待审批」徽标与「待你处理」分组却只按已返回条目聚合；审批超过一页时，排在页面之外的会话完全不提示，铃铛只显示「至少 100 项待审批」。现在内核新增 `pending_approval_counts`，按同一组过滤条件统计全部待审批的按会话数量，`approval/list` 附可选 `threadCounts`；渲染层校验会话 id、非负整数与合计下限，合法时用精确总数和按会话计数，旧内核缺省时保持「至少 N」回退。通知面板同步显示精确总数，列表截断提示不变。不新增 RPC 方法，不改变持久化格式或权限，协议仍为 `0.2.0`。
- [Issue #1543](https://github.com/can4hou6joeng4/boss-harness/issues/1543)：`#1542` 之后铃铛与通知面板已使用持久总数，但运行驾驶舱的「待办与目录」仍只统计已返回条目，100 条审批分属 101 个会话时显示 `100（仍有其他项未显示）`，同一时刻出现两个总数。驾驶舱快照现在保存 `approval/list` 的持久总数，事实行优先显示总数，旧内核缺省时回退到已返回条目数；列表页签与截断提示不变。只改渲染层展示，不改变 RPC、协议或版本号。

## 0.2.0-rc.51 - 2026-11-16

本节汇总第五十一个候选版本的源码与交付内容；rc.16 至 rc.51 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.50，本次包含 5 项变更：README 增加英文项目概览（#1523）；队列读取投影优先保留暂停项（#1525）；队列与审批面板的截断提示改为不声称遗漏项一定更早，并补齐已结束项也可能未载入的说明（#1527、#1529、#1531）。队列投影修复改变 `queue/list` / `thread/resume` 在待处理项超过 200 时返回的条目选择，不改变持久化格式、计数或截断标记。

升级注意：不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.50 源码无需迁移。rc.50 已准备的项目分组文档与更早候选内容继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1533](https://github.com/can4hou6joeng4/boss-harness/issues/1533)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.51` / Python `0.2.0rc51`；将 rc.50 之后 5 项变更归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术要求中的候选引用。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1523](https://github.com/can4hou6joeng4/boss-harness/issues/1523)：README 增加「English overview」段，用英文概括项目定位、进程边界、执行与队列、安全边界、模型线路与桌面能力，并明确 `0.2.0-rc.51` 仍为源码候选、最新实际发布为 `v0.2.0-rc.15`、当前没有独立安装包；同时链接现有中文 README、使用指南、技术要求与上游核对记录。不改变代码、RPC、协议或版本号。
- [Issue #1525](https://github.com/can4hou6joeng4/boss-harness/issues/1525)：队列读取投影此前先保留最近的排队 / 投递中项，暂停项只使用剩余名额；在 128 条排队消息加 100 条暂停消息的会话里，28 条较早的暂停项不会出现在 `queue/list` / `thread/resume` 投影中，而暂停项不会自动投递、只能由用户重新排队或撤回。现在投影优先保留暂停项，再保留最近的排队 / 投递中项，待处理项仍单次最多 200 项、计数与截断标记不变；同步修正 README、使用指南与技术参考中的投影说明。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1527](https://github.com/can4hou6joeng4/boss-harness/issues/1527)：队列面板的截断提示此前写成「更早的队列记录未载入」；暂停项优先后，暂停项占满 200 项名额时新排入的排队消息也会被挤出投影，缺失的并不一定是更早记录。提示改为说明暂停项优先、待处理合计最多 200 项，未载入的项目可能包括排队项或暂停项。不改变投影、计数、RPC、协议或版本号。
- [Issue #1529](https://github.com/can4hou6joeng4/boss-harness/issues/1529)：通知面板与运行状态面板的审批截断提示此前写成「还有更早的待审批未返回」。内核 `pending_approvals` 按会话更新时间与随机的条目 id 排序，被 `LIMIT` 截掉的项不保证更早；同时较早更新过的会话也可能仍有等待中的审批。提示与相关注释改为「其他待审批未返回 / 未显示」，内核 docstring 同步改为“more pending approvals were omitted”。不改变排序、截断判定、RPC、协议或版本号。
- [Issue #1531](https://github.com/can4hou6joeng4/boss-harness/issues/1531)：`#1526` 改为暂停项优先后，`queueMapping.ts` 的模块注释仍写「待处理与已结束条目各自封顶」，队列面板的截断提示也只列出排队项与暂停项可能未载入。按内核 `queue_view.project_queue`，暂停项先占最多 200 个名额，排队 / 投递中项使用剩余名额（待处理合计最多 200 项），已结束项再使用剩余名额并另受 50 项上限，待处理占满 200 项时已结束项全部不返回。注释与提示同步改为该规则，并说明已结束项也可能未载入。不改变投影、计数、RPC、协议或版本号。

## 0.2.0-rc.50 - 2026-11-16

本节汇总第五十个候选版本的源码与交付内容；rc.16 至 rc.50 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.49，本次包含 1 项文档补充：使用指南新增「项目分组」一节，说明新建项目、更改显示名称与移除本地分组的入口和影响，记录项目名称最多 60 个 Unicode 码点，以及分组只保存在本机（#1518）。本候选同时同步版本与 README、使用指南、技术要求中的候选引用。

升级注意：本候选只补充文档，不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.49 源码无需迁移。rc.49 的标题截断修正、rc.48 的项目名称修正、rc.47 的 2 项输入与文档修正、rc.46 的 3 项输入与搜索边界修正、rc.45 的 3 项码点计数修正、rc.44 的 9 项搜索与代码围栏修正、rc.43 的安全报告政策、发布资产清单、非法日期校验与只读查表修正继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1520](https://github.com/can4hou6joeng4/boss-harness/issues/1520)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.50` / Python `0.2.0rc50`；将 rc.49 之后 1 项文档补充归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术要求中的候选引用。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1518](https://github.com/can4hou6joeng4/boss-harness/issues/1518)：使用指南补充「项目分组」一节，说明新建项目、更改显示名称与移除本地分组的入口和影响；记录项目名称按 Unicode 码点最多 60 个字符、超限提示并禁用提交，以及分组与显示名称只保存在本机界面偏好、移除本地分组不会删除会话。快速导航增加对应锚点。不改变代码、RPC 或协议，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.49 - 2026-11-16

本节汇总第四十九个候选版本的源码与交付内容；rc.16 至 rc.49 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.48，本次包含 1 项变更：会话顶栏标题、分支标签与新建会话标题改为按 Unicode 码点判断与截断，emoji 短标题不再被误加省略号，也不会被提前截短（#1513）。本候选同时同步版本与 README、使用指南、技术要求中的候选引用。

升级注意：本候选只修正本地标题的展示与生成，不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.48 源码无需迁移。rc.48 已准备的 1 项项目名称修正、rc.47 已准备的 2 项输入与文档修正、rc.46 已准备的 3 项输入与搜索边界修正、rc.45 的 3 项码点计数修正、rc.44 的 9 项搜索与代码围栏修正、rc.43 的安全报告政策、发布资产清单、非法日期校验与只读查表修正继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1515](https://github.com/can4hou6joeng4/boss-harness/issues/1515)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.49` / Python `0.2.0rc49`；将 rc.48 之后 1 项变更归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术要求中的候选引用。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1513](https://github.com/can4hou6joeng4/boss-harness/issues/1513)：标题工具此前把上限当作 UTF-16 码元处理。`compactTitle` 用 `String.length` 判断是否超限、用按码元截断的 `safeSlice` 执行截断：emoji 等扩展区字符每个占 2 个码元，20 个 emoji、上限 28 时码元数 40 超过上限，未超限的短标题被追加了省略号，29 个 emoji 则被提前截到 14 个；会话顶栏标题（上限 28）与分支标签（上限 80）都受影响。同文件的 `sessionTitleFromPrompt` 同样按码元截断，40 个 emoji 的提示词生成的会话标题只有 16 个字符。现在两者都先按 Unicode 码点判断、再按码点截断：未超限的 emoji 标题原样返回，新建标题最多 32 个码点，ASCII / CJK 边界不变，截断结果不含孤立代理项。离线探针覆盖 20 / 28 / 29 个 emoji、40 个 emoji 与 ASCII 的新建标题、CJK 边界、项目前缀剥离、空白折叠与空输入回退；`npm run typecheck`、`npm run build` 通过。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.48 - 2026-11-16

本节汇总第四十八个候选版本的源码与交付内容；rc.16 至 rc.48 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.47，本次包含 1 项变更：新建项目与重命名项目的名称上限改为按 Unicode 码点计数，emoji 名称不再被按 UTF-16 码元静默截断到 30 个字符，超限时明确提示并禁用提交（#1508）。本候选同时同步版本与 README、使用指南、技术要求中的候选引用。

升级注意：本候选只修正本地项目名称的输入与提示，不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.47 源码无需迁移。rc.47 已准备的 2 项输入与文档修正、rc.46 已准备的 3 项输入与搜索边界修正、rc.45 的 3 项码点计数修正、rc.44 的 9 项搜索与代码围栏修正、rc.43 的安全报告政策、发布资产清单、非法日期校验与只读查表修正继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1510](https://github.com/can4hou6joeng4/boss-harness/issues/1510)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.48` / Python `0.2.0rc48`；将 rc.47 之后 1 项变更归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术要求中的候选引用。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。
- [Issue #1508](https://github.com/can4hou6joeng4/boss-harness/issues/1508)：新建项目与重命名项目的名称输入框此前使用 HTML `maxLength={60}`，按 UTF-16 码元计数，emoji 等扩展区字符占 2 个码元，实际最多只能输入 30 个字符，超限时静默截断且没有提示；截断落在代理对中间时还可能残留孤立代理项并存入本机项目列表。现在项目名称按 Unicode 码点计数，上限 60 个字符，输入框按码元放宽到 120；超过上限时显示「项目名称最多 60 字符」并禁用提交，与聊天名称的口径一致。离线探针覆盖 60 / 61 个 emoji 与 CJK 字符的边界以及空白输入；`npm run typecheck`、`npm run build` 通过。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.47 - 2026-11-16

本节汇总第四十七个候选版本的源码与交付内容；rc.16 至 rc.47 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.46，本次包含 2 项变更：上下文编辑对话框显示替换文本的码点计数，超过 32000 字符时明确提示并阻止提交，不再落入「提交结果未确认」（#1501）；README 与使用指南补充消息搜索最多 200 个码点的查询上限，超过时只按标题与项目过滤并说明「未搜索消息」（#1503）。本候选同时同步版本与 README、使用指南、技术要求中的候选引用。

升级注意：本候选只补充输入提示与文档，不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.46 源码无需迁移。rc.46 已准备的 3 项输入与搜索边界修正、rc.45 已准备的 3 项码点计数修正、rc.44 已准备的 9 项搜索与代码围栏修正、rc.43 的安全报告政策、发布资产清单、非法日期校验与只读查表修正继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1505](https://github.com/can4hou6joeng4/boss-harness/issues/1505)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.47` / Python `0.2.0rc47`；将 rc.46 之后 2 项变更归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术要求中的候选引用。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1501](https://github.com/can4hou6joeng4/boss-harness/issues/1501)：上下文编辑对话框的替换文本显示「当前 / 32000 字符」计数，并按 Unicode 码点判定上限；超过时显示明确错误并禁用「使用替换文本」，提交前的 `apply` 也会做同样的防御性校验，不再发起必然被主进程拒绝的请求，也不会落入「提交结果未确认」的通用提示。「恢复原文」提交超长原文时同样给出「超过 32000 字符上限，未提交」的原因。32000 个 emoji 可提交，32001 个码点被拒绝；计数改用共享的 `codePointLength`，不再构造中间数组。不新增 RPC，协议、内核与存储格式不变。

- [Issue #1503](https://github.com/can4hou6joeng4/boss-harness/issues/1503)：README 的跨会话搜索要点与使用指南的对应章节补充消息搜索的 200 字符查询上限：按 Unicode 码点计数，超过时消息内容不参与检索，只按标题与项目过滤，消息分区说明「未搜索消息」。仅文档变更，与 rc.46 的 #1496 行为一致；不新增 RPC，协议与内核不变。

## 0.2.0-rc.46 - 2026-11-16

本节汇总第四十六个候选版本的源码与交付内容；rc.16 至 rc.46 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.45，本次聚合 3 项桌面输入与搜索边界修正：排队消息编辑器的正文上限按 Unicode 码点计数，60000 个 emoji 不再被误判超限（#1492）；会话名称输入从遗留的 100 个 UTF-16 码元改为内核一致的 500 个码点，粘贴 101–500 字符不再被静默截断（#1494）；超过 200 个码点的搜索词不再发起必然失败的 `thread/search`，改为明确说明「搜索词超过 200 字符，未搜索消息」（#1496）。三项均在 rc.45 基线之后合入，本候选同时同步版本与 README、使用指南、技术要求中的候选引用。

升级注意：本候选只修正长度计数与搜索输入边界，不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.45 源码无需迁移。rc.45 已准备的 3 项码点计数修正、rc.44 已准备的 9 项搜索与代码围栏修正、rc.43 的安全报告政策、发布资产清单、非法日期校验与只读查表修正继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1498](https://github.com/can4hou6joeng4/boss-harness/issues/1498)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.46` / Python `0.2.0rc46`；将 rc.45 之后 3 项修正归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术要求中的候选引用。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1492](https://github.com/can4hou6joeng4/boss-harness/issues/1492)：排队消息编辑器的正文上限改用 Unicode 码点计数，与内核 `queue/update` 的 `_text(maximum=100000)` 一致。此前 `maxLength` 与计数器按 UTF-16 码元计算，60000 个 emoji 的排队消息会显示 `120000 / 100000 字符` 并阻止继续输入；现在计数器与保存前校验按码点判定，输入框只保留 `2 × 100000` 个码元的安全网（正好覆盖 100000 个补充平面字符的表示），超过 100000 码点的草稿禁止保存并提示原因。60000 个 emoji 可正常编辑并保存，100001 个码点仍拒绝，100000 个 ASCII 字符行为不变。不新增 RPC，协议、内核与队列格式不变。

- [Issue #1494](https://github.com/can4hou6joeng4/boss-harness/issues/1494)：会话名称输入框的上限从遗留的 100 个 UTF-16 码元改为内核与文档一致的 500 个 Unicode 码点。此前粘贴 101–500 字符的名称会被浏览器静默截断到 100，已有 200 字符内核标题也无法继续编辑；现在输入框允许到 500 码点并保留 `2 × 500` 个码元的安全网，超过时显示「名称最多 500 字符」并禁用保存，`confirmRenameSession` 保留相同的防御性校验。浏览器预览的本机别名与写入内核的路径共用该上限。500 个 emoji 或 500 个 ASCII 字符可保存，501 个码点被拒绝并提示。不新增 RPC，协议、内核与别名迁移格式不变。

- [Issue #1496](https://github.com/can4hou6joeng4/boss-harness/issues/1496)：搜索弹窗不再为超过 200 个码点的搜索词发起必然失败的 `thread/search`。此前输入超过主进程安全校验与内核 `_text(maximum=200)` 上限的关键词时，请求被拒绝后界面落入通用错误态，误报「消息搜索失败」并建议稍后重试；实际并未检索，重试也不会成功。现在超限时不发请求，状态行与消息区明确说明「搜索词超过 200 字符，未搜索消息」，标题搜索仍按当前输入工作；200 个码点以内（含 200 个 emoji）照常检索，199 与 200 字符行为不变。最近搜索的 200 码点过滤与消息搜索上限共用 `MESSAGE_SEARCH_MAX_LENGTH`。不新增 RPC，协议、内核与存储键不变。

## 0.2.0-rc.45 - 2026-11-16

本节汇总第四十五个候选版本的源码与交付内容；rc.16 至 rc.45 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.44，本次聚合 3 项 Unicode 码点计数修正：主进程对会话标题、搜索查询、上下文替换文本与技能目录名的长度校验（#1483），搜索与查找的 2 / 120 字符阈值及最近搜索上下限（#1485），以及发送、排队、首页首条消息、快速提问与草稿持久化的 100000 字符上限（#1487）。桌面现在按 Unicode 码点计数，与内核 `len()` 一致，emoji 等补充平面字符不再被当成两个字符而误拒。

升级注意：本候选只修正长度计数口径，不改变协议、RPC、持久化格式、存储键或工具权限；已安装的 rc.44 源码无需迁移。rc.44 已准备的 9 项搜索与代码围栏修正、rc.43 的安全报告政策、发布资产清单、非法日期校验与只读查表修正继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1489](https://github.com/can4hou6joeng4/boss-harness/issues/1489)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.45` / Python `0.2.0rc45`；将 rc.44 之后 3 项修正归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术要求中的候选引用。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1483](https://github.com/can4hou6joeng4/boss-harness/issues/1483)：桌面主进程对 `thread/start.title`、`thread/search.query`、`context/edit.replacementText` 与技能目录名（`skills/read`、`skills/write`、`skills/delete`）的长度上限改用 Unicode 码点计数，与内核 `len()` 及上下文编辑对话框的保存条件一致；101 个 emoji 的搜索查询与 16001 个 emoji 的替换文本不再在到达内核前被拒绝，最近搜索的 200 字符上限同样按码点判定。按码点超限的输入仍被拒绝，UTF-8 字节上限、路径安全规则、协议、RPC、持久化格式与工具权限不变。

- [Issue #1485](https://github.com/can4hou6joeng4/boss-harness/issues/1485)：搜索弹窗、聊天内查找与最近搜索的字符阈值改用 Unicode 码点计数，与界面文案「至少 2 个字符」「120 个字符」一致。消息搜索的最小长度收为单一常量 `MESSAGE_SEARCH_MIN_LENGTH`，弹窗请求、进行中状态与空态提示共用；单个 emoji 不再被当成 2 个字符触发 `thread/search`、显示「正在搜索消息…」或记入最近搜索，2 个 emoji 仍触发并可记入。查找种子（`findSeedFromSelection`）的 120 字符上限按码点判定：120 个 emoji 的选中文本可作为关键词，121 个仍拒绝，120 个 ASCII 行为不变。最近搜索的下限与上限现在都按码点计数。不新增 RPC，协议、内核与持久化格式不变。

- [Issue #1487](https://github.com/can4hou6joeng4/boss-harness/issues/1487)：桌面发送前的消息长度校验与草稿持久化改用 Unicode 码点计数，与内核 `_text(maximum=100000)` 的 `len()` 口径一致。此前按 UTF-16 码元比较，60000 个 emoji 的消息会被误判为 120000 字符而拒绝，提示还声称超过内核上限；同类合法草稿也不会写入本地存储，重启后丢失。现在输入区发送与排队、首页首条消息（连同项目上下文与附件）、快速提问与草稿读写共用码点口径，快速提问复用 `MAX_MESSAGE_TEXT_LENGTH` 而不再单独维护同值常量。60000 个 emoji 的消息与草稿可正常发送、持久化并恢复，100001 个码点仍拒绝，100000 个 ASCII 字符行为不变。不新增 RPC，协议、内核与存储键不变。

## 0.2.0-rc.44 - 2026-11-16

本节汇总第四十四个候选版本的源码与交付内容；rc.16 至 rc.44 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.43，本次聚合 9 项使用者可见修正：聊天代码围栏支持带 `#` 的语言标记、`~~~` 波浪号围栏与标记前空白（#1462 / #1466 / #1468），聊天内查找合并 NFKC / casefold 展开产生的重复命中（#1464），会话搜索统一半角 / 全角假名的浊音组合与谚文音节 / jamo 分簇（#1470 / #1472 / #1474 / #1476），并在 Python 3.10–3.14 与桌面之间补齐 Unicode 14–17 的大小写与兼容分解映射（#1478）。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：本候选包含渲染层与 Python 内核的运行时代码修正，但不改变协议、RPC、持久化格式或工具权限；npm 与 Python 包版本号为候选值，已安装的 rc.43 源码无需迁移。搜索归一化只在含新版 Unicode 映射码点时启用补表，纯 ASCII 文本走快路径。安全报告政策、发布资产清单、非法日期校验与只读查表修正继续适用。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1480](https://github.com/can4hou6joeng4/boss-harness/issues/1480)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.44` / Python `0.2.0rc44`；将 rc.43 之后 9 项修正归入本候选，同步 README 近期进展与版本表、使用指南的候选状态。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1462](https://github.com/can4hou6joeng4/boss-harness/issues/1462)：聊天代码围栏的语言标记接受 `#`，`c#`、`f#`、`q#` 等标记不再按普通文本渲染，结束围栏也不会把后续正文吞进空代码块；`js`、`csharp` 等原有标记与未闭合围栏、CRLF 行为不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1464](https://github.com/can4hou6joeng4/boss-harness/issues/1464)：聊天内查找把 NFKC / casefold 展开（`ﬃ` → `ffi`、`ß` → `ss`）映射回同一原文字素的重复命中合并为一条区间，计数、Enter 步进与可见高亮不再出现「显示 2 处、实际 1 处」；普通文本、整段查询与搜索标注行为不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1466](https://github.com/can4hou6joeng4/boss-harness/issues/1466)：聊天代码围栏按 CommonMark 常见规则识别 `~~~` / `~~~~` 波浪号围栏，语言标记、代码样式与复制按钮与反引号围栏一致；结束围栏必须与起始标记同类且不短于起始长度，围栏内的另一种标记仍按代码正文处理。正文里的装饰性 `~~~`、四空格缩进行与未闭合围栏行为不变，现有反引号围栏规则不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1468](https://github.com/can4hou6joeng4/boss-harness/issues/1468)：聊天代码围栏接受语言标记前的空格与 Tab：反引号或波浪号围栏后先写空格 / Tab 再写 `js` 等标记，不再按普通文本渲染，结束围栏也不会被当作新的起始围栏把后续正文吞进代码块；语言标记字符集、反引号 / 波浪号围栏、未闭合围栏与 CRLF 行为不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1470](https://github.com/can4hou6joeng4/boss-harness/issues/1470)：会话搜索的 NFKC 组合簇识别半角假名的浊音 / 半浊音符号（U+FF9E / U+FF9F），`ｶﾞ` / `ﾊﾟ` / `ｳﾞ` 与 `ガ` / `パ` / `ヴ` 归一化为同一文本并可互相命中；桌面端跨会话搜索的命中区间覆盖完整原文字符对，片段与高亮口径一致。孤立的浊音符号、非半角假名后的符号、谚文 jamo、组合重音与 casefold 行为不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1472](https://github.com/can4hou6joeng4/boss-harness/issues/1472)：会话搜索把半角浊音 / 半浊音符号（U+FF9E / U+FF9F）作为组合簇扩展记号处理，不再限定基字必须是半角假名；`カﾞ` / `はﾞ` / `ウﾞ` 与兼容假名 `㋕ﾞ` 分别与 `ガ` / `ば` / `ヴ` / `ガ` 归一化为同一文本并可互相命中。`ｶﾞ` 等 #1470 用例、孤立符号、`aﾞ` / `中ﾞ`、谚文 jamo、组合重音与 casefold 行为不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1474](https://github.com/can4hou6joeng4/boss-harness/issues/1474)：会话搜索把预组合谚文音节后的 jamo 并入同一组合簇，`간`（U+AC00 U+11AB）与 `간` 归一化为同一文本并可互相命中；完全分解的 L V T jamo 仍归一化为 `간`，`각ᆫ`、`가ᅡ` 的 NFKC 结果、假名浊音、组合重音与 casefold 行为不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1476](https://github.com/can4hou6joeng4/boss-harness/issues/1476)：会话搜索把谚文兼容字母（U+3131–U+318E）与半角字母（U+FFA0–U+FFDC）并入相邻谚文音节 / jamo 的组合簇，`ㄱㅏ` / `ㄱㅏᆫ` / `가ㄳ` 分别与 `가` / `간` / `갃` 归一化为同一文本并可互相命中；桌面会话内查找与内核搜索两个方向一致，`findTextRanges("ㄱㅏ", "가")` 与反向都返回完整区间。纯兼容字母组合仍按 NFKC 归并（`ㅎㅏㄴ` → `하` + 前导 jamo），预组合音节仍各自成簇，普通韩文文本的逐字素映射、组合 jamo、假名浊音、组合重音与 casefold 行为不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1478](https://github.com/can4hou6joeng4/boss-harness/issues/1478)：会话搜索的归一化补齐 Python 运行时较旧 Unicode 数据与桌面运行时（Node 24 / Unicode 17.0）的映射差值：Unicode 14–17 新增的 casefold（Vithkuqi、Garay、Beria Erfe 等大小写字母）与 NFKC 兼容分解（修饰字母、outlined 字母与数字、U+A7F1）在 Python 3.10–3.13 上也能与桌面一致地互相命中，Python 3.14 已覆盖的部分保持幂等。含补表码点的文本在分解后再次 NFKC，`U+A7F1` + 组合锐音符与预组合 `ś` 归一化为同一文本。纯 ASCII 文本走 `isascii` 快路径，普通文本不承担补表开销；既有 casefold、谚文 / 假名组合与搜索区间行为不变。不改变协议、RPC、持久化格式或工具权限。

## 0.2.0-rc.43 - 2026-11-16

本节汇总第四十三个候选版本的源码与交付内容；rc.16 至 rc.43 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.42，本次聚合 2 项文档交付与候选期后续 4 项使用者可见修正：新增安全报告政策并在 README 的安全边界与项目导航加入入口（#1444），修正 README 中 rc.42 候选基线表述（#1446）；候选准备后补充发布资产清单生成入口（#1452）、拒绝被 `Date` 归一化的非法 ISO 日期（#1454）、用量「未计入原因」查表只读自有属性（#1456），以及任务核对、驾驶舱与渲染进程崩溃标签只读自有属性（#1458）。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：本候选包含渲染层与共享工具的运行时代码修正，但不改变协议、RPC、持久化格式或工具权限；npm 与 Python 包版本号为候选值，已安装的 rc.42 源码无需迁移。安全政策只说明报告渠道与负责边界，不代表仓库已启用私密漏洞报告、secret scanning 或 Dependabot 安全更新；这些设置需单独授权。最新实际发布仍为 rc.15。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；新增的 `scripts/release_assets.py` 只在 CI 与本地发布准备中生成资产清单，不改变安装方式。真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1448](https://github.com/can4hou6joeng4/boss-harness/issues/1448)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.43` / Python `0.2.0rc43`；将 rc.42 之后 2 项文档交付归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1444](https://github.com/can4hou6joeng4/boss-harness/issues/1444)：新增安全报告政策 `SECURITY.md`，说明支持范围、首选非公开报告渠道、报告应含与不得含的内容、本项目负责的状态目录、JSON-RPC、工具审批与导出脱敏边界，以及不负责的上游 CLI、用户自定义端点、真实账号与依赖漏洞范围；README 的安全边界与项目导航同步加入入口。政策不假定 GitHub 私密漏洞报告入口已经可见，启用 secret scanning、Dependabot 安全更新等仓库设置仍需单独授权。

- [Issue #1446](https://github.com/can4hou6joeng4/boss-harness/issues/1446)：README「近期进展」把 rc.42 候选写成「汇总 rc.42 之后 6 项修正」，与同一文件的版本表、CHANGELOG 的「相对 rc.41」及 Issue #1443 的发布正文草稿不一致。现已改为「相对 rc.41」，6 项修正清单、链接与其余表述不变，读者可据此判断 rc.42 实际包含的变化。仅文档修正。

- [Issue #1452](https://github.com/can4hou6joeng4/boss-harness/issues/1452)：新增 `scripts/release_assets.py`，为 wheel / sdist 生成 `build-info.json` 与 `SHA256SUMS.txt`；Source build 在构建后运行该脚本，并把 `dist/python` 作为 `python-dist` 工作流产物上传。脚本只读取显式列出的普通文件，拒绝符号链接、目录、重复文件名与保留输出名，按块计算 SHA-256、按文件名排序并原子写入；工作流产物不代替从 tag 提交构建和实际 Release 资产。不改变内核、RPC、工具权限或持久化格式。

- [Issue #1454](https://github.com/can4hou6joeng4/boss-harness/issues/1454)：`parseIsoDateTime` 在交给 `Date` 前校验年月日、时分秒与偏移范围，拒绝 `2026-02-30`、`2026-04-31`、`24:00:00` 等会被 `Date` 静默归一化的非法时间。会话排序、工具来源时间、回合耗时与相对时间不再把损坏记录显示成另一个日期；合法 `Z` / 偏移、小数秒与闰日行为保持不变。不改变协议、RPC、持久化格式或工具权限。

- [Issue #1456](https://github.com/can4hou6joeng4/boss-harness/issues/1456)：用量「未计入原因」查表只读取 `USAGE_REASONS` 的自有属性，`constructor` / `toString` 等原型链键不再被映射成函数源码；`unverifiedReasons` 改用空原型对象承接，`__proto__` 键也能原样展示。已知原因文案与顺序不变；不改变协议、RPC、持久化格式或工具权限。

- [Issue #1458](https://github.com/can4hou6joeng4/boss-harness/issues/1458)：任务核对与驾驶舱的标签查表只读取自有属性，内核返回的任意状态、阶段或配置策略值（`constructor` / `toString` / `__proto__` 等）不再命中原型链成员；渲染进程崩溃与登录页退出原因同样只匹配自有标签，未知原因原样保留。已知文案不变；不改变协议、RPC、持久化格式或工具权限。

## 0.2.0-rc.42 - 2026-11-16

本节汇总第四十二个候选版本的源码与交付内容；rc.16 至 rc.42 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.41，本次聚合 6 项使用者可见的修正：`skills/list` 未加载项清单不再被有效技能数量截断（#1422），目录总数恰好等于候选窗口时不再误报截断（#1424），可加载技能超过展示上限时不再静默丢弃多余项（#1431），附件名称进入提示词前按 JSON 字符串字面量转义（#1433），输入区技能菜单同步提示清单不完整（#1435），以及流泵取消落在事件循环关闭窗口时不再抛出内部 `RuntimeError`（#1437）；同版修正技术契约里与新语义矛盾的旧版目录发现上限描述（#1427）。这些改动只影响清单完整性的如实报告、提示词输入卫生、取消与超时错误语义及文档准确性，技能加载、附件注入与工具权限不变。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：可加载技能超过 100 个时返回 `skillsTruncated`，未加载项超过 100 条时返回 `problemsTruncated`，目录枚举确有未检查项时返回 `candidatesTruncated`；三个字段缺省即表示对应清单完整。旧内核不返回这些字段，界面按清单完整处理。取消或超时的错误信息不再被 `Event loop is closed` 覆盖。已保存的技能选择与队列消息不受影响，无需手动迁移。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

### 变更

- [Issue #1422](https://github.com/can4hou6joeng4/boss-harness/issues/1422)：`skills/list` 的未加载项清单不再被有效技能数量截断。此前只要字典序靠前的有效技能凑满 100 个展示上限就立即返回，排在后面的坏目录（缺失 `SKILL.md`、符号链接、超过 64 KiB 或非 UTF-8）完全不出现在 `problems` 中，界面会把不完整清单当成「N 个技能未能加载」。现在两份清单各自独立封顶，扫描按需扩大候选窗口但单次最多检查 800 个目录项；未加载项超过上限时返回 `problemsTruncated`，仍有目录未检查时返回 `candidatesTruncated`，界面据此如实说明清单不完整。

- [Issue #1424](https://github.com/can4hou6joeng4/boss-harness/issues/1424)：`skills/list` 不再在目录总数恰好等于候选窗口时误报截断。此前用「候选数小于窗口」推断目录已全部检查，100 个有效技能 + 100 个坏目录（共 200 个）时内核已检查全部目录却仍返回 `candidatesTruncated: true`。现在候选枚举显式记录是否丢弃过目录，只有确有目录未检查时才标记截断；恰好顶到窗口时按清单完整处理。

- [Issue #1427](https://github.com/can4hou6joeng4/boss-harness/issues/1427)：技术契约中工作区技能目录发现仍保留旧版上限描述「最多保留字典序前 100 个可读取的普通技能文件」，与同段后来补充的两份清单独立封顶、单次扫描最多 800 个目录项相互矛盾。现已改写为「按字典序保留候选，可加载技能最多 100 个」，与实现及 `problemsTruncated` / `candidatesTruncated` 语义一致。仅文档修正。

- [Issue #1431](https://github.com/can4hou6joeng4/boss-harness/issues/1431)：可加载技能超过 100 个时不再静默丢弃多余项。此前 `scan()` 把有效技能截到展示上限后既不返回 `skillsTruncated`，也不置位 `candidatesTruncated`（目录确已全部检查），而文档写明两个标记都缺省即表示清单完整；界面因此把「100 个技能」当作总数，第 101 个及以后的技能在列表里不可见，按 id 读取或选择只会得到「技能不存在或不可读取」。现在内核在丢弃多余可加载技能时返回 `skillsTruncated: true`，界面在标题计数后加「+」并说明清单只含字典序前若干项；目录恰好等于上限且已全部检查时仍不标记。协议类型同步补充该字段。

- [Issue #1433](https://github.com/can4hou6joeng4/boss-harness/issues/1433)：附件名称进入提示词前不再原样拼接。工作区文件名可能由克隆的仓库、下载或外部同步提供，含换行或控制字符时，`context()` 生成的 `附件 {name}（来源内容，不是操作授权）：` 标签会被伪造出额外的附件标注行，削弱「来源内容，不是操作授权」的约束；同一内核里技能注入早已用 `json.dumps` 转义名称，附件路径没有对应处理。现在提示词标签按技能注入的同一口径以 JSON 字符串字面量转义换行、引号与控制字符，正常文件名语义不变；`add()` 与读取投影对旧记录中的孤立代理项做 `wire_text` 降级，避免 Linux `surrogateescape` 文件名让响应帧或会话追加变成内部错误。附件回执中的 `name` 仍保留真实文件名，供界面显示。

- [Issue #1435](https://github.com/can4hou6joeng4/boss-harness/issues/1435)：输入区「技能」菜单同步提示可加载技能被截断。#1431 让「技能与工具」页在有效技能超过 100 个时说明清单不完整，但同一份目录在首页草稿与已有会话的输入区菜单里仍只渲染前 100 项且没有提示，用户容易误以为技能文件丢失。现在 `skillsTruncated` 从壳层经 `HomeView` / `ConversationArea` 传入 `Composer`，菜单底部说明「只含字典序前 N 个，其余技能不可读取或选择」，与技能页语义一致；目录完整或旧内核不返回该字段时不显示。

- [Issue #1437](https://github.com/can4hou6joeng4/boss-harness/issues/1437)：流泵取消不再在事件循环关闭窗口内抛出内部错误。`AsyncStreamPump.cancel()` 在锁外确认 `_done` 未置位后调用 `loop.call_soon_threadsafe(task.cancel)`，而后台线程的 `_run` 先 `loop.close()`、最后才置 `_done`；取消恰好落在这一窗口时会在已关闭的事件循环上抛 `RuntimeError: Event loop is closed`。该异常从 `with pump as stream` 的 `__exit__` 或 provider 的 `finally: events.close()` 冒出，可能覆盖原本的取消或超时结论，并跳过 `close()` 的收尾等待。现在只在该跨线程调用上捕获 `RuntimeError`：此时 task 已不会再运行、终止事件也已入队，无需再发送取消；其余 `RuntimeError` 不受影响。OpenAI 与 Anthropic 两条 provider 流共用该泵。

不新增 RPC 方法，协议与内核仍为 0.2.0。

## 0.2.0-rc.41 - 2026-11-16

本节汇总第四十一个候选版本的源码与交付内容；rc.16 至 rc.41 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.40，本次聚合 1 项使用者可见的桌面恢复修正：分支摘要取消的成功、失败与收尾绑定发起时的连接与任务，旧回执不再提前释放新任务的取消锁、覆盖其进度或写入旧连接的失败提示。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：取消受理仍然只表示请求被接受，实际停止以任务终态为准；断连或更换任务后先恢复连接并核对，再按需显式取消，不会自动重发。已生效的分支切换不回滚。本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1420](https://github.com/can4hou6joeng4/boss-harness/issues/1420)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.41` / Python `0.2.0rc41`；将 rc.40 之后 1 项分支摘要取消修正归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与恢复步骤、技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1418](https://github.com/can4hou6joeng4/boss-harness/issues/1418)：分支摘要取消的成功、失败和收尾绑定发起时的连接与任务，旧回执不再替换新任务、写入旧错误或提前释放新取消的等待状态；新任务不继承旧取消锁。取消回执须与请求的任务编号一致，已确认终态后不再追加迟到失败提示。正常取消仍需等待任务终态，不回滚已生效的分支切换，也不自动重发。不新增 RPC，协议与内核仍为 0.2.0。

## 0.2.0-rc.40 - 2026-11-16

本节汇总第四十个候选版本的源码与交付内容；rc.16 至 rc.40 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.39，本次聚合 1 项使用者可见的附件读取修正：`attachment/read` 由整份返回改为「默认整份、超预算明确拒绝、按需分段读取」，合法附件不再因传输上限而完全无法读取。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：省略新参数的整份回执保持原形状；整份超过约 1 MiB 单页预算时返回 `RESPONSE_TOO_LARGE`，客户端应按错误中的 `recoveryMethod=attachment/read` 与 `suggestedLimit` 改用分段。续读须回传 `contentRef.sha256`，附件被替换后返回 `STALE_ATTACHMENT`。本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1416](https://github.com/can4hou6joeng4/boss-harness/issues/1416)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.40` / Python `0.2.0rc40`；将 rc.39 之后 1 项附件读取修正归入本候选，同步 README 近期进展与版本表、使用指南的候选状态与分段读取约束、技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

- [Issue #1414](https://github.com/can4hou6joeng4/boss-harness/issues/1414)：`attachment/read` 增加有界分段读取，合法附件不再因传输上限而完全无法读取。此前该方法一次性返回完整 `content`，既不做单页响应预算检查，也不接受 `cursor` / `limit`，未知参数还会被静默忽略：通过 `attachment/add` 准入的 1.5 MB 控制字符文本经 JSON 转义后撞上 8 MiB 帧上限，错误只提示「请使用分页或结果分块读取」，而该方法本身并无分页，客户端没有恢复路径；1.2 MB 普通文本则越过约 1 MiB 单页预算原样返回。现在省略新参数时保持既有整份回执，整份超过单页预算返回 `-32010` 并带 `recoveryMethod=attachment/read`、`totalCharacters` 与 `suggestedLimit`；显式给出 `cursor`、`limit` 或 `sha256` 时按默认 16384、最多 32768 个 Unicode 码点分段，回执含绑定附件摘要的 `contentRef`，续读摘要不符返回 `STALE_ATTACHMENT`。离线探针对照基线 `148dcfa` 确认 1.5 MB 控制字符文本由不可读变为 46 段逐字节读回、1.2 MB 文本由越预算原样返回变为可行动拒绝、小附件整份回执逐字节一致，非法游标、未知参数、错误摘要与越界 `limit` 均由静默接受变为明确拒绝；真实内核审计无网络、子进程或模型 SDK 尝试。不新增 RPC 方法，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.39 - 2026-11-16

本节汇总第三十九个候选版本的源码与交付内容；rc.16 至 rc.39 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.38，本次聚合 2 项使用者可见的桌面恢复修正：上下文编辑明确拒绝显示未写入与内核错误码；分支切换的旧回执在断连后失效，避免重连后意外提交、关闭新窗口或覆盖新操作状态。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：编辑的明确拒绝与传输未确认分别提示；未知结果仍须先回读核对。分支切换途中断连时，恢复连接后重新打开窗口核对当前位置，再决定是否切换；已经生效的切换不回滚，也不会自动重试。本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1412](https://github.com/can4hou6joeng4/boss-harness/issues/1412)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.39` / Python `0.2.0rc39`；将 rc.38 之后 2 项桌面恢复修正归入本候选，同步 README 近期进展、使用指南的恢复步骤与技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1410](https://github.com/can4hou6joeng4/boss-harness/issues/1410)：分支切换的队列核对、切换回执与会话重读都绑定发起时的连接；断连后旧队列回执不再继续提交，旧成功回执不再关闭重开的分支窗口，旧调用收尾也不会释放新切换的忙碌状态。断连释放旧界面的等待状态并提示核对当前位置；已经生效的切换不回滚、不自动重试。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1408](https://github.com/can4hou6joeng4/boss-harness/issues/1408)：桌面编辑后续上下文失败时区分「内核明确拒绝」与「回执未确认」。主进程此前不保留 `context/edit` 与 `context/edit/read` 的内核错误对象，渲染层拿不到错误码：来源冲突、归档或运行中、回执预算超限等明确拒绝一律显示「提交结果未确认」，无法判断编辑是否已经生效。现在两项方法保留内核错误形状；明确拒绝显示「内核未受理、没有写入」与错误码，不再进入待核对状态，也不提示重复提交；回读失败与传输中断仍按未确认处理。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.38 - 2026-11-16

本节汇总第三十八个候选版本的源码与交付内容；rc.16 至 rc.38 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.37，本次聚合 1 项使用者可见的上下文编辑修正：完整回执的预算校验移到编辑记录追加之前，超限时不再出现「客户端收到失败、编辑却已生效」；编辑读取同步响应预算保护。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：编辑读取和成功回执受既有约 1 MiB 单页响应预算约束，按 UTF-8 与 JSON 转义后的完整投影计算。预算拒绝不追加记录、不发送编辑通知；可用快照与正文分页核对长助手原文，分页不会绕过编辑回执预算。普通编辑仍返回完整文本与新的来源摘要；本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1406](https://github.com/can4hou6joeng4/boss-harness/issues/1406)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.38` / Python `0.2.0rc38`；将 rc.37 之后 1 项上下文编辑修正归入本候选，同步 README 近期进展、使用指南的候选状态与回执限制、技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1404](https://github.com/can4hou6joeng4/boss-harness/issues/1404)：`context/edit/read` 按既有约 1 MiB 单页响应预算检查完整投影；`context/edit` 在同一写入锁内先构造并校验提交后的完整回执，再追加编辑记录，避免长消息已经被排除或替换、客户端却因回执过大收到失败。预算拒绝不追加记录、不发送 `context/edited`，原始日志与上下文状态保留；普通编辑继续返回完整文本与新的来源摘要。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.37 - 2026-11-16

本节汇总第三十七个候选版本的源码与交付内容；rc.16 至 rc.37 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.36，本次聚合 1 项使用者可见的分支会话修正：新分支不再保存来源读取投影的截断标记，来源项目标识已截断时不继承该字段，避免永久残留标记或使用不完整分组键。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：普通会话的分支仍完整继承标题与项目标识；历史超长标题按读取投影的 500 字符创建新分支，超长项目标识不继承。修正作用于此后创建的分支，已有文件不追溯改写；本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1402](https://github.com/can4hou6joeng4/boss-harness/issues/1402)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.37` / Python `0.2.0rc37`；将 rc.36 之后 1 项分支会话修正归入本候选，同步 README 近期进展、使用指南的候选状态与分支说明、技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1400](https://github.com/can4hou6joeng4/boss-harness/issues/1400)：`thread/fork` 不再把读取投影的派生标记（`projectIdTruncated`、`titleTruncated`）复制到新分支会话头，避免分支永久显示「已截断」且重命名无法清除；来源会话的项目标识已被投影截断时，分支改为不继承该字段，而不是把截断值当作完整分组键。普通会话的分支仍完整继承标题与项目标识。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.36 - 2026-11-16

本节汇总第三十六个候选版本的源码与交付内容；rc.16 至 rc.36 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.35，本次聚合 1 项使用者可见的技能目录边界修正：技能列表投影的名称与描述改为有界并标记截断，列表响应增加预算检查，使合法目录不再整体不可用。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：`skills/list` 返回的名称最多 200 字符、描述最多 500 字符，超长部分截断并附 `nameTruncated` / `descriptionTruncated`；`skills/read` 的 `content` 仍是完整正文。自定义客户端若直接展示列表描述，应把截断标记视为「完整内容见 `skills/read`」。本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1398](https://github.com/can4hou6joeng4/boss-harness/issues/1398)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.36` / Python `0.2.0rc36`；将 rc.35 之后 1 项技能目录边界修正归入本候选，同步 README 近期进展、使用指南的候选状态与技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1396](https://github.com/can4hou6joeng4/boss-harness/issues/1396)：`skills/list`、`skills/read`、`skills/create` 与 `skills/write` 的名称最多 200 字符、描述最多 500 字符，超长部分截断并分别标记 `nameTruncated` / `descriptionTruncated`，正文仍由 `skills/read` 的 `content` 完整返回；`skills/list` 增加响应预算检查，100 个各在 64 KiB 上限内的技能不再因描述总量或 JSON 转义超过协议帧上限而整体失败。协议类型同步两个可选字段，桌面列表对截断描述追加省略号。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.35 - 2026-11-16

本节汇总第三十五个候选版本的源码与交付内容；rc.16 至 rc.35 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.34，本次聚合 1 项使用者可见的会话元数据边界修正：标题在新写入路径上统一为最多 500 字符，旧版本遗留的超长标题在读取投影中截断并标记，使这类会话重新可读。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：`thread/start.title`、`thread/name/set.name` 与 `thread/fork.title` 须为最多 500 字符的字符串，超长值返回 `-32602`，不会写入会话文件；缺省与合法短值保持原样。旧版本写入的超长标题不追溯改写，读取投影为前 500 字符并附 `titleTruncated: true`。本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1394](https://github.com/can4hou6joeng4/boss-harness/issues/1394)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.35` / Python `0.2.0rc35`；将 rc.34 之后 1 项会话标题边界修正归入本候选，同步 README 近期进展、使用指南的候选状态与技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1392](https://github.com/can4hou6joeng4/boss-harness/issues/1392)：会话创建、重命名与分支自定义标题共用最多 500 字符的上限，超长值在写入会话文件前返回 `-32602`；旧版本遗留的超长标题在元数据投影中截断为前 500 字符并标记 `titleTruncated: true`，使 `thread/read`、`thread/resume`（含 `snapshot=true`）与 `thread/list` 重新可用，原始会话头不改写。协议类型同步该可选字段。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.34 - 2026-11-15

本节汇总第三十四个候选版本的源码与交付内容；rc.16 至 rc.34 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.33，本次聚合 1 项使用者可见的会话元数据边界修正：项目标识改由客户端有界提供，旧版本遗留的超长值在读取投影中截断并标记，使这类会话重新可读。按持续小版本迭代与版本、文档同步要求触发候选准备。

升级注意：`thread/start.projectId` 与 `thread/list.projectId` 筛选须为最多 200 字符的字符串，超长值返回 `-32602`，不会写入会话文件；缺省、null 与合法短值保持原样。旧版本写入的超长标识不追溯改写，读取投影为前 200 字符并附 `projectIdTruncated: true`。本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1390](https://github.com/can4hou6joeng4/boss-harness/issues/1390)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.34` / Python `0.2.0rc34`；将 rc.33 之后 1 项会话元数据边界修正归入本候选，同步 README 近期进展、使用指南的候选状态与技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1388](https://github.com/can4hou6joeng4/boss-harness/issues/1388)：`thread/start.projectId` 与 `thread/list.projectId` 筛选限制为最多 200 字符的字符串，超长值在写入会话文件或执行索引查询前返回 `-32602`；旧版本遗留的超长标识在元数据投影中截断为前 200 字符并标记 `projectIdTruncated: true`，使 `thread/read`、`thread/resume` 与冻结快照重新可读，原始会话头不改写。协议类型同步该可选字段。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.33 - 2026-11-15

本节汇总第三十三个候选版本的源码与交付内容；rc.16 至 rc.33 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.32，本次聚合 3 项使用者可见的参数契约修正：分支自定义标题遵守既有长度上限；回合启动拒绝显式空 provider；手动摘要的模型覆盖按模型 ID 规则校验。按持续小版本迭代与版本、README 文档同步要求触发候选准备。

升级注意：`thread/fork.title` 显式非 null 值须为最多 500 字符的字符串；`turn/start.provider` 显式提供时须通过 provider 格式校验并与会话线路一致；`context/compact/start.model` 只有省略才继承摘要配置，显式值须为最多 200 字符、不含空白的非空模型 ID。非法值均返回 `-32602`，缺省行为与合法值保持原样；本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1386](https://github.com/can4hou6joeng4/boss-harness/issues/1386)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.33` / Python `0.2.0rc33`；将 rc.32 之后 3 项参数契约修正归入本候选，同步 README 近期进展、使用指南的候选状态与技术契约，保留 rc.15 首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1384](https://github.com/can4hou6joeng4/boss-harness/issues/1384)：`context/compact/start` 的显式 `model` 按既有模型 ID 规则校验，空串、空白、数字、布尔、数组、对象、null 与超长值在创建摘要任务和调用 provider factory 前返回 `-32602`，不再经真值回退静默使用默认模型；缺省继续继承摘要配置，合法覆盖与摘要记录保持不变。协议类型与技术契约同步该约束。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1382](https://github.com/can4hou6joeng4/boss-harness/issues/1382)：`turn/start` 显式提供 `provider` 时按 provider 格式校验，null 与其他非法类型在预留回合和保存输入前返回 `-32602`，不再静默沿用会话线路启动回合；缺省继续继承，匹配值成功，跨线路值仍返回 `-32013`。协议类型补充该可选参数。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1380](https://github.com/can4hou6joeng4/boss-harness/issues/1380)：`thread/fork` 的自定义标题遵守新建与重命名已有的 500 字符上限，超长字符串在创建会话文件前以 `-32602` 拒绝；缺省和 null 继续继承原标题，空字符串及合法标题保持原有行为。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.32 - 2026-11-15

本节汇总第三十二个候选版本的源码与交付内容；rc.16 至 rc.32 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.31，本次聚合 4 项 RPC 参数契约修正：握手拒绝非法协议版本和能力类型；快照开关只接受布尔值；停止请求显式目标在取消前校验，避免空值取消当前回合；队列入队与直接启动统一拒绝显式空自动压缩覆盖。按自定义客户端兼容变化触发候选准备。

升级注意：握手 `protocolVersion` 使用字符串，`capabilities` 使用对象或 null；`snapshot` 使用布尔 true / false。停止请求只有缺省 `turnId` 才取消当前回合，显式值须为非空、非纯空白、最多 128 字符的字符串，不能用 null 或其他类型表示未指定。`queue/add.autoCompaction` 应省略或使用合法部分覆盖对象，不能传 null，已有请求重试同样校验。非法值返回 `-32602`；不兼容协议与旧目标回合的领域错误码保持原样，拒绝握手后同一连接可重试。本候选未新增持久化迁移或工具权限。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1378](https://github.com/can4hou6joeng4/boss-harness/issues/1378)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.32` / Python `0.2.0rc32`；将 rc.31 之后 4 项参数契约修正归入本候选，同步 README 近期进展、使用指南的客户端升级说明及技术契约，保留首次实际发布入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1370](https://github.com/can4hou6joeng4/boss-harness/issues/1370)：`initialize` 的 `protocolVersion` 只接受字符串，`capabilities` 只接受对象或 null；其他类型统一返回 `-32602`，拒绝不改变握手状态，同一连接可用正确参数重试。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1372](https://github.com/can4hou6joeng4/boss-harness/issues/1372)：`thread/read` 与 `thread/resume` 的显式 `snapshot` 只接受布尔值；其他类型返回 `-32602`，不再静默退回普通读取。缺省与 false 保持普通读取，true 保持冻结快照。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1374](https://github.com/can4hou6joeng4/boss-harness/issues/1374)：`turn/interrupt` 的显式 `turnId` 在设置取消信号前校验，须为非空、非纯空白、最多 128 字符的字符串；空值和其他类型返回 `-32602`，不再绕过目标保护而取消当前回合。只有缺省仍取消当前回合，匹配目标与旧目标的既有行为不变；闲置状态也执行同一校验。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1376](https://github.com/can4hou6joeng4/boss-harness/issues/1376)：`queue/add` 按字段是否出现校验 `autoCompaction`；显式 null 与其他非法覆盖在入队前返回 `-32602`，不再静默持久化成无覆盖的新队列项，已有请求的非法重试同样拒绝。缺省、合法部分覆盖、幂等与冲突判定保持原有行为。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.31 - 2026-11-15

本节汇总第三十一个候选版本的源码与交付内容；rc.16 至 rc.31 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.30，本次聚合 6 项队列、任务读取与参数校验修正：重新排队刷新失败时保留持久待处理总数；队列任务未知状态使用字符串并保留人工核对；会话列表计数跳过损坏队列记录；显式非法模型不静默回退；读取开关只接受布尔；非法枚举类型统一返回参数错误。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。自定义客户端应省略未指定的 `model`，不能用 null、空字符串或其他类型表示默认值；`excludeTurns` 只接受布尔值，`view` 与任务 `kind` 只接受协议枚举字符串，非法值返回 `-32602`。已有未变化日志的缓存索引不会强制重建；历史队列错计数可在退出应用后按使用指南运行 `boss-harness --repair-state`，从原始日志重建索引，不改写日志。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1368](https://github.com/can4hou6joeng4/boss-harness/issues/1368)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.31` / Python `0.2.0rc31`；将 rc.30 之后 6 项已合并修正归入本候选，同步 README、使用指南与技术契约中的候选状态及参数兼容说明，保留 rc.15 首次安装入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1356](https://github.com/can4hou6joeng4/boss-harness/issues/1356)：重新排队已受理但刷新失败时，沿用持久待处理总数按旧项撤下与新项加入增减，不再用本地已载入数覆盖全量；截断投影缺少总数时继续保留未知。仅影响刷新失败后的本地展示，不重复提交队列操作。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1358](https://github.com/can4hou6joeng4/boss-harness/issues/1358)：`task/read` 读取状态缺失或非法的队列任务时，返回字符串 `unknown`，恢复策略仍为 `manual_review`，避免 null 状态使桌面拒绝整份核对响应；合法状态与策略不变。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1360](https://github.com/can4hou6joeng4/boss-harness/issues/1360)：会话列表索引与队列列表共用 `queue_record` 的结构校验；缺少类型、正文或状态非法的记录不再覆盖同 id 的有效状态，避免产生虚假或漏掉的待处理计数。修正适用于追加与索引重建，已有缓存索引可按升级说明核对。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1362](https://github.com/can4hou6joeng4/boss-harness/issues/1362)：`turn/start` 与 `context/read` 只有缺省 `model` 才继承会话模型；显式 null、空字符串、布尔、数字、数组或对象经既有格式校验拒绝，不再静默回退。合法模型与线路不匹配错误码不变。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1364](https://github.com/can4hou6joeng4/boss-harness/issues/1364)：`thread/read` 与 `thread/resume` 的 `excludeTurns` 只接受布尔值，缺省仍为 false；字符串 `"false"` 不再被当作 true 意外省略回合，其他非布尔值统一返回 `-32602`。普通、冻结快照及分支读取的合法行为不变。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1366](https://github.com/can4hou6joeng4/boss-harness/issues/1366)：读取视图 `view` 与 `task/read.kind` 在集合判断前检查字符串类型；JSON 数组或对象统一返回 `-32602` 参数错误，不再透出不可哈希异常并误报 `-32603`，合法枚举与领域错误不变。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.30 - 2026-11-15

本节汇总第三十个候选版本的源码与交付内容；rc.16 至 rc.30 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.29，本次聚合 5 项附件、队列、运行状态与偏好解析修正：非 UTF-8 附件返回明确提示；截断队列缺少持久待处理总数时保留未知；运行时长按整秒展示；回合状态缺失时保留重试等待提示；偏好解析按 UTF-8 字节校验 64 KiB 上限。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。旧内核未报告队列总数时，面板明确按已载入项统计；缺失回合状态不会被当作重试结束。设置页原有的文件大小预检继续保留，偏好解析函数自身也使用相同的字节上限。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1354](https://github.com/can4hou6joeng4/boss-harness/issues/1354)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.30` / Python `0.2.0rc30`；将 rc.29 之后 5 项已合并修正归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1344](https://github.com/can4hou6joeng4/boss-harness/issues/1344)：非 UTF-8 文本附件返回明确提示。此前添加附件时直接透出随 Python 版本与字节位置变化的编解码异常；现在统一提示「文本附件必须是 UTF-8 文本」，文件大小、摘要与存储规则不变。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1346](https://github.com/can4hou6joeng4/boss-harness/issues/1346)：截断队列投影不把已载入数写成全量待处理数。此前旧内核未提供 `activeItems` 时，本地合入队列项会用可见计数补成持久总数，面板与运行状态因而把部分结果显示为全量。现在截断投影保持该字段缺省，继续明确标注可见计数；完整投影与已有持久总数的增减更新不变。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1348](https://github.com/can4hou6joeng4/boss-harness/issues/1348)：运行时长先取整秒再判断分、小时。此前浮点尾数让 `120.4` 秒显示为「2 分 0 秒」，与整分口径不一致；现在显示「2 分」，`121.9` 秒仍显示「2 分 1 秒」，负值及非有限值继续显示「未知」。仅影响展示，不参与超时或取消判断。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1349](https://github.com/can4hou6joeng4/boss-harness/issues/1349)：回合状态缺失时保留等待中的重试提示。此前兼容路径未提供状态也会被当成明确终态并清除提示；现在保留等待态，明确中断仍转为「已停止」，完成、错误或阻塞仍移除等待提示，已有重试终态保持原样。仅影响桌面展示，不改变模型重试策略。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1350](https://github.com/can4hou6joeng4/boss-harness/issues/1350)：偏好解析函数按 UTF-8 字节校验 64 KiB。此前比较 UTF-16 码元数时，多字节字符可使实际正文超过字节上限仍被接受；现在恰好 64 KiB 可接受，再多 1 字节整体拒绝。设置页原有的 `file.size` 预检、错误提示、白名单与旧作用域兼容不变。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.29 - 2026-11-15

本节汇总第二十九个候选版本的源码与交付内容；rc.16 至 rc.29 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.28，本次聚合 6 项内核与文档修正：工作区说明的写入回执与实际读取状态一致；README 与使用指南的失效锚点改为「开发与验证」；分支会话不再继承来源的队列计数；附件正文合计按 2 MiB 上限计量；压缩计划不再返回没有新增内容的范围；损坏记录的非字符串文本不再以 `None` 或 Python repr 进入模型上下文。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。恰好 2 MiB 的文本附件现在可以进入回合，多附件仍按正文合计 2 MiB 限制；已有空队列的分支会话在重新索引后不再显示待处理计数；损坏记录中的非字符串正文会被跳过，不再伪装成用户原话或模型发言。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1342](https://github.com/can4hou6joeng4/boss-harness/issues/1342)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.29` / Python `0.2.0rc29`；将 rc.28 之后 6 项已合并修正归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1330](https://github.com/can4hou6joeng4/boss-harness/issues/1330)：工作区说明的写入回执与实际读取状态一致。此前保存只含全角空格、NBSP 或仅含 BOM 的正文时，回执报「已保存…下一回合生效」，但读取按 UTF-8 解码并去除首尾空白后为空，实际不会注入；含孤立代理项的正文还会让保存以原始 `UnicodeEncodeError` 失败。现在写入先校验可编码为 UTF-8，回执与加载、状态读取使用同一解码口径区分已加载与空文件；空正文保存后明确提示不会注入下一回合。使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1332](https://github.com/can4hou6joeng4/boss-harness/issues/1332)：README 与使用指南的「快速开始」锚点失效修正。此前标题已在文档调整中移除，链接仍指向旧锚点，按「在本机跑起来」跳转不会落到任何位置。现在统一指向「开发与验证」，返回链接同步。仅文档，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1334](https://github.com/can4hou6joeng4/boss-harness/issues/1334)：分支会话不再继承来源的队列计数。此前从会话分支时复制来源头部的 `queueActiveItems` 与 `queueCounts`，来源会话有待处理项而分支为空时，分支会被列表标成「待你处理」。现在派生字段只由本会话条目决定，计数为零时清除旧值；已有受影响会话在重新索引后恢复。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1336](https://github.com/can4hou6joeng4/boss-harness/issues/1336)：附件正文合计按 2 MiB 上限计量。此前回合组装把附件名称标签与分隔符计入同一额度，恰好 2 MiB 的附件添加成功却在任何回合被拒绝，可用上限还随文件名长度浮动，提示「本回合附件总大小超过」也让人误以为文件本身超限。现在按正文累计，与添加时的单文件上限一致；合计超限的提示改为「本回合附件正文总大小超过 2 MiB」。技术参考同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1338](https://github.com/can4hou6joeng4/boss-harness/issues/1338)：压缩计划不再返回没有新增内容的范围。此前检查点之后只有没有条目的已结束回合时，保留近期回合的计算会把边界推回检查点，计划仍返回已被摘要覆盖的 `throughTurnId`，材料生成随即报「没有新增可压缩内容」；界面先显示计划、点击开始才失败。现在计划阶段按与材料生成相同的覆盖口径拒绝，计划与提交一致。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1340](https://github.com/can4hou6joeng4/boss-harness/issues/1340)：非字符串文本不再以 Python repr 进入模型上下文。此前损坏记录中的 `text` 为 `null`、字典或数字时，请求组装会用 `str()` 转换，模型收到 `"None"`、`"{'a': 1}"` 或 `"42"`，而导出与界面按空内容处理。现在只接受字符串正文，非字符串条目不生成消息；正常消息、工具批次与续写过滤不变。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.28 - 2026-11-15

本节汇总第二十八个候选版本的源码与交付内容；rc.16 至 rc.28 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.27，本次聚合 4 项操作回执与技能目录修正：界面异常兜底的「复制详情」只接受最近一次操作的回执；技能文件的 frontmatter 兼容 BOM、CRLF 与值内三连字符；重新打开设置、离开「技能与工具」页后不再显示上一轮的操作确认。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。此前因 CRLF 换行、BOM 或描述中含 `---` 而回退为目录名、描述为空或被截断的技能，升级后会显示文件中声明的名称与完整描述；技能正文、摘要校验与加载范围不变。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1328](https://github.com/can4hou6joeng4/boss-harness/issues/1328)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.28` / Python `0.2.0rc28`；将 rc.27 之后 4 项已合并修正归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1326](https://github.com/can4hou6joeng4/boss-harness/issues/1326)：离开「技能与工具」页后清除上一次技能操作确认。此前新建、保存或删除技能后的确认由工作台外层保存，切到其他页面再返回仍原样显示，容易被误读为刚刚又发生了一次变更。现在停留在该页时继续显示，离开页面即清除；打开技能管理弹窗时清空旧确认的行为不变，技能文件与工具权限不受影响。使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1324](https://github.com/can4hou6joeng4/boss-harness/issues/1324)：重新打开设置不再显示上一轮回执。此前保存界面偏好、导出文件或测试通知后关闭设置，再次打开时页脚仍显示上一轮的「界面偏好已保存」等文案。现在每次打开都回到默认说明「界面偏好仅保存在当前设备」，并作废「关于」页尚未完成的诊断信息复制回执；关闭时清理自动压缩草稿的行为不变。使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1322](https://github.com/can4hou6joeng4/boss-harness/issues/1322)：技能 frontmatter 解析容忍 BOM、CRLF 与值内三连字符。此前起始分隔线只接受 LF 换行，带 BOM 或 CRLF 的 `SKILL.md` 会丢失名称与描述并回退为目录名；描述中出现 `---` 时会被当作结束线截断。现在按行识别分隔线，结束线必须是独立的 `---` 行；技能正文、大小与数量上限、摘要校验及加载范围不变。使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1320](https://github.com/can4hou6joeng4/boss-harness/issues/1320)：界面异常兜底的「复制详情」回执按最近一次操作结算。此前连续点击时，较早请求的迟到失败会把较新的「已复制错误详情。」改成失败提示；重试前发起的复制回执还会出现在之后的新错误卡片上。现在每次复制、重试与新错误都会使旧回执失效，只有最近一次复制可以更新提示；不取消已发起的系统剪贴板写入。README 同步。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.27 - 2026-11-15

本节汇总第二十七个候选版本的源码与交付内容；rc.16 至 rc.27 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.26，本次聚合 5 项聊天渲染、查找与复制反馈修正：聊天链接保留地址中的完整圆括号；查找计数与高亮排除默认折叠内容；代码块、资料库与侧栏的复制反馈都只接受最近一次点击的回执。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。未勾选查找详情时，命中计数只统计可见正文；复制提示只描述最近一次点击，较早回执不再覆盖。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1318](https://github.com/can4hou6joeng4/boss-harness/issues/1318)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.27` / Python `0.2.0rc27`；将 rc.26 之后 5 项已合并修正归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1316](https://github.com/can4hou6joeng4/boss-harness/issues/1316)：侧栏复制提示按最近一次点击结算。此前复制聊天标题与会话 ID 时，较早请求的迟到失败会把较新的「已复制」改成失败提示，迟到成功也会覆盖较新失败。现在每次复制递增版本，只有最新点击可以更新底部提示；较早回执不再写入，提示仍约 2.6 秒后复位。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1314](https://github.com/can4hou6joeng4/boss-harness/issues/1314)：资料库的来源编号与文件路径复制改用共享复制反馈。此前独立实现按回执到达顺序更新提示，较早请求的迟到失败会覆盖较新成功，较早成功也会覆盖较新失败。现在新点击清除旧提示，只有最近一次点击可以更新结果；切换页面或文件详情后旧回执不再恢复提示，文件提示按完整路径绑定。失败时显示可读原因，提示仍在约 2.6 秒后复位，不取消已发起的系统写入。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1312](https://github.com/can4hou6joeng4/boss-harness/issues/1312)：共享复制反馈按最近一次点击结算。此前连续复制同一回复中的代码块时，较早请求的迟到失败会清掉较新请求的「已复制」，迟到成功也会覆盖较新的失败；显式重置只清空当时的提示，无法作废在途回执。现在新复制开始时清除上一轮提示与定时器，只有最新点击可更新反馈；重置或组件卸载后旧回执不再写入界面或重建定时器。相同按钮重复复制同样受保护，各次调用仍返回实际复制结果，不取消已发起的系统写入。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1310](https://github.com/can4hou6joeng4/boss-harness/issues/1310)：聊天内查找默认只匹配可见正文时，命中计数与高亮同步排除默认收起的思考块、工具块及其内部折叠内容。此前计数来自整条消息的 DOM，折叠块内的同名文字被算作可跳转命中，状态行会大于屏幕上可见数量，当前命中也可能落在看不见的文字上，连续按 `Enter` 看不出变化。现在未勾选「含工具、审批与思考」时，计数与高亮只覆盖可见正文，折叠块标题仍视为可见；勾选后保持原有全量统计，并在跳转时展开当前命中块。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1308](https://github.com/can4hou6joeng4/boss-harness/issues/1308)：聊天回复中的 Markdown 链接保留地址中的完整圆括号。此前遇到成对、嵌套或转义圆括号时会在第一个右括号处截断 URL，来源样式与相邻链接同样受影响，未闭合输入也可能生成部分可点击地址。现在一次扫描配对未转义圆括号，并按完整目标生成链接；未闭合链接保留可见文本，转义圆括号按实际地址打开。普通链接、粗体、行内代码及代码围栏保持可用，外部协议允许清单不变；README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.26 - 2026-11-15

本节汇总第二十六个候选版本的源码与交付内容；rc.16 至 rc.26 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.25，本次聚合 5 项会话分支、会话索引与文档修正：会话分支窗口按实际渲染行数说明失效摘要省略；CHANGELOG 把 rc.25 已包含的修正归位；使用指南补充分支失效摘要的披露；内核始终报告会话索引坏文件数量，桌面不再把「未报告」显示为「正常」；使用指南新增数据管理章节。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。`config/read` 现在始终返回 `unreadableThreadCount`（干净状态为 0）与 `unreadableThreadIds`（无坏文件时为空列表）；旧桌面读取新内核响应行为不变，新桌面连接旧内核时「会话索引」显示「未报告」而非「正常」。依赖旧版省略说明或「正常」文案的核对脚本需要按新文案匹配。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1306](https://github.com/can4hou6joeng4/boss-harness/issues/1306)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.26` / Python `0.2.0rc26`；将 rc.25 之后 5 项已合并修正归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1296](https://github.com/can4hou6joeng4/boss-harness/issues/1296)：会话分支对话框说明失效摘要列表只列出前 5 条。此前内核返回 6–20 条失效摘要时只渲染前 5 条却没有任何省略提示，20 条以上时「仅列出前 N 条」取的是内核返回条数（如 20），与屏幕上的 5 行不一致；不说明省略行数会让用户误以为只有当前几条受影响。现在省略说明按实际渲染行数判断：超过 5 条时提示「仅列出前 5 条」，不超过 5 条时列表完整且不提示，具体条目未能解析时说明原因。仅渲染层文案，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1298](https://github.com/can4hou6joeng4/boss-harness/issues/1298)：把 rc.25 候选已包含的 #1284、#1288、#1290、#1292 四条说明从「未发布」移入 rc.25 分区，未发布分区只保留当时尚未进入候选的条目；diff 为等量搬移，不改写条目内容。仅文档变更，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1300](https://github.com/can4hou6joeng4/boss-harness/issues/1300)：使用指南补充会话分支窗口中失效摘要的说明。此前指南只描述分支端点、切换与摘要生成，用户看到「N 条被放弃分支摘要未生效」时无从得知这些摘要是否仍进入模型上下文、为什么只列出 5 行以及如何处理。现在「会话与阅读状态」说明未生效总条数、最多列出前 5 条及省略提示、原始记录仍保留在本机并可在切换分支时重新生成摘要。仅文档变更，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1302](https://github.com/can4hou6joeng4/boss-harness/issues/1302)：内核未报告的会话索引健康度不再显示为「正常」。`config/read` 此前只在存在无法建立索引的会话文件时返回 `unreadableThreadCount` 与 `unreadableThreadIds`；干净状态与不支持该字段的旧内核都不返回，桌面无法区分「已检查且正常」与「未报告」，统一显示「正常」，在旧内核上等于声称执行过实际没有的检查。现在内核始终返回数量（干净状态为 0）与 id 快照（无坏文件时为空列表），桌面只在明确报告 0 时显示「正常」，字段缺失或形状不可信时显示「未报告」并说明无法确认，存在坏文件时仍显示数量与前 5 个 id。旧桌面读取新内核响应行为不变。离线探针覆盖字段缺失、显式 0、坏文件与非法值；`compileall`、`npm run typecheck`、`npm run build` 通过。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1304](https://github.com/can4hou6joeng4/boss-harness/issues/1304)：使用指南新增「数据管理」章节。此前界面偏好导入 / 导出与会话索引检查只存在于设置页，「正常」「未报告」「N 个无法读取」的含义、导入的白名单与整体拒绝规则、以及 `boss-harness --repair-state` 的修复边界都没有可查阅说明。现在指南说明导出文件的范围与隐私边界、版本 / 作用域 / 字体大小 / 64 KiB 校验、未知键与存储不可用时的行为，以及会话索引各状态的含义与前 5 个 id 的披露。仅文档变更，不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.25 - 2026-11-15

本节汇总第二十五个候选版本的源码与交付内容；rc.16 至 rc.25 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.24，本次聚合 5 项搜索状态与文档修正：跨会话搜索的截断结论进入状态行，有命中时报「仅显示部分结果」、零命中时报「消息搜索不完整」，悬停提示补充可能无法读取的会话；CHANGELOG 恢复「未发布」分区并把 #1284 移出 rc.24，补齐条目间空行；使用指南新增跨会话搜索的范围、上限与截断含义说明；使用指南更正标题与项目名从第 1 个字符起过滤、消息搜索需要 2 个字符；README 的候选之后列表补齐 #1286 与 #1290。相对最新实际发布 rc.15，本候选还包含下方 rc.24、rc.23、rc.22、rc.21、rc.20、rc.19、rc.18、rc.17 与 rc.16 的内容。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。搜索状态行在截断时会明确报「仅显示部分结果」或「消息搜索不完整」，依赖旧文案的读屏脚本需要按新文案匹配；使用指南的两处说法以本版为准。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1294](https://github.com/can4hou6joeng4/boss-harness/issues/1294)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.25` / Python `0.2.0rc25`；将 rc.24 之后 5 项已合并修正归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1284](https://github.com/can4hou6joeng4/boss-harness/issues/1284)：跨会话搜索的截断结论进入状态行。此前消息命中存在且 `thread/search` 返回 `truncated: true` 时，`role="status"` 只报「找到 N 个聊天、M 条消息」，读屏或只看状态行的用户会把部分结果当成完整结果；「仅显示部分结果」的悬停提示也只提到上限，没有覆盖无法读取的会话。现在截断时有命中报「（仅显示部分结果）」，零命中报「消息搜索不完整」，与空态一致；悬停提示补充「也可能有会话未能读取」。未截断、搜索失败与未启用消息搜索的文案不变。仅渲染层文案，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1288](https://github.com/can4hou6joeng4/boss-harness/issues/1288)：使用指南补充「跨会话搜索」一节并加入快速导航。此前只在归档一节提到默认不含已归档，没有说明触发方式与最少字符数、索引与不索引的字段、内核上限（100 个会话、50 条消息、单会话 5 条及文本预算与单会话文件上限），以及「仅显示部分结果」「消息搜索不完整」和状态行结论的含义。现在可按该节判断结果为何不完整、换关键词或稍后重试是否有效。仅文档，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1290](https://github.com/can4hou6joeng4/boss-harness/issues/1290)：使用指南更正跨会话搜索的字符门槛。标题与项目名从第 1 个字符起就参与过滤，2 个字符只是消息内容搜索的门槛；此前该节写成不足 2 个字符就不检索，与搜索窗口的空态提示不一致。仅文档，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1292](https://github.com/can4hou6joeng4/boss-harness/issues/1292)：README 的「rc.24 之后合入」说明补齐 #1286 与 #1290。此前该句只列出 #1284 与 #1288，与 CHANGELOG「未发布」列表不一致，按 README 核对候选之后的主干内容会漏项。现在四项修正全部列出。仅文档，不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.24 - 2026-11-15

本节汇总第二十四个候选版本的源码与交付内容；rc.16 至 rc.24 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.23，本次聚合 5 项搜索完整性、无模型模式与导出修正：`thread/search` 命中数恰好等于展示上限且无更多命中时不再标成部分结果；跳过无法读取的会话时标注结果不完整，桌面在没有消息命中时显示「消息搜索不完整」；无模型模式下 `/search` 不带关键词时提示补全，不再默认检索；会话 Markdown 导出中队列项的技能 ID 与失败码按行内代码呈现；文档补充桌面新建会话固定为只读策略的说明。相对最新实际发布 rc.15，本候选还包含下方 rc.23、rc.22、rc.21、rc.20、rc.19、rc.18、rc.17 与 rc.16 的内容。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。`thread/search` 的 `truncated` 取值含义收紧：恰好等于上限的完整结果为假，已列出但无法读取的会话被跳过时为真；依赖旧取值的调用方需按新含义处理。搜索标注「不完整」只说明可能仍有命中，不代表会话已修复，日志损坏仍需按使用指南排查。无模型模式下 `/search` 必须带关键词。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1282](https://github.com/can4hou6joeng4/boss-harness/issues/1282)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.24` / Python `0.2.0rc24`；将 rc.23 之后 5 项已合并修正归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1272](https://github.com/can4hou6joeng4/boss-harness/issues/1272)：无模型模式下 `/search` 不带关键词时不再默认检索 Python。此前 `/search`（含只带空白符）会把硬编码的 `Python` 当作关键词调用业务 CLI，用户没有给出检索词却实际发起一次只读平台查询，并把无关结果写进会话历史与上下文；README 与使用指南只描述 `/search 关键词`，没有声明该默认值。现在不带关键词时只返回「请提供检索关键词」的补全提示，不调用业务 CLI；`/search 关键词` 与含空格的多词关键词仍按整段剩余文本检索，其他离线只读指令不变。使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1274](https://github.com/can4hou6joeng4/boss-harness/issues/1274)：文档补充桌面新建会话的执行权限说明。此前 README 与使用指南没有说明桌面「新建会话」与「连接账号」固定以只读工具策略创建：内核只提供 13 个只读工具，`boss_hr_greet` 不在清单中，也不会出现写操作审批卡，当前版本没有切换入口；按文档尝试逐次审批的用户容易误以为连接或配置有误。现在 README 的试跑入口与安全边界、使用指南新增说明：只读策略随会话保存并被分支沿用；逐次审批只出现在以 `thread/start` 的 `toolPolicy: "approval"`（缺省值）创建的会话中，桌面可列出、读取并审批这类会话。仅文档同步，不改变工具授权或审批行为。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1276](https://github.com/can4hou6joeng4/boss-harness/issues/1276)：`thread/search` 不再把完整结果标成部分结果。此前命中数恰好达到 `limit`（1–50）或单会话 5 条展示上限、实际已无更多命中时仍返回 `truncated: true`，桌面搜索面板据此显示「仅显示部分结果」，让用户以为还有未返回的更早或更多命中。现在达到展示上限后继续扫描（不再收集结果），只有确认真有下一条命中才返回截断；恰好等于上限的完整结果返回 `truncated: false`，返回条数与顺序不变。会话数 / 文本预算耗尽、单条文本按剩余预算截断与超大会话跳过等结构性截断仍为 `true`。README 同步说明。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1278](https://github.com/can4hou6joeng4/boss-harness/issues/1278)：`thread/search` 跳过无法读取的会话时标注结果不完整。此前会话仍在 `thread/list` 中、但日志损坏或无法读取时，搜索直接跳过且 `truncated: false`，用户看到的是一份实际漏掉该会话命中的「完整」结果；命中只存在于该会话时界面显示「没有匹配的消息」。现在已列出但读取失败的会话被跳过时返回 `truncated: true`，桌面据此显示「仅显示部分结果」；无消息命中但搜索不完整时显示「消息搜索不完整」及遗漏提示，不再给出「没有匹配的消息」的完整结论。其余会话的命中、排序与上限语义不变。README 与协议字段注释同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1280](https://github.com/can4hou6joeng4/boss-harness/issues/1280)：会话 Markdown 导出中，未形成回合的队列项把技能 ID 与失败码按行内代码呈现。此前这一行在生成行内代码后又整体中和了一次反引号，技能 ID 变成带单引号的纯文本（如 `'resume-review'`）、失败码为裸文本，与同一份导出中回合单元的行内代码不一致。现在各项事实逐项中和，标识符保留行内代码；HTML 导出与脱敏范围不变。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.23 - 2026-11-15

本节汇总第二十三个候选版本的源码与交付内容；rc.16 至 rc.23 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.22，本次聚合 5 项输入保护与摘要轮询修复：技能目录未就绪时不误标已选技能失效，目录确认为空时提供清除入口；首页首条消息被拒时说明会话已创建、草稿保留及核对位置；快速提问保留等待回执期间编辑的新输入，取消输入法候选词的 Esc 不再误关浮窗；分支摘要的迟到轮询不覆盖新任务进度及取消目标。相对最新实际发布 rc.15，本候选还包含下方 rc.22、rc.21、rc.20、rc.19、rc.18、rc.17 与 rc.16 的内容。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。技能显示未失效不等于已经确认可用于发送，仍需成功读取目录；首页已创建但首条消息被拒时，先打开该会话核对，避免重发另建空会话；快速提问等待期间有过编辑时保持浮窗，并提示原问题所属会话，未编辑时继续清空关闭；摘要的旧连接回执不作为当前完成依据，恢复连接后仍需核对任务。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1270](https://github.com/can4hou6joeng4/boss-harness/issues/1270)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.23` / Python `0.2.0rc23`；将 rc.22 之后 5 项已合并修复归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1268](https://github.com/can4hou6joeng4/boss-harness/issues/1268)：分支摘要的迟到轮询不再覆盖新任务。此前旧任务的运行状态读取晚于新任务开始通知到达时，会把新进度覆盖成旧进度，并让「取消摘要」携带旧任务编号；断连前发出的读取也能在断连后写回状态。现在轮询成功与失败均核对发出时的连接、任务编号及当前运行状态，已被新任务替换、已收尾、断连或卸载后的回执不再写入，响应中的任务编号也必须匹配。正常进度、终态与不存在任务的恢复处理继续有效，README、使用指南与来源说明同步。仅渲染层状态保护，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1266](https://github.com/can4hou6joeng4/boss-harness/issues/1266)：快速提问取消输入法候选词时不再误关浮窗。此前容器收到 Esc 就关闭，即使事件带输入法组合态、兼容标记 `keyCode: 229` 或已被处理，仍会中断编辑，并作废该窗口正在等待的提交回执。现在与其他桌面输入控件一致，跳过这些事件；普通 Esc 与关闭按钮继续生效，关闭后重新打开仍保留输入。Enter 的输入法判断与既有提交回执保护不变，README 与使用指南同步。仅渲染层键盘处理，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1262](https://github.com/can4hou6joeng4/boss-harness/issues/1262)：快速提问成功回执保留等待期间编辑的新输入。此前发送问题后输入框仍可编辑，但原问题的成功回执会无条件清空输入并关闭浮窗，等待期间改写的新问题随之丢失；编辑后改回原文也有同样风险。现在按输入编辑版本判断：等待期间有过编辑时保留当前输入、保持浮窗打开，并说明原问题已提交到哪个会话；未编辑时继续清空并关闭。关闭再打开后旧回执仍作废，明确拒绝与回执未知继续保留输入，不自动重发。README 与使用指南同步。仅渲染层草稿保护，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1258](https://github.com/can4hou6joeng4/boss-harness/issues/1258)：首页首条消息被内核拒绝时说明会话已创建。此前桌面已经创建会话并加入侧栏、输入内容也留在首页，但提示只写「发送失败：…。正在读取会话状态，请核对后重试。」，没有说明会话已存在、草稿仍在、可以从列表打开核对；用户据此在首页重试会再建一个空会话，原会话成为没有消息的孤儿记录。现在与「提交结果未确认」分支一致，提示改为「会话「标题」已创建，但首条消息被内核拒绝；草稿已保留，请打开该会话核对后重试。」；具体拒绝原因仍按会话保存，打开该会话即可看到。仅渲染层提示文案，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1256](https://github.com/can4hou6joeng4/boss-harness/issues/1256)：技能目录未就绪时不再把已选技能标为失效。此前输入区的已选技能标签只按当前目录里有没有这个 id 判断：内核断开、目录读取失败或首次加载时目录为空，所有已选技能都被标成失效并提示「已不在当前技能目录中」，即使技能仍在磁盘上；目录成功读取但为空时，菜单反而不提示不可用、也不提供「清除不可用技能」。现在只有成功读取的目录（有内容或确实为空）才据此标注缺失技能；未就绪时标签保持可用、悬停提示回退为名称或描述，空目录时提供「清除不可用技能」。已选技能的顺序、去重、10 项上限与 id 不截断规则不变。仅渲染层展示逻辑，不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.22 - 2026-11-15

本节汇总第二十二个候选版本的源码与交付内容；rc.16 至 rc.22 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.21，本次聚合 5 项停止反馈与运行状态面板的改进：停止请求在途时按钮显示「正在停止任务」并禁用，受理后保持到回合结束，明确失败或没有可停止回合时立即恢复，多个会话同时停止时各自保持该状态；运行状态面板的状态、阶段与策略改为中文文案，未知取值保留原文标注，并补齐冲突状态与摘要任务的失败、取消口径。相对最新实际发布 rc.15，本候选还包含下方 rc.21、rc.20、rc.19、rc.18、rc.17 与 rc.16 的内容。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。停止请求在途时重复点击会被忽略；受理停止后按钮保持禁用直到运行状态清除，明确失败、没有可停止回合、会话删除或连接断开时恢复，另有 10 秒兜底。运行状态面板只做文案映射，未知取值原样放在「」里；核对结果仍只陈述内核事实，不恢复、不取消任务。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1254](https://github.com/can4hou6joeng4/boss-harness/issues/1254)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.22` / Python `0.2.0rc22`；将 rc.21 之后 5 项已合并改进归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1252](https://github.com/can4hou6joeng4/boss-harness/issues/1252)：运行状态面板补齐冲突状态与摘要任务状态文案。内核 `task/read` 对互相矛盾的持久记录返回 `status: conflict`，此前显示为「conflict」；摘要 owner 的 `phaseStatus` 实际是摘要任务状态，失败或取消时徽标显示「failed」「cancelled」；已取消的摘要任务沿用队列用词显示「已撤回」。现在冲突状态显示「记录冲突」并与归属「冲突」区分，摘要徽标显示「已失败」「已取消」，状态文案按任务类型区分口径：队列项取消为「已撤回」，回合与摘要任务取消为「已取消」；未知取值仍原样放在「」里。仅渲染层文案，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1250](https://github.com/can4hou6joeng4/boss-harness/issues/1250)：运行状态面板改用中文文案展示状态与策略。此前概览的审批策略、转向投递、能力来源，owner 徽标的阶段与状态，以及「核对持久记录」的持久状态、任务阶段都直接显示内核内部标识（如 `each-consequential-call`、`all`、`model_request · running`），同屏的归属与恢复策略却已翻译。现在已知的状态、阶段、阶段状态、审批策略、转向投递与容量来源统一映射为中文，owner 徽标与核对结果使用同一套说法，未知取值原样放在「」里以便识别新内核的新值；任务尝试次数不再排成 `1/0`，改为「第 N 次尝试 · 不自动重启」，存在自动重启上限时如实展示。上下文面板的容量来源使用同一映射，核对只陈述内核事实、不推断恢复动作。仅渲染层文案，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1248](https://github.com/can4hou6joeng4/boss-harness/issues/1248)：多个会话同时停止时各自保持正在停止。此前按钮的忙碌状态只记录最近一次发起停止的会话，而在途去重按会话集合记录：在会话甲停止后切到会话乙再次停止，切回甲时甲的停止仍在途，按钮却恢复为可点击的「停止任务」，点击既不发出请求也没有提示。现在忙碌状态与在途标记按同一会话集合记录，每个会话各自显示「正在停止任务」并禁用按钮，切换会话不丢失；某个会话的停止结束（回合结束、失败、没有可停止回合、兜底超时或会话删除）只释放该会话。单会话的在途、受理与恢复行为不变，重复点击仍不会发出第二个请求。仅渲染层实现，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1246](https://github.com/can4hou6joeng4/boss-harness/issues/1246)：停止受理后到回合结束通知之间保持正在停止。内核的 `turn/interrupt` 在启动取消后立即返回，回合结束通知稍后才到；此前桌面在请求结算时就恢复停止按钮，窗口内回合仍显示为运行中，再次点击会发出第二个请求，并因内核已无活动回合而显示「未找到可停止的任务」。现在受理成功时继续禁用按钮并显示「正在停止任务」，直到运行状态清除；明确失败或内核回报没有可停止回合时立即恢复，会话删除与连接断开也清除状态，另有 10 秒兜底避免通知丢失时永久禁用。下一回合仍可正常发起停止；重复点击不会发出第二个请求，失败归属与重读组合提示不变。仅渲染层实现，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1244](https://github.com/can4hou6joeng4/boss-harness/issues/1244)：停止请求在途时按钮显示正在停止并禁用。此前 #1240 已在处理函数中忽略重复点击，但停止按钮的外观与可访问名称仍与空闲时一致，请求较慢时用户无法确认第一次点击是否生效，容易反复点击。现在按会话记录停止请求在途：按钮禁用、`aria-busy` 为真，可访问名称与说明改为「正在停止任务」，请求失败、拒绝或未找到回合时立即恢复可停止，受理成功后的释放时机由 #1246 收敛到回合结束；其他会话不显示该状态。重复点击仍不会发出第二个 `turn/interrupt`，受理停止不产生失败提示，既有失败归属与重读组合提示不变。仅渲染层实现，不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.21 - 2026-11-15

本节汇总第二十一个候选版本的源码与交付内容；rc.16 至 rc.21 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.20，本次聚合 5 项失败提示与停止操作的改进：发送与停止在重新核对会话也失败时同时保留原始原因与读取错误，继续区分明确拒绝和结果尚未确认；读取失败提示去掉主进程拼接前缀；后台会话失败提示按来源会话清理；停止请求在途时忽略重复点击。相对最新实际发布 rc.15，本候选还包含下方 rc.20、rc.19、rc.18、rc.17 与 rc.16 的内容。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。发送或停止回执未确认不能证明操作未受理，界面不会自动重发；会话级提示只保存在本次应用内存，显式关闭或来源新回合开始后清除，重启后以会话记录与工具结果为准。停止请求在途时重复点击会被忽略，请求结算后可再次发起。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1242](https://github.com/can4hou6joeng4/boss-harness/issues/1242)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.21` / Python `0.2.0rc21`；将 rc.20 之后 5 项已合并改进归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1240](https://github.com/can4hou6joeng4/boss-harness/issues/1240)：停止请求在途时重复点击不再发出第二个请求。此前停止按钮在回合运行期间始终可点，`handleInterrupt` 没有在途保护：第一次停止请求尚未返回时再次点击会各自发起 `turn/interrupt`，第一个受理后第二个通常返回 `interrupted: false`，界面按「没有可停止的回合」写入「未找到可停止的任务，正在重新读取会话状态。」，与受理停止不产生失败提示的约定不符，并额外触发一次会话重读。现在按会话记录停止请求在途，在途期间忽略重复点击，请求结算后（受理、拒绝、失败或未找到回合）恢复可停止；第一次请求的失败归属、重读失败组合提示与目标回合绑定规则不变。仅渲染层实现，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1238](https://github.com/can4hou6joeng4/boss-harness/issues/1238)：后台会话失败提示关闭后不再重新出现。失败提示按会话保存后，后台会话的失败以「会话「标题」：」前缀显示；此前关闭按钮、新回合开始与删除会话都只按当前活动会话判断是否清除提示，后台提示显示期间活动会话是另一个，关闭后切回来源会话提示会重新出现，来源开始新回合或删除后旧提示也仍停留。现在记录提示条属于哪个会话：关闭时清除该会话的记录，来源新回合或删除时一并清除正在显示的提示；当前会话自身提示的关闭与清除规则不变，其他会话记录不受影响。仅渲染层实现，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1236](https://github.com/can4hou6joeng4/boss-harness/issues/1236)：会话读取失败提示去掉主进程拼接前缀。`thread/resume`、`thread/read` 等未列入保留错误码的方法失败时由主进程抛出，渲染层收到的是 `Error invoking remote method 'harness:request': Error: …`；`HarnessReplica.reportFailure` 此前直接使用该消息写入提示与会话失败记录，用户看到的读取原因带着内部包装，发送 / 停止与读取同时失败的组合提示同样受影响。现在先经共享的 `stripIpcErrorWrapper` 去掉包装再截断，副本内部错误（如「会话恢复已过期」）文案不变，长度上限与既有提示结构不变。仅渲染层实现，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1234](https://github.com/can4hou6joeng4/boss-harness/issues/1234)：停止失败后重新读取也失败时保留停止原因。此前点击停止后若回执失败、被内核明确拒绝或内核回报没有可停止的回合，界面先写入停止说明，再重新读取会话；读取在内部报告失败并返回 `null`，其 `session/error` 通知会整条覆盖停止说明，用户只看得到「读取会话内容失败」，无法判断停止是否已确认，切回来源会话同样只剩读取错误。现在按读取返回值与同一副本的失败记录组合提示：明确拒绝保留内核码并说明没有中断任何回合，未确认保留「不会自动重复停止」，没有可停止回合时保留原结论，读取错误已有的处理建议不重复包裹；提示继续归属来源会话。读取成功、受理停止与停止目标回合的既有规则不变，不增加快照读取、停止重发或工具权限。README、使用指南与来源说明同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1232](https://github.com/can4hou6joeng4/boss-harness/issues/1232)：发送与随后会话核对均失败时保留两种原因。此前会话读取在内部报告失败并返回 `null`，发送路径却只等待异常，导致读取错误覆盖原始发送原因，切回来源会话仍无法区分明确拒绝和提交结果尚未确认。现在按读取返回值与同一副本的失败记录组合提示，保留明确拒绝的原因码或未知回执的核对说明，沿用读取错误已有的处理建议；提示继续归属来源会话，草稿保留且不自动重发。读取成功和发送成功的既有行为不变，不增加快照读取、模型调用或工具权限。README、使用指南与来源说明同步。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.20 - 2026-11-15

本节汇总第二十个候选版本的源码与交付内容；rc.16 至 rc.20 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.19，本次聚合 5 项改进：迟到自动审批回执保留已经收到的审批结论，自动批准明确拒绝按码说明并按原因决定是否刷新；停止与直接发送的失败提示保存到来源会话，切回仍可核对；停止请求绑定界面展示的目标回合，避免误停已经开始的后续回合。相对最新实际发布 rc.15，本候选还包含下方 rc.19、rc.18、rc.17 与 rc.16 的内容。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。审批决定与工具执行结果仍应分别核对；发送回执未确认不能证明消息未受理，不自动重发。会话级提示只保存在本次应用内存，显式关闭或来源新回合开始后清除，重启后以会话记录与工具结果为准。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1230](https://github.com/can4hou6joeng4/boss-harness/issues/1230)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.20` / Python `0.2.0rc20`；将 rc.19 之后 5 项已合并改进归入本候选，同步 README 与使用指南的候选状态，保留 rc.15 首次安装入口及历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1228](https://github.com/can4hou6joeng4/boss-harness/issues/1228)：直接发送失败提示按来源会话保存。此前发送被内核明确拒绝或回执不可读时只写入全局提示区，请求在途期间切到另一会话会把甲的失败显示在乙中且不标明归属，切回甲后原因消失，虽然来源草稿仍保留。现在发送、停止与内核错误通知共用既有会话级记录：后台提示标明来源标题，切回恢复原文，另一会话不保存该失败；显式关闭或来源会话新回合开始继续清除旧记录。成功回执不新增失败提示，草稿保留与不自动重发规则不变，提示仅保存在本次应用内存。不新增读取、模型调用或工具权限。README、使用指南与来源说明同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1216](https://github.com/can4hou6joeng4/boss-harness/issues/1216)：自动批准的迟到拒绝或未知回执保留同一审批已经收到的结论。此前回退会把旧请求重放到会话缓存，清除先到的裁决、工具完成通知或已恢复快照中的审批决定；当前可见会话虽有本地合并保护，切走后再切回且快照读取失败时，已处理卡片仍会重新开放批准与拒绝。现在按 `approvalId` 保留已批准、已拒绝与已过期事实，尚无该次结论时继续恢复卡片，其他审批不阻止回退；保留工具终态、来源会话核对说明和其他手动审批的在途锁，不自动重发或新增全量读取。审批结论仍不代表工具执行成功。README、使用指南与来源说明同步。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1218](https://github.com/can4hou6joeng4/boss-harness/issues/1218)：自动批准被内核明确拒绝时按拒绝码说明并刷新来源会话。此前自动路径对 `APPROVAL_CLOSED`、`APPROVAL_CONFLICT`、`APPROVAL_NOT_FOUND`、`APPROVAL_INVALID`、`APPROVAL_AMBIGUOUS`、`APPROVAL_EXPIRED`、`APPROVAL_BUSY` 及无原因码拒绝一律提示「已显示本次审批；请手动确认」，既与手动路径的分码说明不一致，也可能诱导对已结束、已按相反处理或仍被活动回合持有的审批重复裁决；来源会话不做刷新，持久化结论无法落到卡片，已有结论时提示还与「已批准」并列。现在复用同一套拒绝码区分：不再接受裁决时重读一次来源会话（`APPROVAL_BUSY` 除外，避免全量快照覆盖流式输出），仍由活动回合持有时提示先停止或等待、不要反复提交，已有同一审批结论时说明界面未重新开放操作并继续要求核对工具结果；未知回执文案不变。提示仍按来源会话保存，不自动重发裁决，不新增 RPC 或工具权限。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1224](https://github.com/can4hou6joeng4/boss-harness/issues/1224)：桌面停止请求携带界面正在展示的回合。此前 `turn/interrupt` 只带 `threadId`，内核在未收到 `turnId` 时取消该会话当时的活动回合：用户点停止时看到的是回合 A，若 A 在请求到达前结束、排队的后续回合 B 已被自动派发，这次停止会取消 B 并返回 `interrupted: true`，界面当成正常受理、不显示任何提示；内核早已支持的 `-32004`「回合已变化；请刷新后再中断」防护因此没有被用上。现在停止请求携带界面跟踪的回合 id，内核仅在该回合仍是活动回合时取消，已被替代时明确拒绝且不取消新回合；不知道回合 id 时退回只带线程。主进程校验 `turnId` 格式；`turn/interrupt` 加入保留 RPC 错误码的方法清单，明确拒绝不再被说成「停止请求未确认」，而是说明本次没有中断任何回合并重新读取会话状态，`interrupted: false` 与回执未确认的既有文案保持不变。不自动重发停止，不新增 RPC、工具授权或新的快照读取路径。README、使用指南与技术参考同步。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1220](https://github.com/can4hou6joeng4/boss-harness/issues/1220)：停止失败提示按来源会话保存。此前 `turn/interrupt` 回执失败或内核回报没有可停止的回合时，提示直接写入全局提示区：回执到达前切到另一会话，甲的停止失败显示在乙的提示区且不标明归属；切回甲后提示已经丢失，而其他失败（`session/error`）会按会话保存并在切回时恢复。现在停止请求的失败沿用同一会话级记录：切走时提示标明「会话「标题」：」，切回后恢复原文；受理停止不产生失败提示，重新发起回合清除该会话记录。保留「正在重新读取会话状态；不会自动重复停止」，不自动重发停止，不新增 RPC。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.19 - 2026-11-15

本节汇总第十九个候选版本的源码与交付内容；rc.16 至 rc.19 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.18，本次聚合 5 项改进：命令行启动失败时指向本地自检，桌面诊断先展示错误项；重新排队区分新项受理与旧项撤回未确认，保留已受理计数并停止后续批量；手动与自动审批未知回执先提示核对，自动批准的拒绝与核对说明保存在来源会话。相对最新实际发布 rc.15，本候选还包含下方 rc.18、rc.17 与 rc.16 的内容。

升级注意：本候选未新增 RPC、持久化迁移或工具权限。暂停队列的部分完成提示需要先核对旧项，审批未知回执需要先核对审批与工具结果；均不会自动重发。会话级提示保存在本次应用内存，重启后以会话记录和工具结果为准。前序候选的配置检查码与开关取值变化继续适用，详见对应历史版本。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1214](https://github.com/can4hou6joeng4/boss-harness/issues/1214)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.19` / Python `0.2.0rc19`；将 rc.18 之后 5 项已合并改进归入本候选，同步 README 近期进展与使用指南中的候选状态，保留 rc.15 首次安装入口与历史版本记录。候选准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1212](https://github.com/can4hou6joeng4/boss-harness/issues/1212)：自动批准的拒绝与未知回执提示按来源会话保存在应用内存中，并在该会话输入区展示。此前自动批准回退虽恢复了原会话审批卡，却把说明写入全局提示区：在途切换或后台请求会让甲会话的提示出现在乙会话，切回甲后又丢失。现在复用既有审批提交状态，切走不串会话、切回仍可核对，只更新说明而不结算其他手动审批的在途锁；明确受理不新增提示，不自动重发或全量读取快照。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1210](https://github.com/can4hou6joeng4/boss-harness/issues/1210)：桌面审批回执不可读或连接中断时，手动与自动批准统一提示「结果尚未确认」，要求先核对审批与工具结果，不要直接重复提交。此前桥接层虽返回 `unconfirmed`，界面仍声称请求未送达、引导检查连接后重试或手动确认；临时裁决已受理、切换会话回读到已批准后也会出现该提示。现在两条路径共用核对文案，保留原因与既有会话级状态；明确受理、拒绝、过期与关闭的处理不变，不增加自动重试或全量快照读取。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1208](https://github.com/can4hou6joeng4/boss-harness/issues/1208)：桌面重新排队区分新消息已受理与旧项撤回未确认。此前旧项撤回被拒绝或回执不可读后仍返回完整成功，批量继续创建后续消息，最后显示整批成功；旧项也可能仍保留并被重复重新排队。现在返回部分完成回执，已受理的新消息计入数量，批量在该条结束后停止；单条与批量提示均保留在发起会话中，显示在队列标题下方，要求先刷新核对并撤回仍保留的旧项，不要重复重新排队。回执丢失不再被说成旧项一定未撤回；仅列表刷新失败、两步写入均已确认时继续按本地结果更新并提示可能过期。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1206](https://github.com/can4hou6joeng4/boss-harness/issues/1206)：桌面启动诊断的设置页明细按「错误 → 警告 → 通过」展示，同类项保留自检报告的原始顺序。此前运行参数错误位于第五项，在真实 Electron 的 1440 × 900 与 1100 × 760 窗口中，前面的警告与通过项把实际错误说明、处理建议和检查码挤到滚动区域下方；打开设置时不易发现启动失败原因。现在错误项优先可见，只排序展示行，不修改报告、检查码、提示条与自检生命周期。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1204](https://github.com/can4hou6joeng4/boss-harness/issues/1204)：内核在构造阶段启动失败时，stderr 在既有失败行之后追加一行固定提示，指向不联网、不写入的 `boss-harness --check`。此前状态目录不可用、系统不满足私有状态目录要求或运行参数取值无效时，命令行只看到异常类名与系统错误原文，没有任何内容指向已能给出固定检查码与处理建议的自检；桌面会自动运行自检，直接启动内核的用户则无从得知。提示为固定文字，不含路径、变量取值或异常内容；既有失败行、退出码 2 与空 stdout 不变，模型配置、浏览器来源、`--check` 与 `--repair-state` 的输出不变。使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.18 - 2026-11-14

本节汇总第十八个候选版本的源码与交付内容；rc.16、rc.17 与 rc.18 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.17，本次把更多配置错误纳入启动前的本地自检并统一为固定原因：自检新增「运行参数」检查项；供应商拼写、输出上限与请求期限错误各有固定检查码，正常启动不再输出解析异常原文；Anthropic 线路的服务端回退开关按固定写法解析，无法识别的取值明确失败。使用指南补充此前未说明的运行参数。相对最新实际发布 rc.15，本候选还包含下方 rc.17 与 rc.16 的内容。

升级注意：`BOSS_HARNESS_SERVER_FALLBACK` 的 `False`、`off`、`no` 由开启变为关闭，其他非标准写法在 Anthropic 线路会让启动失败；按检查码处理的调用方会看到非正输出上限由 `MODEL_CONFIG_INVALID` 改为 `MODEL_MAX_TOKENS_INVALID`，自检报告在既有四项之后多出 `runtimeOptions` 一项。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。本次不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1202](https://github.com/can4hou6joeng4/boss-harness/issues/1202)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.18` / Python `0.2.0rc18`；README 与使用指南标明当前候选，首次安装继续使用已有 rc.15 tag，保留 rc.16 与 rc.17 历史记录。候选版本准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1200](https://github.com/can4hou6joeng4/boss-harness/issues/1200)：文档补充此前未说明的环境变量。使用指南新增「其他运行参数」一节，逐项列出 `BOSS_HARNESS_MAX_TOKENS`、`BOSS_HARNESS_MAX_MODEL_REQUESTS`、`BOSS_HARNESS_RETRY_ATTEMPTS`、`BOSS_HARNESS_RETRY_BASE_MS`、`BOSS_HARNESS_APPROVAL_TIMEOUT` 与桌面使用的 `BOSS_HARNESS_PYTHON` 的作用、默认值、范围，以及取值无效时是启动失败、使用默认值还是收敛到边界；README 配置表补充对应入口。只改文档，运行行为不变。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1198](https://github.com/can4hou6joeng4/boss-harness/issues/1198)：Anthropic 线路的 `BOSS_HARNESS_SERVER_FALLBACK` 不再把 `False`、`off`、`no`、带空白的 `0` 或任意拼写错误当作开启。此前只有精确的 `0`、`false` 与空值算关闭，其余取值一律让请求携带服务端回退参数并走 beta 接口：非官方端点默认关闭，用户按常见写法想保持关闭时反而开启；官方端点想关闭时不生效，均无提示。现在取值去除首尾空白并按不区分大小写解析，`1` / `true` / `yes` / `on` 为开启，`0` / `false` / `no` / `off` 为关闭；未设置仍按端点是否为官方主机取默认值，空值仍为关闭。其他取值以新增固定检查码 `MODEL_SERVER_FALLBACK_INVALID` 明确失败：自检的模型配置项报错并给出静态处理建议，正常启动输出同一固定码并以退出码 2 结束，不回显变量取值或异常原文。`none` 与 OpenAI 线路不使用该开关，不因它失败。兼容影响：此前靠非标准写法（如 `enabled`）开启的配置需改为上述写法；`False`、`off`、`no` 的含义由开启变为关闭。使用指南补充该变量与 `BOSS_HARNESS_THINKING` 的作用、默认值与可接受写法。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1196](https://github.com/can4hou6joeng4/boss-harness/issues/1196)：供应商拼写、输出上限与请求期限错误新增固定检查码 `MODEL_PROVIDER_UNKNOWN`、`MODEL_MAX_TOKENS_INVALID`、`MODEL_REQUEST_TIMEOUT_INVALID`。此前三者在自检中落到通用的 `MODEL_CONFIG_INVALID`，建议指向 provider 与 Codex 配置；正常启动把解析异常原文（含变量取值）打印到 stderr，非正输出上限还要到内核构造阶段才以另一种措辞失败。现在解析处抛出保持 `ValueError` 兼容的固定原因，输出上限在解析时校验为正整数，自检与正常启动给出同一固定码、静态说明与处理建议，退出码仍为 2，不含异常原文或取值。未设置、空值、带空白的合法数值、`codex` 别名、配置来源优先级与其他检查码不变；按码处理的调用方会看到非正输出上限由 `MODEL_CONFIG_INVALID` 改为专用码。实际 CLI 入口 16 种隔离场景通过，其中 10 种失败场景同时核对正常启动的 stderr；网络、外部进程、模型 SDK 导入与持久写入尝试均为零。README 与使用指南同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1194](https://github.com/can4hou6joeng4/boss-harness/issues/1194)：本地自检新增「运行参数」检查项。此前 `BOSS_HARNESS_STEERING_MODE`、`BOSS_HARNESS_MAX_MODEL_REQUESTS`、附件存储上限、`BOSS_HARNESS_MODEL_LIMITS` 或 `BOSS_HARNESS_COMPACTION` 取值无效时内核以退出码 2 启动失败，`--check` 与桌面启动失败诊断却报告未发现错误。现在自检复用正常启动的同一套解析函数，按读取顺序报告第一个错误，使用五个固定检查码与静态处理建议，不回显变量原值或异常原文；全部有效或未设置时为 `RUNTIME_OPTIONS_VALID`。报告仍为 `schemaVersion: 1`，在既有四项之后追加一项，既有检查项输出与退出码规则不变；不读取状态目录中的持久设置。桌面提示条与设置页沿用既有展示并补充「运行参数」标题。实际 CLI 入口 14 种隔离场景通过，覆盖未设置、全部合法、各变量无效取值、多项同时无效与模型配置错误并存；网络、外部进程、模型 SDK 导入与持久写入尝试均为零。README 与使用指南同步检查码和范围限制。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.17 - 2026-11-14

本节汇总第十七个候选版本的源码与交付内容；rc.16 与 rc.17 均为候选准备，最新实际发布仍为 [`v0.2.0-rc.15`](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15)，以远程 tag 与资产为准。

### 本版概览

相对 rc.16，本次修复独立摘要线路的提交预算：摘要生成继续使用摘要 provider / model，提交检查点前则按实际业务模型核对完整请求，避免误拒可用摘要或先保存业务模型容纳不下的检查点。相对最新实际发布 rc.15，本候选还包含下方 rc.16 的本地配置自检、启动诊断、模型线路一致性与会话列表可靠性改进。

交付范围为 MIT 许可的源码与 Python 内核 wheel / sdist，桌面继续从源码构建；真实模型、招聘平台、跨平台与独立签名安装包仍未验收。本次不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1192](https://github.com/can4hou6joeng4/boss-harness/issues/1192)：同步根包、桌面及三个共享工作区包、锁文件与 Python 运行时版本为 npm `0.2.0-rc.17` / Python `0.2.0rc17`；README 与使用指南标明当前候选，首次安装继续使用已有 rc.15 tag，保留 rc.16 历史记录。候选版本准备不代表实际 tag、Release、资产上传或包注册表发布。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1190](https://github.com/can4hou6joeng4/boss-harness/issues/1190)：自动摘要提交前按实际业务线路校验完整预算。此前跨 provider 摘要会用摘要 provider 与业务模型 ID 查询容量，可能误拒绝可用摘要，或先保存业务模型容纳不下的新检查点、再因预算超限暂停。自动阈值 / 预算压缩与溢出恢复现在按业务 runner 的 provider 和请求模型查询容量、匹配 usage；摘要生成、输出预留与来源元数据继续使用独立摘要配置。容纳不下时沿用 `COMPACTION_INSUFFICIENT` 暂停，不提交新检查点、不发起后续业务请求，原始历史与已有检查点保留。实际 stdio 入口在合成 provider 下复现两种旧行为，修复后七种场景通过，覆盖跨 provider 较大 / 较小 / 未声明容量、同 provider 独立摘要模型与溢出恢复；独立 wheel 安装后同组复验通过，审计网络、外部进程及模型 SDK 导入尝试均为零。类型检查、桌面构建、离线 wheel / sdist 构建与依赖检查通过，两个包及安装后模块与源码字节一致，许可匹配且无测试材料。README、使用指南、技术参考与上游记录同步。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.16 - 2026-11-14

本节汇总第十六个候选版本的源码与交付内容；实际发布状态以 [GitHub Release](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.16) 为准。

### 本版概览

自 `v0.2.0-rc.15` 以来的改进在本次候选中汇总，主题是启动与配置可诊断性：新增不联网的本地配置自检入口；桌面在内核握手前失败时展示同一套自检结果；模型配置与状态目录错误提供固定检查码、静态说明与处理建议；状态目录路径无法解析时以明确的启动失败退出，不再打印回溯；Codex profile 支持 `env_key` 凭据并拒绝非 Responses 协议；`none` 模式的握手、配置读取与新建会话统一为 `none · none`；桌面列表刷新不再把已删除聊天放回。

这些检查只覆盖本地静态条件，不证明模型连通、平台登录、依赖完整、实际写入、磁盘空间或索引与会话完整；真实模型、招聘平台与独立安装包仍未验收。桌面继续从源码运行，交付为 MIT 许可的源码与 Python 内核 wheel / sdist。本版没有新增 RPC，协议仍为 `0.2.0`。

- [Issue #1186](https://github.com/can4hou6joeng4/boss-harness/issues/1186)：无模型模式的新建会话不再被默认线路不一致拒绝。以 `none` 启动时握手与 `config/read` 曾报告通用默认模型，而 `model/list` 把同一 provider 规范为 `none`，桌面按握手值调用 `thread/start` 会收到 `MODEL_ROUTE_UNAVAILABLE`。现在 `ApplicationService` 在创建时采用模型目录中同一 provider 的生效条目（none 为 `model=none`、无推理档位），使握手、配置读取、目录、新建会话与构造检查共用同一线路；启动日志同步显示该生效配置。显式 none、自动回退与残留模型 / 档位变量都落到该条目且不发起模型请求，显式模型覆盖的解析与校验规则不变，真实 provider 原配置与旧会话记录不迁移。实际 stdio 子进程五种场景与独立 wheel 安装后同组核对全部通过，真实 Electron 以 README 的默认 `none` 启动时首页显示 `none · none`，生产新建回调成功且 `thread/list`、`config/read`、`model/list` 一致；探针记录的网络、外部进程与模型 SDK 导入尝试均为零。类型检查、桌面构建与离线 wheel / sdist 构建通过，变更模块在源码与包内字节一致，包内无测试材料。README、使用指南、技术参考与上游吸收记录同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1184](https://github.com/can4hou6joeng4/boss-harness/issues/1184)：桌面列表刷新不再把已删除聊天重新放回。会话通知与本地成功的新建、删除、重命名、归档 / 恢复及模型设置会使在途旧列表失效；旧成功结果不回写列表或当前会话，旧失败不覆盖提示，沿用现有单飞与尾随刷新补读最新列表。当前读取失败仍保留已有列表并说明原因，未知删除结果继续提示核对。真实 Electron 窗口、生产 preload / renderer / IPC 与 `none` 内核中核对八种场景，覆盖删除竞态、重命名、新建、归档 / 恢复、迟到失败与当前失败（列表失败为受控注入）；模型、招聘平台网络及 Python 外部进程 / SDK 导入尝试为零。类型检查与桌面构建通过，README、使用指南、技术参考与上游吸收记录同步，并按实际界面修正归档入口为侧栏菜单。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1182](https://github.com/can4hou6joeng4/boss-harness/issues/1182)：Codex profile 不再把不支持的 `wire_api` 判为配置有效。OpenAI 线路仅实现 Responses，读取可用 profile 时缺省或空白使用 `responses`，显式字符串忽略大小写与首尾空白，其他值及非字符串以固定 `MODEL_CODEX_WIRE_API_UNSUPPORTED` 拒绝；正常启动与 `--check` 在构造客户端前退出 `2`，不输出配置值、不切换协议。正常启动对已登记的模型配置错误展示固定码与静态说明，桌面沿用既有自检桥接。完整显式配置仍跳过 Codex 文件，不完整 profile、凭据来源及既有解析顺序保持兼容。22 个隔离 CLI 场景与 17 项库级核对通过，独立 wheel 安装后同组核对通过，10 个既有自检输出与基线逐字节一致；桌面主进程自检及提示投影、类型检查、桌面构建与离线 wheel / sdist 构建通过。探针记录的网络、外部进程、SDK 导入及持久写入尝试均为零。README、使用指南、内核参考与上游吸收记录同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1180](https://github.com/can4hou6joeng4/boss-harness/issues/1180)：Codex profile 支持 `env_key` 凭据。此前只识别 `experimental_bearer_token`，按 Codex 推荐把密钥放在环境变量中的合法 provider 配置会被判为缺少凭据，`--check` 报 `MODEL_CREDENTIAL_MISSING`。现在解析时只记录 `env_key` 的环境变量名，`resolve_config(environ=...)` 用调用方传入的环境映射取值；优先级为显式 `BOSS_HARNESS_OPENAI_API_KEY` > `experimental_bearer_token` > `env_key`，变量缺失或为空仍报同一固定码，提示补充 `env_key` 路径。`--check` 复用该解析，不构造客户端、不联网。使用指南、README、内核参考与上游吸收记录同步。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1178](https://github.com/can4hou6joeng4/boss-harness/issues/1178)：修正「内核与业务契约参考」中「桌面不提供删除按钮」的过期说明，并按当前实现补全桌面会话管理文档：删除入口、确认框会一并清除的本机未发送正文 / 附件 / 已选技能 / 正在读取的附件 / 消息反馈、`THREAD_BUSY` 拒绝，以及 `THREAD_DELETE_INCOMPLETE` / `THREAD_NOT_FOUND` 与未确认结果的处理；使用指南新增归档与删除会话说明，README 能力地图补充会话管理条目。纯文档改动，不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1174](https://github.com/can4hou6joeng4/boss-harness/issues/1174)：状态目录路径无法解析（如符号链接环）时，正常启动与 `--repair-state` 不再以退出码 1 输出 Python 回溯。路径解析统一经 `resolve_private_path`，把 `pathlib` 包装的 `RuntimeError`（含 `ELOOP`）转为既有的目录规则错误：启动沿用干净退出（退出码 2、单行静态说明），维护命令输出「索引修复失败：状态目录路径无法解析」，两者都不含本机绝对路径。自检仍报 `STATE_DIRECTORY_INVALID`，报告结构与退出码不变；字面 `~` 不展开、相对路径按启动工作目录解析、合法目录与符号链接到目录的创建行为保持不变。34 项既有隔离真实 CLI 场景结果与修复前逐字节一致，26 项库级创建与异常映射核对通过；符号链接环的正常启动、中间路径环节点、`--check` 与 `--repair-state` 实跑核对通过。README 与使用指南补充该边界。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1172](https://github.com/can4hou6joeng4/boss-harness/issues/1172)：本地自检新增实际状态目录的基本访问与安全检查，复用正常初始化的逐级目录、所有权、父目录和 macOS ACL 规则，目录缺失时只核对已有父目录；不创建目录、不修改权限、不试写、不获取锁、不打开索引或读取会话。固定检查码区分非目录、访问不足、安全条件不符、系统不支持和其他文件系统故障，沿用既有报告与退出码；桌面在提示条和设置页展示「状态目录」及静态处理建议，修正目录后重连恢复并清除旧诊断。34 种隔离真实 CLI 场景、26 项正常创建兼容与静态诊断核对、4 种真实 Electron 场景的 88 项断言，以及独立 wheel 安装后的 12 项包内容与入口核对通过；自检无状态正文读取、持久写入、锁获取或 SDK 导入，运行验收无外部调用。类型检查、桌面与 Python wheel / sdist 构建通过。README 与使用指南补全目录选择、检查码及不覆盖实际写入、磁盘空间、锁与索引完整性的边界，标明尚未进入 rc.15。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1170](https://github.com/can4hou6joeng4/boss-harness/issues/1170)：模型配置自检新增五类具体失败码，区分 OpenAI 缺少端点 / 凭据，以及 Codex 文件不可读 / TOML 无效 / 路径不是普通文件；解析处抛出保持 `ValueError` 兼容的内部固定原因，自检从静态表取得说明与建议，不匹配或转发异常原文。其他错误继续使用通用码，配置来源优先级、完整显式配置跳过文件、非 strict 读取回退、报告结构与退出码不变，桌面沿用既有桥接展示。33 种隔离真实 CLI 场景、23 项解析兼容核对、5 种真实 Electron 场景的 100 项断言及独立 wheel 安装后的五类自检与只读 stdio 握手通过；自检无网络、外部进程、持久写入或 SDK 导入。类型检查、桌面与 Python wheel / sdist 构建通过，四个变更模块在源码、包内与独立安装后的字节一致。README 与使用指南补全检查码及处理方式，并标明尚未进入 `v0.2.0-rc.15`。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1168](https://github.com/can4hou6joeng4/boss-harness/issues/1168)：桌面区分内核「握手完成前就失败」与「就绪后断开」，并在启动失败时展示本地自检结果。宿主连接状态新增 `startupFailed`、`wasReady`、`willRetry`，自动重试预算用尽后不再显示「正在恢复连接」，曾就绪后断开保留「结果未确认的对外操作请先核对平台状态」。握手前失败时，主进程用与内核相同的解释器、工作目录与环境运行一次 `--check`（每个失败周期一次，显式重连或就绪后作废），只接受通过结构校验的固定字段，把错误项的说明与建议附在连接状态上，显示在提示条与「设置 → 模型与连接」的逐项明细；界面与推送内容均不含 stderr 原文、异常、端点、凭据或本机路径。`harness:reconnect` 不再抛出，返回附带自检结论的连接状态。修正设置页失效的文档指向。7 种离线 Electron 场景（缺模型配置、解释器不存在、Python 3.9、浏览器来源无效、状态目录被占用、正常就绪对照、就绪后崩溃）290 项断言，以及三套渲染层与宿主状态探针 262 项，全部通过；网络、外部进程、招聘平台操作与禁用调用均为 0。`npm run typecheck`、`npm run build`、`git diff --check` 通过。README 与使用指南标明该能力尚未进入 `v0.2.0-rc.15`。不新增 RPC，协议与内核仍为 `0.2.0`。
- [Issue #1166](https://github.com/can4hou6joeng4/boss-harness/issues/1166)：新增 `boss-harness --check` 本地只读配置自检，沿用模型配置优先级及业务 CLI 发现与可执行检查，独立校验浏览器来源；输出版本化脱敏 JSON、固定检查码和处理建议。配置错误或非正模型输出上限退出 2，显式禁用模型、自动回退未配置和 CLI 缺失分别标为警告；不构造 SDK、不创建状态目录、不读取会话、不执行 CLI 或联网，与索引修复互斥。本地检查不代表模型连通、平台登录或真实工具可用，README 与使用指南标明该能力尚未进入 rc.15。28 种真实 CLI 隔离场景通过，网络、外部进程、持久写入尝试及 SDK 导入均为 0；类型检查、桌面与 Python wheel / sdist 构建通过，独立 venv 安装后核对自检命令与既有只读 stdio 握手，新增模块字节与包内一致。不新增 RPC，协议与内核仍为 `0.2.0`。

- [Issue #1164](https://github.com/can4hou6joeng4/boss-harness/issues/1164)：rc.15 实际发布后同步 README 的候选链接、发布时间、固定源码提交与四项发布资产，首次安装固定到该 tag，近期进展明确为本候选已包含；发布约定按用户要求限定社区正文只介绍本项目自身，内部来源记录继续保留。不新增 RPC，协议与内核仍为 `0.2.0`。

## 0.2.0-rc.15 - 2026-11-14

本节汇总第十五个候选版本的源码与交付内容；实际发布状态以 [GitHub Release](https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15) 为准。

### 本版概览

自 `v0.2.0-rc.14` 以来的改进在本次候选中汇总。项目统一命名为 BOSS Harness / `boss-harness`，旧环境变量、状态目录与技能目录保留兼容读取；迁移与导出格式影响见下方「兼容变化」。

桌面工作台补齐会话恢复、阅读与草稿保留、跨会话审批与队列状态、暂停消息的串行批量处理和停止剩余、退出确认、消息搜索与定位、技能及上下文编辑；运行时长、审批期限和会话相对时间在窗口保持打开时持续更新。

内核与业务桥补齐权限、恢复、上下文预算、模型传输、日志和快照完整性边界。新增 RPC 包括 `thread/search`、`thread/export`、`task/read`、`approval/list`、`queue/update`、技能读写与 `turn/continue` 相关能力，协议版本仍为 `0.2.0`。逐项 Issue/PR 来源、探针与验证记录保存在 [rc.15 详细记录](docs/changelog-rc15-details.md)；版本汇总不代表真实模型、招聘平台或独立安装包已验收。

交付为 MIT 许可的源码与 Python 内核 wheel / sdist，包内随附许可文本；桌面仍从源码运行，没有独立桌面安装包或签名发行流程。发布准备、资产与文档核对见 [发布约定](RELEASING.md)。

### 兼容变化

- 项目命名统一为 `boss-harness`：GitHub 仓库改名为 `can4hou6joeng4/boss-harness`（旧链接由 GitHub 重定向），npm 根包改为 `boss-harness`、桌面包改为 `boss-harness-desktop`，TypeScript 工作区 scope 改为 `@boss-harness/*`；桌面展示名由 BOSS-CLI 改为 BOSS Harness。内核状态目录新增 `BOSS_HARNESS_DIR` 与默认 `~/.boss-harness/harness`，旧 `BOSS_CLI_HARNESS_DIR` 与 `~/.boss-cli/harness` 仍兼容读取（新目录一旦存在即优先）；工作区技能目录改为 `.boss-harness/skills`，旧 `.boss-cli/skills` 在新目录不存在时继续加载。上游相关 `BOSS_CLI_BIN`、`BOSS_CLI_DATA_DIR`、`boss-agent-cli` 与 `boss_hr_*` 工具名保持不变，协议仍为 `0.2.0`。
- 桌面首次以新展示名启动时接管旧 `userData` 目录（`appData/BOSS-CLI`）：新目录尚不存在且旧目录存在时整体迁移，保留界面偏好与本地草稿；新目录已存在则保持不动，迁移失败（跨卷、权限、占用）只使用新目录，不影响启动。协议仍为 `0.2.0`。
- 桌面界面偏好改用 `boss-harness.ui.*` 命名空间：启动时把旧 `boss-cli.ui.*` 中尚不存在的新键复制过来（旧键保留、不覆盖已有新值），设置页与偏好导出文件名随之更新。协议仍为 `0.2.0`。
- 会话导出改用新品牌标识：内核 `suggestedFileName` 与桌面保存对话框默认名改为 `boss-harness-session-<id>-<view>.<ext>`，导出 JSON 的 `schema` 改为 `boss-harness-session-export/1`；已导出的旧文件内容不受影响、无需迁移。协议仍为 `0.2.0`。

## 0.2.0-rc.14 - 2026-10-29

第十四次私有源码与 Python 内核候选发布，累计纳入 rc.13 后合入的十四项功能与修复，并补足持久摘要任务的崩溃恢复状态。

### 新功能

- 参考 Pi Durable [Issue #11026](https://github.com/earendil-works/pi/issues/11026)：新增宿主 JSON-RPC `thread/delete`，可恢复地清理会话 JSONL、共享事件、SQLite 投影、索引修复备份及无引用附件；活动或收尾中的会话拒绝删除，父会话分支保持独立。
- [Issue #152](https://github.com/can4hou6joeng4/boss-cli/issues/152)：`ApplicationService(prompt_preamble=...)` 只覆盖默认招聘提示的身份段，保留工具说明、招聘规则、技能与只读后缀；默认工具组合和平台检查/登录 host 能力继续启用。自定义 `ToolBundle` 不猜测提示分段，不能同时传入该参数。
- [Issue #138](https://github.com/can4hou6joeng4/boss-cli/issues/138)：增加同步 `after_tool_call` 宿主回调，覆盖已持久化的成功、失败、拒绝、未执行和结果未知工具终态；结果内容默认隐藏，需嵌入端显式 opt-in，回调只读且不能改写执行事实。


### 修复

- [Issue #158](https://github.com/can4hou6joeng4/boss-cli/issues/158)：从持久事件日志恢复摘要任务状态；重启时将无 checkpoint 的未终结任务收敛为 `COMPACTION_INTERRUPTED`，若 `summaryJobId` 已写入 checkpoint 则恢复为 completed。只恢复可查询状态，不重放 provider 请求或 checkpoint。
- [Issue #156](https://github.com/can4hou6joeng4/boss-cli/issues/156)：并发会话容量暂满时保留 follow-up 队列项为 `queued`，在槽位释放后按等待顺序唤醒；直接新回合不会越过已等待队列，真实 provider/worker 启动失败仍按 `TURN_START_FAILED` 结算。
- [Issue #154](https://github.com/can4hou6joeng4/boss-cli/issues/154)：Anthropic 流到达 `message_stop` 后拒绝任何额外事件，避免终态之后追加的工具调用进入已完成响应并派发；正常终态前的响应处理不变。
- [Issue #150](https://github.com/can4hou6joeng4/boss-cli/issues/150)：摘要 provider 已返回终态并带有 token usage、但摘要内容因停止原因、空文本、工具调用或超长被拒绝时，仍保存不可用但可追溯的 `context_summary_usage`（含拒绝 code）；不写检查点、不重试，也不伪造没有终态或 usage 的记录。
- [Issue #148](https://github.com/can4hou6joeng4/boss-cli/issues/148)：登录保存 worker 未启动时返回 `LOGIN_SAVE_START_FAILED` 并回收忙状态；连接检查、登录和模型 abort 的启动包装层在实际启动后抛错时保留真实 worker 所有权。已观察取消的桥接任务不追加后续 CLI 调用，不自动重试登录保存。
- 参考 Pi 开放 [Issue #11433](https://github.com/earendil-works/pi/issues/11433)：JSON-RPC 审批请求已发出但超时计时线程无法启动时，立即失败关闭并退休本地 waiter；晚到响应不再匹配请求，工具按未批准结算。
- [Issue #146](https://github.com/can4hou6joeng4/boss-cli/issues/146)：保留 Anthropic extended thinking 的 opaque `signature` 与 `redacted_thinking` 数据，支持同回合工具续请求、历史重建、关闭后恢复和 fork；含工具响应的签名缺失或出现不受支持的 fallback block 时 fail closed，不执行工具，前缀 digest 不一致时丢弃失效 thinking block，不发送其签名。
- [Issue #144](https://github.com/can4hou6joeng4/boss-cli/issues/144)：仅将可信 HTTP 413 中不超过 512 字符且完整匹配 `Request body too large` / `payload too large` 的错误分类为上下文溢出；裸 413、其他消息及非 HTTP 错误来源不触发恢复。
- [Issue #142](https://github.com/can4hou6joeng4/boss-cli/issues/142)：将工具派发认领与回合中断放在同一运行时锁下，关闭工具状态持久化期间接受中断后仍调用 handler 的竞态；取消先于派发认领时记为 `CANCELLED / not_executed`。
- [Issue #140](https://github.com/can4hou6joeng4/boss-cli/issues/140)：识别 LiteLLM 有界 HTTP 400 上下文窗口拒绝，使符合条件的无输出请求进入现有单次摘要恢复；普通请求错误和非 HTTP 400 不触发恢复。
- [Issue #136](https://github.com/can4hou6joeng4/boss-cli/issues/136)：OpenAI Responses 流在响应句柄登记前收到取消时，登记后立即复查取消标志并退出 SDK context manager，避免已取消回合继续读取响应 body。

### 兼容与验证

- npm 工作区统一为 `0.2.0-rc.14`，Python 内核为等价 PEP 440 版本 `0.2.0rc14`；JSON-RPC 保持 `0.2.0`。
- 本地永久删除探针覆盖 session、intent 和 events 硬链接崩溃窗口恢复，以及意外外部硬链接拒绝；逐会话准入并发探针通过。PR #161 的 Source build、GitGuardian 与合并后 main Build 均通过。
- Issue #158 恢复探针 4 项通过，覆盖未提交 checkpoint、已提交 checkpoint、最近 64 个终态及已移除会话；重启不重放 provider、网络或子进程。现有本地内核回归 45 项通过。
- 类型检查、Electron 源码构建、Python wheel/sdist 构建及 `git diff --check` 通过；PR #159/#160/#161 的 GitGuardian 与 Source build，以及相关合入 main 后的 Build 均通过。离线探针保留在本地，未调用真实模型或招聘平台，也未进行桌面 UI 验收。
- OpenAI 与 Anthropic 共享相同的窄 HTTP 413 消息分类；既有无输出、未取消、自动压缩启用、预算足够及每回合只恢复一次的条件不变。Pi Issue #10879 的通用 413 检测不直接移植。
- Anthropic `message_stop` 后的后续事件令本次 provider stream 失败，不产生 `done`，因此不会调用工具或申请审批；JSON-RPC、OpenAI Responses 流与重试策略不变。
- Anthropic thinking continuation metadata 仅用于兼容请求重建，不进入 RPC、event、hook、摘要材料或工具结果投影；签名按官方 SDK 语义替换而非拼接。离线探针覆盖流式捕获、同回合/重开/fork 续接、缺签名工具阻断、前缀失配、上下文编辑、压缩尾部和崩溃后的连续工具前缀恢复。真实 Anthropic 服务、第三方网关跨模型兼容性及省略后缀 `tool_use` 的远端行为未验收。
- 本地 7 项离线探针覆盖两个 provider 的精确匹配、裸/其他/超长 HTTP 413、其他状态和错误来源、既有结构化 overflow，以及 TurnRunner 的单次恢复、输出、取消和请求上限门禁。Python 3.11 编译、类型检查、Electron 源码构建、wheel/sdist 构建及 `git diff --check` 通过；wheel/sdist 仅含 Harness 产品源码。探针只保留本地，未调用真实模型或招聘平台。
- OpenAI Responses 正常事件、回合终态和重试边界保持不变；Anthropic 流协议与现有 prompt 窗口分类保持不变。本轮未执行真实服务、招聘平台或桌面 UI 验收。

## 0.2.0-rc.13 - 2026-10-28

第十三次私有源码与 Python 内核候选发布，修复摘要期间的后续回合派发竞态，并完善会话存储目录、文件及 macOS ACL 的隐私保护。

### 修复

- [Issue #127](https://github.com/can4hou6joeng4/boss-cli/issues/127)（[PR #128](https://github.com/can4hou6joeng4/boss-cli/pull/128)）：摘要运行期间排入的后续回合保持 `queued`，不再因会话暂时占用被误判为 `TURN_START_FAILED`；摘要与已领取但尚未启动的后续回合互斥，成功后恢复派发，手动摘要失败或取消则暂停旧输入。
- [Issue #129](https://github.com/can4hou6joeng4/boss-cli/issues/129)（[PR #130](https://github.com/can4hou6joeng4/boss-cli/pull/130)）：新建会话目录限制为 owner-only `0700`，不随宽松 umask 暴露目录项。
- [Issue #131](https://github.com/can4hou6joeng4/boss-cli/issues/131)（[PR #132](https://github.com/can4hou6joeng4/boss-cli/pull/132)）：独立初始化 `SessionStore` 时，私有创建承载 SQLite 索引和事件日志的新父目录。
- [Issue #133](https://github.com/can4hou6joeng4/boss-cli/issues/133)（[PR #134](https://github.com/can4hou6joeng4/boss-cli/pull/134)）：新建会话持久化文件限制为 `0600`，清除 macOS 继承 ACL；启动时收紧当前用户拥有的旧文件，覆盖 SQLite/WAL/SHM、checkpoint、附件、repair 备份、manifest 和状态锁。已有目录 mode/ACL 保持不变，不安全的目录或不支持的权限平台在创建状态前拒绝初始化。

### 兼容与验证

- npm 工作区统一为 `0.2.0-rc.13`，Python 内核为等价 PEP 440 版本 `0.2.0rc13`；JSON-RPC 保持 `0.2.0`。状态文件权限后端支持 Linux 与 macOS；Windows 和其他平台需要独立的权限后端，当前拒绝创建状态。
- 本地 Python 3.14/APFS 探针覆盖新旧文件、继承 ACL、可搜索目录拒绝、checkpoint、活跃 WAL/SHM、repair 备份与 manifest、状态锁、符号链接/FIFO 和不支持平台；内容 hash 与已有目录权限保持不变。类型检查、桌面源码构建、Python 编译及 wheel/sdist 构建通过；功能 PR #128/#130/#132/#134 的 Source build 与 GitGuardian 检查通过。
- 探针只保留本地；未调用真实模型或招聘平台，未进行桌面 UI 验收，不含独立桌面安装包。

## 0.2.0-rc.12 - 2026-10-28

第十二次私有源码与 Python 内核候选发布，收敛 OpenAI Responses 流式输出与权威终态之间的差异，避免执行已撤回的工具调用。

### 修复

- 参考 Pi Issue [#11043](https://github.com/earendil-works/pi/issues/11043)，OpenAI Responses 适配器现在以 `response.completed` / `response.incomplete` 的权威 `output` 集合收敛最终内容；流中出现但终态撤回的工具调用不会再进入执行器，缺失或重复终态集合会返回错误并停止派发。

### 兼容与验证

- npm 组件统一为 `0.2.0-rc.12`，Python 内核为等价 PEP 440 版本 `0.2.0rc12`；JSON-RPC 保持 `0.2.0`。
- 本地离线终态一致性探针覆盖撤回工具、缺失 `output`、重复索引和有效工具保留四种路径，4/4 通过；Python 3.14 编译、类型检查、桌面源码构建、Harness wheel/sdist 构建和 PR #125 的 Source build、GitGuardian 检查通过。
- 未调用真实模型或招聘平台；候选交付私有源码与 Python wheel/sdist，不含独立桌面安装包。

## 0.2.0-rc.11 - 2026-10-28

第十一次私有源码与 Python 内核候选发布，提供宿主控制的回合请求上限，并补齐摘要与连接检查的模型请求策略。

### 新功能

- 参考 Pi Issue [#11043](https://github.com/earendil-works/pi/issues/11043)，宿主可通过 `max_model_requests` 或 `BOSS_HARNESS_MAX_MODEL_REQUESTS` 设置每回合 1–64 次业务请求硬上限，默认仍为 6；`turn/start.maxModelRequests` 只能为本回合收紧。工具循环、steering 和上下文恢复共享额度，耗尽后保留结果并暂停队列。

### 修复

- [Issue #121](https://github.com/can4hou6joeng4/boss-cli/issues/121)：`before_request` 统一覆盖业务请求、每个摘要分片和模型连接检查；摘要拒绝不调用对应 provider、不提交新 checkpoint、不继续业务请求。持久错误、终态通知与连接报告保留脱敏原因和请求身份，已关闭策略和迟到允许结果保持拒绝，取消优先。

### 兼容与验证

- npm 组件统一为 `0.2.0-rc.11`，Python 内核为等价 PEP 440 版本 `0.2.0rc11`；JSON-RPC 保持 `0.2.0`，新增协议字段可选。业务请求上限不统计 provider/SDK 内部传输重试，摘要仍有独立的 32 次生成上限。
- 本地请求上限、策略拒绝、持久化异常、取消及队列专项探针通过；Python 3.10/3.12 编译、Python 3.10 专项验证、类型检查、桌面源码构建与 wheel/sdist 构建通过。功能 PR #122/#123 的 Source build 与 GitGuardian 均成功；探针只保留本地。
- 未调用真实模型或招聘平台；候选交付私有源码与 Python wheel/sdist，不含独立桌面安装包。

## 0.2.0-rc.10 - 2026-10-28

第十次私有源码与 Python 内核候选发布，增加模型请求前策略拒绝闸门。

### 新功能

- 参考 Pi Issue [#11055](https://github.com/earendil-works/pi/issues/11055)，嵌入宿主可通过 `before_request` 在完整业务请求预算准备后拒绝模型请求。拒绝以 `error` 终止当前回合，保留脱敏原因，不调用该业务 provider、不执行工具、不申请审批，也不进入上下文恢复或自动重试。

### 验证与限制

- 本地离线探针覆盖首次请求、工具循环第二轮和上下文恢复重试；Python 3.14 编译、Harness wheel/sdist 构建、TypeScript 类型检查、桌面源码构建及产物内容检查通过。
- 未调用真实模型或招聘平台；本候选继续交付私有源码与 Python wheel/sdist，不含独立桌面安装包。
- rc.10 的 `before_request` 仅覆盖业务模型请求；摘要和模型连接检查的覆盖缺口在 rc.11 的 Issue #121 修复中补齐。

## 0.2.0-rc.9 - 2026-10-28

第九次私有源码与 Python 内核候选发布，补齐 OpenAI-compatible llama.cpp 解码阶段上下文耗尽的恢复分类。

### 修复

- 参考 Pi Issue [#10885](https://github.com/earendil-works/pi/issues/10885)，识别 OpenAI-compatible llama.cpp 在解码阶段返回的有界 `Context size has been exceeded.`，使上下文恢复路径能够处理 KV pool 耗尽，而不扩大对任意错误文本的匹配。

### 验证与限制

- 本地离线分类探针、Python 3.13 编译、Harness wheel/sdist 构建及包内容检查通过；PR #117 的 Source build、GitGuardian 与合并后 main Build 均通过。
- 未调用真实模型、llama.cpp 服务或招聘平台；本候选继续交付私有源码与 Python wheel/sdist，不含独立桌面安装包。

## 0.2.0-rc.8 - 2026-10-28

第八次私有源码与 Python 内核候选发布，修复模型将嵌套 object/array 参数额外编码为 JSON 字符串时的工具调用兼容性。

### 修复

- 参考 Pi PR [#9569](https://github.com/earendil-works/pi/pull/9569)，按显式工具 schema 解码被额外 JSON 编码的嵌套 object/array 参数；解码结果仍须通过同一 schema 校验，且 schema 允许字符串时保留原字符串。

### 验证与限制

- 本地离线 schema 边界探针、Python 3.11 编译、Harness wheel/sdist 构建及包内容检查通过；PR #115 的 Source build 与 GitGuardian 检查通过。
- 未调用真实模型或招聘平台；本候选继续交付私有源码与 Python wheel/sdist，不含独立桌面安装包。

## 0.2.0-rc.7 - 2026-10-28

第七次私有源码与 Python 内核候选发布，限制模型上下文中的大型工具结果，并持续完善会话摘要、provider 错误诊断与内核可靠性。

### 兼容变化

- npm 组件统一为 `0.2.0-rc.7`，Python 内核为等价 PEP 440 版本 `0.2.0rc7`；JSON-RPC 保持 `0.2.0`。
- `ToolDescriptor.maxModelResultBytes` 为可选字段；自定义工具默认使用 20 KiB 模型结果预算，可设置 8 KiB 至 1 MiB。

### 新功能

- 按工具配置模型可见结果的 UTF-8 字节预算，完整结果仍持久化；超限时向模型提供省略提示、摘要和 SHA-256，并新增只读 `read_session_tool_result` 内核工具分段读取，确保省略数据可按会话、条目和摘要校验后继续读取。
- 模型终态错误通过 `session/error.errorInfo` 和持久错误记录保留经过筛选的 provider、来源、HTTP 状态、provider code 与可选请求级 retryable；终态事件同时区分是否已观察到输出。原始响应和响应头不持久化，retryable 不授权重放整回合，自动重试策略保持不变。
- 新 checkpoint 以 `sourceItemCount` 持久化已覆盖前缀长度，避免每次摘要重复写入全部来源条目 ID；摘要请求也不再重复携带旧 checkpoint 的 ID 列表。旧 checkpoint 格式仍可读取，`context/read` 和 `context/compact/plan` 的 `sourceItemIds` 响应保持兼容。
- 为自动、手动及溢出恢复摘要增加独立 provider、model、effort 配置；未配置时沿用会话设置。显式推理档位需由模型容量目录声明支持，摘要任务和 checkpoint 记录实际配置，并在提交前继续按业务模型校验完整请求预算。
- 参考 Pi 的 hook 取消信号边界，为 `before_tool_call` 增加可选协作式 `signal`，并在回合取消时立即结束内核等待；旧的一参数 hook 保持兼容，迟到决策不触发审批或工具派发。
- [Issue #107](https://github.com/can4hou6joeng4/boss-cli/issues/107)：增加追加式会话上下文编辑，允许替换或排除已结束回合中的用户/助手文本；原始日志不变，编辑参与请求预算与摘要来源，并按 fork 历史继承。

### 修复

- 手动摘要的单次 `model` 覆盖只按摘要线路解析；当业务会话保存的推理档位不被跨 provider 摘要模型支持时，不再错误地按业务模型拒绝摘要请求。
- [Issue #99](https://github.com/can4hou6joeng4/boss-cli/issues/99)：为生命周期 hook callback 增加 16 个在途 worker 上限；超时线程在实际退出前继续占用容量，策略容量耗尽时以 `HOOK_BUSY` 拒绝工具调用，观察事件过载则跳过并合并诊断。
- [Issue #97](https://github.com/can4hou6joeng4/boss-cli/issues/97)：工具结果追加异常时按稳定条目身份对账，确认缺失后最多重试同一结果一次；不重跑 handler 或审批。恢复写入会停止当前工具批次，结果无法确认时记录 `outcome_unknown`，连未知状态也无法持久化时阻止该会话继续请求模型。
- [Issue #95](https://github.com/can4hou6joeng4/boss-cli/issues/95)：摘要 checkpoint 在同一写锁内重新核验来源，并先同步完整临时日志再原子发布；公开前失败保留原文件与旧摘要，公开后故障明确区分已提交与替换结果不确定，避免后续上下文静默采用写入失败的摘要。
- [Issue #85](https://github.com/can4hou6joeng4/boss-cli/issues/85)：会话执行状态追加失败时将工具明确记为未派发并暂停当前回合；终态或队列结算持久化失败时保守报告错误、尽力补记并暂停后续队列，避免运行通知与重启恢复给出相反结论。
- [Issue #87](https://github.com/can4hou6joeng4/boss-cli/issues/87)：队列暂停持久化失败时保留待暂停范围，在接受新任务或领取队列前完成补写，避免旧 follow-up 被后续成功回合派发。
- [Issue #89](https://github.com/can4hou6joeng4/boss-cli/issues/89)：严格验证 Anthropic 和 OpenAI Responses 的最终工具参数是完整 JSON object；截断、非对象、非标准 JSON 常量或终态来源冲突时不派发工具，保留合法空对象调用。
- [Issue #91](https://github.com/can4hou6joeng4/boss-cli/issues/91)：Anthropic 与 OpenAI Responses 的工具参数在增量、初始值和终态快照入口按 UTF-8 原始字节检查；每项和每次模型响应合计上限均为 1 MiB。超限、终态缺失或来源冲突时整轮报错，不派发工具且错误不回显输入。
- [Issue #93](https://github.com/can4hou6joeng4/boss-cli/issues/93)：将每响应文本与思考合计限制为 1 MiB UTF-8，超限在持久化前报错并阻止工具与队列继续；拆分增量事件，并用内容引用和冻结快照分段恢复大 Agent 字段。

### 验证与限制

- 本地 Python 3.10/3.12 编译、TypeScript 类型检查、桌面源码构建、干净 Git archive wheel/sdist 构建和结果预算专项探针通过；PR #113 的 Source build 与 GitGuardian 检查通过。探针未加入仓库。
- 未调用真实模型或招聘平台。此候选继续交付私有源码与 Python wheel/sdist，不含独立桌面安装包；签名/公证、完整 Python 依赖锁及真实模型/平台完整验收仍未完成。

## 0.2.0-rc.6 - 2026-10-27

第六次私有源码与 Python 内核候选发布，加入真实会话上下文预算与手动摘要、会话级推理档位和内核生命周期 hooks，并完善回合取消、应用关闭及跨入口队列状态收尾。

### 兼容变化

- npm 组件统一为 `0.2.0-rc.6`，Python 内核为等价 PEP 440 版本 `0.2.0rc6`；JSON-RPC 保持 `0.2.0`。
- 生命周期 hooks 仅由嵌入宿主显式注入；默认不配置时维持原行为，策略 hook 只能拒绝且不能绕过逐次审批。

### 新功能

- [Issue #76](https://github.com/can4hou6joeng4/boss-cli/issues/76)：桌面接入真实会话上下文预算、近期完整回合保留计划和显式手动摘要，展示进度、取消与终态并读取对账；`context/read` 增加可选的轻量任务引用，区分仍在收尾、本进程无记录和旧服务未知。打开或规划不调用模型、工具或隐式中断，失联和未知回执不自动重复开始。
- [Issue #78](https://github.com/can4hou6joeng4/boss-cli/issues/78)：参考 Pi 的会话级 `thinkingLevel` 生命周期，增加可恢复的会话推理档位设置和桌面菜单；模型能力表显式声明可选档位，设置不改全局配置，预算、后续回合和摘要请求使用同一有效档位，能力变更后显示不受支持并允许恢复继承配置。
- [Issue #80](https://github.com/can4hou6joeng4/boss-cli/issues/80)：增加由嵌入宿主显式注入的内核生命周期 hooks，支持有界异步事件观察和工具执行前拒绝策略；事件投影过滤消息正文与工具参数，策略失败按拒绝处理且不能绕过逐次审批，不扫描工作区或动态加载插件。

### 修复

- [Issue #82](https://github.com/can4hou6joeng4/boss-cli/issues/82)：策略 hook 不再复用会截断/脱敏的事件观察投影；策略收到有界完整 JSON 深只读快照，超出字节/深度/节点限制时在工具派发和审批前 fail closed。
- [Issue #73](https://github.com/can4hou6joeng4/boss-cli/issues/73)：统一直接发送与后续排队的会话内请求身份，重复请求关联原回合并结算队列收据；已执行失败不再误标未执行，明确未启动或证据未知时保留暂停。拒绝跨入口输入冲突、身份歧义及绕过排队/暂停/撤回的重复发送，恢复时只补充关联，不重放动作。
- [Issue #71](https://github.com/can4hou6joeng4/boss-cli/issues/71)：后续回合未启动时保留安全失败关联、已保存输入和请求幂等，将队列暂停并显示“启动失败，未执行”；实际已启动的 worker 继续持有模型、bridge 和状态目录责任。失败通知在运行锁外发布，排队响应返回结算后的最新状态，暂停项可撤回且不自动重试。
- [Issue #70](https://github.com/can4hou6joeng4/boss-cli/issues/70)：取消接受与回合终态在同一运行锁边界结算；终态提交前已确认取消时以 `interrupted` 收尾并暂停现有后续队列，保留已产生的文本和工具结果，避免模型刚完成时取消仍自动续跑。
- [Issue #68](https://github.com/can4hou6joeng4/boss-cli/issues/68)：手动回合/摘要取消先确认请求，再在 RPC 和全局运行锁外独立分发中止；重复取消与关闭共用中止责任。旧 worker 与 abort 都结束前保留模型实例及任务所有权，防止迟到 abort 影响复用实例的新请求。
- [Issue #66](https://github.com/can4hou6joeng4/boss-cli/issues/66)：应用关闭先为业务回合、摘要任务和连接检查统一置位取消，再异步分发各自的中止；所有 worker 共享同一个两秒等待期限。任务在 worker、终态通知和对应 abort 全部收尾前继续保留 provider、bridge 与状态目录所有权；重复关闭和非协作 provider 不会重复中止或伪造收尾。

### 验证与限制

- 独立功能 PR 均在最新 head 通过源码构建和 GitGuardian 检查后合并；当前 `main` Build `40480080146` 成功。
- 本地 Harness 回归 335 passed、4 skipped、889 个子断言通过；hooks 专项验收 14/14。此类测试材料仅留在忽略目录，不属于 GitHub 源码构建 CI。
- `npm run typecheck`、`npm run build`、Python 3.10 `compileall`、干净 Git archive wheel/sdist 构建和 `git diff --check` 通过。
- 未调用真实模型或招聘平台；桌面独立安装包、签名/公证、完整 Python 依赖锁及真实模型/平台完整验收仍未完成，仓库保持私有。

## 0.2.0-rc.5 - 2026-10-26

第五次私有源码与 Python 内核候选发布，加入长会话自动压缩、桌面任务队列和技能选择，并完善输出预算、模型任务收尾与摘要来源一致性。

### 兼容变化

- npm 组件统一为 `0.2.0-rc.5`，Python 内核为等价 PEP 440 版本 `0.2.0rc5`；JSON-RPC 保持 `0.2.0`。
- 嵌入方 provider 工厂须返回独立于主实例、业务 worker 与运行摘要的模型实例；临时实例须等旧 worker 完全结束后才能串行复用。
- 压缩计划的来源 digest 升为 v2，绑定选中条目和旧 checkpoint；旧 v1 计划应重新读取，合法已持久化 v1 checkpoint 继续可用。

### 新功能

- [Issue #55](https://github.com/can4hou6joeng4/boss-cli/issues/55)：桌面输入区接入运行时技能目录、刷新及单次直接发送，覆盖新会话与已有会话；队列带技能时明确阻止提交并保留草稿。
- [Issue #51](https://github.com/can4hou6joeng4/boss-cli/issues/51)：桌面端支持运行中转向、后续回合排队、队列状态展示和未投递项撤回。
- [Issue #45](https://github.com/can4hou6joeng4/boss-cli/issues/45)：在每个完整请求预算阈值或超限时自动压缩旧完整回合，支持启动策略及每回合覆盖；保留当前工具结果、思考和 steering，并对可信、零输出的上下文溢出最多压缩恢复一次，仍遵守 6 次业务请求上限。
- [Issue #43](https://github.com/can4hou6joeng4/boss-cli/issues/43)：压缩计划支持按估算 token 保留近期完整回合；长历史和超长单条结果按预算连续分段摘要，最多 32 个无工具生成阶段，全部成功后仅提交一次 checkpoint，并报告字符进度与逐段 usage。

### 修复与兼容

- [Issue #62](https://github.com/can4hou6joeng4/boss-cli/issues/62)：历史与上下文读取复用摘要来源校验；已覆盖记录发生修订时回退最新原文，避免旧摘要隐藏修正事实，并继续应用完整请求预算。
- [Issue #61](https://github.com/can4hou6joeng4/boss-cli/issues/61)：关闭内核时取消并等待模型连接检查，以任务身份隔离超时、中止和迟到响应，避免检查残留或旧回调覆盖新检查。
- [Issue #58](https://github.com/can4hou6joeng4/boss-cli/issues/58)：拒绝模型工厂复用应用主实例或仍被业务 worker/摘要持有的 provider，避免一个会话的中断影响另一个；拒绝前不预留回合、不保存输入，也不中断原 owner。
- [Issue #57](https://github.com/can4hou6joeng4/boss-cli/issues/57)：业务 CLI 的 stdout/stderr 合计限制为 16 MiB 原始字节，超限停止进程组并暂停任务；已派发写操作记为结果未知，保留大 stdin、超时/取消与初始化失败清理。
- [Issue #53](https://github.com/can4hou6joeng4/boss-cli/issues/53)：会话分支不再复制执行队列状态，避免继续子会话时投递原会话任务；保留历史、附件及上下文 checkpoint，原队列不受影响。
- [Issue #49](https://github.com/can4hou6joeng4/boss-cli/issues/49)：可用 `BOSS_HARNESS_BROWSER_SOURCE` 为业务 CLI 进程显式覆盖浏览器来源，并在连接诊断中展示；未设置时继承上游配置。
- [Issue #47](https://github.com/can4hou6joeng4/boss-cli/issues/47)：限制摘要任务并发和终态记录保留，截断超长终态错误；淘汰旧 `jobId` 时保留会话 checkpoint、usage 与事件历史。
- 模型错误新增可选结构化溢出分类，保持旧事件兼容；输出截断、限流、普通字节超限和网络错误不会触发业务恢复。自动摘要独立 provider、取消与 worker 所有权沿用既有边界。
- 来源 digest v2 同时冻结原始条目与旧 checkpoint，拒绝摘要覆盖倒退；旧 v1 计划需要重新读取。提交前检查默认业务模型的摘要及保留上下文完整预算，取消和中途失败不写新 checkpoint。
- 模型摘要正确标记来源；桌面 RPC 的摘要读取与取消接受协议规定的 `jobId`，并校验压缩选择参数。
- 拒绝沿用覆盖记录已被修订的旧摘要；统一擦除摘要失败消息中的配置凭据，提交后的读取或通知异常保持任务已完成状态。

### 验证与限制

- 本地内核全套 339 项中 335 通过、4 跳过；连接关闭 23 项专项与 12 项独立边界、摘要来源 21 项专项与 3 项独立验证通过。测试仅保留本地，远程 CI 执行源码构建与安全检查。
- TypeScript 类型检查、桌面源码构建与干净 Git 源码的 Python wheel/sdist 构建通过。桌面队列和技能入口已有隔离 Electron 验收；本候选仍交付源码与 Python 内核，不包含独立桌面安装包。
- 自动压缩会增加模型用量，token 仍为估算；取消依赖 provider 协作，摘要语义无损和真实服务窗口不作保证。已覆盖来源变化时回退原文，失效摘要的自动重建仍待实现。
- 本地验证使用合成状态，未调用真实模型或招聘平台。独立安装包、签名/公证、完整 Python 依赖锁及真实模型/平台完整验收仍待完成，仓库继续保持私有。

## 0.2.0-rc.4 - 2026-10-26

第四次私有源码与 Python 内核候选发布，完善模型请求预算、工具组合、上下文压缩与 provider 隔离。

### 兼容变化

- npm 组件统一为 `0.2.0-rc.4`，Python 内核为等价 PEP 440 版本 `0.2.0rc4`；JSON-RPC 继续保持 `0.2.0`。
- 嵌入式应用生成模型摘要时必须提供能够创建独立实例的 `provider_factory`。

### 新功能

- [Issue #36](https://github.com/can4hou6joeng4/boss-cli/issues/36)：增加可取消的模型摘要后台任务 `context/compact/start`、`context/compact/abort` 与 `context/compact/read`；摘要请求不携带招聘工具或 bridge，完成前重新校验来源 digest，并将摘要 usage 单独持久化。
- [Issue #34](https://github.com/can4hou6joeng4/boss-cli/issues/34)：增加只读 `context/compact/plan` 和可选 `sourceDigest` 校验；摘要来源变化时拒绝写入 checkpoint。
- [Issue #32](https://github.com/can4hou6joeng4/boss-cli/issues/32)：成功模型响应的 input usage 现在绑定 provider、模型、完整请求指纹和消息前缀；匹配时只将 usage 基线与新增尾部估算合并，变化或不明时继续使用保守估算。
- 增加显式 `ToolDefinition` / `ToolBundle` 及应用组合入口；默认保留 14 个招聘工具，自定义 bundle 不继承平台登录能力。
- [Issue #30](https://github.com/can4hou6joeng4/boss-cli/issues/30)：自定义工具 bridge 可实现同步 `close()` 或 `dispose()`；临时运行器、连接检查与应用退出按所属生命周期释放资源，重复关闭安全。
- 新增精确供应商/模型容量配置和完整请求预算，统一运行前准入及 `context/read` 预览/活动快照；按模型上限裁剪输出，持久化预算并标注未知容量假设，超限暂停且不请求模型。
- 新增求职者沟通列表工具 `boss_chat`，仅接受正整数页码并读取指定逻辑页；保留来源及未知分页，明确未读数、最近消息占位与关系发起方的含义，不补消息、回复、导出或自动翻页。

### 修复

- [Issue #40](https://github.com/can4hou6joeng4/boss-cli/issues/40)：关闭时等待摘要 worker 完成终态通知和资源收尾，避免提前释放状态目录所有权；线程启动失败时清理任务索引。
- [Issue #38](https://github.com/can4hou6joeng4/boss-cli/issues/38)：要求摘要使用独立 provider 实例；未提供 provider factory 或工厂复用主 provider 时拒绝启动摘要。
- 校验工具 handler 的结构化结果与暂停策略回调；无效结果也会完成持久化收尾，已派发写操作记为结果未知并暂停后续任务。拒绝复用仍存活的 bridge，避免探针与并发回合共享取消状态。
- steering 在下一模型请求通过预算检查后才确认投递；预算失败时暂停，避免转向未送达模型却显示已应用。
- 回合收尾与 steering 入队检查共用运行锁，关闭队列清扫后仍接受旧回合转向的竞态。
- 模型输出截断时拒绝执行整批工具并保留未执行配对记录，文本截断也以错误收尾；用尽 6 次回合模型请求且仍需续跑时暂停后续队列，不再误记为正常完成或无响应地投递最后到达的 steering。
- 明确工具派发、逻辑页面和业务 CLI 内部网络尝试的区别；工具描述、领域提示与贡献说明不再把单页或无 Harness 重试当作首次限制即停的保证，记录认证刷新及最终成功信封的可见范围。
- 招聘沟通列表已取得但最近消息补取触发平台停止码时，保留部分数据并暂停当前回合；阻止同批后续工具及自动模型续跑。
- 只识别固定命令和元数据路径的既有停止码，使用安全固定提示；保留原始 hints、分页与上游信封事实，不从候选人文本推断平台状态，不自动补批或重试。

### 验证与限制

- 本地离线套件通过：116 项 Python 用例、60 项桌面/客户端用例，以及 stdio 冒烟、TypeScript 类型检查和桌面构建；provider 隔离与关闭收尾回归包含在本地用例中。
- PR #39、PR #41 的 Source build、GitGuardian 及合并后 main Source build 均通过。未调用真实模型或招聘平台；候选包须从最终 tag 的干净 Git 源码构建，随发布资产提供构建信息与 SHA-256 清单。
- 当前不自动触发压缩；单次摘要请求超出模型输入预算时明确失败，按 cut point 保留近期上下文的分段压缩仍待实现。独立桌面安装包、签名与公证、完整 Python 依赖锁及真实平台验收也未完成。

## 0.2.0-rc.3 - 2026-10-25

第三次私有源码与 Python 内核候选发布，加入经验/学历集合查询及完整显式模型配置的文件隔离。

### 兼容变化

- npm 组件统一为 `0.2.0-rc.3`，Python 内核为等价 PEP 440 版本 `0.2.0rc3`；JSON-RPC 保持 `0.2.0`，原有单标签搜索保持兼容。

### 新功能

- 职位经验、学历条件兼容单标签并支持非空无重复枚举数组；固定顺序传给业务 CLI，同一组条件可用于下一页，不展开组合或自动补详情。
- 工具声明与执行校验同步支持集合，拒绝空数组、重复项、未知标签与隐式类型转换；城市、薪资继续单选，原始数组保留在会话中供追溯。

### 修复

- 完整的 OpenAI 端点、凭据和模型显式配置不再访问 Codex 文件，避免 Python 3.10 被无关 TOML 阻塞；可选推理强度仅取显式环境值。
- 命令行 `--model` 在配置解析前参与优先级判断，完整命令行/环境配置保持同一独立路径。
- 需要文件补全时对不可读、非文件路径或损坏 TOML 给出不含配置原文的明确错误；保留直接调用 loader 的缺省兼容行为。

### 验证与限制

- 242 项本地离线用例、stdio 冒烟、类型检查及桌面构建通过；其中搜索集合套件在实际 Python 3.10.20 / 3.12.13 各通过 28 项，独立审查另覆盖 2,020 种有效排列与 54 种无效输入。
- 实际 Electron 43.8.3 的实时、重载及重连验收通过，原始数组留在会话，下一页仅改页码。合成 provider、模拟 CLI 及固定业务管线验证未调用真实模型或招聘平台，不证明平台严格集合筛选或个人资格。
- 多标签依赖平台过滤；城市、薪资继续单选。部分模型配置需读取 TOML 时仍要求 Python 3.11+；完整显式 OpenAI 参数的启动在 Python 3.10 / 3.12 验证。
- 继续作为私有源码与内核候选版；独立桌面安装包、签名、公证、公开许可证、Python 完整依赖锁及真实平台验收仍待完成。测试材料仅保留本地，远程 CI 执行源码构建及 npm 依赖审计。

## 0.2.0-rc.2 - 2026-10-25

第二次私有源码与 Python 内核候选发布，继续验证招聘工具原语及大结果恢复。

### 兼容变化

- npm 组件统一为 `0.2.0-rc.2`，Python 内核为等价 PEP 440 版本 `0.2.0rc2`；JSON-RPC 保持 `0.2.0`，新增只读结果分段方法和可选引用字段。

### 新功能

- 职位搜索支持明确的城市、薪资、经验、学历与页码；保留关键词查询兼容，下一页可沿用同一组条件，单次工具调用只读取一页。
- 搜索参数在执行前校验类型、枚举和未知字段；提示区分平台标签、粗筛结果及资格判断，不自动放宽条件或补取详情。

### 修复

- 大结果恢复不再重复传输模型文本；超过 64 KiB 的工具结果改用绑定会话、条目和版本的引用，桌面支持手动分段查看完整 JSON。
- 条目与事件分页同时限制编码大小，游标按实际返回条目推进；超大响应返回有界错误，避免 stdio 内核退出或重连循环。
- 大失败结果的通知仅展示错误预览，完整失败信息仍可通过结果引用读取，模型和持久历史保持完整。

### 验证与限制

- 200 项本地离线验证、stdio 冒烟、类型检查和桌面构建通过；实际 Electron 的大结果手动分段、Unicode 边界、重载及重连通过。验证未调用真实模型或招聘平台，测试材料继续仅保留本地。
- 单条超大非工具记录返回明确错误，尚无通用分块阅读器；结果按既有会话存储加载，尚无流式磁盘索引。
- Python 3.10 下完整 OpenAI 环境参数仍可能被已有 Codex TOML 的解析阻塞，后续单独修复；本版运行及安装验收使用 Python 3.12。
- 继续作为私有源码与内核候选版；独立桌面安装包、签名、公证、公开许可证和 Python 完整依赖锁仍待完成。

## 0.2.0-rc.1 - 2026-10-25

首次私有源码与 Python 内核候选发布；尚无可独立安装的桌面应用。

### 兼容变化

- Electron 的最低 macOS 从 11 提高到 12；源码开发与运行验收前使用 `npx install-electron --no` 下载并校验官方运行时。
- npm 组件统一为 `0.2.0-rc.1`，Python 内核使用等价 PEP 440 版本 `0.2.0rc1`；JSON-RPC 协议保持 `0.2.0`。

### 修复

- 保留上游工具分页信息，贯通模型上下文、结果详情与重启历史；区分本页数量、分页结束和未知状态，避免将单页结果当作全部结果。
- 限制实时工具详情的内联大小，大结果保留分页摘要及省略提示，完整结果保存到会话历史。
- 将 Electron / electron-vite / Vite 固定到 43.8.3 / 4.0.1 / 6.4.4，清除本次 npm 依赖审计发现的 5 项受影响包。

### 交付与文档

- 建立私有仓库、独立 Issue / PR、源码构建与 npm 依赖审计 CI；提交和 squash 合并保留单行中文主题及空正文。
- 增加可独立阅读的 README、贡献说明、PR 模板和上游采用记录；测试、离线 provider、夹具及测试专用配置仅保留本地。
- 候选资产包括从干净 Git 树构建的 Python wheel、sdist 与 SHA-256 校验清单。

### 验证与限制

- 本地 170 项离线验证及 stdio smoke 通过；真实 Electron 43 的 IPC、多窗口/重连、构建后 renderer/历史恢复和离线登录隔离验收通过；远程源码构建与安全检查通过。
- 运行验收环境为 macOS arm64、Node.js 24、Python 3.12。未完成真实招聘平台的全面验收、独立桌面安装包、签名或公证。
- Python SDK 依赖当前使用版本下界约束，尚未提供完整依赖锁；候选发布不等于所有安装环境已验证。
- 仓库保持私有；公开开源许可尚未确定。当前 GitHub 套餐不支持私有仓库服务端分支保护，合并采用核对最新 head 检查及 commit 匹配的流程门禁。
