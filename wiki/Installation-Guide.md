# Installation Guide

This guide will walk you through installing the Discord MCP Server on your system.

## Prerequisites

Before installing the Discord MCP Server, ensure you have:

- **Python 3.12+** - [Download Python](https://www.python.org/downloads/)
- **Discord Bot Token** - [Create a Discord Application](https://discord.com/developers/applications)
- **Redis 6.0+** (Optional) - [Download Redis](https://redis.io/download)

## Installation Methods

### Method 1: Direct Installation (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/tristan-kkim/discord-mcp.git
   cd discord-mcp
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Discord Bot Token
   ```

### Method 2: Docker Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tristan-kkim/discord-mcp.git
   cd discord-mcp
   ```

2. **Set environment variables**
   ```bash
   export DISCORD_BOT_TOKEN=your_bot_token_here
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

### Method 3: pip Installation

```bash
pip install discord-mcp-server
```

## Discord Bot Setup

### Creating a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter a name for your application
4. Click "Create"

### Creating a Bot

1. In your application, go to the "Bot" tab
2. Click "Add Bot"
3. Copy the bot token (you'll need this for the `.env` file)
4. Configure bot settings:
   - **Username**: Choose a display name
   - **Avatar**: Upload a profile picture
   - **Public Bot**: Uncheck if you want to keep it private

### Bot Permissions

Configure the following permissions for your bot:

#### Required Permissions
- `Send Messages` - Send messages to channels
- `Read Message History` - Read message history
- `Use Slash Commands` - Use slash commands (if needed)

#### Optional Permissions
- `Manage Messages` - Edit/delete messages
- `Add Reactions` - Add reactions to messages
- `Manage Channels` - Create/modify channels
- `Manage Roles` - Manage roles
- `Embed Links` - Send embedded messages
- `Attach Files` - Send file attachments

### Inviting the Bot

1. Go to the "OAuth2" → "URL Generator" tab
2. Select "bot" in the scopes
3. Select the permissions you configured
4. Copy the generated URL
5. Open the URL in your browser to invite the bot to your server

## Environment Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379

# Logging Configuration
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=true

# Caching
CACHE_TTL=300

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Environment
ENVIRONMENT=production
```

### Required Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token | ✅ |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `CACHE_TTL` | Cache TTL in seconds | `300` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `ENVIRONMENT` | Environment name | `production` |

## Verification

### Test the Installation

1. **Start the server**
   ```bash
   python run.py
   ```

2. **Check server status**
   ```bash
   curl http://localhost:8000/
   ```

3. **Test health endpoint**
   ```bash
   curl http://localhost:8000/health
   ```

4. **List available tools**
   ```bash
   curl -X POST http://localhost:8000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "mcp_list_tools", "id": 1}'
   ```

### Expected Output

The server should respond with:
- Status: `200 OK`
- Health check: `{"status": "ok", "uptime_seconds": X.X}`
- Tools list: Array of available MCP tools

## Troubleshooting

### Common Issues

#### Bot Token Invalid
- Verify the token is correct
- Ensure the bot is not deleted
- Check for extra spaces or characters

#### Permission Denied
- Verify bot has necessary permissions
- Check server permissions
- Ensure bot is in the correct channels

#### Connection Issues
- Check network connectivity
- Verify Discord API status
- Check firewall settings

#### Redis Connection Failed
- Redis is optional - server will use in-memory cache
- Check Redis server status
- Verify Redis URL format

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](Troubleshooting)
2. Search [GitHub Issues](https://github.com/tristan-kkim/discord-mcp/issues)
3. Create a new issue with:
   - Error messages
   - Steps to reproduce
   - Environment details

## Next Steps

After successful installation:

1. Read the [Quick Start Guide](Quick-Start)
2. Explore [MCP Tools Reference](Channel-Tools)
3. Set up [MCP Client Integration](Cursor-IDE-Integration)
4. Review [Security Best Practices](Security-Guide)
