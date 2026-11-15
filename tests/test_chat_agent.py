"""对话接口端到端测试：注入桩模型，全程离线覆盖成功与错误路径。"""

from typing import cast

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from agent_service.agents.graph import AgentGraphs, build_agent_graph, get_agent_graphs
from agent_service.core.errors import LLMNotConfiguredError
from agent_service.main import create_app
from tests.fakes import ScriptedChatModel

_TOOL_CALL_MSG = AIMessage(
    content="",
    tool_calls=[{"name": "get_current_time", "args": {}, "id": "call_1"}],
)
_FINAL_MSG = AIMessage(content="现在是北京时间 12:00。")


def _graphs(model: ScriptedChatModel) -> AgentGraphs:
    """stateless 不带 checkpointer、stateful 带检查点，与生产构建保持一致。"""
    return AgentGraphs(
        stateless=build_agent_graph(model=model, with_checkpointer=False),
        stateful=build_agent_graph(model=model),
    )


def _client_with_model(model: ScriptedChatModel) -> TestClient:
    """构建图依赖被替换为桩模型的测试客户端。"""
    app = create_app()
    app.dependency_overrides[get_agent_graphs] = lambda: _graphs(model)
    return TestClient(app)


def test_chat_success_with_tool_trace():
    """模型先调工具再回答：接口应返回最终回复、非空 tool_trace 与 thread_id 回显。"""
    client = _client_with_model(ScriptedChatModel(responses=[_TOOL_CALL_MSG, _FINAL_MSG]))

    resp = client.post("/api/v1/chat", json={"message": "现在几点了", "thread_id": "t-42"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "现在是北京时间 12:00。"
    assert body["thread_id"] == "t-42"
    assert len(body["tool_trace"]) == 1
    trace = body["tool_trace"][0]
    assert trace["tool"] == "get_current_time"
    assert trace["args"] == {}
    assert trace["result"]  # 工具确有输出
    assert body["usage"]["total_tokens"] == 0  # 桩消息未带 usage_metadata


def test_chat_generates_thread_id_when_absent():
    """未传 thread_id 时应服务端生成并回显。"""
    client = _client_with_model(ScriptedChatModel(responses=[_FINAL_MSG]))

    body = client.post("/api/v1/chat", json={"message": "你好"}).json()

    assert body["thread_id"]


def test_chat_sums_usage_metadata():
    """各轮模型消息的 usage_metadata.total_tokens 应被累加。"""
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "get_current_time", "args": {}, "id": "call_1"}],
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )
    final_msg = AIMessage(
        content="done",
        usage_metadata={"input_tokens": 20, "output_tokens": 5, "total_tokens": 25},
    )
    client = _client_with_model(ScriptedChatModel(responses=[tool_call_msg, final_msg]))

    body = client.post("/api/v1/chat", json={"message": "现在几点了"}).json()

    assert body["reply"] == "done"
    assert body["usage"]["total_tokens"] == 40


def test_chat_503_when_llm_not_configured():
    """图依赖抛 LLMNotConfiguredError 时应返回 503。"""
    app = create_app()

    def _raise():
        raise LLMNotConfiguredError("未配置 DEEPSEEK_API_KEY")

    app.dependency_overrides[get_agent_graphs] = _raise
    client = TestClient(app)

    resp = client.post("/api/v1/chat", json={"message": "你好"})

    assert resp.status_code == 503
    assert "DEEPSEEK_API_KEY" in resp.json()["detail"]


def test_chat_502_on_execution_error_hides_internal_detail():
    """图执行抛任意异常应返回 502 固定文案，不泄漏内部异常细节。"""

    class _ExplodingGraph:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("connection reset to http://secret-host:9999")

    exploding = cast(Runnable, _ExplodingGraph())
    app = create_app()
    app.dependency_overrides[get_agent_graphs] = lambda: AgentGraphs(
        stateless=exploding, stateful=exploding
    )
    client = TestClient(app)

    resp = client.post("/api/v1/chat", json={"message": "你好"})

    assert resp.status_code == 502
    body = resp.json()["detail"]
    assert body == "上游模型暂时不可用，请稍后重试"
    assert "secret-host" not in body


def test_chat_500_on_recursion_limit():
    """模型无限要求调工具时应触发递归上限，返回 500。"""
    client = _client_with_model(ScriptedChatModel(responses=[_TOOL_CALL_MSG]))

    resp = client.post("/api/v1/chat", json={"message": "现在几点了"})

    assert resp.status_code == 500
    assert "递归上限" in resp.json()["detail"]


def test_chat_422_on_blank_message():
    """全空白消息应被 Pydantic 校验拦截。"""
    client = _client_with_model(ScriptedChatModel(responses=[_FINAL_MSG]))

    resp = client.post("/api/v1/chat", json={"message": "   "})

    assert resp.status_code == 422


def test_list_tools_exposes_builtin_tools():
    client = _client_with_model(ScriptedChatModel(responses=[_FINAL_MSG]))

    resp = client.get("/api/v1/tools")

    assert resp.status_code == 200
    names = {item["name"] for item in resp.json()["tools"]}
    assert {"get_current_time", "calculator", "http_get"} <= names
