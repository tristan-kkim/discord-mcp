# Discord MCP Server

Discord와 통신하는 Model Context Protocol(MCP) 서버입니다. 모든 Discord 기능을 MCP Tool 형태로 노출하여 OpenAI, LangChain, Cursor 등의 MCP 클라이언트에서 안전하게 사용할 수 있습니다.

## 🚀 주요 기능

- **완전한 Discord API 지원**: 채널, 메시지, 스레드, 리액션, 역할, 웹훅 등 모든 Discord 기능
- **MCP 표준 준수**: JSON-RPC 2.0 기반의 표준화된 API
- **고성능**: Redis 캐싱, Rate limit 관리, 자동 재시도
- **보안**: 멘션 필터링, 권한 최소화, 감사 로그
- **관찰성**: 구조화 로깅, 메트릭, 헬스체크
- **확장성**: Docker, CI/CD, 모니터링 지원

## 📋 요구사항

- Python 3.12+
- Discord Bot Token
- Redis 6.0+ (선택사항 - 없으면 메모리 캐시 사용)

## 🛠️ 빠른 시작

### 1. Discord Bot 생성

1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속
2. "New Application" 클릭하여 새 애플리케이션 생성
3. "Bot" 탭에서 "Add Bot" 클릭
4. Bot Token 복사 (나중에 사용)
5. 필요한 권한 설정:
   - `Send Messages`
   - `Read Message History`
   - `Manage Messages`
   - `Add Reactions`
   - `Manage Channels`
   - `Manage Roles`

### 2. 저장소 클론 및 설정

```bash
git clone https://github.com/tristan-kim/discord-mcp.git
cd discord-mcp
```

### 3. 환경 설정

```bash
# 환경 변수 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

`.env` 파일에 Discord Bot Token 설정:
```env
DISCORD_BOT_TOKEN=your_actual_bot_token_here
```

### 4. 의존성 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python run.py
```

### 5. Docker 사용 (권장)

```bash
# 환경 변수 설정
export DISCORD_BOT_TOKEN=your_actual_bot_token_here

# Docker Compose로 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f discord-mcp
```

## 🔧 MCP 클라이언트 연결

### OpenAI ChatGPT 사용

1. ChatGPT에서 "Custom GPT" 생성
2. "Actions" 탭에서 "Import from URL" 선택
3. 다음 URL 입력: `http://your-server:8000/mcp`
4. 또는 로컬에서 실행 중이라면: `http://localhost:8000/mcp`

### Cursor IDE 사용

1. Cursor 설정에서 "MCP Servers" 추가
2. 서버 URL: `http://your-server:8000/mcp`
3. 또는 로컬: `http://localhost:8000/mcp`

### LangChain 사용

```python
from langchain.tools import Tool
import requests

def discord_tool(tool_name: str, **kwargs):
    response = requests.post(
        "http://localhost:8000/mcp/call_tool",
        json={
            "method": "call_tool",
            "params": {
                "tool": f"discord.{tool_name}",
                "params": kwargs
            }
        }
    )
    return response.json()

# 툴 등록
discord_send_message = Tool(
    name="discord_send_message",
    description="Send a message to Discord channel",
    func=lambda channel_id, content: discord_tool("send_message", channel_id=channel_id, content=content)
)
```

## 📚 사용 가능한 MCP 툴

### 채널/길드 관리
- `discord.list_guilds` - 봇이 속한 길드 목록
- `discord.list_channels` - 길드의 채널 목록
- `discord.get_channel` - 채널 정보 조회
- `discord.create_channel` - 새 채널 생성
- `discord.update_channel` - 채널 정보 수정
- `discord.delete_channel` - 채널 삭제

### 메시지 관리
- `discord.list_messages` - 채널의 메시지 목록
- `discord.get_message` - 특정 메시지 조회
- `discord.send_message` - 메시지 전송
- `discord.edit_message` - 메시지 수정
- `discord.delete_message` - 메시지 삭제
- `discord.search_messages` - 메시지 검색

### 스레드 관리
- `discord.create_thread` - 스레드 생성
- `discord.list_threads` - 스레드 목록 조회
- `discord.archive_thread` - 스레드 아카이브
- `discord.unarchive_thread` - 스레드 언아카이브

### 리액션/핀/웹훅
- `discord.add_reaction` - 리액션 추가
- `discord.remove_reaction` - 리액션 제거
- `discord.list_reactions` - 리액션 목록 조회
- `discord.pin_message` - 메시지 고정
- `discord.unpin_message` - 메시지 고정 해제
- `discord.create_webhook` - 웹훅 생성
- `discord.send_via_webhook` - 웹훅으로 메시지 전송

### 역할/권한 관리
- `discord.list_roles` - 역할 목록 조회
- `discord.add_role` - 멤버에게 역할 부여
- `discord.remove_role` - 멤버에서 역할 제거
- `discord.get_permissions` - 권한 정보 조회

### 고급 기능
- `discord.summarize_messages` - 메시지 중요도 기반 요약
- `discord.rank_messages` - 메시지 중요도 순위
- `discord.sync_since` - 마지막 메시지 이후 동기화
- `discord.analyze_channel_activity` - 채널 활동 분석

