"""对话接口的请求/响应模型，API 契约先行定义。"""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求。"""

    message: str = Field(..., min_length=1, description="用户输入的消息")
    thread_id: str | None = Field(default=None, description="会话线程 ID，传入则服务端续聊")


class ToolTrace(BaseModel):
    """单次工具调用轨迹。"""

    tool: str = Field(..., description="工具名称")
    args: dict[str, Any] = Field(default_factory=dict, description="调用参数")
    result: str = Field(default="", description="执行结果")


class Usage(BaseModel):
    """本次请求的 token 用量。"""

    total_tokens: int = 0


class ChatResponse(BaseModel):
    """对话响应。"""

    reply: str = Field(..., description="智能体最终回复")
    tool_trace: list[ToolTrace] = Field(default_factory=list, description="工具调用轨迹")
    usage: Usage = Field(default_factory=Usage, description="token 用量")
