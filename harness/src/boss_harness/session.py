"""Durable sessions: append-only JSONL rollouts with a rebuildable SQLite index.

The transport's ordered event journal is separate from model-visible history.
Forks copy a complete, settled rollout prefix and never replay tool side effects.
Pi reference: 5ba1cbaf3d96d204d847c84ce235c62dae23e0fd, SessionManager.
"""
from __future__ import annotations

import array
import base64
import binascii
import hashlib
import io
import json
import math
import os
import re
import sqlite3
import stat
import threading
import time
import unicodedata
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from boss_harness.item_content import decode_cursor_base64
from boss_harness.persistence import PersistenceIndex, SCHEMA_VERSION
from boss_harness.private_files import ensure_private_directory, open_private_file, restrict_private_file
from boss_harness.tool_results import MAX_PAGE_BYTES, wire_size
from boss_harness.queue_view import ACTIVE_QUEUE_STATUSES, queue_record
from boss_harness.search_unicode import (GRAPHEME_V_EXTRA, extra_combining_class, is_grapheme_extend,
                                          needs_extra, search_normalize)
from boss_harness.models.capabilities import REASONING_EFFORTS

_T = TypeVar("_T")
_THREAD_ID = re.compile(r"[a-f0-9]{12}\Z")
APPROVAL_PARAM_MAX_DEPTH = 64
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
#: 与桌面审批卡片字段的展示上限一致；无法展示工具名或条目 id 的审批不能进入列表或持久计数。
_APPROVAL_VIEW_FIELD_CHARS = 200
_EVENT_ID = re.compile(r"[a-f0-9]{32}\Z")
_ATTACHMENT_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_ATTACHMENT_TEMP = re.compile(r"tmp-[a-f0-9]{32}\Z")
_DELETE_INTENT = re.compile(r"\.delete-([a-f0-9]{12})\.json\Z")
#: 时间戳文法跨版本固定：``fromisoformat`` 的接受集合随版本扩大（3.11+ 基本格式、
#: 逗号小数与不补零的小数/偏移，3.14 还接受 ``24:00``），持久记录可被外部改写，
#: 同一输入不能在一个版本上参与耗时、在另一个版本上被丢弃。先按固定文法取字段，
#: 再补成各版本都接受的规范形式交给 ``fromisoformat`` 校验范围。
_ISO_TIMESTAMP = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})[T ]"
    r"(?P<hour>[01][0-9]|2[0-3]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])"
    r"(?:[.,](?P<fraction>[0-9]{1,6}))?"
    r"(?:(?P<zulu>Z)|(?P<sign>[+-])(?P<offset_hour>[01][0-9]|2[0-3])(?::?(?P<offset_minute>[0-9]{2}))?)?\Z"
)
_TERMINAL = frozenset({"completed", "interrupted", "blocked", "error"})
#: 回合归并自己的顺序记账字段；持久载荷同名键不可信，既不能覆盖内部值，也不随公开回合返回。
_TURN_INTERNAL_FIELDS = frozenset({"firstOrdinal", "lastOrdinal", "boundaryOrdinal"})
_SEARCH_THREADS = 100
_SEARCH_MATCHES = 50
_SEARCH_PER_THREAD = 5
_SEARCH_TEXT_BUDGET = 4 * 1024 * 1024
_SEARCH_THREAD_BYTES = 8 * 1024 * 1024
_SEARCH_SNIPPET_BYTES = 200
_SEARCH_TOOL_ARGS = 2000
_SEARCH_TOOL_TEXT = 6000


def _is_hangul_letter(char: str) -> bool:
    """参与谚文音节组合的字母：组合 jamo（含扩展区）、兼容 jamo 与半角字母。

    NFKC 会把连续的 L / V / T 合成一个音节；兼容 jamo（U+3131–U+318E）与
    半角字母（U+FFA0–U+FFDC）会先分解成组合 jamo 再参与合成，因此
    ``ㄱ`` + ``ㅏ`` → ``가``、``가`` + ``ㄳ`` → ``갃`` 也要求跨字符归一化。
    """
    code = ord(char)
    return (0x1100 <= code <= 0x11FF or 0xA960 <= code <= 0xA97C
            or 0xD7B0 <= code <= 0xD7FB or 0x3131 <= code <= 0x318E
            or 0xFFA0 <= code <= 0xFFDC)


def _is_hangul_syllable(char: str) -> bool:
    """预组合谚文音节（U+AC00–U+D7A3）：NFKC 会与紧随的尾音 jamo 合成一个音节。"""
    return 0xAC00 <= ord(char) <= 0xD7A3


#: 半角假名的浊音 / 半浊音符号。组合类为 0，但 NFKC 会与前面的假名（含全角与
#: 兼容假名）合成预组合假名；按扩展记号并入前一个字素，孤立符号不受影响。
_HALFWIDTH_VOICED_MARKS = frozenset({"ﾞ", "ﾟ"})


def _search_clusters(value: str, normalize: Callable[[str], str] | None = None
                     ) -> Iterator[tuple[int, int, str]]:
    """逐个组合簇产出 (原文起点, 原文终点, NFKC + casefold 后的片段)。

    ``normalize`` 为 None 时走普通 NFKC + casefold；只有正文含新版 Unicode
    映射码点时，调用方才传入补表的 ``search_normalize``。

    NFKC 会把基字符与后续组合记号、分解状态的谚文 jamo、预组合音节后的尾音
    jamo 组合成一个字符；逐码点归一化做不到跨码点组合，NFC / NFD 正文互相
    查询会漏命中。谚文 jamo 只要跟随在音节或另一个 jamo 之后就并入同一簇：
    这比字素规则略宽，只影响原文区间粒度，不改变整簇 NFKC 的结果。兼容 jamo
    与半角字母会先分解成组合 jamo 再参与合成（``ㄱ`` + ``ㅏ`` → ``가``、
    ``가`` + ``ㄳ`` → ``갃``），同样并入同一簇；预组合音节仍各自成簇，避免
    把整段韩文并成一个组合单元。半角假名的浊音 / 半浊音符号组合类为 0，需按
    扩展记号并入前一个字素，否则 ``ｶﾞ`` / ``カﾞ`` 会被拆开而无法与 ``ガ``
    互相命中。casefold 逐码点进行，与旧实现的语义一致（上下文无关，不改变
    词尾 sigma 等结果）。
    """
    index = 0
    length = len(value)
    while index < length:
        end = index + 1
        hangul = _is_hangul_letter(value[index]) or _is_hangul_syllable(value[index])
        while end < length and (
            is_grapheme_extend(ord(value[end]))
            or (hangul and _is_hangul_letter(value[end]))
            or value[end] in _HALFWIDTH_VOICED_MARKS
            or (ord(value[end - 1]) in GRAPHEME_V_EXTRA and ord(value[end]) in GRAPHEME_V_EXTRA)
        ):
            end += 1
        part = value[index:end]
        yield index, end, (unicodedata.normalize("NFKC", part).casefold()
                           if normalize is None else normalize(part))
        index = end


# 持久记录不可信：编号字段只有字符串才有定位意义。其余类型若继续参与集合成员或
# 映射键查询会抛 TypeError，让一条坏记录打断整个会话的读取与投影。
_ITEM_ID_FIELDS = ("turnId", "revises", "toolBatchId", "queueId")


def _record_id(value: object) -> str | None:
    """把编号字段收敛为字符串或缺失；非字符串一律按缺失处理。"""
    return value if isinstance(value, str) else None


# In-session branch pointer (Pi session-manager leafId).  Sessions that never
# record one keep the historical linear projection byte-for-byte.
LEAF_ENTRY_TYPE = "leaf"
# 会话投影内容的版本。投影只在会话文件变化后重建，新增派生字段时已有会话不会自动获得；
# 版本变化后首次打开状态目录，让受影响的会话失效一次。记在 checkpoints 表而不是索引
# 结构版本里：结构没有变化，旧版本仍能打开同一状态目录。
# 2：切换过位置的会话带 branchLastTurn。
THREAD_PROJECTION_VERSION = "2"
_LEAF_RECORD_MARKERS = tuple(
    f'"type":{separator}"{LEAF_ENTRY_TYPE}"'.encode("ascii") for separator in ("", " "))


def _log_mentions_leaf(path: Path) -> bool:
    """按字节查找位置记录的类型标记，不解析日志。

    只用来挑出需要重建投影的会话：工具数据里出现同样的片段只会多重建一次，重建结果
    仍由 ``_index_thread`` 按解析后的条目决定。分块读取并保留跨块的尾部。
    """
    overlap = max(len(marker) for marker in _LEAF_RECORD_MARKERS) - 1
    tail = b""
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            window = tail + chunk
            if any(marker in window for marker in _LEAF_RECORD_MARKERS):
                return True
            tail = window[-overlap:]
    return False


def continuation_entries_digest(entries: list[dict]) -> str:
    """续接边界摘要：与条目逐字节绑定，分叉复制后按复制前缀重算。"""
    encoded = json.dumps(entries, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rehash_continuation_boundaries(copied: list[dict]) -> None:
    """分叉丢弃内核专用记录并改写审批编号：继承的续接边界按复制后的前缀重算。"""
    positions = {entry.get("id"): index for index, entry in enumerate(copied)}
    for entry in copied:
        payload = entry.get("payload")
        if entry.get("type") != "turn" or not isinstance(payload, dict):
            continue
        boundary_id = payload.get("continuationBoundaryEntryId")
        if not isinstance(boundary_id, str):
            continue
        index = positions.get(boundary_id)
        if index is None:
            # 边界条目未复制：删掉摘要，让预检按「持久边界不存在」拒绝，而不是误报历史变化。
            payload.pop("continuationBoundaryDigest", None)
            continue
        payload["continuationBoundaryDigest"] = continuation_entries_digest(copied[:index + 1])

# Pi branchWithSummary(): a model summary of the abandoned branch, appended
# right after the leaf record it belongs to, so it projects only on that branch.
BRANCH_SUMMARY_ENTRY_TYPE = "branch_summary"
MAX_BRANCH_SUMMARY_CHARS = 32_000
# 摘要注入文本还包含被放弃回合与来源摘要；这两项不进摘要正文长度，必须单独
# 有界，否则一条 2 MB 的来源摘要会让压缩后的历史永久超出上下文预算。
MAX_BRANCH_SUMMARY_TURNS = 200
MAX_BRANCH_SUMMARY_TURN_ID_CHARS = 128
MAX_BRANCH_SUMMARY_TURN_TOTAL_CHARS = 4_096
MAX_BRANCH_SUMMARY_DIGEST_CHARS = 128


def branch_summary_issue(payload: dict, positions: Mapping[str, int]) -> str | None:
    """One fixed Chinese reason a branch-summary payload is unusable, or None when valid.

    Context injection and export share this check so the two read paths cannot
    disagree about which summary records the model actually saw; ``positions``
    maps every turn on the reference branch (or log view) to its depth.
    """
    summary, anchor = payload.get("summary"), payload.get("targetTurnId")
    abandoned = payload.get("abandonedTurnIds")
    if not isinstance(summary, str):
        return "摘要正文不是字符串"
    if not summary.strip():
        return "摘要正文为空"
    if len(summary) > MAX_BRANCH_SUMMARY_CHARS:
        return f"摘要正文超过 {MAX_BRANCH_SUMMARY_CHARS} 字符"
    if anchor is not None and (not isinstance(anchor, str) or anchor not in positions):
        return "摘要的目标回合不在当前分支上"
    if (not isinstance(abandoned, list) or not abandoned
            or len(abandoned) > MAX_BRANCH_SUMMARY_TURNS
            or not all(isinstance(turn_id, str)
                       and len(turn_id) <= MAX_BRANCH_SUMMARY_TURN_ID_CHARS for turn_id in abandoned)
            or sum(len(turn_id) for turn_id in abandoned) > MAX_BRANCH_SUMMARY_TURN_TOTAL_CHARS):
        return "被放弃回合列表为空或无效"
    digest = payload.get("sourceTextDigest")
    if digest is not None and (not isinstance(digest, str)
                               or len(digest) > MAX_BRANCH_SUMMARY_DIGEST_CHARS):
        return "摘要来源摘要无效"
    # 这些标识会原样进入 context/read 的 branchSummaries 投影；单条数 MiB 的
    # 值能让读取响应超过 8 MiB 协议帧且没有自愈路径，按损坏摘要处理。
    for key in ("summaryJobId", "fromTurnId"):
        value = payload.get(key)
        if value is not None and (not isinstance(value, str)
                                  or len(value) > MAX_BRANCH_SUMMARY_TURN_ID_CHARS):
            return "摘要辅助标识无效"
    return None


MAX_LEAF_ACTIVE_TURN_IDS = 200
MAX_BRANCH_PREVIEW_CHARS = 120
# 项目标识只用于会话分组，属于客户端可写的会话头元数据。给它一个与其它
# 会话字段同类的上限，避免超大值挤占会话读取与列表的响应预算。
MAX_PROJECT_ID_CHARS = 200
# 标题同时用于会话列表与重命名；旧版本的 fork 记录没有长度上限，读取层
# 采用同一上限，避免历史超长标题让会话无法打开或撑大列表响应。
MAX_THREAD_TITLE_CHARS = 500
_TASK_PHASES = frozenset({"admission", "prepare", "model_request", "tool_execution", "finish"})
_EVENT_READ_CHUNK_BYTES = 64 * 1024
# Event records are persisted from the same bounded JSON-RPC payloads as the
# transport.  Keep one explicit line limit so a damaged append-only log cannot
# make a cold index rebuild allocate without bound.
MAX_EVENT_LINE_BYTES = 8 * 1024 * 1024
# 单页事件最多解析的 `params_json` 原始字节数。单条事件可接近 8 MiB，
# 一页 1000 条时全部取回再逐行解码会在存储锁内占用数 GiB；按原始字节
# 预算逐行读取，超出即停并置 `hasMore`，由调用方的翻页循环续读。
_EVENT_PAGE_RAW_BYTES = 4 * 1024 * 1024
MAX_ITEM_REVISION_ALIASES = 4_096
MAX_ITEM_REVISION_RECORDS = 4_096
MAX_ITEM_REVISION_ALIAS_BYTES = 64 * 1024
MAX_TOOL_BATCH_CALLS = 256
# Canonical results have a separate budget from their bounded transport
# projection.  Validate the final JSON spelling before publishing a record;
# raw CLI bytes and decoded/re-encoded JSON need not have the same size.
MAX_SESSION_LINE_BYTES = 32 * 1024 * 1024
MAX_SESSION_HEADER_BYTES = 8 * 1024 * 1024
# 单条持久记录的 JSON 嵌套上限。正常工具参数受 64 层约束，导出文档允许 256 层；
# 显式拒绝更深的记录，避免 json.loads 的递归上限随 Python 版本改变读取结论。
MAX_JSON_RECORD_DEPTH = 256
# Recovery metadata is tiny in normal operation.  Keep a separate whole-file
# bound so a forged delete marker or repair manifest cannot be materialised
# before its JSON shape is checked.
MAX_DELETE_INTENT_BYTES = 1024 * 1024
MAX_REPAIR_MANIFEST_BYTES = 1024 * 1024
# 条目投影缓存按（大小, mtime_ns）绑定，只用于没有新追加的重复读取。
# 会话条目可能较大，只保留最近使用的少数会话，避免缓存本身占用大量内存。
_MAX_ENTRIES_CACHE_THREADS = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_timestamp(value: Any) -> datetime | None:
    """按固定文法解析扩展格式 ISO 时间；同一输入在 3.10–3.14 上结论一致。

    接受 ``YYYY-MM-DD[T ]HH:MM:SS``，可选 1–6 位小数（``.`` 或 ``,``），可选
    ``Z`` / ``±HH`` / ``±HHMM`` / ``±HH:MM`` 偏移；无偏移时返回朴素时间。小数补齐
    6 位、偏移补成 ``±HH:MM``、``Z`` 写成 ``+00:00`` 后再交给 ``fromisoformat``
    校验月日与偏移范围，避免各版本对同一写法给出不同结论。
    """
    if not isinstance(value, str) or not value or len(value) > 64:
        return None
    match = _ISO_TIMESTAMP.fullmatch(value)
    if match is None:
        return None
    fraction = match.group("fraction")
    if match.group("zulu"):
        offset = "+00:00"
    elif match.group("sign"):
        offset = (f"{match.group('sign')}{match.group('offset_hour')}:"
                  f"{match.group('offset_minute') or '00'}")
    else:
        offset = ""
    text = (f"{match.group('year')}-{match.group('month')}-{match.group('day')}T"
            f"{match.group('hour')}:{match.group('minute')}:{match.group('second')}"
            + (f".{fraction.ljust(6, '0')}" if fraction else "")
            + offset)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _valid_timestamp(value: Any) -> str | None:
    """只接受解析结论稳定的 ISO 时间字符串；非法值不参与耗时统计。

    解析统一走 :func:`_parse_iso_timestamp`：``fromisoformat`` 的接受集合随 Python
    版本扩大，同一份外部改写记录不能在一个版本上参与耗时、在另一个版本上被丢弃。
    """
    if not isinstance(value, str):
        return None
    return value if _parse_iso_timestamp(value) is not None else None


MAX_SKILL_IDS = 10
MAX_SKILL_ID_LENGTH = 200


def bounded_skill_ids(value: Any) -> list[str]:
    """回合实际注入的技能 id：先校验、后计数，按 id 去重并最多 ``MAX_SKILL_IDS`` 项。

    旧记录或畸形值不产生伪技能；前部的非法项也不占名额。
    """
    if not isinstance(value, list):
        return []
    ids: list[str] = []
    for item in value:
        if len(ids) >= MAX_SKILL_IDS:
            break
        if isinstance(item, str) and 0 < len(item) <= MAX_SKILL_ID_LENGTH and item not in ids:
            ids.append(item)
    return ids


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _approval_params_too_deep(arguments: Any) -> bool:
    """显式深度上限，不依赖 json.dumps 的递归异常（Python 3.14 起行为不同）。"""
    pending: list[tuple[Any, int]] = [(arguments, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > APPROVAL_PARAM_MAX_DEPTH:
            return True
        if isinstance(value, dict):
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, (list, tuple)):
            pending.extend((child, depth + 1) for child in value)
    return False


def approval_parameters_digest(arguments: dict[str, Any]) -> str:
    if type(arguments) is not dict:
        raise ValueError("审批参数必须是对象")
    if _approval_params_too_deep(arguments):
        raise ValueError("审批参数无法规范化")
    try:
        encoded = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"),
                             sort_keys=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        raise ValueError("审批参数无法规范化") from None
    return hashlib.sha256(encoded).hexdigest()


class ApprovalDecisionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _encode_session_line(value: dict, *, maximum: int = MAX_SESSION_LINE_BYTES,
                         label: str = "会话日志") -> bytes:
    try:
        encoded = _json(value).encode("utf-8")
    except RecursionError:
        raise ValueError(f"{label}嵌套层级超过上限") from None
    if _json_depth_exceeded(encoded.decode("utf-8"), MAX_JSON_RECORD_DEPTH):
        raise ValueError(f"{label}嵌套层级超过上限")
    if len(encoded) > maximum:
        raise ValueError(f"{label}单行超过大小限制")
    return encoded + b"\n"


def _read_exactly_at(descriptor: int, offset: int, length: int) -> bytes:
    chunks: list[bytes] = []
    os.lseek(descriptor, offset, os.SEEK_SET)
    while length:
        chunk = os.read(descriptor, length)
        if not chunk:
            raise OSError("会话日志读取不完整")
        chunks.append(chunk)
        length -= len(chunk)
    return b"".join(chunks)


def _complete_record_limit(handle: io.BufferedReader, size: int) -> int:
    """把快照的固定读取范围收敛到最后一个完整记录边界内。

    追加在发现末尾残段（无换行）时会先截掉残段再写入完整记录，这会改写残段覆盖的
    字节。快照在写锁内固定范围、在锁外解码，若范围把残段包含在内，截断后的文件会
    短于固定范围：条目快照读到 EOF 抛「会话日志快照读取不完整」，而快照构建器静默
    提前结束，还会把固定范围之外新追加的记录当成固定前缀的一部分。收敛到换行边界
    后，追加只会改写边界之后的字节，锁外读取看到的前缀不再被改写。
    """
    if size <= 0:
        return 0
    handle.seek(size - 1)
    if handle.read(1) == b"\n":
        return size
    window = min(size, MAX_SESSION_LINE_BYTES + 1)
    handle.seek(size - window)
    boundary = handle.read(window).rfind(b"\n")
    if boundary < 0:
        # 整个文件都没有换行时按空前缀固定（与读取端丢弃残段一致）；超过单行窗口仍
        # 找不到边界说明残段本身超出任何合法记录，与追加端使用同一可读错误。
        if size > window:
            raise ValueError("会话日志末尾缺少完整记录边界")
        return 0
    return size - window + boundary + 1


def _truncate_partial_record_tail(descriptor: int, start: int) -> int:
    """截掉末尾没有换行的不完整记录，返回新的文件长度。

    中断的追加会在文件末尾留下半条记录。若直接在它后面补换行再追加，残片会被
    固化成一条无法解析的记录，之后每次读取都会失败；因此下次追加前先把它截掉。
    残片不会超过单行上限，据此向前找到最后一个换行作为记录边界。
    """
    window = min(start, MAX_SESSION_LINE_BYTES + 1)
    offset = start - window
    boundary = _read_exactly_at(descriptor, offset, window).rfind(b"\n")
    if boundary < 0:
        raise ValueError("会话日志末尾缺少完整记录边界")
    truncated = offset + boundary + 1
    if truncated != start:
        os.ftruncate(descriptor, truncated)
        os.fsync(descriptor)
    return truncated


def _iter_bounded_raw_lines_from_handle(handle, *, maximum: int, label: str = "JSONL",
                                        universal_newlines: bool = False,
                                        byte_limit: int | None = None):
    """Yield raw JSONL records from an already pinned handle with a line bound."""
    if byte_limit is not None and (type(byte_limit) is not int or byte_limit < 0):
        raise ValueError("JSONL 快照长度无效")
    pending = bytearray()
    remaining = byte_limit
    while True:
        if remaining is None:
            chunk = handle.read(_EVENT_READ_CHUNK_BYTES)
            eof = not chunk
        elif remaining == 0:
            chunk = b""
            eof = True
        else:
            chunk = handle.read(min(_EVENT_READ_CHUNK_BYTES, remaining))
            if not chunk:
                raise ValueError(f"{label}快照读取不完整")
            remaining -= len(chunk)
            eof = remaining == 0
        if chunk:
            pending.extend(chunk)
        while True:
            newline = pending.find(b"\n")
            carriage = pending.find(b"\r") if universal_newlines else -1
            if carriage >= 0 and (newline < 0 or carriage < newline):
                if carriage + 1 == len(pending) and not eof:
                    break
                separator_end = (carriage + 2 if carriage + 1 < len(pending)
                                 and pending[carriage + 1] == 10 else carriage + 1)
                line = bytes(pending[:carriage])
                del pending[:separator_end]
            elif newline >= 0:
                line = bytes(pending[:newline])
                del pending[:newline + 1]
            else:
                if len(pending) > maximum:
                    raise ValueError(f"{label}单行超过大小限制")
                break
            if len(line) > maximum:
                raise ValueError(f"{label}单行超过大小限制")
            yield line
        if eof:
            break
    # 文件末尾没有换行的那一段只可能来自中断的追加：进程在 os.write 与 fsync 之间
    # 退出或断电，记录只写了一半。记录一律以换行结尾，把残段当记录读出会解码失败，
    # 进而让整个内核无法启动；这里丢弃，写入端会在下次追加前截掉它。
    if pending and len(pending) > maximum:
        raise ValueError(f"{label}单行超过大小限制")


def _iter_bounded_raw_lines(path: Path, *, maximum: int, label: str = "JSONL",
                            universal_newlines: bool = False):
    with path.open("rb") as handle:
        yield from _iter_bounded_raw_lines_from_handle(
            handle, maximum=maximum, label=label, universal_newlines=universal_newlines)


def _reject_json_constant(_: str) -> None:
    raise ValueError


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError
    return parsed


def _validate_json_unicode(value: Any) -> None:
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            try:
                current.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError from None
        elif isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)


_JSON_STRUCTURE = re.compile(r'["{}\[\]]')


def _json_depth_exceeded(text: str, maximum: int) -> bool:
    """统计 JSON 容器深度；跳过字符串正文，不依赖递归或逐字符 Python 扫描。"""
    depth = 0
    position = 0
    while match := _JSON_STRUCTURE.search(text, position):
        character = match[0]
        position = match.end()
        if character == '"':
            while True:
                quote = text.find('"', position)
                if quote < 0:
                    # 字符串未闭合由 json.loads 判定为损坏，词法检查不替代语法校验。
                    return False
                backslash = quote
                while backslash > position and text[backslash - 1] == "\\":
                    backslash -= 1
                escaped = (quote - backslash) % 2
                position = quote + 1
                if not escaped:
                    break
        elif character in "{[":
            depth += 1
            if depth > maximum:
                return True
        else:
            depth -= 1
    return False


def _decode_jsonl_object(line: str | bytes, *, label: str, line_number: int) -> dict:
    try:
        text = line.decode("utf-8") if isinstance(line, bytes) else line
        if _json_depth_exceeded(text, MAX_JSON_RECORD_DEPTH):
            raise ValueError
        record = json.loads(text, object_pairs_hook=_unique_json_object,
                            parse_constant=_reject_json_constant, parse_float=_finite_json_float)
        _validate_json_unicode(record)
    except (ValueError, RecursionError):
        raise ValueError(f"{label}第 {line_number} 行损坏，读取已停止") from None
    if not isinstance(record, dict):
        raise ValueError(f"{label}第 {line_number} 行格式无效，读取已停止")
    return record


def _decode_session_record(line: str | bytes, *, line_number: int) -> dict | None:
    record = _decode_jsonl_object(line, label="会话日志", line_number=line_number)
    if record.get("type") == "session":
        if line_number == 1:
            return None
        raise ValueError(f"会话日志第 {line_number} 行出现重复会话头，读取已停止")
    parent_id = record.get("parentId")
    if (not isinstance(record.get("type"), str) or not isinstance(record.get("id"), str)
            or not isinstance(record.get("timestamp"), str)
            or (parent_id is not None and not isinstance(parent_id, str))):
        raise ValueError(f"会话日志第 {line_number} 行格式无效，读取已停止")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(f"会话日志第 {line_number} 行格式无效，读取已停止")
    return record


def _iter_bounded_lines(path: Path, *, maximum: int, label: str = "JSONL",
                        universal_newlines: bool = False):
    """Yield decoded JSONL lines without materialising the complete file."""
    for line_number, raw_line in enumerate(_iter_bounded_raw_lines(
            path, maximum=maximum, label=label, universal_newlines=universal_newlines), start=1):
        try:
            yield raw_line.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"{label}第 {line_number} 行不是有效 UTF-8，读取已停止") from None


