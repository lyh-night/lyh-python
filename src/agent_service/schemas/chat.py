"""对话接口的请求/响应模型，API 契约先行定义。"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """对话请求。"""

    message: str = Field(..., min_length=1, description="用户输入的消息")
    thread_id: str | None = Field(default=None, description="会话线程 ID，传入则服务端续聊")

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        """去除首尾空白，全空白视为非法输入。"""
        value = value.strip()
        if not value:
            raise ValueError("message 不能为空")
        return value


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
    thread_id: str = Field(..., description="本次会话线程 ID（回显，客户端可复用于续聊）")
    tool_trace: list[ToolTrace] = Field(default_factory=list, description="工具调用轨迹")
    usage: Usage = Field(default_factory=Usage, description="token 用量")


class ToolInfo(BaseModel):
    """单个工具的公开信息。"""

    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")


class ToolListResponse(BaseModel):
    """工具清单响应。"""

    tools: list[ToolInfo] = Field(default_factory=list)
