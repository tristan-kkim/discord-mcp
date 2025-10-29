"""
Discord 채널/길드 관련 MCP 툴
"""
from typing import Any, Dict, List, Optional
from loguru import logger

from ...core.tool_registry import tool_registry
from ...core.schema import create_json_schema, DiscordGuild, DiscordChannel
from ...core.logging import log_tool_call, set_request_context
from ...adapters.discord.http import DiscordClient


# Discord 클라이언트 인스턴스 (나중에 의존성 주입으로 변경)
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


async def list_guilds() -> Dict[str, Any]:
    """봇이 속한 길드 목록 조회"""
    set_request_context(tool_name="discord.list_guilds")
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        guilds = await _discord_client.get_guilds()
        result = {
            "guilds": [guild.model_dump() for guild in guilds],
            "count": len(guilds)
        }
        
        log_tool_call("discord.list_guilds", success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list guilds: {e}")
        log_tool_call("discord.list_guilds", success=False, error_message=str(e))
        raise


async def list_channels(guild_id: str) -> Dict[str, Any]:
    """길드의 채널 목록 조회"""
    set_request_context(tool_name="discord.list_channels", channel_id=guild_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        channels = await _discord_client.get_channels(guild_id)
        result = {
            "guild_id": guild_id,
            "channels": [channel.model_dump() for channel in channels],
            "count": len(channels)
        }
        
        log_tool_call("discord.list_channels", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list channels for guild {guild_id}: {e}")
        log_tool_call("discord.list_channels", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def get_channel(channel_id: str) -> Dict[str, Any]:
    """채널 정보 조회"""
    set_request_context(tool_name="discord.get_channel", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        channel = await _discord_client.get_channel(channel_id)
        result = {"channel": channel.model_dump()}
        
        log_tool_call("discord.get_channel", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get channel {channel_id}: {e}")
        log_tool_call("discord.get_channel", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def create_channel(
    guild_id: str,
    name: str,
    type: int = 0,
    topic: Optional[str] = None,
    parent_id: Optional[str] = None
) -> Dict[str, Any]:
    """채널 생성"""
    set_request_context(tool_name="discord.create_channel", channel_id=guild_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        channel = await _discord_client.create_channel(
            guild_id=guild_id,
            name=name,
            type=type,
            topic=topic,
            parent_id=parent_id
        )
        result = {"channel": channel.model_dump()}
        
        log_tool_call("discord.create_channel", channel_id=guild_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to create channel in guild {guild_id}: {e}")
        log_tool_call("discord.create_channel", channel_id=guild_id, success=False, error_message=str(e))
        raise


async def update_channel(
    channel_id: str,
    name: Optional[str] = None,
    topic: Optional[str] = None,
    position: Optional[int] = None
) -> Dict[str, Any]:
    """채널 정보 수정"""
    set_request_context(tool_name="discord.update_channel", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        channel = await _discord_client.update_channel(
            channel_id=channel_id,
            name=name,
            topic=topic,
            position=position
        )
        result = {"channel": channel.model_dump()}
        
        log_tool_call("discord.update_channel", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to update channel {channel_id}: {e}")
        log_tool_call("discord.update_channel", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def delete_channel(channel_id: str) -> Dict[str, Any]:
    """채널 삭제"""
    set_request_context(tool_name="discord.delete_channel", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.delete_channel(channel_id)
        result = {"message": f"Channel {channel_id} deleted successfully"}
        
        log_tool_call("discord.delete_channel", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete channel {channel_id}: {e}")
        log_tool_call("discord.delete_channel", channel_id=channel_id, success=False, error_message=str(e))
        raise


# 툴 등록
def register_channel_tools():
    """채널 관련 툴 등록"""
    
    # discord.list_guilds
    tool_registry.register_tool(
        name="discord.list_guilds",
        handler=list_guilds,
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="봇이 속한 길드 목록을 조회합니다."
    )
    
    # discord.list_channels
    tool_registry.register_tool(
        name="discord.list_channels",
        handler=list_channels,
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
        description="지정된 길드의 채널 목록을 조회합니다."
    )
    
    # discord.get_channel
    tool_registry.register_tool(
        name="discord.get_channel",
        handler=get_channel,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                }
            },
            "required": ["channel_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="지정된 채널의 정보를 조회합니다."
    )
    
    # discord.create_channel
    tool_registry.register_tool(
        name="discord.create_channel",
        handler=create_channel,
        input_schema={
            "type": "object",
            "properties": {
                "guild_id": {
                    "type": "string",
                    "description": "길드 ID"
                },
                "name": {
                    "type": "string",
                    "description": "채널 이름"
                },
                "type": {
                    "type": "integer",
                    "description": "채널 타입 (0: 텍스트, 2: 음성, 4: 카테고리)",
                    "default": 0
                },
                "topic": {
                    "type": "string",
                    "description": "채널 주제"
                },
                "parent_id": {
                    "type": "string",
                    "description": "부모 채널 ID (카테고리)"
                }
            },
            "required": ["guild_id", "name"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="새로운 채널을 생성합니다."
    )
    
    # discord.update_channel
    tool_registry.register_tool(
        name="discord.update_channel",
        handler=update_channel,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "name": {
                    "type": "string",
                    "description": "새로운 채널 이름"
                },
                "topic": {
                    "type": "string",
                    "description": "새로운 채널 주제"
                },
                "position": {
                    "type": "integer",
                    "description": "새로운 채널 위치"
                }
            },
            "required": ["channel_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="채널 정보를 수정합니다."
    )
    
    # discord.delete_channel
    tool_registry.register_tool(
        name="discord.delete_channel",
        handler=delete_channel,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                }
            },
            "required": ["channel_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="채널을 삭제합니다."
    )
