"""应用级异常定义：由 main.py 统一转换为 HTTP 错误响应。"""


class AgentServiceError(Exception):
    """应用异常基类。"""


class LLMNotConfiguredError(AgentServiceError):
    """LLM 未配置（缺少 API key 等），对应 HTTP 503。"""


class AgentExecutionError(AgentServiceError):
    """智能体执行失败（LLM 网络/超时等），对应 HTTP 502。"""


class AgentRecursionError(AgentServiceError):
    """Agent 循环超出递归上限，对应 HTTP 500。"""
