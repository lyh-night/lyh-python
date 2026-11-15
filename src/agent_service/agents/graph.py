"""Agent 图构建（桩）：M3 里程碑实现 LangGraph 的 agent ↔ tools 循环。"""


def build_agent_graph():
    """构建并返回编译后的 LangGraph 图。

    待实现：``StateGraph(MessagesState)``，agent 节点绑定工具、tools 节点
    执行工具，条件边按最后一条消息是否含 tool_calls 分流，终点为 END。
    """
    raise NotImplementedError("Agent 图构建尚未实现（M3 里程碑）")
