import { useState, useRef, useEffect } from "react";
import { Composer } from "./Composer";
import { IconFolder, IconChevronDown, IconSparkles, IconSearch, IconChat, IconCockpit, IconCheck, IconPlus } from "../components/Icons";
import { Popover } from "../components/Popover";
import { currentShortcutLabel } from "../data/shortcutLabels";
import type { ProjectFolder, ConversationMode } from "../data/mockData";
import type { ModelDescriptor, SkillDescriptor, SkillProblem } from "@boss-harness/protocol";
import type { SkillCatalogState } from "../data/harnessBridge";
import { withDraftText, type ComposerDraft, type UpdateComposerDraft, type ComposerSend } from "../data/composerDraft";
import { suggestionFillIntent } from "../data/homeSuggestions";
interface Props {
  onStartSessionWithPrompt: (prompt: string, domainId: string, provider: string, modelId: string, skillIds?: string[]) => ReturnType<ComposerSend>;
  models?: ModelDescriptor[]; activeModelProvider?: string; activeModelId: string;
  onSelectModel?: (provider: string, id: string) => void | boolean | Promise<void | boolean>; currentMode: ConversationMode; onModeChange: (mode: ConversationMode) => void;
  configuredModelLabel?: string;
  selectedProjectId: string; onSelectProject: (id: string) => void; onNewProject: () => void;
  folders: ProjectFolder[]; preview: boolean; harnessUp: boolean; blocked?: boolean; onOpenSettings: () => void; draft: ComposerDraft; onDraftChange: UpdateComposerDraft;
  skills: SkillDescriptor[]; skillCatalogState: SkillCatalogState; skillCatalogError?: string; onRefreshSkills: () => void; skillProblems?: SkillProblem[];
  /** 工作区模板等待替换确认：只有用户确认后才写入，取消则保留现有草稿。 */
  pendingTemplate?: string | null; onResolveTemplate?: (apply: boolean) => void;
  /** 新聊天等待丢弃确认；空字符串表示不指定项目，null 表示没有待定操作。 */
  pendingNewTaskProject?: string | null; onResolveNewTask?: (discard: boolean) => void;
}
/** 确认条文案：按草稿里实际会丢失的内容列出附件与已选技能，避免「与附件与技能」这类叠词。 */
function templateConfirmText(draft: ComposerDraft): string {
  const parts = [draft.attachments.length > 0 ? "附件" : "", (draft.skillIds ?? []).length > 0 ? "已选技能" : ""].filter(Boolean);
  const lost = parts.length === 0 ? "草稿" : parts.length === 1 ? `草稿与${parts[0]}` : `草稿、${parts[0]}与${parts[1]}`;
  return `工作区模板会替换当前未发送的 ${lost}。`;
}
const suggestions = [
  { icon: IconSearch, title: "拆解岗位画像", detail: "把招聘需求转化为清晰的筛选依据", prompt: "请帮我拆解一个岗位的必备能力、加分项与待确认问题，并注明判断依据。" },
  { icon: IconFolder, title: "对齐候选人履历", detail: "从经历与证据出发，找到合适的人", prompt: "请为我建立候选人履历与岗位要求的比对框架，区分来源事实、模型判断和待确认信息。" },
  { icon: IconChat, title: "准备沟通话术", detail: "写一封有针对性、值得回复的邀约", prompt: "请帮我起草一份个性化招聘邀约，只准备草稿，等待我确认后再发送。" },
  { icon: IconCockpit, title: "复盘招聘进展", detail: "梳理任务进度，明确下一步行动", prompt: "请帮我梳理当前招聘任务的进度、阻塞点与下一步待办，所有结论应附上依据。" },
];
export function HomeView(props: Props) {
  const value = props.draft.text;
  const [pendingSuggestion, setPendingSuggestion] = useState<string | null>(null);
  const setValue = (text: string) => { setPendingSuggestion(null); props.onDraftChange(previous => withDraftText(previous, text)); };
  const project = props.selectedProjectId;
  const [projectMenu, setProjectMenu] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  const pendingNewTask = props.pendingNewTaskProject != null;
  const draftBusy = props.draft.pendingReads > 0 || props.draft.submitting;
  const newTaskProject = props.folders.find(folder => folder.id === props.pendingNewTaskProject)?.name;
  useEffect(() => {
    if (pendingNewTask || props.pendingTemplate) setPendingSuggestion(null);
  }, [pendingNewTask, props.pendingTemplate]);
  // 建议卡会整段改写输入框：已有未发送正文时先显示确认条，避免一次误点丢掉草稿。
  const applySuggestion = (prompt: string) => {
    props.onResolveNewTask?.(false); props.onResolveTemplate?.(false);
    if (suggestionFillIntent(value, prompt) === "confirm") { setPendingSuggestion(prompt); return; }
    setValue(prompt);
    ref.current?.focus();
  };
  useEffect(() => { ref.current?.focus({ preventScroll: true }); }, []);
  return <div className="home-screen" data-screen-label="新聊天">
    <div className="home-content">
      <div className="home-emblem"><IconSparkles size={31} /></div>
      <h1>今天，一起推进什么？</h1>
      <div className="home-project-picker popover-anchor">
        <button onClick={() => setProjectMenu(!projectMenu)} aria-haspopup="menu" aria-expanded={projectMenu}><IconFolder size={14} /><span>{props.folders.find(folder => folder.id === project)?.name ?? "选择招聘项目"}</span><IconChevronDown size={11} /></button>
        <Popover open={projectMenu} onClose={() => setProjectMenu(false)} label="选择招聘项目">
          <button role="menuitemradio" aria-checked={!project} onClick={() => { props.onSelectProject(""); setProjectMenu(false); }}><IconChat size={15} />不指定项目{!project && <IconCheck className="menu-check" />}</button><div className="menu-divider" />
          {props.folders.map(folder => <button role="menuitemradio" aria-checked={project === folder.id} key={folder.id} onClick={() => { props.onSelectProject(folder.id); setProjectMenu(false); }}><IconFolder size={15} />{folder.name}{project === folder.id && <IconCheck className="menu-check" />}</button>)}
          <div className="menu-divider" /><button onClick={() => { setProjectMenu(false); props.onNewProject(); }}><IconPlus size={15} />新建项目</button>
          <div className="menu-note">项目作为任务上下文随消息提供。</div>
        </Popover>
      </div>
      <Composer ref={ref} value={value} onChange={setValue} draft={props.draft} onDraftChange={props.onDraftChange} home readOnly={!props.preview} preview={props.preview} blocked={props.blocked} models={props.models} activeModelProvider={props.activeModelProvider} activeModelId={props.activeModelId} configuredModelLabel={props.configuredModelLabel} onSelectModel={props.onSelectModel} currentMode={props.currentMode} onModeChange={props.onModeChange} onOpenSettings={props.onOpenSettings} skills={props.skills} skillCatalogState={props.skillCatalogState} skillCatalogError={props.skillCatalogError} onRefreshSkills={props.onRefreshSkills} skillProblems={props.skillProblems}
        onSend={(text, skillIds) => props.onStartSessionWithPrompt(project ? `招聘项目：${props.folders.find(folder => folder.id === project)?.name}\n\n${text}` : text, "precision-match", props.activeModelProvider ?? "", props.activeModelId, skillIds)} />
      <div className="starter-prompts">
        {suggestions.map(item => <button key={item.title} onClick={() => applySuggestion(item.prompt)}><item.icon size={18} /><strong>{item.title}</strong><span>{item.detail}</span></button>)}
      </div>
      {pendingSuggestion && <div className="home-suggestion-confirm" role="alert">
        <span>建议会替换当前未发送的草稿。</span>
        <button type="button" onClick={() => { setValue(pendingSuggestion); ref.current?.focus(); }}>替换</button>
        <button type="button" onClick={() => setPendingSuggestion(null)}>取消</button>
      </div>}
      {props.pendingTemplate && <div className="home-suggestion-confirm" role="alert" data-home-template-confirm>
        <span>{templateConfirmText(props.draft)}</span>
        <button type="button" disabled={draftBusy} onClick={() => { props.onResolveTemplate?.(true); ref.current?.focus(); }}>替换</button>
        <button type="button" onClick={() => props.onResolveTemplate?.(false)}>取消</button>
        {draftBusy && <span>正在读取附件或转交消息，请稍候。</span>}
      </div>}
      {pendingNewTask && <div className="home-suggestion-confirm" role="alert" data-home-new-task-confirm>
        <span>{newTaskProject ? `在「${newTaskProject}」开始新聊天` : "开始新聊天"}将清空首页未发送的正文、附件与已选技能。</span>
        <button type="button" disabled={draftBusy} onClick={() => { props.onResolveNewTask?.(true); ref.current?.focus(); }}>丢弃草稿并开始</button>
        <button type="button" onClick={() => { props.onResolveNewTask?.(false); ref.current?.focus(); }}>取消</button>
        {draftBusy && <span>正在读取附件或转交消息，请稍候。</span>}
      </div>}
      <div className="home-keyboard-hint"><span><kbd>/</kbd> 快捷指令</span><span><kbd>{currentShortcutLabel("⇧ Enter")}</kbd> 换行</span></div>
    </div>
    <div className="workspace-status" role="status"><span className={props.preview || !props.harnessUp ? "status-dot preview" : "status-dot"} />{props.preview ? "界面预览 · 使用示例数据" : props.harnessUp ? "已连接本地招聘 Harness" : "本地招聘 Harness 未连接"}<span className="status-divider">·</span>{props.preview ? "对外操作由你确认" : "新会话默认只读"}</div>
  </div>;
}
