"""pytest 公共 fixture。"""

import pytest
from fastapi.testclient import TestClient

from agent_service.core.rate_limit import RATE_LIMITER
from agent_service.main import create_app


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """每个用例前清空限流计数，避免跨用例串扰。"""
    RATE_LIMITER.reset_all()
    yield


@pytest.fixture
def client() -> TestClient:
    """返回应用 TestClient，全程离线。"""
    return TestClient(create_app())
