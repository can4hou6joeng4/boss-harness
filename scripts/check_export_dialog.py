#!/usr/bin/env python3
"""核对导出弹窗的目标固定、回执失效与明文确认。

导出会写出包含会话内容的文件，弹窗必须固定打开时的目标会话；切换目标要让旧回执
失效，保存期间锁定选项与关闭入口；包含工具结果明文必须二次确认，请求只能携带固定
字段。这里固定这些顺序与反向条件，避免重构把旧回执写到新目标或绕过确认。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DIALOG = "apps/desktop/src/renderer/src/components/ExportDialog.tsx"

DIALOG_FRAGMENTS = (
    "export interface ExportTarget { threadId: string; title: string }",
    "const targetId = target?.threadId ?? null;",
    "const previousTargetId = useRef(targetId);",
    "if (previousTargetId.current === targetId) return;",
    "previousTargetId.current = targetId;",
    "version.current += 1;",
    'const effectiveView: ExportView = branchViews ? view : "log";',
    'const saving = status.kind === "saving";',
    "const requestClose = () => { if (!saving) onClose(); };",
    "const blocked = !connected || !window.boss?.exportSession || saving || (includeToolResults && !acknowledged);",
    "const mine = ++version.current;",
    "const response: unknown = await window.boss.exportSession({ threadId, view: effectiveView, format, includeToolResults,",
    "acknowledgePlaintext: includeToolResults && acknowledged });",
    "if (version.current !== mine) return;",
    "const failure = rpcError(response);",
    "const result = savedExportResult(response);",
    "setStatus(result.saved ? { kind: \"saved\", result } : { kind: \"canceled\" });",
    'const message = error instanceof Error && error.message ? harnessErrorText(error) : "导出失败";',
    '<ModalSurface title="导出会话" onClose={requestClose} className="context-panel export-dialog" closeDisabled={saving}>',
    'aria-label="导出范围"',
    'aria-label="导出格式"',
    "Markdown（便于阅读与粘贴）",
    "HTML（自包含，可用浏览器打开与打印）",
    "JSON（结构化，便于工具处理）",
    "data-export-include",
    "setIncludeToolResults(event.target.checked); setAcknowledged(false);",
    "data-export-ack",
    "我了解风险，仍要包含明文",
    "data-export-risk",
    "当前桌面外壳不支持会话导出，请更新桌面端后重试。",
    "本地内核未连接，暂不能导出。",
    'data-export-status="saved"',
    "status.result.truncated",
    'status.result.toolResults === "included"',
    "status.result.permissionsUnchanged",
    'data-export-status="permissions"',
    'data-export-status="canceled"',
    'data-export-status="error"',
    "已取消保存，未写入文件。",
    "number(status.result.exportedTurnCount)",
    "data-export-owner={threadId}",
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


def check_export_dialog() -> int:
    dialog = _read(DIALOG)
    checked = 0
    checked += _expect(DIALOG_FRAGMENTS, dialog, DIALOG)
    # 目标切换：先记录目标，再递增版本使旧回执失效。
    checked += _ordered(
        (
            "const targetId = target?.threadId ?? null;",
            "const previousTargetId = useRef(targetId);",
            "if (previousTargetId.current === targetId) return;",
            "previousTargetId.current = targetId;",
            "version.current += 1;",
        ),
        dialog,
        DIALOG,
    )
    # 保存前先占版本，回执必须核对版本，失败与成功都按固定状态落库。
    checked += _ordered(
        (
            "const mine = ++version.current;",
            "const response: unknown = await window.boss.exportSession({",
            "if (version.current !== mine) return;",
            "const failure = rpcError(response);",
            "const result = savedExportResult(response);",
            'setStatus(result.saved ? { kind: "saved", result } : { kind: "canceled" });',
        ),
        dialog,
        DIALOG,
    )
    # 模板：关闭入口经 requestClose，保存期间关闭按钮禁用。
    checked += _ordered(
        (
            "const requestClose = () => { if (!saving) onClose(); };",
            '<ModalSurface title="导出会话" onClose={requestClose}',
            "closeDisabled={saving}>",
        ),
        dialog,
        DIALOG,
    )
    # 明文：勾选后先清空确认，确认框只在勾选后出现。
    checked += _ordered(
        (
            "data-export-include",
            "setIncludeToolResults(event.target.checked); setAcknowledged(false);",
            "data-export-ack",
            "我了解风险，仍要包含明文",
        ),
        dialog,
        DIALOG,
    )
    # 反向断言：确认不能被短路，关闭不能绕过保存锁定，弹窗必须使用 requestClose。
    for forbidden in ("acknowledgePlaintext: true", "closeDisabled={false}", "onClose={onClose}",
                      "const requestClose = () => { onClose(); };"):
        if forbidden in dialog:
            raise ValueError(f"{DIALOG} 的导出弹窗不得包含 {forbidden}")
    if re.search(r"acknowledgePlaintext:\s*includeToolResults\s*[,}]", dialog):
        raise ValueError(f"{DIALOG} 的 acknowledgePlaintext 必须同时要求 includeToolResults 与 acknowledged")
    return checked + 2


def main() -> int:
    try:
        checked = check_export_dialog()
    except ValueError as error:
        print(f"导出弹窗核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出弹窗一致：{checked} 项目标固定、明文确认、锁定与回执防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
