"""
Discord MCP 서버.

프로토콜 계층은 공식 `mcp` SDK(MCPServer)가 전담한다. 이 모듈이 하는 일은
Discord 툴 함수들을 MCP 툴로 등록하고, DiscordClient의 수명주기를 관리하는 것뿐이다.
"""
import functools
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any, AsyncIterator, Dict, List, Optional

from loguru import logger
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from .adapters.discord.http import DiscordClient
from .config import Settings
from .core.cache import cache_manager
from .core.errors import explain
from .core.health import get_health, get_metrics
from .tools.discord import advanced, channels, messages, reactions, roles, threads

TOOL_MODULES = (channels, messages, threads, reactions, roles, advanced)

# 읽기 전용 / 파괴적 동작 힌트. MCP 클라이언트가 승인 UI를 다르게 걸 수 있도록
# 각 툴에 annotation을 붙인다 (MCP spec의 tool annotations).
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True)

# Message Content Intent 비트 (application flags).
# 없으면 Discord가 봇에게 content/embeds/attachments를 조용히 비워서 준다.
GATEWAY_MESSAGE_CONTENT = 1 << 18
GATEWAY_MESSAGE_CONTENT_LIMITED = 1 << 19

# ------------------------------------------------------------------ 인자 타입
# MCP 클라이언트가 모델에게 보여주는 것은 이 description뿐이다. 타입 힌트만
# 있으면 스키마에 `"title": "Has"` 같은 것만 남아서, 모델은 인자의 의미를
# 추측하게 된다. 추측이 틀리면 툴 호출이 실패한다.
ChannelId = Annotated[str, Field(description="Discord channel snowflake id (numeric string). Get it from list_channels.")]
MessageId = Annotated[str, Field(description="Discord message snowflake id. Get it from list_messages.")]
GuildId = Annotated[Optional[str], Field(description="Guild (server) snowflake id. Optional when DISCORD_GUILD_ID is configured.")]
ThreadId = Annotated[str, Field(description="Thread snowflake id, from list_threads or create_thread.")]
Emoji = Annotated[str, Field(description="Unicode emoji (👍) or a custom emoji as name:id.")]
EmbedList = Annotated[
    Optional[List[Dict[str, Any]]],
    Field(description="Rich embeds. Each is an object with optional title, description, url, color (int) and fields:[{name, value}]."),
]


@dataclass
class AppContext:
    """lifespan이 만들어 툴 호출 동안 살아있는 리소스."""
    discord: DiscordClient
    settings: Settings


def _tool_errors(fn):
    """툴이 던진 예외를 모델이 읽을 수 있는 `ToolError`로 바꾼다.

    SDK 규약상 `ToolError`만 메시지가 클라이언트에 전달되고, 나머지 예외는
    크래시로 분류돼 `Error executing tool <name>`만 남는다. 이 래퍼가 없으면
    403 Missing Access도, 잘못된 id도, rate limit도 모델 눈에는 똑같이 보인다.

    `functools.wraps`가 `__wrapped__`를 남기므로 SDK의 `inspect.signature`는
    원본 시그니처를 그대로 읽는다 — 입력 스키마 생성은 영향받지 않는다.
    """
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except ToolError:
            raise
        except Exception as exc:  # noqa: BLE001 - 여기서 전부 문장으로 바꾼다
            logger.warning("{} failed: {}", fn.__name__.lstrip("_"), exc)
            raise ToolError(explain(exc)) from exc
    return wrapper


async def _warn_if_content_intent_disabled(client: DiscordClient) -> None:
    """Message Content Intent가 꺼져 있으면 시작 시 알린다.

    꺼져 있으면 모든 메시지의 본문이 빈 문자열로 오는데, Discord는 에러를 주지
    않는다. 조용히 빈 채널처럼 보이는 이 상태가 서버가 "안 읽히는" 가장 흔한 원인이다.
    """
    try:
        app = await client.get_application_info()
        flags = int(app.get("flags") or 0)
    except Exception as exc:  # noqa: BLE001 - 진단이 기동을 막아서는 안 된다
        logger.debug("could not read application flags: {}", exc)
        return

    if not flags & (GATEWAY_MESSAGE_CONTENT | GATEWAY_MESSAGE_CONTENT_LIMITED):
        logger.warning(
            "Message Content Intent is disabled for this bot — Discord will return empty "
            "content for every message. Enable it at Developer Portal -> your application -> "
            "Bot -> Privileged Gateway Intents -> Message Content Intent, then restart."
        )


