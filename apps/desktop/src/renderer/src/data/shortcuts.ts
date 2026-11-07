export interface CommandChordEvent {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  altKey: boolean;
}

/** 主修饰键所属平台：macOS 使用 Command，其余平台使用 Control。 */
export type CommandPlatform = "mac" | "other";

/**
 * 把平台标识归一为快捷键族。preload 给出 `process.platform`（darwin / win32 / linux），
 * 浏览器预览给出 `navigator.platform`（MacIntel / Win32 / Linux x86_64）。
 */
export function resolveCommandPlatform(platform: string | undefined | null): CommandPlatform {
  const value = typeof platform === "string" ? platform.trim().toLowerCase() : "";
  return value === "darwin" || value.startsWith("mac") ? "mac" : "other";
}

/** 当前运行平台：优先读 preload 暴露的 process.platform，浏览器预览退回 navigator.platform。 */
export function currentCommandPlatform(): CommandPlatform {
  try {
    const platform = typeof window === "undefined" ? undefined : window.boss?.versions?.platform;
    if (typeof platform === "string" && platform) return resolveCommandPlatform(platform);
  } catch { /* 桥接不可用时继续使用浏览器信息。 */ }
  try {
    return resolveCommandPlatform(typeof navigator === "undefined" ? undefined : navigator.platform);
  } catch { /* 平台信息不可读时按非 macOS 处理。 */ }
  return "other";
}

/**
 * 全局快捷键的精确匹配：只接受当前平台的主修饰键（macOS 为 Command，其余为 Control），
 * 且 Alt 状态与声明一致。另一平台的修饰键必须未按下：macOS 的 Ctrl 组合是系统文本
 * 编辑（⌃B / ⌃K / ⌃F / ⌃N / ⌃⇧A），Windows / Linux 的 Meta 组合归系统所有，应用不再抢占。
 * 未声明的组合（如 ⌘⇧N、⌘⌥K）同样不触发，避免与其他应用冲突。
 *
 * 字母键要求 Shift 状态精确匹配：`⇧K` 的 `event.key` 仍是 `K`，只能靠 shiftKey 区分
 * `⌘K` 与 `⌘⇧K`。符号键不同，`event.key` 就是字符本身——美式布局下只有未按 Shift 才会
 * 得到 `[` / `;` / `/`，约束 Shift 是冗余的；德语（`;` = ⇧+,、`/` = ⇧+7）与法语
 * （`/` = ⇧+:）等布局必须按 Shift 才能输入这些字符，强制 shiftKey 为假会让 `⌘ ;` /
 * `⌘ /` 永远无法触发。因此符号键在调用方未声明 shift 时只按字符匹配；
 * 显式声明 shift 时仍按声明精确匹配。
 *
 * AltGr 产生的符号（德语 `[` = AltGr+8）仍不匹配：Windows / Linux 上 AltGr 报告为
 * Ctrl+Alt，放宽 Alt 会让 Ctrl+Alt+字母 误触 Ctrl+字母，代价大于收益。
 */
export function isCommandChord(
  event: CommandChordEvent,
  key: string,
  modifiers: { shift?: boolean; alt?: boolean } = {},
  platform: CommandPlatform = currentCommandPlatform(),
): boolean {
  const command = platform === "mac" ? event.metaKey : event.ctrlKey;
  const foreign = platform === "mac" ? event.ctrlKey : event.metaKey;
  // 多字符键（如 "Enter"）按严格匹配处理，避免将来引入组合键时被当成符号键放宽。
  const symbolKey = key.length === 1 && !/[a-z]/i.test(key);
  const shiftMatches = symbolKey && modifiers.shift === undefined
    ? true
    : event.shiftKey === (modifiers.shift === true);
  return !foreign && command
    && event.key.toLowerCase() === key
    && shiftMatches
    && event.altKey === (modifiers.alt === true);
}

/** 通知面板快捷键：⌘⇧A（Windows / Linux 为 Ctrl+Shift+A）；带 Alt、缺少 Shift 或按下另一平台修饰键时不匹配。 */
export function isNotificationsShortcut(event: CommandChordEvent, platform: CommandPlatform = currentCommandPlatform()): boolean {
  return isCommandChord(event, "a", { shift: true }, platform);
}
