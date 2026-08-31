# Discord MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-2025--06--18-5865F2)](https://modelcontextprotocol.io)

A [Model Context Protocol](https://modelcontextprotocol.io) server for Discord. It gives an
MCP client — Claude Code, Claude Desktop, Cursor, or anything else that speaks MCP — 31 tools
for reading and writing Discord through a bot token.

Built on the official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) Python SDK,
so the protocol layer is the real thing: `initialize` / `tools/list` / `tools/call` over
JSON-RPC 2.0, on **stdio** or **Streamable HTTP**.

> **Upgrading from 1.x?** See [Breaking changes in 2.0](#breaking-changes-in-20). The 1.x
> server exposed a bespoke REST API that used MCP vocabulary but was not MCP, and no MCP
> client could connect to it.

## Quick start

### 1. Create a bot

1. [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**
2. **Bot** tab → **Reset Token** → copy it (this is `DISCORD_BOT_TOKEN`, not the client secret)
3. **Bot** tab → enable **Message Content Intent**. Without it Discord returns an empty
   `content` for every message *and reports no error*, so a busy channel is indistinguishable
   from an empty one. The server warns at startup and flags it on the affected responses, but
   the text itself is gone. Both the full and the limited (under 100 guilds) grant work.
4. **OAuth2 → URL Generator** → scope `bot` → pick permissions → open the URL to invite it

### 2. Install

```bash
pip install "discord-mcp[redis]"     # redis extra is optional
```

Or from source:

```bash
git clone https://github.com/tristan-kkim/discord-mcp.git
cd discord-mcp
pip install -e ".[dev]"
```

### 3. Point a client at it

**Claude Code**

```bash
claude mcp add discord --env DISCORD_BOT_TOKEN=your_token -- discord-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "discord": {
      "command": "discord-mcp",
      "env": {
        "DISCORD_BOT_TOKEN": "your_token_here",
        "DISCORD_GUILD_ID": "optional_default_guild_id"
      }
    }
  }
}
```

Restart the client, then ask it to `list_guilds`.

## Transports

| Transport | Command | Use for |
|---|---|---|
| **stdio** (default) | `discord-mcp` | Local clients — Claude Desktop, Claude Code, Cursor |
| **Streamable HTTP** | `discord-mcp --transport streamable-http --port 8000` | Remote/shared deployments, containers |

```
discord-mcp --transport streamable-http --host 0.0.0.0 --port 8000 --path /mcp
```

`--stateless` drops session affinity, for running several replicas behind a load balancer.

In HTTP mode the server also serves `GET /health` and `GET /metrics` alongside `/mcp`.
Those are operational endpoints, not MCP — they exist for container health checks and
scraping, and are absent in stdio mode where they would be meaningless.

## Configuration

| Variable | Description | Default | Required |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | Discord bot token (`DISCORD_TOKEN` also accepted) | — | ✅ |
| `DISCORD_GUILD_ID` | Default guild. When set, `guild_id` becomes optional on guild-scoped tools | — | ❌ |
| `REDIS_URL` | Response cache. Without it the server runs uncached | — | ❌ |
| `LOG_LEVEL` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` | `INFO` | ❌ |
| `DISCORD_API_BASE_URL` | Override the Discord API endpoint (tests, corporate proxy) | `https://discord.com/api/v10` | ❌ |

Logs are structured JSON on **stderr** — never stdout, which is the JSON-RPC channel under
stdio transport.

## Tools

33 tools. Every one carries a description and a JSON Schema, plus MCP
[tool annotations](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
(`readOnlyHint` / `destructiveHint`) so clients can gate destructive calls behind confirmation.

### Guilds & channels
`list_guilds` · `list_channels` · `get_channel` · `create_channel` · `update_channel` · `delete_channel` ⚠️

### Messages
`list_messages` · `get_message` · `send_message` · `edit_message` · `delete_message` ⚠️ · `search_messages`

### Threads
`create_thread` · `list_threads` · `archive_thread` · `unarchive_thread`

### Reactions, pins & webhooks
`add_reaction` · `remove_reaction` · `list_reactions` · `pin_message` · `unpin_message` · `create_webhook` · `list_webhooks` · `delete_webhook` ⚠️ · `send_via_webhook`

### Roles & permissions
`list_roles` · `add_role` · `remove_role` · `get_permissions`

### Channel analytics
`summarize_messages` · `rank_messages` · `sync_since` · `analyze_channel_activity`

⚠️ = annotated destructive.

Every argument carries a description and, where it applies, a range — so the model is told
what `has` accepts and that `limit` tops out, instead of guessing and burning a round trip.

**Responses are budgeted, not dumped.** Everything a tool returns lands in the model's
context, so each response keeps the fields you act on and drops the rest. Discord objects are
30-odd fields of which most are `null`; a six-channel `list_channels` went from ~1,200 tokens
to ~220. Message bodies are cut to `content_limit` characters (500 by default, `0` for full
text) with `truncated: true` and a count on the response — `get_message` returns any single
message in full, which is far cheaper than raising the limit across a whole list.
`search_messages` scans deep but returns `max_results` matches (25 by default) while
reporting how many actually matched, so a broad query cannot flood the context.

`rank_messages` and `summarize_messages` are triage: they score on the **full** text and then
preview 200 characters of it. Scoring before truncation matters — cut first and a link or
keyword past the preview silently stops counting.

**Failures explain themselves.** A tool that fails returns the reason and the fix — a `403`
comes back as *"Missing Access — the bot cannot see this channel… call `get_permissions` with
this channel_id"*, not as `Error executing tool list_messages`.

> **On `summarize_messages` and `rank_messages`:** these score messages with a *heuristic*
> (reaction count, links, keyword hits) and hand the top ones back. They do not call
> a language model — the model on the other end of the MCP connection does the summarizing.

> **On `search_messages`:** Discord's server-side search endpoint is closed to bots, so this
> reads the channel's recent history and filters it here — message text, embed text and
> attachment filenames. It searches the most recent `scan_limit` messages (200 by default)
> and says so in the result, so an empty result is never mistaken for "nothing exists".

> **On webhooks:** `create_webhook` mints a credential, so `delete_webhook` revokes one and
> `list_webhooks` finds the id (URLs are withheld from the listing — they *are* the
> credential). `send_via_webhook` returns the message it created, so `delete_message` can
> take it back; without that the tool leaves posts nothing can remove.

> **On pinning:** Discord split `PIN_MESSAGES` out of `MANAGE_MESSAGES`. A bot invited before
> that split can delete messages but not pin them, and `get_permissions` reports exactly that.
> Note that pinning also posts a visible "pinned a message" notice in the channel which
> `unpin_message` does not remove; it comes back labelled `system_event: pinned_a_message`, so
> `delete_message` can clear it.

> **On system messages:** joins, pins, thread creations and the like carry no body by design.
> They are labelled with `system_event` rather than appearing as blank entries, and they are
> excluded from the empty-content check — otherwise a channel of nothing but notices would be
> reported as a disabled Message Content Intent.

> **On `get_permissions`:** it returns permission *names*, not bitfields, plus the list of
> tools that will fail and what each one is missing. Pass `channel_id` to apply that channel's
> overwrites. It works on channels the bot cannot open — which is when you need it.

## Security

- **The bot token is a credential.** Keep it in the environment, never in source or in a
  committed config file.
- **`@everyone` and `@here` are stripped** from outgoing message content.
- **Grant the narrowest permission set that works.** The bot can do anything its Discord
  permissions allow, and an MCP client drives it from model output. Skip `Administrator`.
- **Webhook URLs returned by `create_webhook` are credentials** — anyone holding one can post
  to that channel without authentication.
- **In HTTP mode, bind to localhost unless you have put authentication in front of it.**
  The server has no built-in auth; `--host 0.0.0.0` exposes every tool to the network.

## Development

```bash
pip install -e ".[dev]"
pytest                    # unit + MCP protocol integration tests
```

Two layers of protocol tests, so a regression fails the build:

- **live** — every read tool and the whole write round trip (send → edit → embeds → react →
  thread → channel → webhook → delete) exercised against a real guild, cleaning up after
  itself. This is the layer that found the `PIN_MESSAGES` split and the unremovable webhook
  post; a stub cannot tell you what Discord actually enforces.
- **in-process** — a real MCP client attached to the server object, covering
  `initialize` → `tools/list` → `tools/call`, tool-name validity, and error shape.
- **subprocess** — the installed `discord-mcp` binary launched over stdio exactly the way
  Claude Desktop launches it, talking to a stub Discord API
  (`tests/stub_discord_api.py`) via `DISCORD_API_BASE_URL`. This is the layer that catches
  packaging, console-script, and stdout-framing breakage.

## Breaking changes in 2.0

1.x did not implement MCP. It served a hand-rolled REST API at `POST /mcp/list_tools` and
`POST /mcp/call_tool` with a `{method, params}` body — not JSON-RPC 2.0, no `initialize`
handshake, no `tools/list`, no `tools/call`, no stdio transport. No MCP client could talk to
it. 2.0 replaces that layer with the official SDK.

| 1.x | 2.0 |
|---|---|
| `POST /mcp/list_tools`, `POST /mcp/call_tool` | `initialize` / `tools/list` / `tools/call` (JSON-RPC 2.0) |
| HTTP only, port 8000 | stdio (default) + Streamable HTTP |
| Tool names `discord.send_message` | `send_message` — dots are rejected by MCP clients |
| `python run.py` | `discord-mcp` console script |
| Repo-root modules | `discord_mcp` package, installable from PyPI |

Also fixed along the way, each of which broke the server in production:

- Logs went to **stdout**, which is the JSON-RPC channel — any log line corrupted the stream.
- `MCPError` subclassed pydantic `BaseModel`, so `raise MCPError(...)` died with `TypeError`.
  Every rate-limit and timeout path hit this.
- `DiscordGuild.owner_id` was required, but `GET /users/@me/guilds` returns *partial* guild
  objects without it — so `list_guilds`, the first call anyone makes, always failed.
- The JSON log formatter returned raw JSON where loguru expects a format template, so every
  log record raised `KeyError: '"timestamp"'`.
- `log_tool_call()` passed fields as loguru message-format arguments instead of binding them,
  silently dropping every structured field it claimed to record.

## What changed in 2.1

2.0 made the server speak MCP. 2.1 makes it usable once connected — the gap between "the
client connects" and "the model gets somewhere with it".

| | 2.0 | 2.1 |
|---|---|---|
| A failed call | `Error executing tool list_messages` | the Discord reason, plus what to do about it |
| `list_channels`, 6 channels | ~1,200 tokens, ~85% `null` | ~220 tokens |
| A broad `search_messages` | every match, in full | capped results, real total reported (~26k → ~5k tokens measured) |
| Long message bodies | returned whole, every time | previewed with an explicit escape hatch |
| `search_messages` | called a user-only endpoint, with `channel_id` in the guild slot | reads history and filters, and reports how far it looked |
| `get_permissions` | raw bitfields read from an endpoint that does not return them | permission names, effective per channel, and the tools each gap blocks |
| `analyze_channel_activity(days=7)` | `days` unused; always the last 100 messages | actually windowed, and reports the span it observed |
| `list_threads` | `GET /channels/{id}/threads`, a route that does not exist (405) | active threads from the guild, archived from the channel |
| `send_message(embeds=…)` | `NameError` | works |
| `send_via_webhook` | posted without `?wait=true`, leaving a message with no id — unremovable | returns the message, so `delete_message` can undo it |
| Webhook lifecycle | create only; the server could mint a credential it could not revoke | `list_webhooks` + `delete_webhook` |
| `pin_message` permission check | mapped to `MANAGE_MESSAGES`, so `get_permissions` said "allowed" and Discord returned 403 | `PIN_MESSAGES` (bit 51), matching Discord |
| Pin endpoints | deprecated `/channels/{id}/pins/…` | current `/channels/{id}/messages/pins/…` |
| `list_messages(before=…)` | cache key omitted `before`, so paging looped | keyed on the full request |
| Empty message bodies | indistinguishable from an empty channel | named as the Message Content Intent, at startup and in the response |
| Argument schemas | `{"title": "Has"}` | descriptions and ranges on every argument |

## Prior art

Design borrowed from the community Discord MCP servers, none of which is official:

- [SaseQ/discord-mcp](https://github.com/SaseQ/discord-mcp) — the `DISCORD_GUILD_ID` default
  and the flat `verb_noun` tool naming.
- [barryyip0625/mcp-discord](https://github.com/barryyip0625/mcp-discord) — the
  stdio-plus-streamable-HTTP transport split and its CLI shape.

## License

MIT — see [LICENSE](LICENSE).
