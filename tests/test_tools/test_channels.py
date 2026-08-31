"""
채널 툴 단위 테스트.

반환 형태는 계약이다. Discord 스키마를 그대로 흘려보내면 응답의 8~9할이
`null`이고 그 전부가 모델 컨텍스트를 먹는다. 여기서는 "필요한 필드가 있고,
쓰레기 필드가 없다"를 둘 다 검사한다.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from discord_mcp.tools.discord.channels import (
    list_guilds, list_channels, get_channel,
    create_channel, update_channel, delete_channel, set_discord_client,
)


def _model(payload):
    """model_dump()가 payload를 주는 가짜 pydantic 모델."""
    m = MagicMock()
    m.model_dump.return_value = payload
    return m


@pytest.fixture
def client():
    c = AsyncMock()
    set_discord_client(c)
    yield c
    set_discord_client(None)


# Discord가 실제로 돌려주는 형태 — 대부분이 null이다.
RAW_CHANNEL = {
    "id": "987654321", "name": "test-channel", "type": 0, "guild_id": "123456789",
    "topic": "Test Topic", "position": 2, "parent_id": "111", "nsfw": False,
    "last_message_id": "555", "bitrate": None, "user_limit": None, "recipients": [],
    "icon": None, "owner_id": None, "application_id": None, "rtc_region": None,
    "video_quality_mode": None, "message_count": None, "member_count": None,
    "thread_metadata": None, "member": None, "default_auto_archive_duration": None,
    "permissions": None, "flags": 0, "available_tags": [], "applied_tags": [],
    "default_reaction_emoji": None, "default_sort_order": None,
    "permission_overwrites": [],
}

RAW_GUILD = {"id": "123456789", "name": "Test Guild", "icon": None, "description": None}


async def test_list_guilds_returns_ids_and_names(client):
    client.get_guilds.return_value = [_model(RAW_GUILD)]

    result = await list_guilds()

    assert result["count"] == 1
    assert result["guilds"][0] == {"id": "123456789", "name": "Test Guild"}


async def test_list_channels_keeps_useful_fields(client):
    client.get_channels.return_value = [_model(RAW_CHANNEL)]

    result = await list_channels("123456789")

    assert result["guild_id"] == "123456789"
    assert result["count"] == 1
    channel = result["channels"][0]
    assert channel["id"] == "987654321"
    assert channel["name"] == "test-channel"
    assert channel["topic"] == "Test Topic"
    assert channel["parent_id"] == "111"


async def test_list_channels_drops_null_noise(client):
    """
    실측 기준 채널 6개가 3.6k 토큰이었고 8할 이상이 null이었다.
    바로 이 낭비가 서버의 사용성이므로 회귀로 묶어둔다.
    """
    client.get_channels.return_value = [_model(RAW_CHANNEL)]

    channel = (await list_channels("123456789"))["channels"][0]

    assert None not in channel.values()
    for junk in ("bitrate", "recipients", "video_quality_mode", "available_tags",
                 "permission_overwrites", "thread_metadata"):
        assert junk not in channel, f"{junk} is noise the model never uses"


async def test_channel_type_is_a_name_not_a_number(client):
    """`"type": 4`는 모델이 해석해야 하지만 `"category"`는 그냥 읽힌다."""
    client.get_channels.return_value = [_model(dict(RAW_CHANNEL, type=4))]

    assert (await list_channels("1"))["channels"][0]["type"] == "category"


async def test_get_channel(client):
    client.get_channel.return_value = _model(RAW_CHANNEL)

    result = await get_channel("987654321")

    assert result["channel"]["id"] == "987654321"
    client.get_channel.assert_awaited_once_with("987654321")


async def test_create_channel(client):
    client.create_channel.return_value = _model(RAW_CHANNEL)

    result = await create_channel(guild_id="123456789", name="test-channel", topic="Test Topic")

    assert result["channel"]["name"] == "test-channel"
    client.create_channel.assert_awaited_once()


async def test_update_channel(client):
    client.update_channel.return_value = _model(dict(RAW_CHANNEL, name="renamed"))

    result = await update_channel(channel_id="987654321", name="renamed")

    assert result["channel"]["name"] == "renamed"


async def test_update_channel_with_nothing_to_change_is_rejected(client):
    """빈 PATCH는 Discord에 보내봐야 아무 일도 안 일어난다. 여기서 잡는다."""
    with pytest.raises(ValueError, match="at least one"):
        await update_channel(channel_id="987654321")

    client.update_channel.assert_not_awaited()


async def test_delete_channel_reports_structured_result(client):
    """`{"message": "... deleted successfully"}` 산문 대신 기계가 읽을 결과."""
    result = await delete_channel("987654321")

    assert result == {"deleted": True, "channel_id": "987654321"}
    client.delete_channel.assert_awaited_once_with("987654321")


async def test_missing_client_is_an_error():
    set_discord_client(None)
    with pytest.raises(RuntimeError, match="not initialized"):
        await list_guilds()
