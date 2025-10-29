# API Endpoints

Complete reference for Discord MCP Server API endpoints.

## Base URL

```
http://localhost:8000
```

## Authentication

The Discord MCP Server uses Discord Bot Token authentication. Configure your bot token in the environment variables:

```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

## Endpoints

### Server Status

#### `GET /`

Returns basic server information.

**Response:**
```json
{
  "name": "Discord MCP Server",
  "version": "1.0.0",
  "status": "running",
  "uptime": "2h 30m 15s"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

### Health Check

#### `GET /health`

Returns server health status and dependency information.

**Response:**
```json
{
  "status": "ok",
  "uptime_seconds": 9015.5,
  "dependencies": {
    "redis": "connected",
    "discord_api": "connected"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

### Metrics

#### `GET /metrics`

Returns Prometheus-compatible metrics.

**Response:**
```
# HELP discord_mcp_requests_total Total number of requests
# TYPE discord_mcp_requests_total counter
discord_mcp_requests_total 1250

# HELP discord_mcp_request_duration_seconds Request duration in seconds
# TYPE discord_mcp_request_duration_seconds histogram
discord_mcp_request_duration_seconds_bucket{le="0.1"} 800
discord_mcp_request_duration_seconds_bucket{le="0.5"} 1100
discord_mcp_request_duration_seconds_bucket{le="1.0"} 1200
discord_mcp_request_duration_seconds_bucket{le="+Inf"} 1250

# HELP discord_mcp_rate_limit_hits_total Total number of rate limit hits
# TYPE discord_mcp_rate_limit_hits_total counter
discord_mcp_rate_limit_hits_total 5
```

**Example:**
```bash
curl http://localhost:8000/metrics
```

### MCP Endpoint

#### `POST /mcp`

Main MCP JSON-RPC 2.0 endpoint for tool operations.

**Content-Type:** `application/json`

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "method": "method_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  },
  "id": 1
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "data": "response_data"
  },
  "id": 1
}
```

## MCP Methods

### List Tools

#### `mcp_list_tools`

Returns a list of all available MCP tools.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "mcp_list_tools",
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": [
    {
      "name": "discord.send_message",
      "version": "v1",
      "description": "Send a message to a Discord channel",
      "input_schema": {
        "type": "object",
        "properties": {
          "channel_id": {
            "type": "string",
            "description": "ID of the channel to send message to"
          },
          "content": {
            "type": "string",
            "description": "Content of the message"
          }
        },
        "required": ["channel_id", "content"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "content": {"type": "string"},
          "timestamp": {"type": "string"}
        }
      }
    }
  ],
  "id": 1
}
```

### Call Tool

#### `mcp_call_tool`

Executes a specific MCP tool with provided parameters.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "mcp_call_tool",
  "params": {
    "tool": "discord.send_message",
    "params": {
      "channel_id": "123456789",
      "content": "Hello from MCP!"
    }
  },
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tool_name": "discord.send_message",
    "tool_version": "v1",
    "data": {
      "id": "987654321",
      "content": "Hello from MCP!",
      "timestamp": "2024-01-01T12:00:00Z",
      "author": {
        "id": "bot_user_id",
        "username": "BotName",
        "bot": true
      }
    }
  },
  "id": 1
}
```