def _read_bounded_file(path: Path, *, maximum: int, label: str) -> bytes:
    descriptor = open_private_file(path, os.O_RDONLY)
    with os.fdopen(descriptor, "rb") as handle:
        data = handle.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError(f"{label}超过大小限制")
    return data


class SessionEntriesSnapshot:
    """A rewindable, size-pinned view of one append-only session prefix."""

    def __init__(self, source: io.BufferedReader, size: int, mtime_ns: int, inode: int) -> None:
        self._source = source
        self._size = size
        self.mtime_ns = mtime_ns
        self.inode = inode
        self.line_count = 0

    @property
    def stamp(self) -> tuple[int, int, int]:
        """File identity of the pinned prefix, for cache lookups keyed on later reads."""
        return self._size, self.mtime_ns, self.inode

    def __enter__(self) -> SessionEntriesSnapshot:
        if self._source.closed:
            raise ValueError("会话快照已关闭")
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._source.close()

    def __iter__(self):
        if self._source.closed:
            raise ValueError("会话快照已关闭")
        self._source.seek(0)
        self.line_count = 0
        for line_number, raw_line in enumerate(_iter_bounded_raw_lines_from_handle(
                self._source, maximum=MAX_SESSION_LINE_BYTES, label="会话日志",
                universal_newlines=True, byte_limit=self._size), start=1):
            self.line_count = line_number
            if not raw_line.strip():
                continue
            data = _decode_session_record(raw_line, line_number=line_number)
            if data is not None:
                yield data


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    descriptor = open_private_file(path, os.O_RDONLY)
    with os.fdopen(descriptor, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _limit(value: int, maximum: int = 200) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"limit 必须是 1 到 {maximum} 之间的整数")
    return value


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} 格式无效")
    return value


def _event_cursor(value: str | None) -> int:
    if value is None:
        return 0
    if (not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]{0,18}", value)
            or int(value) > 2**63 - 1):
        raise ValueError("eventCursor 必须是有效的非负十进制字符串")
    return int(value)


def _page_cursor(kind: str, scope: dict, key: list) -> str:
    payload = _json({"kind": kind, "scope": scope, "key": key}).encode()
    return "p1_" + base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _read_page_cursor(cursor: str | None, kind: str, scope: dict) -> list | None:
    if cursor is None:
        return None
    if not isinstance(cursor, str) or not cursor.startswith("p1_") or len(cursor) > 4096:
        raise ValueError("分页游标无效")
    encoded = cursor[3:]
    try:
        raw = decode_cursor_base64(encoded)
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError, binascii.Error, RecursionError):
        # 长度上限内可容纳上千层嵌套；json.loads 对这种输入抛 RecursionError，
        # 与解码失败一样是游标无效，不能让内部异常逃逸成 -32603。
        raise ValueError("分页游标无效") from None
    if (not isinstance(payload, dict) or set(payload) != {"kind", "scope", "key"}
            or payload["kind"] != kind or payload["scope"] != scope
            or not isinstance(payload["key"], list)):
        raise ValueError("分页游标与查询范围不匹配")
    return payload["key"]


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@dataclass
class Entry:
    type: str
    id: str = field(default_factory=_new_id)
    parent_id: str | None = None
    timestamp: str = field(default_factory=_now)
    payload: dict | None = None

    def to_dict(self) -> dict:
        data: dict = {"type": self.type, "id": self.id, "parentId": self.parent_id,
                      "timestamp": self.timestamp}
        if self.payload is not None:
            data["payload"] = self.payload
        return data


class CheckpointCommitUncertain(RuntimeError):
    """The checkpoint publication outcome could not be established."""

    code = "COMPACTION_COMMIT_UNCERTAIN"

    def __init__(self, checkpoint_id: str) -> None:
        self.checkpoint_id = checkpoint_id
        super().__init__(f"摘要检查点 {checkpoint_id} 的提交结果无法确认，可能已经生效；请先核对会话，避免自动重试。")


class CheckpointCommittedError(RuntimeError):
    """A published checkpoint must not be reported as an uncommitted failure."""

    code = "COMPACTION_COMMITTED_REFRESH_FAILED"

    def __init__(self, checkpoint_id: str) -> None:
        self.checkpoint_id = checkpoint_id
        super().__init__(f"摘要检查点 {checkpoint_id} 已经生效，但提交后的状态刷新失败；请重新读取会话，勿重复提交。")


class ToolRevisionPersistenceError(OSError):
    """A tool result revision could not be confirmed as durably present."""

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        super().__init__("工具结果无法确认已持久化")


class SessionAppendRollbackError(OSError):
    """An append failed and its partial file state could not be rolled back safely."""

    def __init__(self) -> None:
        self.outcome = "unknown"
        super().__init__("会话日志追加失败且无法确认已回滚；状态可能需要人工检查")


class ThreadNotFound(ValueError):
    pass


class SessionSizeLimitExceeded(ValueError):
    """An append batch would cross a caller-supplied session file bound."""


class ItemLookupError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class _IndexedMetadataError(ValueError):
    """投影索引里的 metadata_json 无法作为对象使用；读取方据此触发重建。"""

    def __init__(self, thread_id: str) -> None:
        super().__init__(thread_id)
        self.thread_id = thread_id


