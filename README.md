# Discord MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white)](https://discord.com/)

A comprehensive Model Context Protocol (MCP) server for Discord integration. This server exposes all Discord functionality as MCP tools, enabling seamless integration with AI assistants like OpenAI, LangChain, Cursor, and Claude.

## 🌟 Features

- **Complete Discord API Coverage**: Channels, messages, threads, reactions, roles, webhooks, and more
- **MCP Standard Compliance**: JSON-RPC 2.0 based standardized API
- **High Performance**: Redis caching, rate limiting, automatic retries with exponential backoff
- **Security First**: Mention filtering, minimal permissions, audit logging
- **Production Ready**: Docker support, CI/CD pipeline, comprehensive monitoring
- **Advanced AI Features**: Message summarization, activity analysis, intelligent filtering

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Discord Bot Token
- Redis 6.0+ (optional - uses in-memory cache if not available)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tristan-kkim/discord-mcp.git
   cd discord-mcp
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Discord Bot Token
   ```

4. **Run the server**
   ```bash
   python run.py
   ```

### Docker Deployment

```bash
# Using Docker Compose (recommended)
export DISCORD_BOT_TOKEN=your_bot_token_here
docker-compose up -d

# Or using Docker directly
docker build -t discord-mcp .
docker run -d -p 8000:8000 -e DISCORD_BOT_TOKEN=your_token discord-mcp
```

## 🔧 MCP Client Integration

### Cursor IDE

1. Open Cursor Settings → MCP Servers
2. Add server: `http://localhost:8000/mcp`
3. Start using Discord tools in your AI conversations

### OpenAI ChatGPT

1. Create a Custom GPT
2. Add Action with URL: `http://your-server:8000/mcp`
3. Configure with your Discord server details

### Claude Desktop

Add to your MCP configuration:

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

## 📚 Available MCP Tools

### Channel & Guild Management
- `discord.list_guilds` - List all guilds the bot is member of
- `discord.list_channels` - List channels in a guild
- `discord.get_channel` - Get channel information
- `discord.create_channel` - Create a new channel
- `discord.update_channel` - Update channel settings
- `discord.delete_channel` - Delete a channel

### Message Management
- `discord.list_messages` - List messages in a channel
- `discord.get_message` - Get specific message
- `discord.send_message` - Send a message
- `discord.edit_message` - Edit a message
- `discord.delete_message` - Delete a message
- `discord.search_messages` - Search messages with filters

### Thread Management
- `discord.create_thread` - Create a thread
- `discord.list_threads` - List active/archived threads
- `discord.archive_thread` - Archive a thread
- `discord.unarchive_thread` - Unarchive a thread

### Reactions, Pins & Webhooks
- `discord.add_reaction` - Add reaction to message
- `discord.remove_reaction` - Remove reaction
- `discord.list_reactions` - List all reactions
- `discord.pin_message` - Pin a message
- `discord.unpin_message` - Unpin a message
- `discord.create_webhook` - Create webhook
- `discord.send_via_webhook` - Send message via webhook

### Role & Permission Management
- `discord.list_roles` - List guild roles
- `discord.add_role` - Assign role to member
- `discord.remove_role` - Remove role from member
- `discord.get_permissions` - Get permission information

### Advanced AI Features
- `discord.summarize_messages` - AI-powered message summarization
- `discord.rank_messages` - Intelligent message ranking
- `discord.sync_since` - Delta synchronization
- `discord.analyze_channel_activity` - Channel activity analysis

## 🔍 API Reference

### Endpoints

- `GET /` - Server status
- `GET /health` - Health check
- `GET /metrics` - Prometheus-compatible metrics
- `POST /mcp` - MCP JSON-RPC endpoint

### Example Usage

