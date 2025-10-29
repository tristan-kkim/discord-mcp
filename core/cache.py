"""
Redis 기반 캐싱
"""
import json
import hashlib
from typing import Any, Optional, Dict, Union
import redis.asyncio as redis
from loguru import logger

from .schema import ErrorCode, MCPError


class CacheManager:
    """캐시 관리자"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 300):
        self.redis_url = redis_url
        self.ttl = ttl
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Redis 연결"""
        try:
            self._redis = redis.from_url(self.redis_url)
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._connected = False
    
    async def disconnect(self) -> None:
        """Redis 연결 해제"""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Redis cache")
    
    def _generate_key(self, prefix: str, identifier: str, params: Optional[Dict] = None) -> str:
        """캐시 키 생성"""
        key_parts = [prefix, identifier]
        if params:
            # 파라미터를 정렬하여 일관된 키 생성
            sorted_params = sorted(params.items())
            param_str = json.dumps(sorted_params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        return ":".join(key_parts)
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        if not self._connected or not self._redis:
            return None
        
        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to get cache value: {e}")
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """캐시에 값 저장"""
        if not self._connected or not self._redis:
            return False
        
        try:
            ttl = ttl or self.ttl
            serialized_value = json.dumps(value, ensure_ascii=False)
            await self._redis.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.warning(f"Failed to set cache value: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if not self._connected or not self._redis:
            return False
        
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete cache value: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """패턴에 맞는 키들 삭제"""
        if not self._connected or not self._redis:
            return 0
        
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Failed to delete cache pattern: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        if not self._connected or not self._redis:
            return False
        
        try:
            return await self._redis.exists(key)
        except Exception as e:
            logger.warning(f"Failed to check cache existence: {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """캐시에서 가져오거나 팩토리 함수로 생성"""
        # 캐시에서 먼저 확인
        cached_value = await self.get(key)
        if cached_value is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached_value
        
        # 캐시에 없으면 팩토리 함수 실행
        logger.debug(f"Cache miss for key: {key}")
        try:
            value = await factory(*args, **kwargs) if callable(factory) else factory
            await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Factory function failed: {e}")
            raise MCPError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to generate cache value: {str(e)}"
            )


class DiscordCache:
    """Discord API 캐시"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.prefixes = {
            "guild": "discord:guild",
            "channel": "discord:channel",
            "message": "discord:message",
            "user": "discord:user",
            "role": "discord:role",
        }
    
    async def get_guild(self, guild_id: str) -> Optional[Dict]:
        """길드 정보 캐시에서 가져오기"""
        key = self.cache._generate_key(self.prefixes["guild"], guild_id)
        return await self.cache.get(key)
    
    async def set_guild(self, guild_id: str, guild_data: Dict, ttl: int = 300) -> bool:
        """길드 정보 캐시에 저장"""
        key = self.cache._generate_key(self.prefixes["guild"], guild_id)
        return await self.cache.set(key, guild_data, ttl)
    
    async def get_channel(self, channel_id: str) -> Optional[Dict]:
        """채널 정보 캐시에서 가져오기"""
        key = self.cache._generate_key(self.prefixes["channel"], channel_id)
        return await self.cache.get(key)
    
    async def set_channel(self, channel_id: str, channel_data: Dict, ttl: int = 300) -> bool:
        """채널 정보 캐시에 저장"""
        key = self.cache._generate_key(self.prefixes["channel"], channel_id)
        return await self.cache.set(key, channel_data, ttl)
    
    async def get_messages(
        self,
        channel_id: str,
        limit: int,
        after: Optional[str] = None
    ) -> Optional[Dict]:
        """메시지 목록 캐시에서 가져오기"""
        params = {"limit": limit, "after": after}
        key = self.cache._generate_key(
            f"{self.prefixes['message']}:list",
            channel_id,
            params
        )
        return await self.cache.get(key)
    
    async def set_messages(
        self,
        channel_id: str,
        messages_data: Dict,
        limit: int,
        after: Optional[str] = None,
        ttl: int = 60
    ) -> bool:
        """메시지 목록 캐시에 저장"""
        params = {"limit": limit, "after": after}
        key = self.cache._generate_key(
            f"{self.prefixes['message']}:list",
            channel_id,
            params
        )
        return await self.cache.set(key, messages_data, ttl)
    
    async def invalidate_channel(self, channel_id: str) -> None:
        """채널 관련 캐시 무효화"""
        patterns = [
            f"{self.prefixes['channel']}:{channel_id}",
            f"{self.prefixes['message']}:list:{channel_id}:*",
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
    
    async def invalidate_guild(self, guild_id: str) -> None:
        """길드 관련 캐시 무효화"""
        patterns = [
            f"{self.prefixes['guild']}:{guild_id}",
            f"{self.prefixes['channel']}:*",  # 모든 채널 캐시 무효화
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)


# 전역 캐시 인스턴스
cache_manager = CacheManager()
discord_cache = DiscordCache(cache_manager)
