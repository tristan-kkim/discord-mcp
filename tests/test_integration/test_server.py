"""
서버 통합 테스트
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from server.main import app


@pytest.fixture
def client():
    """테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
def mock_discord_client():
    """Mock Discord 클라이언트"""
    client = AsyncMock()
    return client


def test_root_endpoint(client):
    """루트 엔드포인트 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Discord MCP Server"
    assert data["status"] == "running"


def test_health_endpoint(client):
    """헬스체크 엔드포인트 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "uptime" in data


def test_metrics_endpoint(client):
    """메트릭 엔드포인트 테스트"""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_list_tools_endpoint(client):
    """툴 목록 조회 엔드포인트 테스트"""
    response = client.post("/mcp/list_tools")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tools" in data["data"]


def test_call_tool_endpoint_invalid_tool(client):
    """잘못된 툴 호출 테스트"""
    response = client.post("/mcp/call_tool", json={
        "method": "call_tool",
        "params": {
            "tool": "invalid_tool",
            "params": {}
        }
    })
    assert response.status_code == 400


def test_mcp_endpoint(client):
    """MCP 엔드포인트 테스트"""
    response = client.post("/mcp", json={
        "method": "list_tools",
        "params": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_server_startup():
    """서버 시작 테스트"""
    # 환경변수 설정
    import os
    os.environ["DISCORD_BOT_TOKEN"] = "test_token"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    
    # Mock 설정
    with patch('server.main.DiscordClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        with patch('server.main.cache_manager.connect'):
            # 서버 시작 테스트
            from server.main import lifespan
            async with lifespan(app):
                pass


def test_error_handling(client):
    """에러 핸들링 테스트"""
    # 잘못된 JSON 요청
    response = client.post("/mcp/call_tool", data="invalid json")
    assert response.status_code == 422
    
    # 잘못된 메서드
    response = client.post("/mcp", json={
        "method": "invalid_method",
        "params": {}
    })
    assert response.status_code == 400
