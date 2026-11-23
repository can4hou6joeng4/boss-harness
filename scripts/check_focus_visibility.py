#!/usr/bin/env python3
"""核对移除默认焦点环的输入框都有容器级焦点替代。

搜索框与 Composer 为了统一外观会写 `outline: none`。一旦这样做，键盘
Tab 聚焦时浏览器默认焦点环消失；此时容器必须提供 `:focus-within` 的
边框或背景变化，否则界面没有任何可见反馈。这里固定四处输入与其容器
的对应关系，避免后续改样式时只删默认环、不加替代。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "apps/desktop/src/renderer/src/styles"
DOCS = "docs/TECHNICAL_REFERENCE.md"

INPUTS = (
    (".page-search input", ".page-search:focus-within"),
    (".search-field input", ".search-field:focus-within"),
    (".composer-menu-search input", ".composer-menu-search:focus-within"),
    (".composer-surface>textarea", ".composer-surface:focus-within"),
)


def _read_all() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(STYLES.glob("*.css"))
    )


def _rule_body(css: str, selector: str) -> str | None:
    pattern = re.compile(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}")
    match = pattern.search(css)
    return match.group(1) if match else None


def _focus_problems(css: str) -> list[str]:
    problems: list[str] = []
    for selector, container in INPUTS:
        bodies = [_rule_body(css, selector), _rule_body(css, selector + ":focus-visible")]
        if all(body is None for body in bodies):
            problems.append(f"缺少输入规则 {selector}")
            continue
        if not any(body is not None and "outline: none" in body for body in bodies):
            continue
        if f"{container} {{" not in css:
            problems.append(f"{selector} 移除了默认焦点环，但缺少 {container} 替代")
    return problems


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"焦点可见性变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_behaviors() -> int:
    sample = "\n".join(
        f"{selector} {{ border: 0; outline: none; }}\n{container} {{ border-color: red; }}"
        for selector, container in INPUTS
    )
    checked = 0
    checked += _expect_value(len(_focus_problems(sample)), 0, "干净样本")
    checked += _expect_value(
        len(_focus_problems(sample.replace(".page-search:focus-within { border-color: red; }\n", ""))),
        1, "缺少页面搜索容器焦点")
    checked += _expect_value(
        len(_focus_problems(sample.replace(
            ".search-field input { border: 0; outline: none; }",
            ".search-field input { border: 0; }"))),
        0, "保留默认焦点环时不要求容器")
    checked += _expect_value(
        len(_focus_problems(sample.replace(".search-field input { border: 0; outline: none; }\n", ""))),
        1, "缺少输入规则")
    return checked


def _check_documentation() -> int:
    docs = (ROOT / DOCS).read_text(encoding="utf-8")
    if "`check_focus_visibility.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_focus_visibility.py")
    if "共 8 项结构、4 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_focus_visibility.py 检查 8 项结构、4 项行为")
    return 2


def check_focus_visibility() -> tuple[int, int]:
    css = _read_all()
    problems = _focus_problems(css)
    if problems:
        raise ValueError("焦点可见性不一致：" + "；".join(problems))
    structure = len(INPUTS) * 2
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_focus_visibility()
    except (OSError, ValueError) as error:
        print(f"焦点可见性核对失败，{error}", file=sys.stderr)
        return 2
    print(f"焦点可见性一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
