"""鉴权与限流测试（P0-3 修复验证）。"""

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from agent_service.agents.graph import AgentGraphs, build_agent_graph, get_agent_graphs
from agent_service.api.deps import get_app_settings
from agent_service.core.config import Settings
from agent_service.main import create_app
from tests.fakes import ScriptedChatModel


def _client_with(settings: Settings) -> TestClient:
    """用指定 Settings 与桩图构建测试客户端。"""
    app = create_app(settings)
    stateless = build_agent_graph(
        model=ScriptedChatModel(responses=[AIMessage(content="ok")]),
        with_checkpointer=False,
    )
    stateful = build_agent_graph(model=ScriptedChatModel(responses=[AIMessage(content="ok")]))
    app.dependency_overrides[get_agent_graphs] = lambda: AgentGraphs(
        stateless=stateless, stateful=stateful
    )
    app.dependency_overrides[get_app_settings] = lambda: settings
    return TestClient(app)


class TestApiKey:
    def test_401_when_token_configured_and_missing(self):
        client = _client_with(Settings(api_auth_token="secret-token"))

        resp = client.post("/api/v1/chat", json={"message": "你好"})

        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    def test_401_when_token_wrong(self):
        client = _client_with(Settings(api_auth_token="secret-token"))

        resp = client.post(
            "/api/v1/chat",
            json={"message": "你好"},
            headers={"Authorization": "Bearer wrong-token"},
        )

        assert resp.status_code == 401

    def test_200_with_valid_bearer_token(self):
        client = _client_with(Settings(api_auth_token="secret-token"))

        resp = client.post(
            "/api/v1/chat",
            json={"message": "你好"},
            headers={"Authorization": "Bearer secret-token"},
        )

        assert resp.status_code == 200
        assert resp.json()["reply"] == "ok"

    def test_open_when_token_unset(self):
        """token 未配置（本地开发模式）时不做鉴权。"""
        client = _client_with(Settings(api_auth_token=""))

        resp = client.post("/api/v1/chat", json={"message": "你好"})

        assert resp.status_code == 200


class TestRateLimit:
    def test_429_after_exceeding_limit(self):
        client = _client_with(Settings(rate_limit_per_minute=1))

        first = client.post("/api/v1/chat", json={"message": "你好"})
        second = client.post("/api/v1/chat", json={"message": "你好"})

        assert first.status_code == 200
        assert second.status_code == 429

    def test_disabled_when_limit_zero(self):
        client = _client_with(Settings(rate_limit_per_minute=0))

        for _ in range(3):
            assert client.post("/api/v1/chat", json={"message": "你好"}).status_code == 200
