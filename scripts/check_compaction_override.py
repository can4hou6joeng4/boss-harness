#!/usr/bin/env python3
"""核对自动压缩覆盖的取出、消耗与明确拒绝后的恢复。

覆盖只作用于本会话下一条发送：`take` 在请求发出前移除并复位表单。发送被内核明确
拒绝时回合没有启动，覆盖必须写回；回执未知或成功则保持已消耗。恢复只对取出时的
同一份覆盖生效，期间重新应用、清除或再次取用都不得被旧回执覆盖。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "apps/desktop/src/renderer/src/data/useAutoCompaction.ts"
APP = "apps/desktop/src/renderer/src/App.tsx"

MODULE_FRAGMENTS = (
    "const consumed = useRef(new Map<string, { policy: TurnAutoCompactionOverride; stamp: number }>());",
    "const stamps = useRef(new Map<string, number>());",
    "const stampOf = (id: string) => {",
    "consumed.current.set(id, { policy: pending, stamp: stampOf(id) });",
    "consumed.current.delete(threadId);",
    "consumed.current.delete(id);",
    "stamps.current.delete(id);",
    "const restore = useCallback((id: string, policy: TurnAutoCompactionOverride | undefined) => {",
    "if (!policy) return;",
    "const record = consumed.current.get(id);",
    "if (!record || record.policy !== policy || record.stamp !== stamps.current.get(id)) return;",
    "const next = { ...overridesRef.current, [id]: policy };",
    "const restored = draftFrom(policy);",
    "setEnabled, setTriggerPercent, setKeepRecentTokens, apply, clear, take, restore,",
)

APP_FRAGMENTS = (
    "const override = autoCompaction.take(id);",
    "const accepted = await sendTurn(id, text, clientId, model, skillIds, override);",
    "autoCompaction.restore(id, override);",
    "const policy = autoCompaction.take(session.id);",
    "if (isHarnessRpcRejection(cause)) autoCompaction.restore(session.id, policy);",
    "throw cause;",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _slice(text: str, start_marker: str, end_marker: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"{label} 缺少：{start_marker}")
    end = text.find(end_marker, start)
    if end < 0:
        raise ValueError(f"{label} 缺少收尾标记：{end_marker}")
    return text[start:end]


def check_compaction_override() -> int:
    module = _read(MODULE)
    app = _read(APP)
    checked = _expect(MODULE_FRAGMENTS, module, MODULE)
    checked += _expect(APP_FRAGMENTS, app, APP)

    restore = _slice(module, "const restore = useCallback(", "\n  }, []);", MODULE)
    # 恢复只写回覆盖与草稿；不得重新写入草稿或改动标记，也不得经 take 重新取用。
    if "dirtyThreads.current" in restore or "sessionDrafts.current" in restore:
        raise ValueError(f"{MODULE} 的恢复不得重建草稿或改动标记")
    if "take(" in restore:
        raise ValueError(f"{MODULE} 的恢复不得重新取用覆盖")
    if "setError(" in restore:
        raise ValueError(f"{MODULE} 的恢复不得改写失败提示")
    checked += 1

    take = _slice(module, "const take = useCallback(", "\n  }, [defaults]);", MODULE)
    # 取用必须先登记本次消耗再移除覆盖，登记与移除不得调换。
    registered = take.find("consumed.current.set(id,")
    removed = take.find("overridesRef.current = rest;")
    if registered < 0 or removed < 0 or registered < removed:
        raise ValueError(f"{MODULE} 的取用必须登记本次消耗后再移除覆盖")
    checked += 1

    send = _slice(app, "const send = useCallback", "const handleStartSessionWithPrompt", APP)
    take_index = send.find("const override = autoCompaction.take(id);")
    request_index = send.find("await sendTurn(")
    reject_index = send.find("rejected = isHarnessRpcRejection(cause);")
    restore_index = send.find("autoCompaction.restore(id, override);")
    if min(take_index, request_index, reject_index, restore_index) < 0 or not (
        take_index < request_index < reject_index < restore_index
    ):
        raise ValueError(f"{APP} 的直接发送必须按「取出 → 发送 → 判定拒绝 → 恢复」处理覆盖")
    checked += 1
    # 恢复只属于明确拒绝分支：未确认回执不得恢复，避免把可能已生效的覆盖再发一次。
    rejected_block = _slice(send, "if (rejected) {", "}", APP)
    if "autoCompaction.restore(id, override);" not in rejected_block:
        raise ValueError(f"{APP} 的覆盖恢复必须在明确拒绝分支内")
    if send.count("autoCompaction.restore(") != 1:
        raise ValueError(f"{APP} 的直接发送只应在明确拒绝时恢复一次覆盖")
    checked += 1

    queue = _slice(app, "const handleQueueMessage = useCallback", "const handleCheckQueueSubmission", APP)
    if queue.count("autoCompaction.restore(session.id, policy);") != 1:
        raise ValueError(f"{APP} 的排队发送只应恢复一次覆盖")
    if "if (isHarnessRpcRejection(cause))" not in queue:
        raise ValueError(f"{APP} 的排队发送只有在明确拒绝时恢复覆盖")
    if "throw cause;" not in queue:
        raise ValueError(f"{APP} 的排队发送恢复后必须继续抛出原错误")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_compaction_override()
    except ValueError as error:
        print(f"自动压缩覆盖恢复核对失败，{error}", file=sys.stderr)
        return 2
    print(f"自动压缩覆盖恢复一致：{checked} 项取出、拒绝恢复与未确认语义")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())