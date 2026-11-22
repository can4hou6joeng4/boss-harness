#!/usr/bin/env python3
"""核对会话导出的默认脱敏、请求边界与脱敏行为。

静态扫描固定导出格式、字节上限、请求字段白名单、脱敏标记与管线顺序；行为对照直接
构造 Redactor 并调用敏感信息 / 个人信息 / 文本接口，核对凭据、环境变量、路径与候选人
信息的替换结果、计数以及路径延续、短文本与状态文本的边界。任一放宽都可能让本机数据进入
导出文件。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT_MODULE = "harness/src/boss_harness/session_export.py"
APPLICATION_MODULE = "harness/src/boss_harness/application.py"
SECURITY_MODULE = "apps/desktop/src/main/security.ts"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session_export import (  # noqa: E402
    ENV_MARK,
    MAX_PII_VALUES,
    MAX_TEXT_CHARS,
    PATH_MARK,
    PII_MARK,
    SECRET_MARK,
    Redactor,
    _continues_path,
    _known_paths,
    _known_secrets,
    _last_path_segment,
    _normalize_key,
    _path_end,
    _short_text,
    _status_text,
)
DESKTOP_EXPORT = re.compile(r"const EXPORT_MAX_BYTES = (\d+(?:\s*\*\s*\d+)*);")
DESKTOP_EXPORT_CHECK = 'Buffer.byteLength(value.content, "utf8") > EXPORT_MAX_BYTES'
EXPECTED_FORMATS = ("markdown", "json", "html")
REQUEST_BOUNDARY = (
    'if not set(params) <= {"threadId", "view", "format", "includeToolResults", "maxBytes"}:'
)
DEFAULT_REDACTION = 'include_tool_results=params.get("includeToolResults", False)'
REDACTION_FRAGMENTS = (
    "from boss_harness.models.secret import redact_secrets",
    'SECRET_MARK = "[已脱敏:凭据]"',
    'ENV_MARK = "[已脱敏:环境变量]"',
    'PATH_MARK = "[已脱敏:本机路径]"',
    'PII_MARK = "[已打码:候选人信息]"',
    "redact_secrets(",
)
PATH_SEGMENT_FRAGMENTS = (
    # 末段提取同时剥离两种分隔符，否则 Windows 路径的尾分隔符会把末段判为空。
    r'return re.split(r"[/\\]", value.rstrip("/\\"))[-1]',
)
FORBIDDEN_WRITES = (
    "write_text(",
    "write_bytes(",
    "open(",
    "os.replace(",
    "unlink(",
    "mkdir(",
)
SENSITIVE_PIPELINE = (
    "self.secrets = sorted({value for value in secrets if isinstance(value, str) and len(value) >= 6}",
    "self.paths = sorted({value.rstrip(\"/\\\\\") for value in paths",
    'self.counts = {"secrets": 0, "environment": 0, "paths": 0, "personalInfo": 0}',
    "if depth > 32 or len(self.pii_values) >= MAX_PII_VALUES:",
    "if _normalize_key(key) in _PII_KEYS:",
    "if 2 <= len(text) <= 4_000 and text not in self.pii_values:",
    "self.pii_values.sort(key=len, reverse=True)",
    "self.counts[counter] += count",
    'self.counts["paths"] += count',
    "if value in text:",
    'self.counts["secrets"] += text.count(value)',
    "text = text.replace(value, SECRET_MARK)",
    "scrubbed = redact_secrets(text)",
    'scrubbed.count("<redacted>")',
    'scrubbed.replace("<redacted>", SECRET_MARK)',
    "text = self._sub(_TOKEN_PATTERNS[0], SECRET_MARK, text, \"secrets\")",
    "text = self._sub(_TOKEN_PATTERNS[1],",
    "text = self._sub(_TOKEN_PATTERNS[2],",
    "text = self._sub(_KEY_PATTERN, SECRET_MARK, text, \"secrets\")",
    "text = self._sub(_URL_USERINFO,",
    "text = self._sub(_ENV_ASSIGNMENT,",
    "for pattern in self.path_patterns:",
    "text = self._sub_paths(_ABSOLUTE_PATH, text)",
    "text = self._sub_paths(_SINGLE_SEGMENT_PATH, text)",
    "return self._sub(_TOKEN_PATTERNS[3], SECRET_MARK, text, \"secrets\")",
    "for value in self.pii_values:",
    'self.counts["personalInfo"] += text.count(value)',
    "text = text.replace(value, PII_MARK)",
    "text = self._sub(_PII_PATTERNS[0], PII_MARK, text, \"personalInfo\")",
    "text = self._sub(_PII_PATTERNS[1], PII_MARK, text, \"personalInfo\")",
    "text = self._sub(_PII_PATTERNS[2], PII_MARK, text, \"personalInfo\")",
    "return self._sub(_PII_PATTERNS[3],",
    "return _clip(self.personal(self.sensitive(value)), limit)",
    "_PII_KEYS = frozenset({",
    "_PII_PATTERNS = (",
    "_TOKEN_PATTERNS = (",
    '_SENSITIVE_ENV = re.compile(r"(?i)(key|token|secret|password|passwd|cookie|auth|credential|session)")',
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _module_assignment(tree: ast.Module, name: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(
            isinstance(target, ast.Name) and target.id == name for target in targets
        ):
            return node.value
    raise ValueError(f"session_export.py 缺少 {name}")


def _int_constant(node: ast.AST, name: str) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _int_constant(node.left, name) * _int_constant(node.right, name)
    raise ValueError(f"session_export.py 的 {name} 必须是正整数常量表达式")


def _ts_product(literal: str) -> int:
    value = 1
    for part in literal.split("*"):
        value *= int(part.strip())
    return value


TOOL_PROJECTION = (
    '_SAFE_ARGUMENTS = frozenset({"keyword", "query", "page", "city", "salary", "experience", "education", "action"})',
    "MAX_SCRUB_DEPTH = 64",
    'DEPTH_MARK = "[嵌套层级超出显示上限]"',
    'if _depth > MAX_SCRUB_DEPTH:',
    "for key, value in list(arguments.items())[:40]:",
    "name = str(key)[:64]",
    "elif key in _SAFE_ARGUMENTS and (isinstance(value, (int, float, bool)) or value is None",
    'out[name] = f"{OMITTED}（{_describe_value(value)}）"',
    "return self._scrub_json(out, personal=not self.include)",
    'redactor.collect_personal(result.get("data"))',
    'redactor.collect_personal(result.get("error"))',
    'redactor.collect_personal(item.get("toolArguments"))',
    'if self.include:',
    'text = json.dumps(self._scrub_json(body, personal=False), ensure_ascii=False, indent=2,',
    'unit["result"] = {"included": True, "text": _clip(text, MAX_RESULT_CHARS)}',
    '"data": _structure(result.get("data"), self.redactor),',
    '"pagination": _pagination(result.get("pagination")),',
    '"hintCount": len(result["hints"]) if isinstance(result.get("hints"), list) else 0,',
    "return _wire_bytes(render(meta, units[:count], counts, len(units), max_bytes, queue))",
    "if size(keep) > max_bytes:",
    "if size(middle) <= max_bytes:",
    'raise ValueError("会话导出头部超出大小上限")',
    'extension = {"markdown": "md", "json": "json", "html": "html"}[fmt]',
)


def _check_tool_projection(tree: ast.Module, source: str) -> int:
    missing = [fragment for fragment in TOOL_PROJECTION if fragment not in source]
    if missing:
        raise ValueError("会话导出工具数据边界缺少：" + "、".join(missing))
    arguments = _method_source(tree, source, "_arguments")
    safe = arguments.find("elif key in _SAFE_ARGUMENTS")
    omitted = arguments.find('out[name] = f"{OMITTED}')
    if safe < 0 or omitted < 0 or safe > omitted:
        raise ValueError("_arguments() 必须先在安全白名单外以省略摘要替代")
    scrub = _method_source(tree, source, "_scrub_json")
    depth = scrub.find("if _depth > MAX_SCRUB_DEPTH:")
    for fragment in ("self.redactor.sensitive(value)", "self.redactor.personal(text) if personal else text"):
        position = scrub.find(fragment)
        if position < 0 or (depth >= 0 and position < depth):
            raise ValueError("_scrub_json() 必须先检查递归上限再脱敏字符串")
    tool = _method_source(tree, source, "_tool")
    included = tool.find('unit["result"] = {"included": True')
    structured = tool.find('"data": _structure(result.get("data"), self.redactor),')
    if included < 0 or structured < 0 or included > structured:
        raise ValueError("_tool() 的默认分支必须只导出结构与状态")
    return len(TOOL_PROJECTION) + 3


def _method_source(tree: ast.Module, source: str, method_name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"session_export.py 缺少 Redactor.{method_name}")


def _ordered_steps(body: str, steps: tuple[str, ...], name: str) -> None:
    positions = [body.find(fragment) for fragment in steps]
    missing = [fragment for fragment, position in zip(steps, positions) if position < 0]
    if missing:
        raise ValueError(f"{name} 缺少脱敏步骤：" + "、".join(missing))
    if positions != sorted(positions):
        raise ValueError(f"{name} 的脱敏步骤顺序被改变")


def _check_sensitive_pipeline(tree: ast.Module, source: str) -> int:
    _ordered_steps(_method_source(tree, source, "sensitive"), (
        "if value in text:",
        "scrubbed = redact_secrets(text)",
        "text = self._sub(_TOKEN_PATTERNS[0],",
        "text = self._sub(_ENV_ASSIGNMENT,",
        "for pattern in self.path_patterns:",
        "text = self._sub_paths(_ABSOLUTE_PATH, text)",
        "return self._sub(_TOKEN_PATTERNS[3],",
    ), "sensitive()")
    _ordered_steps(_method_source(tree, source, "personal"), (
        "for value in self.pii_values:",
        "text = text.replace(value, PII_MARK)",
        "text = self._sub(_PII_PATTERNS[0],",
        "return self._sub(_PII_PATTERNS[3],",
    ), "personal()")
    missing = [fragment for fragment in SENSITIVE_PIPELINE if fragment not in source]
    if missing:
        raise ValueError("会话导出脱敏管线缺少：" + "、".join(missing))
    return len(SENSITIVE_PIPELINE) + 2


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"会话导出隐私行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _known_secrets_check() -> int:
    token_name = "BOSS_HARNESS_PROBE_TOKEN"
    label_name = "BOSS_HARNESS_PROBE_LABEL"
    previous = {name: os.environ.get(name) for name in (token_name, label_name)}
    try:
        os.environ[token_name] = "probe-token-value"
        os.environ[label_name] = "probe-label-value"
        values = _known_secrets(["explicit-value", ""])
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    checked = _expect_value("explicit-value" in values, True, "显式凭据保留")
    checked += _expect_value("" in values, False, "空凭据忽略")
    checked += _expect_value("probe-token-value" in values, True, "环境凭据收集")
    checked += _expect_value("probe-label-value" in values, False, "非敏感环境忽略")
    return checked


def _known_paths_check() -> int:
    values = _known_paths(["/tmp/session-export-probe", ""])
    checked = _expect_value("/tmp/session-export-probe" in values, True, "显式路径保留")
    checked += _expect_value("" in values, False, "空路径忽略")
    checked += _expect_value(str(Path.home()) in values, True, "主目录路径收集")
    return checked


def _behavior_checks() -> int:
    checked = 0

    redactor = Redactor(secrets=["abcdef", "abcde", 5, None, "abcdef", "abcdefgh"], paths=[])
    checked += _expect_value(redactor.secrets, ["abcdefgh", "abcdef"], "凭据归一化")
    redactor = Redactor(secrets=[], paths=["/Users/x/", "/Users/x", "/a/", "", 3])
    checked += _expect_value(redactor.paths, ["/Users/x", "/a"], "路径归一化")
    checked += _expect_value(
        redactor.counts,
        {"secrets": 0, "environment": 0, "paths": 0, "personalInfo": 0}, "计数初值")
    checked += _expect_value(redactor.pii_values, [], "个人信息初值")

    redactor = Redactor(secrets=["secret-token"], paths=[])
    checked += _expect_value(
        redactor.sensitive("a secret-token b secret-token"),
        f"a {SECRET_MARK} b {SECRET_MARK}", "已知凭据替换")
    checked += _expect_value(redactor.counts["secrets"], 2, "已知凭据计数")

    redactor = Redactor(secrets=["abc"], paths=[])
    checked += _expect_value(redactor.sensitive("abc"), "abc", "短凭据忽略")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("Authorization: Bearer abc12345"),
        f"Authorization: {SECRET_MARK}", "Bearer 头")
    checked += _expect_value(redactor.counts["secrets"], 2, "Bearer 头计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("Cookie: session=abc123; theme=dark"),
        f"Cookie: {SECRET_MARK}", "Cookie 头")
    checked += _expect_value(redactor.counts["secrets"], 1, "Cookie 头计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("key sk-abcdefgh1234 end"),
        f"key {SECRET_MARK} end", "sk 前缀")
    checked += _expect_value(redactor.counts["secrets"], 1, "sk 前缀计数")

    redactor = Redactor(secrets=[], paths=[])
    # 运行时拼出测试用 JWT 形态，避免仓库里出现可被密钥扫描误判的完整令牌字面量。
    jwt = ".".join(("e" + "yJhbGciOiJIUzI1NiJ9", "e" + "yJzdWIiOiIxMjM0NTY3ODkwIn0",
                    "c2lnbmF0dXJl"))
    checked += _expect_value(
        redactor.sensitive(f"jwt {jwt} end"), f"jwt {SECRET_MARK} end", "JWT")
    checked += _expect_value(redactor.counts["secrets"], 1, "JWT 计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("__zp_token=abc123def; x=1"),
        f"__zp_token={SECRET_MARK}; x=1", "招聘 Cookie")
    checked += _expect_value(redactor.counts["secrets"], 1, "招聘 Cookie 计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("value " + "A1" * 20 + " end"),
        f"value {SECRET_MARK} end", "长 token")
    checked += _expect_value(redactor.counts["secrets"], 1, "长 token 计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("https://user:pass@example.test/x"),
        f"https://{SECRET_MARK}@example.test/x", "URL 用户信息")
    checked += _expect_value(redactor.counts["secrets"], 1, "URL 用户信息计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("REGION=us-east-1"), f"REGION={ENV_MARK}", "环境变量赋值")
    checked += _expect_value(redactor.counts["environment"], 1, "环境变量计数")
    checked += _expect_value(redactor.counts["secrets"], 0, "环境变量不计凭据")

    redactor = Redactor(secrets=[], paths=["/Users/alice/secret"])
    checked += _expect_value(
        redactor.sensitive("见 /Users/alice/secret/resume.pdf 完"),
        f"见 {PATH_MARK} 完", "已知路径尾段")
    checked += _expect_value(redactor.counts["paths"], 1, "已知路径计数")

    redactor = Redactor(secrets=[], paths=["/Users/alice/My Documents"])
    checked += _expect_value(
        redactor.sensitive("/Users/alice/My Documents/file.pdf"),
        PATH_MARK, "含空格已知路径")

    redactor = Redactor(secrets=[], paths=["/Users/alice/secret"])
    checked += _expect_value(
        redactor.sensitive("目录 /Users/alice/secret"), f"目录 {PATH_MARK}", "已知路径本身")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("打开 /Users/unknown/Documents/report.pdf"),
        f"打开 {PATH_MARK}", "通用绝对路径")
    checked += _expect_value(redactor.counts["paths"], 1, "通用绝对路径计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("/Users/unknown/Job Search/resume.pdf"),
        PATH_MARK, "空格延续路径")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("/Users/unknown/Job search notes"),
        f"{PATH_MARK} search notes", "正文不吞并")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("配置见/etc。"), f"配置见{PATH_MARK}。", "单段根路径")
    checked += _expect_value(redactor.sensitive("/help 可用"), "/help 可用", "正文斜杠词")
    checked += _expect_value(redactor.counts["paths"], 1, "正文斜杠词不计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("C:\\Users\\bob\\file.txt"), PATH_MARK, "Windows 路径")
    checked += _expect_value(redactor.counts["paths"], 1, "Windows 路径计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive(r"\\server\share\file.txt"), PATH_MARK, "UNC 路径")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("file:///Users/bob/x.txt"), PATH_MARK, "file URL")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.sensitive("/Users/x/report.pdf。请查收"),
        f"{PATH_MARK}。请查收", "路径后接正文")

    redactor = Redactor(secrets=[], paths=[])
    redactor.collect_personal({"data": {
        "name": "张三", "mobile_phone": "13900139000",
        "Geek_Name": "李四", "email": "a@b.co"}})
    redactor.finalize()
    checked += _expect_value(
        redactor.pii_values, ["13900139000", "a@b.co", "张三", "李四"], "个人信息收集")

    redactor = Redactor(secrets=[], paths=[])
    redactor.collect_personal({"name": True, "geek_name": "张",
                               "realname": " 王五 ", "nickname": "王五"})
    redactor.finalize()
    checked += _expect_value(redactor.pii_values, ["王五"], "个人信息值边界")

    redactor = Redactor(secrets=[], paths=[])
    redactor.collect_personal({"phone": 13800138000, "wechat": 1.5})
    redactor.finalize()
    checked += _expect_value(redactor.pii_values, ["13800138000", "1.5"], "数值个人信息")

    redactor = Redactor(secrets=[], paths=[])
    redactor.collect_personal({"name": "x" * 4_000})
    redactor.collect_personal({"name": "x" * 4_001})
    checked += _expect_value(
        [len(value) for value in redactor.pii_values], [4_000], "个人信息长度上限")

    redactor = Redactor(secrets=[], paths=[])
    redactor.collect_personal({"name": "张三"}, depth=33)
    checked += _expect_value(redactor.pii_values, [], "个人信息深度上限")

    redactor = Redactor(secrets=[], paths=[])
    for index in range(MAX_PII_VALUES + 1):
        redactor.collect_personal({"name": f"v{index:04d}"})
    checked += _expect_value(len(redactor.pii_values), MAX_PII_VALUES, "个人信息总量上限")
    checked += _expect_value("v3999" in redactor.pii_values, True, "上限内保留")
    checked += _expect_value("v4000" in redactor.pii_values, False, "上限外丢弃")

    redactor = Redactor(secrets=[], paths=[])
    redactor.collect_personal({"name": "张三"})
    redactor.collect_personal({"name": "张三丰"})
    redactor.finalize()
    checked += _expect_value(
        redactor.personal("张三丰 的简历"), f"{PII_MARK} 的简历", "长值优先")
    checked += _expect_value(redactor.counts["personalInfo"], 1, "长值优先计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.personal("联系 a.b+c@example.co 谢谢"),
        f"联系 {PII_MARK} 谢谢", "邮箱")
    checked += _expect_value(redactor.personal("+86 138-0013-8000"), PII_MARK, "手机号区号")
    checked += _expect_value(
        redactor.personal("电话 138 0013 8000"), f"电话 {PII_MARK}", "手机号空格")
    checked += _expect_value(
        redactor.personal("身份证 110101199003071234 完"),
        f"身份证 {PII_MARK} 完", "身份证号")
    checked += _expect_value(
        redactor.personal("微信号：abc_12345"), f"微信号：{PII_MARK}", "微信号")
    checked += _expect_value(redactor.counts["personalInfo"], 5, "个人信息计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(redactor.text(None), "", "空值文本")
    checked += _expect_value(redactor.text(123), "", "数值文本")

    redactor = Redactor(secrets=[], paths=[])
    redactor.collect_personal({"name": "张三"})
    redactor.finalize()
    checked += _expect_value(
        redactor.text("张三 联系 a@b.co，sk-abcdefgh1234"),
        f"{PII_MARK} 联系 {PII_MARK}，{SECRET_MARK}", "文本组合管线")
    checked += _expect_value(redactor.counts["secrets"], 1, "文本组合凭据计数")
    checked += _expect_value(redactor.counts["personalInfo"], 2, "文本组合个人信息计数")

    redactor = Redactor(secrets=[], paths=[])
    checked += _expect_value(
        redactor.text("x" * 20, limit=10),
        "x" * 10 + "\n…（本段已截断：原长 20 字符，仅保留前 10 字符）", "文本截断")
    checked += _expect_value(redactor.text("x" * 10, limit=10), "x" * 10, "截断边界")

    redactor = Redactor(secrets=[], paths=[])
    clipped = redactor.text("y" * (MAX_TEXT_CHARS + 1))
    checked += _expect_value(
        (clipped.startswith("y" * MAX_TEXT_CHARS),
         clipped.endswith(
             f"原长 {MAX_TEXT_CHARS + 1} 字符，仅保留前 {MAX_TEXT_CHARS} 字符）")),
        (True, True), "默认截断上限")

    checked += _expect_value(
        (_continues_path("resume.pdf", previous_upper=False),
         _continues_path("文件.txt", previous_upper=False),
         _continues_path("x/y", previous_upper=False),
         _continues_path("Search", previous_upper=True),
         _continues_path("search", previous_upper=True),
         _continues_path("Search", previous_upper=False)),
        (True, True, True, True, False, False), "路径延续判定")

    checked += _expect_value(
        (_last_path_segment("/Users/Alice/resume.pdf"),
         _last_path_segment("/Users/Alice/"),
         _last_path_segment("resume.pdf")),
        ("resume.pdf", "Alice", "resume.pdf"), "POSIX 末段")
    checked += _expect_value(
        (_last_path_segment("C:\\Users\\Alice\\resume.pdf"),
         _last_path_segment("C:\\Users\\Alice\\"),
         _last_path_segment("a/b\\c")),
        ("resume.pdf", "Alice", "c"), "Windows 末段")
    checked += _expect_value(
        (_last_path_segment("/"), _last_path_segment("//"), _last_path_segment(""),
         _last_path_segment("C:\\")),
        ("", "", "", "C:"), "退化末段")

    checked += _expect_value(
        _path_end("/etc 只是单段根", 0, 4), 4, "路径正文停止")
    continued = "/tmp/a" + "".join(f" /x{index}" for index in range(10))
    checked += _expect_value(_path_end(continued, 0, 6), 6 + 8 * 4, "路径续接上限")

    checked += _expect_value(
        (_short_text("abc", 5), _short_text("", 5), _short_text("abcdef", 5),
         _short_text(5, 5), _short_text("ab", 2)),
        ("abc", None, None, None, "ab"), "短文本边界")

    checked += _expect_value(
        (_status_text("ok", default="missing"), _status_text(None, default="missing"),
         _status_text("", default="missing"), _status_text("x" * 65, default="missing"),
         _status_text("x" * 64, default="missing")),
        ("ok", "missing", "unknown", "unknown", "x" * 64), "状态文本边界")

    checked += _expect_value(
        (_normalize_key("Geek_Name"), _normalize_key("手机 号"),
         _normalize_key("EMAIL"), _normalize_key(5)),
        ("geekname", "手机号", "email", "5"), "字段归一化")

    checked += _known_secrets_check()
    checked += _known_paths_check()
    return checked


def check_export_privacy() -> int:
    export_text = _read(EXPORT_MODULE)
    application_text = _read(APPLICATION_MODULE)
    security_text = _read(SECURITY_MODULE)
    tree = ast.parse(export_text, filename=EXPORT_MODULE)
    formats = _module_assignment(tree, "EXPORT_FORMATS")
    values = (
        tuple(
            item.value
            for item in formats.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        )
        if isinstance(formats, ast.Tuple)
        else ()
    )
    if (
        not isinstance(formats, ast.Tuple)
        or len(formats.elts) != len(EXPECTED_FORMATS)
        or values != EXPECTED_FORMATS
    ):
        raise ValueError(
            "session_export.py 的 EXPORT_FORMATS 应恰为 markdown / json / html"
        )
    minimum = _int_constant(
        _module_assignment(tree, "MIN_EXPORT_BYTES"), "MIN_EXPORT_BYTES"
    )
    default = _int_constant(
        _module_assignment(tree, "DEFAULT_EXPORT_BYTES"), "DEFAULT_EXPORT_BYTES"
    )
    maximum = _int_constant(
        _module_assignment(tree, "MAX_EXPORT_BYTES"), "MAX_EXPORT_BYTES"
    )
    if not minimum <= default <= maximum:
        raise ValueError(
            "会话导出字节上限必须满足 MIN_EXPORT_BYTES ≤ DEFAULT_EXPORT_BYTES ≤ MAX_EXPORT_BYTES"
        )
    if maximum >= 1024 * 1024:
        raise ValueError("会话导出 MAX_EXPORT_BYTES 必须低于传输单页上限 1 MiB")
    desktop_cap = DESKTOP_EXPORT.search(security_text)
    if desktop_cap is None:
        raise ValueError("security.ts 缺少 EXPORT_MAX_BYTES")
    desktop_maximum = _ts_product(desktop_cap.group(1))
    if desktop_maximum != maximum:
        raise ValueError(
            f"主进程 EXPORT_MAX_BYTES {desktop_maximum} 与内核 MAX_EXPORT_BYTES {maximum} 不一致"
        )
    if DESKTOP_EXPORT_CHECK not in security_text:
        raise ValueError("security.ts 必须按 UTF-8 字节数核对导出正文上限")
    if REQUEST_BOUNDARY not in application_text:
        raise ValueError("thread/export 的请求字段白名单缺失或被改动")
    if DEFAULT_REDACTION not in application_text:
        raise ValueError("thread/export 的 includeToolResults 必须默认 False")
    missing = [
        fragment for fragment in REDACTION_FRAGMENTS if fragment not in export_text
    ]
    if missing:
        raise ValueError("会话导出缺少脱敏标记或调用：" + "、".join(missing))
    missing = [
        fragment for fragment in PATH_SEGMENT_FRAGMENTS if fragment not in export_text
    ]
    if missing:
        raise ValueError("路径末段提取缺少分隔符处理：" + "、".join(missing))
    writes = [token for token in FORBIDDEN_WRITES if token in export_text]
    if writes:
        raise ValueError("session_export.py 不得触碰目标文件：" + "、".join(writes))
    pipeline = _check_sensitive_pipeline(tree, export_text)
    tool = _check_tool_projection(tree, export_text)
    behavior = _behavior_checks()
    return 7 + len(PATH_SEGMENT_FRAGMENTS) + pipeline + tool + behavior


def main() -> int:
    try:
        guards = check_export_privacy()
    except (OSError, SyntaxError, ValueError) as error:
        print(f"会话导出隐私边界核对失败，{error}", file=sys.stderr)
        return 2
    print(
        "会话导出隐私边界一致：3 种格式、请求字段与默认脱敏、"
        f"4 个脱敏标记、字节上限有序且低于 1 MiB 并与主进程一致、脱敏管线顺序、"
        f"工具数据边界、导出模块不写盘与脱敏行为对照（{guards} 项）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
