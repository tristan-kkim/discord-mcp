"""
Discord 고도화 기능 MCP 툴
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import re
from loguru import logger

from ...core.logging import log_tool_call, set_request_context
from ...adapters.discord.http import DiscordClient


# Discord 클라이언트 인스턴스
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


def calculate_message_score(message: Dict[str, Any], keywords: List[str] = None) -> float:
    """메시지 중요도 점수 계산"""
    score = 0.0
    
    # 리액션 수 (가중치 1.5)
    reactions = message.get("reactions", [])
    reaction_count = sum(reaction.get("count", 0) for reaction in reactions)
    score += reaction_count * 1.5
    
    # 링크 포함 (가중치 2.0)
    content = message.get("content", "")
    if "http" in content or "www." in content:
        score += 2.0
    
    # 키워드 매칭 (가중치 1.0)
    if keywords:
        content_lower = content.lower()
        for keyword in keywords:
            if keyword.lower() in content_lower:
                score += 1.0
    
    # 임베드 포함 (가중치 1.0)
    if message.get("embeds"):
        score += 1.0
    
    # 첨부파일 포함 (가중치 0.5)
    if message.get("attachments"):
        score += 0.5
    
    return score


async def summarize_messages(
    channel_id: str,
    limit: int = 50,
    keywords: Optional[List[str]] = None,
    min_score: float = 2.0,
    max_messages: int = 10
) -> Dict[str, Any]:
    """메시지 요약"""
    set_request_context(tool_name="summarize_messages", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 메시지 조회
        messages = await _discord_client.get_messages(
            channel_id=channel_id,
            limit=limit
        )
        
        # 메시지 점수 계산 및 정렬
        scored_messages = []
        for message in messages:
            message_dict = message.model_dump()
            score = calculate_message_score(message_dict, keywords)
            if score >= min_score:
                scored_messages.append((message_dict, score))
        
        # 점수순 정렬
        scored_messages.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 메시지 선택
        top_messages = scored_messages[:max_messages]
        
        # 요약 생성
        summary = {
            "channel_id": channel_id,
            "total_messages": len(messages),
            "filtered_messages": len(scored_messages),
            "summary_messages": len(top_messages),
            "keywords": keywords or [],
            "min_score": min_score,
            "messages": [
                {
                    "id": msg["id"],
                    "content": msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"],
                    "author": msg["author"]["username"],
                    "timestamp": msg["timestamp"],
                    "score": score,
                    "reactions": len(msg.get("reactions", [])),
                    "has_links": "http" in msg["content"] or "www." in msg["content"],
                    "has_embeds": bool(msg.get("embeds")),
                    "has_attachments": bool(msg.get("attachments"))
                }
                for msg, score in top_messages
            ]
        }
        
        log_tool_call("summarize_messages", channel_id=channel_id, success=True)
        return summary
        
    except Exception as e:
        logger.error(f"Failed to summarize messages in channel {channel_id}: {e}")
        log_tool_call("summarize_messages", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def rank_messages(
    channel_id: str,
    limit: int = 100,
    keywords: Optional[List[str]] = None,
    sort_by: str = "score"
) -> Dict[str, Any]:
    """메시지 중요도 순위"""
    set_request_context(tool_name="rank_messages", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 메시지 조회
        messages = await _discord_client.get_messages(
            channel_id=channel_id,
            limit=limit
        )
        
        # 메시지 점수 계산
        ranked_messages = []
        for message in messages:
            message_dict = message.model_dump()
            score = calculate_message_score(message_dict, keywords)
            
            ranked_messages.append({
                "id": message_dict["id"],
                "content": message_dict["content"][:100] + "..." if len(message_dict["content"]) > 100 else message_dict["content"],
                "author": message_dict["author"]["username"],
                "timestamp": message_dict["timestamp"],
                "score": score,
                "reactions": len(message_dict.get("reactions", [])),
                "has_links": "http" in message_dict["content"] or "www." in message_dict["content"],
                "has_embeds": bool(message_dict.get("embeds")),
                "has_attachments": bool(message_dict.get("attachments"))
            })
        
        # 정렬
        if sort_by == "score":
            ranked_messages.sort(key=lambda x: x["score"], reverse=True)
        elif sort_by == "reactions":
            ranked_messages.sort(key=lambda x: x["reactions"], reverse=True)
        elif sort_by == "timestamp":
            ranked_messages.sort(key=lambda x: x["timestamp"], reverse=True)
        
        result = {
            "channel_id": channel_id,
            "total_messages": len(messages),
            "keywords": keywords or [],
            "sort_by": sort_by,
            "ranked_messages": ranked_messages
        }
        
        log_tool_call("rank_messages", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to rank messages in channel {channel_id}: {e}")
        log_tool_call("rank_messages", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def sync_since(
    channel_id: str,
    last_message_id: str,
    limit: int = 50
) -> Dict[str, Any]:
    """마지막 메시지 ID 이후 동기화"""
    set_request_context(tool_name="sync_since", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 마지막 메시지 ID 이후 메시지 조회
        messages = await _discord_client.get_messages(
            channel_id=channel_id,
            limit=limit,
            after=last_message_id
        )
        
        # 새 메시지 ID 추출
        new_message_ids = [msg.id for msg in messages]
        latest_message_id = new_message_ids[0] if new_message_ids else last_message_id
        
        result = {
            "channel_id": channel_id,
            "last_message_id": last_message_id,
            "latest_message_id": latest_message_id,
            "new_messages": len(messages),
            "message_ids": new_message_ids,
            "messages": [msg.model_dump() for msg in messages]
        }
        
        log_tool_call("sync_since", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to sync messages since {last_message_id} in channel {channel_id}: {e}")
        log_tool_call("sync_since", channel_id=channel_id, success=False, error_message=str(e))
        raise


async def analyze_channel_activity(
    channel_id: str,
    days: int = 7,
    limit: int = 1000
) -> Dict[str, Any]:
    """채널 활동 분석"""
    set_request_context(tool_name="analyze_channel_activity", channel_id=channel_id)
    
    if not _discord_client:
        raise ValueError("Discord client not initialized")
    
    try:
        # 최근 메시지 조회
        messages = await _discord_client.get_messages(
            channel_id=channel_id,
            limit=limit
        )
        
        # 분석 데이터 수집
        author_counts = {}
        hourly_counts = {}
        daily_counts = {}
        reaction_counts = {}
        link_counts = 0
        embed_counts = 0
        
        for message in messages:
            msg_dict = message.model_dump()
            author = msg_dict["author"]["username"]
            timestamp = msg_dict["timestamp"]
            
            # 작성자별 카운트
            author_counts[author] = author_counts.get(author, 0) + 1
            
            # 시간대별 카운트
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour = dt.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                
                # 일별 카운트
                day = dt.date()
                daily_counts[str(day)] = daily_counts.get(str(day), 0) + 1
            except:
                pass
            
            # 리액션 카운트
            reactions = msg_dict.get("reactions", [])
            for reaction in reactions:
                emoji = reaction.get("emoji", {}).get("name", "unknown")
                reaction_counts[emoji] = reaction_counts.get(emoji, 0) + reaction.get("count", 0)
            
            # 링크 카운트
            if "http" in msg_dict["content"] or "www." in msg_dict["content"]:
                link_counts += 1
            
            # 임베드 카운트
            if msg_dict.get("embeds"):
                embed_counts += 1
        
        # 상위 통계
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_reactions = sorted(reaction_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        result = {
            "channel_id": channel_id,
            "analysis_period_days": days,
            "total_messages": len(messages),
            "unique_authors": len(author_counts),
            "top_authors": top_authors,
            "top_reactions": top_reactions,
            "most_active_hours": top_hours,
            "daily_activity": daily_counts,
            "link_ratio": link_counts / len(messages) if messages else 0,
            "embed_ratio": embed_counts / len(messages) if messages else 0,
            "avg_messages_per_author": len(messages) / len(author_counts) if author_counts else 0
        }
        
        log_tool_call("analyze_channel_activity", channel_id=channel_id, success=True)
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze channel activity for {channel_id}: {e}")
        log_tool_call("analyze_channel_activity", channel_id=channel_id, success=False, error_message=str(e))
        raise


# 툴 등록
