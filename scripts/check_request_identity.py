#!/usr/bin/env python3
"""核对请求身份的校验、去重与冲突边界。

clientUserMessageId 决定重试是关联原请求还是新增输入，也决定转向与直接发送的
类型冲突；持久队列与回合记录不可信。正则、链接收敛或冲突判定被删改不会触发
构建失败，因此用静态检查固定这些边界。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/request_identity.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

ID_FRAGMENTS = (
    '_CLIENT_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")',
    "return value if isinstance(value, str) and _CLIENT_ID.fullmatch(value) else None",
    'raise ValueError("clientUserMessageId 格式无效")',
)
LINK_FRAGMENTS = (
    "def _linked_queue_id(item: dict) -> str | None:",
    "return value if isinstance(value, str) else None",
    "def _linked_turn_id(queue: dict) -> str | None:",
    "return value if isinstance(value, str) and value else None",
    # 链接只在持久记录里解析；两轮收敛把队列、输入与回合连成同一身份。
    "for _ in range(2):",
    'record = queue_record(entry.get("payload"))',
    'if key == queue_id or (client_id is not None and item.get("clientUserMessageId") == client_id)}',
)
CONFLICT_FRAGMENTS = (
    '_reject("CLIENT_REQUEST_CONFLICT", "请求编号已用于转向消息，不能改为直接或后续任务")',
    '_reject("CLIENT_REQUEST_CONFLICT", "clientUserMessageId 已用于不同输入")',
    '_reject("CLIENT_REQUEST_AMBIGUOUS", "请求编号对应多条历史身份，请先核对会话")',
    '_reject("REQUEST_REQUIRES_REVIEW", "旧请求对应多条原始输入，请先核对会话")',
    'digest = hashlib.sha256(text.encode("utf-8")).hexdigest()',
)
FACT_FRAGMENTS = (
    'if len(persistence_facts) > 1 or (start_failed and turn is not None and turn.get("status") == "completed"):',
    "if client_id is None and queue_id is None:",
    "return RequestIdentity()",
    'failureCode="TURN_START_FAILED"',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "相同编号的不同输入、steering 类型冲突或历史身份歧义会明确拒绝"),
    (USER_GUIDE, "相同 `clientUserMessageId` 会关联原请求，输入已接受不表示回合已成功"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_request_identity() -> int:
    module = _read(MODULE)
    checked = _expect(ID_FRAGMENTS, module, MODULE)
    checked += _expect(LINK_FRAGMENTS, module, MODULE)
    checked += _expect(CONFLICT_FRAGMENTS, module, MODULE)
    checked += _expect(FACT_FRAGMENTS, module, MODULE)
    # 身份必须整串匹配；子串匹配会把 queue-<id> 之类的字符串误当成客户端编号。
    if "_CLIENT_ID.search(" in module:
        raise ValueError(f"{MODULE} 的 clientUserMessageId 必须整串匹配")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_request_identity()
    except ValueError as error:
        print(f"请求身份核对失败，{error}", file=sys.stderr)
        return 2
    print(f"请求身份一致：{checked} 项校验、冲突与文档防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
