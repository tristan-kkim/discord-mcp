"""
Discord 역할/권한 관련 MCP 툴
"""
from typing import Any, Dict, List, Optional
from loguru import logger

from ...core.logging import log_tool_call, set_request_context
from ...core import permissions
from ...core.render import role_brief
from ...adapters.discord.http import DiscordClient


# Discord 클라이언트 인스턴스
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


async def list_roles(guild_id: str) -> Dict[str, Any]:
    """역할 목록 조회"""
    set_request_context(tool_name="list_roles", channel_id=guild_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        roles = await _discord_client.get_roles(guild_id)
        
        result = {
            "guild_id": guild_id,
            "roles": [role_brief(role.model_dump()) for role in roles],
            "count": len(roles)
        }
        
        log_tool_call("list_roles", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list roles for guild {guild_id}: {e}")
        log_tool_call("list_roles", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def add_role_to_member(
    guild_id: str,
    user_id: str,
    role_id: str
) -> Dict[str, Any]:
    """멤버에게 역할 부여"""
    set_request_context(tool_name="add_role", channel_id=guild_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.add_role_to_member(guild_id, user_id, role_id)
        
        result = {
            "message": f"Role {role_id} added to user {user_id}",
            "guild_id": guild_id,
            "user_id": user_id,
            "role_id": role_id
        }
        
        log_tool_call("add_role", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to add role {role_id} to user {user_id}: {e}")
        log_tool_call("add_role", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def remove_role_from_member(
    guild_id: str,
    user_id: str,
    role_id: str
) -> Dict[str, Any]:
    """멤버에서 역할 제거"""
    set_request_context(tool_name="remove_role", channel_id=guild_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.remove_role_from_member(guild_id, user_id, role_id)
        
        result = {
            "message": f"Role {role_id} removed from user {user_id}",
            "guild_id": guild_id,
            "user_id": user_id,
            "role_id": role_id
        }
        
        log_tool_call("remove_role", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to remove role {role_id} from user {user_id}: {e}")
        log_tool_call("remove_role", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def _find_channel_in_guild(client, guild_id: str, channel_id: str):
    """길드 채널 목록에서 채널을 찾는다. 볼 수 없는 채널도 여기엔 나온다."""
    for channel in await client.get_channels(guild_id):
        if channel.id == channel_id:
            return channel
    raise ValueError(
        f"Channel {channel_id} is not in guild {guild_id}. Call list_channels to see the "
        "channels this bot can enumerate."
    )


async def get_permissions(guild_id: str, channel_id: Optional[str] = None) -> Dict[str, Any]:
    """봇의 실효 권한 조회.

    403의 원인을 짚기 위한 툴이다. 그러려면 비트필드가 아니라 **이름**과
    **어떤 툴이 막히는지**를 돌려줘야 한다. channel_id를 주면 채널
    오버라이트까지 적용해 그 채널에서의 실효 권한을 계산한다.
    """
    set_request_context(tool_name="get_permissions", channel_id=channel_id or guild_id)

    client = _discord_client
    if not client:
        raise RuntimeError("Discord client not initialized")

    guild_bits = await client.get_guild_permissions(guild_id)
    if guild_bits is None:
        raise ValueError(
            f"The bot is not a member of guild {guild_id}. Call list_guilds for the guilds it can see."
        )

    granted = permissions.decode(guild_bits)
    result: Dict[str, Any] = {
        "guild_id": guild_id,
        "guild_permissions": granted,
    }

    if channel_id:
        # `GET /channels/{id}`는 봇이 볼 수 없는 채널에 403을 준다 — 그런데 그게
        # 바로 이 툴을 부르는 상황이다. 길드의 채널 목록은 View Channel 없이도
        # 오버라이트까지 포함해 돌아오므로 그쪽에서 찾는다.
        channel = await _find_channel_in_guild(client, guild_id, channel_id)
        member = await client.get_guild_member_me(guild_id)
        effective = permissions.effective_channel_permissions(
            base=guild_bits,
            guild_id=guild_id,
            member_role_ids=member.get("roles", []),
            member_id=(member.get("user") or {}).get("id"),
            overwrites=[o if isinstance(o, dict) else o.model_dump()
                        for o in (channel.permission_overwrites or [])],
        )
        granted = permissions.decode(effective)
        result["channel_id"] = channel_id
        result["channel_name"] = channel.name
        result["channel_permissions"] = granted
        result["scope"] = "channel (guild permissions with this channel's overwrites applied)"
    else:
        result["scope"] = "guild (channel overwrites not applied — pass channel_id for the effective set)"

    blocked = permissions.blocked_tools(granted)
    if blocked:
        result["blocked_tools"] = blocked
        result["hint"] = (
            "These tools will fail here until the listed permissions are granted to the bot's "
            "role in Discord (Server Settings → Roles), or via a channel permission overwrite."
        )

    log_tool_call("get_permissions", channel_id=channel_id or guild_id, success=True)
    return result
