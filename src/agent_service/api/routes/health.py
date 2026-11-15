"""健康检查路由。"""

from fastapi import APIRouter

from agent_service.api.deps import AppSettings

router = APIRouter(tags=["system"])


@router.get("/health")
def health(settings: AppSettings) -> dict[str, str]:
    """存活探针：返回服务状态与版本。"""
    return {"status": "ok", "version": settings.app_version}
