"""内置工具集：新增工具只需编写 ``@tool`` 函数并加入 ``BUILTIN_TOOLS``。"""

import ast
import ipaddress
import operator
import socket
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from langchain_core.tools import BaseTool, tool

from agent_service.core.config import get_settings
from agent_service.tools.registry import register_tool

# ---- get_current_time ----


@tool
def get_current_time() -> str:
    """获取当前时间（时区由 APP_TIMEZONE 配置，默认北京时间）。"""
    return datetime.now(ZoneInfo(get_settings().app_timezone)).strftime("%Y-%m-%d %H:%M:%S %Z")


# ---- calculator（基于 ast 的安全求值，禁用 eval）----

_ALLOWED_BINOPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_MAX_EXPONENT = 1000


def _safe_eval(node: ast.AST) -> int | float:
    """递归求值白名单 AST 节点，其余一律拒绝。"""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, bool):  # bool 是 int 子类，显式排除
            raise ValueError("不支持布尔字面量")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError(f"指数过大（|指数| 不得超过 {_MAX_EXPONENT}）")
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_eval(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    raise ValueError(f"不支持的表达式元素: {type(node).__name__}")


@tool
def calculator(expression: str) -> str:
    """计算四则运算表达式，支持 + - * / // % ** 与括号，例如 (1+2)*3。"""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as exc:
        return f"计算失败: {exc}"
    return f"{expression} = {result}"


# ---- http_get（限协议/公网地址/超时/大小，供智能体检索网页文本）----

_HTTP_TIMEOUT_SECONDS = 10.0
_HTTP_MAX_BYTES = 1_000_000
_HTTP_MAX_CHARS = 4000
_HTTP_MAX_REDIRECTS = 5
_HTTP_USER_AGENT = "agent-service/0.1"

# 测试接缝：单测可注入 httpx.MockTransport，正常运行恒为 None
_HTTP_TRANSPORT: httpx.BaseTransport | None = None


def _assert_public_host(url: str) -> None:
    """解析 URL 主机并拒绝所有非公网地址（防 SSRF：环回/私网/链路本地/保留段）。"""
    host = urlparse(url).hostname
    if not host:
        raise ValueError("无法解析主机名")
    try:
        addrinfos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValueError(f"域名解析失败: {host}") from exc
    for info in addrinfos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(f"禁止访问非公网地址: {ip}")


@tool
def http_get(url: str) -> str:
    """抓取指定 URL 的文本内容。仅支持 http/https 公网地址，超时 10 秒，超出部分截断。"""
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        return "抓取失败: 仅支持 http/https 协议"
    try:
        text = _fetch_text(url)
    except (httpx.HTTPError, ValueError) as exc:
        return f"抓取失败: {exc}"
    return text[:_HTTP_MAX_CHARS]


def _fetch_text(url: str) -> str:
    """手动跟随重定向（有上限），每一跳都重新做 SSRF 校验。"""
    current = url
    with httpx.Client(
        timeout=_HTTP_TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=_HTTP_TRANSPORT,
        headers={"User-Agent": _HTTP_USER_AGENT},
    ) as client:
        for _ in range(_HTTP_MAX_REDIRECTS):
            _assert_public_host(current)
            response = client.get(current)
            if response.is_redirect:
                if response.next_request is None:
                    raise ValueError("重定向缺少 Location 头")
                current = str(response.next_request.url)
                continue
            response.raise_for_status()
            break
        else:
            raise ValueError(f"重定向超过 {_HTTP_MAX_REDIRECTS} 次")
    truncated = len(response.content) > _HTTP_MAX_BYTES
    text = response.content[:_HTTP_MAX_BYTES].decode(response.encoding or "utf-8", errors="replace")
    if truncated:
        text += "\n…[响应超过 1MB，已截断]"
    return text


# ---- 注册 ----

BUILTIN_TOOLS: list[BaseTool] = [get_current_time, calculator, http_get]


def register_builtin_tools() -> None:
    """将全部内置工具注册到注册中心（幂等，重名覆盖）。"""
    for tool_instance in BUILTIN_TOOLS:
        register_tool(tool_instance.name, tool_instance)