class SessionStore:
    def __init__(self, root: Path, *, attachments_root: Path | None = None) -> None:
        self.root = Path(root).resolve()
        ensure_private_directory(self.root.parent)
        ensure_private_directory(self.root)
        self.attachments_root = Path(attachments_root or self.root.parent / "attachments").absolute()
        self._lock = threading.RLock()
        self._entries_cache: dict[str, tuple[tuple[int, int, int], int, list[dict]]] = {}
        self.database_path = self.root.parent / "state.sqlite3"
        self.events_path = self.root.parent / "events.jsonl"
        for path in (self.database_path.with_name(self.database_path.name + "-wal"),
                     self.database_path.with_name(self.database_path.name + "-shm"), self.events_path,
                     *self.root.glob("*.jsonl"), *self.root.glob(".*.tmp"),
                     *self.root.glob(".delete-*.json"),
                     *self.root.parent.glob(".events.jsonl.delete-*.tmp")):
            try:
                path.lstat()
            except FileNotFoundError:
                continue
            restrict_private_file(path)
        self._index = PersistenceIndex(self.database_path)
        self._recover_deletions()
        # Unindexed logs that could not be projected on the last refresh; repair
        # reports them so a skipped session does not disappear silently.
        self.unreadable_threads: set[str] = set()
        self._expire_outdated_projections()
        self._refresh_threads()
        self._sync_events()

    def close(self) -> None:
        """Connections are operation-scoped; retained for explicit owner cleanup."""

    def path_for(self, thread_id: str) -> Path:
        if not isinstance(thread_id, str) or not _THREAD_ID.fullmatch(thread_id):
            raise ValueError("threadId 格式无效")
        return self.root / f"{thread_id}.jsonl"

    def _delete_intent_path(self, thread_id: str) -> Path:
        self.path_for(thread_id)
        return self.root / f".delete-{thread_id}.json"

    def has_pending_deletion(self, thread_id: str) -> bool:
        return self._delete_intent_path(thread_id).exists()

    def _read_delete_intent(self, path: Path) -> dict[str, Any]:
        match = _DELETE_INTENT.fullmatch(path.name)
        if match is None:
            raise ValueError("会话删除标记名称无效")
        try:
            raw = _read_bounded_file(path, maximum=MAX_DELETE_INTENT_BYTES, label="会话删除标记")
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
            raise ValueError("会话删除标记损坏，会话暂不可操作") from None
        thread_id = match.group(1)
        if (not isinstance(value, dict) or set(value) != {"version", "threadId", "attachmentDigests", "eventId"}
                or value.get("version") != 1 or value.get("threadId") != thread_id
                or not isinstance(value.get("attachmentDigests"), list)
                or any(not isinstance(item, str) or not _ATTACHMENT_DIGEST.fullmatch(item)
                       for item in value["attachmentDigests"])
                or not isinstance(value.get("eventId"), str)
                or not _EVENT_ID.fullmatch(value["eventId"])):
            raise ValueError("会话删除标记损坏，会话暂不可操作")
        value["attachmentDigests"] = sorted(set(value["attachmentDigests"]))
        return value

    def _pending_deletion_ids(self) -> set[str]:
        pending: set[str] = set()
        for path in self.root.glob(".delete-*.json"):
            # The marker name identifies the blocked session even when its
            # contents are damaged; listings must not depend on reading it.
            match = _DELETE_INTENT.fullmatch(path.name)
            if match is None:
                continue
            try:
                path.lstat()
            except FileNotFoundError:
                # A marker that vanished after the glob no longer blocks anything.
                continue
            except OSError:
                pass
            pending.add(match.group(1))
        return pending

    def _write_delete_intent(self, thread_id: str, entries: list[dict]) -> dict[str, Any]:
        path = self._delete_intent_path(thread_id)
        if path.exists():
            return self._read_delete_intent(path)
        digests = sorted({entry.get("payload", {}).get("digest") for entry in entries
                          if entry.get("type") == "attachment"
                          and isinstance(entry.get("payload", {}).get("digest"), str)
                          and _ATTACHMENT_DIGEST.fullmatch(entry["payload"]["digest"])})
        intent = {"version": 1, "threadId": thread_id,
                  "attachmentDigests": digests, "eventId": uuid.uuid4().hex}
        temporary = self.root / f".delete-{thread_id}.{uuid.uuid4().hex}.tmp"
        descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write((_json(intent) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        _fsync_directory(self.root)
        return intent

    def _recover_deletions(self) -> None:
        for path in sorted(self.root.glob(".delete-*.json")):
            try:
                intent = self._read_delete_intent(path)
            except FileNotFoundError:
                # Same snapshot rule as _pending_deletion_ids: a vanished
                # marker means there is nothing left to finish.
                continue
            except ValueError:
                # A damaged marker cannot describe what to finish. Keep it so the
                # session stays blocked, and let an explicit repair handle it
                # instead of preventing every other session from starting.
                continue
            try:
                self._finish_deletion(intent)
            except (OSError, ValueError):
                # The target cannot be removed yet (foreign file, unexpected link,
                # untrusted attachment directory). Keep the marker and retry on the
                # next start; one stuck deletion must not stop the kernel.
                continue

    def require_thread(self, thread_id: str) -> dict:
        path = self.path_for(thread_id)
        with self._lock:
            if self._delete_intent_path(thread_id).exists():
                raise ValueError("会话正在删除，暂不可读取")
            try:
                with closing(_iter_bounded_lines(path, maximum=MAX_SESSION_HEADER_BYTES,
                             label="会话头", universal_newlines=True)) as lines:
                    header = _decode_jsonl_object(next(lines), label="会话头", line_number=1)
            except FileNotFoundError:
                raise ValueError("会话不存在") from None
            except ValueError as exc:
                if "第 1 行" in str(exc):
                    raise
                raise ValueError("会话头损坏，请保留原文件后恢复") from None
            except (IndexError, StopIteration):
                raise ValueError("会话头损坏，请保留原文件后恢复") from None
            if header.get("type") != "session" or header.get("id") != thread_id:
                raise ValueError("会话头第 1 行格式无效")
            return header

    @staticmethod
    def _append_line(path: Path, value: dict) -> None:
        encoded = _encode_session_line(value)
        descriptor = open_private_file(path, os.O_RDWR | os.O_APPEND)
        try:
            original = os.fstat(descriptor)
            visible = path.lstat()
            identity = (original.st_dev, original.st_ino, original.st_mode, original.st_uid,
                        original.st_gid, original.st_nlink)
            if (not stat.S_ISREG(original.st_mode) or original.st_nlink != 1
                    or (visible.st_dev, visible.st_ino) != identity[:2]):
                raise ValueError("会话日志不是稳定的私有单链接文件")
            start = original.st_size
            if start:
                start = _truncate_partial_record_tail(descriptor, start)
            suffix = encoded
            written = 0
            try:
                os.lseek(descriptor, 0, os.SEEK_END)
                while written < len(suffix):
                    count = os.write(descriptor, suffix[written:])
                    if count <= 0:
                        raise OSError("会话日志追加未取得进展")
                    written += count
                os.fsync(descriptor)
            except BaseException as append_error:
                try:
                    current = os.fstat(descriptor)
                    visible = path.lstat()
                    current_identity = (current.st_dev, current.st_ino, current.st_mode,
                                        current.st_uid, current.st_gid, current.st_nlink)
                    if (current_identity != identity or (visible.st_dev, visible.st_ino) != identity[:2]
                            or current.st_size != start + written):
                        raise OSError("会话日志身份或长度已变化")
                    os.lseek(descriptor, start, os.SEEK_SET)
                    remaining = written
                    appended = bytearray()
                    while remaining:
                        chunk = os.read(descriptor, min(remaining, _EVENT_READ_CHUNK_BYTES))
                        if not chunk:
                            raise OSError("会话日志追加后缀读取不完整")
                        appended.extend(chunk)
                        remaining -= len(chunk)
                    if appended != suffix[:written]:
                        raise OSError("会话日志追加后缀与本次写入不一致")
                    os.ftruncate(descriptor, start)
                    os.fsync(descriptor)
                    rolled_back = os.fstat(descriptor)
                    visible = path.lstat()
                    rolled_identity = (rolled_back.st_dev, rolled_back.st_ino, rolled_back.st_mode,
                                       rolled_back.st_uid, rolled_back.st_gid, rolled_back.st_nlink)
                    if (rolled_identity != identity or rolled_back.st_size != start
                            or (visible.st_dev, visible.st_ino) != identity[:2]):
                        raise OSError("会话日志回滚结果无法确认")
                except BaseException:
                    raise SessionAppendRollbackError from append_error
                raise
        finally:
            try:
                os.close(descriptor)
            except OSError:
                # Successful fsync is the durability boundary; close errors do not undo it.
                pass

    def _write_new(self, header: dict, entries: list[dict] | None = None) -> dict:
        path = self.path_for(header["id"])
        encoded = b"".join([
            _encode_session_line(header, maximum=MAX_SESSION_HEADER_BYTES, label="会话头"),
            *(_encode_session_line(entry) for entry in entries or []),
        ])
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with self._lock, self._index.transaction() as connection:
            # Publish a complete rollout only after fsync. Hard-link creation is
            # atomic and refuses to overwrite an existing thread on an ID collision.
            try:
                descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
            # 硬链接新增的目录项与临时名删除也要落盘，否则索引行可能先于源
            # rollout 持久化；重启后的重建会把这条索引当作源已删除而清掉。
            _fsync_directory(self.root)
            self._index_thread(header["id"], connection)
        return self.get_thread(header["id"])

    def create(self, title: str = "新会话", **metadata: Any) -> dict:
        if not isinstance(title, str) or len(title) > MAX_THREAD_TITLE_CHARS:
            raise ValueError(f"title 必须是最多 {MAX_THREAD_TITLE_CHARS} 字符的字符串")
        changes = self._validate_changes(metadata)
        header = {"type": "session", "version": 2, "id": uuid.uuid4().hex[:12],
                  "sessionId": uuid.uuid4().hex, "title": title, "createdAt": _now(),
                  "archived": False, **changes}
        return self._write_new(header)

    def append(self, thread_id: str, entry: Entry) -> Entry:
        # SQLite's writer transaction also serializes JSONL appends across store instances.
        with self._lock, self._index.transaction() as connection:
            self.require_thread(thread_id)
            self._index_thread(thread_id, connection)
            self._append_line(self.path_for(thread_id), entry.to_dict())
            self._index_thread(thread_id, connection)
        return entry

    def append_many(self, thread_id: str, entries: list[Entry], *, maximum_bytes: int | None = None) -> list[Entry]:
        """Durably append entries and refresh their SQLite projection once."""
        if not isinstance(entries, list) or any(not isinstance(entry, Entry) for entry in entries):
            raise ValueError("会话追加批次必须是 Entry 列表")
        if maximum_bytes is not None and (type(maximum_bytes) is not int or maximum_bytes < 1):
            raise ValueError("会话追加上限必须是正整数")
        if not entries:
            return []
        encoded = [_encode_session_line(entry.to_dict()) for entry in entries]
        path = self.path_for(thread_id)
        with self._lock, self._index.transaction() as connection:
            self.require_thread(thread_id)
            current_size = path.stat().st_size
            if maximum_bytes is not None:
                prefix_size = 0
                if current_size:
                    with path.open("rb") as handle:
                        handle.seek(-1, os.SEEK_END)
                        prefix_size = int(handle.read(1) != bytes([10]))
                if current_size + prefix_size + sum(map(len, encoded)) > maximum_bytes:
                    raise SessionSizeLimitExceeded("会话历史超过续接读取上限。")
            self._index_thread(thread_id, connection)
            for entry in entries:
                self._append_line(path, entry.to_dict())
            self._index_thread(thread_id, connection)
        return entries

    def append_attachment(self, thread_id: str, entry: Entry, publish: Callable[[], None]) -> Entry:
        """Publish an attachment and its durable reference under the shared writer lock."""
        payload = entry.payload or {}
        digest = payload.get("digest")
        if entry.type != "attachment" or not isinstance(digest, str) or not _ATTACHMENT_DIGEST.fullmatch(digest):
            raise ValueError("附件记录格式无效")
        if not callable(publish):
            raise ValueError("附件发布器无效")
        with self._lock, self._index.transaction() as connection:
            # Reject damaged history before publishing content or appending a reference.
            with self.open_entries_snapshot(thread_id) as entries:
                for _entry in entries:
                    pass
            publish()
            _fsync_directory(self.attachments_root)
            self._append_line(self.path_for(thread_id), entry.to_dict())
            self._index_thread(thread_id, connection)
        return entry

    def cleanup_unreferenced_attachments(self, digests: list[str]) -> None:
        """Serialize failed-publication cleanup with attachment adds and deletion."""
        with self._lock, self._index.transaction():
            self._purge_unreferenced_attachments(digests)

    def cleanup_attachment_temporaries(self) -> None:
        """Remove only private temp names left by interrupted attachment publication."""
        with self._lock, self._index.transaction():
            try:
                directory_stat = self.attachments_root.lstat()
            except FileNotFoundError:
                return
            current_uid = getattr(os, "getuid", lambda: -1)()
            if not stat.S_ISDIR(directory_stat.st_mode) or directory_stat.st_uid != current_uid:
                raise ValueError("附件目录不可信，临时文件清理已暂停")
            changed = False
            try:
                entries = os.scandir(self.attachments_root)
            except OSError:
                raise ValueError("附件目录不可读取，临时文件清理已暂停") from None
            with entries:
                for entry in entries:
                    if _ATTACHMENT_TEMP.fullmatch(entry.name) is None:
                        continue
                    path = self.attachments_root / entry.name
                    try:
                        original = path.lstat()
                    except OSError:
                        raise ValueError("附件临时文件发生变化，清理已暂停") from None
                    if (not stat.S_ISREG(original.st_mode) or original.st_uid != current_uid
                            or original.st_nlink != 1):
                        raise ValueError("附件临时文件不可信，清理已暂停")
                    restrict_private_file(path)
                    path.unlink()
                    changed = True
            if changed:
                _fsync_directory(self.attachments_root)

    def append_tool_revision(self, thread_id: str, entry: Entry) -> tuple[Entry, bool]:
        """Append a terminal tool revision, reconciling one ambiguous failure.

        The entry identity and payload are fixed before this method is called.
        A result that reached JSONL is fsynced and reused; a missing result gets
        at most one append retry. No handler or approval is replayed here.
        """
        payload = entry.payload or {}
        if (entry.type != "item" or payload.get("kind") != "toolCall"
                or not isinstance(payload.get("revises"), str)):
            raise ValueError("工具结果修订格式无效")
        path = self.path_for(thread_id)
        expected = entry.to_dict()
        outcome = "absent"
        last_error: Exception | None = None

        def inspect_and_sync() -> str:
            nonlocal outcome
            found = False
            try:
                for line_number, line in enumerate(_iter_bounded_lines(
                        path, maximum=MAX_SESSION_LINE_BYTES, label="会话日志",
                        universal_newlines=True), start=1):
                    if not line.strip():
                        continue
                    current = _decode_session_record(line, line_number=line_number)
                    if current is None:
                        continue
                    if current.get("id") == entry.id:
                        if current != expected:
                            return "conflict"
                        found = True
            except ValueError as exc:
                raise ToolRevisionPersistenceError("invalid") from exc
            if not found:
                return "absent"
            try:
                with path.open("r+b") as handle:
                    os.fsync(handle.fileno())
            except OSError:
                return "present_uncertain"
            return "durable"

        try:
            with self._lock, self._index.transaction() as connection:
                self.require_thread(thread_id)
                self._index_thread(thread_id, connection)
                self._append_line(path, expected)
                self._index_thread(thread_id, connection)
            return entry, False
        except Exception as exc:
            last_error = exc

        for attempt in range(2):
            try:
                with self._lock, self._index.transaction() as connection:
                    self.require_thread(thread_id)
                    outcome = inspect_and_sync()
                    if outcome == "durable":
                        self._index_thread(thread_id, connection)
                        return entry, True
                    if outcome in {"conflict", "present_uncertain"}:
                        raise ToolRevisionPersistenceError(outcome)
                    if attempt == 0:
                        self._append_line(path, expected)
                        self._index_thread(thread_id, connection)
                        return entry, True
            except ToolRevisionPersistenceError:
                raise
            except Exception as exc:
                last_error = exc
                try:
                    with self._lock, self._index.transaction():
                        self.require_thread(thread_id)
                        outcome = inspect_and_sync()
                    if outcome == "durable":
                        return entry, True
                except Exception as reconcile_error:
                    last_error = reconcile_error
                    outcome = "uncertain"
                if outcome in {"conflict", "present_uncertain"}:
                    raise ToolRevisionPersistenceError(outcome) from exc
            if attempt == 1 or outcome != "absent":
                raise ToolRevisionPersistenceError(outcome) from last_error
        raise ToolRevisionPersistenceError(outcome) from last_error

    def append_checkpoint(self, thread_id: str, entry_factory: Callable[[], Entry], *,
                          on_committed: Callable[[], None] | None = None) -> Entry:
        """Publish a fully fsynced checkpoint copy on a local filesystem.

        The writer transaction covers source validation and publication across
        store instances. Replacement is the process-visible commit point; a
        successful publication also syncs the session directory so the new
        inode survives an abrupt power loss.
        """
        if not callable(entry_factory) or (on_committed is not None and not callable(on_committed)):
            raise ValueError("摘要提交回调必须可调用")
        temporary: Path | None = None
        entry: Entry | None = None
        committed = False
        try:
            with self._lock, self._index.transaction() as connection:
                path = self.path_for(thread_id)
                original = path.lstat()
                current_uid = getattr(os, "getuid", None)
                if (not stat.S_ISREG(original.st_mode) or original.st_nlink != 1
                        or current_uid is None or original.st_uid != current_uid()):
                    raise ValueError("摘要仅支持当前用户拥有的普通单链接会话文件")
                original_identity = (original.st_dev, original.st_ino)
                original_signature = (original.st_dev, original.st_ino, original.st_size,
                                      original.st_mtime_ns, original.st_ctime_ns,
                                      original.st_mode, original.st_uid, original.st_gid, original.st_nlink)
                with path.open("rb") as source:
                    opened = os.fstat(source.fileno())
                    opened_signature = (opened.st_dev, opened.st_ino, opened.st_size,
                                        opened.st_mtime_ns, opened.st_ctime_ns,
                                        opened.st_mode, opened.st_uid, opened.st_gid, opened.st_nlink)
                    if opened_signature != original_signature or not stat.S_ISREG(opened.st_mode):
                        raise ValueError("会话文件已变化，请重新读取摘要来源")
                    self.require_thread(thread_id)
                    # This callback must read/validate the final source without
                    # opening a second SQLite writer transaction.
                    entry = entry_factory()
                    if not isinstance(entry, Entry) or entry.type != "context_checkpoint":
                        raise ValueError("摘要提交必须构造 context_checkpoint 条目")
                    encoded = _encode_session_line(entry.to_dict())
                    candidate_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.checkpoint.tmp")
                    descriptor = open_private_file(candidate_path, os.O_WRONLY | os.O_EXCL)
                    temporary = candidate_path
                    with os.fdopen(descriptor, "wb") as target:
                        last_byte = b""
                        copied = 0
                        complete_end = 0
                        while chunk := source.read(1024 * 1024):
                            target.write(chunk)
                            copied += len(chunk)
                            boundary = chunk.rfind(b"\n")
                            if boundary >= 0:
                                complete_end = copied - len(chunk) + boundary + 1
                            last_byte = chunk[-1:]
                        if last_byte and last_byte != b"\n":
                            # 崩溃可能留下没有换行的半条记录；补换行会把它固化成一条
                            # 非法行，之后每次读取都会失败。与 `_append_line` 一样只保留
                            # 最后一个完整记录边界；找不到边界时拒绝发布候选文件。
                            if not complete_end:
                                raise ValueError("会话日志末尾缺少完整记录边界")
                            target.truncate(complete_end)
                            target.seek(complete_end)
                        target.write(encoded)
                        target.flush()
                        os.fchown(target.fileno(), -1, original.st_gid)
                        os.fchmod(target.fileno(), 0o600)
                        os.fsync(target.fileno())
                        candidate = os.fstat(target.fileno())
                        candidate_identity = (candidate.st_dev, candidate.st_ino)
                    copied = os.fstat(source.fileno())
                    copied_signature = (copied.st_dev, copied.st_ino, copied.st_size,
                                        copied.st_mtime_ns, copied.st_ctime_ns,
                                        copied.st_mode, copied.st_uid, copied.st_gid, copied.st_nlink)
                    if copied_signature != original_signature:
                        raise ValueError("会话文件在摘要复制期间变化，请重新读取摘要来源")
                candidate_stat = temporary.lstat()
                candidate_signature = (candidate_stat.st_dev, candidate_stat.st_ino,
                                       candidate_stat.st_size, candidate_stat.st_mtime_ns,
                                       candidate_stat.st_ctime_ns, candidate_stat.st_mode,
                                       candidate_stat.st_uid, candidate_stat.st_gid, candidate_stat.st_nlink)
                expected_candidate_signature = (candidate_identity[0], candidate_identity[1],
                    candidate.st_size, candidate.st_mtime_ns, candidate.st_ctime_ns, candidate.st_mode,
                    candidate.st_uid, candidate.st_gid, candidate.st_nlink)
                if candidate_signature != expected_candidate_signature:
                    raise ValueError("已同步的摘要候选文件在发布前变化")
                visible_before_replace = path.lstat()
                visible_signature = (visible_before_replace.st_dev, visible_before_replace.st_ino,
                                     visible_before_replace.st_size, visible_before_replace.st_mtime_ns,
                                     visible_before_replace.st_ctime_ns, visible_before_replace.st_mode,
                                     visible_before_replace.st_uid, visible_before_replace.st_gid,
                                     visible_before_replace.st_nlink)
                if visible_signature != original_signature or not stat.S_ISREG(visible_before_replace.st_mode):
                    raise ValueError("会话文件在摘要发布前变化，请重新读取摘要来源")
                try:
                    os.replace(temporary, path)
                except Exception as exc:
                    try:
                        visible = path.lstat()
                    except OSError:
                        raise CheckpointCommitUncertain(entry.id) from exc
                    visible_identity = (visible.st_dev, visible.st_ino)
                    if visible_identity == original_identity:
                        raise
                    if visible_identity != candidate_identity or not stat.S_ISREG(visible.st_mode):
                        raise CheckpointCommitUncertain(entry.id) from exc
                    # This is identity with the already-fsynced inode, not a
                    # content readback pretending that a failed fsync succeeded.
                else:
                    try:
                        visible = path.lstat()
                    except OSError as exc:
                        raise CheckpointCommitUncertain(entry.id) from exc
                    if ((visible.st_dev, visible.st_ino) != candidate_identity
                            or not stat.S_ISREG(visible.st_mode)):
                        raise CheckpointCommitUncertain(entry.id)
                committed = True
                # 候选内容已经 fsync，但替换只改变进程可见的目录项；在事务内同步
                # 会话目录，避免提交回执成功后掉电又回到旧 inode。此处失败由上层
                # 按已提交异常处理，不能伪装成未提交后重试。
                _fsync_directory(path.parent)
                if on_committed is not None:
                    on_committed()
                self._index_thread(thread_id, connection)
            return entry
        except Exception as exc:
            if committed and entry is not None:
                raise CheckpointCommittedError(entry.id) from exc
            raise
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except Exception:
                    pass  # Cleanup cannot undo or obscure the publication result.

    def last_entry_id(self, thread_id: str) -> str | None:
        entries = self.read_entries(thread_id)
        return entries[-1]["id"] if entries else None

    def read_entries(self, thread_id: str) -> list[dict]:
        with self._lock:
            self.require_thread(thread_id)
            with self.path_for(thread_id).open("rb") as handle:
                stat_result = os.fstat(handle.fileno())
                stamp = (stat_result.st_size, stat_result.st_mtime_ns, stat_result.st_ino)
                cached = self._touch_cached_entries(thread_id, stamp)
                if cached is not None:
                    return list(cached[2])
                previous = self._appendable_entries(thread_id, stamp, handle)
                if previous is not None:
                    entries, line_count = self._read_appended_entries(handle, previous, stamp)
                else:
                    entries, line_count = self._read_all_entries(handle, stamp)
                if self._line_boundary(handle, stamp[0]):
                    self._store_entries(thread_id, stamp, line_count, entries)
                return list(entries)

    def read_entries_snapshot(self, thread_id: str) -> list[dict]:
        """Decode one pinned prefix without holding the writer lock while scanning.

        `read_entries` keeps the store lock for the whole decode, so a large
        rollout blocks every other session's reads and appends for seconds.
        Callers that only project a display view can pin the prefix under the
        lock and decode it outside; the returned entries lag at most by appends
        that land after the pin, exactly like any other point-in-time read.
        Repeated reads without an append reuse the bounded entry cache instead
        of decoding the same rollout again.
        """
        with self._lock:
            self.require_thread(thread_id)
            stamp = self._entries_stamp(thread_id)
            cached = self._touch_cached_entries(thread_id, stamp)
            if cached is not None:
                return list(cached[2])
        with self.open_entries_snapshot(thread_id) as snapshot:
            entries = list(snapshot)
            line_count = snapshot.line_count
        # 只有解码期间没有新的追加（文件仍是同一前缀）时才挂到该 stamp 下；
        # 否则缓存会以新文件的身份返回旧前缀，下一次命中就掩盖了新条目。
        with self._lock:
            try:
                current = self._entries_stamp(thread_id)
            except (FileNotFoundError, ValueError):
                current = None
            if current == snapshot.stamp:
                self._store_entries(thread_id, current, line_count, entries)
        return list(entries)

    def _entries_stamp(self, thread_id: str) -> tuple[int, int, int]:
        stat_result = self.path_for(thread_id).stat()
        return stat_result.st_size, stat_result.st_mtime_ns, stat_result.st_ino

    def _touch_cached_entries(self, thread_id: str, stamp: tuple[int, int, int]):
        cached = self._entries_cache.get(thread_id)
        if cached is None or cached[0] != stamp:
            return None
        # 最近使用排在末尾，超限时淘汰最久未用的会话。
        self._entries_cache.pop(thread_id, None)
        self._entries_cache[thread_id] = cached
        return cached

    def _appendable_entries(self, thread_id: str, stamp: tuple[int, int, int], handle):
        """Return the cached prefix when only an append separates it from `stamp`.

        缓存必须来自同一 inode、严格更短的前缀，且旧前缀末尾在当前文件上仍是
        换行边界；外部截断重写会破坏其中一条，按全量重新解码。
        """
        cached = self._entries_cache.get(thread_id)
        if cached is None:
            return None
        (size, _, inode), line_count, entries = cached
        if inode != stamp[2] or not 0 < size < stamp[0]:
            return None
        handle.seek(size - 1)
        if handle.read(1) != b"\n":
            return None
        self._entries_cache.pop(thread_id, None)
        self._entries_cache[thread_id] = cached
        return size, line_count, entries

    def _read_all_entries(self, handle, stamp: tuple[int, int, int]) -> tuple[list[dict], int]:
        handle.seek(0)
        out: list[dict] = []
        line_count = 0
        for line_count, line in enumerate(_iter_bounded_raw_lines_from_handle(
                handle, maximum=MAX_SESSION_LINE_BYTES, label="会话日志",
                universal_newlines=True, byte_limit=stamp[0]), start=1):
            if not line.strip():
                continue
            data = _decode_session_record(line, line_number=line_count)
            if data is not None:
                out.append(data)
        return out, line_count

    def _read_appended_entries(self, handle, previous: tuple[int, int, list[dict]],
                               stamp: tuple[int, int, int]) -> tuple[list[dict], int]:
        size, line_count, entries = previous
        handle.seek(size)
        appended: list[dict] = []
        added = 0
        for added, line in enumerate(_iter_bounded_raw_lines_from_handle(
                handle, maximum=MAX_SESSION_LINE_BYTES, label="会话日志",
                universal_newlines=True, byte_limit=stamp[0] - size), start=1):
            if not line.strip():
                continue
            data = _decode_session_record(line, line_number=line_count + added)
            if data is not None:
                appended.append(data)
        return entries + appended, line_count + added

    def _line_boundary(self, handle, size: int) -> bool:
        if size <= 0:
            return False
        handle.seek(size - 1)
        return handle.read(1) == b"\n"

    def _store_entries(self, thread_id: str, stamp: tuple[int, int, int], line_count: int,
                       entries: list[dict]) -> None:
        self._entries_cache.pop(thread_id, None)
        self._entries_cache[thread_id] = (stamp, line_count, entries)
        while len(self._entries_cache) > _MAX_ENTRIES_CACHE_THREADS:
            self._entries_cache.pop(next(iter(self._entries_cache)))

    def open_entries_snapshot(self, thread_id: str) -> SessionEntriesSnapshot:
        """Pin a readable session prefix without holding the writer lock while scanning."""
        with self._lock:
            self.require_thread(thread_id)
            source = self.path_for(thread_id).open("rb")
            try:
                stat_result = os.fstat(source.fileno())
                size = _complete_record_limit(source, stat_result.st_size)
                return SessionEntriesSnapshot(source, size,
                                              stat_result.st_mtime_ns, stat_result.st_ino)
            except BaseException:
                source.close()
                raise

    def open_snapshot_source(self, thread_id: str) -> tuple[io.BufferedReader, int, str]:
        """Pin one rollout inode and cursor while session writers are excluded."""
        with self._lock:
            self.require_thread(thread_id)
            with self._index.connection() as connection:
                event_checkpoint = connection.execute(
                    "SELECT value FROM checkpoints WHERE name='events'").fetchone()
                if self.events_path.exists():
                    stat_result = self.events_path.stat()
                    fingerprint = f"{stat_result.st_size}:{stat_result.st_mtime_ns}"
                    if event_checkpoint is None or event_checkpoint["value"] != fingerprint:
                        raise ValueError("事件索引与日志不同步，请重试冻结快照")
                elif event_checkpoint is not None:
                    raise ValueError("事件索引与日志不同步，请重试冻结快照")
                cursor = str(connection.execute(
                    "SELECT COALESCE(MAX(cursor),0) FROM events").fetchone()[0])
            source = self.path_for(thread_id).open("rb")
            try:
                # 固定范围同样收敛到完整记录边界；快照构建从当前游标顺序读取，读回起点。
                size = _complete_record_limit(source, os.fstat(source.fileno()).st_size)
                source.seek(0)
                return source, size, cursor
            except BaseException:
                source.close()
                raise

    def snapshot_projection(self, thread_id: str, *, include_turns: bool = True,
                            max_turn_bytes: int = 1024 * 1024
                            ) -> tuple[dict, list[dict], bool]:
        """Read indexed metadata at the caller's cut; skipped turns are not budgeted."""
        with self._lock:
            if self._delete_intent_path(thread_id).exists():
                raise ValueError("会话正在删除，暂不可读取")

            def read() -> tuple[dict, list[dict], bool]:
                with self._index.connection() as connection:
                    thread = connection.execute(
                        "SELECT id,metadata_json,indexed_size,indexed_mtime_ns FROM threads WHERE id=?",
                        (thread_id,)).fetchone()
                    if thread is None:
                        raise ValueError("会话不存在")
                    stat_result = self.path_for(thread_id).stat()
                    if (thread["indexed_size"], thread["indexed_mtime_ns"]
                            ) != (stat_result.st_size, stat_result.st_mtime_ns):
                        raise ValueError("会话索引与日志不同步，请重试冻结快照")
                    metadata = self._thread_metadata(thread)
                    turns = []
                    if not include_turns:
                        return metadata, turns, False
                    rows = connection.execute("""SELECT thread_id,metadata_json FROM turns
                        WHERE thread_id=? ORDER BY first_ordinal,turn_id LIMIT 50""", (thread_id,))
                    turn_bytes = 0
                    for row in rows:
                        raw = row["metadata_json"]
                        if not isinstance(raw, str):
                            # 投影列被改写为 BLOB / 整数时交给既有重建路径，不能让
                            # .encode() 的 AttributeError 绕过重试逃逸成 -32603。
                            raise _IndexedMetadataError(row["thread_id"])
                        turn_bytes += len(raw.encode("utf-8"))
                        if turn_bytes > max_turn_bytes:
                            return metadata, turns, True
                        turns.append(self._turn_metadata(row))
                return metadata, turns, False

            return self._with_repaired_index(read)

    def read(self, thread_id: str) -> list[dict]:
        """Read all rollout entries, including queue/context/approval extension records."""
        return self.read_entries(thread_id)

    @staticmethod
    def _project_items(thread_id: str, entries: list[dict]) -> list[dict]:
        """One logical item for each original ID; revisions retain all structured fields."""
        items: list[dict] = []
        index_by_id: dict[str, int] = {}
        for entry in entries:
            if entry.get("type") != "item":
                continue
            payload = dict(entry.get("payload") or {})
            # 空 id 与缺 id 一样无法作为编辑、内容引用和快照分页的稳定定位键；
            # 普通读取与冻结快照都跳过这类记录，不让一条坏记录使整次恢复失败。
            entry_id = _record_id(entry.get("id")) or ""
            if not entry_id:
                continue
            target_id = _record_id(payload.get("revises")) or ""
            if not target_id and payload.get("kind") == "toolCall" and payload.get("status") != "running":
                parent_id = str(entry.get("parentId") or "")
                if parent_id in index_by_id and items[index_by_id[parent_id]].get("kind") == "toolCall":
                    target_id = parent_id
            # 投影出口收敛编号字段：上下文、请求身份与分叉会把它们用作集合成员。
            for field in _ITEM_ID_FIELDS:
                if field in payload and not isinstance(payload[field], str):
                    del payload[field]
            # 非对象 approval 不描述任何审批；分支操作应按「没有待决审批」处理。
            if "approval" in payload and not isinstance(payload["approval"], dict):
                del payload["approval"]
            if target_id and target_id in index_by_id:
                slot = index_by_id[target_id]
                items[slot] = {**items[slot], **payload, "id": items[slot]["id"], "threadId": thread_id}
                index_by_id[entry_id] = slot
            else:
                if entry_id in index_by_id:
                    # 同一编号的条目重复出现（外部改写或异常写入）：投影只能保留一条，
                    # 否则编辑、压缩与分叉按编号定位时会同时命中多条消息。保留先出现
                    # 的记录并跳过后续同编号条目，损坏记录不阻断整段历史。
                    continue
                index_by_id[entry_id] = len(items)
                items.append({**payload, "id": entry_id, "threadId": thread_id})
        return items

    def read_items(self, thread_id: str) -> list[dict]:
        return self._project_items(thread_id, self.read_entries(thread_id))

    def read_item(self, thread_id: str, item_id: str) -> dict | None:
        """Project one logical item while retaining only its live revision aliases."""
        if not isinstance(item_id, str) or not item_id or len(item_id) > 128:
            raise ValueError("itemId 格式无效")
        aliases: set[str] = set()
        alias_bytes = 0
        revision_records = 0
        selected: dict | None = None
        with self.open_entries_snapshot(thread_id) as entries:
            for entry in entries:
                if entry.get("type") != "item":
                    continue
                payload = dict(entry.get("payload") or {})
                entry_id = str(entry.get("id") or "")
                target_id = str(payload.get("revises") or "")
                if (not target_id and payload.get("kind") == "toolCall"
                        and payload.get("status") != "running"):
                    parent_id = str(entry.get("parentId") or "")
                    if (selected is not None and parent_id in aliases
                            and selected.get("kind") == "toolCall"):
                        target_id = parent_id

                if target_id in aliases:
                    if entry_id == item_id:
                        raise ItemLookupError("INVALID_RESULT_REFERENCE", "结果条目身份存在冲突")
                    revision_records += 1
                    if revision_records > MAX_ITEM_REVISION_RECORDS:
                        raise ItemLookupError("RESULT_HISTORY_LIMIT", "工具结果修订历史超过读取上限")
                    if len(entry_id) > 128:
                        raise ItemLookupError("RESULT_HISTORY_LIMIT", "工具结果修订别名超过长度上限")
                    if entry_id not in aliases and len(aliases) >= MAX_ITEM_REVISION_ALIASES:
                        raise ItemLookupError("RESULT_HISTORY_LIMIT", "工具结果修订历史超过读取上限")
                    if entry_id not in aliases:
                        alias_bytes += len(entry_id.encode("utf-8"))
                        if alias_bytes > MAX_ITEM_REVISION_ALIAS_BYTES:
                            raise ItemLookupError("RESULT_HISTORY_LIMIT", "工具结果修订别名超过大小上限")
                    aliases.add(entry_id)
                    if "kind" in payload:
                        selected["kind"] = payload["kind"]
                    if "result" in payload:
                        selected["result"] = payload["result"]
                    continue

                if entry_id == item_id:
                    if selected is not None or target_id or (
                            payload.get("kind") == "toolCall" and payload.get("status") != "running"
                            and entry.get("parentId")):
                        raise ItemLookupError("INVALID_RESULT_REFERENCE", "结果条目身份存在冲突")
                    selected = {"id": item_id, "threadId": thread_id}
                    for key in ("kind", "result"):
                        if key in payload:
                            selected[key] = payload[key]
                    aliases.add(entry_id)
                    alias_bytes = len(entry_id.encode("utf-8"))
                else:
                    if entry_id in aliases:
                        aliases.remove(entry_id)
                        alias_bytes -= len(entry_id.encode("utf-8"))
        return selected

    @staticmethod
    def _valid_approval_item(item: dict, *, pending_only: bool) -> bool:
        approval = item.get("approval")
        arguments = item.get("toolArguments")
        decision = approval.get("decision") if isinstance(approval, dict) else None
        tool_name = approval.get("toolName") if isinstance(approval, dict) else None
        visible_name = tool_name.strip() if isinstance(tool_name, str) else ""
        item_id = item.get("id")
        visible_item_id = item_id.strip() if isinstance(item_id, str) else ""
        # 桌面按去空白后的非空、≤200 字符展示工具名与条目 id；无法展示的审批不能进入索引、
        # 列表或持久计数，否则铃铛总数会大于通知面板中可处理的条目。
        if (item.get("kind") != "toolCall" or not isinstance(approval, dict)
                or (decision is not None and (not isinstance(decision, str)
                    or decision not in {"approve", "deny", "expired"}))
                or not isinstance(approval.get("approvalId"), str)
                or not _EVENT_ID.fullmatch(approval["approvalId"])
                or not visible_name
                or len(visible_name) > _APPROVAL_VIEW_FIELD_CHARS
                or not visible_item_id
                or len(visible_item_id) > _APPROVAL_VIEW_FIELD_CHARS
                or tool_name != item.get("toolName")
                or not isinstance(item.get("turnId"), str)
                or not _IDENTIFIER.fullmatch(item["turnId"])
                or type(arguments) is not dict or approval.get("params") != arguments):
            return False
        status, execution_state = item.get("status"), item.get("executionState")
        if not isinstance(status, str) or not isinstance(execution_state, str):
            return False
        if pending_only or decision is None:
            if status != "running" or execution_state != "pending_approval":
                return False
        elif decision == "approve":
            if (not isinstance(status, str) or status not in {"running", "failed", "completed"}
                    or not isinstance(execution_state, str)
                    or execution_state not in {
                        "approved", "executing", "completed", "failed", "not_executed", "outcome_unknown"
                    }):
                return False
        elif decision == "deny":
            if status not in {"running", "failed"} or execution_state != "not_approved":
                return False
        elif status not in {"running", "failed"} or execution_state != "not_executed":
            return False
        deadline = approval.get("deadline")
        try:
            deadline_valid = (type(deadline) in {int, float} and math.isfinite(float(deadline))
                              and deadline > 0)
        except (OverflowError, TypeError, ValueError):
            deadline_valid = False
        if not deadline_valid:
            return False
        description = approval.get("description")
        if not isinstance(description, str) or len(description) > 1_000:
            return False
        try:
            digest = approval_parameters_digest(arguments)
        except ValueError:
            return False
        return approval.get("paramsDigest") == digest

    def _pending_approvals_where(self, thread_id: str | None) -> tuple[str, list[Any]] | None:
        """待审批的共享过滤条件；删除占位过多时返回 None，调用方放弃整次读取。"""
        pending_deletions = sorted(self._pending_deletion_ids())
        if len(pending_deletions) > 800:
            return None
        where = """ FROM approvals a
                    JOIN threads t ON t.id=a.thread_id
                    JOIN turns r ON r.thread_id=a.thread_id AND r.turn_id=a.turn_id
                    WHERE a.decision IS NULL AND a.status='running'
                      AND a.execution_state='pending_approval' AND a.deadline>?
                      AND t.archived=0 AND r.status IN ('running','interrupted')
                      AND typeof(a.approval_id)='text' AND typeof(a.thread_id)='text'
                      AND typeof(a.turn_id)='text' AND typeof(a.item_id)='text'
                      AND typeof(a.tool_name)='text' AND typeof(a.params_digest)='text'
                      AND typeof(a.deadline) IN ('integer','real')
                      AND a.approval_id<>'' AND a.thread_id<>'' AND a.turn_id<>''
                      AND a.item_id<>'' AND a.tool_name<>'' AND a.params_digest<>''
                      AND a.deadline BETWEEN 0 AND 1e15"""
        parameters: list[Any] = [time.time()]
        if thread_id is not None:
            where += " AND a.thread_id=?"
            parameters.append(thread_id)
        if pending_deletions:
            where += " AND a.thread_id NOT IN (" + ",".join("?" for _ in pending_deletions) + ")"
            parameters.extend(pending_deletions)
        return where, parameters

    def pending_approvals(self, thread_id: str | None = None, *,
                          limit: int = 100) -> tuple[list[dict], bool]:
        """Return the bounded pending page and whether more pending approvals were omitted."""
        _limit(limit, maximum=200)
        if thread_id is not None:
            self.path_for(thread_id)
        with self._lock:
            if thread_id is not None:
                self.require_thread(thread_id)
            condition = self._pending_approvals_where(thread_id)
            if condition is None:
                return [], False
            where, parameters = condition
            query = ("""SELECT a.approval_id,a.thread_id,a.turn_id,a.item_id,a.tool_name,
                       a.deadline,a.params_digest""" + where
                     + " ORDER BY t.updated_at DESC,a.thread_id DESC,a.item_id DESC LIMIT ?")
            # Fetch one extra row only to distinguish “exactly at the limit” from “more remain”.
            parameters.append(limit + 1)
            with self._index.connection() as connection:
                rows = connection.execute(query, parameters).fetchall()
            truncated = len(rows) > limit
            approvals = []
            for row in rows[:limit]:
                deadline = row["deadline"]
                # 索引列不保证仍是写入时的类型：外部改写可把 deadline 变成 BLOB，
                # 原样返回会让 JSON 序列化抛 TypeError，整次 approval/list 变成
                # -32603 并连带隐藏其余可处理的审批。损坏行按缺失处理，与共享
                # 过滤条件的 typeof 守卫保持一致，列表与计数因此仍然自洽。
                deadline_valid = (type(deadline) is int
                                  or (isinstance(deadline, float) and math.isfinite(deadline)))
                if (not deadline_valid
                        or not all(isinstance(row[key], str) and row[key] for key in
                                   ("approval_id", "thread_id", "turn_id", "item_id",
                                    "tool_name", "params_digest"))):
                    continue
                approvals.append({"approvalId": row["approval_id"], "threadId": row["thread_id"],
                                  "turnId": row["turn_id"], "itemId": row["item_id"],
                                  "toolName": row["tool_name"],
                                  "summary": f"需要你批准后才会执行：{row['tool_name']}",
                                  "deadline": deadline, "paramsDigest": row["params_digest"]})
            return approvals, truncated

    def pending_approval_counts(self, thread_id: str | None = None) -> dict[str, int]:
        """按会话统计全部待审批数量，不受 approval/list 的条目上限影响。

        侧栏徽标需要覆盖列表页之外的审批；与列表共用同一组过滤条件。
        """
        if thread_id is not None:
            self.path_for(thread_id)
        with self._lock:
            if thread_id is not None:
                self.require_thread(thread_id)
            condition = self._pending_approvals_where(thread_id)
            if condition is None:
                return {}
            where, parameters = condition
            with self._index.connection() as connection:
                rows = connection.execute(
                    "SELECT a.thread_id,COUNT(*)" + where + " GROUP BY a.thread_id",
                    parameters).fetchall()
            return {str(row[0]): int(row[1]) for row in rows}

    def _append_approval_decision(self, thread_id: str, item: dict, decision: str,
                                  *, live_owner: bool) -> dict:
        approval = {**item["approval"], "decision": decision, "decidedAt": _now()}
        payload = {key: value for key, value in item.items() if key not in {"id", "threadId"}}
        payload.update(revises=item["id"], approval=approval)
        if live_owner:
            payload["executionState"] = "approved" if decision == "approve" else "not_approved"
        else:
            payload.update(status="failed")
            if decision == "approve":
                payload.update(executionState="not_executed", errorCode="SESSION_INTERRUPTED",
                               resultSummary="审批已记录，但原回合已经中断；工具未执行。若仍需执行，请发起新回合并重新审批。",
                               recoveryAction="明确发起新回合；旧审批不会触发工具执行。")
            elif decision == "deny":
                payload.update(executionState="not_approved", errorCode="NOT_APPROVED",
                               resultSummary="用户在恢复会话后拒绝了该操作。", recoveryAction=None)
            else:
                payload.update(executionState="not_executed", errorCode="APPROVAL_EXPIRED",
                               resultSummary="审批已失效；工具未执行。", recoveryAction=None)
        self.append(thread_id, Entry(type="item", parent_id=self.last_entry_id(thread_id), payload=payload))
        return {"approval": approval, "executionState": payload["executionState"],
                "status": payload.get("status", item.get("status")),
                "threadId": thread_id, "turnId": item.get("turnId"), "itemId": item["id"],
                "toolName": item["toolName"], "decision": decision,
                "executed": (True if payload["executionState"] == "completed" else
                             False if payload["executionState"] in {"not_executed", "not_approved"} else None),
                "changed": True, "errorCode": payload.get("errorCode"),
                "resultSummary": payload.get("resultSummary"),
                "recoveryAction": payload.get("recoveryAction")}

    def decide_approval(self, approval_id: str, approved: bool, *, live_owner: bool = False,
                        expire_only: bool = False) -> dict | None:
        if not isinstance(approval_id, str) or not _EVENT_ID.fullmatch(approval_id):
            raise ApprovalDecisionError("APPROVAL_INVALID", "approvalId 格式无效")
        if (type(approved) is not bool or type(live_owner) is not bool or type(expire_only) is not bool
                or (expire_only and live_owner)):
            raise ApprovalDecisionError("APPROVAL_INVALID", "审批裁决参数无效")
        requested = "approve" if approved else "deny"
        with self._lock:
            with self._index.connection() as connection:
                rows = connection.execute("SELECT thread_id,item_id FROM approvals WHERE approval_id=?",
                                          (approval_id,)).fetchall()
            if len(rows) != 1:
                code = "APPROVAL_NOT_FOUND" if not rows else "APPROVAL_AMBIGUOUS"
                message = "审批不存在或所属会话已删除" if not rows else "审批记录重复，已拒绝裁决"
                raise ApprovalDecisionError(code, message)
            thread_id, item_id = rows[0]["thread_id"], rows[0]["item_id"]
            if thread_id in self._pending_deletion_ids():
                raise ApprovalDecisionError("APPROVAL_NOT_FOUND", "审批所属会话已删除")
            thread = self.get_thread(thread_id)
            entries = self.read_entries(thread_id)
            item = next((value for value in self._project_items(thread_id, entries)
                         if value["id"] == item_id), None)
            item_approval = item.get("approval") if item is not None else None
            if item is None or not isinstance(item_approval, dict) or item_approval.get("approvalId") != approval_id:
                raise ApprovalDecisionError("APPROVAL_INVALID", "审批索引与会话记录不一致")
            approval = item.get("approval")
            if not self._valid_approval_item(item, pending_only=False):
                raise ApprovalDecisionError("APPROVAL_INVALID", "审批记录无效，已拒绝裁决")
            existing = approval.get("decision")
            if existing is not None:
                if expire_only:
                    return None
                if existing != requested:
                    raise ApprovalDecisionError("APPROVAL_CONFLICT", "该审批已经按相反决策处理")
                return {"approval": approval, "executionState": item.get("executionState"),
                        "status": item.get("status"), "threadId": thread["id"],
                        "turnId": item.get("turnId"), "itemId": item["id"],
                        "toolName": item.get("toolName"), "decision": existing,
                        "executed": (True if item.get("executionState") == "completed" else
                                     False if (isinstance(item.get("executionState"), str)
                                               and item.get("executionState") in {"not_executed", "not_approved"})
                                     else None),
                        "changed": False, "errorCode": item.get("errorCode"),
                        "resultSummary": item.get("resultSummary"),
                        "recoveryAction": item.get("recoveryAction")}
            if thread.get("archived"):
                raise ApprovalDecisionError("APPROVAL_CLOSED", "已归档会话中的审批不能裁决")
            if not self._valid_approval_item(item, pending_only=True):
                raise ApprovalDecisionError("APPROVAL_INVALID", "审批参数摘要或调用状态无效，已拒绝裁决")
            now = time.time()
            if expire_only and approval["deadline"] > now:
                return None
            if approval["deadline"] <= now:
                return self._append_approval_decision(thread["id"], item, "expired", live_owner=False)
            turn_id = item.get("turnId")
            turn = next((turn for turn in self._turns(entries, thread["id"])
                         if turn.get("turnId") == turn_id), None)
            if turn is None:
                raise ApprovalDecisionError("APPROVAL_INVALID", "审批所属回合不存在")
            if live_owner:
                if turn.get("status") != "running":
                    raise ApprovalDecisionError("APPROVAL_CLOSED", "审批所属回合已经结束")
            elif turn.get("status") != "interrupted":
                code = "APPROVAL_BUSY" if turn.get("status") == "running" else "APPROVAL_CLOSED"
                message = "审批仍由活动回合持有" if code == "APPROVAL_BUSY" else "审批所属回合状态不支持恢复裁决"
                raise ApprovalDecisionError(code, message)
            return self._append_approval_decision(thread["id"], item, requested, live_owner=live_owner)

    def expired_pending_approvals(self, *, limit: int = 32) -> list[str]:
        _limit(limit, maximum=128)
        now = time.time()
        with self._lock, self._index.connection() as connection:
            pending_deletions = sorted(self._pending_deletion_ids())
            if len(pending_deletions) > 800:
                return []
            exclusion = ""
            parameters: list[Any] = [now]
            if pending_deletions:
                exclusion = " AND a.thread_id NOT IN (" + ",".join("?" for _ in pending_deletions) + ")"
                parameters.extend(pending_deletions)
            parameters.append(limit)
            rows = connection.execute("""SELECT a.approval_id FROM approvals a
                JOIN threads t ON t.id=a.thread_id
                JOIN turns r ON r.thread_id=a.thread_id AND r.turn_id=a.turn_id
                WHERE a.decision IS NULL AND a.status='running'
                  AND a.execution_state='pending_approval' AND a.deadline<=?
                  AND t.archived=0 AND r.status='interrupted'
                  AND typeof(a.approval_id)='text' AND typeof(a.thread_id)='text'
                  AND typeof(a.turn_id)='text' AND typeof(a.item_id)='text'
                  AND typeof(a.deadline) IN ('integer','real')""" + exclusion +
                " ORDER BY a.deadline,a.thread_id,a.item_id LIMIT ?", parameters).fetchall()
        return [row["approval_id"] for row in rows]

    def next_recoverable_approval_deadline(self) -> float | None:
        with self._lock, self._index.connection() as connection:
            pending_deletions = sorted(self._pending_deletion_ids())
            if len(pending_deletions) > 800:
                return None
            exclusion = ""
            parameters: list[Any] = []
            if pending_deletions:
                exclusion = " AND a.thread_id NOT IN (" + ",".join("?" for _ in pending_deletions) + ")"
                parameters.extend(pending_deletions)
            row = connection.execute("""SELECT MIN(a.deadline) FROM approvals a
                JOIN threads t ON t.id=a.thread_id
                JOIN turns r ON r.thread_id=a.thread_id AND r.turn_id=a.turn_id
                WHERE a.decision IS NULL AND a.status='running'
                  AND a.execution_state='pending_approval' AND t.archived=0
                  AND r.status='interrupted'
                  AND typeof(a.approval_id)='text' AND typeof(a.thread_id)='text'
                  AND typeof(a.turn_id)='text' AND typeof(a.item_id)='text'
                  AND typeof(a.deadline) IN ('integer','real')""" + exclusion, parameters).fetchone()
        return row[0] if row and row[0] is not None else None

    def expire_approval(self, approval_id: str) -> dict | None:
        try:
            return self.decide_approval(approval_id, False, expire_only=True)
        except ApprovalDecisionError as exc:
            if exc.code in {"APPROVAL_NOT_FOUND", "APPROVAL_CLOSED"}:
                return None
            raise

    @staticmethod
    def _item_owners(entries: list[dict]) -> dict[str, str | None]:
        """Resolve both explicit turn IDs and legacy user-before-turn/revision ordering."""
        owners: dict[str, str | None] = {}
        pending: list[str] = []
        seen_turns: set[str] = set()
        active: str | None = None
        for entry in entries:
            payload = entry["payload"]
            if entry.get("type") == "item":
                target = _record_id(payload.get("revises"))
                if not target and payload.get("kind") == "toolCall" and payload.get("status") != "running":
                    target = _record_id(entry.get("parentId"))
                explicit = _record_id(payload.get("turnId"))
                owner = explicit if explicit is not None else owners.get(target) or active
                # 与 _project_items 保持一致：重复编号只保留先出现的归属，否则
                # 同一 id 跨回合时归属检查会与保留的条目对不上，历史永久失败。
                if entry["id"] not in owners:
                    owners[entry["id"]] = owner
                    if owner is None:
                        pending.append(entry["id"])
            elif entry.get("type") == "turn":
                turn_id = payload.get("turnId")
                if not isinstance(turn_id, str) or not _IDENTIFIER.fullmatch(turn_id):
                    continue
                if turn_id not in seen_turns:
                    for entry_id in pending:
                        owners[entry_id] = turn_id
                    pending.clear()
                    seen_turns.add(turn_id)
                if payload.get("status") == "running":
                    active = turn_id
                elif (isinstance(payload.get("status"), str)
                      and payload.get("status") in _TERMINAL and active == turn_id):
                    active = None
        return owners

    @staticmethod
    def _turns(entries: list[dict], thread_id: str) -> list[dict]:
        turns: dict[str, dict] = {}
        previous_end = -1
        for ordinal, entry in enumerate(entries):
            if entry.get("type") == "task_phase":
                payload = entry.get("payload")
                if not isinstance(payload, dict):
                    continue
                task_id = payload.get("taskId")
                turn = turns.get(task_id) if isinstance(task_id, str) else None
                phase, status = payload.get("phase"), payload.get("status")
                attempt, restart_limit = payload.get("attempt"), payload.get("restartLimit")
                if (payload.get("ownerKind") == "turn" and turn is not None
                        and isinstance(phase, str) and phase in _TASK_PHASES
                        and isinstance(status, str) and status in _TERMINAL | {"running"}
                        and type(attempt) is int and 1 <= attempt <= 1_000
                        and type(restart_limit) is int and 0 <= restart_limit <= 32):
                    turn.update(taskPhase=phase, taskPhaseStatus=status, taskAttempt=attempt,
                                taskRestartLimit=restart_limit)
                    if (isinstance(payload.get("recoveryReason"), str)
                            and len(payload["recoveryReason"]) <= 256):
                        turn["taskRecoveryReason"] = payload["recoveryReason"]
                    if (isinstance(payload.get("resumePolicy"), str)
                            and payload["resumePolicy"] in {"manual", "closed"}):
                        turn["taskResumePolicy"] = payload["resumePolicy"]
                continue
            if entry.get("type") != "turn":
                continue
            payload = entry["payload"]
            turn_id = payload.get("turnId")
            if not isinstance(turn_id, str) or not _IDENTIFIER.fullmatch(turn_id):
                continue
            turn = turns.get(turn_id)
            if turn is None:
                turn = {"turnId": turn_id, "threadId": thread_id,
                        "startedAt": entry.get("timestamp", ""), "firstOrdinal": previous_end + 1}
                turns[turn_id] = turn
            first_ordinal = turn["firstOrdinal"]
            # 持久载荷不可信：顺序字段是归并过程的记账，不能被同名键覆盖。否则首条
            # 终态记录的 boundaryOrdinal 会原样留在内部对象上，fork 的边界切片拿到
            # 字符串就抛 TypeError（-32603），拿到负数则静默截断分支。
            turn.update({key: value for key, value in payload.items()
                         if key not in _TURN_INTERNAL_FIELDS})
            turn.update(threadId=thread_id, turnId=turn_id, firstOrdinal=first_ordinal,
                        lastOrdinal=ordinal, updatedAt=entry.get("timestamp", ""))
            if isinstance(turn.get("status"), str) and turn.get("status") in _TERMINAL:
                turn.setdefault("boundaryOrdinal", ordinal)
                turn.setdefault("completedAt", entry.get("timestamp", ""))
                previous_end = ordinal
        return list(turns.values())

    @staticmethod
    def _public_turn(turn: dict) -> dict:
        return {key: value for key, value in turn.items()
                if key not in _TURN_INTERNAL_FIELDS}

    @staticmethod
    def _queue_status_counts(entries: list[dict]) -> dict[str, int]:
        """按队列项 id 归并最新状态，分别统计尚未形成回合的待处理项。"""
        statuses: dict[str, str] = {}
        for entry in entries:
            if entry.get("type") != "queue":
                continue
            # 与 TurnQueue.list 共用同一结构契约：缺 kind、input 或状态枚举之外的
            # 损坏记录必须跳过，不能覆盖同一 id 先前记录的有效状态，否则会话列表
            # 的待处理数会与 queue/list 的实际条目对不上。
            record = queue_record(entry.get("payload"))
            if record is not None:
                statuses[record["id"]] = record["status"]
        counts = {"queued": 0, "delivering": 0, "paused": 0}
        for status in statuses.values():
            if status in ACTIVE_QUEUE_STATUSES:
                counts[status] += 1
        return counts

    def _index_thread(self, thread_id: str, connection: sqlite3.Connection) -> None:
        path = self.path_for(thread_id)
        header = self.require_thread(thread_id)
        stat = path.stat()
        previous = connection.execute(
            "SELECT indexed_size,indexed_mtime_ns FROM threads WHERE id=?", (thread_id,)
        ).fetchone()
        if previous and tuple(previous) == (stat.st_size, stat.st_mtime_ns):
            return
        entries = self.read_entries(thread_id)
        metadata = {key: value for key, value in header.items() if key not in {"type", "version"}}
        for entry in entries:
            if entry.get("type") == "thread_info":
                # Unknown existing fields are retained, and the raw header is never rewritten.
                metadata.update({key: value for key, value in entry["payload"].items()
                                 if key not in {"id", "sessionId", "createdAt"}})
        metadata.update(id=thread_id, sessionId=header.get("sessionId") or thread_id,
                        title=metadata.get("title", "未命名会话"),
                        createdAt=header.get("createdAt", ""),
                        updatedAt=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        archived=bool(metadata.get("archived", False)))
        # Persisted metadata is untrusted. These fields only feed listing and
        # display, never an authorization or execution decision, so a malformed
        # value falls back to its neutral default instead of making the whole
        # session unreadable. The fallback keeps every value bound to its SQL
        # column the expected type: a raw binding error must not escape startup.
        if not isinstance(metadata["sessionId"], str):
            metadata["sessionId"] = thread_id
        if not isinstance(metadata["title"], str):
            metadata["title"] = "未命名会话"
        if not isinstance(metadata["createdAt"], str):
            metadata["createdAt"] = ""
        if metadata.get("projectId") is not None and not isinstance(metadata["projectId"], str):
            metadata["projectId"] = None
        turns = self._turns(entries, thread_id)
        metadata["lastTurn"] = self._public_turn(turns[-1]) if turns else None
        # 切换过位置的会话另报当前分支末回合。``lastTurn`` 保持日志末回合，未感知分支的
        # 客户端语义不变；列表侧的状态与继续入口需要的是当前位置上的回合。字段只由本会话
        # 条目推导：会话头或 thread_info 带来的同名值先清掉。取值与 ``branch_last_turn``
        # 一致（当前分支末回合在日志回合表中的那一行）。
        metadata.pop("branchLastTurn", None)
        if any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):
            try:
                leaf_turn_id = self._leaf_state(thread_id, entries)["leafTurnId"]
            except ValueError:
                # 条目编号重复时分支无法投影：分支读取会报出具体错误，列表不因此整体失败，
                # 也不猜测位置；缺少该字段时客户端沿用 lastTurn。
                pass
            else:
                metadata["branchLastTurn"] = next(
                    (self._public_turn(turn) for turn in turns if turn["turnId"] == leaf_turn_id), None)
        queue_counts = self._queue_status_counts(entries)
        metadata["queueActiveItems"] = sum(queue_counts.values())
        # 队列派生字段只由本会话条目决定：头部可能带着来源会话或上一轮索引的旧值，
        # 计数为零时必须清掉，否则空队列的分支会被列表当成「待你处理」。
        if metadata["queueActiveItems"]:
            metadata["queueCounts"] = queue_counts
        else:
            metadata.pop("queueCounts", None)
        try:
            connection.execute("""INSERT INTO threads
                (id,session_id,rollout_path,title,project_id,archived,created_at,updated_at,
                 last_turn_id,metadata_json,indexed_size,indexed_mtime_ns)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                session_id=excluded.session_id,rollout_path=excluded.rollout_path,title=excluded.title,
                project_id=excluded.project_id,archived=excluded.archived,created_at=excluded.created_at,
                updated_at=excluded.updated_at,last_turn_id=excluded.last_turn_id,
                metadata_json=excluded.metadata_json,indexed_size=excluded.indexed_size,
                indexed_mtime_ns=excluded.indexed_mtime_ns""",
                (thread_id, metadata["sessionId"], str(path), metadata["title"], metadata.get("projectId"),
                 int(metadata["archived"]), metadata["createdAt"], metadata["updatedAt"],
                 turns[-1]["turnId"] if turns else None, _json(metadata), stat.st_size, stat.st_mtime_ns))
        except sqlite3.ProgrammingError:
            raise ValueError("会话元数据字段类型无效") from None
        except sqlite3.IntegrityError:
            raise ValueError("会话 sessionId 与其他会话重复") from None
        connection.execute("DELETE FROM turns WHERE thread_id=?", (thread_id,))
        for turn in turns:
            status = turn.get("status")
            connection.execute("""INSERT INTO turns
                (thread_id,turn_id,status,first_ordinal,last_ordinal,metadata_json) VALUES(?,?,?,?,?,?)""",
                (thread_id, turn["turnId"], status if isinstance(status, str) else "error",
                 turn["firstOrdinal"], turn["lastOrdinal"], _json(self._public_turn(turn))))
        connection.execute("DELETE FROM approvals WHERE thread_id=?", (thread_id,))
        for item in self._project_items(thread_id, entries):
            if not self._valid_approval_item(item, pending_only=False):
                continue
            approval = item["approval"]
            connection.execute("""INSERT INTO approvals
                (approval_id,thread_id,item_id,turn_id,tool_name,deadline,params_digest,
                 decision,status,execution_state) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (approval["approvalId"], thread_id, item["id"], item["turnId"], item["toolName"],
                 float(approval["deadline"]), approval["paramsDigest"], approval.get("decision"),
                 item["status"], item["executionState"]))

    def _sync_thread(self, thread_id: str) -> None:
        with self._lock, self._index.transaction() as connection:
            self._index_thread(thread_id, connection)

    @staticmethod
    def _thread_metadata(row: sqlite3.Row) -> dict[str, Any]:
        """读取线程投影行；损坏时抛出内部信号，由读取方触发重建。"""
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, ValueError, RecursionError):
            raise _IndexedMetadataError(row["id"]) from None
        if not isinstance(metadata, dict):
            raise _IndexedMetadataError(row["id"])
        # 投影行必须自称与主键相同的会话 id：外部改写或半写状态可能留下没有 id、
        # 或复制自其它会话的 metadata_json。列表会把它原样交给调用方，启动恢复、
        # 搜索与队列恢复随后读 thread["id"] 抛 KeyError（-32603），一条坏行就能
        # 让内核每次启动都失败。按索引损坏处理，走既有重建路径。
        if metadata.get("id") != row["id"]:
            raise _IndexedMetadataError(row["id"])
        # 投影行还必须满足协议的字段类型：createdAt / title 是必需字符串，
        # sessionId 可选字符串，projectId 可选字符串或 null。外部改写可能留下
        # NaN 时间或对象标题——NaN 会让 JSON-RPC 帧编码失败（整次 thread/list
        # 变成 RESPONSE_INVALID），对象标题会让桌面拒绝整份会话列表。按索引损坏
        # 处理，走既有重建；_index_thread 会把这些字段归一为合法值。
        if not isinstance(metadata.get("createdAt"), str) or not isinstance(metadata.get("title"), str):
            raise _IndexedMetadataError(row["id"])
        if any(metadata.get(key) is not None and not isinstance(metadata[key], str)
               for key in ("sessionId", "projectId")):
            raise _IndexedMetadataError(row["id"])
        # 旧版本没有长度上限，历史会话头可能留着超长标识或标题。原始记录不改写，
        # 投影固定截断到同一上限并标记，使这类会话重新可读。
        project_id = metadata.get("projectId")
        if isinstance(project_id, str) and len(project_id) > MAX_PROJECT_ID_CHARS:
            metadata["projectId"] = project_id[:MAX_PROJECT_ID_CHARS]
            metadata["projectIdTruncated"] = True
        title = metadata.get("title")
        if isinstance(title, str) and len(title) > MAX_THREAD_TITLE_CHARS:
            metadata["title"] = title[:MAX_THREAD_TITLE_CHARS]
            metadata["titleTruncated"] = True
        return metadata

    @staticmethod
    def _turn_metadata(row: sqlite3.Row) -> dict[str, Any]:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, ValueError, RecursionError):
            raise _IndexedMetadataError(row["thread_id"]) from None
        if not isinstance(metadata, dict):
            raise _IndexedMetadataError(row["thread_id"])
        return metadata

    def _repair_thread_index(self, thread_id: str) -> None:
        """投影索引从会话 JSONL 派生：标记过期后按源日志重建该会话。"""
        with self._lock, self._index.transaction() as connection:
            connection.execute("UPDATE threads SET indexed_size=-1,indexed_mtime_ns=-1 WHERE id=?",
                               (thread_id,))
            self._index_thread(thread_id, connection)

    def _with_repaired_index(self, read: Callable[[], _T], *, skip: set[str] | None = None) -> _T:
        """metadata_json 损坏时逐个会话重建后重试；源日志错误原样向上。

        ``skip`` 供聚合读取（会话列表）使用：某个会话的投影与源日志同时损坏时，
        重建无法完成，按既有「按会话隔离」约定把它记入 ``unreadable_threads``
        并从这个结果集中跳过，而不是让整次列表读取——进而让内核启动的整体恢复
        流程——失败。调用方的 ``read`` 必须过滤 ``skip`` 中的会话 id；
        单会话读取不传 ``skip``，仍以可读 ValueError 报出具体损坏行。
        """
        repaired: set[str] = set()
        while True:
            try:
                return read()
            except _IndexedMetadataError as exc:
                if exc.thread_id in repaired:
                    # 调用方没有过滤 skip 说明是内部实现错误；给可读错误而非死循环。
                    raise ValueError("会话索引已损坏，请重新打开应用后重试") from None
                repaired.add(exc.thread_id)
                try:
                    self._repair_thread_index(exc.thread_id)
                except (OSError, ValueError):
                    if skip is None:
                        raise
                    skip.add(exc.thread_id)
                    self.unreadable_threads.add(exc.thread_id)


    def _expire_outdated_projections(self) -> None:
        """投影内容版本变化后，让含位置记录的会话失效一次，由随后的刷新重建。

        只有切换过位置的会话的投影内容随版本变化，其余会话不重建：启动耗时不随全部
        日志的解析量增长。失效与版本记录在同一事务提交；重建中途退出时这些行仍是失效
        状态，下次启动继续。读不出的日志同样标记失效，不当作已处理，也不阻断启动。
        """
        with self._lock, self._index.transaction() as connection:
            row = connection.execute(
                "SELECT value FROM checkpoints WHERE name='threadProjection'").fetchone()
            if row is not None and row["value"] == THREAD_PROJECTION_VERSION:
                return
            for indexed in connection.execute("SELECT id FROM threads WHERE indexed_size>=0").fetchall():
                thread_id = indexed["id"]
                if not isinstance(thread_id, str) or not _THREAD_ID.fullmatch(thread_id):
                    continue
                try:
                    outdated = _log_mentions_leaf(self.root / f"{thread_id}.jsonl")
                except FileNotFoundError:
                    continue
                except OSError:
                    outdated = True
                if outdated:
                    connection.execute(
                        "UPDATE threads SET indexed_size=-1,indexed_mtime_ns=-1 WHERE id=?", (thread_id,))
            connection.execute(
                "INSERT INTO checkpoints(name,value) VALUES('threadProjection',?) "
                "ON CONFLICT(name) DO UPDATE SET value=excluded.value", (THREAD_PROJECTION_VERSION,))

    def _refresh_threads(self) -> None:
        with self._lock, self._index.transaction() as connection:
            known: set[str] = set()
            for path in sorted(self.root.glob("*.jsonl")):
                if not _THREAD_ID.fullmatch(path.stem):
                    continue
                known.add(path.stem)
                indexed = connection.execute("SELECT 1 FROM threads WHERE id=?", (path.stem,)).fetchone()
                try:
                    self._index_thread(path.stem, connection)
                except (OSError, ValueError):
                    if indexed is None:
                        # Leave an unindexed unreadable log untouched so one damaged
                        # file cannot stop recovery of every other session. A later
                        # start indexes it once the file is readable again.
                        self.unreadable_threads.add(path.stem)
                        continue
                    # Preserve the last listing projection; session reads report the damaged line.
                    continue
                self.unreadable_threads.discard(path.stem)
            # A deleted or renamed damaged log must not linger in the diagnostic set.
            self.unreadable_threads.intersection_update(known)
            for row in connection.execute("SELECT id,rollout_path FROM threads").fetchall():
                if row["id"] in known:
                    continue
                rollout_path = row["rollout_path"]
                # 投影列可能被外部改写为 BLOB 或整数；这类行没有可核对的源日志，
                # 与已删除日志的陈旧投影一样清理，不能让 Path() 的 TypeError 阻断启动。
                if not isinstance(rollout_path, str) or Path(rollout_path).parent == self.root:
                    connection.execute("DELETE FROM threads WHERE id=?", (row["id"],))

    def get_thread(self, thread_id: str) -> dict:
        self._sync_thread(thread_id)

        def read() -> dict:
            with self._index.connection() as connection:
                row = connection.execute(
                    "SELECT id,metadata_json FROM threads WHERE id=?", (thread_id,)).fetchone()
            if row is None:
                raise ValueError("会话不存在")
            return self._thread_metadata(row)

        return self._with_repaired_index(read)

    @staticmethod
    def _validate_changes(changes: dict) -> dict:
        changes = dict(changes)
        if "project_id" in changes:
            if "projectId" in changes:
                raise ValueError("projectId 不可重复提供")
            changes["projectId"] = changes.pop("project_id")
        if set(changes) - {"title", "projectId", "provider", "model", "cwd", "toolPolicy", "reasoningEffort"}:
            raise ValueError("会话元数据包含不支持的更新字段")
        for key, value in changes.items():
            if key == "toolPolicy" and (not isinstance(value, str) or value not in {"readOnly", "approval"}):
                raise ValueError("toolPolicy 必须是 readOnly 或 approval")
            if key == "reasoningEffort" and value is not None and value not in REASONING_EFFORTS:
                raise ValueError("reasoningEffort 档位无效")
            if key == "title" and (not isinstance(value, str) or len(value) > MAX_THREAD_TITLE_CHARS):
                raise ValueError(f"title 必须是最多 {MAX_THREAD_TITLE_CHARS} 字符的字符串")
            if key == "provider" and (not isinstance(value, str) or not value
                    or len(value) > 64 or any(char.isspace() for char in value)):
                raise ValueError("provider 必须是非空 provider id")
            if key in {"projectId", "cwd"} and value is not None and not isinstance(value, str):
                raise ValueError(f"{key} 必须是字符串或 null")
            if key == "projectId" and isinstance(value, str) and len(value) > MAX_PROJECT_ID_CHARS:
                raise ValueError(f"projectId 必须是最多 {MAX_PROJECT_ID_CHARS} 字符的字符串")
            if key == "model" and value is not None and not isinstance(value, (str, dict)):
                raise ValueError("model 必须是字符串、对象或 null")
        _json(changes)
        return changes

    def update_thread(self, thread_id: str, **changes: Any) -> dict:
        changes = self._validate_changes(changes)
        if changes:
            self.append(thread_id, Entry(type="thread_info", parent_id=self.last_entry_id(thread_id), payload=changes))
        return self.get_thread(thread_id)

    def archive_thread(self, thread_id: str) -> dict:
        with self._lock:
            thread = self.get_thread(thread_id)
            if not thread["archived"]:
                entries = self.read_entries(thread_id)
                for item in self._project_items(thread_id, entries):
                    approval = item.get("approval")
                    # 与 decide_approval / 索引重建 / 启动恢复同一校验：畸形审批没有
                    # 可持久化的裁决语义，_append_approval_decision 还会在缺 toolName
                    # 时抛 KeyError（-32603）。归档本身必须完成，坏记录按「不需要结算」
                    # 跳过，既不中断归档也不写下伪 expired 裁决。
                    if (item.get("executionState") == "pending_approval"
                            and isinstance(approval, dict) and not approval.get("decision")
                            and self._valid_approval_item(item, pending_only=False)):
                        self._append_approval_decision(thread_id, item, "expired", live_owner=False)
                self.append(thread_id, Entry(type="thread_info", parent_id=self.last_entry_id(thread_id),
                                             payload={"archived": True}))
            return self.get_thread(thread_id)

    def unarchive_thread(self, thread_id: str) -> dict:
        if self.get_thread(thread_id)["archived"]:
            self.append(thread_id, Entry(type="thread_info", parent_id=self.last_entry_id(thread_id), payload={"archived": False}))
        return self.get_thread(thread_id)

    archive = archive_thread
    unarchive = unarchive_thread

    def delete_thread(self, thread_id: str, *, _on_committed: Callable[[], None] | None = None) -> dict:
        """Permanently remove a rollout and its private event/attachment data."""
        if _on_committed is not None and not callable(_on_committed):
            raise ValueError("会话删除提交回调必须可调用")
        with self._lock:
            intent_path = self._delete_intent_path(thread_id)
            if intent_path.exists():
                intent = self._read_delete_intent(intent_path)
            else:
                prior = None
                with self._index.transaction() as connection:
                    try:
                        self.require_thread(thread_id)
                    except ValueError:
                        if self.path_for(thread_id).exists():
                            raise
                        prior = self._previous_deletion_event(connection, thread_id)
                        if prior is None:
                            raise ThreadNotFound("会话不存在") from None
                    if prior is None:
                        entries = self.read_entries(thread_id)
                        intent = self._write_delete_intent(thread_id, entries)
                        connection.execute("UPDATE checkpoints SET value='' WHERE name='events'")
                if prior is not None:
                    if _on_committed is not None:
                        _on_committed()
                    return prior
            return self._finish_deletion(intent, _on_committed=_on_committed)

    @staticmethod
    def _previous_deletion_event(connection: sqlite3.Connection, thread_id: str) -> dict | None:
        for row in connection.execute("SELECT method,params_json FROM events WHERE method='thread/deleted'"):
            try:
                params = json.loads(row["params_json"])
            except (TypeError, ValueError, RecursionError):
                # 无法解析的索引行无法参与匹配；事件索引可从源日志重建，
                # 下一次同步或回放会自愈，不能阻断删除。
                continue
            if not isinstance(params, dict):
                continue
            if params.get("deletedThreadId") == thread_id:
                return {"method": row["method"], "params": params}
        return None

    def _finish_deletion(self, intent: dict[str, Any], *,
                         _on_committed: Callable[[], None] | None = None) -> dict:
        thread_id = intent["threadId"]
        with self._lock, self._index.transaction() as connection:
            connection.execute("PRAGMA secure_delete=ON")
            self._index_events(connection)
            event = self._rewrite_events_for_deletion(connection, intent)
            self._remove_thread_files(thread_id)
            # 删除后缓存不能再持有整份条目投影（大会话可能占用大量内存）。
            self._entries_cache.pop(thread_id, None)
            self._purge_unreferenced_attachments(intent["attachmentDigests"])
            self._purge_repair_backups(thread_id)
            connection.execute("DELETE FROM events")
            connection.execute("DELETE FROM checkpoints WHERE name='events'")
            self._index_events(connection)
            connection.execute("DELETE FROM threads WHERE id=?", (thread_id,))
        if _on_committed is not None:
            _on_committed()
        self._checkpoint_and_truncate_wal()
        intent_path = self._delete_intent_path(thread_id)
        if intent_path.exists():
            restrict_private_file(intent_path)
            intent_path.unlink()
            _fsync_directory(self.root)
        return event

    def _remove_private_temporaries(self, paths: list[Path], target: Path) -> None:
        current_uid = getattr(os, "getuid", lambda: -1)()
        for path in paths:
            try:
                original = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(original.st_mode) or original.st_uid != current_uid:
                raise ValueError("会话删除遇到非私有普通文件，清理已暂停")
            if original.st_nlink == 2:
                try:
                    target_stat = target.lstat()
                except FileNotFoundError:
                    target_stat = None
                if (target_stat is None or not stat.S_ISREG(target_stat.st_mode)
                        or target_stat.st_uid != current_uid or target_stat.st_nlink != 2
                        or (original.st_dev, original.st_ino) != (target_stat.st_dev, target_stat.st_ino)):
                    raise ValueError("会话删除遇到无法确认的硬链接临时文件，清理已暂停")
            elif original.st_nlink != 1:
                raise ValueError("会话删除遇到非私有普通文件，清理已暂停")
            restrict_private_file(path)
            path.unlink()
        if paths:
            _fsync_directory(paths[0].parent)

    def _remove_thread_files(self, thread_id: str) -> None:
        session_path = self.path_for(thread_id)
        self._remove_private_temporaries(list(self.root.glob(f".{thread_id}.jsonl.*.tmp")), session_path)
        self._remove_private_temporaries(list(self.root.glob(f".delete-{thread_id}.*.tmp")),
                                         self._delete_intent_path(thread_id))
        self._remove_private_temporaries(
            list(self.root.parent.glob(f".events.jsonl.delete-{thread_id}.*.tmp")), self.events_path)

        try:
            original = session_path.lstat()
        except FileNotFoundError:
            return
        current_uid = getattr(os, "getuid", lambda: -1)()
        if (not stat.S_ISREG(original.st_mode) or original.st_nlink != 1 or original.st_uid != current_uid):
            raise ValueError("会话删除遇到非私有普通文件，清理已暂停")
        restrict_private_file(session_path)
        session_path.unlink()
        _fsync_directory(self.root)

    @staticmethod
    def _event_high_water(connection: sqlite3.Connection) -> int:
        maximum = int(connection.execute("SELECT COALESCE(MAX(cursor),0) FROM events").fetchone()[0])
        try:
            sequence = connection.execute("SELECT seq FROM sqlite_sequence WHERE name='events'").fetchone()
        except sqlite3.OperationalError:
            sequence = None
        return max(maximum, int(sequence[0]) if sequence else 0)

    def _rewrite_events_for_deletion(self, connection: sqlite3.Connection,
                                     intent: dict[str, Any]) -> dict:
        thread_id = intent["threadId"]
        target = self.events_path
        try:
            original = target.lstat()
        except FileNotFoundError:
            original = None
        source_signature = None
        source_handle = None
        if original is not None:
            if not stat.S_ISREG(original.st_mode) or original.st_nlink != 1:
                raise ValueError("事件日志不是普通私有文件，清理已暂停")
            restrict_private_file(target)
            descriptor = open_private_file(target, os.O_RDONLY)
            source_handle = os.fdopen(descriptor, "rb")
            opened = os.fstat(descriptor)
            source_signature = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns,
                                opened.st_ctime_ns, opened.st_mode, opened.st_uid, opened.st_gid,
                                opened.st_nlink)
            visible = target.lstat()
            if (visible.st_dev, visible.st_ino) != (opened.st_dev, opened.st_ino):
                source_handle.close()
                raise ValueError("事件日志在删除期间变化，清理已暂停")

        temporary = target.with_name(f".events.jsonl.delete-{thread_id}.{uuid.uuid4().hex}.tmp")
        descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)
        event: dict | None = None
        event_count = 0
        maximum_cursor = self._event_high_water(connection)
        seen_cursors: set[int] = set()
        seen_event_ids: set[str] = set()
        last_byte = b"\n"
        try:
            with os.fdopen(descriptor, "wb") as output:
                if source_handle is not None:
                    for line_number, raw_line in enumerate(_iter_bounded_raw_lines_from_handle(
                            source_handle, maximum=MAX_EVENT_LINE_BYTES, label="事件日志"), start=1):
                        if not raw_line.strip():
                            output.write(raw_line + b"\n")
                            last_byte = b"\n"
                            continue
                        try:
                            record = _decode_jsonl_object(
                                raw_line, label="事件日志", line_number=line_number)
                        except ValueError as exc:
                            raise ValueError(f"事件日志损坏，无法安全删除会话：{exc}") from None
                        if not isinstance(record, dict):
                            raise ValueError("事件日志格式无效，无法安全删除会话")
                        method = record.get("method")
                        timestamp = record.get("timestamp")
                        if (record.get("type") != "event"
                                or not isinstance(timestamp, str)
                                or not isinstance(method, str) or not method or len(method) > 256
                                or any(ord(char) < 32 for char in method)
                                or not isinstance(record.get("params"), dict)):
                            raise ValueError("事件日志格式无效，无法安全删除会话")
                        params = record["params"]
                        cursor = _event_cursor(params.get("eventCursor"))
                        event_id = params.get("eventId")
                        if cursor < 1 or not isinstance(event_id, str) or not _EVENT_ID.fullmatch(event_id):
                            raise ValueError("事件日志游标无效，无法安全删除会话")
                        if cursor in seen_cursors:
                            raise ValueError("事件日志存在重复游标，无法安全删除会话")
                        if event_id in seen_event_ids:
                            raise ValueError("事件日志存在重复事件 ID，无法安全删除会话")
                        seen_cursors.add(cursor)
                        seen_event_ids.add(event_id)
                        event_thread_id = params.get("threadId")
                        if event_thread_id is not None:
                            if not isinstance(event_thread_id, str):
                                raise ValueError("事件日志会话 ID 无效，无法安全删除会话")
                            try:
                                self.path_for(event_thread_id)
                            except ValueError:
                                raise ValueError("事件日志会话 ID 无效，无法安全删除会话") from None
                        maximum_cursor = max(maximum_cursor, cursor)
                        if event_id == intent["eventId"]:
                            event_count += 1
                            if (record["method"] != "thread/deleted"
                                    or params.get("deletedThreadId") != thread_id
                                    or "threadId" in params):
                                raise ValueError("会话删除事件与恢复标记冲突")
                            event = {"method": record["method"], "params": params}
                            output.write(raw_line + b"\n")
                            last_byte = b"\n"
                        elif params.get("threadId") != thread_id:
                            output.write(raw_line + b"\n")
                            last_byte = b"\n"
                if event_count > 1:
                    raise ValueError("事件日志含重复的会话删除事件")
                if event is None:
                    if maximum_cursor >= 2**63 - 1:
                        raise ValueError("事件游标已耗尽，无法完成会话删除")
                    params = {"deletedThreadId": thread_id, "eventId": intent["eventId"],
                              "eventCursor": str(maximum_cursor + 1)}
                    event = {"method": "thread/deleted", "params": params}
                    if last_byte != b"\n":
                        output.write(b"\n")
                    output.write((_json({"type": "event", "timestamp": _now(), **event}) + "\n").encode("utf-8"))
                output.flush()
                os.fsync(output.fileno())
            if source_handle is not None:
                opened = os.fstat(source_handle.fileno())
                current_signature = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns,
                                     opened.st_ctime_ns, opened.st_mode, opened.st_uid, opened.st_gid,
                                     opened.st_nlink)
                if current_signature != source_signature:
                    raise ValueError("事件日志在删除期间变化，清理已暂停")
                visible = target.lstat()
                if (visible.st_dev, visible.st_ino) != source_signature[:2]:
                    raise ValueError("事件日志在删除期间变化，清理已暂停")
            if original is None:
                os.link(temporary, target)
                temporary.unlink()
            else:
                os.replace(temporary, target)
            _fsync_directory(target.parent)
        finally:
            if source_handle is not None:
                source_handle.close()
            temporary.unlink(missing_ok=True)
        if event is None:
            raise RuntimeError("删除事件未能生成")
        return event

    def _purge_unreferenced_attachments(self, digests: list[str]) -> None:
        # 候选直接拼接为附件路径：在读取目录与扫描会话前收敛为摘要格式，
        # 避免内部方法被误用时指向附件根之外的状态文件。
        if not isinstance(digests, (list, tuple)) or any(
                not isinstance(digest, str) or not _ATTACHMENT_DIGEST.fullmatch(digest)
                for digest in digests):
            raise ValueError("附件清理候选摘要格式无效")
        candidates = set(digests)
        if not candidates:
            return
        try:
            directory_stat = self.attachments_root.lstat()
        except FileNotFoundError:
            return
        current_uid = getattr(os, "getuid", lambda: -1)()
        if not stat.S_ISDIR(directory_stat.st_mode) or directory_stat.st_uid != current_uid:
            raise ValueError("附件目录不可信，清理已暂停")
        referenced: set[str] = set()
        for session_path in self.root.glob("*.jsonl"):
            if session_path.stem in self._pending_deletion_ids():
                continue
            original = session_path.lstat()
            if not stat.S_ISREG(original.st_mode) or original.st_uid != current_uid or original.st_nlink != 1:
                raise ValueError("会话文件不可信，无法确认共享附件引用")
            restrict_private_file(session_path)
            try:
                self.require_thread(session_path.stem)
                for line_number, line in enumerate(_iter_bounded_lines(
                        session_path, maximum=MAX_SESSION_LINE_BYTES,
                        label="会话日志", universal_newlines=True), start=1):
                    if not line.strip():
                        continue
                    entry = _decode_session_record(line, line_number=line_number)
                    if (entry is not None and entry.get("type") == "attachment"
                            and isinstance(entry.get("payload"), dict)):
                        digest = entry["payload"].get("digest")
                        if isinstance(digest, str) and _ATTACHMENT_DIGEST.fullmatch(digest):
                            referenced.add(digest)
            except ValueError:
                raise ValueError("会话记录损坏，无法确认共享附件引用") from None
        changed = False
        for digest in candidates - referenced:
            path = self.attachments_root / digest
            try:
                original = path.lstat()
            except FileNotFoundError:
                continue
            if (not stat.S_ISREG(original.st_mode) or original.st_uid != current_uid
                    or original.st_nlink != 1):
                raise ValueError("附件文件不可信，清理已暂停")
            restrict_private_file(path)
            path.unlink()
            changed = True
        if changed:
            _fsync_directory(self.attachments_root)

    def _purge_repair_backups(self, thread_id: str) -> None:
        repair_root = self.root.parent / "repairs"
        try:
            root_stat = repair_root.lstat()
        except FileNotFoundError:
            return
        current_uid = getattr(os, "getuid", lambda: -1)()
        if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != current_uid:
            raise ValueError("修复备份目录不可信，清理已暂停")
        for database_path in sorted(repair_root.rglob("state.sqlite3")):
            original = database_path.lstat()
            if (not stat.S_ISREG(original.st_mode) or original.st_uid != current_uid
                    or original.st_nlink != 1):
                raise ValueError("修复备份不是私有普通文件，清理已暂停")
            restrict_private_file(database_path)
            backup = sqlite3.connect(database_path, timeout=10, isolation_level=None)
            try:
                backup.execute("PRAGMA busy_timeout=10000")
                backup.execute("PRAGMA foreign_keys=ON")
                backup.execute("PRAGMA synchronous=FULL")
                backup.execute("PRAGMA secure_delete=ON")
                version = int(backup.execute("PRAGMA user_version").fetchone()[0])
                if version > SCHEMA_VERSION:
                    raise ValueError("修复备份包含较新索引，无法安全删除会话")
                tables = {row[0] for row in backup.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                backup.execute("BEGIN IMMEDIATE")
                try:
                    if "events" in tables:
                        backup.execute("DELETE FROM events WHERE thread_id=?", (thread_id,))
                    if "turns" in tables:
                        backup.execute("DELETE FROM turns WHERE thread_id=?", (thread_id,))
                    if "threads" in tables:
                        backup.execute("DELETE FROM threads WHERE id=?", (thread_id,))
                    backup.commit()
                except BaseException:
                    backup.rollback()
                    raise
                backup.execute("VACUUM")
                result = backup.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if result and result[0] != 0:
                    raise OSError("修复备份 WAL 尚未收敛")
            finally:
                backup.close()
            backup_directory = database_path.parent
            for sidecar in (database_path.with_name(database_path.name + "-wal"),
                            database_path.with_name(database_path.name + "-shm")):
                try:
                    sidecar_stat = sidecar.lstat()
                except FileNotFoundError:
                    continue
                if (not stat.S_ISREG(sidecar_stat.st_mode) or sidecar_stat.st_uid != current_uid
                        or sidecar_stat.st_nlink != 1):
                    raise ValueError("修复备份 sidecar 不可信，清理已暂停")
                restrict_private_file(sidecar)
                sidecar.unlink()
            _fsync_directory(backup_directory)
            manifest_path = backup_directory / "manifest.json"
            if manifest_path.exists():
                restrict_private_file(manifest_path)
                try:
                    manifest = json.loads(_read_bounded_file(
                        manifest_path, maximum=MAX_REPAIR_MANIFEST_BYTES,
                        label="修复备份清单").decode("utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
                    raise ValueError("修复备份清单损坏，清理已暂停") from None
                if not isinstance(manifest, list) or any(not isinstance(item, dict) for item in manifest):
                    raise ValueError("修复备份清单格式无效，清理已暂停")
                updated = []
                for item in manifest:
                    if item.get("name") in {"state.sqlite3-wal", "state.sqlite3-shm"}:
                        continue
                    if item.get("name") == "state.sqlite3":
                        item = {**item, "bytes": database_path.stat().st_size,
                                "sha256": _sha256_file(database_path)}
                    updated.append(item)
                temporary = manifest_path.with_name(f".manifest.{uuid.uuid4().hex}.tmp")
                descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)
                try:
                    with os.fdopen(descriptor, "wb") as output:
                        output.write((json.dumps(updated, indent=2) + "\n").encode("utf-8"))
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temporary, manifest_path)
                finally:
                    temporary.unlink(missing_ok=True)
                _fsync_directory(backup_directory)

    def _checkpoint_and_truncate_wal(self) -> None:
        with self._index.connection() as connection:
            result = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if result and result[0] != 0:
            raise OSError("会话索引 WAL 尚未收敛；删除会在下次启动时继续")

    def list_threads(self, *, include_archived: bool = False) -> list[dict]:
        with self._lock:
            self._refresh_threads()
            pending = self._pending_deletion_ids()
            # 投影与源日志同时损坏的会话无法重建：列表按会话隔离跳过，单会话读取
            # 仍会报告具体损坏行。让列表整体失败会连带阻断内核启动的整体恢复。
            skip: set[str] = set()

            def read() -> list[dict]:
                with self._index.connection() as connection:
                    rows = connection.execute("SELECT id,metadata_json FROM threads" +
                        ("" if include_archived else " WHERE archived=0")
                        + " ORDER BY updated_at DESC,id DESC").fetchall()
                threads = []
                for row in rows:
                    if row["id"] in skip:
                        continue
                    metadata = self._thread_metadata(row)
                    if row["id"] not in pending:
                        threads.append(metadata)
                return threads

            return self._with_repaired_index(read, skip=skip)

    def unreadable_thread_ids(self) -> list[str]:
        """本进程刷新索引时跳过的会话 id 快照，按字典序排列供运行诊断读取。"""
        with self._lock:
            self._refresh_threads()
            return sorted(self.unreadable_threads)

    def list_threads_page(self, *, cursor: str | None = None, limit: int = 50,
                          archived: bool = False, project_id: str | None = None) -> dict:
        _limit(limit)
        if type(archived) is not bool or (project_id is not None and not isinstance(project_id, str)):
            raise ValueError("会话筛选参数无效")
        if project_id is not None and len(project_id) > MAX_PROJECT_ID_CHARS:
            raise ValueError(f"projectId 必须是最多 {MAX_PROJECT_ID_CHARS} 字符的字符串")
        scope = {"archived": archived, "projectId": project_id}
        key = _read_page_cursor(cursor, "threads", scope)
        parameters: list[Any] = [int(archived)]
        query = "SELECT * FROM threads WHERE archived=?"
        if project_id is not None:
            query += " AND project_id=?"
            parameters.append(project_id)
        if key is not None:
            if len(key) != 2 or not isinstance(key[0], str) or not isinstance(key[1], str) or not _THREAD_ID.fullmatch(key[1]):
                raise ValueError("会话分页游标无效")
            # SQL 侧是字符串比较，游标时间必须与索引列同样由 isoformat 写出：
            # 3.11+ 的 fromisoformat 能接受 ``Z`` 结尾等非规范写法，直接放行会让
            # 同一时刻的 ``Z`` 游标把 ``+00:00`` 行全部挡在窗口外，分页重复或跳行；
            # 3.10 则直接拒绝。解析后再序列化回原值，使各版本对同一输入结论一致。
            try:
                if datetime.fromisoformat(key[0]).isoformat() != key[0]:
                    raise ValueError
            except ValueError:
                raise ValueError("会话分页游标无效") from None
            query += " AND (updated_at<? OR (updated_at=? AND id<?))"
            parameters.extend([key[0], key[0], key[1]])
        with self._lock:
            self._refresh_threads()
            pending = sorted(self._pending_deletion_ids())
            if pending:
                query += " AND id NOT IN (" + ",".join("?" for _ in pending) + ")"
                parameters.extend(pending)
            query += " ORDER BY updated_at DESC,id DESC"
            skip: set[str] = set()

            def read() -> dict:
                # 损坏会话必须从候选窗口之外继续取行：若先取 limit+1 再过滤，
                # 损坏行会吃掉 lookahead，后面的健康会话被误判为没有下一页。
                page: list[Any] = []
                has_more = False
                with self._index.connection() as connection:
                    cursor = connection.execute(query, parameters)
                    while True:
                        row = cursor.fetchone()
                        if row is None:
                            break
                        if row["id"] in skip:
                            continue
                        # 投影列不保证仍是建表时的类型：SQLite 的列亲和性不会阻止外部把
                        # updated_at 改写成 BLOB。游标的 json.dumps 会抛 TypeError，绕过
                        # 只捕获 _IndexedMetadataError 的重建重试，把 -32603 送给调用方。
                        if not isinstance(row["updated_at"], str):
                            raise _IndexedMetadataError(row["id"])
                        if len(page) == limit:
                            has_more = True
                            break
                        page.append(row)
                next_cursor = (_page_cursor("threads", scope, [page[-1]["updated_at"], page[-1]["id"]])
                               if page and has_more else None)
                return {"threads": [self._thread_metadata(row) for row in page],
                        "nextCursor": next_cursor}

            return self._with_repaired_index(read, skip=skip)

    @staticmethod
    def _search_normalized(value: str) -> tuple[str, array.array | None, array.array | None]:
        """按组合簇 NFKC + casefold 归一化，返回文本与每个字符对应的原文起止索引。

        单码点簇归一化后仍是单字符时映射恒等，返回 `None` 让调用方直接用下标，
        常见正文因此不必为每个码点保留索引。需要映射时用 `array('I')` 紧凑存放：
        文本上限为 `_SEARCH_THREAD_BYTES`，索引远小于 2**32；逐码点的 Python 整数
        列表会让长文本的搜索内存放大到文本大小的上百倍。纯 ASCII 不受 NFKC /
        casefold 影响，直接小写返回；其余文本只在含补表码点时走
        `search_unicode.search_normalize`，普通文本不承担补表开销。
        """
        if value.isascii():
            return value.lower(), None, None
        normalize = search_normalize if needs_extra(value) else None
        parts = io.StringIO()
        identity = True
        for index, end, part in _search_clusters(value, normalize):
            if not part:
                continue
            parts.write(part)
            if end - index != 1 or len(part) != 1:
                identity = False
        normalized = parts.getvalue()
        if identity:
            return normalized, None, None
        starts = array.array("I")
        ends = array.array("I")
        for index, end, part in _search_clusters(value, normalize):
            starts.extend([index] * len(part))
            ends.extend([end] * len(part))
        return normalized, starts, ends

    @staticmethod
    def _search_snippet(text: str, start: int, end: int) -> str:
        """截取命中片段：完整保留命中区间，空白折叠只作用于两侧上下文。

        桌面端在片段中按内核归一化重新查找查询词并高亮，片段必须完整包含
        `text[start:end]`。整段折叠空白会把查询中的连续空白抹平，尾部硬截断
        会切掉长查询的命中尾巴，两者都会让结果行无法高亮。
        """
        left, right = max(0, start - 40), min(len(text), end + 40)
        before = re.sub(r"\s+", " ", text[left:start]).lstrip()
        hit = text[start:end]
        after = re.sub(r"\s+", " ", text[end:right]).rstrip()
        room = _SEARCH_SNIPPET_BYTES - len(hit)
        trimmed_before = trimmed_after = False
        if len(before) + len(after) > room:
            # 命中本身已超出预算时 room 为负：只保留命中词，仍完整可高亮。
            keep_left = min(len(before), max(0, room) // 2)
            keep_right = min(len(after), max(0, room) - keep_left)
            keep_left = min(len(before), max(0, room) - keep_right)
            trimmed_before, trimmed_after = keep_left < len(before), keep_right < len(after)
            if trimmed_before:
                before = before[len(before) - keep_left:] if keep_left else ""
            if trimmed_after:
                after = after[:keep_right]
        return (("…" if left or trimmed_before else "") + f"{before}{hit}{after}".strip()
                + ("…" if right < len(text) or trimmed_after else ""))

    @staticmethod
    def _search_tool_text(item: dict) -> str:
        """把工具调用压成可检索文本：工具名 + 来源编号 + 有界参数 + 结果摘要；无工具名返回空串。"""
        name = item.get("toolName")
        if not isinstance(name, str) or not name.strip():
            return ""
        parts = [name.strip()]
        # 来源编号是工具卡默认可见的标识；紧随工具名，长参数与摘要不会把它挤出文本上限。
        source = item.get("source")
        reference = source.get("ref") if isinstance(source, dict) else None
        if isinstance(reference, str) and reference.strip():
            parts.append(reference.strip())
        arguments = item.get("toolArguments")
        if isinstance(arguments, dict):
            try:
                rendered = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
            except RecursionError:
                rendered = ""
            except (TypeError, ValueError):
                rendered = ""
            if rendered and len(rendered) <= _SEARCH_TOOL_ARGS:
                parts.append(rendered)
        summary = item.get("resultSummary")
        if isinstance(summary, str) and summary:
            parts.append(summary)
        return "\n".join(parts)[:_SEARCH_TOOL_TEXT]

    def search_messages(self, query: str, *, limit: int = 30, include_archived: bool = False) -> dict:
        """在会话的用户 / 助手消息与工具调用中做有界全文搜索；默认不含已归档，跳过损坏或过大的会话。

        达到展示上限后仍继续扫描（不再收集结果），确认真有下一条命中才报告截断；恰好
        等于 ``limit`` 或单会话上限的完整结果保持 ``truncated = False``。会话数 / 文本
        预算耗尽、跳过超大会话、会话已列出但无法读取等结构性截断仍为真。
        """
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise ValueError("query 必须是非空字符串（最多 200 字符）")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("limit 必须是 1–50 的整数")
        if type(include_archived) is not bool:
            raise ValueError("includeArchived 必须是布尔值")
        needle, _, _ = self._search_normalized(query.strip())
        if not needle:
            return {"query": query.strip(), "matches": [], "truncated": False}
        matches: list[dict] = []
        truncated = False
        more_matches = False
        scanned_threads = scanned_chars = 0
        for thread in self.list_threads(include_archived=include_archived):
            if scanned_threads >= _SEARCH_THREADS or scanned_chars >= _SEARCH_TEXT_BUDGET:
                truncated = True
                break
            try:
                if self.path_for(thread["id"]).stat().st_size > _SEARCH_THREAD_BYTES:
                    truncated = True
                    continue
                entries = self.read_entries(thread["id"])
                items = self._project_items(thread["id"], entries)
                # 会话区按当前分支视图展示，搜索却覆盖完整日志：切换过位置的会话额外
                # 标明命中是否在当前位置的分支上，客户端据此提示「其他分支」。
                # 投影失败（如条目编号重复）时省略该字段，搜索结果照常返回。
                branch_item_ids: set[str] | None = None
                if any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):
                    try:
                        branch_item_ids = {str(item.get("id") or "")
                                           for item in self._project_items(thread["id"],
                                                                           self._active_entries(entries))}
                    except ValueError:
                        branch_item_ids = None
            except (OSError, ValueError):
                # 会话已被列出但无法读取：其中可能包含命中，结果必须标注不完整。
                truncated = True
                continue
            scanned_threads += 1
            per_thread = 0
            for item in items:
                if scanned_chars >= _SEARCH_TEXT_BUDGET:
                    # 预算按消息粒度生效：单个大会话里的长消息不能越过上限继续扫描。
                    truncated = True
                    break
                kind = item.get("kind")
                if kind == "toolCall":
                    text, role = self._search_tool_text(item), "tool"
                    if not text:
                        continue
                elif kind in ("userMessage", "agentMessage") and isinstance(item.get("text"), str) and item["text"]:
                    text, role = item["text"], "user" if kind == "userMessage" else "agent"
                else:
                    continue
                remaining = _SEARCH_TEXT_BUDGET - scanned_chars
                if len(text) > remaining:
                    # 搜索是有界尽力而为：单条超长文本按剩余预算截断，不整条归一化。
                    text = text[:remaining]
                    truncated = True
                scanned_chars += len(text)
                normalized, starts, ends = self._search_normalized(text)
                index = normalized.find(needle)
                if index < 0:
                    continue
                if len(matches) >= limit or per_thread >= _SEARCH_PER_THREAD:
                    # 已到展示上限：继续扫描只为确认是否还有未返回的命中，找到一条即停。
                    truncated = True
                    more_matches = True
                    break
                if starts is None:
                    start, end = index, index + len(needle)
                else:
                    start = starts[index]
                    end = ends[index + len(needle) - 1]
                title = thread.get("title")
                item_id = str(item.get("id") or "")
                match = {
                    "threadId": thread["id"],
                    "threadTitle": title if isinstance(title, str) else "",
                    "itemId": item_id,
                    "role": role,
                    "snippet": self._search_snippet(text, start, end),
                }
                if branch_item_ids is not None:
                    match["onBranch"] = item_id in branch_item_ids
                matches.append(match)
                per_thread += 1
            if more_matches or scanned_chars >= _SEARCH_TEXT_BUDGET:
                truncated = True
                break
        return {"query": query.strip(), "matches": matches[:_SEARCH_MATCHES], "truncated": truncated}

    def record_turn(self, thread_id: str, turn_id: str, status: str, **fields: Any) -> None:
        _identifier(turn_id, "turnId")
        if not isinstance(status, str) or status not in _TERMINAL | {"running"}:
            raise ValueError("回合状态无效")
        if set(fields) & {"turnId", "status", "threadId", "firstOrdinal", "lastOrdinal", "boundaryOrdinal"}:
            raise ValueError("回合身份与状态不可重复提供")
        self.append(thread_id, Entry(type="turn", parent_id=self.last_entry_id(thread_id),
                    payload={**fields, "turnId": turn_id, "status": status}))

    def record_task_phase(self, thread_id: str, task_id: str, phase: str, status: str, *,
                          attempt: int = 1, restart_limit: int = 0,
                          recovery_reason: str | None = None,
                          resume_policy: str | None = None) -> None:
        """Persist a bounded turn phase checkpoint without replaying its side effects.

        A phase is an observation of local ownership, not permission to retry a
        provider or tool operation.  Recovery may therefore close a running
        phase as interrupted/manual-review while preserving the append-only
        transcript and the existing external-effect fence.
        """
        _identifier(task_id, "taskId")
        if not isinstance(phase, str) or phase not in _TASK_PHASES:
            raise ValueError("任务阶段无效")
        if not isinstance(status, str) or status not in _TERMINAL | {"running"}:
            raise ValueError("任务阶段状态无效")
        if type(attempt) is not int or not 1 <= attempt <= 1_000:
            raise ValueError("任务阶段 attempt 必须是 1 到 1000 之间的整数")
        if type(restart_limit) is not int or not 0 <= restart_limit <= 32:
            raise ValueError("任务阶段 restartLimit 必须是 0 到 32 之间的整数")
        for name, value in (("recoveryReason", recovery_reason), ("resumePolicy", resume_policy)):
            if value is not None and (not isinstance(value, str) or not value or len(value) > 256):
                raise ValueError(f"{name} 格式无效")
        if recovery_reason not in {None, "processExit", "terminalStateRecovered"}:
            raise ValueError("recoveryReason 无效")
        if resume_policy not in {None, "manual", "closed"}:
            raise ValueError("resumePolicy 无效")
        payload: dict[str, Any] = {"taskId": task_id, "ownerKind": "turn", "phase": phase,
                                   "status": status, "attempt": attempt,
                                   "restartLimit": restart_limit}
        if recovery_reason is not None:
            payload["recoveryReason"] = recovery_reason
        if resume_policy is not None:
            payload["resumePolicy"] = resume_policy
        self.append(thread_id, Entry(type="task_phase", parent_id=self.last_entry_id(thread_id),
                                     payload=payload))

    def record_tool_batch(self, thread_id: str, turn_id: str, batch_id: str,
                          call_ids: list[str], status: str, *,
                          assistant_item_id: str | None = None,
                          request_fingerprint: str | None = None) -> Entry:
        """Persist the complete expected call set before any handler can run."""
        _identifier(turn_id, "turnId")
        _identifier(batch_id, "toolBatchId")
        if (not isinstance(call_ids, list) or not 1 <= len(call_ids) <= MAX_TOOL_BATCH_CALLS
                or any(not isinstance(value, str) or not value or len(value) > 256 for value in call_ids)
                or len(set(call_ids)) != len(call_ids)):
            raise ValueError("工具批次调用清单无效")
        if status not in {"started", "completed"}:
            raise ValueError("工具批次状态无效")
        if assistant_item_id is not None and (not isinstance(assistant_item_id, str)
                or not _IDENTIFIER.fullmatch(assistant_item_id)):
            raise ValueError("工具批次 assistant 条目标识无效")
        if request_fingerprint is not None and (not isinstance(request_fingerprint, str)
                or not re.fullmatch(r"[a-f0-9]{64}", request_fingerprint)):
            raise ValueError("工具批次请求摘要无效")
        payload: dict[str, Any] = {"turnId": turn_id, "toolBatchId": batch_id,
                                   "callIds": list(call_ids), "status": status}
        if assistant_item_id is not None:
            payload["assistantItemId"] = assistant_item_id
        if request_fingerprint is not None:
            payload["requestFingerprint"] = request_fingerprint
        entry = Entry(type="tool_batch", parent_id=self.last_entry_id(thread_id), payload=payload)
        return self.append(thread_id, entry)

    def last_turn(self, thread_id: str) -> dict | None:
        return self.get_thread(thread_id).get("lastTurn")

    def get_turn(self, thread_id: str, turn_id: str) -> dict:
        _identifier(turn_id, "turnId")
        self._sync_thread(thread_id)

        def read() -> dict:
            with self._index.connection() as connection:
                row = connection.execute(
                    "SELECT * FROM turns WHERE thread_id=? AND turn_id=?", (thread_id, turn_id)).fetchone()
            if row is None:
                raise ValueError("回合不存在")
            rollout = self.read_entries(thread_id)
            owners = self._item_owners(rollout)
            entries = [entry for entry in rollout if owners.get(entry["id"]) == turn_id]
            return {**self._turn_metadata(row), "items": self._project_items(thread_id, entries)}

        return self._with_repaired_index(read)

    def list_turns(self, thread_id: str, *, cursor: str | None = None, limit: int = 50) -> dict:
        _limit(limit)
        self.path_for(thread_id)
        scope = {"threadId": thread_id}
        key = _read_page_cursor(cursor, "turns", scope)
        query = "SELECT * FROM turns WHERE thread_id=?"
        parameters: list[Any] = [thread_id]
        if key is not None:
            if len(key) != 2 or type(key[0]) is not int or key[0] < 0:
                raise ValueError("回合分页游标无效")
            _identifier(key[1], "turnId")
            query += " AND (first_ordinal>? OR (first_ordinal=? AND turn_id>?))"
            parameters.extend([key[0], key[0], key[1]])
        query += " ORDER BY first_ordinal,turn_id LIMIT ?"
        parameters.append(limit + 1)
        self._sync_thread(thread_id)

        def read() -> dict:
            with self._index.connection() as connection:
                rows = connection.execute(query, parameters).fetchall()
            page = rows[:limit]
            for row in page:
                # 与 list_branch_turns 同款守卫（#1802）：first_ordinal 被外部改写成
                # BLOB 时游标 json.dumps 抛 TypeError，回合分页会持续 -32603。
                if type(row["first_ordinal"]) is not int or not isinstance(row["turn_id"], str):
                    raise _IndexedMetadataError(thread_id)
            next_cursor = (_page_cursor("turns", scope, [page[-1]["first_ordinal"], page[-1]["turn_id"]])
                           if len(rows) > limit else None)
            return {"turns": [self._turn_metadata(row) for row in page], "nextCursor": next_cursor}

        return self._with_repaired_index(read)

    def list_branch_turns(self, thread_id: str, *, cursor: str | None = None, limit: int = 50,
                          entries: list[dict] | None = None) -> dict:
        """Indexed turn metadata restricted to the current branch (same order/cursor shape as list_turns).

        ``branch`` is the leaf state of the very entries the page was filtered by:
        callers compare it across pages to detect a leaf move between requests,
        so it must not come from a second read taken after the lock is released.
        ``entries`` pins a snapshot the caller already read (thread/read), so the
        page describes the same records as the caller's items and leaf state.
        """
        _limit(limit)
        self.path_for(thread_id)
        scope = {"threadId": thread_id, "view": "branch"}
        key = _read_page_cursor(cursor, "turns", scope)
        if key is not None:
            if len(key) != 2 or type(key[0]) is not int or key[0] < 0:
                raise ValueError("回合分页游标无效")
            _identifier(key[1], "turnId")
        self._sync_thread(thread_id)

        pinned = entries

        def read() -> dict:
            with self._lock:
                entries = self.read_entries(thread_id) if pinned is None else pinned
                active_turns = self._turns(self._active_entries(entries), thread_id)
                active_ids = {turn["turnId"] for turn in active_turns}
                # 回合集合与位置必须出自同一份条目：释放锁后再读一次，期间的切换或
                # 新回合会让同一响应里的 turns 属于旧位置、branch 却是新位置。
                leaf = self._leaf_state(thread_id, entries, turns=active_turns)
                with self._index.connection() as connection:
                    rows = connection.execute(
                        "SELECT * FROM turns WHERE thread_id=? ORDER BY first_ordinal,turn_id",
                        (thread_id,)).fetchall()
            selected = []
            for row in rows:
                # 投影列不保证仍是建表时的类型：SQLite 的列亲和性不会阻止外部把
                # first_ordinal 改写成文本。与游标整数比较会抛 TypeError，绕过只捕获
                # _IndexedMetadataError 的重建重试，把 -32603 送给调用方。按索引损坏
                # 处理，由既有重建路径从会话日志恢复行类型；放在成员判断之前，
                # 否则非文本 turn_id 只会让该回合从分页里静默消失。
                if type(row["first_ordinal"]) is not int or not isinstance(row["turn_id"], str):
                    raise _IndexedMetadataError(thread_id)
                if row["turn_id"] not in active_ids:
                    continue
                if key is not None and (row["first_ordinal"], row["turn_id"]) <= (key[0], key[1]):
                    continue
                selected.append(row)
                if len(selected) > limit:
                    break
            page = selected[:limit]
            next_cursor = (_page_cursor("turns", scope, [page[-1]["first_ordinal"], page[-1]["turn_id"]])
                           if len(selected) > limit else None)
            return {"turns": [self._turn_metadata(row) for row in page], "nextCursor": next_cursor,
                    "branch": leaf}

        return self._with_repaired_index(read)

    def branch_last_turn(self, thread_id: str, *, entries: list[dict] | None = None) -> dict | None:
        """Indexed metadata of the current branch's last turn (None before the first turn).

        ``entries`` pins a snapshot the caller already read, so the last turn
        belongs to the same branch as the caller's items.
        """
        if entries is not None:
            leaf = self._leaf_state(thread_id, entries)
        else:
            with self._lock:
                leaf = self._leaf_state(thread_id, self.read_entries(thread_id))
        if leaf["leafTurnId"] is None:
            return None
        self._sync_thread(thread_id)

        def read() -> dict | None:
            with self._index.connection() as connection:
                row = connection.execute(
                    "SELECT thread_id,metadata_json FROM turns WHERE thread_id=? AND turn_id=?",
                    (thread_id, leaf["leafTurnId"])).fetchone()
            return self._turn_metadata(row) if row is not None else None

        return self._with_repaired_index(read)

    _BRANCH_INDEPENDENT_TYPES = frozenset({"attachment", "thread_info", "queue"})

    @classmethod
    def _active_entries(cls, entries: list[dict]) -> list[dict]:
        """Project the branch selected by the latest leaf record.

        Entries keep file order.  Each appended entry continues the projection
        tail at its append time, so the result does not trust writer-provided
        parentId values.  Without any leaf record the input is returned as is.
        """
        if not any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):
            return entries
        previous: dict[str, str | None] = {}
        records: dict[str, dict] = {}
        tail: str | None = None
        for entry in entries:
            if entry.get("type") == LEAF_ENTRY_TYPE:
                payload = entry.get("payload")
                target = payload.get("targetId") if isinstance(payload, dict) else None
                if target is not None and (not isinstance(target, str) or target not in records
                                           or records[target].get("type") != "turn"):
                    # 持久叶记录可被外部改写或由崩溃留下半写状态：损坏指针按缺失
                    # 处理，继续使用上一个有效叶。整段 raise 会让分支读取、分支
                    # 列表、导出、fork、上下文读取与所有模型回合一起失败，会话既
                    # 无法查看也无法恢复。
                    continue
                tail = target
                continue
            if entry["id"] in records:
                raise ValueError("会话条目编号重复，无法投影分支")
            records[entry["id"]] = entry
            previous[entry["id"]] = tail
            tail = entry["id"]
        path: set[str] = set()
        cursor = tail
        while cursor is not None:
            path.add(cursor)
            cursor = previous[cursor]
        included_turns = {_record_id(entry["payload"].get("turnId")) for entry in entries
                          if entry["id"] in path and entry.get("type") == "turn"
                          and isinstance(entry.get("payload"), dict)}
        included_turns.discard(None)
        owners = cls._item_owners([entry for entry in entries if entry.get("type") != LEAF_ENTRY_TYPE])

        def keep(entry: dict) -> bool:
            kind = entry.get("type")
            if kind == LEAF_ENTRY_TYPE:
                return False
            payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            if kind == "item":
                owner = owners.get(entry["id"])
                # Late revisions follow their owning turn, not the physical tail.
                return owner in included_turns if owner is not None else entry["id"] in path
            if entry["id"] in path:
                return True
            if kind in cls._BRANCH_INDEPENDENT_TYPES:
                # Session-level state (uploaded files, title, queue) is shared by
                # every branch; only content owned by abandoned turns is dropped.
                return True
            if kind in {"turn", "task_phase", "tool_batch"}:
                return _record_id(payload.get("turnId", payload.get("taskId"))) in included_turns
            if kind == "context_edit":
                return owners.get(_record_id(payload.get("targetItemId"))) in included_turns
            if kind == "context_checkpoint":
                return _record_id(payload.get("throughTurnId")) in included_turns
            return False

        return [entry for entry in entries if keep(entry)]

    @classmethod
    def _turn_tree(cls, entries: list[dict]) -> tuple[dict[str, str | None], list[str]]:
        """Parent turn of every turn, following the same append-time tail rule as _active_entries.

        Returns (parent by turnId, turnIds in first-appearance order).  Forged
        leaf targets raise exactly like the projection does.
        """
        cls._active_entries(entries)
        owners = cls._item_owners([entry for entry in entries if entry.get("type") != LEAF_ENTRY_TYPE])
        known = {entry["payload"].get("turnId") for entry in entries if entry.get("type") == "turn"
                 and isinstance(entry.get("payload"), dict)
                 and isinstance(entry["payload"].get("turnId"), str)
                 and _IDENTIFIER.fullmatch(entry["payload"]["turnId"])}
        parent: dict[str, str | None] = {}
        order: list[str] = []
        record_turn: dict[str, str | None] = {}
        tail: str | None = None
        for entry in entries:
            kind = entry.get("type")
            payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            if kind == LEAF_ENTRY_TYPE:
                target = payload.get("targetId")
                tail = record_turn.get(target) if isinstance(target, str) else None
                continue
            if kind == "turn":
                owner = payload.get("turnId")
            elif kind == "item":
                owner = owners.get(entry["id"])
            elif kind in {"task_phase", "tool_batch"}:
                owner = payload.get("turnId", payload.get("taskId"))
            else:
                owner = None
            if isinstance(owner, str) and owner in known:
                if owner not in parent:
                    parent[owner] = tail if tail != owner else None
                    order.append(owner)
                tail = owner
            record_turn[entry["id"]] = tail
        return parent, order

    def list_branches(self, thread_id: str, *, cursor: str | None = None, limit: int = 50) -> dict:
        """Enumerate branch endpoints (turns without children) of the in-session turn tree."""
        _limit(limit)
        self.path_for(thread_id)
        scope = {"threadId": thread_id, "view": "endpoints"}
        key = _read_page_cursor(cursor, "branches", scope)
        if key is not None:
            if len(key) != 2 or type(key[0]) is not int or key[0] < 0:
                raise ValueError("分支分页游标无效")
            _identifier(key[1], "turnId")
        with self._lock:
            entries = self.read_entries(thread_id)
            parent, order = self._turn_tree(entries)
            leaf = self._leaf_state(thread_id, entries)
            turns = {turn["turnId"]: turn for turn in self._turns(entries, thread_id)}
            owners = self._item_owners([entry for entry in entries if entry.get("type") != LEAF_ENTRY_TYPE])
        previews: dict[str, str] = {}
        for entry in entries:
            payload = entry.get("payload")
            if (entry.get("type") == "item" and isinstance(payload, dict)
                    and payload.get("kind") == "userMessage" and isinstance(payload.get("text"), str)):
                owner = owners.get(entry["id"])
                if isinstance(owner, str) and owner not in previews:
                    text = " ".join(payload["text"].split())
                    previews[owner] = text[:MAX_BRANCH_PREVIEW_CHARS] + ("…" if len(text) > MAX_BRANCH_PREVIEW_CHARS else "")
        children: dict[str | None, list[str]] = {}
        for turn_id in order:
            children.setdefault(parent[turn_id], []).append(turn_id)
        position = {turn_id: index for index, turn_id in enumerate(order)}
        leaf_path: set[str] = set()
        cursor_turn = leaf["leafTurnId"]
        while cursor_turn is not None:
            leaf_path.add(cursor_turn)
            cursor_turn = parent.get(cursor_turn)
        endpoints = [turn_id for turn_id in order if turn_id not in children]
        if key is not None:
            endpoints = [turn_id for turn_id in endpoints if (position[turn_id], turn_id) > (key[0], key[1])]
        page = endpoints[:limit]
        result = []
        for turn_id in page:
            path = [turn_id]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            path.reverse()
            fork_point = next((ancestor for ancestor in reversed(path[:-1])
                               if len(children.get(ancestor, [])) > 1), None)
            branch_turn = path[0] if fork_point is None else path[path.index(fork_point) + 1]
            turn = turns.get(turn_id, {})
            result.append({
                "turnId": turn_id, "status": turn.get("status"),
                "startedAt": turn.get("startedAt"), "updatedAt": turn.get("updatedAt"),
                "completedAt": turn.get("completedAt"),
                "depth": len(path), "forkTurnId": fork_point, "branchTurnId": branch_turn,
                "branchInputPreview": previews.get(branch_turn),
                "inputPreview": previews.get(turn_id),
                "containsLeaf": leaf["leafTurnId"] in path,
                "isLeaf": leaf["leafTurnId"] == turn_id,
                "selectable": isinstance(turn.get("status"), str) and turn.get("status") in _TERMINAL})
        next_cursor = (_page_cursor("branches", scope, [position[page[-1]], page[-1]])
                       if len(endpoints) > limit else None)
        return {"threadId": thread_id, "branched": leaf["branched"], "leafTurnId": leaf["leafTurnId"],
                "turnCount": len(order), "endpoints": result, "nextCursor": next_cursor}

    def read_active_entries(self, thread_id: str) -> list[dict]:
        return self._active_entries(self.read_entries(thread_id))

    def _leaf_state(self, thread_id: str, entries: list[dict], active: list[dict] | None = None, *,
                    turns: list[dict] | None = None) -> dict:
        # ``turns`` 供已算出当前分支回合的调用方复用，保证位置与其回合集合同源。
        if turns is None:
            active = self._active_entries(entries) if active is None else active
            turns = self._turns(active, thread_id)
        turn_ids = [turn["turnId"] for turn in turns]
        return {"threadId": thread_id,
                "branched": any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries),
                "leafTurnId": turn_ids[-1] if turn_ids else None,
                "activeTurnCount": len(turn_ids),
                "activeTurnIds": turn_ids[-MAX_LEAF_ACTIVE_TURN_IDS:],
                "activeTurnIdsTruncated": len(turn_ids) > MAX_LEAF_ACTIVE_TURN_IDS}

    def usage_page(self, thread_id: str, *, branch: bool, cursor: str | None = None, limit: int = 50,
                   active_summary_job_id: str | None = None,
                   entries: list[dict] | None = None) -> dict:
        """Read-only per-turn usage aggregated from persisted usage records.

        ``active_summary_job_id`` is the caller's validated current-branch
        checkpoint job; it only marks the matching summary job, never resolves
        jobs from usage records on its own. ``entries`` may pin the snapshot a
        caller already read so usage and its marker describe the same records.
        Only the log view reports ``cacheWaste``; the branch projection
        interleaves abandoned requests, so its linear baseline is not reported.
        """
        from boss_harness.usage import SOURCE, summarize_usage
        _limit(limit)
        scope = {"threadId": thread_id, "view": "branch" if branch else "log"}
        key = _read_page_cursor(cursor, "usage", scope)
        if key is not None and (len(key) != 1 or type(key[0]) is not int or key[0] < 0):
            raise ValueError("用量分页游标无效")
        offset = key[0] if key is not None else 0
        with self._lock:
            if entries is None:
                entries = self.read_entries(thread_id)
            else:
                self.require_thread(thread_id)
            scope_entries = self._active_entries(entries) if branch else entries
            turns = self._turns(scope_entries, thread_id)
            active = {turn["turnId"] for turn in turns} if branch else None
            policies = {turn["turnId"]: turn.get("compactionPolicy") for turn in turns
                        if turn.get("compactionPolicy") is not None}
            # 耗时取自同一快照的回合记录；用量记录只决定哪些回合出现，不改变时间事实。
            timing = {turn["turnId"]: turn for turn in turns}
            leaf = self._leaf_state(thread_id, entries) if branch else None
        result = summarize_usage(entries, active, policies, active_summary_job_id)
        turns = result["turns"]
        for turn in turns:
            record = timing.get(turn["turnId"])
            if record is None:
                continue
            for key in ("startedAt", "completedAt"):
                value = _valid_timestamp(record.get(key))
                if value is not None:
                    turn[key] = value
            status = record.get("status")
            if isinstance(status, str) and status in _TERMINAL | {"running"}:
                turn["status"] = status
            skill_ids = bounded_skill_ids(record.get("skillIds"))
            if skill_ids:
                turn["skillIds"] = skill_ids
        out = {"threadId": thread_id, "view": scope["view"], "source": SOURCE, "costAvailable": False,
               "turnCount": len(turns), "turns": [], "nextCursor": None,
               "summaryTasks": result["summaryTasks"], "totals": result["totals"],
               "summaryJobs": result["summaryJobs"], "summaryJobCount": result["summaryJobCount"],
               "summaryJobsTruncated": result["summaryJobsTruncated"]}
        if "cacheWaste" in result:
            # 只在“全部记录”视图返回：分支视图的请求流交错，线性基线不可解释。
            out["cacheWaste"] = result["cacheWaste"]
        if leaf is not None:
            out["branch"] = leaf
        try:
            fixed_size = wire_size(out)
        except (TypeError, ValueError):
            fixed_size = MAX_PAGE_BYTES + 1
        if fixed_size > MAX_PAGE_BYTES or offset > len(turns):
            return out
        page: list[dict] = []
        end = min(offset + limit, len(turns))
        position = offset
        while position < end:
            candidate = page + [turns[position]]
            out["turns"] = candidate
            out["nextCursor"] = (_page_cursor("usage", scope, [position + 1])
                                 if position + 1 < len(turns) else None)
            if wire_size(out) > MAX_PAGE_BYTES:
                if not page:
                    break
                out["turns"] = page
                out["nextCursor"] = (_page_cursor("usage", scope, [position])
                                     if position < len(turns) else None)
                return out
            page = candidate
            position += 1
        out["turns"] = page
        return out

    def read_leaf(self, thread_id: str, *, entries: list[dict] | None = None) -> dict:
        """Current leaf state; ``entries`` pins a snapshot the caller already read."""
        if entries is not None:
            return self._leaf_state(thread_id, entries)
        with self._lock:
            return self._leaf_state(thread_id, self.read_entries(thread_id))

    def branch_snapshot_projection(self, thread_id: str, entries: list[dict], *,
                                   max_turn_bytes: int = 1024 * 1024) -> dict:
        """Branch projection of one pinned rollout prefix, for frozen view=branch snapshots.

        keepIds is None when the prefix has no leaf record (the branch equals the
        log); leafEntryId binds the snapshot to the latest leaf record it saw.
        Turn metadata matches thread/turns/list view=branch (first page only).
        """
        active = self._active_entries(entries)
        leaf = self._leaf_state(thread_id, entries, active)
        leaf_entry_id = next((entry["id"] for entry in reversed(entries)
                              if entry.get("type") == LEAF_ENTRY_TYPE), None)
        turns = [self._public_turn(turn) for turn in self._turns(active, thread_id)]
        page: list[dict] = []
        turn_bytes = 0
        too_large = False
        for turn in turns[:50]:
            turn_bytes += len(_json(turn).encode("utf-8"))
            if turn_bytes > max_turn_bytes:
                too_large = True
                break
            page.append(turn)
        return {"leaf": leaf, "leafEntryId": leaf_entry_id,
                "keepIds": frozenset(entry["id"] for entry in active) if leaf["branched"] else None,
                "lastTurn": turns[-1] if turns else None, "turns": page, "turnsTooLarge": too_large}

    def set_leaf(self, thread_id: str, turn_id: str | None, *, _with_entry_id: bool = False) -> dict:
        """Move the in-session branch pointer to a settled turn (None = before the first turn)."""
        if turn_id is not None:
            _identifier(turn_id, "turnId")
        with self._lock, self._index.transaction() as connection:
            self.require_thread(thread_id)
            self._index_thread(thread_id, connection)
            entries = self.read_entries(thread_id)
            current = self._leaf_state(thread_id, entries)
            if current["leafTurnId"] == turn_id and (turn_id is not None or current["activeTurnCount"] == 0):
                return {**current, "changed": False}
            target_id: str | None = None
            if turn_id is not None:
                records = [entry for entry in entries if entry.get("type") == "turn"
                           and isinstance(entry.get("payload"), dict)
                           and entry["payload"].get("turnId") == turn_id]
                if (not records or not isinstance(records[-1]["payload"].get("status"), str)
                        or records[-1]["payload"].get("status") not in _TERMINAL):
                    raise ValueError("仅可把分支指针移到已经结束的回合")
                target_id = records[-1]["id"]
            all_turns = self._turns(entries, thread_id)
            if any(not isinstance(turn.get("status"), str) or turn.get("status") not in _TERMINAL
                   for turn in all_turns):
                raise ValueError("会话仍有未结束的回合，不能切换分支")
            for item in self._project_items(thread_id, entries):
                approval = item.get("approval") or {}
                if item.get("status") == "running" or (approval and not approval.get("decision")):
                    raise ValueError("会话中仍有未收尾条目或审批，不能切换分支")
            entry = Entry(type=LEAF_ENTRY_TYPE, parent_id=target_id,
                          payload={"targetId": target_id, "turnId": turn_id,
                                   "fromTurnId": current["leafTurnId"]})
            candidate = entries + [entry.to_dict()]
            state = self._leaf_state(thread_id, candidate)
            if state["leafTurnId"] != turn_id:
                raise ValueError("分支指针目标与回合边界不一致")
            self._append_line(self.path_for(thread_id), entry.to_dict())
            self._index_thread(thread_id, connection)
            result = {**state, "changed": True}
            if _with_entry_id:
                result["_leafEntryId"] = entry.id
            return result

    def abandoned_branch(self, thread_id: str, target_turn_id: str | None,
                         entries: list[dict] | None = None) -> dict:
        """Turns given up by moving the leaf to target: old leaf back to the common ancestor (exclusive)."""
        entries = self.read_entries(thread_id) if entries is None else entries
        parent, _ = self._turn_tree(entries)
        leaf = self._leaf_state(thread_id, entries)
        if target_turn_id is not None and target_turn_id not in parent:
            raise ValueError("目标回合不存在")
        ancestors: set[str] = set()
        cursor = target_turn_id
        while cursor is not None:
            ancestors.add(cursor)
            cursor = parent.get(cursor)
        abandoned: list[str] = []
        cursor = leaf["leafTurnId"]
        while cursor is not None and cursor not in ancestors:
            abandoned.append(cursor)
            cursor = parent.get(cursor)
        abandoned.reverse()
        return {"fromTurnId": leaf["leafTurnId"], "targetTurnId": target_turn_id,
                "commonTurnId": cursor, "abandonedTurnIds": abandoned}

    def append_branch_summary(self, thread_id: str, leaf_entry_id: str, payload: dict,
                              *, on_committed: Callable[[], None] | None = None) -> Entry:
        """Append a branch summary only while the leaf record that requested it is still current."""
        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip() or len(summary) > MAX_BRANCH_SUMMARY_CHARS:
            raise ValueError("被放弃分支摘要必须是 1 到 32000 字符")
        with self._lock, self._index.transaction() as connection:
            self.require_thread(thread_id)
            entries = self.read_entries(thread_id)
            index = next((position for position in range(len(entries) - 1, -1, -1)
                          if entries[position].get("type") == LEAF_ENTRY_TYPE), None)
            if index is None or entries[index]["id"] != leaf_entry_id:
                raise ValueError("分支指针已变化，未写入被放弃分支摘要")
            if any(entry.get("type") in {"turn", BRANCH_SUMMARY_ENTRY_TYPE} for entry in entries[index + 1:]):
                raise ValueError("切换后已有新回合或摘要，未写入被放弃分支摘要")
            entry = Entry(type=BRANCH_SUMMARY_ENTRY_TYPE, payload={**payload, "leafEntryId": leaf_entry_id})
            self._append_line(self.path_for(thread_id), entry.to_dict())
            if on_committed is not None:
                on_committed()
            self._index_thread(thread_id, connection)
            return entry

    def fork_thread(self, thread_id: str, *, turn_id: str | None = None, title: str | None = None) -> dict:
        with self._lock:
            source = self.get_thread(thread_id)
            # A fork copies only one branch; leaf records never travel.  Without
            # turnId it is the active branch; a settled turn on another branch
            # selects that branch as if the leaf pointed at it (no record written).
            raw_entries = self.read_entries(thread_id)
            entries = self._active_entries(raw_entries)
            if turn_id is not None and isinstance(turn_id, str) and _IDENTIFIER.fullmatch(turn_id) and not any(
                    turn["turnId"] == turn_id for turn in self._turns(entries, thread_id)):
                records = [entry for entry in raw_entries if entry.get("type") == "turn"
                           and isinstance(entry.get("payload"), dict)
                           and entry["payload"].get("turnId") == turn_id]
                last_status = records[-1]["payload"].get("status") if records else None
                if isinstance(last_status, str) and last_status in _TERMINAL:
                    synthetic = Entry(type=LEAF_ENTRY_TYPE, parent_id=records[-1]["id"],
                                      payload={"targetId": records[-1]["id"], "turnId": turn_id})
                    entries = self._active_entries(raw_entries + [synthetic.to_dict()])
            turns = self._turns(entries, thread_id)
            if turn_id is None:
                selected = turns[-1] if turns else None
            else:
                _identifier(turn_id, "turnId")
                selected = next((turn for turn in turns if turn["turnId"] == turn_id), None)
            if (selected is None or not isinstance(selected.get("status"), str)
                    or selected.get("status") not in _TERMINAL):
                raise ValueError("仅可从已经结束的回合创建分支")
            cutoff = selected.get("boundaryOrdinal", selected["lastOrdinal"])
            turn_positions = {turn["turnId"]: position for position, turn in enumerate(turns)}
            selected_position = turn_positions[selected["turnId"]]

            def checkpoint_in_branch(entry: dict) -> bool:
                payload = entry.get("payload")
                through_turn_id = payload.get("throughTurnId") if isinstance(payload, dict) else None
                position = turn_positions.get(through_turn_id) if isinstance(through_turn_id, str) else None
                return position is not None and position <= selected_position

            prefix = [entry for entry in entries[:cutoff + 1]
                      if entry.get("type") != "context_checkpoint" or checkpoint_in_branch(entry)]
            included_turns = {_record_id(entry["payload"]["turnId"]) for entry in prefix
                              if entry.get("type") == "turn" and "turnId" in entry["payload"]}
            included_turns.discard(None)
            owners = self._item_owners(entries)
            # Recovery may append a revision after later settled turns. Include only
            # corrections owned by the selected prefix, never those unrelated turns.
            for entry in entries[cutoff + 1:]:
                if ((entry.get("type") == "item" and owners.get(entry["id"]) in included_turns)
                        or (entry.get("type") == "turn"
                            and _record_id(entry["payload"].get("turnId")) in included_turns)
                        or (entry.get("type") == "context_edit"
                            and owners.get(_record_id(entry["payload"].get("targetItemId"))) in included_turns)
                        or (entry.get("type") == "context_checkpoint" and checkpoint_in_branch(entry))):
                    prefix.append(entry)
            projected = self._project_items(thread_id, prefix)
            for item in projected:
                approval = item.get("approval") or {}
                if item.get("status") == "running" or (approval and not approval.get("decision")):
                    raise ValueError("回合中仍有未收尾条目或审批，不能创建分支")
            batches = {item["toolBatchId"] for item in projected if item.get("toolBatchId")}
            included_items = {item["id"] for item in projected}
            if any(item.get("toolBatchId") in batches and item["id"] not in included_items
                   for item in self._project_items(thread_id, entries)):
                raise ValueError("分支边界会拆开工具批次")
            header = {key: value for key, value in source.items()
                      if key not in {"id", "sessionId", "createdAt", "updatedAt", "lastTurn",
                                     "branchLastTurn", "queueActiveItems", "queueCounts",
                                     # 读取投影的派生标记不是会话头字段，写进新会话会变成
                                     # 永久状态，重命名也无法清除。
                                     "projectIdTruncated", "titleTruncated"}}
            # 来源标识已被投影截断：不把截断值当成完整标识继承，也不猜测原值。
            if source.get("projectIdTruncated"):
                header.pop("projectId", None)
            header.update(type="session", version=2, id=uuid.uuid4().hex[:12],
                          sessionId=uuid.uuid4().hex, createdAt=_now(), archived=False,
                          forkedFromId=thread_id, forkedFromTurnId=selected["turnId"])
            if title is not None:
                if not isinstance(title, str) or len(title) > MAX_THREAD_TITLE_CHARS:
                    raise ValueError(f"title 必须是最多 {MAX_THREAD_TITLE_CHARS} 字符的字符串")
                header["title"] = title
            request_offset = selected.get("continuationRequestOffset", 0)
            if type(request_offset) is not int or request_offset < 0:
                raise ValueError("来源回合模型请求计数无法核验，不能创建分支")
            for entry in entries:
                payload = entry.get("payload")
                if (entry.get("type") != "task_phase" or not isinstance(payload, dict)
                        or payload.get("taskId") != selected["turnId"]
                        or payload.get("phase") != "model_request"):
                    continue
                attempt = payload.get("attempt")
                if (payload.get("ownerKind") != "turn" or type(attempt) is not int
                        or not 1 <= attempt <= 1_000):
                    raise ValueError("来源回合模型请求阶段无法核验，不能创建分支")
                request_offset = max(request_offset, attempt)
            copied: list[dict] = []
            copied_ids: set[str] = set()
            approval_ids: dict[str, str] = {}
            for entry in json.loads(_json(prefix)):
                # Queue state belongs to one thread, not its transcript forks.
                if entry["type"] in {"thread_info", "queue", "task_phase"}:
                    continue
                if (entry["type"] == "turn"
                        and entry["payload"].get("turnId") == selected["turnId"]):
                    entry["payload"]["continuationRequestOffset"] = request_offset
                if (entry["type"] == "context_edit"
                        and owners.get(_record_id(entry["payload"].get("targetItemId"))) not in included_turns):
                    continue
                if entry.get("parentId") not in copied_ids:
                    entry["parentId"] = copied[-1]["id"] if copied else None
                if entry["payload"].get("threadId") == thread_id:
                    entry["payload"]["threadId"] = header["id"]
                approval = entry["payload"].get("approval")
                approval_id = approval.get("approvalId") if isinstance(approval, dict) else None
                if isinstance(approval_id, str):
                    # approval/respond resolves an id globally; a copied decision
                    # must not make the source approval ambiguous.
                    if approval_id not in approval_ids:
                        approval_ids[approval_id] = uuid.uuid4().hex
                    approval["approvalId"] = approval_ids[approval_id]
                copied.append(entry)
                copied_ids.add(entry["id"])
            _rehash_continuation_boundaries(copied)
            return self._write_new(header, copied)

    def recover(self) -> None:
        """Finalize abandoned work, including archived sessions; never execute a tool."""
        for thread in self.list_threads(include_archived=True):
            thread_id = thread["id"]
            try:
                entries = self.read_entries(thread_id)
            except (OSError, ValueError):
                # Reads of a damaged thread keep reporting the damaged line;
                # startup recovery still has to finalize every other session.
                continue
            turns = self._turns(entries, thread_id)
            # The last record written before this process started is the closest
            # known point to the previous exit. Recovered turns use it as their
            # completedAt so downtime after a crash is not counted as busy time.
            last_activity = _valid_timestamp(entries[-1].get("timestamp")) if entries else None
            turns_by_id = {turn["turnId"]: turn for turn in turns}
            latest_phases: dict[str, dict[str, Any]] = {}
            for entry in entries:
                if entry.get("type") != "task_phase" or not isinstance(entry.get("payload"), dict):
                    continue
                payload = entry["payload"]
                task_id, phase = payload.get("taskId"), payload.get("phase")
                if (payload.get("ownerKind") == "turn" and isinstance(task_id, str)
                        and _IDENTIFIER.fullmatch(task_id)
                        and isinstance(phase, str) and phase in _TASK_PHASES):
                    latest_phases[task_id] = payload
            for task_id, phase in latest_phases.items():
                turn = turns_by_id.get(task_id)
                if turn is None:
                    continue
                if isinstance(turn.get("status"), str) and turn.get("status") in _TERMINAL:
                    status = turn["status"]
                    reason = "terminalStateRecovered"
                    policy = "closed"
                else:
                    status = "interrupted"
                    reason = "processExit"
                    policy = "manual"
                if (phase.get("phase") == "finish" and phase.get("status") == status
                        and (phase.get("resumePolicy") == policy or policy == "closed")):
                    continue
                attempt = phase.get("attempt", 1)
                if type(attempt) is not int or not 1 <= attempt <= 1_000:
                    attempt = 1
                restart_limit = phase.get("restartLimit", 0)
                if type(restart_limit) is not int or not 0 <= restart_limit <= 32:
                    restart_limit = 0
                phase_was_running = phase.get("status") == "running"
                if phase_was_running:
                    self.record_task_phase(
                        thread_id, task_id, phase["phase"], status,
                        attempt=attempt, restart_limit=restart_limit,
                        recovery_reason=reason, resume_policy=policy,
                    )
                if phase.get("phase") != "finish" or not phase_was_running:
                    self.record_task_phase(thread_id, task_id, "finish", status,
                                           attempt=attempt, restart_limit=restart_limit,
                                           recovery_reason=reason, resume_policy=policy)
            turn_by_item = self._item_owners(entries)
            items = self._project_items(thread_id, entries)
            recovered_turns: set[str] = set()
            for item in items:
                approval = item.get("approval")
                pending_approval = isinstance(approval, dict) and not approval.get("decision")
                if item.get("status") != "running" and not pending_approval:
                    continue
                affected_turn = item.get("turnId") or turn_by_item.get(item["id"])
                owner_status = turns_by_id.get(affected_turn, {}).get("status") if affected_turn else None
                # 只有仍可恢复的回合才保留待决审批：approval/list 也只对 running /
                # interrupted 回合开放。所属回合已终态却留下待决审批，说明收尾中途
                # 失败，再等 deadline 只会让它继续不可见。损坏的状态无法证明回合
                # 仍可恢复，同样按失效处理，且不能让启动恢复因不可哈希值中断。
                if (pending_approval and isinstance(owner_status, str)
                        and owner_status in {"running", "interrupted"}
                        and self._valid_approval_item(item, pending_only=True)
                        and approval["deadline"] > time.time()):
                    continue
                payload = self._abandoned_item_payload(
                    item, error_code="SESSION_INTERRUPTED",
                    unknown_summary="上次进程在操作收尾前退出，结果不确定；先核对平台状态，不要直接重试。",
                    not_executed_summary="上次进程在工具执行前退出，该操作未执行；旧审批已经失效。")
                self.append(thread_id, Entry(type="item", parent_id=self.last_entry_id(thread_id), payload=payload))
                if affected_turn:
                    recovered_turns.add(affected_turn)
            for turn in turns:
                if turn.get("status") == "running" or turn["turnId"] in recovered_turns:
                    fields: dict[str, Any] = {"recoveryReason": "processExit"}
                    if last_activity is not None:
                        fields["completedAt"] = last_activity
                    self.record_turn(thread_id, turn["turnId"], "interrupted", **fields)

    @staticmethod
    def _abandoned_item_payload(item: dict, *, error_code: str, unknown_summary: str,
                                not_executed_summary: str) -> dict:
        """构造被遗弃条目的终态修订；启动恢复与在线回合结算共用同一规则。"""
        payload = {key: value for key, value in item.items() if key not in {"id", "threadId"}}
        payload.update(status="failed", revises=item["id"])
        approval = item.get("approval")
        if isinstance(approval, dict) and not approval.get("decision"):
            payload["approval"] = {**approval, "decision": "expired", "decidedAt": _now()}
        if item.get("kind") == "toolCall":
            payload.update(errorCode=error_code, resultSummary=unknown_summary)
            phase = item.get("executionState")
            # 损坏的执行状态无法证明操作未执行，只能按结果不确定处理。
            payload["executionState"] = "not_executed" if (
                isinstance(phase, str)
                and phase in {"queued", "pending_approval", "approved", "not_approved"}
            ) else "outcome_unknown"
            if payload["executionState"] == "not_executed":
                payload["resultSummary"] = not_executed_summary
        return payload

    def settle_abandoned_turn(self, thread_id: str, turn_id: str) -> int:
        """结算刚结束的回合遗留的 running 条目与待决审批，返回条目数。

        回合可能在上报审批或写入完成修订时失败，条目已落库为 running 却没有
        终态。进程不重启就不会有人再收尾它：approval/list 只列 running /
        interrupted 回合的待决审批，压缩又拒绝任何 running 条目，于是审批
        不可见、线程也无法压缩或分支。这里按启动恢复的同一规则补终态记录。
        """
        with self._lock:
            self.require_thread(thread_id)
            entries = self.read_entries(thread_id)
            owners = self._item_owners(entries)
            settled = 0
            for item in self._project_items(thread_id, entries):
                approval = item.get("approval")
                pending_approval = isinstance(approval, dict) and not approval.get("decision")
                if item.get("status") != "running" and not pending_approval:
                    continue
                if (item.get("turnId") or owners.get(item["id"])) != turn_id:
                    continue
                payload = self._abandoned_item_payload(
                    item, error_code="TURN_FAILED",
                    unknown_summary="回合在工具收尾前失败，结果不确定；先核对平台状态，不要直接重试。",
                    not_executed_summary="回合在工具执行前失败，该操作未执行；旧审批已经失效。")
                self.append(thread_id, Entry(type="item", parent_id=self.last_entry_id(thread_id),
                                             payload=payload))
                settled += 1
            return settled

    def _sync_events(self) -> None:
        with self._lock, self._index.transaction() as connection:
            self._index_events(connection)

    def _index_events(self, connection: sqlite3.Connection) -> None:
        pending = self._pending_deletion_ids()
        if pending:
            connection.execute("PRAGMA secure_delete=ON")
        for thread_id in pending:
            connection.execute("DELETE FROM events WHERE thread_id=?", (thread_id,))
        if not self.events_path.exists():
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("DELETE FROM events")
            connection.execute("DELETE FROM checkpoints WHERE name='events'")
            return
        stat = self.events_path.stat()
        fingerprint = f"{stat.st_size}:{stat.st_mtime_ns}"
        checkpoint = connection.execute("SELECT value FROM checkpoints WHERE name='events'").fetchone()
        if checkpoint and checkpoint["value"] == fingerprint:
            return
        connection.execute("PRAGMA secure_delete=ON")
        connection.execute("DELETE FROM events")
        for line_number, line in enumerate(_iter_bounded_lines(
                self.events_path, maximum=MAX_EVENT_LINE_BYTES, label="事件日志"), start=1):
            if not line.strip():
                continue
            record = _decode_jsonl_object(line, label="事件日志", line_number=line_number)
            params = record.get("params")
            method = record.get("method")
            if (record.get("type") != "event" or not isinstance(record.get("timestamp"), str)
                    or not isinstance(params, dict) or not isinstance(method, str) or not method
                    or len(method) > 256 or any(ord(char) < 32 for char in method)):
                raise ValueError(f"事件日志第 {line_number} 行格式无效，读取已停止")
            event_id = params.get("eventId")
            try:
                cursor = _event_cursor(params.get("eventCursor"))
            except ValueError:
                raise ValueError(f"事件日志第 {line_number} 行游标无效，读取已停止") from None
            thread_id = params.get("threadId")
            if (not isinstance(event_id, str) or not _EVENT_ID.fullmatch(event_id) or cursor < 1
                    or (thread_id is not None and not isinstance(thread_id, str))):
                raise ValueError(f"事件日志第 {line_number} 行格式无效，读取已停止")
            if thread_id is not None:
                try:
                    self.path_for(thread_id)
                except ValueError:
                    raise ValueError(f"事件日志第 {line_number} 行 threadId 无效，读取已停止") from None
            previous = connection.execute("SELECT event_id FROM events WHERE cursor=?", (cursor,)).fetchone()
            if previous and previous["event_id"] != event_id:
                raise ValueError("事件日志存在重复游标，请保留原文件后恢复")
            try:
                connection.execute("""INSERT INTO events(cursor,event_id,method,thread_id,params_json)
                    VALUES(?,?,?,?,?)""", (cursor, event_id, method, thread_id, _json(params)))
            except sqlite3.IntegrityError:
                raise ValueError(f"事件日志第 {line_number} 行包含重复 eventId，读取已停止") from None
        for thread_id in pending:
            connection.execute("DELETE FROM events WHERE thread_id=?", (thread_id,))
        connection.execute("INSERT INTO checkpoints(name,value) VALUES('events',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (fingerprint,))

    def append_event(self, method: str, params: dict[str, Any] | None = None) -> dict:
        if (not isinstance(method, str) or not method or len(method) > 256
                or any(ord(char) < 32 for char in method)):
            raise ValueError("事件方法名无效")
        if params is not None and not isinstance(params, dict):
            raise ValueError("事件参数必须是对象")
        payload = dict(params or {})
        if {"eventId", "eventCursor"} & set(payload):
            raise ValueError("eventId 与 eventCursor 由存储层生成")
        thread_id = payload.get("threadId")
        _json(payload)
        with self._lock, self._index.transaction() as connection:
            if thread_id is not None:
                self.require_thread(thread_id)
            self._index_events(connection)
            event_id = uuid.uuid4().hex
            inserted = connection.execute("INSERT INTO events(event_id,method,thread_id,params_json) VALUES(?,?,?,'{}')", (event_id, method, thread_id))
            payload.update(eventId=event_id, eventCursor=str(inserted.lastrowid))
            frame = {"method": method, "params": payload}
            record = {"type": "event", "timestamp": _now(), **frame}
            if len(_json(record).encode("utf-8")) > MAX_EVENT_LINE_BYTES:
                raise ValueError("事件日志单行超过大小限制")
            self._append_line(self.events_path, record)
            connection.execute("UPDATE events SET params_json=? WHERE cursor=?", (_json(payload), inserted.lastrowid))
            stat = self.events_path.stat()
            connection.execute("INSERT INTO checkpoints(name,value) VALUES('events',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (f"{stat.st_size}:{stat.st_mtime_ns}",))
        return frame

    def events_after(self, cursor: str | None = None, thread_id: str | None = None, limit: int = 100,
                     methods: tuple[str, ...] | list[str] | None = None) -> dict:
        position = _event_cursor(cursor)
        _limit(limit, 1000)
        if thread_id is not None:
            self.require_thread(thread_id)
        if methods is not None and (not isinstance(methods, (tuple, list)) or not 1 <= len(methods) <= 16
                or any(not isinstance(method, str) or not method or len(method) > 256
                       or any(ord(char) < 32 for char in method) for method in methods)):
            raise ValueError("事件方法筛选无效")
        query = "SELECT cursor,method,params_json FROM events WHERE cursor>?"
        parameters: list[Any] = [position]
        if thread_id is not None:
            query += " AND thread_id=?"
            parameters.append(thread_id)
        if methods is not None:
            query += " AND method IN (" + ",".join("?" for _ in methods) + ")"
            parameters.extend(methods)
        query += " ORDER BY cursor LIMIT ?"
        parameters.append(limit + 1)
        with self._lock:
            pending = sorted(self._pending_deletion_ids()) if thread_id is None else []
            if pending:
                query = query.replace(" ORDER BY cursor LIMIT ?",
                    " AND (thread_id IS NULL OR thread_id NOT IN (" + ",".join("?" for _ in pending)
                    + ")) ORDER BY cursor LIMIT ?")
                parameters[-1:-1] = pending
            self._sync_events()
            rows, has_more = self._event_rows(query, parameters, limit)
            try:
                events = self._event_page_entries(rows, limit)
            except ValueError:
                # 事件索引从 events.jsonl 派生，可重建：先修复再重试一次，
                # 避免一行坏索引让整个回放永久不可用。
                self._rebuild_event_index()
                rows, has_more = self._event_rows(query, parameters, limit)
                try:
                    events = self._event_page_entries(rows, limit)
                except ValueError:
                    raise ValueError("事件索引已损坏，事件回放暂不可用") from None
        return {"events": events,
                "nextCursor": str(rows[-1]["cursor"]) if rows else str(position), "hasMore": has_more}

    def _event_rows(self, query: str, parameters: list[Any], limit: int) -> tuple[list[sqlite3.Row], bool]:
        """读取一页事件索引行，返回 `(行, 是否还有更多)`。

        查询本身已带 `LIMIT limit+1`；这里额外按 `params_json` 原始字节预算
        逐行读取，避免一次取回 1000 条大事件后在锁内逐行解码。预算之外的行
        留给下一次翻页。首行即使超过预算也照常返回，保证游标总能推进。
        """
        rows: list[sqlite3.Row] = []
        raw_bytes = 0
        with self._index.connection() as connection:
            cursor = connection.execute(query, parameters)
            while True:
                row = cursor.fetchone()
                if row is None:
                    return rows, False
                if len(rows) >= limit:
                    return rows, True
                payload = row["params_json"]
                size = len(payload) if isinstance(payload, str) else 0
                if rows and raw_bytes + size > _EVENT_PAGE_RAW_BYTES:
                    return rows, True
                rows.append(row)
                raw_bytes += size

    @staticmethod
    def _event_page_entries(rows: list[sqlite3.Row], limit: int) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for row in rows[:limit]:
            try:
                params = json.loads(row["params_json"])
            except (TypeError, ValueError, RecursionError):
                # 深嵌套与非法 JSON 同样是索引损坏，不能逃逸成 -32603。
                raise ValueError("事件索引已损坏") from None
            if not isinstance(params, dict):
                raise ValueError("事件索引已损坏")
            # 索引行必须与它自己的游标列一致。params_json 被改写、缺 key 或指向别的游标时，
            # 按索引损坏处理走既有重建路径；否则 event/list 读取 params["eventCursor"]
            # 会抛 KeyError（-32603），重建重试永远不可达。
            if params.get("eventCursor") != str(row["cursor"]):
                raise ValueError("事件索引已损坏")
            # method 列同样来自持久库：外部可把它改写成 BLOB，返回帧随后在
            # wire_size / json.dumps 处抛 TypeError（-32603）。按索引损坏处理，
            # 由 events_after 的既有重建重试从 events.jsonl 恢复。
            if not isinstance(row["method"], str) or not row["method"]:
                raise ValueError("事件索引已损坏")
            entries.append({"method": row["method"], "params": params})
        return entries

    def _rebuild_event_index(self) -> None:
        with self._index.transaction() as connection:
            connection.execute("DELETE FROM checkpoints WHERE name='events'")
            self._index_events(connection)

    def latest_event_cursor(self) -> str:
        self._sync_events()
        with self._index.connection() as connection:
            maximum = connection.execute("SELECT COALESCE(MAX(cursor),0) FROM events").fetchone()[0]
        return str(maximum)
