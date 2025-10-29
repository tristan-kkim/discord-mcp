"""
Discord 리액션/핀/웹훅 관련 MCP 툴
"""
from typing import Any, Dict, List, Optional
from loguru import logger

from ...core.tool_registry import tool_registry
from ...core.schema import create_json_schema, DiscordEmbed
from ...core.logging import log_tool_call, set_request_context
from ...adapters.discord.http import DiscordClient


# Discord 클라이언트 인스턴스
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


async def add_reaction(channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
    """리액션 추가"""
    set_request_context(tool_name="discord.add_reaction", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.add_reaction(channel_id, message_id, emoji)
        
        result = {"message": f"Reaction {emoji} added to message {message_id}"}
        
        log_tool_call("discord.add_reaction", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to add reaction to message {message_id}: {e}")
        log_tool_call("discord.add_reaction", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def remove_reaction(channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
    """리액션 제거"""
    set_request_context(tool_name="discord.remove_reaction", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.remove_reaction(channel_id, message_id, emoji)
        
        result = {"message": f"Reaction {emoji} removed from message {message_id}"}
        
        log_tool_call("discord.remove_reaction", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to remove reaction from message {message_id}: {e}")
        log_tool_call("discord.remove_reaction", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def list_reactions(
    channel_id: str,
    message_id: str,
    emoji: str,
    limit: int = 25
) -> Dict[str, Any]:
    """리액션 사용자 목록 조회"""
    set_request_context(tool_name="discord.list_reactions", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        users = await _discord_client.get_reactions(channel_id, message_id, emoji, limit)
        
        result = {
            "channel_id": channel_id,
            "message_id": message_id,
            "emoji": emoji,
            "users": [user.model_dump() for user in users],
            "count": len(users)
        }
        
        log_tool_call("discord.list_reactions", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list reactions for message {message_id}: {e}")
        log_tool_call("discord.list_reactions", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def pin_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """메시지 고정"""
    set_request_context(tool_name="discord.pin_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.pin_message(channel_id, message_id)
        
        result = {"message": f"Message {message_id} pinned successfully"}
        
        log_tool_call("discord.pin_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to pin message {message_id}: {e}")
        log_tool_call("discord.pin_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def unpin_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """메시지 고정 해제"""
    set_request_context(tool_name="discord.unpin_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.unpin_message(channel_id, message_id)
        
        result = {"message": f"Message {message_id} unpinned successfully"}
        
        log_tool_call("discord.unpin_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to unpin message {message_id}: {e}")
        log_tool_call("discord.unpin_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def create_webhook(
    channel_id: str,
    name: str,
    avatar: Optional[str] = None
) -> Dict[str, Any]:
    """웹훅 생성"""
    set_request_context(tool_name="discord.create_webhook", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        webhook = await _discord_client.create_webhook(channel_id, name, avatar)
        
        result = {"webhook": webhook.model_dump()}
        
        log_tool_call("discord.create_webhook", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to create webhook in channel {channel_id}: {e}")
        log_tool_call("discord.create_webhook", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def send_via_webhook(
    webhook_url: str,
    content: str,
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
    embeds: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """웹훅으로 메시지 전송"""
    set_request_context(tool_name="discord.send_via_webhook")
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 임베드 변환
        embed_objects = None
        if embeds:
            embed_objects = [DiscordEmbed(**embed) for embed in embeds]
        
        await _discord_client.send_webhook_message(
            webhook_url=webhook_url,
            content=content,
            username=username,
            avatar_url=avatar_url,
            embeds=embed_objects
        )
        
        result = {"message": "Message sent via webhook successfully"}
        
        log_tool_call("discord.send_via_webhook", success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to send message via webhook: {e}")
        log_tool_call("discord.send_via_webhook", success=False, error_message=str(e))
        raise


# 툴 등록
def register_reaction_tools():
    """리액션/핀/웹훅 관련 툴 등록"""
    
    # discord.add_reaction
    tool_registry.register_tool(
        name="discord.add_reaction",
        handler=add_reaction,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "message_id": {
                    "type": "string",
                    "description": "메시지 ID"
                },
                "emoji": {
                    "type": "string",
                    "description": "이모지 (예: 😀, :smile:)"
                }
            },
            "required": ["channel_id", "message_id", "emoji"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="메시지에 리액션을 추가합니다."
    )
    
    # discord.remove_reaction
    tool_registry.register_tool(
        name="discord.remove_reaction",
        handler=remove_reaction,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "message_id": {
                    "type": "string",
                    "description": "메시지 ID"
                },
                "emoji": {
                    "type": "string",
                    "description": "이모지 (예: 😀, :smile:)"
                }
            },
            "required": ["channel_id", "message_id", "emoji"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="메시지에서 리액션을 제거합니다."
    )
    
    # discord.list_reactions
    tool_registry.register_tool(
        name="discord.list_reactions",
        handler=list_reactions,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "message_id": {
                    "type": "string",
                    "description": "메시지 ID"
                },
                "emoji": {
                    "type": "string",
                    "description": "이모지 (예: 😀, :smile:)"
                },
                "limit": {
                    "type": "integer",
                    "description": "조회할 사용자 수 (최대 100)",
                    "default": 25,
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": ["channel_id", "message_id", "emoji"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="리액션을 누른 사용자 목록을 조회합니다."
    )
    
    # discord.pin_message
    tool_registry.register_tool(
        name="discord.pin_message",
        handler=pin_message,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "message_id": {
                    "type": "string",
                    "description": "메시지 ID"
                }
            },
            "required": ["channel_id", "message_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="메시지를 고정합니다."
    )
    
    # discord.unpin_message
    tool_registry.register_tool(
        name="discord.unpin_message",
        handler=unpin_message,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "message_id": {
                    "type": "string",
                    "description": "메시지 ID"
                }
            },
            "required": ["channel_id", "message_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="메시지 고정을 해제합니다."
    )
    
    # discord.create_webhook
    tool_registry.register_tool(
        name="discord.create_webhook",
        handler=create_webhook,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "name": {
                    "type": "string",
                    "description": "웹훅 이름"
                },
                "avatar": {
                    "type": "string",
                    "description": "아바타 URL"
                }
            },
            "required": ["channel_id", "name"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="웹훅을 생성합니다."
    )
    
    # discord.send_via_webhook
    tool_registry.register_tool(
        name="discord.send_via_webhook",
        handler=send_via_webhook,
        input_schema={
            "type": "object",
            "properties": {
                "webhook_url": {
                    "type": "string",
                    "description": "웹훅 URL"
                },
                "content": {
                    "type": "string",
                    "description": "메시지 내용"
                },
                "username": {
                    "type": "string",
                    "description": "사용자명"
                },
                "avatar_url": {
                    "type": "string",
                    "description": "아바타 URL"
                },
                "embeds": {
                    "type": "array",
                    "description": "임베드 목록",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "color": {"type": "integer"},
                            "fields": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "value": {"type": "string"},
                                        "inline": {"type": "boolean"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "required": ["webhook_url", "content"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="웹훅을 통해 메시지를 전송합니다."
    )
