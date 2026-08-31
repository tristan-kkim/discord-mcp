"""
Discord 채널/길드 관련 MCP 툴.
"""
from typing import Any, Dict, Optional

from ...core.logging import log_tool_call, set_request_context
from ...core.render import channel_brief, guild_brief
from ...adapters.discord.http import DiscordClient


_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


def _client() -> DiscordClient:
    if not _discord_client:
        raise RuntimeError("Discord client not initialized")
    return _discord_client


async def list_guilds() -> Dict[str, Any]:
    """봇이 속한 길드 목록 조회"""
    set_request_context(tool_name="list_guilds")

    guilds = await _client().get_guilds()
    log_tool_call("list_guilds", success=True)
    return {
        "guilds": [guild_brief(g.model_dump()) for g in guilds],
        "count": len(guilds),
    }


async def list_channels(guild_id: str) -> Dict[str, Any]:
    """길드의 채널 목록 조회"""
    set_request_context(tool_name="list_channels", channel_id=guild_id)

    channels = await _client().get_channels(guild_id)
    briefs = [channel_brief(c.model_dump()) for c in channels]
    log_tool_call("list_channels", channel_id=guild_id, success=True)
    return {"guild_id": guild_id, "channels": briefs, "count": len(briefs)}


async def get_channel(channel_id: str) -> Dict[str, Any]:
    """채널 정보 조회"""
    set_request_context(tool_name="get_channel", channel_id=channel_id)

    channel = await _client().get_channel(channel_id)
    log_tool_call("get_channel", channel_id=channel_id, success=True)
    return {"channel": channel_brief(channel.model_dump())}


async def create_channel(
    guild_id: str,
    name: str,
    type: int = 0,
    topic: Optional[str] = None,
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """채널 생성"""
    set_request_context(tool_name="create_channel", channel_id=guild_id)

    channel = await _client().create_channel(
        guild_id=guild_id, name=name, type=type, topic=topic, parent_id=parent_id
    )
    log_tool_call("create_channel", channel_id=guild_id, success=True)
    return {"channel": channel_brief(channel.model_dump())}


async def update_channel(
    channel_id: str,
    name: Optional[str] = None,
    topic: Optional[str] = None,
    position: Optional[int] = None
) -> Dict[str, Any]:
    """채널 정보 수정"""
    set_request_context(tool_name="update_channel", channel_id=channel_id)

    if name is None and topic is None and position is None:
        raise ValueError("Pass at least one of name, topic or position to change.")

    channel = await _client().update_channel(
        channel_id=channel_id, name=name, topic=topic, position=position
    )
    log_tool_call("update_channel", channel_id=channel_id, success=True)
    return {"channel": channel_brief(channel.model_dump())}


async def delete_channel(channel_id: str) -> Dict[str, Any]:
    """채널 삭제"""
    set_request_context(tool_name="delete_channel", channel_id=channel_id)

    await _client().delete_channel(channel_id)
    log_tool_call("delete_channel", channel_id=channel_id, success=True)
    return {"deleted": True, "channel_id": channel_id}
