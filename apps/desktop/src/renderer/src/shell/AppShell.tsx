import { useState, useEffect, useRef } from "react";
import { TitleBar } from "./TitleBar";
import { NavigationRail, type WorkspacePage } from "./NavigationRail";
import { ProjectSidebar, type SidebarPreferences } from "./ProjectSidebar";
import { HomeView } from "./HomeView";
import { ConversationArea } from "./ConversationArea";
import { ErrorBoundary } from "../components/ErrorBoundary";
import type { TurnContinuationReadResponse } from "@boss-harness/protocol";
import { UI_STORAGE_PREFIX } from "../data/uiStorage";
import { RightPanel } from "./RightPanel";
import { LoginBrowserPanel } from "./LoginBrowserPanel";
import { LoginChoice } from "../components/LoginChoice";
import { usePlatformLogin } from "../data/usePlatformLogin";
import { WorkspacePages } from "./WorkspacePages";
import { SettingsDialog, type SettingsSection } from "../components/SettingsDialog";
import { SearchDialog } from "../components/SearchDialog";
import { NotificationsDialog } from "../components/NotificationsDialog";
import { ModalSurface } from "../components/ModalSurface";
import { type ProjectFolder, type SessionItem, type MessageItem, type ConversationMode } from "../data/mockData";
import { countPendingApprovalsByThread, isApprovalCountEvent, readApprovalFocus } from "../data/pendingApprovals";
import { createSingleFlightReload } from "../data/singleFlightReload";
import { readThreadFocus } from "../data/threadFocus";
import { focusResolution } from "../data/focusIntent";
import { approvalSoundEnabled, playApprovalChime } from "../data/approvalChime";
import { isCommandChord, isNotificationsShortcut } from "../data/shortcuts";
import { booleanPreference, projectFolders, stringList, stringRecord } from "../data/preferenceShapes";
import { planAliasMigrations } from "../data/aliasMigration";
import { type ModelDescriptor, type SkillDescriptor, type ToolDescriptor } from "@boss-harness/protocol";
import { createComposerDraft, withDraftText, type ComposerDraft, type UpdateComposerDraft, type ComposerSend } from "../data/composerDraft";
import { homeDraftHasContent, templateFillIntent, withHomeDraftSkill } from "../data/homeDraftFill";
import { createdSession, sessionStartSendOutcome, type SessionStartOutcome } from "../data/sessionStart";
import { loadComposerDraftStore, restoreComposerDraft, restoreSessionDrafts, saveComposerDrafts } from "../data/composerDraftStorage";
import type { CheckQueueSubmission, ComposerQueue } from "../data/composerDraft";
import { exportMarkdown } from "../data/exportMarkdown";
import type { QueueItem } from "@boss-harness/protocol";
import type { QueueRefreshResult } from "../data/queueRefresh";
import { harnessErrorText, listPendingApprovals, listSkills, listTools, type SkillCatalogState, type ToolCatalogState, type ApprovalDelivery, type ApprovalOutcome } from "../data/harnessBridge";
import type { SkillProblem } from "@boss-harness/protocol";
import type { SessionReasoningControl } from "../data/useSessionReasoning";
import type { ModelRetryStatus } from "../data/modelRetry";
import type { SessionBranchesView } from "./ConversationArea";
import type { ThemePreference } from "../data/themePreference";
import { dropSessionHistory, nextReachableIndex } from "../data/routeHistory";
import type { QueueActionOutcome } from "../data/queueAction";
import "../styles/login-sidebar.css";

