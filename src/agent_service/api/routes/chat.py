"""对话路由：POST /api/v1/chat 与工具清单 GET /api/v1/tools。"""

import logging
import uuid
from typing import Any, NamedTuple

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from agent_service.api.deps import AgentGraphsDep, AppSettings
from agent_service.api.security import enforce_rate_limit, require_api_key
from agent_service.core.errors import AgentExecutionError, AgentRecursionError
from agent_service.core.request_context import get_request_id
from agent_service.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ToolInfo,
    ToolListResponse,
    ToolTrace,
    Usage,
)
from agent_service.tools.registry import get_tools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

_UPSTREAM_UNAVAILABLE = "上游模型暂时不可用，请稍后重试"


class _PendingCall(NamedTuple):
    """一次待配对的模型工具调用。"""

    name: str
    args: dict[str, Any]


def _final_reply(messages: list[AnyMessage]) -> str:
    """取最后一条不含 tool_calls 的模型消息作为最终回答。"""
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            return str(message.content)
    return ""


def _build_tool_trace(messages: list[AnyMessage]) -> list[ToolTrace]:
    """扫描消息序列，按 tool_call_id 配对还原每次工具调用的名称/参数/结果。"""
    traces: list[ToolTrace] = []
    pending: dict[str, _PendingCall] = {}
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                call_id = call["id"]
                if isinstance(call_id, str):
                    pending[call_id] = _PendingCall(
                        name=str(call["name"]), args=call.get("args") or {}
                    )
        elif isinstance(message, ToolMessage) and message.tool_call_id in pending:
            info = pending.pop(message.tool_call_id)
            traces.append(ToolTrace(tool=info.name, args=info.args, result=str(message.content)))
    return traces


def _total_tokens(messages: list[AnyMessage]) -> int:
    """汇总全部模型消息的 token 用量（模型未上报时为 0）。"""
    total = 0
    for message in messages:
        usage = getattr(message, "usage_metadata", None)
        if usage:
            total += usage.get("total_tokens", 0)
    return total


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
)
def chat(request: ChatRequest, graphs: AgentGraphsDep, settings: AppSettings) -> ChatResponse:
    """与智能体对话：传入 thread_id 则按会话续聊，否则本次请求独立成会话（不落检查点）。"""
    if request.thread_id:
        graph, thread_id = graphs.stateful, request.thread_id
    else:
        graph, thread_id = graphs.stateless, uuid.uuid4().hex

    config: dict[str, Any] = {"recursion_limit": settings.agent_recursion_limit}
    if request.thread_id:
        config["configurable"] = {"thread_id": thread_id}
    try:
        # langgraph 在运行期扩展了 config（recursion_limit 不在 langchain RunnableConfig 类型中）
        state = graph.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config,  # type: ignore[arg-type]
        )
    except GraphRecursionError as exc:
        logger.warning("agent recursion limit exceeded rid=%s", get_request_id())
        raise AgentRecursionError("Agent 执行超出递归上限") from exc
    except Exception as exc:
        # 原始异常只进日志（可按 rid 关联），对外暴露固定文案，防内部细节泄漏
        logger.warning("agent execution failed: %r rid=%s", exc, get_request_id())
        raise AgentExecutionError(_UPSTREAM_UNAVAILABLE) from exc

    messages = state["messages"]
    return ChatResponse(
        reply=_final_reply(messages),
        thread_id=thread_id,
        tool_trace=_build_tool_trace(messages),
        usage=Usage(total_tokens=_total_tokens(messages)),
    )


@router.get("/tools", response_model=ToolListResponse)
def list_registered_tools() -> ToolListResponse:
    """列出全部已注册工具（名称与描述）；注册在 create_app 启动时完成。"""
    return ToolListResponse(
        tools=[
            ToolInfo(name=tool_instance.name, description=tool_instance.description)
            for tool_instance in get_tools()
        ]
    )