```bash
# List available tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "mcp_list_tools", "id": 1}'

# Send a message
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## 🔒 Security

### Bot Token Security
- **Never expose your bot token** - Treat it like a password
- **Use environment variables** - Never hardcode in source code
- **Minimal permissions** - Only grant necessary Discord permissions

### Required Discord Permissions
- `Send Messages` - Send messages to channels
- `Read Message History` - Read message history
- `Manage Messages` - Edit/delete messages
- `Add Reactions` - Add reactions to messages
- `Manage Channels` - Create/modify channels (if needed)
- `Manage Roles` - Manage roles (if needed)

### Built-in Security Features
- Automatic `@everyone` and `@here` mention filtering
- Rate limiting with Discord API compliance
- Audit logging for all operations
- Input validation and sanitization

## 📊 Monitoring & Observability

### Health Checks
```bash
curl http://localhost:8000/health
```

### Metrics
```bash
curl http://localhost:8000/metrics
```

### Logging
All logs are structured JSON with fields:
- `request_id` - Unique request identifier
- `tool` - MCP tool being called
- `channel_id` - Discord channel context
- `latency_ms` - Response time
- `success` - Operation success status

## 🚀 Production Deployment

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DISCORD_BOT_TOKEN` | Discord Bot Token | - | ✅ |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` | ❌ |
| `LOG_LEVEL` | Logging level | `INFO` | ❌ |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | ❌ |
| `CACHE_TTL` | Cache TTL in seconds | `300` | ❌ |
| `HOST` | Server host | `0.0.0.0` | ❌ |
| `PORT` | Server port | `8000` | ❌ |

### Cloud Deployment

#### Heroku
```bash
heroku create your-discord-mcp
heroku config:set DISCORD_BOT_TOKEN=your_token
git push heroku main
```

#### Railway
```bash
railway login
railway init
railway add redis
railway deploy
```

#### AWS ECS/Fargate
```bash
# Use provided Dockerfile
docker build -t discord-mcp .
# Deploy to ECS with environment variables
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run unit tests
pytest tests/test_tools/

# Run integration tests
pytest tests/test_integration/

