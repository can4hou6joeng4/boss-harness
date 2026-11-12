import { useState, useRef, useEffect, useId, forwardRef } from "react";
import { IconPlus, IconSend, IconStop, IconShield, IconChevronDown, IconCheck, IconClose, IconFolder, IconSparkles, IconSettings, IconSearch, IconBranch, IconChat, IconLock } from "../components/Icons";
import { Popover } from "../components/Popover";
import { SlashCommandList, filterSlashCommands, slashMenuVisible, type SlashCommandItem } from "../components/SlashCommandList";
import { MODEL_OPTIONS, type ConversationMode } from "../data/mockData";
import type { ModelDescriptor, SkillDescriptor, SkillProblem } from "@boss-harness/protocol";
import type { SkillCatalogState } from "../data/harnessBridge";
import { harnessErrorText, isHarnessRpcRejection } from "../data/harnessBridge";
import { filterSkills } from "../data/skillFilter";
import { skillChips } from "../data/skillChips";
import { attachmentFailureNotice, readTextAttachments } from "../data/attachmentRead";
import type { SessionReasoningControl } from "../data/useSessionReasoning";
import { createComposerDraft, clearTransferredDraft, composerSendResult, composedMessageText, MAX_MESSAGE_TEXT_LENGTH, type ComposerDraft, type UpdateComposerDraft, type ComposerSend, type ComposerSendOutcome, type ComposerQueue, type QueueIntent, type QueueSubmission, type CheckQueueSubmission } from "../data/composerDraft";
import { queueSkillNotice } from "../data/queueSkillNotice";
import { recallAfterValueChange, recallKeyDirection, recallNewer, recallOlder, type PromptRecallState } from "../data/composerHistory";
import "../styles/composer-menus.css";

export interface ComposerProps {
  readOnly?: boolean; /** 会话已归档：可查看草稿但不能发送，恢复后才继续对话。 */ archived?: boolean;
  value: string; onChange: (text: string) => void; onSend: ComposerSend;
  onQueue?: ComposerQueue;
  onCheckQueueSubmission?: CheckQueueSubmission;
  draft?: ComposerDraft; onDraftChange?: UpdateComposerDraft;
  isRunning?: boolean; blocked?: boolean; onInterrupt?: () => void; preview?: boolean;
  currentMode?: ConversationMode; onModeChange?: (mode: ConversationMode) => void;
  models?: ModelDescriptor[]; activeModelProvider?: string; activeModelId?: string; configuredModelLabel?: string;
  onSelectModel?: (provider: string, id: string) => void | boolean | Promise<void | boolean>; onOpenSettings?: () => void;
  sessionReasoning?: SessionReasoningControl;
  skills?: SkillDescriptor[]; skillCatalogState?: SkillCatalogState; skillCatalogError?: string; onRefreshSkills?: () => void; skillProblems?: SkillProblem[];
  /** 本会话已发送的用户输入（从旧到新）；空数组表示不启用上下键调取。 */
  history?: readonly string[];
  home?: boolean;
  onLogin?: () => void;
}
const MODES = [
  { id: "agent", name: "Agent", detail: "结合招聘工具持续推进任务", icon: IconSparkles },
  { id: "plan", name: "Plan", detail: "梳理目标并制定执行计划", icon: IconBranch },
  { id: "ask", name: "Ask", detail: "围绕当前上下文快速提问", icon: IconChat },
] as const;
const MAX_ATTACHMENTS = 4;
const MAX_ATTACHMENT_BYTES = 200000;

/** 同时覆盖父层草稿与本组件的本地草稿；任一可被恢复覆盖的字段变化都让旧确认失效。 */
function queueRestoreDraftUnchanged(current: ComposerDraft, snapshot: ComposerDraft): boolean {
  return current.id === snapshot.id && current.textVersion === snapshot.textVersion
    && current.attachments === snapshot.attachments && current.skillIds === snapshot.skillIds
    && current.queueSubmission === snapshot.queueSubmission && current.pendingReads === snapshot.pendingReads
    && current.submitting === snapshot.submitting;
}

