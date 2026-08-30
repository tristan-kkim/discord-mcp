"""
Discord MCP 서버.

프로토콜 계층은 공식 `mcp` SDK(MCPServer)가 전담한다. 이 모듈이 하는 일은
Discord 툴 함수들을 MCP 툴로 등록하고, DiscordClient의 수명주기를 관리하는 것뿐이다.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from .adapters.discord.http import DiscordClient
from .config import Settings
from .core.cache import cache_manager
from .core.health import get_health, get_metrics
from .tools.discord import advanced, channels, messages, reactions, roles, threads

TOOL_MODULES = (channels, messages, threads, reactions, roles, advanced)

# 읽기 전용 / 파괴적 동작 힌트. MCP 클라이언트가 승인 UI를 다르게 걸 수 있도록
# 각 툴에 annotation을 붙인다 (MCP spec의 tool annotations).
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True)


@dataclass
class AppContext:
    """lifespan이 만들어 툴 호출 동안 살아있는 리소스."""
    discord: DiscordClient
    settings: Settings


def build_server(settings: Settings) -> MCPServer:
    """설정을 받아 툴이 전부 등록된 MCPServer를 만든다."""

    @asynccontextmanager
    async def lifespan(_server: MCPServer) -> AsyncIterator[AppContext]:
        client = DiscordClient(settings.bot_token, base_url=settings.api_base_url)
        await client.connect()
        for module in TOOL_MODULES:
            module.set_discord_client(client)
        await cache_manager.connect()
        logger.info("discord-mcp ready ({} tools)", len(_server._tool_manager.list_tools()))
        try:
            yield AppContext(discord=client, settings=settings)
        finally:
            await client.disconnect()
            await cache_manager.disconnect()

    mcp = MCPServer(
        name="discord-mcp",
        title="Discord",
        version="2.0.0",
        instructions=(
            "Read and write Discord through a bot token. Channel and message IDs are "
            "Discord snowflakes (numeric strings). Use list_guilds then list_channels "
            "to discover IDs before calling anything that needs them."
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
    async def _list_guilds() -> Dict[str, Any]:
        """List every Discord server (guild) the bot has been added to. Returns guild ids and names — start here when you do not know a guild_id."""
        return await channels.list_guilds()

    # -------------------------------------------------------------- channels
    @mcp.tool(name="list_channels", annotations=READ_ONLY)
    async def _list_channels(guild_id: Optional[str] = None) -> Dict[str, Any]:
        """List all channels in a guild, with their ids, names and types. Use this to find the channel_id for messaging tools."""
        return await channels.list_channels(guild(guild_id))

    @mcp.tool(name="get_channel", annotations=READ_ONLY)
    async def _get_channel(channel_id: str) -> Dict[str, Any]:
        """Get details for a single channel: name, type, topic, parent category and NSFW flag."""
        return await channels.get_channel(channel_id)

    @mcp.tool(name="create_channel", annotations=WRITE)
    async def _create_channel(
        name: str,
        guild_id: Optional[str] = None,
        type: int = 0,
        topic: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a channel in a guild. type is the Discord channel type: 0 text, 2 voice, 4 category, 5 announcement, 15 forum. Requires the Manage Channels permission."""
        return await channels.create_channel(
            guild_id=guild(guild_id), name=name, type=type, topic=topic, parent_id=parent_id
        )

    @mcp.tool(name="update_channel", annotations=WRITE)
    async def _update_channel(
        channel_id: str,
        name: Optional[str] = None,
        topic: Optional[str] = None,
        position: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Rename a channel, change its topic, or move it in the sidebar. Only the fields you pass are changed."""
        return await channels.update_channel(
            channel_id=channel_id, name=name, topic=topic, position=position
        )

    @mcp.tool(name="delete_channel", annotations=DESTRUCTIVE)
    async def _delete_channel(channel_id: str) -> Dict[str, Any]:
        """Permanently delete a channel and all of its message history. This cannot be undone — confirm with the user first."""
        return await channels.delete_channel(channel_id)

    # -------------------------------------------------------------- messages
    @mcp.tool(name="list_messages", annotations=READ_ONLY)
    async def _list_messages(
        channel_id: str,
        limit: int = 50,
        after: Optional[str] = None,
        before: Optional[str] = None,
        around: Optional[str] = None,
        include_pins: bool = False,
    ) -> Dict[str, Any]:
        """Read recent messages from a channel, newest first. limit caps at 100 per Discord. Use before/after with a message id to page through history."""
        return await messages.list_messages(
            channel_id=channel_id, limit=limit, after=after, before=before,
            around=around, include_pins=include_pins,
        )

    @mcp.tool(name="get_message", annotations=READ_ONLY)
    async def _get_message(channel_id: str, message_id: str) -> Dict[str, Any]:
        """Fetch one message by id, including its embeds, reactions and attachments."""
        return await messages.get_message(channel_id, message_id)

    @mcp.tool(name="send_message", annotations=WRITE)
    async def _send_message(
        channel_id: str,
        content: str,
        embeds: Optional[List[Dict[str, Any]]] = None,
        tts: bool = False,
    ) -> Dict[str, Any]:
        """Post a message to a channel. @everyone and @here are stripped automatically. content supports Discord markdown and is capped at 2000 characters."""
        return await messages.send_message(
            channel_id=channel_id, content=content, embeds=embeds, tts=tts
        )

    @mcp.tool(name="edit_message", annotations=WRITE)
    async def _edit_message(
        channel_id: str,
        message_id: str,
        content: str,
        embeds: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Replace the content of a message the bot itself sent. Bots cannot edit other users' messages."""
        return await messages.edit_message(
            channel_id=channel_id, message_id=message_id, content=content, embeds=embeds
        )

    @mcp.tool(name="delete_message", annotations=DESTRUCTIVE)
    async def _delete_message(channel_id: str, message_id: str) -> Dict[str, Any]:
        """Delete a message. Deleting someone else's message requires the Manage Messages permission and cannot be undone."""
        return await messages.delete_message(channel_id, message_id)

    @mcp.tool(name="search_messages", annotations=READ_ONLY)
    async def _search_messages(
        channel_id: str,
        query: str,
        author_id: Optional[str] = None,
        has: Optional[str] = None,
        max_id: Optional[str] = None,
        min_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search a channel's recent messages for a substring, optionally filtered by author or by attachment type (has: link, embed, file, image)."""
        return await messages.search_messages(
            channel_id=channel_id, query=query, author_id=author_id, has=has,
            max_id=max_id, min_id=min_id,
        )

    # --------------------------------------------------------------- threads
    @mcp.tool(name="create_thread", annotations=WRITE)
    async def _create_thread(
        channel_id: str,
        name: str,
        message_id: Optional[str] = None,
        auto_archive_duration: int = 1440,
    ) -> Dict[str, Any]:
        """Start a thread in a channel. Pass message_id to branch the thread off an existing message. auto_archive_duration is in minutes: 60, 1440, 4320 or 10080."""
        return await threads.create_thread(
            channel_id=channel_id, name=name, message_id=message_id,
            auto_archive_duration=auto_archive_duration,
        )

    @mcp.tool(name="list_threads", annotations=READ_ONLY)
    async def _list_threads(channel_id: str) -> Dict[str, Any]:
        """List the active threads under a channel, with their archive and lock state."""
        return await threads.list_threads(channel_id)

    @mcp.tool(name="archive_thread", annotations=WRITE)
    async def _archive_thread(thread_id: str) -> Dict[str, Any]:
        """Archive a thread. Archived threads stay readable and can be reopened with unarchive_thread."""
        return await threads.archive_thread(thread_id)

    @mcp.tool(name="unarchive_thread", annotations=WRITE)
    async def _unarchive_thread(thread_id: str) -> Dict[str, Any]:
        """Reopen an archived thread."""
        return await threads.unarchive_thread(thread_id)

    # ----------------------------------------------- reactions / pins / hooks
    @mcp.tool(name="add_reaction", annotations=WRITE)
    async def _add_reaction(channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
        """React to a message. emoji is a unicode character (👍) or a custom emoji as name:id."""
        return await reactions.add_reaction(channel_id, message_id, emoji)

    @mcp.tool(name="remove_reaction", annotations=WRITE)
    async def _remove_reaction(channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
        """Remove the bot's own reaction from a message."""
        return await reactions.remove_reaction(channel_id, message_id, emoji)

    @mcp.tool(name="list_reactions", annotations=READ_ONLY)
    async def _list_reactions(
        channel_id: str, message_id: str, emoji: str, limit: int = 25
    ) -> Dict[str, Any]:
        """List the users who reacted to a message with a given emoji."""
        return await reactions.list_reactions(channel_id, message_id, emoji, limit)

    @mcp.tool(name="pin_message", annotations=WRITE)
    async def _pin_message(channel_id: str, message_id: str) -> Dict[str, Any]:
        """Pin a message to its channel. A channel holds at most 50 pins."""
        return await reactions.pin_message(channel_id, message_id)

    @mcp.tool(name="unpin_message", annotations=WRITE)
    async def _unpin_message(channel_id: str, message_id: str) -> Dict[str, Any]:
        """Unpin a previously pinned message."""
        return await reactions.unpin_message(channel_id, message_id)

    @mcp.tool(name="create_webhook", annotations=WRITE)
    async def _create_webhook(
        channel_id: str, name: str, avatar: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a webhook on a channel and return its URL. The URL is a credential — treat it as a secret. Requires the Manage Webhooks permission."""
        return await reactions.create_webhook(channel_id, name, avatar)

    @mcp.tool(name="send_via_webhook", annotations=WRITE)
    async def _send_via_webhook(
        webhook_url: str,
        content: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Post through a webhook URL, optionally overriding the display name and avatar. Use this to post as a custom identity rather than as the bot."""
        return await reactions.send_via_webhook(
            webhook_url=webhook_url, content=content, username=username,
            avatar_url=avatar_url, embeds=embeds,
        )

    # ----------------------------------------------------------------- roles
    @mcp.tool(name="list_roles", annotations=READ_ONLY)
    async def _list_roles(guild_id: Optional[str] = None) -> Dict[str, Any]:
        """List a guild's roles with their ids, colors, positions and permission bitfields."""
        return await roles.list_roles(guild(guild_id))

    @mcp.tool(name="add_role", annotations=WRITE)
    async def _add_role(
        user_id: str, role_id: str, guild_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Grant a role to a member. The bot's own highest role must sit above the role being granted."""
        return await roles.add_role_to_member(guild(guild_id), user_id, role_id)

    @mcp.tool(name="remove_role", annotations=WRITE)
    async def _remove_role(
        user_id: str, role_id: str, guild_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Take a role away from a member."""
        return await roles.remove_role_from_member(guild(guild_id), user_id, role_id)

    @mcp.tool(name="get_permissions", annotations=READ_ONLY)
    async def _get_permissions(
        guild_id: Optional[str] = None, channel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect permissions for a guild, or for one channel's overwrites. Use this to diagnose why a write tool returned 403 Forbidden."""
        return await roles.get_permissions(guild(guild_id), channel_id)

    # ------------------------------------------------------------- analytics
    @mcp.tool(name="summarize_messages", annotations=READ_ONLY)
    async def _summarize_messages(
        channel_id: str,
        limit: int = 50,
        keywords: Optional[List[str]] = None,
        min_score: float = 2.0,
        max_messages: int = 10,
    ) -> Dict[str, Any]:
        """Pick out the most notable recent messages in a channel and return them for you to summarize. Scoring is heuristic (reactions, length, links, keyword hits) — this tool does not call a language model itself."""
        return await advanced.summarize_messages(
            channel_id=channel_id, limit=limit, keywords=keywords,
            min_score=min_score, max_messages=max_messages,
        )

    @mcp.tool(name="rank_messages", annotations=READ_ONLY)
    async def _rank_messages(
        channel_id: str,
        limit: int = 100,
        keywords: Optional[List[str]] = None,
        sort_by: str = "score",
    ) -> Dict[str, Any]:
        """Rank a channel's recent messages by heuristic score, reaction count, or timestamp. sort_by is one of: score, reactions, timestamp."""
        return await advanced.rank_messages(
            channel_id=channel_id, limit=limit, keywords=keywords, sort_by=sort_by
        )

    @mcp.tool(name="sync_since", annotations=READ_ONLY)
    async def _sync_since(
        channel_id: str, last_message_id: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Fetch only the messages posted after a given message id. Use this to catch up incrementally instead of re-reading a whole channel."""
        return await advanced.sync_since(channel_id, last_message_id, limit)

    @mcp.tool(name="analyze_channel_activity", annotations=READ_ONLY)
    async def _analyze_channel_activity(
        channel_id: str, days: int = 7, limit: int = 1000
    ) -> Dict[str, Any]:
        """Compute activity statistics for a channel over a recent window: message counts, top posters, and hourly distribution."""
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
