"""
Discord REST API 클라이언트
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Union
import aiohttp
from loguru import logger

from ..core.retry import retry_with_backoff, RateLimitError, TimeoutError, DiscordAPIError
from ..core.ratelimit import discord_rate_limiter
from ..core.cache import discord_cache
from ..core.health import health_checker
from ..core.logging import log_discord_api_call
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
                await self._make_request("GET", "/users/@me")
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
                    error_data = await response.json()
                    error_message = error_data.get("message", f"HTTP {response.status}")
                    raise DiscordAPIError(error_message, status_code=response.status)
                
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
        
        # 캐시에서 먼저 확인
        cached_messages = await discord_cache.get_messages(channel_id, limit, after)
        if cached_messages:
            return [DiscordMessage(**msg) for msg in cached_messages.get("messages", [])]
        
        response = await self._make_request_with_retry(
            "GET", 
            f"/channels/{channel_id}/messages", 
            params=params,
            use_cache=True,
            cache_ttl=60  # 메시지는 짧은 TTL
        )
        
        messages = [DiscordMessage(**msg) for msg in response]
        
        # 캐시에 저장
        await discord_cache.set_messages(channel_id, {"messages": response}, limit, after)
        
        return messages
    
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
        
        data = {"content": content}
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
        max_id: Optional[str] = None,
        min_id: Optional[str] = None
    ) -> List[DiscordMessage]:
        """메시지 검색"""
        params = {"q": query}
        if author_id:
            params["author_id"] = author_id
        if has:
            params["has"] = has
        if max_id:
            params["max_id"] = max_id
        if min_id:
            params["min_id"] = min_id
        
        response = await self._make_request_with_retry("GET", f"/guilds/{channel_id}/messages/search", params=params)
        
        # 검색 결과에서 메시지 추출
        messages = []
        for result in response.get("messages", []):
            for message_data in result:
                messages.append(DiscordMessage(**message_data))
        
        return messages
    
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
    
    async def get_threads(self, channel_id: str) -> List[DiscordThread]:
        """스레드 목록 조회"""
        response = await self._make_request_with_retry("GET", f"/channels/{channel_id}/threads")
        return [DiscordThread(**thread) for thread in response.get("threads", [])]
    
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
    async def pin_message(self, channel_id: str, message_id: str) -> None:
        """메시지 고정"""
        await self._make_request_with_retry("PUT", f"/channels/{channel_id}/pins/{message_id}")
    
    async def unpin_message(self, channel_id: str, message_id: str) -> None:
        """메시지 고정 해제"""
        await self._make_request_with_retry("DELETE", f"/channels/{channel_id}/pins/{message_id}")
    
    async def get_pinned_messages(self, channel_id: str) -> List[DiscordMessage]:
        """고정된 메시지 목록 조회"""
        response = await self._make_request_with_retry("GET", f"/channels/{channel_id}/pins")
        return [DiscordMessage(**msg) for msg in response]
    
    # Role 관련 메서드
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
    
    async def send_webhook_message(
        self,
        webhook_url: str,
        content: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        embeds: Optional[List[DiscordEmbed]] = None
    ) -> None:
        """웹훅으로 메시지 전송"""
        data = {"content": content}
        if username:
            data["username"] = username
        if avatar_url:
            data["avatar_url"] = avatar_url
        if embeds:
            data["embeds"] = [embed.model_dump() for embed in embeds]
        
        # 웹훅은 별도 세션 사용
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise DiscordAPIError(f"Webhook error: {error_text}", status_code=response.status)
