"""
Discord 객체를 모델이 읽을 만한 크기로 줄인다.

이전 버전은 pydantic 모델을 `model_dump()` 그대로 반환했다. 실측하면
채널 6개가 3.6k 토큰, 메시지 2건이 1.4k 토큰이었고 그중 80~90%는 `null`이다
(`bitrate`, `video_quality_mode`, `sticker_items`, `nonce`, ...). MCP 툴의
반환값은 전부 모델 컨텍스트를 차지하므로, 이 낭비가 곧 서버의 사용성이다.

여기서는 Discord 스키마를 그대로 옮기지 않고, **모델이 다음 툴 호출을 위해
실제로 필요로 하는 필드**만 고른다. 빠진 필드가 필요하면 get_* 툴이 있다.
"""
from typing import Any, Dict, List, Optional

# https://discord.com/developers/docs/resources/channel#channel-object-channel-types
CHANNEL_TYPES = {
    0: "text", 1: "dm", 2: "voice", 3: "group_dm", 4: "category",
    5: "announcement", 10: "announcement_thread", 11: "public_thread",
    12: "private_thread", 13: "stage", 14: "directory", 15: "forum", 16: "media",
}


# 목록을 돌려주는 툴의 기본 본문 미리보기 길이(문자).
# 컨텐트가 실려 오기 시작하면 크기 문제가 null 노이즈에서 본문으로 옮겨간다.
# 실측: Intent를 켠 뒤 list_messages(limit=150)이 32.5k 토큰이었다.
DEFAULT_CONTENT_LIMIT = 500


def _truncate(text: Optional[str], limit: Optional[int]) -> tuple[Optional[str], bool]:
    """`limit`자로 자르고 잘렸는지 알린다. limit이 None/0이면 그대로 둔다."""
    if not text or not limit or len(text) <= limit:
        return text, False
    return text[:limit].rstrip() + "…", True


def _drop_empty(d: Dict[str, Any]) -> Dict[str, Any]:
    """None과 빈 컬렉션을 턴다. False와 0은 정보이므로 남긴다."""
    return {k: v for k, v in d.items() if v is not None and v != [] and v != {} and v != ""}


def guild_brief(g: Dict[str, Any]) -> Dict[str, Any]:
    return _drop_empty({
        "id": g.get("id"),
        "name": g.get("name"),
        "owner": g.get("owner"),
    })


def channel_brief(c: Dict[str, Any]) -> Dict[str, Any]:
    kind = c.get("type")
    return _drop_empty({
        "id": c.get("id"),
        "name": c.get("name"),
        "type": CHANNEL_TYPES.get(kind, kind),
        "topic": c.get("topic"),
        "parent_id": c.get("parent_id"),
        "position": c.get("position"),
        "nsfw": c.get("nsfw") or None,
        "last_message_id": c.get("last_message_id"),
    })


def _author_brief(a: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not a:
        return None
    return _drop_empty({
        "id": a.get("id"),
        "name": a.get("global_name") or a.get("username"),
        "bot": a.get("bot") or None,
    })


def _embed_brief(e: Dict[str, Any], limit: Optional[int]) -> Dict[str, Any]:
    description, _ = _truncate(e.get("description"), limit)
    return _drop_empty({
        "title": e.get("title"),
        "description": description,
        "url": e.get("url"),
        "fields": [
            _drop_empty({"name": f.get("name"), "value": _truncate(f.get("value"), limit)[0]})
            for f in (e.get("fields") or [])
        ],
    })


def message_brief(m: Dict[str, Any], content_limit: Optional[int] = None) -> Dict[str, Any]:
    """메시지 하나를 투영한다.

    `content_limit`을 주면 본문과 임베드 텍스트를 그 길이로 자르고
    `truncated: true`를 붙인다. 전문이 필요하면 `get_message`로 그 id 하나만
    다시 부르면 된다 — 목록 전체를 전문으로 받는 것보다 훨씬 싸다.
    """
    reactions = [
        {"emoji": (r.get("emoji") or {}).get("name"), "count": r.get("count")}
        for r in (m.get("reactions") or [])
    ]
    ref = m.get("message_reference") or {}
    content, cut = _truncate(m.get("content"), content_limit)
    return _drop_empty({
        "id": m.get("id"),
        "author": _author_brief(m.get("author")),
        "content": content,
        "truncated": cut or None,
        "timestamp": m.get("timestamp"),
        "edited_timestamp": m.get("edited_timestamp"),
        "pinned": m.get("pinned") or None,
        "reply_to": ref.get("message_id"),
        "attachments": [
            _drop_empty({
                "filename": a.get("filename"),
                "url": a.get("url"),
                "content_type": a.get("content_type"),
            })
            for a in (m.get("attachments") or [])
        ],
        "embeds": [_embed_brief(e, content_limit) for e in (m.get("embeds") or [])],
        "reactions": reactions,
        "thread_id": (m.get("thread") or {}).get("id"),
    })


def role_brief(r: Dict[str, Any]) -> Dict[str, Any]:
    return _drop_empty({
        "id": r.get("id"),
        "name": r.get("name"),
        "position": r.get("position"),
        "managed": r.get("managed") or None,
        "mentionable": r.get("mentionable") or None,
        "permissions": r.get("permissions"),
    })


def thread_brief(t: Dict[str, Any]) -> Dict[str, Any]:
    meta = t.get("thread_metadata") or {}
    return _drop_empty({
        "id": t.get("id"),
        "name": t.get("name"),
        "parent_id": t.get("parent_id"),
        "message_count": t.get("message_count"),
        "member_count": t.get("member_count"),
        "archived": meta.get("archived") or None,
        "locked": meta.get("locked") or None,
        "auto_archive_duration": meta.get("auto_archive_duration"),
    })


def webhook_brief(w: Dict[str, Any]) -> Dict[str, Any]:
    return _drop_empty({
        "id": w.get("id"),
        "name": w.get("name"),
        "channel_id": w.get("channel_id"),
        "url": w.get("url"),
    })


def messages_brief(
    messages: List[Any], content_limit: Optional[int] = DEFAULT_CONTENT_LIMIT
) -> List[Dict[str, Any]]:
    """pydantic 모델 리스트든 dict 리스트든 받는다.

    목록 경로의 기본값은 잘라내기다. 한 번의 툴 호출이 컨텍스트를 통째로
    먹는 쪽이, 미리보기가 짧은 쪽보다 훨씬 나쁘다.
    """
    return [
        message_brief(m if isinstance(m, dict) else m.model_dump(), content_limit)
        for m in messages
    ]


# Message Content Intent가 꺼져 있으면 Discord는 content/embeds/attachments를
# 조용히 비워서 돌려준다. 에러가 아니라서 빈 채널과 구분이 안 되고, 실제로
# 이 서버가 "읽히지 않는" 가장 흔한 원인이다. 감지되면 대신 말해준다.
CONTENT_INTENT_HINT = (
    "Every message came back with empty content. This is almost always the Message Content "
    "Intent being disabled: Discord silently blanks content, embeds and attachments for bots "
    "without it. Turn it on at Developer Portal → your application → Bot → "
    "Privileged Gateway Intents → Message Content Intent, then restart the server."
)


def content_intent_warning(briefs: List[Dict[str, Any]]) -> Optional[str]:
    """전부 본문이 비어 있으면 경고 문자열, 아니면 None."""
    if not briefs:
        return None
    if any(b.get("content") or b.get("embeds") or b.get("attachments") for b in briefs):
        return None
    return CONTENT_INTENT_HINT
