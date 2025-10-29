# Security Guide

Comprehensive security guide for Discord MCP Server deployment and usage.

## Bot Token Security

### Token Protection

Your Discord Bot Token is the most critical security component. Treat it like a password:

#### ✅ Do's
- Store in environment variables
- Use `.env` files (never commit to version control)
- Rotate tokens regularly
- Use different tokens for different environments

#### ❌ Don'ts
- Never hardcode in source code
- Never commit to version control
- Never share in chat/email
- Never log or print tokens

### Environment Variables

```bash
# .env file (never commit this!)
DISCORD_BOT_TOKEN=your_actual_bot_token_here
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

### Token Rotation

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to "Bot" tab
4. Click "Reset Token"
5. Update your environment variables
6. Restart the server

## Discord Bot Permissions

### Principle of Least Privilege

Only grant the minimum permissions required for your use case:

#### Required Permissions
- `Send Messages` - Send messages to channels
- `Read Message History` - Read message history

#### Optional Permissions (use only if needed)
- `Manage Messages` - Edit/delete messages
- `Add Reactions` - Add reactions
- `Manage Channels` - Create/modify channels
- `Manage Roles` - Manage roles
- `Embed Links` - Send embedded messages
- `Attach Files` - Send file attachments

### Permission Audit

Regularly audit your bot's permissions:

```bash
# Check bot permissions in a guild
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "mcp_call_tool",
    "params": {
      "tool": "discord.get_permissions",
      "params": {
        "guild_id": "123456789",
        "user_id": "BOT_USER_ID"
      }
    },
    "id": 1
  }'
```

## Input Validation & Sanitization

### Built-in Security Features

The Discord MCP Server includes several security features:

#### Mention Filtering
- `@everyone` → `＠everyone` (full-width character)
- `@here` → `＠here` (full-width character)
- Prevents accidental mass mentions

#### Content Sanitization
- HTML tag filtering
- Script injection prevention
- URL validation

#### Rate Limiting
- Automatic Discord API rate limit compliance
- Exponential backoff on failures
- Request queuing

### Custom Validation

Add custom validation for your use case:

```python
def validate_channel_id(channel_id: str) -> bool:
    """Validate Discord channel ID format"""
    return channel_id.isdigit() and len(channel_id) >= 17

def sanitize_message_content(content: str) -> str:
    """Sanitize message content"""
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '&', '"', "'"]
    for char in dangerous_chars:
        content = content.replace(char, '')
    return content
```

## Network Security

### HTTPS/TLS

Always use HTTPS in production:

```bash
# Use reverse proxy (nginx)
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Firewall Configuration

```bash
# Allow only necessary ports
ufw allow 443/tcp  # HTTPS
ufw allow 22/tcp   # SSH
ufw deny 8000/tcp  # Block direct access to MCP server
```

### VPN Access

For sensitive deployments, use VPN access:

```bash
# OpenVPN configuration
client
dev tun
proto udp
remote your-server.com 1194
resolv-retry infinite
nobind
persist-key
persist-tun
ca ca.crt
cert client.crt
key client.key
```

## Audit Logging

### Enable Audit Logging

```bash
# .env configuration
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=true
AUDIT_LOG_FILE=logs/audit.log
```

### Log Format

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "event": "tool_call",
  "tool": "discord.send_message",
  "user_id": "123456789",
  "channel_id": "987654321",
  "success": true,
  "latency_ms": 150,
  "ip_address": "192.168.1.100"
}
```

### Log Analysis

```bash
# Monitor suspicious activity
tail -f logs/audit.log | grep "tool_call" | jq 'select(.success == false)'

# Check rate limit hits
grep "rate_limit" logs/audit.log | jq '.tool'

# Monitor failed authentications
grep "auth_failed" logs/audit.log
```

## Redis Security

### Redis Configuration

```bash
# redis.conf
bind 127.0.0.1
port 6379
requirepass your_strong_password
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Connection Security

```bash
# Use Redis AUTH
REDIS_URL=redis://:password@localhost:6379

# Use Redis TLS (if supported)
REDIS_URL=rediss://:password@localhost:6380
```

## Container Security

### Docker Security

```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' mcpuser
USER mcpuser

# Use specific image tags
FROM python:3.12-slim-bookworm

# Remove unnecessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
```

### Docker Compose Security

```yaml
version: '3.8'
services:
  discord-mcp:
    build: .
    user: "1000:1000"  # Non-root user
    read_only: true
    tmpfs:
      - /tmp
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
    networks:
      - internal
    restart: unless-stopped

networks:
  internal:
    driver: bridge
    internal: true
```

## Monitoring & Alerting

### Health Checks

```bash
# Basic health check
curl -f http://localhost:8000/health || exit 1

# Detailed health check
health=$(curl -s http://localhost:8000/health)
echo $health | jq '.status == "ok"'
```

### Security Monitoring

```bash
# Monitor failed login attempts
grep "auth_failed" logs/audit.log | wc -l

# Check for unusual activity
grep "tool_call" logs/audit.log | jq 'select(.latency_ms > 5000)'

# Monitor rate limit hits
grep "rate_limit" logs/audit.log | jq '.tool'
```

### Alerting Setup

```bash
# Send alerts on security events
#!/bin/bash
if grep -q "auth_failed" logs/audit.log; then
    curl -X POST "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK" \
         -H "Content-Type: application/json" \
         -d '{"text":"Security Alert: Failed authentication attempt"}'
fi
```

## Incident Response

### Security Incident Checklist

1. **Immediate Response**
   - Rotate bot token
   - Check audit logs
   - Verify system integrity

2. **Investigation**
   - Analyze attack vector
   - Check for data compromise
   - Document findings

3. **Recovery**
   - Apply security patches
   - Update configurations
   - Test system functionality

4. **Prevention**
   - Update security policies
   - Enhance monitoring
   - Conduct security review

### Emergency Contacts

- **Discord Support**: [Discord Developer Support](https://discord.com/developers/docs/support)
- **Security Team**: security@your-company.com
- **System Administrator**: admin@your-company.com

## Compliance

### Data Protection

- **GDPR Compliance**: Implement data retention policies
- **CCPA Compliance**: Provide data deletion capabilities
- **SOC 2**: Maintain audit trails and access controls

### Regular Security Reviews

- Monthly permission audits
- Quarterly security assessments
- Annual penetration testing
- Continuous vulnerability scanning

## Best Practices Summary

1. **Token Security**: Never expose bot tokens
2. **Minimal Permissions**: Use least privilege principle
3. **Input Validation**: Sanitize all inputs
4. **Audit Logging**: Log all security events
5. **Regular Updates**: Keep dependencies updated
6. **Network Security**: Use HTTPS and firewalls
7. **Monitoring**: Implement security monitoring
8. **Incident Response**: Have a response plan

## Resources

- [Discord Developer Security](https://discord.com/developers/docs/support)
- [OWASP Security Guidelines](https://owasp.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
