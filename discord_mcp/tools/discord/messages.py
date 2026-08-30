"""
Discord 메시지 관련 MCP 툴
"""
from typing import Any, Dict, List, Optional
from loguru import logger

from ...core.logging import log_tool_call, set_request_context
from ...adapters.discord.http import DiscordClient


# Discord 클라이언트 인스턴스 (나중에 의존성 주입으로 변경)
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


async def list_messages(
    channel_id: str,
    limit: int = 50,
    after: Optional[str] = None,
    before: Optional[str] = None,
    around: Optional[str] = None,
    include_pins: bool = False
) -> Dict[str, Any]:
    """메시지 목록 조회"""
    set_request_context(tool_name="list_messages", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        messages = await _discord_client.get_messages(
            channel_id=channel_id,
            limit=limit,
            after=after,
            before=before,
            around=around
        )
        
        # 고정된 메시지 포함 여부
        pinned_messages = []
        if include_pins:
            pinned_messages = await _discord_client.get_pinned_messages(channel_id)
        
        result = {
            "channel_id": channel_id,
            "messages": [message.model_dump() for message in messages],
            "pinned_messages": [msg.model_dump() for msg in pinned_messages] if include_pins else [],
            "count": len(messages),
            "pinned_count": len(pinned_messages) if include_pins else 0
        }
        
        log_tool_call("list_messages", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list messages in channel {channel_id}: {e}")
        log_tool_call("list_messages", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def get_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """특정 메시지 조회"""
    set_request_context(tool_name="get_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        message = await _discord_client.get_message(channel_id, message_id)
        result = {"message": message.model_dump()}
        
        log_tool_call("get_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to get message {message_id} in channel {channel_id}: {e}")
        log_tool_call("get_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def send_message(
    channel_id: str,
    content: str,
    embeds: Optional[List[Dict[str, Any]]] = None,
    tts: bool = False
) -> Dict[str, Any]:
    """메시지 전송"""
    set_request_context(tool_name="send_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 임베드 변환
        embed_objects = None
        if embeds:
            embed_objects = [DiscordEmbed(**embed) for embed in embeds]
        
        message = await _discord_client.send_message(
            channel_id=channel_id,
            content=content,
            embeds=embed_objects,
            tts=tts
        )
        
        result = {"message": message.model_dump()}
        
        log_tool_call("send_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to send message to channel {channel_id}: {e}")
        log_tool_call("send_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def edit_message(
    channel_id: str,
    message_id: str,
    content: str,
    embeds: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """메시지 수정"""
    set_request_context(tool_name="edit_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 임베드 변환
        embed_objects = None
        if embeds:
            embed_objects = [DiscordEmbed(**embed) for embed in embeds]
        
        message = await _discord_client.edit_message(
            channel_id=channel_id,
            message_id=message_id,
            content=content,
            embeds=embed_objects
        )
        
        result = {"message": message.model_dump()}
        
        log_tool_call("edit_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to edit message {message_id} in channel {channel_id}: {e}")
        log_tool_call("edit_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def delete_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """메시지 삭제"""
    set_request_context(tool_name="delete_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.delete_message(channel_id, message_id)
        result = {"message": f"Message {message_id} deleted successfully"}
        
        log_tool_call("delete_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete message {message_id} in channel {channel_id}: {e}")
        log_tool_call("delete_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def search_messages(
    channel_id: str,
    query: str,
    author_id: Optional[str] = None,
    has: Optional[str] = None,
    max_id: Optional[str] = None,
    min_id: Optional[str] = None
) -> Dict[str, Any]:
    """메시지 검색"""
    set_request_context(tool_name="search_messages", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        messages = await _discord_client.search_messages(
            channel_id=channel_id,
            query=query,
            author_id=author_id,
            has=has,
            max_id=max_id,
            min_id=min_id
        )
        
        result = {
            "channel_id": channel_id,
            "query": query,
            "messages": [message.model_dump() for message in messages],
            "count": len(messages)
        }
        
        log_tool_call("search_messages", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to search messages in channel {channel_id}: {e}")
        log_tool_call("search_messages", channel_id=channel_id, success=False, error_message=str(e))
        raise


# 툴 등록
