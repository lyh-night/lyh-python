"""内置工具与注册中心测试（全程离线）。"""

import re

import httpx

from agent_service.tools import builtin
from agent_service.tools.builtin import (
    BUILTIN_TOOLS,
    calculator,
    get_current_time,
    http_get,
    register_builtin_tools,
)
from agent_service.tools.registry import (
    TOOL_REGISTRY,
    get_tool,
    get_tool_names,
    get_tools,
    register_tool,
)

_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ")


class TestCalculator:
    def test_basic_arithmetic(self):
        assert calculator.invoke({"expression": "1+2*3"}) == "1+2*3 = 7"
        assert calculator.invoke({"expression": "(1+2)*3"}) == "(1+2)*3 = 9"
        assert calculator.invoke({"expression": "10/4"}) == "10/4 = 2.5"
        assert calculator.invoke({"expression": "2**10"}) == "2**10 = 1024"
        assert calculator.invoke({"expression": "-(3+4)"}) == "-(3+4) = -7"

    def test_invalid_expression_rejected(self):
        assert calculator.invoke({"expression": "1/0"}).startswith("计算失败")
        assert calculator.invoke({"expression": "__import__('os')"}).startswith("计算失败")
        assert calculator.invoke({"expression": "(1+2"}).startswith("计算失败")


class TestGetCurrentTime:
    def test_format(self):
        result = get_current_time.invoke({})
        assert _TIME_PATTERN.match(result), result


class TestHttpGet:
    def test_non_http_scheme_rejected_without_network(self):
        assert "仅支持 http/https" in http_get.invoke({"url": "ftp://example.com/file"})

    def test_loopback_rejected(self):
        result = http_get.invoke({"url": "http://127.0.0.1:8000/docs"})
        assert "禁止访问非公网地址" in result

    def test_private_network_rejected(self):
        assert "禁止访问非公网地址" in http_get.invoke({"url": "http://10.0.0.1/"})

    def test_link_local_metadata_rejected(self):
        assert "禁止访问非公网地址" in http_get.invoke({"url": "http://169.254.169.254/"})

    def test_success_via_mock_transport(self, monkeypatch):
        """注入 MockTransport 验证成功路径（URL 用公网 IP 字面量，全程离线）。"""
        monkeypatch.setattr(builtin, "_HTTP_TRANSPORT", httpx.MockTransport(_mock_handler))

        result = http_get.invoke({"url": "http://93.184.216.34/hello"})

        assert result == "hello world"

    def test_follows_redirect_with_recheck(self, monkeypatch):
        """手动跟随重定向，目标路径可达。"""
        monkeypatch.setattr(builtin, "_HTTP_TRANSPORT", httpx.MockTransport(_mock_handler))

        result = http_get.invoke({"url": "http://93.184.216.34/redirect"})

        assert result == "final page"


def _mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/redirect":
        return httpx.Response(302, headers={"location": "/final"})
    if request.url.path == "/final":
        return httpx.Response(200, text="final page")
    return httpx.Response(200, text="hello world")


class TestRegistry:
    def test_register_and_overwrite(self):
        register_tool("unit_test_tool", object())
        replacement = object()
        try:
            assert get_tool("unit_test_tool") is not None
            register_tool("unit_test_tool", replacement)
            assert get_tool("unit_test_tool") is replacement
        finally:
            TOOL_REGISTRY.pop("unit_test_tool", None)

    def test_register_builtin_tools_is_idempotent(self):
        register_builtin_tools()
        register_builtin_tools()
        names = get_tool_names()
        for tool_instance in BUILTIN_TOOLS:
            assert tool_instance.name in names
        assert get_tools()  # 非空
