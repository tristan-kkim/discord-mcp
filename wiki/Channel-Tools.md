# Channel Tools

Comprehensive guide to Discord channel and guild management tools.

## Available Tools

### Guild Management

#### `discord.list_guilds`
Lists all guilds (servers) the bot is a member of.

**Parameters:** None

**Response:**
```json
{
  "guilds": [
    {
      "id": "123456789",
      "name": "My Server",
      "icon": "https://cdn.discordapp.com/icons/...",
      "owner_id": "987654321"
    }
  ]
}
```

**Example:**
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

### Channel Management

#### `discord.list_channels`
Lists all channels in a guild.

**Parameters:**
- `guild_id` (string, required): The guild ID

**Response:**
```json
{
  "channels": [
    {
      "id": "123456789",
      "guild_id": "987654321",
      "name": "general",
      "type": 0,
      "topic": "General discussion",
      "nsfw": false,
      "position": 0
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.list_channels",
      "params": {
        "guild_id": "123456789"
      }
    },
    "id": 1
  }'
```

#### `discord.get_channel`
Gets detailed information about a specific channel.

**Parameters:**
- `channel_id` (string, required): The channel ID

**Response:**
```json
{
  "id": "123456789",
  "guild_id": "987654321",
  "name": "general",
  "type": 0,
  "topic": "General discussion",
  "nsfw": false,
  "position": 0,
  "permission_overwrites": [],
  "rate_limit_per_user": 0
}
```

#### `discord.create_channel`
Creates a new channel in a guild.

**Parameters:**
- `guild_id` (string, required): The guild ID
- `name` (string, required): Channel name
- `type` (integer, optional): Channel type (0=text, 2=voice, 4=category)
- `topic` (string, optional): Channel topic
- `nsfw` (boolean, optional): NSFW flag

**Response:**
```json
{
  "id": "123456789",
  "guild_id": "987654321",
  "name": "new-channel",
  "type": 0,
  "topic": "New channel topic",
  "nsfw": false,
  "position": 1
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.create_channel",
      "params": {
        "guild_id": "123456789",
        "name": "announcements",
        "type": 0,
        "topic": "Important announcements"
      }
    },
    "id": 1
  }'
```

#### `discord.update_channel`
Updates channel settings.

**Parameters:**
- `channel_id` (string, required): The channel ID
- `name` (string, optional): New channel name
- `topic` (string, optional): New channel topic
- `nsfw` (boolean, optional): NSFW flag

**Response:**
```json
{
  "id": "123456789",
  "guild_id": "987654321",
  "name": "updated-name",
  "topic": "Updated topic",
  "nsfw": false
}
```

#### `discord.delete_channel`
Deletes a channel.

**Parameters:**
- `channel_id` (string, required): The channel ID

**Response:**
```json
{
  "success": true,
  "message": "Channel deleted successfully"
}
```

## Channel Types

| Type | Name | Description |
|------|------|-------------|
| 0 | GUILD_TEXT | Text channel |
| 2 | GUILD_VOICE | Voice channel |
| 4 | GUILD_CATEGORY | Category channel |
| 5 | GUILD_ANNOUNCEMENT | Announcement channel |
| 10 | ANNOUNCEMENT_THREAD | Announcement thread |
| 11 | PUBLIC_THREAD | Public thread |
| 12 | PRIVATE_THREAD | Private thread |
| 13 | GUILD_STAGE_VOICE | Stage channel |
| 15 | GUILD_FORUM | Forum channel |

## Best Practices

### Channel Organization

1. **Use Categories**: Group related channels under categories
2. **Clear Naming**: Use descriptive channel names
3. **Proper Permissions**: Set appropriate permissions for each channel
4. **Topic Descriptions**: Add helpful topic descriptions

### Permission Management

1. **Minimal Permissions**: Only grant necessary permissions
2. **Role-Based Access**: Use roles to manage channel access
3. **Regular Audits**: Periodically review channel permissions

### Channel Lifecycle

1. **Creation**: Use descriptive names and topics
2. **Maintenance**: Keep channels organized and active
3. **Archival**: Archive unused channels instead of deleting
4. **Cleanup**: Regularly clean up old channels

## Error Handling

### Common Errors

#### `CHANNEL_NOT_FOUND`
- Channel ID is invalid
- Bot doesn't have access to the channel
- Channel was deleted

#### `MISSING_PERMISSIONS`
- Bot lacks necessary permissions
- Check bot role permissions
- Verify channel-specific permissions

#### `INVALID_CHANNEL_TYPE`
- Channel type is not supported
- Check channel type values
- Verify guild supports the channel type

### Error Response Format

```json
{
  "error": {
    "code": -32000,
    "message": "Channel not found",
    "data": {
      "channel_id": "123456789",
      "error_type": "CHANNEL_NOT_FOUND"
    }
  }
}
```

## Rate Limits

Discord API has rate limits for channel operations:

- **Create Channel**: 2 requests per 10 minutes per guild
- **Modify Channel**: 5 requests per 10 minutes per channel
- **Delete Channel**: 2 requests per 10 minutes per guild

The MCP server automatically handles rate limiting with exponential backoff.

## Examples

### Creating a Channel Structure

```bash
# Create a category
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.create_channel",
      "params": {
        "guild_id": "123456789",
        "name": "Development",
        "type": 4
      }
    },
    "id": 1
  }'

# Create channels under the category
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.create_channel",
      "params": {
        "guild_id": "123456789",
        "name": "general",
        "type": 0,
        "topic": "General development discussion"
      }
    },
    "id": 2
  }'
```

### Bulk Channel Operations

```bash
# List all channels
channels=$(curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.list_channels",
      "params": {
        "guild_id": "123456789"
      }
    },
    "id": 1
  }')

# Process channels (example with jq)
echo $channels | jq '.result.channels[] | select(.type == 0) | .name'
```

## Related Tools

- [Message Tools](Message-Tools) - Message management
- [Thread Tools](Thread-Tools) - Thread operations
- [Role Tools](Role-Tools) - Permission management
