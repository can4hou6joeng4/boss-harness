#!/usr/bin/env python3
"""核对桌面启动接管、单实例与退出确认边界。

存在运行中回合时退出必须先弹原生确认框，默认按钮与 Esc 都落在「继续运行」，确认框
重复触发只保留一个；确认或无法显示时才继续退出并清理自检与 Host。首次以新名字启动
时只接管空的新 userData 目录：旧目录非空不覆盖、删除空壳失败就不改名、改名失败保留
旧目录；整个过程不得递归删除或复制用户数据。后启动的实例只激活已有窗口。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
QUIT = "apps/desktop/src/main/quitConfirmation.ts"
HARNESS = "apps/desktop/src/main/harness.ts"
PROFILE = "apps/desktop/src/main/profile.ts"
INDEX = "apps/desktop/src/main/index.ts"

QUIT_FRAGMENTS = (
    'import type { MessageBoxOptions } from "electron";',
    'export type QuitConfirmationOptions = Pick<MessageBoxOptions,',
    '"type" | "title" | "message" | "detail" | "buttons" | "defaultId" | "cancelId" | "noLink">;',
    "const count = Number.isFinite(runningTurns) ? Math.floor(runningTurns) : 0;",
    "if (count < 1) return null;",
    'type: "warning",',
    'title: "退出 BOSS Harness",',
    'message: count === 1 ? "有 1 个招聘任务正在运行" : `有 ${count} 个招聘任务正在运行`,',
    'detail: "现在退出会中断正在运行的回合；已排队但尚未开始的后续消息会保留，已执行的招聘操作不会撤回。",',
    'buttons: ["继续运行", "停止并退出"],',
    "defaultId: 0,",
    "cancelId: 0,",
    "noLink: true,",
)
HARNESS_FRAGMENTS = (
    "let quitConfirmed = false;",
    "let quitPromptOpen = false;",
    "if (quitConfirmed) return true;",
    "const content = quitConfirmationContent(turnStartedAt.size);",
    "if (!content) return true;",
    "event.preventDefault();",
    "if (quitPromptOpen) return false;",
    "quitPromptOpen = true;",
    "const parent = [...windows].find((window) => !window.isDestroyed());",
    "prompt = parent ? dialog.showMessageBox(parent, content) : dialog.showMessageBox(content);",
    'prompt = Promise.reject(new Error("quit confirmation could not open"));',
    "void prompt.then(({ response }) => {",
    "if (response !== 1) { revealWindow(); return; }",
    "if (response !== 1) { revealWindow(); return; }\n    quitConfirmed = true;\n    app.quit();",
    "}, () => {\n    // 确认框无法显示或完成时按用户明确的退出意图继续退出，避免应用无法关闭。\n    quitPromptOpen = false;\n    quitConfirmed = true;\n    app.quit();\n  });",
    "app.quit();",
    "if (!confirmQuit(event)) return;",
    "platformLogin.cancel(); diagnostics?.reset(); diagnostics = null; startupCheckTarget = null;",
    "manualStartupCheck.cancel();",
    "manager.dispose(); host = null; windows.clear();",
)
PROFILE_FRAGMENTS = (
    'import { existsSync, readdirSync, renameSync, rmdirSync } from "node:fs";',
    "try {\n    return readdirSync(path).length;\n  } catch (error) {",
    'return (error as NodeJS.ErrnoException)?.code === "ENOENT" ? 0 : null;',
    "if (current === legacy || !existsSync(legacy)) return current;",
    "const entries = directoryEntryCount(current);",
    "if (entries === null || entries > 0) return current;",
    "if (existsSync(current)) {",
    "rmdirSync(current);\n    } catch {\n      return current;\n    }",
    "renameSync(legacy, current);",
    "// 旧目录保留在原处：用户可见的代价是一次重新设置，而不是启动失败。",
)
INDEX_FRAGMENTS = (
    'app.setName("BOSS Harness");',
    'adoptLegacyUserData(app.getPath("userData"), join(app.getPath("appData"), "BOSS-CLI"));',
    "setHarnessWindowFactory(showMainWindow);",
    "if (!app.requestSingleInstanceLock()) {\n  app.quit();\n} else {",
    'app.on("second-instance", () => { void app.whenReady().then(showMainWindow); });',
    'app.on("window-all-closed", () => {',
    'if (process.platform !== "darwin") app.quit();',
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


def check_lifecycle() -> int:
    quit_ = _read(QUIT)
    harness = _read(HARNESS)
    profile = _read(PROFILE)
    index = _read(INDEX)
    checked = 0
    checked += _expect(QUIT_FRAGMENTS, quit_, QUIT)
    checked += _expect(HARNESS_FRAGMENTS, harness, HARNESS)
    checked += _expect(PROFILE_FRAGMENTS, profile, PROFILE)
    checked += _expect(INDEX_FRAGMENTS, index, INDEX)
    # 退出确认：已确认放行 → 只在有运行回合时拦截 → 单次弹框 → 选择或失败后退出。
    checked += _ordered(
        (
            "if (quitConfirmed) return true;",
            "const content = quitConfirmationContent(turnStartedAt.size);",
            "if (!content) return true;",
            "event.preventDefault();",
            "if (quitPromptOpen) return false;",
            "quitPromptOpen = true;",
            "void prompt.then(({ response }) => {",
            "if (response !== 1) { revealWindow(); return; }",
        ),
        harness,
        HARNESS,
    )
    # 退出清理：确认通过后才释放自检与 Host。
    checked += _ordered(
        (
            'app.on("before-quit", (event) => {',
            "if (!confirmQuit(event)) return;",
            "manualStartupCheck.cancel();",
            "manager.dispose(); host = null; windows.clear();",
        ),
        harness,
        HARNESS,
    )
    # 旧目录接管：先看旧目录，再看新目录是否空壳，最后才删空壳并改名。
    checked += _ordered(
        (
            "if (current === legacy || !existsSync(legacy)) return current;",
            "const entries = directoryEntryCount(current);",
            "if (entries === null || entries > 0) return current;",
            "if (existsSync(current)) {",
            "rmdirSync(current);",
            "renameSync(legacy, current);",
        ),
        profile,
        PROFILE,
    )
    # 启动顺序：设置应用名并接管旧目录后，才读取其它本地状态；单实例锁在窗口工厂之后。
    checked += _ordered(
        (
            'app.setName("BOSS Harness");',
            "adoptLegacyUserData(app.getPath(\"userData\"), join(app.getPath(\"appData\"), \"BOSS-CLI\"));",
            "setHarnessWindowFactory(showMainWindow);",
            "if (!app.requestSingleInstanceLock()) {",
        ),
        index,
        INDEX,
    )
    # 反向断言：确认框不得把默认 / 取消按钮放到「停止并退出」，旧目录接管不得递归删除或复制。
    if "defaultId: 1" in quit_ or "cancelId: 1" in quit_:
        raise ValueError(f"{QUIT} 的默认与取消按钮必须落在继续运行")
    for forbidden in ("rmSync(", "cpSync(", "recursive: true"):
        if forbidden in profile:
            raise ValueError(f"{PROFILE} 接管旧目录不得递归删除或复制：{forbidden}")
    return checked + 1


def main() -> int:
    try:
        checked = check_lifecycle()
    except ValueError as error:
        print(f"桌面生命周期边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"桌面生命周期边界一致：{checked} 项接管、单实例与退出防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
