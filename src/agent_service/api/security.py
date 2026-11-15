"""API 安全：静态 Bearer 鉴权与进程内限流（P0-3 / P1 修复）。

- ``api_auth_token`` 为空时鉴权关闭（仅限本地开发，启动时会打 WARNING）；
  配置后要求请求头 ``Authorization: Bearer <token>``。
- 限流为单实例内存实现，多实例部署需换外部存储（见 core/rate_limit.py）。
"""

import secrets

from fastapi import HTTPException, Request, status

from agent_service.api.deps import AppSettings
from agent_service.core.rate_limit import RATE_LIMITER


def _client_identity(request: Request) -> str:
    """限流维度：优先取客户端 IP，缺失时退化为固定占位符。"""
    return request.client.host if request.client else "unknown"


def require_api_key(request: Request, settings: AppSettings) -> None:
    """校验 Authorization: Bearer <token>；未配置 token 时直接放行。"""
    token = settings.api_auth_token
    if not token:
        return
    scheme, _, credential = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key，请携带 Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not secrets.compare_digest(credential, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 无效",
            headers={"WWW-Authenticate": "Bearer"},
        )


def enforce_rate_limit(request: Request, settings: AppSettings) -> None:
    """对对话接口做每分钟请求数限制，超限返回 429。"""
    ok = RATE_LIMITER.check(_client_identity(request), settings.rate_limit_per_minute)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后重试",
        )
