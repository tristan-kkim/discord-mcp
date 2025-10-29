"""
Discord 스레드 관련 MCP 툴
"""
from typing import Any, Dict, Optional
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


async def create_thread(
    channel_id: str,
    name: str,
    message_id: Optional[str] = None,
    auto_archive_duration: int = 1440
) -> Dict[str, Any]:
    """스레드 생성"""
    set_request_context(tool_name="discord.create_thread", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        thread = await _discord_client.create_thread(
            channel_id=channel_id,
            name=name,
            message_id=message_id,
            auto_archive_duration=auto_archive_duration
        )
        
        result = {"thread": thread.model_dump()}
        
        log_tool_call("discord.create_thread", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to create thread in channel {channel_id}: {e}")
        log_tool_call("discord.create_thread", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def list_threads(channel_id: str) -> Dict[str, Any]:
    """스레드 목록 조회"""
    set_request_context(tool_name="discord.list_threads", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        threads = await _discord_client.get_threads(channel_id)
        
        result = {
            "channel_id": channel_id,
            "threads": [thread.model_dump() for thread in threads],
            "count": len(threads)
        }
        
        log_tool_call("discord.list_threads", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list threads in channel {channel_id}: {e}")
        log_tool_call("discord.list_threads", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def archive_thread(thread_id: str) -> Dict[str, Any]:
    """스레드 아카이브"""
    set_request_context(tool_name="discord.archive_thread", channel_id=thread_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        thread = await _discord_client.archive_thread(thread_id)
        
        result = {"thread": thread.model_dump()}
        
        log_tool_call("discord.archive_thread", channel_id=thread_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to archive thread {thread_id}: {e}")
        log_tool_call("discord.archive_thread", channel_id=thread_id, success=False, error_message=str(e))
        raise


async def unarchive_thread(thread_id: str) -> Dict[str, Any]:
    """스레드 언아카이브"""
    set_request_context(tool_name="discord.unarchive_thread", channel_id=thread_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        thread = await _discord_client.unarchive_thread(thread_id)
        
        result = {"thread": thread.model_dump()}
        
        log_tool_call("discord.unarchive_thread", channel_id=thread_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to unarchive thread {thread_id}: {e}")
        log_tool_call("discord.unarchive_thread", channel_id=thread_id, success=False, error_message=str(e))
        raise


# 툴 등록
def register_thread_tools():
    """스레드 관련 툴 등록"""
    
    # discord.create_thread
    tool_registry.register_tool(
        name="discord.create_thread",
        handler=create_thread,
        input_schema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "채널 ID"
                },
                "name": {
                    "type": "string",
                    "description": "스레드 이름"
                },
                "message_id": {
                    "type": "string",
                    "description": "메시지 ID (선택사항)"
                },
                "auto_archive_duration": {
                    "type": "integer",
                    "description": "자동 아카이브 지속 시간 (분)",
                    "default": 1440
                }
            },
            "required": ["channel_id", "name"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="새로운 스레드를 생성합니다."
    )
    
    # discord.list_threads
    tool_registry.register_tool(
        name="discord.list_threads",
        handler=list_threads,
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
        description="채널의 스레드 목록을 조회합니다."
    )
    
    # discord.archive_thread
    tool_registry.register_tool(
        name="discord.archive_thread",
        handler=archive_thread,
        input_schema={
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "스레드 ID"
                }
            },
            "required": ["thread_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="스레드를 아카이브합니다."
    )
    
    # discord.unarchive_thread
    tool_registry.register_tool(
        name="discord.unarchive_thread",
        handler=unarchive_thread,
        input_schema={
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "스레드 ID"
                }
            },
            "required": ["thread_id"]
        },
        output_schema=create_json_schema(Dict[str, Any]),
        description="스레드를 언아카이브합니다."
    )
