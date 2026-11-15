"""工具注册中心：所有智能体可调用的工具在此集中注册。

约定：M3 接入核心后，新工具只需在 ``builtin.py`` 编写 ``@tool`` 函数
并调用 ``register_tool`` 注册，其余模块零改动。
"""

from typing import Any

TOOL_REGISTRY: dict[str, Any] = {}


def register_tool(name: str, tool: Any) -> None:
    """注册一个工具，重名注册会覆盖旧实现。"""
    TOOL_REGISTRY[name] = tool


def get_tool(name: str) -> Any:
    """按名称取工具，未注册返回 None。"""
    return TOOL_REGISTRY.get(name)


def get_tools() -> list[Any]:
    """返回全部已注册工具（保持注册顺序）。"""
    return list(TOOL_REGISTRY.values())


def get_tool_names() -> list[str]:
    """返回全部已注册工具名称（保持注册顺序）。"""
    return list(TOOL_REGISTRY.keys())
