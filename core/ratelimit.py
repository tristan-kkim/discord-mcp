"""
Rate limit 관리
"""
import asyncio
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from .schema import ErrorCode, MCPError


@dataclass
class RateLimitInfo:
    """Rate limit 정보"""
    remaining: int
    reset_after: float
    bucket: Optional[str] = None
    global_limit: bool = False


class RateLimiter:
    """Rate limit 관리자"""
    
    def __init__(self):
        self._buckets: Dict[str, RateLimitInfo] = {}
        self._global_limit: Optional[RateLimitInfo] = None
        self._locks: Dict[str, asyncio.Lock] = {}
    
    def _get_lock(self, bucket: str) -> asyncio.Lock:
        """버킷별 락 가져오기"""
        if bucket not in self._locks:
            self._locks[bucket] = asyncio.Lock()
        return self._locks[bucket]
    
    def update_rate_limit(
        self,
        bucket: str,
        remaining: int,
        reset_after: float,
        is_global: bool = False
    ) -> None:
        """Rate limit 정보 업데이트"""
        rate_limit_info = RateLimitInfo(
            remaining=remaining,
            reset_after=reset_after,
            bucket=bucket,
            global_limit=is_global
        )
        
        if is_global:
            self._global_limit = rate_limit_info
        else:
            self._buckets[bucket] = rate_limit_info
        
        logger.debug(
            "Rate limit updated",
            bucket=bucket,
            remaining=remaining,
            reset_after=reset_after,
            is_global=is_global
        )
    
    async def wait_for_rate_limit(self, bucket: str) -> None:
        """Rate limit 대기"""
        async with self._get_lock(bucket):
            # 글로벌 rate limit 확인
            if self._global_limit and self._global_limit.remaining <= 0:
                wait_time = self._global_limit.reset_after
                logger.warning(
                    "Global rate limit hit, waiting",
                    wait_time=wait_time
                )
                await asyncio.sleep(wait_time)
                self._global_limit = None
            
            # 버킷별 rate limit 확인
            if bucket in self._buckets:
                rate_limit_info = self._buckets[bucket]
                if rate_limit_info.remaining <= 0:
                    wait_time = rate_limit_info.reset_after
                    logger.warning(
                        "Rate limit hit for bucket",
                        bucket=bucket,
                        wait_time=wait_time
                    )
                    await asyncio.sleep(wait_time)
                    # 대기 후 제거
                    del self._buckets[bucket]
    
    def is_rate_limited(self, bucket: str) -> bool:
        """Rate limit 상태 확인"""
        # 글로벌 rate limit 확인
        if self._global_limit and self._global_limit.remaining <= 0:
            return True
        
        # 버킷별 rate limit 확인
        if bucket in self._buckets:
            rate_limit_info = self._buckets[bucket]
            return rate_limit_info.remaining <= 0
        
        return False
    
    def get_remaining_requests(self, bucket: str) -> int:
        """남은 요청 수 반환"""
        if bucket in self._buckets:
            return self._buckets[bucket].remaining
        return 999  # 기본값
    
    def get_reset_time(self, bucket: str) -> float:
        """리셋 시간 반환"""
        if bucket in self._buckets:
            return self._buckets[bucket].reset_after
        return 0.0


class DiscordRateLimiter:
    """Discord API Rate Limiter"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self._bucket_patterns = {
            "guilds": "guilds",
            "channels": "channels",
            "messages": "messages",
            "reactions": "reactions",
            "webhooks": "webhooks",
        }
    
    def _get_bucket(self, endpoint: str) -> str:
        """엔드포인트에서 버킷 추출"""
        for pattern, bucket in self._bucket_patterns.items():
            if pattern in endpoint.lower():
                return bucket
        return "default"
    
    def parse_rate_limit_headers(
        self,
        headers: Dict[str, str],
        endpoint: str
    ) -> Optional[RateLimitInfo]:
        """Rate limit 헤더 파싱"""
        try:
            remaining = int(headers.get("X-RateLimit-Remaining", "1"))
            reset_after = float(headers.get("X-RateLimit-Reset-After", "0"))
            bucket = headers.get("X-RateLimit-Bucket", self._get_bucket(endpoint))
            is_global = headers.get("X-RateLimit-Global", "").lower() == "true"
            
            return RateLimitInfo(
                remaining=remaining,
                reset_after=reset_after,
                bucket=bucket,
                global_limit=is_global
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
            return None
    
    async def handle_rate_limit(
        self,
        endpoint: str,
        headers: Dict[str, str]
    ) -> None:
        """Rate limit 헤더 처리"""
        rate_limit_info = self.parse_rate_limit_headers(headers, endpoint)
        if not rate_limit_info:
            return
        
        bucket = rate_limit_info.bucket or self._get_bucket(endpoint)
        
        # Rate limit 정보 업데이트
        self.rate_limiter.update_rate_limit(
            bucket=bucket,
            remaining=rate_limit_info.remaining,
            reset_after=rate_limit_info.reset_after,
            is_global=rate_limit_info.global_limit
        )
        
        # Rate limit 대기
        if self.rate_limiter.is_rate_limited(bucket):
            await self.rate_limiter.wait_for_rate_limit(bucket)
    
    async def check_rate_limit(self, endpoint: str) -> None:
        """Rate limit 확인 및 대기"""
        bucket = self._get_bucket(endpoint)
        
        if self.rate_limiter.is_rate_limited(bucket):
            await self.rate_limiter.wait_for_rate_limit(bucket)
    
    def get_rate_limit_info(self, endpoint: str) -> Tuple[int, float]:
        """Rate limit 정보 반환 (remaining, reset_time)"""
        bucket = self._get_bucket(endpoint)
        remaining = self.rate_limiter.get_remaining_requests(bucket)
        reset_time = self.rate_limiter.get_reset_time(bucket)
        return remaining, reset_time


# 전역 Rate Limiter 인스턴스
discord_rate_limiter = DiscordRateLimiter()