# Run with coverage
pytest --cov=. --cov-report=html
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [GitHub Wiki](https://github.com/tristan-kkim/discord-mcp/wiki)
- **Issues**: [GitHub Issues](https://github.com/tristan-kkim/discord-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tristan-kkim/discord-mcp/discussions)

## 🔄 Changelog

### v1.0.0 (2024-10-29)
- 🎉 Initial release
- ✅ Complete Discord API integration
- ✅ MCP standard compliance
- ✅ Docker support
- ✅ Advanced AI features
- ✅ Security enhancements
- ✅ Comprehensive documentation

---

## 한국어 문서

# Discord MCP 서버

Discord와 통신하는 Model Context Protocol(MCP) 서버입니다. 모든 Discord 기능을 MCP Tool 형태로 노출하여 OpenAI, LangChain, Cursor 등의 MCP 클라이언트에서 안전하게 사용할 수 있습니다.

## 🌟 주요 기능

- **완전한 Discord API 지원**: 채널, 메시지, 스레드, 리액션, 역할, 웹훅 등 모든 Discord 기능
- **MCP 표준 준수**: JSON-RPC 2.0 기반의 표준화된 API
- **고성능**: Redis 캐싱, Rate limit 관리, 지수 백오프 재시도
- **보안 우선**: 멘션 필터링, 최소 권한, 감사 로그
- **프로덕션 준비**: Docker 지원, CI/CD 파이프라인, 포괄적 모니터링
- **고급 AI 기능**: 메시지 요약, 활동 분석, 지능형 필터링

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.12+
- Discord Bot Token
- Redis 6.0+ (선택사항 - 없으면 메모리 캐시 사용)

### 설치

1. **저장소 클론**
   ```bash
   git clone https://github.com/tristan-kkim/discord-mcp.git
   cd discord-mcp
   ```

2. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

3. **환경 설정**
   ```bash
   cp .env.example .env
   # .env 파일에 Discord Bot Token 설정
   ```

4. **서버 실행**
   ```bash
   python run.py
   ```

### Docker 배포

```bash
# Docker Compose 사용 (권장)
export DISCORD_BOT_TOKEN=your_bot_token_here
docker-compose up -d

# 또는 Docker 직접 사용
docker build -t discord-mcp .
docker run -d -p 8000:8000 -e DISCORD_BOT_TOKEN=your_token discord-mcp
```

## 🔧 MCP 클라이언트 통합

### Cursor IDE

1. Cursor 설정 → MCP 서버 열기
2. 서버 추가: `http://localhost:8000/mcp`
3. AI 대화에서 Discord 도구 사용 시작

### OpenAI ChatGPT

1. Custom GPT 생성
2. Action 추가: `http://your-server:8000/mcp`
3. Discord 서버 세부사항으로 구성

### Claude Desktop

MCP 구성에 추가:

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

## 📚 사용 가능한 MCP 도구

### 채널 및 길드 관리
- `discord.list_guilds` - 봇이 속한 모든 길드 목록
- `discord.list_channels` - 길드의 채널 목록
- `discord.get_channel` - 채널 정보 조회
- `discord.create_channel` - 새 채널 생성
- `discord.update_channel` - 채널 설정 업데이트
- `discord.delete_channel` - 채널 삭제

### 메시지 관리
- `discord.list_messages` - 채널의 메시지 목록
- `discord.get_message` - 특정 메시지 조회
- `discord.send_message` - 메시지 전송
- `discord.edit_message` - 메시지 편집
- `discord.delete_message` - 메시지 삭제
- `discord.search_messages` - 필터로 메시지 검색

### 스레드 관리
- `discord.create_thread` - 스레드 생성
- `discord.list_threads` - 활성/아카이브된 스레드 목록
- `discord.archive_thread` - 스레드 아카이브
- `discord.unarchive_thread` - 스레드 언아카이브

### 리액션, 핀 및 웹훅
- `discord.add_reaction` - 메시지에 리액션 추가
- `discord.remove_reaction` - 리액션 제거
- `discord.list_reactions` - 모든 리액션 목록
- `discord.pin_message` - 메시지 고정
- `discord.unpin_message` - 메시지 고정 해제
- `discord.create_webhook` - 웹훅 생성
- `discord.send_via_webhook` - 웹훅으로 메시지 전송

### 역할 및 권한 관리
- `discord.list_roles` - 길드 역할 목록
- `discord.add_role` - 멤버에게 역할 부여
- `discord.remove_role` - 멤버에서 역할 제거
- `discord.get_permissions` - 권한 정보 조회

### 고급 AI 기능
- `discord.summarize_messages` - AI 기반 메시지 요약
- `discord.rank_messages` - 지능형 메시지 순위
- `discord.sync_since` - 델타 동기화
- `discord.analyze_channel_activity` - 채널 활동 분석

## 🔒 보안

### Bot Token 보안
- **Bot 토큰을 절대 노출하지 마세요** - 비밀번호처럼 취급
- **환경변수 사용** - 소스코드에 하드코딩 금지
- **최소 권한** - 필요한 Discord 권한만 부여

### 필요한 Discord 권한
- `Send Messages` - 채널에 메시지 전송
- `Read Message History` - 메시지 기록 읽기
- `Manage Messages` - 메시지 편집/삭제
- `Add Reactions` - 메시지에 리액션 추가
- `Manage Channels` - 채널 생성/수정 (필요시)
- `Manage Roles` - 역할 관리 (필요시)

### 내장 보안 기능
- `@everyone` 및 `@here` 멘션 자동 필터링
- Discord API 준수 Rate limiting
- 모든 작업에 대한 감사 로그
- 입력 검증 및 정제

## 📊 모니터링 및 관찰성

### 헬스체크
```bash
curl http://localhost:8000/health
```

### 메트릭
```bash
curl http://localhost:8000/metrics
```

### 로깅
모든 로그는 다음 필드가 포함된 구조화된 JSON입니다:
- `request_id` - 고유 요청 식별자
- `tool` - 호출되는 MCP 도구
- `channel_id` - Discord 채널 컨텍스트
- `latency_ms` - 응답 시간
- `success` - 작업 성공 상태

## 🚀 프로덕션 배포

### 환경 변수

| 변수 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `DISCORD_BOT_TOKEN` | Discord Bot Token | - | ✅ |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379` | ❌ |
| `LOG_LEVEL` | 로깅 레벨 | `INFO` | ❌ |
| `RATE_LIMIT_ENABLED` | Rate limiting 활성화 | `true` | ❌ |
| `CACHE_TTL` | 캐시 TTL (초) | `300` | ❌ |
| `HOST` | 서버 호스트 | `0.0.0.0` | ❌ |
| `PORT` | 서버 포트 | `8000` | ❌ |

### 클라우드 배포

#### Heroku
```bash
heroku create your-discord-mcp
heroku config:set DISCORD_BOT_TOKEN=your_token
git push heroku main
```

#### Railway
```bash
railway login
railway init
railway add redis
railway deploy
```

#### AWS ECS/Fargate
```bash
# 제공된 Dockerfile 사용
docker build -t discord-mcp .
# 환경 변수와 함께 ECS에 배포
```

## 🧪 테스트

```bash
# 테스트 의존성 설치
pip install pytest pytest-asyncio pytest-cov

# 단위 테스트 실행
pytest tests/test_tools/

# 통합 테스트 실행
pytest tests/test_integration/

# 커버리지와 함께 실행
pytest --cov=. --cov-report=html
```

## 🤝 기여하기

기여를 환영합니다! 자세한 내용은 [기여 가이드](CONTRIBUTING.md)를 참조하세요.

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 열기

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원

- **문서**: [GitHub Wiki](https://github.com/tristan-kkim/discord-mcp/wiki)
- **이슈**: [GitHub Issues](https://github.com/tristan-kkim/discord-mcp/issues)
- **토론**: [GitHub Discussions](https://github.com/tristan-kkim/discord-mcp/discussions)

## 🔄 변경 로그

### v1.0.0 (2024-10-29)
- 🎉 초기 릴리즈
- ✅ 완전한 Discord API 통합
- ✅ MCP 표준 준수
- ✅ Docker 지원
- ✅ 고급 AI 기능
- ✅ 보안 강화
- ✅ 포괄적 문서화