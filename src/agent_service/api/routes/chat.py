"""对话路由（桩）：智能体核心实现后接入。"""

from fastapi import APIRouter, HTTPException, status

from agent_service.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """与智能体对话（核心待实现，当前仅提供契约）。"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="智能体核心尚未实现（M3 里程碑），当前仅提供接口契约。",
    )
