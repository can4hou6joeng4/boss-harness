#!/usr/bin/env python3
"""核对会话内分支切换的提交、回执与失败文案分界。

切换先核对目标会话自己的队列，再提交 `thread/leaf/set`；回执必须与所选会话和位置
一致。内核确认切换后，界面重新读取会话失败不属于「结果未确认」：分支位置以内核为
准，只能提示重读失败。未提交、明确拒绝与未确认的文案各自独立，不能混用。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BRANCHES = "apps/desktop/src/renderer/src/data/useSessionBranches.ts"

FRAGMENTS = (
    "const switchTo = useCallback(async (turnId: string | null, summarize: boolean): Promise<boolean> => {",
    "const queue = await listQueue(id);",
    "队列中仍有排队或投递中的消息，暂不能切换分支：请等待投递完成或先撤回（排队消息切换后会自动投递到新分支）。",
    "attempted = true;",
    "const result = await setThreadLeaf(",
    "if (result.threadId !== id || result.leafTurnId !== turnId) throw new Error(\"切换回执与所选位置不一致\");",
    "await current.current.onSwitched(id);",
    "分支已切换，但重新读取会话失败：",
    "内核拒绝切换，分支保持不变：",
    "切换结果尚未确认：",
    "未能核对目标会话的队列，分支未切换：",
)

RELOAD_NOTICE = "分支已切换，但重新读取会话失败："


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{BRANCHES} 缺少：" + "、".join(missing))
    return len(fragments)


def _slice(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"{BRANCHES} 缺少：{start_marker}")
    end = text.find(end_marker, start)
    if end < 0:
        raise ValueError(f"{BRANCHES} 缺少收尾标记：{end_marker}")
    return text[start:end]


def check_branch_switch() -> int:
    source = _read(BRANCHES)
    checked = _expect(FRAGMENTS, source)

    switch = _slice(source, "const switchTo = useCallback", "}, [applyJob, refresh, update]);")

    # 顺序：队列核对 → 提交标记 → 回执校验 → 重读。提交标记不得早于队列核对。
    position = -1
    for marker in ("const queue = await listQueue(id);", "attempted = true;",
                   "const result = await setThreadLeaf(", "if (result.threadId !== id || result.leafTurnId !== turnId)",
                   "await current.current.onSwitched(id);"):
        index = switch.find(marker)
        if index < 0 or index <= position:
            raise ValueError(f"切换步骤缺少或顺序变化：{marker}")
        position = index
        checked += 1

    # 重读失败必须就近捕获并给出已确认文案，不能落入未确认分支后再重试重读。
    reload_try = _slice(switch, "try {\n        await current.current.onSwitched(id);", "return valid();")
    if RELOAD_NOTICE not in reload_try:
        raise ValueError("重读失败必须在就近的 catch 内说明分支已切换")
    if "切换结果尚未确认" in reload_try:
        raise ValueError("已确认切换的重读失败不得使用未确认文案")
    if switch.count(RELOAD_NOTICE) != 1:
        raise ValueError("已确认切换的重读失败文案只应出现一次")
    checked += 1

    # 未确认文案只属于「已提交但回执未知」，其余两类失败各有独立文案。
    failure = (
        "update(id, { switchError: attempted\n"
        "        ? detail.rpc ? `内核拒绝切换，分支保持不变：${detail.text}` : "
        "`切换结果尚未确认：${detail.text}。已重新读取分支状态；不会自动重试。`\n"
        "        : `未能核对目标会话的队列，分支未切换：${detail.text}` });"
    )
    if failure not in switch:
        raise ValueError("切换失败文案必须按未提交、明确拒绝与未确认三类分支决定")
    checked += 1
    precheck = switch[: switch.find("attempted = true;")]
    if "切换结果尚未确认" in precheck:
        raise ValueError("未提交的队列核对失败不得使用未确认文案")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_branch_switch()
    except ValueError as error:
        print(f"分支切换文案核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支切换一致：{checked} 项提交、回执与失败文案分界")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())