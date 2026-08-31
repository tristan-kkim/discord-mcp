"""
모델이 실패를 스스로 고칠 수 있는가에 대한 테스트.

MCP SDK 2.1은 `ToolError`만 메시지를 클라이언트로 넘기고, 그 밖의 예외는
크래시로 보아 `Error executing tool <name>`만 남긴다. 이전 버전은 어댑터가
올린 `DiscordAPIError`를 그대로 재전파했으므로, 403 Missing Access도 잘못된
id도 rate limit도 모델 눈에는 전부 같은 한 줄이었다 — 실제로 이 저장소의
서버를 붙여놓고 `list_messages`를 호출했을 때 나온 것이 정확히 그 한 줄이다.
"""
import pytest
from unittest.mock import AsyncMock

from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from discord_mcp.adapters.discord.models import DiscordGuild
from discord_mcp.config import Settings
from discord_mcp.core.errors import explain
from discord_mcp.core.retry import DiscordAPIError, RateLimitError, TimeoutError
from discord_mcp.server import build_server


@pytest.fixture
def settings():
    return Settings(bot_token="t", default_guild_id="1", redis_url=None, log_level="CRITICAL")


@pytest.fixture
def fake_discord(monkeypatch):
    client = AsyncMock()
    client.get_application_info.return_value = {"flags": 1 << 18}
    client.get_guilds.return_value = [DiscordGuild(id="1", name="G", icon=None)]
    monkeypatch.setattr("discord_mcp.server.DiscordClient", lambda token, **kw: client)
    return client


def test_missing_access_names_the_permission_and_the_next_tool():
    """
    실측: quant 채널의 list_messages는 `{"message": "Missing Access", "code": 50001}`로
    실패했지만 모델에게는 `Error executing tool list_messages`만 도달했다.
    """
    message = explain(DiscordAPIError("Missing Access", status_code=403, discord_code=50001))

    assert "Missing Access" in message
    assert "View Channel" in message
    assert "get_permissions" in message


@pytest.mark.parametrize(
    "code,expected",
    [
        (10003, "Unknown channel"),
        (10008, "Unknown message"),
        (50013, "Missing Permissions"),
        (50005, "Cannot edit"),
        (30003, "50 pinned"),
    ],
)
def test_known_discord_codes_become_actionable_text(code, expected):
    assert expected in explain(DiscordAPIError("x", status_code=403, discord_code=code))


def test_unmapped_code_still_carries_discord_own_words():
    """매핑에 없는 코드일 때 Discord 원문이 유일한 단서다. 버리면 안 된다."""
    message = explain(DiscordAPIError("Something specific", status_code=400, discord_code=999999))
    assert "Something specific" in message


def test_rate_limit_tells_the_model_how_long_to_wait():
    assert "12s" in explain(RateLimitError("slow down", retry_after=12.0))


def test_timeout_suggests_a_smaller_limit():
    assert "limit" in explain(TimeoutError("timed out"))


def test_bad_token_points_at_the_env_var():
    assert "DISCORD_BOT_TOKEN" in explain(DiscordAPIError("Unauthorized", status_code=401))


async def test_tool_failure_reaches_the_model_with_its_reason(settings, fake_discord):
    """엔드투엔드: 툴 실패 메시지가 MCP 클라이언트까지 실려 나가야 한다."""
    fake_discord.get_guilds.side_effect = DiscordAPIError(
        "Missing Access", status_code=403, discord_code=50001
    )

    async with Client(build_server(settings)) as session:
        result = await session.call_tool("list_guilds", {})

    assert result.is_error is True
    text = " ".join(getattr(block, "text", "") for block in result.content)
    assert "Missing Access" in text, f"the reason never reached the model: {text!r}"
    assert text.strip() != "Error executing tool list_guilds"


async def test_argument_constraints_are_enforced_before_discord(settings, fake_discord):
    """limit 범위를 스키마에 박아두면 왕복 한 번을 아낀다."""
    async with Client(build_server(settings)) as session:
        result = await session.call_tool("list_messages", {"channel_id": "1", "limit": 9999})

    assert result.is_error is True
    fake_discord.iter_messages.assert_not_awaited()


async def test_every_tool_argument_is_documented(settings, fake_discord):
    """
    설명 없는 인자는 모델이 의미를 추측하게 만든다. 이전 스키마의 `has`는
    `{"title": "Has"}`뿐이라 link/embed/file/image 중 무엇을 넣어야 할지
    알 방법이 없었다.
    """
    async with Client(build_server(settings)) as session:
        tools = (await session.list_tools()).tools

    undocumented = [
        f"{tool.name}.{name}"
        for tool in tools
        for name, spec in tool.input_schema.get("properties", {}).items()
        if not spec.get("description")
    ]
    assert undocumented == [], f"arguments with no description: {undocumented}"
