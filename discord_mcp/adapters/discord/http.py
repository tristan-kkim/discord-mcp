"""
Discord REST API 클라이언트
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Union
import aiohttp
from loguru import logger

from ...core.retry import retry_with_backoff, RateLimitError, TimeoutError, DiscordAPIError
from ...core.ratelimit import discord_rate_limiter
from ...core.cache import discord_cache
from ...core.health import health_checker
from ...core.logging import log_discord_api_call
from ...core.errors import discord_code_of
from .models import (
    DiscordUser, DiscordGuild, DiscordChannel, DiscordMessage, 
    DiscordThread, DiscordRole, DiscordWebhook, DiscordEmbed
)


class DiscordClient:
    """Discord REST API 클라이언트"""
    
    def __init__(self, bot_token: str, base_url: str = "https://discord.com/api/v10"):
        self.bot_token = bot_token
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        # 봇 자신의 user id. 멤버 조회에 "@me"를 쓸 수 없어서 필요하다.
        self._bot_user_id: Optional[str] = None
        
        # 기본 헤더
        self.default_headers = {
            "Authorization": f"Bot {bot_token}",
            "User-Agent": "DiscordMCP/1.0.0",
            "Content-Type": "application/json"
        }
    
    async def connect(self) -> None:
        """세션 연결"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            
            self.session = aiohttp.ClientSession(
                headers=self.default_headers,
                timeout=timeout,
                connector=connector
            )
            
            # 연결 테스트
            try:
                me = await self._make_request("GET", "/users/@me")
                self._bot_user_id = me.get("id")
                self._connected = True
                health_checker.update_discord_status(True)
                logger.info("Connected to Discord API")
            except Exception as e:
                self._connected = False
                health_checker.update_discord_status(False)
                logger.error(f"Failed to connect to Discord API: {e}")
                raise
    
    async def disconnect(self) -> None:
        """세션 연결 해제"""
        if self.session and not self.session.closed:
            await self.session.close()
            self._connected = False
            health_checker.update_discord_status(False)
            logger.info("Disconnected from Discord API")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """HTTP 요청 실행"""
        if not self.session:
            await self.connect()
        
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            # Rate limit 확인
            await discord_rate_limiter.check_rate_limit(endpoint)
            
            # 캐시 확인 (GET 요청만)
            if use_cache and method == "GET":
                cache_key = f"{method}:{endpoint}:{params or {}}"
                cached_response = await discord_cache.cache.get(cache_key)
                if cached_response:
                    logger.debug(f"Cache hit for {endpoint}")
                    return cached_response
            
            # 요청 실행
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                # Rate limit 헤더 처리
                await discord_rate_limiter.handle_rate_limit(endpoint, dict(response.headers))
                
                # 응답 로깅
                log_discord_api_call(
                    method=method,
                    endpoint=endpoint,
                    status_code=response.status,
                    latency_ms=latency_ms,
                    rate_limit_remaining=discord_rate_limiter.rate_limiter.get_remaining_requests(
                        discord_rate_limiter._get_bucket(endpoint)
                    )
                )
                
                # 에러 처리
                if response.status == 429:
                    retry_after = float(response.headers.get("Retry-After", 1.0))
                    raise RateLimitError("Rate limited", retry_after)
                elif response.status >= 500:
                    raise DiscordAPIError(f"Server error: {response.status}")
                elif response.status >= 400:
                    try:
                        error_data = await response.json()
                    except Exception:  # noqa: BLE001 - 본문이 JSON이 아닐 수도 있다
                        error_data = {}
                    error_message = error_data.get("message", f"HTTP {response.status}")
                    # Discord의 숫자 코드(50001 Missing Access 등)는 HTTP status보다
                    # 구체적이라, 모델에게 무엇을 고치라고 말할 때 이게 필요하다.
                    raise DiscordAPIError(
                        error_message,
                        status_code=response.status,
                        discord_code=discord_code_of(error_data),
                    )
                
                # 응답 데이터 파싱
                if response.content_type == "application/json":
                    response_data = await response.json()
                else:
                    response_data = {"text": await response.text()}
                
                # 캐시 저장 (GET 요청만)
                if use_cache and method == "GET" and response.status == 200:
                    cache_key = f"{method}:{endpoint}:{params or {}}"
                    await discord_cache.cache.set(cache_key, response_data, cache_ttl)
                
                # 메트릭 기록
                health_checker.record_request(
                    success=200 <= response.status < 300,
                    latency=latency_ms / 1000,
                    rate_limited=response.status == 429
                )
                
                return response_data
                
        except asyncio.TimeoutError:
            raise TimeoutError("Request timeout")
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            health_checker.record_request(success=False, latency=latency_ms / 1000)
            raise
    
    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """재시도와 함께 HTTP 요청 실행"""
        return await retry_with_backoff(
            self._make_request,
            method=method,
            endpoint=endpoint,
            data=data,
            params=params,
            use_cache=use_cache,
            cache_ttl=cache_ttl
        )
    
    # Guild 관련 메서드
    async def get_guilds(self) -> List[DiscordGuild]:
        """길드 목록 조회"""
        response = await self._make_request_with_retry("GET", "/users/@me/guilds", use_cache=True)
        return [DiscordGuild(**guild) for guild in response]
    
    async def get_guild(self, guild_id: str) -> DiscordGuild:
        """길드 정보 조회"""
        # 캐시에서 먼저 확인
        cached_guild = await discord_cache.get_guild(guild_id)
        if cached_guild:
            return DiscordGuild(**cached_guild)
        
        response = await self._make_request_with_retry("GET", f"/guilds/{guild_id}", use_cache=True)
        guild = DiscordGuild(**response)
        
        # 캐시에 저장
        await discord_cache.set_guild(guild_id, response)
        
        return guild
    
    # Channel 관련 메서드
    async def get_channels(self, guild_id: str) -> List[DiscordChannel]:
        """길드의 채널 목록 조회"""
        response = await self._make_request_with_retry("GET", f"/guilds/{guild_id}/channels", use_cache=True)
        return [DiscordChannel(**channel) for channel in response]
    
    async def get_channel(self, channel_id: str) -> DiscordChannel:
        """채널 정보 조회"""
        # 캐시에서 먼저 확인
        cached_channel = await discord_cache.get_channel(channel_id)
        if cached_channel:
            return DiscordChannel(**cached_channel)
        
        response = await self._make_request_with_retry("GET", f"/channels/{channel_id}", use_cache=True)
        channel = DiscordChannel(**response)
        
        # 캐시에 저장
        await discord_cache.set_channel(channel_id, response)
        
        return channel
    
    async def create_channel(
        self,
        guild_id: str,
        name: str,
        type: int = 0,
        topic: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> DiscordChannel:
        """채널 생성"""
        data = {
            "name": name,
            "type": type,
            "topic": topic,
            "parent_id": parent_id
        }
        
        response = await self._make_request_with_retry("POST", f"/guilds/{guild_id}/channels", data=data)
        channel = DiscordChannel(**response)
        
        # 캐시 무효화
        await discord_cache.invalidate_guild(guild_id)
        
        return channel
    
    async def update_channel(
        self,
        channel_id: str,
        name: Optional[str] = None,
        topic: Optional[str] = None,
        position: Optional[int] = None
    ) -> DiscordChannel:
        """채널 정보 수정"""
        data = {}
        if name is not None:
            data["name"] = name
        if topic is not None:
            data["topic"] = topic
        if position is not None:
            data["position"] = position
        
        response = await self._make_request_with_retry("PATCH", f"/channels/{channel_id}", data=data)
        channel = DiscordChannel(**response)
        
        # 캐시 무효화
        await discord_cache.invalidate_channel(channel_id)
        
        return channel
    
    async def delete_channel(self, channel_id: str) -> None:
        """채널 삭제"""
        await self._make_request_with_retry("DELETE", f"/channels/{channel_id}")
        
        # 캐시 무효화
        await discord_cache.invalidate_channel(channel_id)
    
    # Message 관련 메서드
    async def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
        after: Optional[str] = None,
        before: Optional[str] = None,
        around: Optional[str] = None
    ) -> List[DiscordMessage]:
        """메시지 목록 조회"""
        params = {"limit": min(limit, 100)}  # Discord 최대 제한
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        if around:
            params["around"] = around
        
        # 캐시 키는 params 전체여야 한다. 이전 버전은 (channel, limit, after)만
        # 썼기 때문에 before/around로 과거를 넘기면 첫 페이지가 그대로 되돌아왔다.
        cached_messages = await discord_cache.get_messages(channel_id, params)
        if cached_messages:
            return [DiscordMessage(**msg) for msg in cached_messages.get("messages", [])]

        response = await self._make_request_with_retry(
            "GET",
            f"/channels/{channel_id}/messages",
            params=params,
        )

        messages = [DiscordMessage(**msg) for msg in response]

        await discord_cache.set_messages(channel_id, {"messages": response}, params)

        return messages

    async def iter_messages(
        self,
        channel_id: str,
        limit: int,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[DiscordMessage]:
        """`limit`건이 모일 때까지 100건씩 거슬러 올라간다.

        Discord는 한 요청에 100건만 준다. 이전 버전은 `min(limit, 100)`으로
        조용히 잘라서, limit=1000을 준 호출자에게 100건을 1000건인 양 돌려줬다.
        """
        collected: List[DiscordMessage] = []
        cursor = before
        while len(collected) < limit:
            page = await self.get_messages(
                channel_id=channel_id,
                limit=min(100, limit - len(collected)),
                before=cursor,
                after=after if not collected else None,
            )
            if not page:
                break
            collected.extend(page)
            if len(page) < 100:
                break
            cursor = page[-1].id
        return collected[:limit]
    
    async def get_message(self, channel_id: str, message_id: str) -> DiscordMessage:
        """특정 메시지 조회"""
        response = await self._make_request_with_retry("GET", f"/channels/{channel_id}/messages/{message_id}")
        return DiscordMessage(**response)
    
    def _sanitize_content(self, content: str) -> str:
        """메시지 내용 정리 (멘션 필터링)"""
        # @everyone, @here를 전각문자로 치환
        content = content.replace("@everyone", "＠everyone")
        content = content.replace("@here", "＠here")
        return content
    
    async def send_message(
        self,
        channel_id: str,
        content: str,
        embeds: Optional[List[DiscordEmbed]] = None,
        tts: bool = False
    ) -> DiscordMessage:
        """메시지 전송"""
        # 내용 정리
        content = self._sanitize_content(content)
        
        data = {
            "content": content,
            "tts": tts,
            "allowed_mentions": {"parse": []}  # 멘션 비활성화
        }
        
        if embeds:
            data["embeds"] = [embed.model_dump() for embed in embeds]
        
        response = await self._make_request_with_retry("POST", f"/channels/{channel_id}/messages", data=data)
        
        # 캐시 무효화
        await discord_cache.invalidate_channel(channel_id)
        
        return DiscordMessage(**response)
    
    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        embeds: Optional[List[DiscordEmbed]] = None
    ) -> DiscordMessage:
        """메시지 수정"""
        # 내용 정리
        content = self._sanitize_content(content)

        # _sanitize_content는 리터럴 "@everyone"만 치환한다. 역할/유저 멘션
        # 문법(<@&123>)은 그대로 통과하므로 allowed_mentions로 함께 막아야 한다.
        data = {
            "content": content,
            "allowed_mentions": {"parse": []},
        }
        if embeds:
            data["embeds"] = [embed.model_dump() for embed in embeds]

        response = await self._make_request_with_retry("PATCH", f"/channels/{channel_id}/messages/{message_id}", data=data)
        
        # 캐시 무효화
        await discord_cache.invalidate_channel(channel_id)
        
        return DiscordMessage(**response)
    
    async def delete_message(self, channel_id: str, message_id: str) -> None:
        """메시지 삭제"""
        await self._make_request_with_retry("DELETE", f"/channels/{channel_id}/messages/{message_id}")
        
        # 캐시 무효화
        await discord_cache.invalidate_channel(channel_id)
    
    async def search_messages(
        self,
        channel_id: str,
        query: str,
        author_id: Optional[str] = None,
        has: Optional[str] = None,
        scan_limit: int = 200,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[DiscordMessage]:
        """채널 최근 기록을 직접 훑어 필터한다.

        서버사이드 검색(`GET /guilds/{id}/messages/search`)은 유저 토큰 전용이라
        봇은 401/403을 받는다. 이전 버전은 그 엔드포인트를, 그것도 guild 자리에
        channel_id를 넣어 호출했으므로 이 툴은 한 번도 성공한 적이 없다.
        """
        messages = await self.iter_messages(
            channel_id=channel_id, limit=scan_limit, before=before, after=after
        )

        needle = query.lower()
        matches = []
        for message in messages:
            if author_id and message.author.id != author_id:
                continue
            if has and not self._message_has(message, has):
                continue
            if needle and needle not in self._searchable_text(message).lower():
                continue
            matches.append(message)
        return matches

    @staticmethod
    def _searchable_text(message: DiscordMessage) -> str:
        """본문 + 임베드 텍스트 + 첨부 파일명. 임베드만 있는 봇 글도 걸리게 한다."""
        parts = [message.content]
        for embed in message.embeds:
            parts.extend(filter(None, [embed.title, embed.description, embed.url]))
            for field in embed.fields:
                parts.extend(str(field.get(k, "")) for k in ("name", "value"))
        parts.extend(a.filename for a in message.attachments)
        return " ".join(p for p in parts if p)

    @staticmethod
    def _message_has(message: DiscordMessage, has: str) -> bool:
        kind = has.lower()
        if kind == "link":
            return "http://" in message.content or "https://" in message.content
        if kind == "embed":
            return bool(message.embeds)
        if kind == "file":
            return bool(message.attachments)
        if kind == "image":
            return any(
                (a.content_type or "").startswith("image/") for a in message.attachments
            )
        raise ValueError(
            f"has must be one of: link, embed, file, image (got {has!r})"
        )

    async def get_current_user_id(self) -> str:
        """봇 자신의 user id."""
        if not self._bot_user_id:
            me = await self._make_request_with_retry("GET", "/users/@me", use_cache=True)
            self._bot_user_id = me["id"]
        return self._bot_user_id

    async def get_guild_member_me(self, guild_id: str) -> Dict[str, Any]:
        """길드 안에서 봇 자신의 멤버 객체.

        어떤 role을 갖고 있는지 알아야 채널 오버라이트를 적용해 실효 권한을
        계산할 수 있다. `@me` 별칭은 이 경로에서 동작하지 않고
        (`50035 Value "@me" is not snowflake`), `/users/@me/guilds/{id}/member`는
        봇에게 닫혀 있다 (`20001`). 실제 id를 넣는 형태만 남는다.
        """
        user_id = await self.get_current_user_id()
        return await self._make_request_with_retry(
            "GET", f"/guilds/{guild_id}/members/{user_id}", use_cache=True, cache_ttl=60
        )

    async def get_guild_permissions(self, guild_id: str) -> Optional[str]:
        """길드 레벨에서 봇에게 부여된 권한 비트.

        `GET /guilds/{id}`에는 이 필드가 없다 — partial guild를 주는
        `/users/@me/guilds`에만 있다. 이전 버전은 전자를 읽어 항상 null이었다.
        """
        response = await self._make_request_with_retry(
            "GET", "/users/@me/guilds", use_cache=True
        )
        for guild in response:
            if guild.get("id") == guild_id:
                return guild.get("permissions")
        return None

    async def get_application_info(self) -> Dict[str, Any]:
        """봇 애플리케이션 정보. Message Content Intent 활성 여부 확인용."""
        return await self._make_request_with_retry("GET", "/applications/@me")

    # Thread 관련 메서드
    async def create_thread(
        self,
        channel_id: str,
        name: str,
        message_id: Optional[str] = None,
        auto_archive_duration: int = 1440
    ) -> DiscordThread:
        """스레드 생성"""
        data = {
            "name": name,
            "auto_archive_duration": auto_archive_duration
        }
        
        if message_id:
            response = await self._make_request_with_retry(
                "POST", 
                f"/channels/{channel_id}/messages/{message_id}/threads", 
                data=data
            )
        else:
            response = await self._make_request_with_retry(
                "POST", 
                f"/channels/{channel_id}/threads", 
                data=data
            )
        
        return DiscordThread(**response)
    
    async def get_threads(
        self, channel_id: str, include_archived: bool = True
    ) -> List[DiscordThread]:
        """채널의 스레드 목록.

        `GET /channels/{id}/threads`는 존재하지 않는 경로다 — 실제로 호출하면
        405 Method Not Allowed가 돌아오고, 이전 구현은 그걸 호출하고 있었다.
        활성 스레드는 길드 단위로만 조회되므로 받아서 parent_id로 거르고,
        아카이브된 스레드는 채널 단위 경로에서 따로 가져온다.
        """
        channel = await self.get_channel(channel_id)
        guild_id = channel.guild_id
        if not guild_id:
            raise DiscordAPIError(
                f"Channel {channel_id} is not in a guild, so it cannot have threads.",
                status_code=400,
            )

        active = await self._make_request_with_retry(
            "GET", f"/guilds/{guild_id}/threads/active"
        )
        threads = [
            DiscordThread(**t)
            for t in active.get("threads", [])
            if t.get("parent_id") == channel_id
        ]

        if include_archived:
            archived = await self._make_request_with_retry(
                "GET", f"/channels/{channel_id}/threads/archived/public"
            )
            threads.extend(DiscordThread(**t) for t in archived.get("threads", []))

        return threads

    async def archive_thread(self, channel_id: str) -> DiscordThread:
        """스레드 아카이브"""
        response = await self._make_request_with_retry("PATCH", f"/channels/{channel_id}", data={"archived": True})
        return DiscordThread(**response)
    
    async def unarchive_thread(self, channel_id: str) -> DiscordThread:
        """스레드 언아카이브"""
        response = await self._make_request_with_retry("PATCH", f"/channels/{channel_id}", data={"archived": False})
        return DiscordThread(**response)
    
    # Reaction 관련 메서드
    async def add_reaction(self, channel_id: str, message_id: str, emoji: str) -> None:
        """리액션 추가"""
        # 이모지 URL 인코딩
        if emoji.startswith(":"):
            emoji = emoji.replace(":", "")
        emoji = emoji.replace(" ", "_")
        
        await self._make_request_with_retry(
            "PUT", 
            f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"
        )
    
    async def remove_reaction(self, channel_id: str, message_id: str, emoji: str) -> None:
        """리액션 제거"""
        # 이모지 URL 인코딩
        if emoji.startswith(":"):
            emoji = emoji.replace(":", "")
        emoji = emoji.replace(" ", "_")
        
        await self._make_request_with_retry(
            "DELETE", 
            f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"
        )
    
    async def get_reactions(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
        limit: int = 25
    ) -> List[DiscordUser]:
        """리액션 사용자 목록 조회"""
        # 이모지 URL 인코딩
        if emoji.startswith(":"):
            emoji = emoji.replace(":", "")
        emoji = emoji.replace(" ", "_")
        
        response = await self._make_request_with_retry(
            "GET", 
            f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}",
            params={"limit": limit}
        )
        
        return [DiscordUser(**user) for user in response]
    
    # Pin 관련 메서드
    # 핀 경로는 `/channels/{id}/pins/...`에서 `/channels/{id}/messages/pins/...`로
    # 옮겨갔고, 새 경로는 MANAGE_MESSAGES가 아니라 별도의 PIN_MESSAGES 권한을
    # 요구한다. 구 경로는 deprecated이므로 현행 경로만 쓴다.
    async def pin_message(self, channel_id: str, message_id: str) -> None:
        """메시지 고정"""
        await self._make_request_with_retry(
            "PUT", f"/channels/{channel_id}/messages/pins/{message_id}"
        )
        await discord_cache.invalidate_channel(channel_id)

    async def unpin_message(self, channel_id: str, message_id: str) -> None:
        """메시지 고정 해제"""
        await self._make_request_with_retry(
            "DELETE", f"/channels/{channel_id}/messages/pins/{message_id}"
        )
        await discord_cache.invalidate_channel(channel_id)

    async def get_pinned_messages(self, channel_id: str) -> List[DiscordMessage]:
        """고정된 메시지 목록.

        현행 경로는 배열이 아니라 `{"items": [{"pinned_at", "message"}], "has_more"}`를
        돌려준다. 구 경로의 배열 형태도 아직 살아 있어 둘 다 받는다.
        """
        response = await self._make_request_with_retry(
            "GET", f"/channels/{channel_id}/messages/pins"
        )
        if isinstance(response, dict):
            items = [item.get("message", item) for item in response.get("items", [])]
        else:
            items = response
        return [DiscordMessage(**msg) for msg in items]

    async def get_roles(self, guild_id: str) -> List[DiscordRole]:
        """역할 목록 조회"""
        response = await self._make_request_with_retry("GET", f"/guilds/{guild_id}/roles")
        return [DiscordRole(**role) for role in response]
    
    async def add_role_to_member(self, guild_id: str, user_id: str, role_id: str) -> None:
        """멤버에게 역할 부여"""
        await self._make_request_with_retry("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")
    
    async def remove_role_from_member(self, guild_id: str, user_id: str, role_id: str) -> None:
        """멤버에서 역할 제거"""
        await self._make_request_with_retry("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")
    
    # Webhook 관련 메서드
    async def create_webhook(
        self,
        channel_id: str,
        name: str,
        avatar: Optional[str] = None
    ) -> DiscordWebhook:
        """웹훅 생성"""
        data = {"name": name}
        if avatar:
            data["avatar"] = avatar
        
        response = await self._make_request_with_retry("POST", f"/channels/{channel_id}/webhooks", data=data)
        return DiscordWebhook(**response)
    
    async def get_webhooks(self, channel_id: str) -> List[Dict[str, Any]]:
        """채널의 웹훅 목록. url은 토큰을 포함하므로 여기서는 그대로 싣지 않는다."""
        return await self._make_request_with_retry("GET", f"/channels/{channel_id}/webhooks")

    async def delete_webhook(self, webhook_id: str) -> None:
        """웹훅 폐기.

        create_webhook은 자격증명을 만든다. 폐기 경로가 없으면 이 서버는
        스스로 만든 것을 회수할 수 없고, 유출된 URL은 영구히 유효하다.
        """
        await self._make_request_with_retry("DELETE", f"/webhooks/{webhook_id}")

    async def send_webhook_message(
        self,
        webhook_url: str,
        content: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        embeds: Optional[List[DiscordEmbed]] = None
    ) -> Dict[str, Any]:
        """웹훅으로 메시지 전송하고 만들어진 메시지를 돌려준다.

        `?wait=true` 없이 부르면 Discord는 204를 주고 메시지 객체를 돌려주지
        않는다. 그러면 방금 만든 글의 id를 알 방법이 없어 지울 수도 없다 —
        되돌릴 수 없는 쓰기를 남기는 셈이라 항상 wait한다.
        """
        # send_message와 동일한 멘션 가드를 적용한다. 없으면 모델이 웹훅 경로로
        # @everyone 필터를 그대로 우회할 수 있다.
        content = self._sanitize_content(content)

        data = {
            "content": content,
            "allowed_mentions": {"parse": []},
        }
        if username:
            data["username"] = username
        if avatar_url:
            data["avatar_url"] = avatar_url
        if embeds:
            data["embeds"] = [embed.model_dump() for embed in embeds]
        
        # 웹훅 URL은 봇 토큰이 아닌 자체 자격증명이라 별도 세션을 쓴다.
        separator = "&" if "?" in webhook_url else "?"
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{webhook_url}{separator}wait=true", json=data) as response:
                if response.status >= 400:
                    try:
                        error_data = await response.json()
                    except Exception:  # noqa: BLE001
                        error_data = {"message": await response.text()}
                    raise DiscordAPIError(
                        error_data.get("message", f"Webhook error: HTTP {response.status}"),
                        status_code=response.status,
                        discord_code=discord_code_of(error_data),
                    )
                return await response.json()