def build_server(settings: Settings) -> MCPServer:
    """설정을 받아 툴이 전부 등록된 MCPServer를 만든다."""

    @asynccontextmanager
    async def lifespan(_server: MCPServer) -> AsyncIterator[AppContext]:
        client = DiscordClient(settings.bot_token, base_url=settings.api_base_url)
        await client.connect()
        for module in TOOL_MODULES:
            module.set_discord_client(client)
        await cache_manager.connect()
        await _warn_if_content_intent_disabled(client)
        logger.info("discord-mcp ready ({} tools)", len(_server._tool_manager.list_tools()))
        try:
            yield AppContext(discord=client, settings=settings)
        finally:
            await client.disconnect()
            await cache_manager.disconnect()

    mcp = MCPServer(
        name="discord-mcp",
        title="Discord",
        version="2.1.0",
        instructions=(
            "Read and write Discord through a bot token. Channel and message IDs are "
            "Discord snowflakes (numeric strings). Use list_guilds then list_channels "
            "to discover IDs before calling anything that needs them. If a tool reports "
            "missing access or permissions, call get_permissions with the channel_id to "
            "see exactly which permission is absent."
            + (
                f" A default guild is configured ({settings.default_guild_id}); "
                "guild_id may be omitted on guild-scoped tools."
                if settings.default_guild_id
                else ""
            )
        ),
        lifespan=lifespan,
    )

    def guild(guild_id: Optional[str]) -> str:
        """guild_id를 확정한다. 없으면 DISCORD_GUILD_ID로 대체."""
        resolved = guild_id or settings.default_guild_id
        if not resolved:
            raise ValueError(
                "guild_id is required. Pass it explicitly, or set the "
                "DISCORD_GUILD_ID environment variable to make it optional."
            )
        return resolved

    # ---------------------------------------------------------------- guilds
    @mcp.tool(name="list_guilds", annotations=READ_ONLY)
    @_tool_errors
    async def _list_guilds() -> Dict[str, Any]:
        """List every Discord server (guild) the bot has been added to. Returns guild ids and names — start here when you do not know a guild_id."""
        return await channels.list_guilds()

    # -------------------------------------------------------------- channels
    @mcp.tool(name="list_channels", annotations=READ_ONLY)
    @_tool_errors
    async def _list_channels(guild_id: GuildId = None) -> Dict[str, Any]:
        """List all channels in a guild, with their ids, names and types. Use this to find the channel_id for messaging tools."""
        return await channels.list_channels(guild(guild_id))

    @mcp.tool(name="get_channel", annotations=READ_ONLY)
    @_tool_errors
    async def _get_channel(channel_id: ChannelId) -> Dict[str, Any]:
        """Get details for a single channel: name, type, topic, parent category and NSFW flag."""
        return await channels.get_channel(channel_id)

    @mcp.tool(name="create_channel", annotations=WRITE)
    @_tool_errors
    async def _create_channel(
        name: Annotated[str, Field(description="Channel name, 1-100 characters.", min_length=1, max_length=100)],
        guild_id: GuildId = None,
        type: Annotated[int, Field(description="Discord channel type: 0 text, 2 voice, 4 category, 5 announcement, 15 forum.")] = 0,
        topic: Annotated[Optional[str], Field(description="Channel topic, up to 1024 characters. Text channels only.")] = None,
        parent_id: Annotated[Optional[str], Field(description="Id of the category channel (type 4) to nest this under.")] = None,
    ) -> Dict[str, Any]:
        """Create a channel in a guild. Requires the Manage Channels permission."""
        return await channels.create_channel(
            guild_id=guild(guild_id), name=name, type=type, topic=topic, parent_id=parent_id
        )

    @mcp.tool(name="update_channel", annotations=WRITE)
    @_tool_errors
    async def _update_channel(
        channel_id: ChannelId,
        name: Annotated[Optional[str], Field(description="New channel name.", max_length=100)] = None,
        topic: Annotated[Optional[str], Field(description="New channel topic.", max_length=1024)] = None,
        position: Annotated[Optional[int], Field(description="New sidebar position, 0 is topmost.", ge=0)] = None,
    ) -> Dict[str, Any]:
        """Rename a channel, change its topic, or move it in the sidebar. Only the fields you pass are changed."""
        return await channels.update_channel(
            channel_id=channel_id, name=name, topic=topic, position=position
        )

    @mcp.tool(name="delete_channel", annotations=DESTRUCTIVE)
    @_tool_errors
    async def _delete_channel(channel_id: ChannelId) -> Dict[str, Any]:
        """Permanently delete a channel and all of its message history. This cannot be undone — confirm with the user first."""
        return await channels.delete_channel(channel_id)

    # -------------------------------------------------------------- messages
    @mcp.tool(name="list_messages", annotations=READ_ONLY)
    @_tool_errors
    async def _list_messages(
        channel_id: ChannelId,
        limit: Annotated[int, Field(description="How many messages to return. Paged internally past Discord's 100-per-request cap.", ge=1, le=500)] = 50,
        after: Annotated[Optional[str], Field(description="Return only messages newer than this message id.")] = None,
        before: Annotated[Optional[str], Field(description="Return only messages older than this message id. Use oldest_message_id from a previous call to page back.")] = None,
        around: Annotated[Optional[str], Field(description="Return messages centred on this message id. Caps at 100 and cannot be combined with paging.")] = None,
        include_pins: Annotated[bool, Field(description="Also return the channel's pinned messages.")] = False,
        content_limit: Annotated[int, Field(description="Cut each message body to this many characters. 0 returns full text, which is expensive over many messages — prefer get_message for the few you need in full.", ge=0, le=4000)] = 500,
    ) -> Dict[str, Any]:
        """Read recent messages from a channel, newest first. Bodies are cut to content_limit characters; returns oldest_message_id/newest_message_id as paging cursors."""
        return await messages.list_messages(
            channel_id=channel_id, limit=limit, after=after, before=before,
            around=around, include_pins=include_pins, content_limit=content_limit,
        )

    @mcp.tool(name="get_message", annotations=READ_ONLY)
    @_tool_errors
    async def _get_message(channel_id: ChannelId, message_id: MessageId) -> Dict[str, Any]:
        """Fetch one message by id with its full, untruncated text, plus embeds, reactions and attachments. Use this after a list or search shows a body was cut."""
        return await messages.get_message(channel_id, message_id)

    @mcp.tool(name="send_message", annotations=WRITE)
    @_tool_errors
    async def _send_message(
        channel_id: ChannelId,
        content: Annotated[str, Field(description="Message text, Discord markdown, max 2000 characters. @everyone/@here are stripped.", max_length=2000)],
        embeds: EmbedList = None,
        tts: Annotated[bool, Field(description="Send as text-to-speech.")] = False,
    ) -> Dict[str, Any]:
        """Post a message to a channel. All mentions are disabled server-side, so the message cannot ping anyone."""
        return await messages.send_message(
            channel_id=channel_id, content=content, embeds=embeds, tts=tts
        )

    @mcp.tool(name="edit_message", annotations=WRITE)
    @_tool_errors
    async def _edit_message(
        channel_id: ChannelId,
        message_id: MessageId,
        content: Annotated[str, Field(description="Replacement text, max 2000 characters.", max_length=2000)],
        embeds: EmbedList = None,
    ) -> Dict[str, Any]:
        """Replace the content of a message the bot itself sent. Bots cannot edit other users' messages."""
        return await messages.edit_message(
            channel_id=channel_id, message_id=message_id, content=content, embeds=embeds
        )

    @mcp.tool(name="delete_message", annotations=DESTRUCTIVE)
    @_tool_errors
    async def _delete_message(channel_id: ChannelId, message_id: MessageId) -> Dict[str, Any]:
        """Delete a message. Deleting someone else's message requires the Manage Messages permission and cannot be undone."""
        return await messages.delete_message(channel_id, message_id)

    @mcp.tool(name="search_messages", annotations=READ_ONLY)
    @_tool_errors
    async def _search_messages(
        channel_id: ChannelId,
        query: Annotated[str, Field(description="Case-insensitive substring to find in message text, embed text or attachment filenames. Pass an empty string to filter by author/has alone.")],
        author_id: Annotated[Optional[str], Field(description="Only match messages from this user id.")] = None,
        has: Annotated[Optional[str], Field(description="Only match messages containing: link, embed, file or image.")] = None,
        scan_limit: Annotated[int, Field(description="How far back to read before filtering. Higher is slower but searches deeper.", ge=1, le=1000)] = 200,
        max_results: Annotated[int, Field(description="How many matches to return. The result reports the total matched, so you can tell a narrow hit from a flood.", ge=1, le=100)] = 25,
        content_limit: Annotated[int, Field(description="Cut each matched body to this many characters. 0 returns full text.", ge=0, le=4000)] = 500,
        before: Annotated[Optional[str], Field(description="Start scanning from before this message id, to search further back.")] = None,
        after: Annotated[Optional[str], Field(description="Only scan messages newer than this message id.")] = None,
    ) -> Dict[str, Any]:
        """Search a channel by reading its recent history and filtering it here. Discord's server-side search is not available to bots, so this scans the most recent scan_limit messages — the result reports how far it looked and how many matched."""
        return await messages.search_messages(
            channel_id=channel_id, query=query, author_id=author_id, has=has,
            scan_limit=scan_limit, max_results=max_results, content_limit=content_limit,
            before=before, after=after,
        )

    # --------------------------------------------------------------- threads
    @mcp.tool(name="create_thread", annotations=WRITE)
    @_tool_errors
    async def _create_thread(
        channel_id: ChannelId,
        name: Annotated[str, Field(description="Thread name, 1-100 characters.", min_length=1, max_length=100)],
        message_id: Annotated[Optional[str], Field(description="Branch the thread off this existing message instead of starting a standalone one.")] = None,
        auto_archive_duration: Annotated[int, Field(description="Minutes of inactivity before auto-archiving: 60, 1440, 4320 or 10080.")] = 1440,
    ) -> Dict[str, Any]:
        """Start a thread in a channel."""
        return await threads.create_thread(
            channel_id=channel_id, name=name, message_id=message_id,
            auto_archive_duration=auto_archive_duration,
        )

    @mcp.tool(name="list_threads", annotations=READ_ONLY)
    @_tool_errors
    async def _list_threads(channel_id: ChannelId) -> Dict[str, Any]:
        """List the active threads under a channel, with their archive and lock state."""
        return await threads.list_threads(channel_id)

    @mcp.tool(name="archive_thread", annotations=WRITE)
    @_tool_errors
    async def _archive_thread(thread_id: ThreadId) -> Dict[str, Any]:
        """Archive a thread. Archived threads stay readable and can be reopened with unarchive_thread."""
        return await threads.archive_thread(thread_id)

    @mcp.tool(name="unarchive_thread", annotations=WRITE)
    @_tool_errors
    async def _unarchive_thread(thread_id: ThreadId) -> Dict[str, Any]:
        """Reopen an archived thread."""
        return await threads.unarchive_thread(thread_id)

    # ----------------------------------------------- reactions / pins / hooks
    @mcp.tool(name="add_reaction", annotations=WRITE)
    @_tool_errors
    async def _add_reaction(channel_id: ChannelId, message_id: MessageId, emoji: Emoji) -> Dict[str, Any]:
        """React to a message as the bot."""
        return await reactions.add_reaction(channel_id, message_id, emoji)

    @mcp.tool(name="remove_reaction", annotations=WRITE)
    @_tool_errors
    async def _remove_reaction(channel_id: ChannelId, message_id: MessageId, emoji: Emoji) -> Dict[str, Any]:
        """Remove the bot's own reaction from a message."""
        return await reactions.remove_reaction(channel_id, message_id, emoji)

    @mcp.tool(name="list_reactions", annotations=READ_ONLY)
    @_tool_errors
    async def _list_reactions(
        channel_id: ChannelId,
        message_id: MessageId,
        emoji: Emoji,
        limit: Annotated[int, Field(description="Maximum users to return.", ge=1, le=100)] = 25,
    ) -> Dict[str, Any]:
        """List the users who reacted to a message with a given emoji."""
        return await reactions.list_reactions(channel_id, message_id, emoji, limit)

    @mcp.tool(name="pin_message", annotations=WRITE)
    @_tool_errors
    async def _pin_message(channel_id: ChannelId, message_id: MessageId) -> Dict[str, Any]:
        """Pin a message to its channel. A channel holds at most 50 pins."""
        return await reactions.pin_message(channel_id, message_id)

    @mcp.tool(name="unpin_message", annotations=WRITE)
    @_tool_errors
    async def _unpin_message(channel_id: ChannelId, message_id: MessageId) -> Dict[str, Any]:
        """Unpin a previously pinned message."""
        return await reactions.unpin_message(channel_id, message_id)

    @mcp.tool(name="create_webhook", annotations=WRITE)
    @_tool_errors
    async def _create_webhook(
        channel_id: ChannelId,
        name: Annotated[str, Field(description="Webhook display name.", min_length=1, max_length=80)],
        avatar: Annotated[Optional[str], Field(description="Avatar as a base64 data URI (data:image/png;base64,...).")] = None,
    ) -> Dict[str, Any]:
        """Create a webhook on a channel and return its URL. The URL is a credential — treat it as a secret. Requires the Manage Webhooks permission."""
        return await reactions.create_webhook(channel_id, name, avatar)

    @mcp.tool(name="list_webhooks", annotations=READ_ONLY)
    @_tool_errors
    async def _list_webhooks(channel_id: ChannelId) -> Dict[str, Any]:
        """List a channel's webhooks by id and name. URLs are withheld because they are credentials; you only need the id to delete one."""
        return await reactions.list_webhooks(channel_id)

    @mcp.tool(name="delete_webhook", annotations=DESTRUCTIVE)
    @_tool_errors
    async def _delete_webhook(
        webhook_id: Annotated[str, Field(description="Snowflake id of the webhook, from create_webhook or list_webhooks.")],
    ) -> Dict[str, Any]:
        """Revoke a webhook. Anyone holding its URL can post to the channel until this is done, so delete webhooks you created once you are finished with them."""
        return await reactions.delete_webhook(webhook_id)

    @mcp.tool(name="send_via_webhook", annotations=WRITE)
    @_tool_errors
    async def _send_via_webhook(
        webhook_url: Annotated[str, Field(description="Full webhook URL from create_webhook or Discord's channel settings.")],
        content: Annotated[str, Field(description="Message text, max 2000 characters. @everyone/@here are stripped.", max_length=2000)],
        username: Annotated[Optional[str], Field(description="Override the display name for this message.")] = None,
        avatar_url: Annotated[Optional[str], Field(description="Override the avatar image URL for this message.")] = None,
        embeds: EmbedList = None,
    ) -> Dict[str, Any]:
        """Post through a webhook URL, optionally overriding the display name and avatar. Returns the created message with its id, so it can be removed again with delete_message."""
        return await reactions.send_via_webhook(
            webhook_url=webhook_url, content=content, username=username,
            avatar_url=avatar_url, embeds=embeds,
        )

    # ----------------------------------------------------------------- roles
    @mcp.tool(name="list_roles", annotations=READ_ONLY)
    @_tool_errors
    async def _list_roles(guild_id: GuildId = None) -> Dict[str, Any]:
        """List a guild's roles with their ids, names and positions."""
        return await roles.list_roles(guild(guild_id))

    @mcp.tool(name="add_role", annotations=WRITE)
    @_tool_errors
    async def _add_role(
        user_id: Annotated[str, Field(description="Snowflake id of the guild member.")],
        role_id: Annotated[str, Field(description="Snowflake id of the role, from list_roles.")],
        guild_id: GuildId = None,
    ) -> Dict[str, Any]:
        """Grant a role to a member. The bot's own highest role must sit above the role being granted."""
        return await roles.add_role_to_member(guild(guild_id), user_id, role_id)

    @mcp.tool(name="remove_role", annotations=WRITE)
    @_tool_errors
    async def _remove_role(
        user_id: Annotated[str, Field(description="Snowflake id of the guild member.")],
        role_id: Annotated[str, Field(description="Snowflake id of the role, from list_roles.")],
        guild_id: GuildId = None,
    ) -> Dict[str, Any]:
        """Take a role away from a member."""
        return await roles.remove_role_from_member(guild(guild_id), user_id, role_id)

    @mcp.tool(name="get_permissions", annotations=READ_ONLY)
    @_tool_errors
    async def _get_permissions(
        guild_id: GuildId = None,
        channel_id: Annotated[Optional[str], Field(description="Resolve the bot's effective permissions inside this channel, with its overwrites applied.")] = None,
    ) -> Dict[str, Any]:
        """Show what the bot is actually allowed to do, by name, and which tools are blocked for lack of a permission. Call this first when a tool reports missing access or missing permissions."""
        return await roles.get_permissions(guild(guild_id), channel_id)

    # ------------------------------------------------------------- analytics
    @mcp.tool(name="summarize_messages", annotations=READ_ONLY)
    @_tool_errors
    async def _summarize_messages(
        channel_id: ChannelId,
        limit: Annotated[int, Field(description="How many recent messages to score.", ge=1, le=500)] = 50,
        keywords: Annotated[Optional[List[str]], Field(description="Terms that add to a message's score when present.")] = None,
        min_score: Annotated[float, Field(description="Drop messages scoring below this. Lower it if nothing comes back.", ge=0)] = 2.0,
        max_messages: Annotated[int, Field(description="Maximum messages to return.", ge=1, le=100)] = 10,
    ) -> Dict[str, Any]:
        """Pick out the most notable recent messages in a channel and return them for you to summarize. Scoring is heuristic (reactions, links, keyword hits) — this tool does not call a language model itself."""
        return await advanced.summarize_messages(
            channel_id=channel_id, limit=limit, keywords=keywords,
            min_score=min_score, max_messages=max_messages,
        )

    @mcp.tool(name="rank_messages", annotations=READ_ONLY)
    @_tool_errors
    async def _rank_messages(
        channel_id: ChannelId,
        limit: Annotated[int, Field(description="How many recent messages to rank.", ge=1, le=500)] = 100,
        keywords: Annotated[Optional[List[str]], Field(description="Terms that add to a message's score when present.")] = None,
        sort_by: Annotated[str, Field(description="One of: score, reactions, timestamp.")] = "score",
    ) -> Dict[str, Any]:
        """Rank a channel's recent messages by heuristic score, reaction count, or timestamp."""
        return await advanced.rank_messages(
            channel_id=channel_id, limit=limit, keywords=keywords, sort_by=sort_by
        )

    @mcp.tool(name="sync_since", annotations=READ_ONLY)
    @_tool_errors
    async def _sync_since(
        channel_id: ChannelId,
        last_message_id: Annotated[str, Field(description="The last message id you already processed. Use latest_message_id from the previous sync_since call.")],
        limit: Annotated[int, Field(description="Maximum new messages to return.", ge=1, le=100)] = 50,
    ) -> Dict[str, Any]:
        """Fetch only the messages posted after a given message id, and return the new cursor. Use this to catch up incrementally instead of re-reading a whole channel."""
        return await advanced.sync_since(channel_id, last_message_id, limit)

    @mcp.tool(name="analyze_channel_activity", annotations=READ_ONLY)
    @_tool_errors
    async def _analyze_channel_activity(
        channel_id: ChannelId,
        days: Annotated[int, Field(description="Only count messages from the last N days.", ge=1, le=365)] = 7,
        limit: Annotated[int, Field(description="Cap on messages read while covering the window. Raise it if the result reports truncation.", ge=1, le=2000)] = 1000,
    ) -> Dict[str, Any]:
        """Compute activity statistics for a channel over the last N days: message counts, top posters, and hourly distribution. Reports the actual time span it observed."""
        return await advanced.analyze_channel_activity(channel_id, days, limit)

    # ------------------------------------------------- operational endpoints
    # streamable-http로 띄웠을 때만 노출된다. stdio에서는 무의미하므로 무시된다.
    @mcp.custom_route("/health", methods=["GET"])
    async def _health(_request):  # pragma: no cover - thin passthrough
        from starlette.responses import JSONResponse

        return JSONResponse(await get_health())

    @mcp.custom_route("/metrics", methods=["GET"])
    async def _metrics(_request):  # pragma: no cover - thin passthrough
        from starlette.responses import JSONResponse

        return JSONResponse(await get_metrics())

    return mcp