export interface AppShellProps {
  isDark: boolean; theme: ThemePreference; onToggleTheme: () => void; onThemeChange: (next: ThemePreference) => void; isSidebarOpen: boolean; onToggleSidebar: () => void;
  folders: ProjectFolder[]; activeSession: SessionItem | null; isHomeView: boolean; messages: MessageItem[];
  /** turnId → 该回合实际注入的技能 id；旧内核不返回时为空。 */
  turnSkillIds?: Record<string, string[]>;
  currentMode: ConversationMode; onModeChange: (mode: ConversationMode) => void;
  onSelectSession: (session: SessionItem) => void; onNewTask: () => void;
  /** 删除会话；返回 false 表示会话仍保留（失败原因由外层提示）。 */
  onDeleteSession?: (session: SessionItem) => Promise<boolean>; onSendMessage: ComposerSend;
  /** 归档或恢复会话；失败原因由外层提示，界面以内核事件刷新为准。 */
  onArchiveSession?: (session: SessionItem, archived: boolean) => Promise<boolean>;
  /** 重命名会话；成功写入内核标题并持久化，返回 false 表示名称未保存（失败原因由外层提示）。 */
  onRenameSession?: (session: SessionItem, name: string, options?: { silent?: boolean }) => Promise<boolean>;
  onQueueMessage?: ComposerQueue; onCheckQueueSubmission?: CheckQueueSubmission; queueItems?: QueueItem[]; queueTotalItems?: number; queueActiveItems?: number; queueTruncated?: boolean; onRemoveQueueItem?: (id: string) => Promise<QueueActionOutcome>; onRetryQueueItem?: (item: QueueItem) => Promise<QueueActionOutcome>; onReadQueueItem?: (item: QueueItem) => Promise<QueueItem>; onUpdateQueueItem?: (item: QueueItem, input: string) => Promise<QueueItem>; onRefreshQueue?: () => Promise<QueueRefreshResult>;
  simulateLocal?: boolean; harnessUp?: boolean; running?: boolean; taskBlocked?: boolean;
  /** 会话列表是否至少成功加载过一次；通知定位在列表加载完成前需要保留意图。 */
  sessionsLoaded?: boolean;
  /** 内核声明 skills/read 后，「技能与工具」页才能展示技能正文。 */
  skillsReadable?: boolean;
  /** 内核声明 threadSearch 后，⌘K 弹窗才会按消息正文搜索。 */
  threadSearchable?: boolean;
  /** 内核声明 threadSearchArchived 后，搜索弹窗才提供「含已归档」开关。 */
  threadSearchArchived?: boolean;
  skillsCreatable?: boolean;
  skillsWritable?: boolean;
  skillsDeletable?: boolean;
  /** 内核声明 workspaceInstructionsEdit 后，「技能与工具」页才提供说明编辑。 */
  workspaceInstructionsEditable?: boolean;
  /** 内核声明 autoCompactionConfig 后，设置页才能保存自动压缩默认策略。 */
  autoCompactionConfig?: boolean;
  continuationCheck?: { threadId: string; sourceTurnId: string; loading: boolean; submitting?: boolean;
    uncertain?: boolean; response?: TurnContinuationReadResponse; error?: string } | null;
  onContinueInterruptedTurn?: () => void;
  modelRetry?: ModelRetryStatus; onDismissModelRetry?: () => void;
  sessionBranches?: SessionBranchesView;
  onInterrupt?: () => void;
  onApprovalDecision?: (approvalId: string, approved: boolean, toolName: string, remember: boolean) => void | ApprovalDelivery | ApprovalOutcome | Promise<void | ApprovalDelivery | ApprovalOutcome>;
  onStartSessionWithPrompt: (prompt: string, domainId: string, provider: string, modelId: string, skillIds?: string[]) => Promise<SessionStartOutcome>;
  models?: ModelDescriptor[]; activeModelProvider?: string; activeModelId?: string;
  onSelectModel?: (provider: string, modelId: string) => void | boolean | Promise<void | boolean>;
  configuredModelLabel?: string;
  sessionReasoning?: SessionReasoningControl;
  onOpenCockpit: () => void; onOpenSideChat: () => void; onOpenRewind: () => void; onOpenShortcuts: () => void;
  onOpenContext?: () => void;
  onOpenUsage?: () => void;
  onOpenExport?: () => void;
  onReviewDiff: () => void; onRevertDiff: () => void;
  onCreateConnectionSession: () => Promise<SessionItem | null>;
}
function preference(key: string, initial: unknown): unknown {
  try { return JSON.parse(localStorage.getItem(UI_STORAGE_PREFIX + key) ?? "null") ?? initial; } catch { return initial; }
}
interface Route { page: WorkspacePage; sessionId?: string; }
export function AppShell(props: AppShellProps) {
  const login = usePlatformLogin();
  const loginEntryFlight = useRef(false);
  const [page, setPage] = useState<WorkspacePage>("home");
  /** 从对话里的回合技能标签跳到「技能与工具」时的一次性聚焦意图。 */
  const [skillFocus, setSkillFocus] = useState<string | null>(null);
  const [messageFocus, setMessageFocus] = useState<{ threadId: string; itemId: string; revealToolBlock?: boolean } | null>(null);
  /** 跨会话搜索落地后留在目标消息里的关键词；离开会话、再次搜索或点击后清除。 */
  const [searchHighlight, setSearchHighlight] = useState<{ threadId: string; itemId: string; query: string } | null>(null);
  const [settings, setSettings] = useState(false), [search, setSearch] = useState(false), [notifications, setNotifications] = useState(false);
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [pendingApprovalsTruncated, setPendingApprovalsTruncated] = useState(false);
  /** 每个会话的待审批数量；读取失败时保留上一次结果，不把失败显示成 0。 */
  const [approvalCounts, setApprovalCounts] = useState<Record<string, number>>({});
  const [approvalPulse, setApprovalPulse] = useState(0);
  const pendingReload = useRef<() => void>(() => {});
  useEffect(() => {
    // 示例模式与断开的内核不读取审批；读取失败保留上一次数量，不把失败显示成 0。
    if (props.simulateLocal || props.harnessUp === false) { setPendingApprovals(0); setPendingApprovalsTruncated(false); setApprovalCounts({}); return; }
    let disposed = false;
    // 轮询、聚焦、重新可见与通知防抖共用一次读取；在途期间的刷新合并为一次尾随读取，
    // 否则审批通知恰好撞上慢轮询时，徽标要等到下一次轮询才会更新。
    const reload = createSingleFlightReload(async () => {
      const result = await listPendingApprovals(100);
      if (disposed) return;
      setPendingApprovals(result.approvals.length);
      setPendingApprovalsTruncated(result.truncated);
      setApprovalCounts(countPendingApprovalsByThread(result.approvals));
    }, () => document.visibilityState !== "hidden");
    pendingReload.current = reload.run;
    reload.run();
    const timer = window.setInterval(reload.run, 30_000);
    window.addEventListener("focus", reload.run);
    const onVisibility = () => { if (document.visibilityState === "visible") reload.run(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      disposed = true;
      reload.cancel();
      pendingReload.current = () => {};
      window.clearInterval(timer); window.removeEventListener("focus", reload.run); document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [props.simulateLocal, props.harnessUp]);
  useEffect(() => {
    // 待审批数量同步到应用图标徽标；平台不支持时主进程返回 applied=false，不影响侧栏徽标。
    if (props.simulateLocal) return;
    const api = window.boss;
    if (!api?.setBadgeCount) return;
    void api.setBadgeCount(pendingApprovals).catch(() => {});
  }, [pendingApprovals, props.simulateLocal]);
  useEffect(() => {
    // 内核主动推送审批变化时尽快刷新徽标；连续事件防抖合并为一次读取。
    if (props.simulateLocal || props.harnessUp === false) return;
    const api = window.boss;
    if (!api?.onNotification) return;
    let timer: number | undefined;
    const unsubscribe = api.onNotification(raw => {
      const method = (raw as { method?: unknown }).method;
      // 提示音是可选的本机反馈：只在新审批请求到达且用户开启时播放，失败不影响刷新。
      if (method === "approval/requested" && approvalSoundEnabled()) playApprovalChime();
      if (!isApprovalCountEvent(method)) return;
      if (timer !== undefined) window.clearTimeout(timer);
      timer = window.setTimeout(() => { timer = undefined; setApprovalPulse(previous => previous + 1); pendingReload.current(); }, 250);
    });
    return () => { unsubscribe(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [props.simulateLocal, props.harnessUp]);
  const [settingsSection, setSettingsSection] = useState<SettingsSection>("general");
  const [summaryAvailable, setSummaryAvailable] = useState(() => window.matchMedia("(min-width: 1200px)").matches);
  const [summaryOpen, setSummaryOpen] = useState(() => booleanPreference(preference("summaryOpen", true), true));
  const [pinned, setPinned] = useState<string[]>(() => stringList(preference("pinned", [])));
  const [hidden, setHidden] = useState<string[]>(() => stringList(preference("hidden", [])));
  const [aliases, setAliases] = useState<Record<string, string>>(() => stringRecord(preference("aliases", {})));
  const [groups, setGroups] = useState<ProjectFolder[]>(() => projectFolders(preference("groups", [])));
  const [projectAliases, setProjectAliases] = useState<Record<string, string>>(() => stringRecord(preference("projectAliases", {})));
  const [threadGroups, setThreadGroups] = useState<Record<string, string>>(() => stringRecord(preference("threadGroups", {})));
  const [sidebarPreferences, setSidebarPreferences] = useState<SidebarPreferences>(() => {
    const saved = preference("sidebar", {});
    const value = saved && typeof saved === "object" && !Array.isArray(saved) ? saved as Partial<SidebarPreferences> : {};
    return { grouping: value.grouping === "list" ? "list" : "project", sort: value.sort === "name" ? "name" : "updated", showRecent: value.showRecent === true, showHidden: value.showHidden === true, showArchived: value.showArchived === true };
  });
  const [newProject, setNewProject] = useState(false), [projectName, setProjectName] = useState("");
  const [rename, setRename] = useState<SessionItem | null>(null), [name, setName] = useState(""), [renameBusy, setRenameBusy] = useState(false);
  const [deleteSession, setDeleteSession] = useState<SessionItem | null>(null), [deleteBusy, setDeleteBusy] = useState(false);
  const [renameProject, setRenameProject] = useState<ProjectFolder | null>(null), [folderName, setFolderName] = useState("");
  const [removeProject, setRemoveProject] = useState<ProjectFolder | null>(null);
  /** 分别在启动时恢复，不长期保留可能含已删除内容的原始存储快照。 */
  const [draft, updateHomeDraft] = useState(() => restoreComposerDraft(loadComposerDraftStore().home));
  const [sessionDrafts, setSessionDrafts] = useState<Record<string, ComposerDraft>>(() => restoreSessionDrafts(loadComposerDraftStore()));
  const deletedSessionDraftIds = useRef(new Set<string>());
  const draftRef = useRef(draft); draftRef.current = draft;
  const sessionDraftsRef = useRef(sessionDrafts); sessionDraftsRef.current = sessionDrafts;
  useEffect(() => {
    const timer = window.setTimeout(() => saveComposerDrafts(draftRef.current, sessionDraftsRef.current), 300);
    return () => window.clearTimeout(timer);
  }, [draft, sessionDrafts]);
  useEffect(() => {
    // 防抖窗口内关闭窗口或重载时补写一次，避免最后 300ms 的输入丢失。
    const flush = () => saveComposerDrafts(draftRef.current, sessionDraftsRef.current);
    window.addEventListener("pagehide", flush);
    window.addEventListener("beforeunload", flush);
    return () => { window.removeEventListener("pagehide", flush); window.removeEventListener("beforeunload", flush); };
  }, []);
  const setDraft = (text: string) => updateHomeDraft(previous => withDraftText(previous, text));
  const resetDraft = () => updateHomeDraft(createComposerDraft());
  const sessionDraftId = props.activeSession?.id ?? "conversation";
  const sessionDraft = sessionDrafts[sessionDraftId] ?? createComposerDraft("session:" + sessionDraftId);
  const updateSessionDraft: UpdateComposerDraft = change => setSessionDrafts(previous => {
    // 删除成功后，旧组件的附件读取等迟到回调不能为同一会话重新创建草稿。
    if (deletedSessionDraftIds.current.has(sessionDraftId)) return previous;
    const current = previous[sessionDraftId] ?? createComposerDraft("session:" + sessionDraftId);
    const next = change(current);
    return next === current ? previous : { ...previous, [sessionDraftId]: next };
  });
  const [draftProjectId, setDraftProjectId] = useState("");
  // 工作区模板等待用户确认替换的首页草稿；首页渲染确认条，写入或取消后清空。
  const [pendingTemplate, setPendingTemplate] = useState<string | null>(null);
  const [pendingNewTask, setPendingNewTask] = useState<{ projectId: string; draft: ComposerDraft } | null>(null);
  const [tools, setTools] = useState<ToolDescriptor[]>([]);
  const [toolCatalogState, setToolCatalogState] = useState<ToolCatalogState>("unavailable");
  const [toolCatalogError, setToolCatalogError] = useState("");
  const [skills, setSkills] = useState<SkillDescriptor[]>([]);
  const [skillCatalogState, setSkillCatalogState] = useState<SkillCatalogState>("unavailable");
  const [skillCatalogError, setSkillCatalogError] = useState("");
  const [skillRoot, setSkillRoot] = useState<string | null>(null);
  const [skillProblems, setSkillProblems] = useState<SkillProblem[]>([]);
  const [skillRefresh, setSkillRefresh] = useState(0);
  const [history, setHistory] = useState<Route[]>([{ page: "home" }]), [cursor, setCursor] = useState(0);
  const cursorRef = useRef(cursor); cursorRef.current = cursor;
  const historyRef = useRef(history); historyRef.current = history;
  const hasConversation = page === "home" && !props.isHomeView && Boolean(props.activeSession);
  const loginThreadId = props.activeSession?.id ?? "";
  const browserOpen = hasConversation && login.panelThreadId === loginThreadId;
  const loginStatus = login.status.threadId === loginThreadId ? login.status : undefined;
  const baseFolders = [...props.folders, ...groups.filter(group => !props.folders.some(folder => folder.id === group.id))];
  const sessions = [...new Map(baseFolders.flatMap(folder => folder.sessions).map(session => [session.id, session])).values()];
  const allFolders = baseFolders.map(folder => ({ ...folder, name: projectAliases[folder.id] || folder.name,
    sessions: sessions.filter(session => (baseFolders.some(item => item.id === threadGroups[session.id]) ? threadGroups[session.id] : session.projectId) === folder.id)
      .map(session => ({ ...session, title: aliases[session.id] || session.title })),
  }));
  const currentProject = allFolders.find(folder => folder.sessions.some(session => session.id === props.activeSession?.id));
  const title = page === "home" ? props.isHomeView ? "BOSS Harness" : aliases[props.activeSession?.id ?? ""] || props.activeSession?.title || "新聊天" : { recents: "最近聊天", library: "资料库", skills: "技能与工具" }[page];
  // 旧版本只写本机别名：连接内核后把遗留名称一次性写回内核，并删除本机别名。
  // 失败保留别名、不提示，下次启动再试；卸载后不再发起后续写入。
  const aliasMigrationStarted = useRef(false);
  const aliasMigrationAlive = useRef(true);
  const sessionsRef = useRef(sessions); sessionsRef.current = sessions;
  useEffect(() => {
    // StrictMode 会在开发环境重跑副作用：重新挂载时恢复存活标记，避免迁移循环被上一次清理中止。
    aliasMigrationAlive.current = true;
    return () => { aliasMigrationAlive.current = false; };
  }, []);
  useEffect(() => {
    if (aliasMigrationStarted.current || props.simulateLocal || props.harnessUp !== true || !props.onRenameSession) return;
    if (!sessions.length) return;
    aliasMigrationStarted.current = true;
    const plan = planAliasMigrations(aliases, sessions);
    if (plan.drop.length > 0) {
      setAliases(previous => {
        const next = { ...previous };
        for (const id of plan.drop) delete next[id];
        return next;
      });
    }
    if (!plan.rename.length) return;
    const rename = props.onRenameSession;
    void (async () => {
      for (const { session, name } of plan.rename) {
        if (!aliasMigrationAlive.current) return;
        // 会话已被其他入口更新（例如手动重命名）时放弃旧别名，避免覆盖较新的标题。
        const current = sessionsRef.current.find(item => item.id === session.id);
        if (!current || current.title !== session.title) continue;
        let renamed = false;
        try { renamed = await rename(session, name, { silent: true }); }
        catch { renamed = false; }
        if (!renamed || !aliasMigrationAlive.current) continue;
        setAliases(previous => {
          const stored = previous[session.id];
          if (typeof stored !== "string" || stored.trim() !== name) return previous;
          const next = { ...previous };
          delete next[session.id];
          return next;
        });
      }
    })();
  }, [sessions, aliases, props.simulateLocal, props.harnessUp, props.onRenameSession]);
  const pushRoute = (route: Route) => {
    const previous = historyRef.current, current = previous[cursorRef.current];
    if (current?.page === route.page && current.sessionId === route.sessionId) return;
    const next = [...previous.slice(0, cursorRef.current + 1), route];
    historyRef.current = next; cursorRef.current = next.length - 1; setHistory(next); setCursor(next.length - 1);
  };
  const routeReachable = (route: Route): boolean =>
    route.page !== "home" || !route.sessionId || sessions.some(session => session.id === route.sessionId);
  const openRoute = (route: Route, record = true, keepFocus = false) => {
    // 历史栈里可能残留已删除会话的路由：保持当前视图，不记录、也不拿它去开新任务。
    if (!routeReachable(route)) return;
    // 离开首页草稿或进入会话时作废待确认操作，避免返回后继续执行旧的替换或丢弃。
    if (route.page !== "home" || route.sessionId) { setPendingTemplate(null); setPendingNewTask(null); }
    if (record) pushRoute(route);
    // 一次定位意图只服务创建它的那次跳转；普通导航先作废，否则切回同一会话时
    // 会补做一次用户并未请求的滚动与高亮。显式定位的跳转通过 keepFocus 保留。
    if (!keepFocus) setMessageFocus(null);
    setSkillFocus(null);
    setPage(route.page);
    if (route.page === "home") {
      const session = allFolders.flatMap(folder => folder.sessions).find(item => item.id === route.sessionId);
      if (session) { setHidden(prev => prev.filter(id => id !== session.id)); props.onSelectSession(session); }
      else props.onNewTask();
    }
  };
  const startEmptyTask = (projectId = "") => {
    setPendingTemplate(null); setPendingNewTask(null);
    resetDraft(); setDraftProjectId(projectId); openRoute({ page: "home" });
  };
  const requestNewTask = (projectId = "") => {
    setPendingTemplate(null);
    if (homeDraftHasContent(draftRef.current)) {
      setPendingNewTask({ projectId, draft: draftRef.current });
      openRoute({ page: "home" });
      return;
    }
    startEmptyTask(projectId);
  };
  const newTask = () => requestNewTask();
  // 工作区模板入口：草稿非空时不能直接 reset，否则正文、附件与技能会被静默清空。
  // 回到首页交给首页确认条处理，确认后才替换；取消则原样保留。
  const useTemplate = (template: string) => {
    setPendingNewTask(null);
    if (templateFillIntent(draftRef.current, template) === "confirm") {
      setPendingTemplate(template);
      openRoute({ page: "home" });
      return;
    }
    startEmptyTask();
    setDraft(template);
  };
  // 技能入口只并入技能，保留首页正文与附件；不能走 newTask()。
  // 从工作区页进入时切回首页；已在首页时原地并入，不再重置草稿。
  const useSkillInNewChat = (skillId: string) => {
    if (page !== "home") openRoute({ page: "home" });
    updateHomeDraft(previous => withHomeDraftSkill(previous, skillId));
  };
  // 确认条结论：应用模板时清空旧草稿后再写入，取消只丢弃待定模板。
  const resolveTemplate = (apply: boolean) => {
    const template = pendingTemplate;
    setPendingTemplate(null);
    if (apply && template !== null) { resetDraft(); setDraft(template); }
  };
  const resolveNewTask = (discard: boolean) => {
    if (discard && (draftRef.current.pendingReads > 0 || draftRef.current.submitting)) return;
    const pending = pendingNewTask;
    setPendingNewTask(null);
    // 确认只适用于展示时的草稿，期间发生编辑或异步读取完成都不能沿用旧确认。
    if (discard && pending?.draft === draftRef.current) startEmptyTask(pending.projectId);
  };
  useEffect(() => {
    // 继续编辑或更改项目说明用户已接手，收起旧的替换和丢弃意图。
    setPendingTemplate(null); setPendingNewTask(null);
  }, [draft, draftProjectId]);
  const newTaskInProject = (folder: ProjectFolder) => requestNewTask(folder.id);
  const openSettings = (section: SettingsSection = "general") => { setSettingsSection(section); setSettings(true); };
  const startInProject = async (prompt: string, domainId: string, provider: string, modelId: string, skillIds: string[] = []) => {
    const projectId = draftProjectId;
    const outcome = await props.onStartSessionWithPrompt(prompt, domainId, provider, modelId, skillIds);
    // 会话可能已经建立而首条消息没送达：分组仍要记在真实会话上，结果按状态归一给输入区。
    const session = createdSession(outcome);
    if (session && projectId) setThreadGroups(prev => ({ ...prev, [session.id]: projectId }));
    return sessionStartSendOutcome(outcome);
  };
  const select = (session: SessionItem, keepFocus = false) => { setSearchHighlight(null); openRoute({ page: "home", sessionId: session.id }, true, keepFocus); };
  const openMessage = (session: SessionItem, itemId: string, revealToolBlock = false, query = "") => {
    setMessageFocus({ threadId: session.id, itemId, revealToolBlock });
    select(session, true);
    // 搜索命中才保留关键词；审批通知等没有查询词的定位不产生高亮。
    setSearchHighlight(query.trim() ? { threadId: session.id, itemId, query: query.trim() } : null);
  };
  /**
   * 通知定位意图：会话列表尚未加载时先保留，列表就绪后再应用或放弃。
   * 系统通知的主场景是窗口被关闭后重建，此时 `thread/list` 必然晚于定位载荷。
   */
  const [approvalFocus, setApprovalFocus] = useState<{ threadId: string; itemId: string } | null>(null);
  const [threadFocus, setThreadFocus] = useState<{ threadId: string } | null>(null);
  useEffect(() => {
    if (props.simulateLocal) return;
    const api = window.boss;
    if (!api?.onApprovalFocus) return;
    return api.onApprovalFocus(value => {
      const target = readApprovalFocus(value);
      if (target) setApprovalFocus(target);
    });
  }, [props.simulateLocal]);
  useEffect(() => {
    if (props.simulateLocal) return;
    const api = window.boss;
    if (!api?.onThreadFocus) return;
    return api.onThreadFocus(value => {
      const target = readThreadFocus(value);
      if (target) setThreadFocus(target);
    });
  }, [props.simulateLocal]);
  useEffect(() => {
    if (!approvalFocus) return;
    const session = allFolders.flatMap(folder => folder.sessions).find(item => item.id === approvalFocus.threadId);
    const resolution = focusResolution(props.sessionsLoaded === true, Boolean(session));
    if (resolution === "drop") { setApprovalFocus(null); return; }
    // 等待列表时保持当前视图；只有真正找到会话才应用，绝不新建任务。
    if (!session) return;
    setApprovalFocus(null);
    setMessageFocus({ threadId: approvalFocus.threadId, itemId: approvalFocus.itemId });
    openRoute({ page: "home", sessionId: session.id }, true, true);
  }, [approvalFocus, allFolders, props.sessionsLoaded]);
  useEffect(() => {
    if (!threadFocus) return;
    const session = allFolders.flatMap(folder => folder.sessions).find(item => item.id === threadFocus.threadId);
    const resolution = focusResolution(props.sessionsLoaded === true, Boolean(session));
    if (resolution === "drop") { setThreadFocus(null); return; }
    if (!session) return;
    setThreadFocus(null);
    setMessageFocus(null);
    select(session);
  }, [threadFocus, allFolders, props.sessionsLoaded]);
  const confirmRenameSession = async () => {
    const target = rename;
    const nextName = name.trim();
    if (!target || renameBusy || !nextName) return;
    // 无内核桥接（浏览器预览）时保留原本地别名行为；有桥接则必须写入内核，失败不静默回退。
    if (!props.onRenameSession) {
      setAliases(previous => ({ ...previous, [target.id]: nextName }));
      setRename(null);
      return;
    }
    setRenameBusy(true);
    let renamed = false;
    try { renamed = await props.onRenameSession(target, nextName); }
    catch { renamed = false; }
    finally { setRenameBusy(false); }
    if (!renamed) return;
    // 内核已成为标题的唯一真值来源：清掉旧别名，避免本机显示名与持久化标题分叉。
    const id = target.id;
    setAliases(previous => { if (!(id in previous)) return previous; const next = { ...previous }; delete next[id]; return next; });
    setRename(null);
  };
  const confirmDeleteSession = async () => {
    const target = deleteSession;
    if (!target || deleteBusy || !props.onDeleteSession) return;
    setDeleteBusy(true);
    let removed = false;
    try { removed = await props.onDeleteSession(target); }
    catch { removed = false; }
    finally { setDeleteBusy(false); }
    if (!removed) return;
    const id = target.id;
    deletedSessionDraftIds.current.add(id);
    const removeDraft = (previous: Record<string, ComposerDraft>) => {
      if (!(id in previous)) return previous;
      const next = { ...previous }; delete next[id]; return next;
    };
    // 立即同步关闭补写的快照与本地存储，不等待渲染提交或 300ms 防抖。
    sessionDraftsRef.current = removeDraft(sessionDraftsRef.current);
    setSessionDrafts(removeDraft);
    saveComposerDrafts(draftRef.current, sessionDraftsRef.current);
    // 会话已不存在：同时清掉只存在于本设备的隐藏、置顶、别名与分组记录。
    setPinned(previous => previous.filter(item => item !== id));
    setHidden(previous => previous.filter(item => item !== id));
    setAliases(previous => { if (!(id in previous)) return previous; const next = { ...previous }; delete next[id]; return next; });
    setThreadGroups(previous => { if (!(id in previous)) return previous; const next = { ...previous }; delete next[id]; return next; });
    // 历史栈里的旧路由同样失效：移除并修正光标，前进/后退按钮状态随之更新。
    const pruned = dropSessionHistory(historyRef.current, cursorRef.current, id);
    if (pruned) { historyRef.current = pruned.routes; cursorRef.current = pruned.cursor; setHistory(pruned.routes); setCursor(pruned.cursor); }
    setDeleteSession(null);
  };
  const loginEntry = async (direct = false) => {
    if (!window.boss || loginEntryFlight.current) return;
    loginEntryFlight.current = true;
    try {
      const owner = ["opening", "waiting", "saving"].includes(login.status.state)
        ? sessions.find(session => session.id === login.status.threadId) : undefined;
      const target = owner ?? (!props.isHomeView ? props.activeSession : null) ?? await props.onCreateConnectionSession();
      if (!target) return;
      setSettings(false); setPage("home");
      pushRoute({ page: "home", sessionId: target.id });
      // 直接切换会话同样作废待处理的定位意图。
      setMessageFocus(null);
      props.onSelectSession(target);
      if (direct) void login.open(target.id); else login.show(target.id);
    } finally { loginEntryFlight.current = false; }
  };
  const go = (delta: number) => {
    // 跳过已删除会话留下的失效路由，落到最近一个仍可打开的位置。
    const next = nextReachableIndex(historyRef.current, cursorRef.current, delta, routeReachable);
    if (next < 0) return;
    cursorRef.current = next; setCursor(next); openRoute(historyRef.current[next]!, false);
  };
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1200px)");
    const update = () => setSummaryAvailable(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (!props.isHomeView && props.activeSession && page === "home") pushRoute({ page: "home", sessionId: props.activeSession.id });
  }, [props.activeSession?.id, props.isHomeView]);
  useEffect(() => {
    const entries: Record<string, unknown> = { summaryOpen, pinned, hidden, aliases, groups, projectAliases, threadGroups, sidebar: sidebarPreferences };
    for (const [key, value] of Object.entries(entries)) { try { localStorage.setItem(UI_STORAGE_PREFIX + key, JSON.stringify(value)); } catch { /* UI preferences are optional. */ } }
  }, [summaryOpen, pinned, hidden, aliases, groups, projectAliases, threadGroups, sidebarPreferences]);
  useEffect(() => {
    let current = true;
    setTools([]);
    setToolCatalogError("");
    if (!props.harnessUp || !window.boss) { setToolCatalogState("unavailable"); return () => { current = false; }; }
    setToolCatalogState("loading");
    void listTools().then(result => {
      if (!current) return;
      setTools(result);
      setToolCatalogState(result.length ? "ready" : "empty");
    }).catch(cause => {
      // 读取失败不能显示成「没有工具」：旧清单作废，但状态要如实标为失败。
      if (!current) return;
      setTools([]);
      setToolCatalogError(harnessErrorText(cause));
      setToolCatalogState("error");
    });
    return () => { current = false; };
  }, [props.harnessUp]);
  useEffect(() => {
    let current = true;
    setSkillCatalogError("");
    if (!props.harnessUp || !window.boss) {
      // 断开或预览时旧目录已不可用，立即清空，避免继续展示可能过期的技能。
      setSkills([]);
      setSkillRoot(null);
      setSkillProblems([]);
      setSkillCatalogState("unavailable");
      return () => { current = false; };
    }
    // 刷新期间保留上一次成功读取的目录与选中项；读取失败的分支仍会清空。
    setSkillCatalogState("loading");
    void listSkills().then(result => {
      if (!current) return;
      setSkills(result.skills);
      setSkillRoot(result.root);
      setSkillProblems(result.problems);
      // 全部文件都未能加载时仍按 empty 处理，但问题清单会说明原因。
      setSkillCatalogState(result.skills.length ? "ready" : "empty");
    }).catch(cause => {
      // 读取失败不能显示成「没有技能」：旧清单作废，但状态要如实标为失败并保留原因。
      if (!current) return;
      setSkills([]);
      setSkillRoot(null);
      setSkillProblems([]);
      setSkillCatalogError(harnessErrorText(cause));
      setSkillCatalogState("error");
    });
    return () => { current = false; };
  }, [props.harnessUp, skillRefresh]);
  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.isComposing || event.keyCode === 229) return;
      if (document.querySelector('[aria-modal="true"]')) return;
      if (!event.metaKey && !event.ctrlKey) return;
      if (isCommandChord(event, "k")) { event.preventDefault(); setSearch(true); }
      if (isNotificationsShortcut(event)) { event.preventDefault(); setNotifications(true); }
      if (isCommandChord(event, "n")) { event.preventDefault(); newTask(); }
      if (isCommandChord(event, ",")) { event.preventDefault(); openSettings(); }
      if (isCommandChord(event, "b", { alt: true }) && summaryAvailable) { event.preventDefault(); setSummaryOpen(prev => !prev); }
      if (isCommandChord(event, "[")) { event.preventDefault(); go(-1); }
      if (isCommandChord(event, "]")) { event.preventDefault(); go(1); }
    };
    window.addEventListener("keydown", handle); return () => window.removeEventListener("keydown", handle);
  });
  const exportChat = () => {
    if (!hasConversation) return;
    const markdown = exportMarkdown(title, props.messages);
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = title.replace(/[\\/:*?"<>|]/g, "_") + ".md"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <>
    <div className={`app-container ${window.boss ? "native-window" : "browser-window"} ${browserOpen ? `with-browser${login.expanded ? " browser-expanded" : ""}` : summaryOpen && hasConversation ? "with-summary" : ""}`}>
      <TitleBar summaryAvailable={summaryAvailable && !browserOpen} hasConversation={hasConversation} title={title} isSidebarOpen={props.isSidebarOpen} isSummaryOpen={summaryOpen && !browserOpen} canGoBack={nextReachableIndex(history, cursor, -1, routeReachable) >= 0} canGoForward={nextReachableIndex(history, cursor, 1, routeReachable) >= 0} onBack={() => go(-1)} onForward={() => go(1)} onToggleSidebar={props.onToggleSidebar} onToggleSummary={() => setSummaryOpen(!summaryOpen)} onNewTask={newTask} onOpenSettings={() => openSettings()} onOpenRewind={props.onOpenRewind} onOpenContext={props.onOpenContext} onOpenUsage={props.onOpenUsage} onOpenExport={props.onOpenExport} onOpenBranches={props.sessionBranches ? () => props.sessionBranches?.onOpen() : undefined} onRename={() => { if (props.activeSession) { setRename(props.activeSession); setName(title); } }} onPin={() => { const id = props.activeSession?.id; if (id) setPinned(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]); }} isPinned={pinned.includes(props.activeSession?.id ?? "")} onDelete={() => { if (props.activeSession) setDeleteSession(props.activeSession); }} onExport={exportChat} browserOpen={browserOpen} onOpenBrowser={window.boss ? () => { if (browserOpen) login.closePanel(); else void loginEntry(); } : undefined} />
      <div className="workspace-layout">
        <NavigationRail page={page} isDark={props.isDark} harnessUp={props.harnessUp ?? false} onToggleTheme={props.onToggleTheme} onOpenShortcuts={props.onOpenShortcuts} onNavigate={next => openRoute({ page: next })} onOpenSettings={openSettings} onOpenCockpit={props.onOpenCockpit} onOpenSideChat={props.onOpenSideChat} />
        <div className="workspace-surface">
          <ProjectSidebar isOpen={props.isSidebarOpen} folders={allFolders} activeSessionId={props.activeSession?.id ?? null} isHomeView={props.isHomeView || page !== "home"} pinned={pinned}
            hiddenSessionIds={hidden} onUnhideSession={id => setHidden(prev => prev.filter(item => item !== id))}
            preferences={sidebarPreferences} onPreferencesChange={setSidebarPreferences} localGroupIds={groups.map(group => group.id)} onSelectSession={select} onNewTask={newTask} onNewTaskInProject={newTaskInProject} onSearch={() => setSearch(true)} onOpenSettings={() => openSettings()} onRecents={() => openRoute({ page: "recents" })} onNewProject={() => setNewProject(true)} pendingApprovals={pendingApprovals} pendingApprovalsTruncated={pendingApprovalsTruncated} approvalCounts={approvalCounts} onNotifications={() => setNotifications(true)}
            onRename={session => { setRename(session); setName(session.title); }} onPin={id => setPinned(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id])} onHide={id => setHidden(prev => [...prev.filter(item => item !== id), id])} onDelete={setDeleteSession}
            onArchive={session => { void props.onArchiveSession?.(session, true); }} onUnarchive={session => { void props.onArchiveSession?.(session, false); }}
            onMoveSession={(id, folderId) => setThreadGroups(prev => ({ ...prev, [id]: folderId }))} onRenameProject={folder => { setRenameProject(folder); setFolderName(folder.name); }} onRemoveProject={setRemoveProject} />
          <main className="main-canvas">
            {page !== "home" ? <WorkspacePages page={page} folders={allFolders} messages={props.messages} onSelect={select} onNewTask={newTask} onDraft={useTemplate} tools={tools} toolCatalogState={toolCatalogState} toolCatalogError={toolCatalogError} skills={skills} skillCatalogState={skillCatalogState} skillCatalogError={skillCatalogError} onRefreshSkills={() => setSkillRefresh(previous => previous + 1)} skillsReadable={props.skillsReadable === true} skillsCreatable={props.skillsCreatable === true} skillsWritable={props.skillsWritable === true} skillsDeletable={props.skillsDeletable === true} skillRoot={skillRoot} skillProblems={skillProblems} onUseSkill={useSkillInNewChat} workspaceInstructionsEditable={props.workspaceInstructionsEditable === true} harnessUp={props.harnessUp === true} preview={props.simulateLocal ?? true} focusSkillId={skillFocus} onFocusSkill={() => setSkillFocus(null)} /> : props.isHomeView ? <HomeView key={draft.id} folders={allFolders} draft={draft} onDraftChange={updateHomeDraft} pendingTemplate={pendingTemplate} onResolveTemplate={resolveTemplate} pendingNewTaskProject={pendingNewTask?.projectId ?? null} onResolveNewTask={resolveNewTask} selectedProjectId={draftProjectId} onSelectProject={setDraftProjectId} onNewProject={() => setNewProject(true)} preview={!window.boss} harnessUp={props.harnessUp ?? false} blocked={props.taskBlocked} models={props.models} activeModelProvider={props.activeModelProvider} activeModelId={props.activeModelId ?? "deepseek-v4"} configuredModelLabel={props.configuredModelLabel} onSelectModel={props.onSelectModel} currentMode={props.currentMode} onModeChange={props.onModeChange} skills={skills} skillCatalogState={skillCatalogState} skillCatalogError={skillCatalogError} onRefreshSkills={() => setSkillRefresh(previous => previous + 1)} skillProblems={skillProblems} onStartSessionWithPrompt={startInProject} onOpenSettings={() => openSettings("connections")} /> : <>
              <div className="conversation-pane">
                {props.simulateLocal && <div className="conversation-preview-badge">示例会话 · 交互预览</div>}
                <ErrorBoundary key={props.activeSession?.id ?? "conversation"} scope="会话区" compact hint="侧边栏、导航和其他会话仍可使用；切换会话或重试即可恢复。">
                  <ConversationArea readOnly={props.activeSession?.toolPolicy === "readOnly"} archived={props.activeSession?.archived === true} threadId={props.activeSession?.id} key={props.activeSession?.id ?? "conversation"} draft={sessionDraft} onDraftChange={updateSessionDraft} messages={props.messages} turnSkillIds={props.turnSkillIds ?? {}} onInspectSkill={skillId => { openRoute({ page: "skills" }); setSkillFocus(skillId); }} focusMessageId={messageFocus && messageFocus.threadId === props.activeSession?.id ? messageFocus.itemId : null} focusRevealTool={messageFocus !== null && messageFocus.threadId === props.activeSession?.id && messageFocus.revealToolBlock === true} onFocusMessage={() => setMessageFocus(null)} searchHighlight={searchHighlight && searchHighlight.threadId === props.activeSession?.id ? searchHighlight : null} onDismissSearchHighlight={() => setSearchHighlight(null)} currentMode={props.currentMode} onModeChange={props.onModeChange} onSendMessage={props.onSendMessage} onQueueMessage={props.onQueueMessage} onCheckQueueSubmission={props.onCheckQueueSubmission} queueItems={props.queueItems} queueTotalItems={props.queueTotalItems} queueActiveItems={props.queueActiveItems} queueTruncated={props.queueTruncated} onRemoveQueueItem={props.onRemoveQueueItem} onRetryQueueItem={props.onRetryQueueItem} onReadQueueItem={props.onReadQueueItem} onUpdateQueueItem={props.onUpdateQueueItem} onRefreshQueue={props.onRefreshQueue} simulateLocal={props.simulateLocal} harnessUp={props.harnessUp} running={props.running} taskBlocked={props.taskBlocked} models={props.models} activeModelProvider={props.activeModelProvider} activeModelId={props.activeModelId} configuredModelLabel={props.configuredModelLabel} onSelectModel={props.onSelectModel} sessionReasoning={props.sessionReasoning} skills={skills} skillCatalogState={skillCatalogState} skillCatalogError={skillCatalogError} onRefreshSkills={() => setSkillRefresh(previous => previous + 1)} skillProblems={skillProblems} onOpenSettings={() => openSettings("connections")} onInterrupt={props.onInterrupt} onApprovalDecision={props.onApprovalDecision} onReviewDiff={props.onReviewDiff} onRevertDiff={props.onRevertDiff} onOpenRewind={props.onOpenRewind} onOpenCockpit={props.onOpenCockpit} continuationCheck={props.continuationCheck} onContinueInterruptedTurn={props.onContinueInterruptedTurn} modelRetry={props.modelRetry} onDismissModelRetry={props.onDismissModelRetry} sessionBranches={props.sessionBranches}
                    onLogin={window.boss ? () => { void loginEntry(); } : undefined}
                    loginGuide={login.visibleIn(loginThreadId) ? <LoginChoice status={loginStatus} pending={login.choiceThreadId === loginThreadId} busy={login.busy} panelOpen={browserOpen} error={login.error?.threadId === loginThreadId ? login.error.message : undefined} onOpen={() => { void login.open(loginThreadId); }} onHide={login.hideForLater} onCancel={() => { void login.cancel(loginThreadId); }} onDismiss={() => login.dismiss(loginThreadId)} onSettings={() => openSettings("connections")} /> : undefined} />
                </ErrorBoundary>
                <RightPanel isOpen={summaryOpen && !browserOpen} projectName={currentProject?.name ?? "本地招聘项目"} messages={props.messages} preview={props.simulateLocal ?? true} onReviewChanges={props.onReviewDiff} onOpenSettings={() => openSettings("connections")} />
              </div>
              {browserOpen && <LoginBrowserPanel key={loginThreadId} threadId={loginThreadId} status={loginStatus} expanded={login.expanded} onToggleExpanded={login.toggleExpanded} onClose={login.closePanel} onRetry={() => { void login.open(loginThreadId); }} />}
            </>}
          </main>
        </div>
      </div>
    </div>
    <SettingsDialog isOpen={settings} initialSection={settingsSection} onClose={() => setSettings(false)} theme={props.theme} onThemeChange={props.onThemeChange} onOpenShortcuts={() => { setSettings(false); props.onOpenShortcuts(); }} harnessUp={props.harnessUp ?? false} autoCompactionConfig={props.autoCompactionConfig === true} onLogin={() => { void loginEntry(true); }} />
    {search && <SearchDialog folders={allFolders} onSelect={select} onOpenMessage={openMessage} onClose={() => setSearch(false)} searchMessages={props.threadSearchable === true} searchArchived={props.threadSearchArchived === true} />}
    {notifications && <NotificationsDialog folders={allFolders} preview={props.simulateLocal === true} refreshToken={approvalPulse} onSelect={select} onOpenMessage={openMessage} onLoaded={(approvals, truncated) => { setPendingApprovals(approvals.length); setPendingApprovalsTruncated(truncated); setApprovalCounts(countPendingApprovalsByThread(approvals)); }} onClose={() => setNotifications(false)} />}
    {newProject && <ModalSurface title="新建项目" onClose={() => setNewProject(false)} className="compact-dialog"><form className="dialog-form" onSubmit={event => { event.preventDefault(); if (!projectName.trim()) return; const id = "group-" + crypto.randomUUID(); setGroups(prev => [...prev, { id, name: projectName.trim(), sessions: [] }]); setDraftProjectId(id); openRoute({ page: "home" }); setProjectName(""); setNewProject(false); }}><label>项目名称<input autoFocus maxLength={60} value={projectName} onChange={event => setProjectName(event.target.value)} placeholder="例如：核心产研团队招聘" /></label><p>创建一个保存在此设备上的项目分组。</p><button className="solid-button" disabled={!projectName.trim()}>创建项目</button></form></ModalSurface>}
    {rename && <ModalSurface title="更改显示名称" onClose={() => { if (!renameBusy) setRename(null); }} closeDisabled={renameBusy} className="compact-dialog"><form className="dialog-form" onSubmit={event => { event.preventDefault(); void confirmRenameSession(); }}><label>聊天名称<input autoFocus value={name} maxLength={100} disabled={renameBusy} onChange={event => setName(event.target.value)} /></label><p>{props.onRenameSession ? "名称会写入本地内核并随会话保存。" : "只更新此工作区的显示名称。"}</p><button className="solid-button" disabled={!name.trim() || renameBusy}>{renameBusy ? "正在保存…" : "保存"}</button></form></ModalSurface>}
    {renameProject && <ModalSurface title="更改项目显示名称" onClose={() => setRenameProject(null)} className="compact-dialog"><form className="dialog-form" onSubmit={event => { event.preventDefault(); if (!folderName.trim()) return; setProjectAliases(prev => ({ ...prev, [renameProject.id]: folderName.trim() })); setRenameProject(null); }}><label>项目名称<input autoFocus maxLength={60} value={folderName} onChange={event => setFolderName(event.target.value)} /></label><p>显示名称保存在此设备上。</p><button className="solid-button" disabled={!folderName.trim()}>保存</button></form></ModalSurface>}
    {removeProject && <ModalSurface title="移除本地分组" onClose={() => setRemoveProject(null)} className="compact-dialog"><div className="dialog-form"><p>移除“{removeProject.name}”后，其中的聊天会回到原项目。</p><div className="dialog-actions"><button className="secondary-button" onClick={() => setRemoveProject(null)}>取消</button><button className="solid-button" onClick={() => { const id = removeProject.id; setGroups(prev => prev.filter(folder => folder.id !== id)); setThreadGroups(prev => Object.fromEntries(Object.entries(prev).filter(([, folderId]) => folderId !== id))); if (draftProjectId === id) setDraftProjectId(""); setRemoveProject(null); }}>移除分组</button></div></div></ModalSurface>}
    {deleteSession && <ModalSurface title="删除聊天" onClose={() => { if (!deleteBusy) setDeleteSession(null); }} className="compact-dialog"><div className="dialog-form">
      <p>“{aliases[deleteSession.id] || deleteSession.title}”及其全部消息会从本机移除，无法恢复。</p>
      <p>仍有运行中的回合或排队消息时，内核会拒绝删除；请先停止当前回合。</p>
      <div className="dialog-actions">
        <button className="secondary-button" disabled={deleteBusy} onClick={() => setDeleteSession(null)}>取消</button>
        <button className="solid-button danger-button" disabled={deleteBusy} onClick={() => { void confirmDeleteSession(); }}>{deleteBusy ? "正在删除…" : "删除聊天"}</button>
      </div>
    </div></ModalSurface>}
  </>;
}
