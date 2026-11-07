import { currentCommandPlatform } from "../data/shortcuts";
import { shortcutKeyLabel } from "../data/shortcutLabels";
import { ModalSurface } from "./ModalSurface";
const GROUPS: Array<{ title: string; shortcuts: Array<[keys: string, description: string]> }> = [
  { title: "工作区", shortcuts: [
    ["⌘ K", "搜索聊天"], ["⌘ ⇧ A", "通知与待审批"], ["⌘ F", "在当前聊天中查找"], ["⌘ N", "新聊天"], ["⌘ B", "切换项目侧栏"],
    ["⌘ ⌥ B", "切换聊天摘要"], ["⌘ [ / ⌘ ]", "后退 / 前进"], ["⌘ ,", "打开设置"], ["⌘ /", "键盘快捷键"],
  ] },
  { title: "输入", shortcuts: [["Enter", "发送消息"], ["⇧ Enter", "换行"], ["/", "选择快捷指令"], ["↑ / ↓", "选择菜单项"], ["Esc", "关闭菜单或弹窗"]] },
  { title: "项目扩展", shortcuts: [["⌘ ⇧ K", "运行状态"], ["⌘ ;", "快速提问"], ["Esc Esc", "会话回溯 / 新建分支"]] },
];
const FOOTER = "运行中的任务可通过输入框右侧的停止按钮中断。";
export function KeyboardShortcutsModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  if (!isOpen) return null;
  const platform = currentCommandPlatform();
  return <ModalSurface title="键盘快捷键" onClose={onClose} className="shortcuts-dialog">
    <div className="shortcuts-content">{GROUPS.map(group => <section key={group.title}><h3>{group.title}</h3>{group.shortcuts.map(([keys, description]) => <div className="shortcut-row" key={keys}><span>{description}</span><kbd>{shortcutKeyLabel(keys, platform)}</kbd></div>)}</section>)}<p className="dialog-note">{platform === "mac" ? "macOS 使用 ⌘ 作为主修饰键；Ctrl 组合保留给输入框文本编辑。" : "Windows / Linux 使用 Ctrl 作为主修饰键，Alt 与 Shift 分别对应 macOS 的 ⌥ 与 ⇧。"}{FOOTER}</p></div>
  </ModalSurface>;
}
