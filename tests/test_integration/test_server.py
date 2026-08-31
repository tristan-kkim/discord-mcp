"""
MCP 프로토콜 통합 테스트.

실제 MCP 클라이언트를 서버에 붙여 initialize → tools/list → tools/call 왕복을
검증한다. 이전 버전의 테스트는 FastAPI TestClient로 자체 REST 엔드포인트를
때렸는데, 그건 MCP가 아니어서 어떤 MCP 클라이언트도 이 서버를 쓸 수 없었다.
"""
import re
from unittest.mock import AsyncMock

import pytest
from mcp import Client

from discord_mcp.adapters.discord.models import DiscordChannel, DiscordGuild
from discord_mcp.config import Settings
from discord_mcp.server import build_server

# MCP 툴 이름 제약. Claude를 포함한 주요 클라이언트가 이 패턴으로 검증한다 —
# 점(.)이 들어간 이름은 거부된다.
TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


@pytest.fixture
def settings():
    return Settings(
        bot_token="test-token",
        default_guild_id=None,
        redis_url=None,
        log_level="CRITICAL",
    )


@pytest.fixture
def fake_discord(monkeypatch):
    """네트워크를 타지 않도록 DiscordClient를 대체한다."""
    client = AsyncMock()
    client.get_application_info.return_value = {"flags": 1 << 18}
    client.get_guilds.return_value = [
        DiscordGuild(id="1", name="Test Guild", icon=None, description=None, member_count=3)
    ]
    client.get_channels.return_value = [
        DiscordChannel(id="10", name="general", type=0, guild_id="1")
    ]
    monkeypatch.setattr(
        "discord_mcp.server.DiscordClient", lambda token, **kwargs: client
    )
    return client


async def test_initialize_advertises_server(settings, fake_discord):
    """MCP 핸드셰이크가 성립하고 서버 정보가 넘어온다."""
    async with Client(build_server(settings)) as session:
        assert session.server_info.name == "discord-mcp"
        assert session.server_capabilities.tools is not None


async def test_tool_names_are_client_compatible(settings, fake_discord):
    """모든 툴 이름이 클라이언트 검증 패턴을 통과해야 한다."""
    async with Client(build_server(settings)) as session:
        tools = (await session.list_tools()).tools

    assert tools, "no tools registered"
    offenders = [t.name for t in tools if not TOOL_NAME_PATTERN.match(t.name)]
    assert offenders == [], f"tool names rejected by MCP clients: {offenders}"


async def test_every_tool_has_description_and_schema(settings, fake_discord):
    """설명 없는 툴은 모델이 언제 써야 할지 알 수 없다."""
    async with Client(build_server(settings)) as session:
        tools = (await session.list_tools()).tools

    for tool in tools:
        assert tool.description, f"{tool.name} has no description"
        assert tool.input_schema.get("type") == "object", f"{tool.name} has a bad inputSchema"


async def test_call_tool_returns_content(settings, fake_discord):
    """tools/call이 MCP 결과 형식으로 돌아온다."""
    async with Client(build_server(settings)) as session:
        result = await session.call_tool("list_guilds", {})

    assert result.is_error is False
    assert result.content, "tool returned no content blocks"
    assert result.structured_content["result"]["count"] == 1
    assert result.structured_content["result"]["guilds"][0]["name"] == "Test Guild"


async def test_tool_failure_is_reported_as_is_error(settings, fake_discord):
    """툴 실패는 예외가 아니라 isError=true 결과로 나와야 한다."""
    fake_discord.get_guilds.side_effect = RuntimeError("discord is down")

    async with Client(build_server(settings)) as session:
        result = await session.call_tool("list_guilds", {})

    assert result.is_error is True


async def test_default_guild_id_makes_guild_id_optional(fake_discord):
    """DISCORD_GUILD_ID가 있으면 guild_id 없이 호출된다."""
    settings = Settings(
        bot_token="test-token",
        default_guild_id="1",
        redis_url=None,
        log_level="CRITICAL",
    )
    async with Client(build_server(settings)) as session:
        result = await session.call_tool("list_channels", {})

    assert result.is_error is False
    fake_discord.get_channels.assert_awaited_once_with("1")


async def test_missing_guild_id_without_default_is_an_error(settings, fake_discord):
    """기본 길드가 없으면 guild_id 누락은 명확한 에러여야 한다."""
    async with Client(build_server(settings)) as session:
        result = await session.call_tool("list_channels", {})

    assert result.is_error is True