## Error Handling

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "Tool execution failed",
    "data": {
      "tool": "discord.send_message",
      "error_type": "CHANNEL_NOT_FOUND",
      "details": "Channel with ID 123456789 not found"
    }
  },
  "id": 1
}
```

### Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse Error | Invalid JSON was received |
| -32600 | Invalid Request | The JSON sent is not a valid Request object |
| -32601 | Method Not Found | The method does not exist |
| -32602 | Invalid Params | Invalid method parameter(s) |
| -32603 | Internal Error | Internal JSON-RPC error |
| -32000 | Server Error | Tool execution error |
| -32001 | Rate Limited | Discord API rate limit exceeded |
| -32002 | Unauthorized | Bot token invalid or expired |
| -32003 | Forbidden | Insufficient permissions |

### Common Errors

#### Channel Not Found
```json
{
  "error": {
    "code": -32000,
    "message": "Channel not found",
    "data": {
      "error_type": "CHANNEL_NOT_FOUND",
      "channel_id": "123456789"
    }
  }
}
```

#### Rate Limited
```json
{
  "error": {
    "code": -32001,
    "message": "Rate limit exceeded",
    "data": {
      "retry_after_ms": 5000,
      "rate_limited": true
    }
  }
}
```

#### Missing Permissions
```json
{
  "error": {
    "code": -32003,
    "message": "Missing permissions",
    "data": {
      "error_type": "MISSING_PERMISSIONS",
      "required_permissions": ["SEND_MESSAGES"]
    }
  }
}
```

## Rate Limiting

### Discord API Limits

The Discord MCP Server automatically handles Discord API rate limits:

- **Global Rate Limit**: 50 requests per second
- **Per-Resource Limits**: Varies by endpoint
- **Per-Guild Limits**: Some operations have guild-specific limits

### Rate Limit Headers

Discord API responses include rate limit information:

```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 49
X-RateLimit-Reset: 1640995200
X-RateLimit-Reset-After: 1.0
```

### Automatic Handling

The server automatically:
- Respects rate limits
- Implements exponential backoff
- Queues requests when limits are hit
- Returns appropriate error responses

## Request/Response Examples

### Send Message

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.send_message",
      "params": {
        "channel_id": "123456789",
        "content": "Hello World!"
      }
    },
    "id": 1
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tool_name": "discord.send_message",
    "tool_version": "v1",
    "data": {
      "id": "987654321",
      "content": "Hello World!",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  },
  "id": 1
}
```

### List Guilds

**Request:**
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

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tool_name": "discord.list_guilds",
    "tool_version": "v1",
    "data": {
      "guilds": [
        {
          "id": "123456789",
          "name": "My Server",
          "icon": "https://cdn.discordapp.com/icons/...",
          "owner_id": "987654321"
        }
      ]
    }
  },
  "id": 1
}
```

### Search Messages

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.search_messages",
      "params": {
        "channel_id": "123456789",
        "query": "important",
        "limit": 10
      }
    },
    "id": 1
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tool_name": "discord.search_messages",
    "tool_version": "v1",
    "data": {
      "messages": [
        {
          "id": "111111111",
          "content": "This is an important message",
          "timestamp": "2024-01-01T11:30:00Z",
          "author": {
            "id": "222222222",
            "username": "User"
          }
        }
      ],
      "total_results": 1
    }
  },
  "id": 1
}
```

## WebSocket Support (Future)

Future versions may include WebSocket support for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## SDK Examples

### Python SDK

```python
import requests

class DiscordMCPClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def call_tool(self, tool_name, params=None):
        payload = {
            "jsonrpc": "2.0",
            "method": "mcp_call_tool",
            "params": {
                "tool": tool_name,
                "params": params or {}
            },
            "id": 1
        }
        response = requests.post(f"{self.base_url}/mcp", json=payload)
        return response.json()
    
    def send_message(self, channel_id, content):
        return self.call_tool("discord.send_message", {
            "channel_id": channel_id,
            "content": content
        })

# Usage
client = DiscordMCPClient()
result = client.send_message("123456789", "Hello from Python!")
```

### JavaScript SDK

```javascript
class DiscordMCPClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }
  
  async callTool(toolName, params = {}) {
    const payload = {
      jsonrpc: '2.0',
      method: 'mcp_call_tool',
      params: {
        tool: toolName,
        params: params
      },
      id: 1
    };
    
    const response = await fetch(`${this.baseUrl}/mcp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    
    return response.json();
  }
  
  async sendMessage(channelId, content) {
    return this.callTool('discord.send_message', {
      channel_id: channelId,
      content: content
    });
  }
}

// Usage
const client = new DiscordMCPClient();
const result = await client.sendMessage('123456789', 'Hello from JavaScript!');
```
