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
3. **Bot** tab → enable **Message Content Intent** if you want to read message bodies
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

31 tools. Every one carries a description and a JSON Schema, plus MCP
[tool annotations](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
(`readOnlyHint` / `destructiveHint`) so clients can gate destructive calls behind confirmation.

### Guilds & channels
`list_guilds` · `list_channels` · `get_channel` · `create_channel` · `update_channel` · `delete_channel` ⚠️

### Messages
`list_messages` · `get_message` · `send_message` · `edit_message` · `delete_message` ⚠️ · `search_messages`

### Threads
`create_thread` · `list_threads` · `archive_thread` · `unarchive_thread`

### Reactions, pins & webhooks
`add_reaction` · `remove_reaction` · `list_reactions` · `pin_message` · `unpin_message` · `create_webhook` · `send_via_webhook`

### Roles & permissions
`list_roles` · `add_role` · `remove_role` · `get_permissions`

### Channel analytics
`summarize_messages` · `rank_messages` · `sync_since` · `analyze_channel_activity`

⚠️ = annotated destructive.

> **On `summarize_messages` and `rank_messages`:** these score messages with a *heuristic*
> (reaction count, length, links, keyword hits) and hand the top ones back. They do not call
> a language model — the model on the other end of the MCP connection does the summarizing.

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

## Prior art

Design borrowed from the community Discord MCP servers, none of which is official:

- [SaseQ/discord-mcp](https://github.com/SaseQ/discord-mcp) — the `DISCORD_GUILD_ID` default
  and the flat `verb_noun` tool naming.
- [barryyip0625/mcp-discord](https://github.com/barryyip0625/mcp-discord) — the
  stdio-plus-streamable-HTTP transport split and its CLI shape.

## License

MIT — see [LICENSE](LICENSE).
