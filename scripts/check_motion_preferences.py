#!/usr/bin/env python3
"""核对桌面动效偏好：全局减少动效块与三处局部媒体查询保持启用。

系统开启 `prefers-reduced-motion: reduce` 时，渲染层必须停止播放完整动效：
`tokens.css` 的全局块把过渡令牌降为近零，并强制动画与过渡时长、迭代次数与滚动行为；
popover / 登录侧栏 / tooltip 继续保留各自的局部媒体查询。这里扫描这些 CSS，防止全局块
或局部规则被删除。行为侧用合成 CSS 核对每条规则。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
TOKENS = "apps/desktop/src/renderer/src/styles/tokens.css"
LOCAL_FILES = (
    "apps/desktop/src/renderer/src/styles/popover.css",
    "apps/desktop/src/renderer/src/styles/login-sidebar.css",
    "apps/desktop/src/renderer/src/styles/tooltip.css",
)
MEDIA = re.compile(r"@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)")
GLOBAL_TOKENS = (
    "--transition-fast: 0.01s",
    "--transition-normal: 0.01s",
)
GLOBAL_PROPERTIES = (
    "animation-duration: 0.01ms",
    "animation-iteration-count: 1",
    "transition-duration: 0.01ms",
    "scroll-behavior: auto",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _global_problems(text: str) -> list[str]:
    found: list[str] = []
    match = MEDIA.search(text)
    if match is None:
        found.append(f"{TOKENS} 缺少 prefers-reduced-motion 全局块")
        return found
    block = text[match.start():]
    for snippet in GLOBAL_TOKENS + GLOBAL_PROPERTIES:
        if snippet not in block:
            found.append(f"{TOKENS} 的全局块缺少 {snippet}")
    return found


def _local_problems(relative: str, text: str) -> list[str]:
    if MEDIA.search(text) is None:
        return [f"{relative} 缺少 prefers-reduced-motion 媒体查询"]
    return []


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"动效偏好变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    problems = _global_problems(_read(TOKENS))
    for relative in LOCAL_FILES:
        problems += _local_problems(relative, _read(relative))
    if problems:
        raise ValueError("动效偏好变化：" + "；".join(problems))
    return 1 + len(GLOBAL_TOKENS) + len(GLOBAL_PROPERTIES) + len(LOCAL_FILES)


def _clean_tokens() -> str:
    return (
        ":root { --transition-fast: 0.15s ease; --transition-normal: 0.2s ease; }\n"
        "@media (prefers-reduced-motion: reduce) {\n"
        "  :root { --transition-fast: 0.01s; --transition-normal: 0.01s; }\n"
        "  *, *::before, *::after {\n"
        "    animation-duration: 0.01ms !important;\n"
        "    animation-iteration-count: 1 !important;\n"
        "    transition-duration: 0.01ms !important;\n"
        "    scroll-behavior: auto !important;\n"
        "  }\n"
        "}\n"
    )


def _clean_local() -> str:
    return ("@media (prefers-reduced-motion:reduce) {\n"
            "  .panel { animation: none; }\n"
            "}\n")


def _expect_count(found: int, expected: int, label: str) -> int:
    return _expect_value(found, expected, label)


def _check_behaviors() -> int:
    checked = 0
    checked += _expect_count(len(_global_problems(_clean_tokens())), 0, "干净令牌文件")
    checked += _expect_count(
        len(_global_problems(_clean_tokens().replace(
            "@media (prefers-reduced-motion: reduce)", "@media (min-width: 720px)"))),
        1, "缺少全局媒体查询")
    for snippet in GLOBAL_TOKENS + GLOBAL_PROPERTIES:
        checked += _expect_count(
            len(_global_problems(_clean_tokens().replace(snippet, ""))),
            1, f"缺少 {snippet}")
    checked += _expect_count(len(_local_problems("popover.css", _clean_local())), 0,
                             "干净局部样式")
    checked += _expect_count(
        len(_local_problems("popover.css", _clean_local().replace(
            "@media (prefers-reduced-motion:reduce)", "@media (min-width: 720px)"))),
        1, "缺少局部媒体查询")
    checked += _expect_count(
        len(_global_problems(_clean_tokens().replace(":root { --transition-fast", ":root { /* 令牌 */ --transition-fast"))),
        0, "无关注释调整")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_motion_preferences.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_motion_preferences.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少动效偏好检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"动效偏好一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
