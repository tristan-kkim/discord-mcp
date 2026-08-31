"""
Discord 권한 비트필드를 사람이 읽는 이름으로 푼다.

`get_permissions` 툴은 403의 원인을 짚기 위해 존재하는데, 이전 버전은
`"permissions": "2248491451018833"` 같은 원본 비트를 그대로 돌려줬다.
모델이 이 숫자로 할 수 있는 일이 없다. 여기서 이름으로 풀고, 채널
오버라이트까지 적용해 **실효 권한**을 계산한다.

https://discord.com/developers/docs/topics/permissions
"""
from typing import Any, Dict, Iterable, List, Optional

ADMINISTRATOR = 1 << 3

# 이 서버의 31개 툴이 실제로 요구하는 권한만 담는다.
PERMISSIONS: Dict[str, int] = {
    "CREATE_INSTANT_INVITE": 1 << 0,
    "KICK_MEMBERS": 1 << 1,
    "BAN_MEMBERS": 1 << 2,
    "ADMINISTRATOR": ADMINISTRATOR,
    "MANAGE_CHANNELS": 1 << 4,
    "MANAGE_GUILD": 1 << 5,
    "ADD_REACTIONS": 1 << 6,
    "VIEW_AUDIT_LOG": 1 << 7,
    "VIEW_CHANNEL": 1 << 10,
    "SEND_MESSAGES": 1 << 11,
    "SEND_TTS_MESSAGES": 1 << 12,
    "MANAGE_MESSAGES": 1 << 13,
    "EMBED_LINKS": 1 << 14,
    "ATTACH_FILES": 1 << 15,
    "READ_MESSAGE_HISTORY": 1 << 16,
    "MENTION_EVERYONE": 1 << 17,
    "USE_EXTERNAL_EMOJIS": 1 << 18,
    "MANAGE_WEBHOOKS": 1 << 29,
    "MANAGE_ROLES": 1 << 28,
    "MANAGE_THREADS": 1 << 34,
    # Discord가 MANAGE_MESSAGES에서 떼어낸 별도 권한. 이걸 MANAGE_MESSAGES로
    # 잘못 매핑해두면 get_permissions가 "핀 가능"이라 답하는데 Discord는 403을
    # 준다 — 진단 도구가 틀린 답을 확신하는 쪽이 답을 안 주는 쪽보다 나쁘다.
    "PIN_MESSAGES": 1 << 51,
    "CREATE_PUBLIC_THREADS": 1 << 35,
    "CREATE_PRIVATE_THREADS": 1 << 36,
    "SEND_MESSAGES_IN_THREADS": 1 << 38,
}

# 툴 → 그 툴이 없으면 403이 나는 권한.
TOOL_REQUIREMENTS: Dict[str, List[str]] = {
    "list_messages": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "get_message": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "search_messages": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "summarize_messages": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "rank_messages": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "sync_since": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "analyze_channel_activity": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "send_message": ["VIEW_CHANNEL", "SEND_MESSAGES"],
    "edit_message": ["VIEW_CHANNEL", "SEND_MESSAGES"],
    "delete_message": ["VIEW_CHANNEL", "MANAGE_MESSAGES"],
    "add_reaction": ["VIEW_CHANNEL", "ADD_REACTIONS", "READ_MESSAGE_HISTORY"],
    "remove_reaction": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "list_reactions": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "pin_message": ["VIEW_CHANNEL", "PIN_MESSAGES"],
    "unpin_message": ["VIEW_CHANNEL", "PIN_MESSAGES"],
    "create_thread": ["VIEW_CHANNEL", "CREATE_PUBLIC_THREADS"],
    "list_threads": ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY"],
    "archive_thread": ["VIEW_CHANNEL", "MANAGE_THREADS"],
    "unarchive_thread": ["VIEW_CHANNEL", "MANAGE_THREADS"],
    "create_channel": ["MANAGE_CHANNELS"],
    "update_channel": ["MANAGE_CHANNELS"],
    "delete_channel": ["MANAGE_CHANNELS"],
    "create_webhook": ["MANAGE_WEBHOOKS"],
    "list_webhooks": ["MANAGE_WEBHOOKS"],
    "delete_webhook": ["MANAGE_WEBHOOKS"],
    "add_role": ["MANAGE_ROLES"],
    "remove_role": ["MANAGE_ROLES"],
    "list_roles": [],
    "list_guilds": [],
    "list_channels": [],
    "get_channel": ["VIEW_CHANNEL"],
    "get_permissions": [],
    "send_via_webhook": [],
}


def decode(bits: Optional[str | int]) -> List[str]:
    """비트필드를 권한 이름 목록으로. ADMINISTRATOR면 전부 가진 것으로 본다."""
    if bits is None:
        return []
    value = int(bits)
    if value & ADMINISTRATOR:
        return sorted(PERMISSIONS)
    return sorted(name for name, bit in PERMISSIONS.items() if value & bit)


def effective_channel_permissions(
    base: Optional[str | int],
    guild_id: str,
    member_role_ids: Iterable[str],
    member_id: Optional[str],
    overwrites: Iterable[Dict[str, Any]],
) -> int:
    """길드 기본 권한에 채널 오버라이트를 Discord 순서대로 적용한다.

    @everyone → 역할들(deny를 모두 모은 뒤 allow) → 멤버 개별. ADMINISTRATOR는
    오버라이트를 무시하므로 그대로 통과시킨다.
    """
    permissions = int(base or 0)
    if permissions & ADMINISTRATOR:
        return permissions

    by_id = {str(o.get("id")): o for o in overwrites}

    everyone = by_id.get(str(guild_id))
    if everyone:
        permissions &= ~int(everyone.get("deny", 0))
        permissions |= int(everyone.get("allow", 0))

    role_deny = role_allow = 0
    for role_id in member_role_ids:
        overwrite = by_id.get(str(role_id))
        if overwrite:
            role_deny |= int(overwrite.get("deny", 0))
            role_allow |= int(overwrite.get("allow", 0))
    permissions &= ~role_deny
    permissions |= role_allow

    member = by_id.get(str(member_id)) if member_id else None
    if member:
        permissions &= ~int(member.get("deny", 0))
        permissions |= int(member.get("allow", 0))

    return permissions


def blocked_tools(granted: Iterable[str]) -> Dict[str, List[str]]:
    """현재 권한으로 실패할 툴과, 각각 무엇이 모자란지."""
    have = set(granted)
    if "ADMINISTRATOR" in have:
        return {}
    blocked = {}
    for tool, required in TOOL_REQUIREMENTS.items():
        missing = [r for r in required if r not in have]
        if missing:
            blocked[tool] = missing
    return blocked
