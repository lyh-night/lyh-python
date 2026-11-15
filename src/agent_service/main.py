"""FastAPI 应用入口。"""

from fastapi import FastAPI

from agent_service.api.routes import chat, health
from agent_service.core.config import Settings, get_settings
from agent_service.core.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    settings = settings or get_settings()
    setup_logging(settings)

    app = FastAPI(
        title="Agent Service",
        description="基于 Python + FastAPI + LangGraph 的对话智能体服务",
        version=settings.app_version,
    )
    app.include_router(health.router)
    app.include_router(chat.router)
    return app


app = create_app()
