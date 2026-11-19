#!/usr/bin/env python3
"""核对窗口状态的解析、恢复与原子保存边界。

窗口状态来自用户可改的 JSON，恢复前必须整体校验并按当前显示器收敛，否则下一次
启动可能完全看不见窗口。保存用同目录独占临时文件加改名，临时名带进程号、时间戳
与计数器，`EEXIST` 说明路径被预植文件或链接占用，不能删除别人的文件。移动、缩放
后防抖保存，关闭前再保存一次；最大化时保存还原后的位置。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE = "apps/desktop/src/main/windowState.ts"
INDEX = "apps/desktop/src/main/index.ts"

STATE_FRAGMENTS = (
    "export const MIN_WINDOW_WIDTH = 240;",
    "export const MIN_WINDOW_HEIGHT = 160;",
    "const DEFAULT_WINDOW_WIDTH = 1440;",
    "const DEFAULT_WINDOW_HEIGHT = 900;",
    "const MAX_WINDOW_SIZE = 16_384;",
    "const MIN_VISIBLE_WIDTH = 80;",
    "const MIN_VISIBLE_HEIGHT = 40;",
    "try { value = JSON.parse(text); } catch { return null; }",
    "if (!value || typeof value !== \"object\" || Array.isArray(value)) return null;",
    "if (![x, y, width, height].every(item => typeof item === \"number\" && Number.isSafeInteger(item))) return null;",
    "maximized: state.maximized === true };",
    "width: Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x),",
    "height: Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y),",
    "return value.width > 0 && value.height > 0 ? value.width * value.height : 0;",
    "const largest = workAreas.reduce<Rectangle | null>((best, area) =>",
    "!best || area.width * area.height > best.width * best.height ? area : best, null);",
    "width: Math.min(DEFAULT_WINDOW_WIDTH, largest ? Math.max(MIN_WINDOW_WIDTH, largest.width) : DEFAULT_WINDOW_WIDTH),",
    "height: Math.min(DEFAULT_WINDOW_HEIGHT, largest ? Math.max(MIN_WINDOW_HEIGHT, largest.height) : DEFAULT_WINDOW_HEIGHT),",
    "if (!state || workAreas.length === 0) return fallback;",
    "const saved: Rectangle = state;",
    "return value.width >= MIN_VISIBLE_WIDTH && value.height >= MIN_VISIBLE_HEIGHT;",
    "if (!visible) return fallback;",
    "const target = workAreas.reduce((best, area) => overlapArea(saved, area) > overlapArea(saved, best) ? area : best);",
    "const width = Math.min(state.width, target.width);",
    "const height = Math.min(state.height, target.height);",
    "x: Math.min(Math.max(state.x, target.x), target.x + target.width - width),",
    "y: Math.min(Math.max(state.y, target.y), target.y + target.height - height),",
    "maximized: state.maximized,",
    "try { return parseWindowState(readFileSync(path, \"utf8\")); } catch { return null; }",
    "writeExclusive: (path, text) => writeFileSync(path, text, { encoding: \"utf8\", mode: 0o600, flag: \"wx\" }),",
    "rename: (from, to) => renameSync(from, to),",
    "remove: path => unlinkSync(path),",
    "let tempSequence = 0;",
    "tempSequence = (tempSequence + 1) % 1_000_000;",
    "return `${path}.${process.pid}.${Date.now().toString(36)}.${tempSequence.toString(36)}.tmp`;",
    "const temp = windowStateTempPath(path);",
    "const text = JSON.stringify(state);",
    "if ((error as NodeJS.ErrnoException)?.code !== \"EEXIST\") {",
    "} catch {\n    try { ops.remove(temp); } catch { /* 清理失败也不影响退出。 */ }\n  }",
    "let timer: ReturnType<typeof setTimeout> | undefined;",
    "if (window.isDestroyed()) return;",
    "writeWindowState(path, { ...window.getNormalBounds(), maximized: window.isMaximized() });",
    "timer = setTimeout(() => { timer = undefined; save(); }, 500);",
    "window.on(\"resize\", schedule);",
    "window.on(\"move\", schedule);",
    "window.on(\"close\", () => { if (timer !== undefined) clearTimeout(timer); timer = undefined; save(); });",
)
INDEX_FRAGMENTS = (
    "const statePath = join(app.getPath(\"userData\"), \"window-state.json\");",
    "const restored = restoreWindowState(readWindowState(statePath), screen.getAllDisplays().map(display => display.workArea));",
    "mainWindow = createMainWindow(restored);",
    "trackWindowState(mainWindow, statePath);",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_window_state() -> int:
    state = _read(STATE)
    index = _read(INDEX)
    checked = 0
    checked += _expect(STATE_FRAGMENTS, state, STATE)
    checked += _expect(INDEX_FRAGMENTS, index, INDEX)
    # 解析：整数、尺寸上下限，任何一项不合格都整体丢弃。
    checked += _ordered(
        (
            "try { value = JSON.parse(text); } catch { return null; }",
            "if (!value || typeof value !== \"object\" || Array.isArray(value)) return null;",
            "if (![x, y, width, height].every(item => typeof item === \"number\" && Number.isSafeInteger(item))) return null;",
            "if ((width as number) < MIN_WINDOW_WIDTH || (height as number) < MIN_WINDOW_HEIGHT ||",
            "return { x: x as number, y: y as number, width: width as number, height: height as number, maximized: state.maximized === true };",
        ),
        state,
        STATE,
    )
    # 恢复：至少一块工作区里有可见部分，再收敛到重叠最多的工作区。
    checked += _ordered(
        (
            "if (!state || workAreas.length === 0) return fallback;",
            "const visible = workAreas.some(area => {",
            "if (!visible) return fallback;",
            "const target = workAreas.reduce((best, area) => overlapArea(saved, area) > overlapArea(saved, best) ? area : best);",
            "x: Math.min(Math.max(state.x, target.x), target.x + target.width - width),",
        ),
        state,
        STATE,
    )
    # 保存：独占临时文件 → 改名 → 失败清理；EEXIST 不删除既有路径。
    checked += _ordered(
        (
            "const temp = windowStateTempPath(path);",
            "ops.writeExclusive(temp, text);",
            "if ((error as NodeJS.ErrnoException)?.code !== \"EEXIST\") {",
            "ops.rename(temp, path);",
        ),
        state,
        STATE,
    )
    # 防抖保存：resize / move 触发，close 前补一次。
    checked += _ordered(
        (
            "window.on(\"resize\", schedule);",
            "window.on(\"move\", schedule);",
            "window.on(\"close\", () => { if (timer !== undefined) clearTimeout(timer); timer = undefined; save(); });",
        ),
        state,
        STATE,
    )
    # 反向断言：保存必须走临时文件，最大化时不得保存当前全屏边界。
    if "writeFileSync(path, text)" in state:
        raise ValueError(f"{STATE} 不得直接写目标文件")
    if "window.getBounds()" in state:
        raise ValueError(f"{STATE} 最大化时必须保存还原后的边界")
    return checked + 1


def main() -> int:
    try:
        checked = check_window_state()
    except ValueError as error:
        print(f"窗口状态边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"窗口状态边界一致：{checked} 项解析、恢复与原子保存防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
