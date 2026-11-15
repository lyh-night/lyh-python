"""pytest 公共 fixture。"""

import pytest
from fastapi.testclient import TestClient

from agent_service.main import create_app


@pytest.fixture
def client() -> TestClient:
    """返回应用 TestClient，全程离线。"""
    return TestClient(create_app())
