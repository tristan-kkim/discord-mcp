"""
조용히 깨져 있던 것들에 대한 회귀 테스트.

셋 다 실제로 프로덕션 경로에서 죽던 버그다.
"""
import sys

import pytest
from loguru import logger

from discord_mcp.adapters.discord.models import DiscordGuild
from discord_mcp.core.logging import setup_logging
from discord_mcp.core.schema import ErrorCode, MCPError


def test_mcp_error_is_raisable():
    """
    MCPError는 pydantic BaseModel이었다. `raise MCPError(...)`가
    TypeError로 죽어서 rate limit / timeout 경로가 전부 오작동했다.
    """
    assert issubclass(MCPError, Exception)

    with pytest.raises(MCPError) as excinfo:
        raise MCPError(
            code=ErrorCode.RATE_LIMITED,
            message="slow down",
            retry_after_ms=1500,
            rate_limited=True,
        )

    err = excinfo.value
    assert err.code is ErrorCode.RATE_LIMITED
    assert err.retry_after_ms == 1500
    assert "slow down" in str(err)


def test_partial_guild_parses_without_owner_id():
    """
    GET /users/@me/guilds 는 owner_id 없는 partial guild를 준다.
    owner_id가 필수였을 때는 list_guilds가 항상 ValidationError로 죽었다.
    """
    guild = DiscordGuild(id="1", name="Test Guild", icon=None)
    assert guild.owner_id is None


def test_logging_never_writes_to_stdout():
    """
    stdio 전송에서 stdout은 JSON-RPC 채널이다. 로그가 한 줄이라도 섞이면
    클라이언트의 프레임 파싱이 깨진다.
    """
    setup_logging("INFO")
    try:
        sinks = [h._sink for h in logger._core.handlers.values()]
        stream_targets = [getattr(s, "_stream", None) for s in sinks]
        assert sys.stdout not in stream_targets, "a log sink is writing to stdout"
        assert sys.stderr in stream_targets, "expected a stderr log sink"
    finally:
        logger.remove()


@pytest.mark.parametrize("method", ["send_message", "edit_message", "send_webhook_message"])
def test_mention_guard_covers_every_write_path(method):
    """
    @everyone 가드는 모든 쓰기 경로에 있어야 한다. send_via_webhook에만
    빠져 있으면 모델이 그 경로로 필터를 우회한다.
    """
    import inspect

    from discord_mcp.adapters.discord.http import DiscordClient

    source = inspect.getsource(getattr(DiscordClient, method))
    assert "_sanitize_content" in source, f"{method} does not sanitize content"
    assert "allowed_mentions" in source, f"{method} does not disable mention parsing"
