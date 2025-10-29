"""
Discord 역할/권한 관련 MCP 툴
"""
from typing import Any, Dict, List, Optional
from loguru import logger

from ...core.tool_registry import tool_registry
from ...core.schema import create_json_schema
from ...core.logging import log_tool_call, set_request_context
from ...adapters.discord.http import DiscordClient


# Discord 클라이언트 인스턴스
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


async def list_roles(guild_id: str) -> Dict[str, Any]:
    """역할 목록 조회"""
    set_request_context(tool_name="discord.list_roles", channel_id=guild_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        roles = await _discord_client.get_roles(guild_id)
        
        result = {
            "guild_id": guild_id,
            "roles": [role.model_dump() for role in roles],
            "count": len(roles)
        }
        
        log_tool_call("discord.list_roles", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list roles for guild {guild_id}: {e}")
        log_tool_call("discord.list_roles", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def add_role_to_member(
    guild_id: str,
    user_id: str,
    role_id: str
) -> Dict[str, Any]:
    """멤버에게 역할 부여"""
    set_request_context(tool_name="discord.add_role", channel_id=guild_id)
    
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
        
        log_tool_call("discord.add_role", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to add role {role_id} to user {user_id}: {e}")
        log_tool_call("discord.add_role", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def remove_role_from_member(
    guild_id: str,
    user_id: str,
    role_id: str
) -> Dict[str, Any]:
    """멤버에서 역할 제거"""
    set_request_context(tool_name="discord.remove_role", channel_id=guild_id)
    
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
        
        log_tool_call("discord.remove_role", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to remove role {role_id} from user {user_id}: {e}")
        log_tool_call("discord.remove_role", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def get_permissions(guild_id: str, channel_id: Optional[str] = None) -> Dict[str, Any]:
    """권한 조회"""
    set_request_context(tool_name="discord.get_permissions", channel_id=channel_id or guild_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 길드 정보 조회
        guild = await _discord_client.get_guild(guild_id)
        
        result = {
            "guild_id": guild_id,
            "guild_name": guild.name,
            "permissions": {
                "guild_permissions": guild.permissions,
                "features": guild.features
            }
        }
        
        # 채널별 권한이 요청된 경우
        if channel_id:
            channel = await _discord_client.get_channel(channel_id)
            result["channel_permissions"] = {
                "channel_id": channel_id,
                "channel_name": channel.name,
                "permission_overwrites": channel.permission_overwrites
            }
        
        log_tool_call("discord.get_permissions", channel_id=channel_id or guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get permissions for guild {guild_id}: {e}")
        log_tool_call("discord.get_permissions", channel_id=channel_id or guild_id, success=False, error_message=str(e))
        raise


# 툴 등록
def register_role_tools():
    """역할/권한 관련 툴 등록"""
    
    # discord.list_roles
    tool_registry.register_tool(
        name="discord.list_roles",
        handler=list_roles,
        input_schema={
            "type": "object",
            "properties": {
                "guild_id": {
                    "type": "string",
                    "description": "길드 ID"
                }
            },
            "required": ["guild_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="길드의 역할 목록을 조회합니다."
    )
    
    # discord.add_role
    tool_registry.register_tool(
        name="discord.add_role",
        handler=add_role_to_member,
        input_schema={
            "type": "object",
            "properties": {
                "guild_id": {
                    "type": "string",
                    "description": "길드 ID"
                },
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID"
                },
                "role_id": {
                    "type": "string",
                    "description": "역할 ID"
                }
            },
            "required": ["guild_id", "user_id", "role_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="멤버에게 역할을 부여합니다."
    )
    
    # discord.remove_role
    tool_registry.register_tool(
        name="discord.remove_role",
        handler=remove_role_from_member,
        input_schema={
            "type": "object",
            "properties": {
                "guild_id": {
                    "type": "string",
                    "description": "길드 ID"
                },
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID"
                },
                "role_id": {
                    "type": "string",
                    "description": "역할 ID"
                }
            },
            "required": ["guild_id", "user_id", "role_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="멤버에서 역할을 제거합니다."
    )
    
    # discord.get_permissions
    tool_registry.register_tool(
        name="discord.get_permissions",
        handler=get_permissions,
        input_schema={
            "type": "object",
            "properties": {
                "guild_id": {
                    "type": "string",
                    "description": "길드 ID"
                },
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID (선택사항)"
                }
            },
            "required": ["guild_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="길드 또는 채널의 권한 정보를 조회합니다."
    )
