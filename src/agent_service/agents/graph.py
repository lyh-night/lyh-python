"""LangGraph 编排：agent ↔ tools 循环。

流程：START → agent（模型决定是否调用工具）→（含 tool_calls）tools → agent
→ … →（无 tool_calls）END。工具异常经 ToolNode 转为错误消息回传模型自行纠错。
"""

from functools import lru_cache
from typing import Any, NamedTuple

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent_service.llm.model import get_chat_model
from agent_service.tools.builtin import register_builtin_tools
from agent_service.tools.registry import get_tools


class AgentGraphs(NamedTuple):
    """编译后的图对。

    - ``stateful``：挂 MemorySaver，按 thread_id 检查点续聊（进程内存，重启即失）
    - ``stateless``：不挂 checkpointer，单轮请求不留下任何检查点，避免内存无上限增长
    """

    stateless: Runnable
    stateful: Runnable


def build_agent_graph(
    model: BaseChatModel | None = None, with_checkpointer: bool = True
) -> Runnable:
    """构建并编译 agent 图；``model`` 供测试注入桩模型，默认取真实 DeepSeek 模型。"""
    register_builtin_tools()
    llm = model or get_chat_model()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    def agent(state: MessagesState) -> dict[str, Any]:
        """调用模型生成下一条消息（可能包含 tool_calls）。"""
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    checkpointer = MemorySaver() if with_checkpointer else None
    return builder.compile(checkpointer=checkpointer)


@lru_cache
def get_agent_graphs() -> AgentGraphs:
    """返回全局图单例对（stateless 与 stateful 共享工具注册与模型连接池）。"""
    return AgentGraphs(
        stateless=build_agent_graph(with_checkpointer=False),
        stateful=build_agent_graph(with_checkpointer=True),
    )
