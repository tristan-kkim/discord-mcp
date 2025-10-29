# Quick Start

Get up and running with Discord MCP Server in just a few minutes!

## Prerequisites

- Python 3.12+
- Discord Bot Token
- Basic command line knowledge

## 5-Minute Setup

### Step 1: Clone and Install

```bash
git clone https://github.com/tristan-kkim/discord-mcp.git
cd discord-mcp
pip install -r requirements.txt
```

### Step 2: Configure Bot Token

```bash
cp .env.example .env
# Edit .env and add your Discord Bot Token
echo "DISCORD_BOT_TOKEN=your_bot_token_here" > .env
```

### Step 3: Start the Server

```bash
python run.py
```

You should see:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Test the Server

```bash
# Check server status
curl http://localhost:8000/

# List available tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "mcp_list_tools", "id": 1}'
```

## Your First MCP Tool Call

### Send a Message

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.send_message",
      "params": {
        "channel_id": "YOUR_CHANNEL_ID",
        "content": "Hello from MCP! 🚀"
      }
    },
    "id": 1
  }'
```

### List Guilds

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.list_guilds"
    },
    "id": 1
  }'
```

## MCP Client Integration

### Cursor IDE

1. Open Cursor Settings
2. Go to "MCP Servers"
3. Add server: `http://localhost:8000/mcp`
4. Start chatting with Discord!

### Claude Desktop

Add to your MCP config:

```json
{
  "mcpServers": {
    "discord-mcp": {
      "command": "uvx",
      "args": ["discord-mcp@latest"],
      "env": {
        "DISCORD_BOT_TOKEN": "your_bot_token"
      }
    }
  }
}
```

## Common Tasks

### Get Channel ID

1. Enable Developer Mode in Discord
2. Right-click on a channel
3. Click "Copy ID"

### List Channels in a Guild

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.list_channels",
      "params": {
        "guild_id": "YOUR_GUILD_ID"
      }
    },
    "id": 1
  }'
```

### Read Recent Messages

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.list_messages",
      "params": {
        "channel_id": "YOUR_CHANNEL_ID",
        "limit": 10
      }
    },
    "id": 1
  }'
```

## Next Steps

- Explore [Channel Tools](Channel-Tools)
- Learn about [Security Best Practices](Security-Guide)
- Set up [Monitoring](Monitoring)
- Read [API Reference](API-Endpoints)

## Need Help?

- Check [Troubleshooting](Troubleshooting)
- Join our [Discord Community](https://discord.gg/your-server)
- Open a [GitHub Issue](https://github.com/tristan-kkim/discord-mcp/issues)
