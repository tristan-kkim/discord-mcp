"""
채널 분석 계열 MCP 툴.

여기 있는 스코어러는 LLM이 아니다 — 리액션 수·링크·키워드 히트로 매기는
휴리스틱이고, 요약은 이 값을 받아본 MCP 반대편의 모델이 한다.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from ...core.logging import log_tool_call, set_request_context
from ...core.render import _truncate, content_intent_warning, messages_brief
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


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def calculate_message_score(message: Dict[str, Any], keywords: List[str] = None) -> float:
    """메시지 중요도 점수 계산 (휴리스틱)"""
    score = 0.0

    reactions = message.get("reactions", [])
    score += sum(reaction.get("count", 0) or 0 for reaction in reactions) * 1.5

    content = message.get("content", "") or ""
    if "http" in content or "www." in content:
        score += 2.0

    if keywords:
        content_lower = content.lower()
        score += sum(1.0 for keyword in keywords if keyword.lower() in content_lower)

    if message.get("embeds"):
        score += 1.0
    if message.get("attachments"):
        score += 0.5

    return score


# 순위/요약 출력의 미리보기 길이. 이 툴들은 "무엇을 더 볼지" 고르는 자리이지
# 읽는 자리가 아니다. 고른 다음에 get_message로 전문을 받으면 된다.
TRIAGE_PREVIEW = 200


def _preview(briefs: List[Dict[str, Any]], limit: int = TRIAGE_PREVIEW) -> List[Dict[str, Any]]:
    """출력 직전에만 자른다. 점수는 전문으로 매겨야 정확하다 —
    본문을 먼저 자르면 200자 뒤의 키워드와 링크가 점수에서 사라진다."""
    out = []
    for brief in briefs:
        content, cut = _truncate(brief.get("content"), limit)
        trimmed = dict(brief)
        if content is not None:
            trimmed["content"] = content
        if cut:
            trimmed["truncated"] = True
        trimmed.pop("embeds", None)  # 임베드 전문은 triage 단계에서 필요 없다
        out.append(trimmed)
    return out


async def _recent(channel_id: str, limit: int, days: Optional[int] = None) -> List[Dict[str, Any]]:
    """최근 메시지를 brief로. 본문은 자르지 않는다 — 점수 계산에 전문이 필요하다.
    days를 주면 그 창 안으로 자른다."""
    messages = await _client().iter_messages(channel_id=channel_id, limit=limit)
    briefs = messages_brief(messages, content_limit=None)
    if days is None:
        return briefs

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = []
    for brief in briefs:
        stamp = _parse_ts(brief.get("timestamp", ""))
        if stamp is None or stamp >= cutoff:
            kept.append(brief)
    return kept


async def summarize_messages(
    channel_id: str,
    limit: int = 50,
    keywords: Optional[List[str]] = None,
    min_score: float = 2.0,
    max_messages: int = 10
) -> Dict[str, Any]:
    """점수가 높은 메시지만 골라 돌려준다"""
    set_request_context(tool_name="summarize_messages", channel_id=channel_id)

    briefs = await _recent(channel_id, limit)
    scored = [(b, calculate_message_score(b, keywords)) for b in briefs]
    selected = sorted(
        [(b, s) for b, s in scored if s >= min_score], key=lambda x: x[1], reverse=True
    )[:max_messages]

    result = {
        "channel_id": channel_id,
        "scanned_messages": len(briefs),
        "returned_messages": len(selected),
        "keywords": keywords or [],
        "min_score": min_score,
        "scoring": "heuristic (reactions ×1.5, link +2, keyword hit +1, embed +1, attachment +0.5)",
        "messages": _preview([dict(b, score=s) for b, s in selected]),
        "note": (
            f"Bodies are previews of {TRIAGE_PREVIEW} characters, scored on the full text. "
            "Call get_message with an id for its complete content."
        ),
    }

    warning = content_intent_warning(briefs)
    if warning:
        result["warning"] = warning

    log_tool_call("summarize_messages", channel_id=channel_id, success=True)
    return result


async def rank_messages(
    channel_id: str,
    limit: int = 100,
    keywords: Optional[List[str]] = None,
    sort_by: str = "score"
) -> Dict[str, Any]:
    """메시지 순위"""
    set_request_context(tool_name="rank_messages", channel_id=channel_id)

    if sort_by not in ("score", "reactions", "timestamp"):
        raise ValueError(f"sort_by must be one of: score, reactions, timestamp (got {sort_by!r})")

    briefs = await _recent(channel_id, limit)
    ranked = []
    for brief in briefs:
        reactions = sum(r.get("count", 0) or 0 for r in brief.get("reactions", []))
        ranked.append(dict(brief, score=calculate_message_score(brief, keywords), reaction_total=reactions))

    key = {
        "score": lambda m: m["score"],
        "reactions": lambda m: m["reaction_total"],
        "timestamp": lambda m: m.get("timestamp", ""),
    }[sort_by]
    ranked.sort(key=key, reverse=True)

    log_tool_call("rank_messages", channel_id=channel_id, success=True)
    return {
        "channel_id": channel_id,
        "total_messages": len(ranked),
        "keywords": keywords or [],
        "sort_by": sort_by,
        "ranked_messages": _preview(ranked),
        "note": (
            f"Bodies are previews of {TRIAGE_PREVIEW} characters, scored on the full text. "
            "Call get_message with an id for its complete content."
        ),
    }


async def sync_since(
    channel_id: str,
    last_message_id: str,
    limit: int = 50
) -> Dict[str, Any]:
    """마지막 메시지 ID 이후 동기화"""
    set_request_context(tool_name="sync_since", channel_id=channel_id)

    messages = await _client().get_messages(
        channel_id=channel_id, limit=min(limit, 100), after=last_message_id
    )
    briefs = messages_brief(messages)

    log_tool_call("sync_since", channel_id=channel_id, success=True)
    return {
        "channel_id": channel_id,
        "last_message_id": last_message_id,
        # 다음 sync_since에 그대로 넘길 커서. 새 글이 없으면 입력값이 유지된다.
        "latest_message_id": briefs[0]["id"] if briefs else last_message_id,
        "new_messages": len(briefs),
        "messages": briefs,
    }


async def analyze_channel_activity(
    channel_id: str,
    days: int = 7,
    limit: int = 1000
) -> Dict[str, Any]:
    """채널 활동 분석.

    이전 버전은 `days`를 받아 출력에 되풀이할 뿐 필터링하지 않았고, limit도
    `min(limit, 100)`에 잘려 언제나 최근 100건이었다. 결과의 기간 표기는
    거짓이었다. 이제 실제로 days 창 안에서 집계하고, 실측 구간을 함께 보고한다.
    """
    set_request_context(tool_name="analyze_channel_activity", channel_id=channel_id)

    if days < 1:
        raise ValueError("days must be at least 1.")

    briefs = await _recent(channel_id, limit, days=days)

    author_counts: Dict[str, int] = {}
    hourly_counts: Dict[int, int] = {}
    daily_counts: Dict[str, int] = {}
    reaction_counts: Dict[str, int] = {}
    link_count = embed_count = 0
    stamps: List[datetime] = []

    for brief in briefs:
        author = (brief.get("author") or {}).get("name", "unknown")
        author_counts[author] = author_counts.get(author, 0) + 1

        stamp = _parse_ts(brief.get("timestamp", ""))
        if stamp:
            stamps.append(stamp)
            hourly_counts[stamp.hour] = hourly_counts.get(stamp.hour, 0) + 1
            day = str(stamp.date())
            daily_counts[day] = daily_counts.get(day, 0) + 1

        for reaction in brief.get("reactions", []):
            emoji = reaction.get("emoji") or "unknown"
            reaction_counts[emoji] = reaction_counts.get(emoji, 0) + (reaction.get("count") or 0)

        content = brief.get("content", "") or ""
        if "http" in content or "www." in content:
            link_count += 1
        if brief.get("embeds"):
            embed_count += 1

    total = len(briefs)
    result: Dict[str, Any] = {
        "channel_id": channel_id,
        "requested_days": days,
        # 요청한 창과 실제로 데이터가 있던 구간은 다르다. 둘 다 밝힌다.
        "observed_from": min(stamps).isoformat() if stamps else None,
        "observed_to": max(stamps).isoformat() if stamps else None,
        "total_messages": total,
        "unique_authors": len(author_counts),
        "top_authors": sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_reactions": sorted(reaction_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "most_active_hours_utc": sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        "daily_activity": dict(sorted(daily_counts.items())),
        "link_ratio": round(link_count / total, 3) if total else 0,
        "embed_ratio": round(embed_count / total, 3) if total else 0,
        "avg_messages_per_author": round(total / len(author_counts), 2) if author_counts else 0,
    }

    # limit에 걸려 창 전체를 못 봤으면 통계가 절단된 것이다. 조용히 넘기지 않는다.
    if total == limit:
        result["truncated"] = (
            f"Hit the {limit}-message scan limit, so this covers less than {days} days. "
            "Raise limit for the full window."
        )

    log_tool_call("analyze_channel_activity", channel_id=channel_id, success=True)
    return result