## 🔍 API 테스트

### 기본 엔드포인트 확인

```bash
# 서버 상태 확인
curl http://localhost:8000/

# 헬스체크
curl http://localhost:8000/health

# 사용 가능한 툴 목록
curl -X POST http://localhost:8000/mcp/list_tools
```

### 툴 호출 예시

```bash
# 메시지 전송
curl -X POST http://localhost:8000/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "method": "call_tool",
    "params": {
      "tool": "discord.send_message",
      "params": {
        "channel_id": "YOUR_CHANNEL_ID",
        "content": "Hello from MCP!"
      }
    }
  }'
```

## 🔒 보안 고려사항

### Bot Token 보안
- **절대 공개하지 마세요**: Bot Token은 비밀번호와 같습니다
- **환경변수 사용**: 코드에 직접 하드코딩하지 마세요
- **권한 최소화**: Bot이 필요한 최소한의 권한만 부여하세요

### 권한 설정
Discord Bot에 다음 권한만 부여하세요:
- `Send Messages` - 메시지 전송
- `Read Message History` - 메시지 읽기
- `Manage Messages` - 메시지 관리
- `Add Reactions` - 리액션 추가
- `Manage Channels` - 채널 관리 (필요시)
- `Manage Roles` - 역할 관리 (필요시)

### 멘션 필터링
- `@everyone`, `@here` 멘션은 자동으로 전각문자로 치환됩니다
- 기본적으로 모든 멘션은 비활성화됩니다

## 📊 모니터링 및 로깅

### 헬스체크
```bash
curl http://localhost:8000/health
```

### 메트릭
```bash
curl http://localhost:8000/metrics
```

### 로그 형식
모든 로그는 JSON 형식으로 출력되며 다음 정보를 포함합니다:
- `request_id`: 요청 고유 ID
- `tool`: 호출된 툴 이름
- `channel_id`: 관련 채널 ID
- `latency_ms`: 응답 시간
- `success`: 성공 여부

## 🚀 프로덕션 배포

### Docker Compose (권장)

```bash
# 환경변수 설정
export DISCORD_BOT_TOKEN=your_actual_bot_token

# 프로덕션 배포
docker-compose up -d

# 로그 모니터링
docker-compose logs -f discord-mcp
```

### 수동 Docker 배포

```bash
# 이미지 빌드
docker build -t discord-mcp .

# 컨테이너 실행
docker run -d \
  --name discord-mcp \
  -p 8000:8000 \
  -e DISCORD_BOT_TOKEN=your_token \
  -e REDIS_URL=redis://your-redis-host:6379 \
  discord-mcp
```

### 클라우드 배포

#### Heroku
```bash
# Heroku CLI 설치 후
heroku create your-discord-mcp
heroku config:set DISCORD_BOT_TOKEN=your_token
git push heroku main
```

#### Railway
```bash
# Railway CLI 설치 후
railway login
railway init
railway add redis
railway deploy
```

## 📝 환경 변수

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `DISCORD_BOT_TOKEN` | Discord Bot Token | - | ✅ |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379` | ❌ |
| `LOG_LEVEL` | 로그 레벨 | `INFO` | ❌ |
| `RATE_LIMIT_ENABLED` | Rate limit 활성화 | `true` | ❌ |
| `CACHE_TTL` | 캐시 TTL (초) | `300` | ❌ |
| `HOST` | 서버 호스트 | `0.0.0.0` | ❌ |
| `PORT` | 서버 포트 | `8000` | ❌ |
| `ENVIRONMENT` | 실행 환경 | `production` | ❌ |

## 🧪 테스트

```bash
# 의존성 설치
pip install pytest pytest-asyncio pytest-cov

# 단위 테스트
pytest tests/test_tools/

# 통합 테스트
pytest tests/test_integration/

# 커버리지 포함 테스트
pytest --cov=. --cov-report=html
```

## 🤝 기여하기

1. 이 저장소를 Fork하세요
2. 기능 브랜치를 생성하세요 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋하세요 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시하세요 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성하세요

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 문제 해결

### 일반적인 문제들

#### Bot이 메시지를 보내지 못함
- Bot Token이 올바른지 확인
- Bot이 채널에 접근 권한이 있는지 확인
- Bot이 온라인 상태인지 확인

#### Rate Limit 에러
- Discord API Rate Limit에 걸렸습니다
- 잠시 후 다시 시도하세요
- 서버가 자동으로 재시도합니다

#### Redis 연결 실패
- Redis 서버가 실행 중인지 확인
- `REDIS_URL` 환경변수가 올바른지 확인
- Redis 없이도 실행 가능합니다 (메모리 캐시 사용)

### 지원

문제가 발생하면 [GitHub Issues](https://github.com/tristan-kim/discord-mcp/issues)에 등록해 주세요.

## 🔄 업데이트 내역

### v1.0.0 (2024-01-XX)
- 🎉 초기 릴리즈
- ✅ 모든 기본 Discord 기능 지원
- ✅ MCP 표준 준수
- ✅ Docker 지원
- ✅ CI/CD 파이프라인
- ✅ 고급 분석 기능
- ✅ 보안 강화
