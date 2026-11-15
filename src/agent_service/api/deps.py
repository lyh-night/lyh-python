"""FastAPI 依赖注入。"""

from typing import Annotated

from fastapi import Depends

from agent_service.agents.graph import AgentGraphs, get_agent_graphs
from agent_service.core.config import Settings, get_settings


def get_app_settings() -> Settings:
    """返回全局配置单例，供路由通过 Depends 注入。"""
    return get_settings()


# 路由签名直接写 ``settings: AppSettings`` / ``graphs: AgentGraphsDep`` 即可完成注入
AppSettings = Annotated[Settings, Depends(get_app_settings)]
AgentGraphsDep = Annotated[AgentGraphs, Depends(get_agent_graphs)]
