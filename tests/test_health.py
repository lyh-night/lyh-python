"""健康检查接口测试。"""


def test_health_returns_ok(client):
    """GET /health 应返回 200、status=ok 与版本号。"""
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
