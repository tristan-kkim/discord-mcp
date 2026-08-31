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


def test_message_cache_key_covers_every_paging_param():
    """
    캐시 키가 (channel, limit, after)뿐이라 before/around가 빠져 있었다.
    before로 과거를 넘기면 캐시된 첫 페이지가 되돌아와, 페이지네이션이
    같은 자리를 맴돈다. 에러가 안 나서 더 위험하다.
    """
    from discord_mcp.core.cache import discord_cache

    first = discord_cache._messages_key("c1", {"limit": 50})
    older = discord_cache._messages_key("c1", {"limit": 50, "before": "999"})
    around = discord_cache._messages_key("c1", {"limit": 50, "around": "999"})

    assert len({first, older, around}) == 3


def test_message_cache_key_is_order_independent():
    """dict 순서가 달라도 같은 요청이면 같은 키여야 캐시가 실제로 맞는다."""
    from discord_mcp.core.cache import discord_cache

    assert discord_cache._messages_key("c1", {"limit": 50, "before": "9"}) == \
           discord_cache._messages_key("c1", {"before": "9", "limit": 50})


def test_search_does_not_call_the_user_only_endpoint():
    """
    `GET /guilds/{id}/messages/search`는 유저 토큰 전용이라 봇은 403을 받는다.
    이전 구현은 그 엔드포인트를, 그것도 guild 자리에 channel_id를 넣어 호출했다.
    이 툴은 한 번도 성공한 적이 없다.
    """
    import inspect

    from discord_mcp.adapters.discord.http import DiscordClient

    source = inspect.getsource(DiscordClient.search_messages)
    body = source.split('"""')[-1]  # 독스트링에는 그 엔드포인트가 왜 안 되는지 적혀 있다
    assert "_make_request" not in body, "search still hits a REST endpoint directly"
    assert "iter_messages" in body, "search should read history and filter here"


def test_list_threads_does_not_use_a_nonexistent_endpoint():
    """
    `GET /channels/{id}/threads`는 Discord에 없는 경로다. 실제로 호출하면
    405 Method Not Allowed가 돌아온다 — 이 서버를 라이브로 붙여놓고
    list_threads를 부르면 정확히 그랬다. 활성 스레드는 길드 단위,
    아카이브된 것은 채널 단위 경로에서 온다.
    """
    import inspect

    from discord_mcp.adapters.discord.http import DiscordClient

    body = inspect.getsource(DiscordClient.get_threads).split('"""')[-1]
    assert 'f"/channels/{channel_id}/threads"' not in body
    assert "threads/active" in body
    assert "threads/archived/public" in body


def test_webhook_send_waits_for_the_message():
    """
    `?wait=true` 없이는 Discord가 204를 주고 메시지 객체를 안 돌려준다.
    그러면 방금 만든 글의 id를 알 수 없어 지울 방법이 없다 — 되돌릴 수 없는
    쓰기를 남기는 셈이다. 라이브 검증에서 실제로 잔여물이 남았다.
    """
    import inspect

    from discord_mcp.adapters.discord.http import DiscordClient

    source = inspect.getsource(DiscordClient.send_webhook_message)
    assert "wait=true" in source
    assert "return await response.json()" in source


def test_created_webhooks_can_be_revoked():
    """자격증명을 만들 수 있으면 회수도 할 수 있어야 한다."""
    from discord_mcp.adapters.discord.http import DiscordClient

    assert hasattr(DiscordClient, "delete_webhook")
    assert hasattr(DiscordClient, "get_webhooks")


def test_pins_use_the_current_endpoint():
    """구 `/channels/{id}/pins/...`는 deprecated다."""
    import inspect

    from discord_mcp.adapters.discord.http import DiscordClient

    for method in ("pin_message", "unpin_message", "get_pinned_messages"):
        body = inspect.getsource(getattr(DiscordClient, method)).split('"""')[-1]
        assert "messages/pins" in body, f"{method} uses the deprecated pins route"
