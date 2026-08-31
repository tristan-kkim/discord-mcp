"""
Discord 메시지 관련 MCP 툴.

반환값은 전부 `core.render`를 거친다. 툴의 반환값은 그대로 모델 컨텍스트를
차지하므로, Discord 스키마를 통째로 흘려보내지 않고 다음 행동에 필요한
필드만 남긴다.
"""
from typing import Any, Dict, List, Optional
from loguru import logger

from ...core.logging import log_tool_call, set_request_context
from ...core.render import (
    DEFAULT_CONTENT_LIMIT, content_intent_warning, message_brief, messages_brief,
)
from ...adapters.discord.http import DiscordClient
from ...adapters.discord.models import DiscordEmbed


# Discord 클라이언트 인스턴스 (나중에 의존성 주입으로 변경)
_discord_client: Optional[DiscordClient] = None


def set_discord_client(client: DiscordClient) -> None:
    """Discord 클라이언트 설정"""
    global _discord_client
    _discord_client = client


def _client() -> DiscordClient:
    if not _discord_client:
        raise RuntimeError("Discord client not initialized")
    return _discord_client


def _to_embeds(embeds: Optional[List[Dict[str, Any]]]) -> Optional[List[DiscordEmbed]]:
    """dict 임베드를 모델로 검증한다.

    이전 버전은 `DiscordEmbed`를 import하지 않고 여기서 썼다. embeds를 넘긴
    send_message/edit_message/send_via_webhook 호출은 전부 NameError로 죽었다.
    """
    if not embeds:
        return None
    try:
        return [DiscordEmbed(**embed) for embed in embeds]
    except Exception as exc:  # noqa: BLE001 - 모델이 고칠 수 있게 문장으로 바꾼다
        raise ValueError(
            f"embeds is malformed: {exc}. Each embed is an object with optional "
            "title, description, url, color and fields[{name, value}]."
        ) from exc


async def list_messages(
    channel_id: str,
    limit: int = 50,
    after: Optional[str] = None,
    before: Optional[str] = None,
    around: Optional[str] = None,
    include_pins: bool = False,
    content_limit: int = DEFAULT_CONTENT_LIMIT,
) -> Dict[str, Any]:
    """메시지 목록 조회"""
    set_request_context(tool_name="list_messages", channel_id=channel_id)

    if around:
        messages = await _client().get_messages(
            channel_id=channel_id, limit=min(limit, 100), around=around
        )
    else:
        messages = await _client().iter_messages(
            channel_id=channel_id, limit=limit, before=before, after=after
        )

    briefs = messages_brief(messages, content_limit or None)
    result: Dict[str, Any] = {
        "channel_id": channel_id,
        "messages": briefs,
        "count": len(briefs),
    }

    if include_pins:
        pinned = await _client().get_pinned_messages(channel_id)
        result["pinned_messages"] = messages_brief(pinned, content_limit or None)
        result["pinned_count"] = len(pinned)

    # 페이지네이션 커서를 돌려준다. 없으면 모델이 마지막 id를 직접 찾아야 한다.
    if briefs:
        result["oldest_message_id"] = briefs[-1]["id"]
        result["newest_message_id"] = briefs[0]["id"]

    cut = sum(1 for b in briefs if b.get("truncated"))
    if cut:
        result["truncated_messages"] = cut
        result["note"] = (
            f"{cut} message(s) were cut to {content_limit} characters. Call get_message with "
            "a specific id for its full text — that is far cheaper than raising content_limit "
            "across the whole list."
        )

    warning = content_intent_warning(briefs)
    if warning:
        result["warning"] = warning

    log_tool_call("list_messages", channel_id=channel_id, success=True)
    return result


async def get_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """특정 메시지 조회"""
    set_request_context(tool_name="get_message", channel_id=channel_id)

    message = await _client().get_message(channel_id, message_id)
    log_tool_call("get_message", channel_id=channel_id, success=True)
    return {"message": message_brief(message.model_dump())}


async def send_message(
    channel_id: str,
    content: str,
    embeds: Optional[List[Dict[str, Any]]] = None,
    tts: bool = False
) -> Dict[str, Any]:
    """메시지 전송"""
    set_request_context(tool_name="send_message", channel_id=channel_id)

    if len(content) > 2000:
        raise ValueError(
            f"content is {len(content)} characters; Discord caps a message at 2000. "
            "Split it across several send_message calls."
        )

    message = await _client().send_message(
        channel_id=channel_id, content=content, embeds=_to_embeds(embeds), tts=tts
    )

    log_tool_call("send_message", channel_id=channel_id, success=True)
    return {"message": message_brief(message.model_dump())}


async def edit_message(
    channel_id: str,
    message_id: str,
    content: str,
    embeds: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """메시지 수정"""
    set_request_context(tool_name="edit_message", channel_id=channel_id)

    message = await _client().edit_message(
        channel_id=channel_id, message_id=message_id, content=content,
        embeds=_to_embeds(embeds),
    )

    log_tool_call("edit_message", channel_id=channel_id, success=True)
    return {"message": message_brief(message.model_dump())}


async def delete_message(channel_id: str, message_id: str) -> Dict[str, Any]:
    """메시지 삭제"""
    set_request_context(tool_name="delete_message", channel_id=channel_id)

    await _client().delete_message(channel_id, message_id)
    log_tool_call("delete_message", channel_id=channel_id, success=True)
    return {"deleted": True, "message_id": message_id, "channel_id": channel_id}


async def search_messages(
    channel_id: str,
    query: str,
    author_id: Optional[str] = None,
    has: Optional[str] = None,
    scan_limit: int = 200,
    max_results: int = 25,
    content_limit: int = DEFAULT_CONTENT_LIMIT,
    before: Optional[str] = None,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """채널 기록을 훑어 검색.

    스캔은 깊게, 반환은 적게. 넓은 질의가 수백 건을 맞히면 전부 돌려주는 것이
    곧 컨텍스트 폭발이다 — 실측으로 `has=embed` 하나가 26k 토큰이었다.
    """
    set_request_context(tool_name="search_messages", channel_id=channel_id)

    messages = await _client().search_messages(
        channel_id=channel_id, query=query, author_id=author_id, has=has,
        scan_limit=scan_limit, before=before, after=after,
    )

    matched = len(messages)
    briefs = messages_brief(messages[:max_results], content_limit or None)

    notes = [
        f"Scanned the most recent {scan_limit} messages — Discord's server-side search is not "
        "available to bots. Raise scan_limit or pass before= to look further back."
    ]
    if matched > max_results:
        notes.append(
            f"{matched} messages matched; showing the {max_results} most recent. "
            "Narrow the query or raise max_results."
        )

    log_tool_call("search_messages", channel_id=channel_id, success=True)
    return {
        "channel_id": channel_id,
        "query": query,
        "messages": briefs,
        "count": len(briefs),
        "matched": matched,
        # 스캔 범위를 밝힌다. 못 찾은 게 "없다"인지 "더 뒤에 있다"인지 구분되도록.
        "scanned": scan_limit,
        "note": " ".join(notes),
    }
