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