export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(function Composer({
  value, onChange, onSend, draft, onDraftChange, isRunning = false, blocked = false, onInterrupt, preview = true, readOnly = false, archived = false,
  onQueue, onCheckQueueSubmission,
  currentMode = "agent", onModeChange, models = [], activeModelProvider, activeModelId, configuredModelLabel, onSelectModel, onOpenSettings, home = false, onLogin,
  skills = [], skillCatalogState = "unavailable", skillCatalogError, onRefreshSkills, skillProblems = [],
  history = [],
  sessionReasoning,
}, forwardedRef) {
  const [menu, setMenu] = useState<"add" | "permissions" | "mode" | "model" | "skills" | null>(null);
  const [modelQuery, setModelQuery] = useState("");
  const [skillQuery, setSkillQuery] = useState("");
  const [modelPending, setModelPending] = useState(false);
  const [modelError, setModelError] = useState("");
  const [slashOpen, setSlashOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [localDraft, setLocalDraft] = useState(createComposerDraft);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState("");
  const [checkingQueue, setCheckingQueue] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const modelInputRef = useRef<HTMLInputElement>(null);
  const skillInputRef = useRef<HTMLInputElement>(null);
  const composingRef = useRef(false);
  const readingRef = useRef(false);
  const sendingRef = useRef(false);
  const alive = useRef(true);
  const [queueIntent, setQueueIntent] = useState<QueueIntent>("steering");
  const [pendingQueueRestore, setPendingQueueRestore] = useState<{ draft: ComposerDraft; intent: QueueIntent } | null>(null);
  const lastValue = useRef(value), valueVersion = useRef(0);
  if (lastValue.current !== value) { lastValue.current = value; valueVersion.current += 1; }
  // 上下键调取历史的游标：-1 表示当前草稿，draft 保存进入历史前的输入。
  const recall = useRef<PromptRecallState>({ index: -1, draft: "" });
  // 调取把原草稿只留在组件内；离开会话或卸载时写回，避免被调取正文覆盖。
  const recallStash = useRef<{ draftId: string; update: UpdateComposerDraft; original: string; recalled: string } | null>(null);
  // 记录本组件最后写入的文本；父层或其他入口改写 value 后，已请求打开的快捷指令菜单立即失效。
  const ownedText = useRef(value);
  const composerDraft = draft && onDraftChange ? draft : { ...localDraft, text: value, textVersion: valueVersion.current };
  const draftRef = useRef(composerDraft); draftRef.current = composerDraft;
  const attachments = composerDraft.attachments;
  const selectedSkillIds = composerDraft.skillIds ?? [];
  const selectedSkillChips = skillChips(selectedSkillIds, skills);
  const staleSkillIds = selectedSkillIds.filter(id => !skills.some(skill => skill.id === id));
  // 筛选只影响菜单展示，不改变已选技能；被筛掉但已选中的技能仍会随消息应用。
  const filteredSkills = filterSkills(skills, skillQuery);
  const hiddenSelectedSkills = skillQuery.trim()
    ? selectedSkillIds.filter(id => skills.some(skill => skill.id === id) && !filteredSkills.some(skill => skill.id === id)).length
    : 0;
  const readingAttachments = composerDraft.pendingReads > 0;
  const submitting = composerDraft.submitting;
  const uncertainQueue = composerDraft.queueSubmission?.uncertain ? composerDraft.queueSubmission : null;
  const queueModeActive = isRunning || Boolean(uncertainQueue?.intent === "followUp");
  const queueRestoreBusy = readingAttachments || submitting || checkingQueue;
  const currentQueueRestore = pendingQueueRestore && queueRestoreDraftUnchanged(composerDraft, pendingQueueRestore.draft)
    && pendingQueueRestore.intent === queueIntent && !queueRestoreBusy ? pendingQueueRestore : null;
  const queueRestoreStateRef = useRef({ confirmation: currentQueueRestore, checking: checkingQueue });
  queueRestoreStateRef.current = { confirmation: currentQueueRestore, checking: checkingQueue };
  /**
   * 发起核对时的草稿与请求快照：只有它们仍是当前待核对请求，结果才能结算。
   * 同编号重试会复用同一请求对象，因此另记提交代数，排除核对发出后的新尝试。
   */
  const queueCheckRef = useRef<{ draftId: string; submission: QueueSubmission; transfer: number } | null>(null);
  const queueTransferRef = useRef(0);
  // 恢复会替换正文、附件与技能；任何草稿变化或处理方式切换后，旧确认都不能继续生效。
  useEffect(() => {
    if (pendingQueueRestore && !currentQueueRestore) setPendingQueueRestore(null);
  }, [pendingQueueRestore, currentQueueRestore]);
  const skillQueueNotice = queueSkillNotice(queueModeActive, queueIntent, selectedSkillIds.length);
  const updateDraft: UpdateComposerDraft = change => {
    if (draft && onDraftChange) onDraftChange(change);
    else if (alive.current) setLocalDraft(previous => change({ ...previous, text: lastValue.current, textVersion: valueVersion.current }));
  };
  /**
   * 历史调取期间暂存进入前的草稿；↓ / Esc 或外部改写会让调取结束，随后清空。
   * 只在正文仍是最后一次调取内容时写回，避免覆盖用户后来显式编辑的正文。
   * 进入调取时同时把原稿写入草稿字段，重启 / 重载时优先恢复它。
   */
  const clearRecallDraft = () => updateDraft(previous =>
    previous.recallDraft === undefined ? previous : { ...previous, recallDraft: undefined });
  const rememberRecall = (state: PromptRecallState, text: string) => {
    if (state.index === -1) { recallStash.current = null; clearRecallDraft(); return; }
    const stash = recallStash.current;
    if (stash && stash.draftId === composerDraft.id) stash.recalled = text;
    else {
      recallStash.current = { draftId: composerDraft.id, update: updateDraft, original: state.draft, recalled: text };
      // 重启 / 重载不会触发组件卸载时的写回，因此随草稿持久化进入调取前的正文。
      updateDraft(previous => previous.id === composerDraft.id ? { ...previous, recallDraft: state.draft } : previous);
    }
  };
  const restoreRecallBeforeLeaving = () => {
    const stash = recallStash.current;
    recallStash.current = null;
    if (!stash) return;
    stash.update(previous => {
      if (previous.id !== stash.draftId) return previous;
      const restore = previous.text === stash.recalled && !previous.submitting;
      if (!restore && previous.recallDraft === undefined) return previous;
      return { ...previous, text: restore ? stash.original : previous.text,
        textVersion: previous.textVersion + (restore ? 1 : 0), recallDraft: undefined };
    });
  };
  useEffect(() => () => restoreRecallBeforeLeaving(), []);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  // 外部改写（编辑消息、恢复队列消息、发送后清空）会让历史游标与草稿失去对应关系，
  // 统一由共享判定退出历史；本组件自己写回的文本仍保留浏览位置。
  useEffect(() => {
    const next = recallAfterValueChange(recall.current, value, ownedText.current);
    if (next.index === -1 && recallStash.current) { recallStash.current = null; clearRecallDraft(); }
    recall.current = next;
  }, [value]);
  const dragDepth = useRef(0);
  const slashQuery = value.match(/^\/([^\s]*)$/)?.[1] ?? "";
  // 渲染时以当前 value 为准：建议词、编辑消息、恢复队列消息会绕过 change() 直接改写输入。
  const slashMenuOpen = slashMenuVisible(slashOpen, value, ownedText.current);
  // 列表与键盘共用同一份结果；活动项索引也按同一规则夹取，供 aria-activedescendant 使用。
  const slashListId = useId();
  const slashOptions = filterSlashCommands(slashQuery);
  const slashActiveIndex = slashOptions.length ? Math.min(selectedIndex, slashOptions.length - 1) : -1;
  const slashListVisible = slashMenuOpen && slashOptions.length > 0;
  const availableModels = preview ? MODEL_OPTIONS : models.filter(model => model.configured && model.available);
  const currentDescriptor = availableModels.find(model => model.id === activeModelId && model.provider === activeModelProvider);
  const modelName = preview
    ? (MODEL_OPTIONS.find(model => model.id === activeModelId)?.name.replace("Adaptive Router: ", "") ?? "默认模型")
    : (currentDescriptor ? `${currentDescriptor.provider} · ${currentDescriptor.id}` : configuredModelLabel?.trim() || "配置的模型");
  const query = modelQuery.trim().toLowerCase();
  const filteredModels = availableModels.filter(model => ["name" in model ? model.name : "", model.provider, model.id].join(" ").toLowerCase().includes(query));
  const configuredModelMatches = [modelName, "启动配置 当前模型"].join(" ").toLowerCase().includes(query);
  const mode = MODES.find(item => item.id === currentMode) ?? MODES[0];

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(180, Math.max(home ? 66 : 52, inputRef.current.scrollHeight)) + "px";
    }
  }, [value, home]);
  const focusInput = () => requestAnimationFrame(() => inputRef.current?.focus());
  const toggleMenu = (next: typeof menu) => {
    setMenu(previous => previous === next ? null : next);
    setModelQuery(""); setSkillQuery(""); setSlashOpen(false);
  };
  const writeText = (text: string) => { ownedText.current = text; onChange(text); };
  const change = (text: string) => {
    writeText(text); setNotice(""); setSelectedIndex(0);
    setSlashOpen(/^\/[^\s]*$/.test(text));
  };
  // 快捷指令按钮：空输入先写入 /；已有草稿时把当前文本收归本组件，选择命令后前缀插入。
  const openSlashMenu = () => {
    const text = value.trim() ? value : "/";
    ownedText.current = text;
    if (text !== value) onChange(text);
    setSlashOpen(true); setSelectedIndex(0); setMenu(null); focusInput();
  };
  const selectSlash = (item: SlashCommandItem) => {
    setSlashOpen(false);
    writeText(/^\/[^\s]*$/.test(value) ? item.command + " " : `${item.command} ${value}`);
    focusInput();
  };
  const addFiles = async (files: File[]) => {
    if (!files.length) return;
    const started = draftRef.current;
    if (readingRef.current || started.pendingReads > 0) { setNotice("正在读取附件，请稍候。"); return; }
    if (sendingRef.current || started.submitting) { setNotice("正在转交消息，请稍候再添加附件。"); return; }
    if (files.length + started.attachments.length > MAX_ATTACHMENTS || files.some(file => file.size > MAX_ATTACHMENT_BYTES)) {
      setNotice("最多添加 4 个文本文件，每个文件不超过 200 KB。"); return;
    }
    if (files.some(file => !/\.(?:txt|md|markdown|json|csv)$/i.test(file.name))) {
      setNotice("请选择 TXT、Markdown、JSON 或 CSV 文本文件。"); return;
    }
    readingRef.current = true; setNotice("");
    updateDraft(previous => previous.id === started.id ? { ...previous, pendingReads: previous.pendingReads + 1 } : previous);
    try {
      const { added, failures } = await readTextAttachments(files, () => crypto.randomUUID());
      updateDraft(previous => previous.id !== started.id || previous.attachments.length + added.length > MAX_ATTACHMENTS ? previous : { ...previous, attachments: [...previous.attachments, ...added] });
      if (failures.length && alive.current && draftRef.current.id === started.id) {
        setNotice(attachmentFailureNotice(failures, added.length));
      }
      const active = document.activeElement;
      if (alive.current && draftRef.current.id === started.id && (active === document.body || inputRef.current?.closest(".composer-surface")?.contains(active))) focusInput();
    } finally {
      readingRef.current = false;
      updateDraft(previous => previous.id === started.id ? { ...previous, pendingReads: Math.max(0, previous.pendingReads - 1) } : previous);
    }
  };
  const submit = async () => {
    if (archived) return;
    const submitted = draftRef.current;
    const priorQueueSubmission = submitted.queueSubmission;
    const queueing = Boolean(onQueue && (isRunning || (priorQueueSubmission?.uncertain && priorQueueSubmission.intent === "followUp")));
    if ((!isRunning && blocked) || (isRunning && !queueing) || readingRef.current || submitted.pendingReads > 0 || sendingRef.current || submitted.submitting || (!submitted.text.trim() && !submitted.attachments.length)) return;
    if (queueing && queueIntent === "steering" && (submitted.skillIds?.length ?? 0) > 0) {
      setNotice("转向当前回合的消息不支持技能；可改为排到后续回合，或清除已选技能。");
      return;
    }
    if ((submitted.skillIds?.length ?? 0) > 0 && (skillCatalogState !== "ready" || submitted.skillIds?.some(id => !skills.some(skill => skill.id === id)))) {
      setNotice("所选技能尚未确认可用，请刷新技能目录或清除不可用技能后再发送。");
      return;
    }
    const text = composedMessageText(submitted.text, submitted.attachments);
    // 附件按原文拼进消息，界面允许的 4 × 200 KB 很容易超过内核单条上限；
    // 在内核之前拦下，避免把必被拒绝的消息送出（首页还会先建会话留下空会话）。
    if (text.length > MAX_MESSAGE_TEXT_LENGTH) {
      setNotice(`消息连同附件共 ${text.length} 字符，超过内核单条 ${MAX_MESSAGE_TEXT_LENGTH} 字符上限；请减少附件或精简正文后再发送。`);
      return;
    }
    const skillIds = submitted.skillIds ?? [];
    if (priorQueueSubmission?.uncertain) {
      const sameRequest = priorQueueSubmission.text === text && priorQueueSubmission.intent === queueIntent
        && JSON.stringify(priorQueueSubmission.skillIds ?? []) === JSON.stringify(skillIds);
      if (!sameRequest) {
        setNotice("上一条队列消息结果尚未确认；恢复原消息和处理方式后才能用相同请求编号重试。");
        return;
      }
      if (!queueing) {
        setNotice("转向目标回合已结束。请先核对队列，再决定是否作为新消息提交。");
        return;
      }
    }
    sendingRef.current = true; queueTransferRef.current += 1; setNotice("");
    updateDraft(previous => previous.id === submitted.id ? { ...previous, submitting: true } : previous);
    let queueRequest: ComposerDraft["queueSubmission"];
    try {
      let transferred: ComposerSendOutcome;
      if (queueing && onQueue) {
        queueRequest = priorQueueSubmission?.text === text && priorQueueSubmission.intent === queueIntent
          && JSON.stringify(priorQueueSubmission.skillIds ?? []) === JSON.stringify(skillIds)
          ? priorQueueSubmission
          : { text, intent: queueIntent, id: crypto.randomUUID(), skillIds, uncertain: false };
        updateDraft(previous => previous.id === submitted.id ? { ...previous, queueSubmission: queueRequest } : previous);
        transferred = await onQueue(text, queueIntent, queueRequest.id, skillIds);
      } else {
        transferred = await onSend(text, skillIds);
      }
      const outcome = composerSendResult(transferred);
      if (outcome !== "sent") {
        // 不确定时不清空正文、附件与技能选择：服务端可能没收到，草稿是唯一还能重发的副本。
        updateDraft(previous => previous.id === submitted.id
          ? { ...previous, submitting: false, ...(outcome === "rejected" && queueing ? { queueSubmission: undefined } : {}) }
          : previous);
        if (outcome === "uncertain" && alive.current && draftRef.current.id === submitted.id) {
          setNotice("提交结果尚未确认；内容已保留在输入框，请先核对聊天记录再决定是否重发。");
        }
        return;
      }
      if (!draft || !onDraftChange) {
        if (alive.current && draftRef.current.id === submitted.id && valueVersion.current === submitted.textVersion) onChange("");
      }
      // 提交期间开始的调取不能把已发送的原草稿再写回输入框。
      if (recallStash.current?.original === submitted.text) recallStash.current = null;
      updateDraft(previous => clearTransferredDraft(previous, submitted));
      if (alive.current && draftRef.current.id === submitted.id) { setSlashOpen(false); setMenu(null); }
    } catch (cause) {
      // 内核明确拒绝说明消息未入队 / 未转向：解除待核对状态，内容保留在输入框供修改后正常重试。
      if (queueing && isHarnessRpcRejection(cause)) {
        updateDraft(previous => previous.id === submitted.id
          ? { ...previous, submitting: false, queueSubmission: undefined }
          : previous);
        if (alive.current && draftRef.current.id === submitted.id) {
          setNotice(`${queueRequest?.intent === "steering" ? "转向" : "加入队列"}被内核拒绝：${harnessErrorText(cause)}；消息仍保留在输入框，请调整后重试。`);
        }
        return;
      }
      // 回调异常不能证明消息未转交；保留内容和提交锁，避免直接重复发送。
      if (alive.current && draftRef.current.id === submitted.id) setNotice(queueing
        ? "队列提交结果尚未确认；恢复原消息后再次提交会使用同一请求编号。"
        : "提交结果尚未确认，请先核对聊天记录；不会自动重复提交。");
      if (queueing && queueRequest) {
        updateDraft(previous => previous.id === submitted.id
          ? { ...previous, submitting: false, queueSubmission: { ...queueRequest!, uncertain: true } }
          : previous);
      }
    } finally { sendingRef.current = false; }
  };
  const applyQueueRestore = (expected: ComposerDraft, confirmation?: typeof pendingQueueRestore) => {
    const current = draftRef.current, pending = current.queueSubmission;
    if (!queueRestoreDraftUnchanged(current, expected) || !pending?.uncertain || readingRef.current || sendingRef.current
      || current.pendingReads > 0 || current.submitting || queueRestoreStateRef.current.checking
      || (confirmation && queueRestoreStateRef.current.confirmation !== confirmation)) return;
    setPendingQueueRestore(null); setSlashOpen(false);
    updateDraft(previous => queueRestoreDraftUnchanged(previous, expected)
      ? { ...previous, text: pending.text, textVersion: previous.textVersion + 1, attachments: [], skillIds: pending.skillIds ?? [], queueSubmission: pending }
      : previous);
    if (!draft || !onDraftChange) onChange(pending.text);
    setQueueIntent(pending.intent);
    setNotice("已恢复原队列消息；重试会沿用原请求编号。");
    focusInput();
  };
  const restoreQueueSubmission = () => {
    const current = draftRef.current, pending = current.queueSubmission;
    if (!pending?.uncertain || readingRef.current || sendingRef.current
      || current.pendingReads > 0 || current.submitting || queueRestoreStateRef.current.checking) return;
    const currentSkills = current.skillIds ?? [], pendingSkills = pending.skillIds ?? [];
    const sameSkills = currentSkills.length === pendingSkills.length && currentSkills.every((id, index) => id === pendingSkills[index]);
    const hasContent = Boolean(current.text.trim()) || current.attachments.length > 0 || currentSkills.length > 0;
    if (hasContent && (composedMessageText(current.text, current.attachments) !== pending.text || !sameSkills)) {
      setPendingQueueRestore({ draft: current, intent: queueIntent });
      return;
    }
    applyQueueRestore(current);
  };
  const checkUncertainQueueSubmission = async () => {
    const current = draftRef.current, pending = current.queueSubmission;
    if (!pending?.uncertain || !onCheckQueueSubmission || checkingQueue || readingRef.current || sendingRef.current
      || current.pendingReads > 0 || current.submitting) return;
    // 核对期间仍可提交新的请求；迟到的结果只能结算发起时的那一份请求。
    const check = { draftId: current.id, submission: pending, transfer: queueTransferRef.current };
    queueCheckRef.current = check;
    setCheckingQueue(true);
    setNotice("正在核对内核队列…");
    const ownsResult = () => {
      const latest = draftRef.current;
      return alive.current && queueCheckRef.current === check && latest.id === check.draftId
        && latest.queueSubmission === pending && !latest.submitting && !sendingRef.current
        && queueTransferRef.current === check.transfer;
    };
    // 写入时再次核对草稿与请求快照，避免结果落到已被替换的请求上。
    const settle = (change: (draft: ComposerDraft) => ComposerDraft) => updateDraft(previous =>
      queueCheckRef.current === check && previous.id === check.draftId && previous.queueSubmission === pending
        && !previous.submitting ? change(previous) : previous);
    try {
      const result = await onCheckQueueSubmission(pending.id);
      if (!alive.current) return;
      // 核对期间已换了请求或开始新的转交：这次读取已过期，静默保留当前内容与提示。
      if (!ownsResult()) return;
      if (result.status === "unavailable") {
        setNotice(`暂时无法读取内核队列${result.reason ? `（${result.reason}）` : ""}；草稿和请求编号已保留，请稍后或恢复连接后再核对。`);
        return;
      }
      // 投影被截断时未命中只说明未载入，不能据此宣称队列里没有原消息。
      if (result.status === "unknown") {
        setNotice("队列记录过多，本次读取未包含原消息，无法确认是否已入队；草稿和请求编号已保留，请稍后再核对。");
        return;
      }
      if (result.status === "found") {
        settle(previous => {
          const currentText = composedMessageText(previous.text, previous.attachments);
          const matchesPending = currentText === pending.text;
          return { ...previous, text: matchesPending ? "" : previous.text,
            textVersion: previous.textVersion + (matchesPending && previous.text ? 1 : 0),
            attachments: matchesPending ? [] : previous.attachments, submitting: false, queueSubmission: undefined };
        });
        setNotice(`已核对：原消息在队列中，状态为${result.item.status === "queued" ? "排队中" : result.item.status === "delivering" ? "正在投递" : result.item.status === "delivered" ? "已投递" : "已暂停"}；不会重复提交。`);
        return;
      }
      settle(previous => ({ ...previous, submitting: false, queueSubmission: undefined }));
      setNotice(result.status === "cancelled" ? "已核对：原消息已撤回；当前输入可作为新请求提交。" : "已核对：队列中没有原消息；当前输入可作为新请求提交。");
    } catch (cause) {
      // 核对失败也要给出真实原因（如断连、超时），否则用户不知道该重连还是继续等待。
      if (ownsResult()) setNotice(`核对内核队列失败：${harnessErrorText(cause)}；草稿和请求编号已保留，请稍后重试。`);
    } finally {
      if (queueCheckRef.current === check) {
        queueCheckRef.current = null;
        if (alive.current) setCheckingQueue(false);
      }
    }
  };
  const selectModel = async (provider: string, id: string) => {
    if (!onSelectModel || modelPending || isRunning || blocked) return;
    setModelPending(true); setModelError("");
    try {
      const changed = await onSelectModel(provider, id);
      if (changed !== false) { setMenu(null); focusInput(); }
      else setModelError("模型设置未确认；当前选择保持不变。");
    } catch (cause) {
      setModelError(`模型设置失败：${harnessErrorText(cause)}；当前选择保持不变。`);
    } finally { setModelPending(false); }
  };
  const selectReasoning = async (effort: string | null) => {
    if (!sessionReasoning || sessionReasoning.pending) return;
    await sessionReasoning.select(effort);
  };
  const toggleSkill = (id: string) => updateDraft(previous => {
    const current = previous.skillIds ?? [];
    if (current.includes(id)) return { ...previous, skillIds: current.filter(skillId => skillId !== id) };
    return current.length >= 10 ? previous : { ...previous, skillIds: [...current, id] };
  });

  return <div className={`composer-surface ${home ? "home-composer" : ""} ${dragging ? "composer-drop-active" : ""}`}
    onDragEnter={event => { if (event.dataTransfer.types.includes("Files")) { event.preventDefault(); dragDepth.current += 1; setDragging(true); } }}
    onDragOver={event => { if (event.dataTransfer.types.includes("Files")) { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; } }}
    onDragLeave={event => { if (event.dataTransfer.types.includes("Files")) { event.preventDefault(); dragDepth.current = Math.max(0, dragDepth.current - 1); if (!dragDepth.current) setDragging(false); } }}
    onDrop={event => { if (!event.dataTransfer.types.includes("Files")) return; event.preventDefault(); dragDepth.current = 0; setDragging(false); void addFiles([...event.dataTransfer.files]); }}>
    {dragging && <div className="composer-drop-hint" aria-hidden="true"><IconFolder size={25} /><strong>添加文件作为上下文</strong><span>TXT、Markdown、JSON、CSV · 每个最多 200 KB</span></div>}
    {attachments.length > 0 && <div className="attachment-list">{attachments.map(file => <div className="attachment-chip" key={file.id} title={`${file.name} · ${Math.max(1, Math.ceil(file.size / 1000))} KB`}><IconFolder size={15} /><span>{file.name}<small>{Math.max(1, Math.ceil(file.size / 1000))} KB · 文本</small></span><button type="button" aria-label={`移除附件 ${file.name}`} title={submitting ? "正在转交消息，暂不能更改附件" : "移除附件"} disabled={submitting} onClick={() => updateDraft(previous => ({ ...previous, attachments: previous.attachments.filter(item => item.id !== file.id) }))}><IconClose size={12} /></button></div>)}</div>}
    {selectedSkillChips.length > 0 && <div className="composer-skill-chips" aria-label="已选运行时技能">{selectedSkillChips.map(chip => <div className={`composer-skill-chip${chip.stale ? " is-stale" : ""}`} key={chip.id} title={chip.stale ? `${chip.id} · 已不在当前技能目录中` : chip.description ?? chip.name}><IconSparkles size={11} /><span>{chip.name}</span><button type="button" aria-label={`移除技能：${chip.name}`} title={submitting ? "正在转交消息，暂不能更改技能" : "移除技能"} disabled={submitting} onClick={() => toggleSkill(chip.id)}><IconClose size={11} /></button></div>)}</div>}
    <SlashCommandList isOpen={slashMenuOpen} onClose={() => setSlashOpen(false)} onSelect={selectSlash} search={slashQuery} selectedIndex={selectedIndex} listboxId={slashListId} />
    <textarea aria-label="消息输入" aria-haspopup="listbox" aria-expanded={slashListVisible} aria-autocomplete="list"
      aria-controls={slashListVisible ? slashListId : undefined}
      aria-activedescendant={slashListVisible && slashActiveIndex >= 0 ? `${slashListId}-option-${slashActiveIndex}` : undefined}
      ref={element => { inputRef.current = element; if (typeof forwardedRef === "function") forwardedRef(element); else if (forwardedRef) forwardedRef.current = element; }} rows={2}
      placeholder={archived ? "已归档，恢复后可继续对话" : isRunning ? queueIntent === "steering" ? "补充当前任务要求…" : "安排当前任务结束后的下一步…" : blocked ? "另一个任务正在运行，请等待完成" : "和 BOSS Harness 一起工作"}
      title={history.length ? "↑ 调取已发送消息：有输入时只在该前缀的消息间移动 · ↓ 返回草稿 · Esc 退出历史" : undefined}
      value={value} onChange={event => { recall.current = { index: -1, draft: "" }; recallStash.current = null; clearRecallDraft(); change(event.target.value); }}
      onPaste={event => {
        const files = [...event.clipboardData.files];
        if (files.length) { event.preventDefault(); void addFiles(files); return; }
        const text = event.clipboardData.getData("text/plain");
        if (text.length >= 5000 && attachments.length < MAX_ATTACHMENTS && !readingRef.current && !readingAttachments && !submitting) {
          const file = new File([text], "粘贴的文本.txt", { type: "text/plain" });
          if (file.size <= MAX_ATTACHMENT_BYTES) { event.preventDefault(); void addFiles([file]); }
        }
      }}
      onCompositionStart={() => { composingRef.current = true; }} onCompositionEnd={() => { composingRef.current = false; }}
      onKeyDown={event => {
        if (event.nativeEvent.isComposing || composingRef.current || event.keyCode === 229) return;
        if (slashMenuOpen) {
          if ((event.key === "ArrowDown" || event.key === "ArrowUp") && slashOptions.length) { event.preventDefault(); setSelectedIndex(previous => (previous + (event.key === "ArrowDown" ? 1 : -1) + slashOptions.length) % slashOptions.length); return; }
          if (event.key === "Enter" || event.key === "Tab") {
            // 与列表渲染和 aria-activedescendant 使用同一个夹取后的索引。
            const option = slashOptions[slashActiveIndex];
            if (option && !event.shiftKey) { event.preventDefault(); selectSlash(option); return; }
            setSlashOpen(false);
          }
          if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setSlashOpen(false); return; }
        }
        // 上下键调取已发送消息：↑ 从草稿进入最新一条并向更早移动，↓ 向更近移动并最终恢复草稿。
        // 带修饰键时保留原生的选择与按词移动；输入法组合期间由上面的 composing 判断提前返回。
        const browsing = recall.current.index !== -1;
        const input = event.currentTarget;
        const direction = recallKeyDirection({
          key: event.key, selectionStart: input.selectionStart, selectionEnd: input.selectionEnd,
          singleLine: !value.includes("\n"),
          shiftKey: event.shiftKey, altKey: event.altKey, metaKey: event.metaKey, ctrlKey: event.ctrlKey,
        }, browsing);
        if (direction) {
          const next = direction === "older" ? recallOlder(history, recall.current, value) : recallNewer(history, recall.current, value);
          if (next.text !== value || next.state.index !== recall.current.index) {
            event.preventDefault();
            recall.current = next.state;
            rememberRecall(next.state, next.text);
            writeText(next.text); setNotice(""); setSelectedIndex(0); setSlashOpen(false);
            const atEnd = direction === "newer";
            requestAnimationFrame(() => { const area = inputRef.current; if (area) { const position = atEnd ? area.value.length : 0; area.setSelectionRange(position, position); } });
          }
          return;
        }
        if (event.key === "Escape" && browsing) {
          event.preventDefault(); event.stopPropagation();
          const draft = recall.current.draft;
          recall.current = { index: -1, draft: "" };
          recallStash.current = null;
          clearRecallDraft();
          change(draft);
          requestAnimationFrame(() => { const area = inputRef.current; if (area) area.setSelectionRange(area.value.length, area.value.length); });
          return;
        }
        if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(); }
      }} />
    {queueModeActive && onQueue && <div className="composer-queue-mode" role="group" aria-label="运行中消息处理方式">
      <button type="button" aria-pressed={queueIntent === "steering"} title="当前已发出的工具调用完成后，在下一次模型请求前加入此消息。" onClick={() => { setQueueIntent("steering"); if (selectedSkillIds.length) setNotice("转向消息不使用技能；所选技能仅用于排到后续回合的消息。"); }}>转向当前回合</button>
      <button type="button" aria-pressed={queueIntent === "followUp"} title="等当前任务自然结束后，再以新回合处理此消息。" onClick={() => setQueueIntent("followUp")}>排到后续回合</button>
    </div>}
    <div className="composer-controls">
      <div className="composer-control-left">
        <div className="popover-anchor">
          <button type="button" className={`composer-mode composer-skills-trigger ${menu === "skills" ? "is-open" : ""}`} aria-label={`选择运行时技能${selectedSkillIds.length ? `，已选 ${selectedSkillIds.length} 项` : ""}`} data-count={selectedSkillIds.length || undefined} title={submitting ? "正在转交消息，暂不能更改技能" : queueModeActive ? "所选技能应用于排到后续回合的消息；转向消息不使用技能" : "选择应用于消息的运行时技能"} aria-haspopup="menu" aria-expanded={menu === "skills"} disabled={submitting} onClick={() => toggleMenu("skills")}><IconSparkles size={14} /><span>技能{selectedSkillIds.length ? ` ${selectedSkillIds.length}` : ""}</span><IconChevronDown size={10} /></button>
          <Popover open={menu === "skills"} onClose={() => setMenu(null)} above label="选择运行时技能" className="composer-action-menu composer-skills-menu">
            <div className="composer-menu-heading">运行时技能</div>
            {skillCatalogState === "ready" && skills.length > 0 && <div className="composer-menu-search"><IconSearch size={15} /><input ref={skillInputRef} data-menu-autofocus aria-label="筛选技能" placeholder="搜索技能名称或描述…" value={skillQuery} onChange={event => setSkillQuery(event.target.value)} onKeyDown={event => {
              if (event.nativeEvent.isComposing) return;
              const options = event.currentTarget.closest(".composer-action-menu")?.querySelectorAll<HTMLButtonElement>(":scope > button[role='menuitemcheckbox']:not(:disabled)");
              if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                const option = event.key === "ArrowDown" ? options?.[0] : options?.[(options?.length ?? 0) - 1];
                if (option) { event.preventDefault(); event.stopPropagation(); option.focus(); }
              }
              if (event.key === "Enter" && options?.length) { event.preventDefault(); event.stopPropagation(); options[0]?.click(); }
            }} />{skillQuery && <button type="button" data-menu-keep-open aria-label="清除技能筛选" onClick={() => { setSkillQuery(""); skillInputRef.current?.focus(); }}><IconClose size={12} /></button>}</div>}
            {skillCatalogState === "loading" && <div className="composer-menu-empty">正在加载可用技能…</div>}
            {skillCatalogState === "unavailable" && <div className="composer-menu-empty">{preview ? "运行时技能仅在连接桌面 Harness 后可用。" : "连接本地 Harness 后可加载技能。"}</div>}
            {skillCatalogState === "error" && <div className="composer-menu-empty">技能目录读取失败{skillCatalogError ? `：${skillCatalogError}` : ""}。这只表示读取没有完成，不代表工作区没有技能；请重试。</div>}
            {skillCatalogState === "empty" && <div className="composer-menu-empty">当前工作区没有可用技能。</div>}
            {skillCatalogState === "ready" && filteredSkills.map(skill => <button type="button" role="menuitemcheckbox" aria-checked={selectedSkillIds.includes(skill.id)} key={skill.id} disabled={submitting || (selectedSkillIds.length >= 10 && !selectedSkillIds.includes(skill.id))} onClick={() => toggleSkill(skill.id)}><IconSparkles /><span>{skill.name}<small>{skill.description || "无描述"}</small></span>{selectedSkillIds.includes(skill.id) && <IconCheck className="menu-check" />}</button>)}
            {skillCatalogState === "ready" && skills.length > 0 && filteredSkills.length === 0 && <div className="composer-menu-empty">没有匹配的技能。</div>}
            {skillCatalogState === "ready" && selectedSkillIds.length >= 10 && <div className="composer-menu-footer">每回合最多选择 10 项技能。</div>}
            {hiddenSelectedSkills > 0 && <div className="composer-menu-footer">已选技能中有 {hiddenSelectedSkills} 项不在当前筛选结果中，仍会随消息应用。</div>}
            {staleSkillIds.length > 0 && skillCatalogState === "ready" && <div className="composer-menu-empty">{staleSkillIds.length} 项已选技能已不在当前目录中。</div>}
            {staleSkillIds.length > 0 && skillCatalogState === "ready" && <button type="button" disabled={submitting} onClick={() => updateDraft(previous => ({ ...previous, skillIds: previous.skillIds.filter(id => !staleSkillIds.includes(id)) }))}>清除不可用技能</button>}
            {selectedSkillIds.length > 0 && skillCatalogState !== "ready" && <button type="button" disabled={submitting} onClick={() => updateDraft(previous => ({ ...previous, skillIds: [] }))}>清除已选技能</button>}
            {skillProblems.length > 0 && <div className="composer-menu-footer" role="status">{skillProblems.length} 个技能未能加载；到「技能与工具」页查看原因。</div>}
            {skillCatalogState !== "unavailable" && onRefreshSkills && <button type="button" disabled={submitting || skillCatalogState === "loading"} onClick={onRefreshSkills}>{skillCatalogState === "error" ? "重试加载技能" : "刷新技能目录"}</button>}
            <div className="composer-menu-footer">所选技能应用于本次发送或排到后续回合的消息；转交成功后清空。</div>
          </Popover>
        </div>
        <div className="popover-anchor">
          <button type="button" className={`composer-icon ${menu === "add" ? "is-open" : ""}`} aria-label="添加附件或上下文" title="添加附件或上下文" aria-haspopup="menu" aria-expanded={menu === "add"} onClick={() => toggleMenu("add")}><IconPlus size={19} /></button>
          <Popover open={menu === "add"} onClose={() => setMenu(null)} above label="添加上下文" className="composer-action-menu">
            <div className="composer-menu-heading">添加上下文</div>
            <button type="button" disabled={readingAttachments || submitting || attachments.length >= MAX_ATTACHMENTS} onClick={() => { fileRef.current?.click(); setMenu(null); }}><IconFolder /><span>添加文件<small>TXT、Markdown、JSON、CSV</small></span><span className="menu-shortcut">本地</span></button>
            <div className="menu-divider" />
            {onLogin && <button type="button" onClick={() => { setMenu(null); onLogin(); }}><IconLock /><span>连接 BOSS 直聘<small>在当前会话右侧扫码登录</small></span></button>}
            <button type="button" onClick={openSlashMenu}><IconSparkles /><span>快捷指令</span><span className="menu-shortcut">/</span></button>
            <div className="composer-menu-footer">也可拖入文本文件，或粘贴较长文本作为附件。</div>
          </Popover>
        </div>
        <div className="popover-anchor">
          <button type="button" className={`permission-button ${menu === "permissions" ? "is-open" : ""}`} aria-label="执行权限" title="查看执行权限" aria-haspopup="menu" aria-expanded={menu === "permissions"} onClick={() => toggleMenu("permissions")}><IconShield size={15} /><span>{readOnly ? "只读会话" : "请求批准"}</span><IconChevronDown size={10} /></button>
          <Popover open={menu === "permissions"} onClose={() => setMenu(null)} above label="执行权限" className="composer-action-menu composer-permission-menu">
            <div className="composer-menu-heading">{readOnly ? "本会话允许哪些操作？" : "如何批准 BOSS Harness 的操作？"}</div>
            <button type="button" role="menuitemradio" aria-checked="true" onClick={() => { setMenu(null); focusInput(); }}><IconShield /><span>{readOnly ? "只读会话" : "请求批准"}<small>{readOnly ? "可读取职位与履历，服务端禁止对外写操作" : "对外沟通、投递等操作前由你确认"}</small></span><IconCheck className="menu-check" /></button>
            <button type="button" role="menuitemradio" aria-checked="false" disabled title="当前连接暂不支持自动审批"><IconSparkles /><span>代我批准<small>当前连接暂不支持自动审批</small></span></button>
            <button type="button" role="menuitemradio" aria-checked="false" disabled title="当前运行配置不提供完全访问"><IconLock /><span>完全访问<small>当前运行配置不提供完全访问</small></span></button>
            <div className="composer-menu-footer">{preview ? "当前为界面预览。权限选择以连接后的运行配置为准。" : readOnly ? "只读限制随会话保存，重启和创建分支后继续生效。" : "权限由运行配置管理；涉及对外操作仍需明确授权。"}</div>
          </Popover>
        </div>
        <div className="popover-anchor">
          <button type="button" className={`composer-mode ${menu === "mode" ? "is-open" : ""}`} aria-label="任务模式" title="选择任务模式" aria-haspopup="menu" aria-expanded={menu === "mode"} onClick={() => toggleMenu("mode")}><mode.icon size={14} /><span>{preview ? mode.name : "Agent"}</span><IconChevronDown size={10} /></button>
          <Popover open={menu === "mode"} onClose={() => setMenu(null)} above label="任务模式" className="composer-action-menu composer-mode-menu">
            <div className="composer-menu-heading">任务模式{preview && <span className="composer-menu-badge">预览</span>}</div>
            {MODES.map(item => <button type="button" role="menuitemradio" aria-checked={(preview ? currentMode : "agent") === item.id} key={item.id} disabled={(!preview && item.id !== "agent") || !onModeChange} onClick={() => { onModeChange?.(item.id); setMenu(null); focusInput(); }}><item.icon /><span>{item.name}<small>{!preview && item.id !== "agent" ? "当前连接暂不支持此模式" : item.detail}</small></span>{(preview ? currentMode : "agent") === item.id && <IconCheck className="menu-check" />}</button>)}
          </Popover>
        </div>
      </div>
      <div className="composer-control-right">
        <div className="popover-anchor">
          <button className={`composer-model ${menu === "model" ? "is-open" : ""}`} type="button" aria-label="选择模型" title={`当前模型：${modelName}`} aria-haspopup="menu" aria-expanded={menu === "model"} aria-busy={modelPending} onClick={() => { setModelError(""); toggleMenu("model"); }}><span>{modelName}</span><IconChevronDown size={11} /></button>
          <Popover open={menu === "model"} onClose={() => setMenu(null)} align="right" above label="选择模型" className="composer-action-menu composer-model-menu">
            <div className="composer-menu-heading">模型{preview && <span className="composer-menu-badge">预览</span>}</div>
            <div className="composer-menu-search"><IconSearch size={15} /><input ref={modelInputRef} data-menu-autofocus aria-label="搜索模型" placeholder="搜索模型…" value={modelQuery} onChange={event => setModelQuery(event.target.value)} onKeyDown={event => {
              if (event.nativeEvent.isComposing) return;
              if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                const options = event.currentTarget.closest(".composer-action-menu")?.querySelectorAll<HTMLButtonElement>(".composer-model-options > button:not(:disabled)");
                const option = (event.key === "ArrowDown" ? options?.[0] : options?.[(options?.length ?? 0) - 1])
                  ?? event.currentTarget.closest(".composer-action-menu")?.querySelector<HTMLButtonElement>(":scope > button:not(:disabled)");
                if (option) { event.preventDefault(); event.stopPropagation(); option.focus(); }
              }
              if (event.key === "Enter" && onSelectModel && filteredModels[0] && !modelPending) { event.preventDefault(); event.stopPropagation(); void selectModel(filteredModels[0].provider, filteredModels[0].id); }
            }} />{modelQuery && <button type="button" data-menu-keep-open aria-label="清除模型搜索" onClick={() => { setModelQuery(""); modelInputRef.current?.focus(); }}><IconClose size={12} /></button>}</div>
            <div className="composer-model-options">
              {filteredModels.map(model => {
                const name = "name" in model ? model.name.replace("Adaptive Router: ", "") : model.id;
                const selected = model.provider === activeModelProvider && model.id === activeModelId;
                return <button type="button" role="menuitemradio" aria-checked={selected} key={`${model.provider}:${model.id}`} disabled={!onSelectModel || modelPending || isRunning || blocked || (selected && !preview)} onClick={() => { void selectModel(model.provider, model.id); }}><span className="composer-model-monogram" aria-hidden="true">{model.provider.slice(0, 1)}</span><span>{name}<small>{model.provider}</small></span>{"badge" in model && model.badge && <span className="composer-menu-badge">{model.badge}</span>}{selected && <IconCheck className="menu-check" />}</button>;
              })}
              {modelPending && <div className="composer-menu-footer" role="status">正在保存模型设置…</div>}
              {modelError && <div className="composer-menu-footer" role="alert">{modelError}</div>}
              {!filteredModels.length && <div className="composer-menu-empty">{models.length ? "未找到匹配模型" : preview ? "未找到匹配模型" : "没有可用的本机模型线路"}</div>}
              {!preview && currentDescriptor && configuredModelMatches && !filteredModels.some(model => model.id === activeModelId && model.provider === activeModelProvider) && <div className="composer-configured-model"><span className="composer-model-monogram" aria-hidden="true"><IconSparkles size={15} /></span><span>{modelName}<small>当前会话</small></span><IconCheck className="menu-check" /></div>}
            </div>
            {!preview && sessionReasoning && <>
              <div className="menu-divider" /><div className="composer-menu-heading">会话推理强度</div>
              {sessionReasoning.data && <>
                <button type="button" role="menuitemradio" data-menu-keep-open aria-checked={sessionReasoning.data.effort === null} disabled={sessionReasoning.pending} onClick={() => { void selectReasoning(null); }}><IconSparkles /><span>继承配置<small>{sessionReasoning.data.configuredEffort ?? "供应商默认"}</small></span>{sessionReasoning.data.effort === null && <IconCheck className="menu-check" />}</button>
                {sessionReasoning.data.availableEfforts.map(effort => <button type="button" role="menuitemradio" data-menu-keep-open aria-checked={sessionReasoning.data?.effort === effort} key={effort} disabled={sessionReasoning.pending} onClick={() => { void selectReasoning(effort); }}><span>{effort}</span>{sessionReasoning.data?.effort === effort && <IconCheck className="menu-check" />}</button>)}
                {!sessionReasoning.data.supported && <div className="composer-menu-footer" role="alert">保存的 {sessionReasoning.data.effort} 不在当前模型支持列表中；请重新选择。</div>}
                <div className="composer-menu-footer">{sessionReasoning.data.availableEfforts.length ? "保存到当前会话；下次请求准备时生效。" : "当前模型未声明可选推理档位。"}</div>
              </>}
              {sessionReasoning.error && <div className="composer-menu-footer" role="alert">{sessionReasoning.error}</div>}
              {(!sessionReasoning.data || sessionReasoning.error) && <button type="button" disabled={sessionReasoning.pending} onClick={() => { void sessionReasoning.refresh(); }}><span>重新加载推理设置</span></button>}
            </>}
            <div className="menu-divider" /><button type="button" disabled={!onOpenSettings} onClick={() => { setMenu(null); onOpenSettings?.(); }}><IconSettings /><span>模型与连接设置</span></button>
          </Popover>
        </div>
        <button type="button" className="composer-submit" aria-label={queueModeActive ? queueIntent === "steering" ? "转向当前回合" : "排入后续回合" : "发送消息"} title={queueModeActive ? queueIntent === "steering" ? "转向当前回合 · Enter" : "排入后续回合 · Enter" : submitting ? "正在转交消息" : "发送 · Enter"} disabled={archived || (blocked && !isRunning) || readingAttachments || submitting || (!value.trim() && !attachments.length)} onClick={() => { void submit(); }}><IconSend size={18} /></button>
        {isRunning && onInterrupt && <button type="button" className="composer-stop" aria-label="停止任务" title="停止当前任务" onClick={onInterrupt}><IconStop size={15} /></button>}
      </div>
    </div>
    {skillQueueNotice && <div className="composer-notice" role="status">{skillQueueNotice}<button type="button" className="composer-menu-retry" disabled={submitting} onClick={() => updateDraft(previous => ({ ...previous, skillIds: [] }))}>清除已选技能</button></div>}
    {(notice || readingAttachments || submitting) && <div className="composer-notice" role="status">{notice || (readingAttachments ? "正在读取附件…" : "正在转交消息…")}</div>}
    {uncertainQueue && <div className="composer-notice-actions">
      <button type="button" disabled={queueRestoreBusy} title={queueRestoreBusy ? "正在读取附件、转交消息或核对队列，请稍候" : undefined} onClick={restoreQueueSubmission}>恢复待确认消息</button>
      <button type="button" disabled={!onCheckQueueSubmission || queueRestoreBusy} title={!checkingQueue && queueRestoreBusy ? "正在读取附件或转交消息，请稍候" : undefined} onClick={() => { void checkUncertainQueueSubmission(); }}>{checkingQueue ? "正在核对队列…" : "核对服务端队列"}</button>
    </div>}
    {currentQueueRestore && <div className="composer-notice" role="alert" data-queue-restore-confirm>
      <span>恢复待确认消息会替换当前未发送的正文、附件与已选技能。</span>
      <div className="composer-notice-actions">
        <button type="button" onClick={() => applyQueueRestore(currentQueueRestore.draft, currentQueueRestore)}>替换</button>
        <button type="button" onClick={() => { setPendingQueueRestore(null); focusInput(); }}>取消</button>
      </div>
    </div>}
    <input ref={fileRef} className="visually-hidden" type="file" accept=".txt,.md,.markdown,.json,.csv" multiple onChange={event => { const files = [...(event.target.files ?? [])]; event.target.value = ""; void addFiles(files); }} />
  </div>;
});
