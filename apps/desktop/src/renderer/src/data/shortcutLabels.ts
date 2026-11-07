import { currentCommandPlatform, type CommandPlatform } from "./shortcuts";

/**
 * macOS 修饰键符号与其余平台的键名。
 *
 * 非 macOS 平台的组合键惯用 `+` 连接（`Ctrl+Shift+A`），而说明里的 macOS 写法是
 * 空格分隔（`⌘ ⇧ A`）；直接替换符号会得到难以阅读的 `Ctrl Shift A` 或 `CtrlShiftK`，
 * 所以键名自带 `+`，替换后再清掉加号后的空格与孤立的尾随加号。
 */
const MODIFIER_LABELS: ReadonlyArray<readonly [string, string]> = [
  ["⌘", "Ctrl+"],
  ["⌥", "Alt+"],
  ["⇧", "Shift+"],
];

/**
 * 快捷键说明里的键位文案。
 *
 * 说明面板、设置页、标题栏提示、菜单与侧栏按钮共用这一条规则：macOS 保留
 * `⌘` / `⌥` / `⇧`，其余平台改写为 `Ctrl+` / `Alt+` / `Shift+`。事件匹配早已按平台
 * 选择主修饰键（`isCommandChord`），说明却一直写死 macOS 符号：Windows / Linux 用户
 * 只能靠脚注换算，而脚注只提到 `⌘`，Alt 与 Shift 仍要自己猜；设置页连脚注都没有。
 * 按平台渲染后，说明与实际按键重新对齐。
 *
 * 只替换修饰键符号，不碰按键与分隔符：`⌘ [ / ⌘ ]` 里的 `/` 原样保留，
 * `Esc Esc`、`↑ / ↓` 与单独的 `/` 也不受影响。单独一个修饰键（如设置页把 `⌘` 与
 * `N` 分成两个 `<kbd>`）不会留下尾随加号。
 */
export function shortcutKeyLabel(label: string, platform: CommandPlatform): string {
  if (platform === "mac") return label;
  const replaced = MODIFIER_LABELS.reduce((text, [symbol, name]) => text.split(symbol).join(name), label);
  return replaced.replace(/\+ /g, "+").replace(/\+$/, "");
}

/** 按当前运行平台渲染。组件只依赖这一个入口，避免每处各自读取平台。 */
export function currentShortcutLabel(label: string): string {
  return shortcutKeyLabel(label, currentCommandPlatform());
}
