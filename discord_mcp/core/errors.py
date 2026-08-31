"""
Discord 실패를 모델이 읽고 고칠 수 있는 문장으로 바꾼다.

MCP SDK 2.1의 규약이 여기서 중요하다. 툴이 던진 예외 중 `ToolError`만
메시지가 클라이언트로 전달되고, 그 외 예외는 전부 "크래시"로 분류돼
모델에게는 `Error executing tool <name>`만 남는다. 원인은 서버 로그에 갇힌다.

이전 버전은 어댑터가 올린 `DiscordAPIError`를 그대로 재전파했다. 그래서
403 Missing Access도, 잘못된 channel_id도, rate limit도 모델 눈에는 전부
같은 한 줄이었고 스스로 고칠 방법이 없었다.
"""
from typing import Optional

from mcp.server.mcpserver.exceptions import ToolError

from .retry import DiscordAPIError, RateLimitError, TimeoutError
from .schema import MCPError

# https://discord.com/developers/docs/topics/opcodes-and-status-codes#json
# 모델이 실제로 다음 행동을 바꿀 수 있는 코드만 옮긴다.
_DISCORD_CODES = {
    10003: "Unknown channel — the channel_id does not exist, or the bot is not in that guild. "
           "Call list_channels to get valid ids.",
    10004: "Unknown guild — the bot is not a member of this guild. Call list_guilds.",
    10008: "Unknown message — the message_id does not exist in this channel, or it was deleted.",
    10011: "Unknown role — call list_roles for valid role ids.",
    10013: "Unknown user — the user_id is not a member of this guild.",
    30003: "This channel already has the maximum of 50 pinned messages. Unpin one first.",
    50001: "Missing Access — the bot cannot see this channel. Either it lacks View Channel, or a "
           "channel permission overwrite denies it. Call get_permissions with this channel_id to "
           "confirm, then grant the bot access in Discord.",
    50005: "Cannot edit a message authored by someone else. Bots may only edit their own messages.",
    50013: "Missing Permissions — the bot's role does not grant what this action needs. For role "
           "changes the bot's highest role must also sit above the role being changed.",
    50021: "Cannot act on a system message.",
    50035: "Discord rejected the request body as invalid. Check field lengths — message content "
           "caps at 2000 characters and channel names at 100.",
    160002: "Cannot start a thread on this message; one already exists.",
}

_STATUS_FALLBACK = {
    400: "Discord rejected the request as malformed.",
    401: "Discord rejected the bot token. DISCORD_BOT_TOKEN is wrong or was reset — "
         "reissue it in the Developer Portal under Bot → Reset Token.",
    403: "Forbidden — the bot lacks the permission this action requires. "
         "Call get_permissions to see what it actually has.",
    404: "Not found — the id does not exist or the bot cannot see it.",
    408: "The request to Discord timed out. Retry, or lower `limit` if you asked for a lot.",
    429: "Rate limited by Discord.",
}


def explain(exc: BaseException) -> str:
    """예외를 모델이 읽을 한 문장으로 만든다."""
    if isinstance(exc, RateLimitError):
        wait = f" Retry in about {exc.retry_after:.0f}s." if exc.retry_after else ""
        return f"Rate limited by Discord.{wait}"

    if isinstance(exc, TimeoutError):
        return _STATUS_FALLBACK[408]

    if isinstance(exc, DiscordAPIError):
        code = getattr(exc, "discord_code", None)
        if code in _DISCORD_CODES:
            return _DISCORD_CODES[code]
        status = exc.status_code
        if status in _STATUS_FALLBACK:
            # Discord가 준 원문도 붙여둔다 — 매핑에 없는 코드일 때 유일한 단서다.
            return f"{_STATUS_FALLBACK[status]} (Discord said: {exc})"
        return f"Discord API error: {exc}"

    if isinstance(exc, MCPError):
        return str(exc)

    return str(exc) or exc.__class__.__name__


def as_tool_error(exc: BaseException) -> ToolError:
    """`explain`을 붙여 SDK가 모델에게 전달하는 형태로 감싼다."""
    return ToolError(explain(exc))


def discord_code_of(payload: Optional[dict]) -> Optional[int]:
    """Discord 에러 응답 본문에서 숫자 코드를 꺼낸다."""
    if not isinstance(payload, dict):
        return None
    code = payload.get("code")
    return code if isinstance(code, int) else None
