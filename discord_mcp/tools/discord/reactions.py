"""
Discord 리액션/핀/웹훅 관련 MCP 툴
"""
from typing import Any, Dict, List, Optional
from loguru import logger

from ...core.logging import log_tool_call, set_request_context
from ...core.render import message_brief, webhook_brief
from ...adapters.discord.http import DiscordClient
from ...adapters.discord.models import DiscordEmbed


# Discord 클라이언트 인스턴스
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


async def add_reaction(channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
    """리액션 추가"""
    set_request_context(tool_name="add_reaction", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.add_reaction(channel_id, message_id, emoji)
        
        result = {"message": f"Reaction {emoji} added to message {message_id}"}
        
        log_tool_call("add_reaction", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to add reaction to message {message_id}: {e}")
        log_tool_call("add_reaction", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def remove_reaction(channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
    """리액션 제거"""
    set_request_context(tool_name="remove_reaction", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.remove_reaction(channel_id, message_id, emoji)
        
        result = {"message": f"Reaction {emoji} removed from message {message_id}"}
        
        log_tool_call("remove_reaction", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to remove reaction from message {message_id}: {e}")
        log_tool_call("remove_reaction", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def list_reactions(
    channel_id: str,
    message_id: str,
    emoji: str,
    limit: int = 25
) -> Dict[str, Any]:
    """리액션 사용자 목록 조회"""
    set_request_context(tool_name="list_reactions", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        users = await _discord_client.get_reactions(channel_id, message_id, emoji, limit)
        
        result = {
            "channel_id": channel_id,
            "message_id": message_id,
            "emoji": emoji,
            "users": [{"id": u.id, "name": u.username} for u in users],
            "count": len(users)
        }
        
        log_tool_call("list_reactions", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list reactions for message {message_id}: {e}")
        log_tool_call("list_reactions", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def pin_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """메시지 고정"""
    set_request_context(tool_name="pin_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.pin_message(channel_id, message_id)
        
        result = {"message": f"Message {message_id} pinned successfully"}
        
        log_tool_call("pin_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to pin message {message_id}: {e}")
        log_tool_call("pin_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def unpin_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """메시지 고정 해제"""
    set_request_context(tool_name="unpin_message", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        await _discord_client.unpin_message(channel_id, message_id)
        
        result = {"message": f"Message {message_id} unpinned successfully"}
        
        log_tool_call("unpin_message", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to unpin message {message_id}: {e}")
        log_tool_call("unpin_message", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def create_webhook(
    channel_id: str,
    name: str,
    avatar: Optional[str] = None
) -> Dict[str, Any]:
    """웹훅 생성"""
    set_request_context(tool_name="create_webhook", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        webhook = await _discord_client.create_webhook(channel_id, name, avatar)
        
        result = {"webhook": webhook_brief(webhook.model_dump())}
        
        log_tool_call("create_webhook", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to create webhook in channel {channel_id}: {e}")
        log_tool_call("create_webhook", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def send_via_webhook(
    webhook_url: str,
    content: str,
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
    embeds: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """웹훅으로 메시지 전송"""
    set_request_context(tool_name="send_via_webhook")
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 임베드 변환
        embed_objects = None
        if embeds:
            embed_objects = [DiscordEmbed(**embed) for embed in embeds]
        
        sent = await _discord_client.send_webhook_message(
            webhook_url=webhook_url,
            content=content,
            username=username,
            avatar_url=avatar_url,
            embeds=embed_objects
        )

        # id와 channel_id를 돌려줘야 delete_message로 되돌릴 수 있다.
        result = {"message": message_brief(sent)}
        
        log_tool_call("send_via_webhook", success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to send message via webhook: {e}")
        log_tool_call("send_via_webhook", success=False, error_message=str(e))
        raise


# 툴 등록


async def list_webhooks(channel_id: str) -> Dict[str, Any]:
    """채널의 웹훅 목록"""
    set_request_context(tool_name="list_webhooks", channel_id=channel_id)

    if not _discord_client:
        raise RuntimeError("Discord client not initialized")

    hooks = await _discord_client.get_webhooks(channel_id)
    log_tool_call("list_webhooks", channel_id=channel_id, success=True)
    return {
        "channel_id": channel_id,
        # url은 자격증명이라 목록에서는 뺀다. 폐기에는 id만 있으면 된다.
        "webhooks": [
            {"id": h.get("id"), "name": h.get("name"), "channel_id": h.get("channel_id")}
            for h in hooks
        ],
        "count": len(hooks),
    }


async def delete_webhook(webhook_id: str) -> Dict[str, Any]:
    """웹훅 폐기"""
    set_request_context(tool_name="delete_webhook")

    if not _discord_client:
        raise RuntimeError("Discord client not initialized")

    await _discord_client.delete_webhook(webhook_id)
    log_tool_call("delete_webhook", success=True)
    return {"deleted": True, "webhook_id": webhook_id}
