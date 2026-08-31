"""
Discord 스레드 관련 MCP 툴
"""
from typing import Any, Dict, Optional
from loguru import logger

from ...core.logging import log_tool_call, set_request_context
from ...core.render import thread_brief
from ...adapters.discord.http import DiscordClient


# Discord 클라이언트 인스턴스
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


async def create_thread(
    channel_id: str,
    name: str,
    message_id: Optional[str] = None,
    auto_archive_duration: int = 1440
) -> Dict[str, Any]:
    """스레드 생성"""
    set_request_context(tool_name="create_thread", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        thread = await _discord_client.create_thread(
            channel_id=channel_id,
            name=name,
            message_id=message_id,
            auto_archive_duration=auto_archive_duration
        )
        
        result = {"thread": thread_brief(thread.model_dump())}
        
        log_tool_call("create_thread", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to create thread in channel {channel_id}: {e}")
        log_tool_call("create_thread", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def list_threads(channel_id: str) -> Dict[str, Any]:
    """스레드 목록 조회"""
    set_request_context(tool_name="list_threads", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        threads = await _discord_client.get_threads(channel_id)
        
        result = {
            "channel_id": channel_id,
            "threads": [thread_brief(thread.model_dump()) for thread in threads],
            "count": len(threads)
        }
        
        log_tool_call("list_threads", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list threads in channel {channel_id}: {e}")
        log_tool_call("list_threads", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def archive_thread(thread_id: str) -> Dict[str, Any]:
    """스레드 아카이브"""
    set_request_context(tool_name="archive_thread", channel_id=thread_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        thread = await _discord_client.archive_thread(thread_id)
        
        result = {"thread": thread_brief(thread.model_dump())}
        
        log_tool_call("archive_thread", channel_id=thread_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to archive thread {thread_id}: {e}")
        log_tool_call("archive_thread", channel_id=thread_id, success=False, error_message=str(e))
        raise


async def unarchive_thread(thread_id: str) -> Dict[str, Any]:
    """스레드 언아카이브"""
    set_request_context(tool_name="unarchive_thread", channel_id=thread_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        thread = await _discord_client.unarchive_thread(thread_id)
        
        result = {"thread": thread_brief(thread.model_dump())}
        
        log_tool_call("unarchive_thread", channel_id=thread_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to unarchive thread {thread_id}: {e}")
        log_tool_call("unarchive_thread", channel_id=thread_id, success=False, error_message=str(e))
        raise


# 툴 등록
