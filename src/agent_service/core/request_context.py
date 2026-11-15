"""请求级上下文（contextvar）：贯穿日志链路的请求 ID。"""

from contextvars import ContextVar, Token

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(value: str) -> Token[str]:
    """在当前请求上下文中设置请求 ID，返回 token 供复位。"""
    return _request_id.set(value)


def reset_request_id(token: Token[str]) -> None:
    """复位请求 ID，避免泄漏到线程池复用的其他请求。"""
    _request_id.reset(token)


def get_request_id() -> str:
    """读取当前请求 ID（无中间件上下文时为占位符）。"""
    return _request_id.get()
