"""Recruitment command conveniences, outside the generic execution kernel."""
from __future__ import annotations

from typing import Any

_READ_ONLY_COMMANDS: dict[str, tuple[str, str]] = {
    "/tools": ("boss_list_tools", "上游能力目录"),
    "/status": ("boss_status", "账号与连接健康度"),
    "/stats": ("boss_stats", "招聘与转化漏斗"),
    "/recommend": ("boss_recommend", "职位推荐"),
    "/jobs": ("boss_hr_jobs", "已发布职位"),
    "/chat": ("boss_hr_chat", "沟通消息"),
    "/candidates": ("boss_hr_candidates", "候选人搜索"),
}


def _parse_command(stripped: str) -> tuple[str, str]:
    parts = stripped.split(maxsplit=1)
    if not parts:
        return "", ""
    return parts[0], parts[1].strip() if len(parts) > 1 else ""


def offline_reply(runner: Any, thread_id: str, text: str) -> str:
    command, argument = _parse_command(text.strip())
    if command == "/search":
        # 不带关键词时不替用户选定检索词：默认值会发起一次用户没有要求的
        # 平台检索，并把无关结果写进会话。只提示补全，不调用业务 CLI。
        if not argument:
            return "请提供检索关键词，例如 `/search Python`。未发出检索，也不会使用默认关键词。"
        result = runner.execute_tool(thread_id, "boss_search", {"keyword": argument})
        return f"检索「{argument}」：\n{result.content}"
    entry = _READ_ONLY_COMMANDS.get(command)
    if entry is not None:
        tool_name, title = entry
        arguments: dict[str, Any] = {"query": argument} if command == "/candidates" and argument else {}
        result = runner.execute_tool(thread_id, tool_name, arguments)
        return f"{title}：\n{result.content}"
    if not runner.tool_bridge.available():
        return "内核已连通，但未找到可用的 boss 可执行文件，领域工具暂不可用。"
    return "当前未配置模型。可以使用 /tools、/status、/stats 等只读指令，或配置模型后继续任务。"
