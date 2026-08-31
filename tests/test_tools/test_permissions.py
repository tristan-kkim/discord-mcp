"""
권한 진단 테스트.

`get_permissions`는 403의 원인을 짚기 위해 존재하는 툴인데, 이전 버전은
`GET /guilds/{id}`에서 `permissions`를 읽으려 했다. 그 엔드포인트에는 그
필드가 없으므로 답은 언제나 `null`이었고, 있었더라도 원본 비트필드라
모델이 쓸 수 없었다.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from discord_mcp.core import permissions
from discord_mcp.tools.discord import roles

VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
READ_HISTORY = 1 << 16
MANAGE_CHANNELS = 1 << 4
EVERYTHING = str((1 << 41) - 1)


@pytest.fixture
def client():
    c = AsyncMock()
    roles.set_discord_client(c)
    yield c
    roles.set_discord_client(None)


def _channel(name="general", overwrites=(), id="c1"):
    ch = MagicMock()
    ch.id = id
    ch.name = name
    ch.permission_overwrites = list(overwrites)
    return ch


def test_decode_turns_bits_into_names():
    assert permissions.decode(str(VIEW_CHANNEL | SEND_MESSAGES)) == [
        "SEND_MESSAGES", "VIEW_CHANNEL"
    ]


def test_administrator_implies_everything():
    assert "MANAGE_WEBHOOKS" in permissions.decode(str(1 << 3))


def test_channel_overwrite_can_take_a_permission_away():
    """
    실측한 quant 채널이 정확히 이 모양이다: @everyone에 VIEW_CHANNEL deny.
    길드 권한만 보면 읽을 수 있어 보이지만 실제로는 403이 난다.
    """
    effective = permissions.effective_channel_permissions(
        base=str(VIEW_CHANNEL | READ_HISTORY),
        guild_id="g1",
        member_role_ids=["r1"],
        member_id="bot",
        overwrites=[{"id": "g1", "type": 0, "allow": "0", "deny": str(VIEW_CHANNEL)}],
    )
    assert "VIEW_CHANNEL" not in permissions.decode(effective)


def test_a_role_overwrite_can_give_it_back():
    effective = permissions.effective_channel_permissions(
        base="0",
        guild_id="g1",
        member_role_ids=["r1"],
        member_id="bot",
        overwrites=[
            {"id": "g1", "type": 0, "allow": "0", "deny": str(VIEW_CHANNEL)},
            {"id": "r1", "type": 0, "allow": str(VIEW_CHANNEL), "deny": "0"},
        ],
    )
    assert "VIEW_CHANNEL" in permissions.decode(effective)


def test_member_overwrite_wins_over_role():
    effective = permissions.effective_channel_permissions(
        base=str(VIEW_CHANNEL),
        guild_id="g1",
        member_role_ids=["r1"],
        member_id="bot",
        overwrites=[
            {"id": "r1", "type": 0, "allow": str(VIEW_CHANNEL), "deny": "0"},
            {"id": "bot", "type": 1, "allow": "0", "deny": str(VIEW_CHANNEL)},
        ],
    )
    assert "VIEW_CHANNEL" not in permissions.decode(effective)


def test_blocked_tools_names_what_is_missing():
    blocked = permissions.blocked_tools(["VIEW_CHANNEL", "SEND_MESSAGES"])

    assert blocked["list_messages"] == ["READ_MESSAGE_HISTORY"]
    assert "MANAGE_CHANNELS" in blocked["create_channel"]
    assert "send_message" not in blocked


def test_nothing_is_blocked_for_an_administrator():
    assert permissions.blocked_tools(["ADMINISTRATOR"]) == {}


async def test_get_permissions_returns_names_not_bitfields(client):
    client.get_guild_permissions.return_value = str(VIEW_CHANNEL | SEND_MESSAGES)

    result = await roles.get_permissions("g1")

    assert result["guild_permissions"] == ["SEND_MESSAGES", "VIEW_CHANNEL"]
    assert "READ_MESSAGE_HISTORY" in result["blocked_tools"]["list_messages"]


async def test_get_permissions_applies_channel_overwrites(client):
    client.get_guild_permissions.return_value = str(VIEW_CHANNEL | READ_HISTORY)
    client.get_guild_member_me.return_value = {"roles": ["r1"], "user": {"id": "bot"}}
    # 볼 수 없는 채널이라도 길드 채널 목록에는 오버라이트까지 나온다.
    client.get_channels.return_value = [_channel(
        "quant", [{"id": "g1", "type": 0, "allow": "0", "deny": str(VIEW_CHANNEL)}]
    )]

    result = await roles.get_permissions("g1", channel_id="c1")

    assert result["channel_name"] == "quant"
    assert "VIEW_CHANNEL" not in result["channel_permissions"]
    assert "VIEW_CHANNEL" in result["blocked_tools"]["list_messages"]


async def test_get_permissions_works_on_a_channel_the_bot_cannot_open(client):
    """
    `GET /channels/{id}`는 볼 수 없는 채널에 403을 준다 — 그런데 그게 바로
    이 툴을 부르는 상황이다. 진단 도구가 진단 대상과 함께 죽으면 쓸모가 없다.
    """
    client.get_guild_permissions.return_value = str(VIEW_CHANNEL | READ_HISTORY)
    client.get_guild_member_me.return_value = {"roles": [], "user": {"id": "bot"}}
    client.get_channels.return_value = [_channel(
        "quant", [{"id": "g1", "type": 0, "allow": "0", "deny": str(VIEW_CHANNEL)}]
    )]

    result = await roles.get_permissions("g1", channel_id="c1")

    assert "VIEW_CHANNEL" in result["blocked_tools"]["list_messages"]
    client.get_channel.assert_not_awaited()


async def test_get_permissions_on_a_guild_the_bot_is_not_in(client):
    client.get_guild_permissions.return_value = None

    with pytest.raises(ValueError, match="not a member"):
        await roles.get_permissions("nope")


async def test_full_permissions_report_no_blocked_tools(client):
    client.get_guild_permissions.return_value = EVERYTHING

    assert "blocked_tools" not in await roles.get_permissions("g1")


def test_pinning_needs_its_own_permission():
    """
    Discord가 MANAGE_MESSAGES에서 PIN_MESSAGES(1<<51)를 떼어냈다. 핀을
    MANAGE_MESSAGES로 매핑해두면 get_permissions가 "핀 가능"이라 답하는데
    Discord는 403을 준다 — 라이브 호출에서 실제로 그렇게 나왔다.
    """
    granted = permissions.decode(str(1 << 13 | VIEW_CHANNEL))  # MANAGE_MESSAGES만

    assert "MANAGE_MESSAGES" in granted
    assert "PIN_MESSAGES" not in granted
    assert permissions.blocked_tools(granted)["pin_message"] == ["PIN_MESSAGES"]
    # 삭제는 여전히 MANAGE_MESSAGES다. 둘을 뭉뚱그리면 반대 방향으로 틀린다.
    assert "delete_message" not in permissions.blocked_tools(granted)


def test_pin_permission_is_recognised_when_present():
    granted = permissions.decode(str((1 << 51) | VIEW_CHANNEL))
    assert "pin_message" not in permissions.blocked_tools(granted)


def test_every_tool_requirement_names_a_known_permission():
    """오타 하나가 그 툴을 영구히 '막힘'으로 보고하게 만든다."""
    unknown = {
        perm
        for required in permissions.TOOL_REQUIREMENTS.values()
        for perm in required
        if perm not in permissions.PERMISSIONS
    }
    assert unknown == set()
