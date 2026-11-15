"""FastAPI 应用入口。"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent_service.api.routes import chat, health
from agent_service.core.config import Settings, get_settings
from agent_service.core.errors import (
    AgentExecutionError,
    AgentRecursionError,
    LLMNotConfiguredError,
)
from agent_service.core.logging import setup_logging
from agent_service.core.request_context import (
    get_request_id,
    reset_request_id,
    set_request_id,
)
from agent_service.tools.builtin import register_builtin_tools

logger = logging.getLogger(__name__)


def _llm_not_configured_handler(request: Request, exc: Exception) -> JSONResponse:
    """LLM 未配置：503，服务不可用但配置后即可恢复。"""
    logger.warning("llm not configured rid=%s", get_request_id())
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def _agent_execution_handler(request: Request, exc: Exception) -> JSONResponse:
    """智能体执行失败（LLM 网络/超时等上游错误）：502，原始异常已在路由层记录。"""
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def _agent_recursion_handler(request: Request, exc: Exception) -> JSONResponse:
    """Agent 循环超出递归上限：500，任务可能过于复杂。"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Agent 执行超出递归上限，任务可能过于复杂，请简化问题后重试"},
    )


def _register_middleware(app: FastAPI) -> None:
    """请求上下文中间件：注入/透传 X-Request-ID，输出访问日志。"""

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = set_request_id(request_id)
        start = time.perf_counter()

        def _log(status_code: object) -> None:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "%s %s -> %s rid=%s %.1fms",
                request.method,
                request.url.path,
                status_code,
                request_id,
                elapsed_ms,
            )

        try:
            response = await call_next(request)
        except Exception:
            _log("ERR")
            reset_request_id(token)
            raise
        _log(response.status_code)
        reset_request_id(token)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    settings = settings or get_settings()
    setup_logging(settings)
    register_builtin_tools()

    if not settings.api_auth_token:
        logger.warning("API_AUTH_TOKEN 未配置，鉴权已关闭（仅限本地开发环境使用）")

    app = FastAPI(
        title="Agent Service",
        description="基于 Python + FastAPI + LangGraph 的对话智能体服务",
        version=settings.app_version,
    )
    app.include_router(health.router)
    app.include_router(chat.router)
    _register_middleware(app)

    app.add_exception_handler(LLMNotConfiguredError, _llm_not_configured_handler)
    app.add_exception_handler(AgentExecutionError, _agent_execution_handler)
    app.add_exception_handler(AgentRecursionError, _agent_recursion_handler)
    return app


app = create_app()
