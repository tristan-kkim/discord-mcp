"""
재시도 로직 (tenacity 기반)
"""
import asyncio
import random
from typing import Any, Callable, Optional, Type, Union
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
from loguru import logger

from .schema import ErrorCode, MCPError


class RetryConfig:
    """재시도 설정"""
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_multiplier = exponential_multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


# 기본 재시도 설정
DEFAULT_RETRY_CONFIG = RetryConfig()


def create_retry_decorator(config: RetryConfig = DEFAULT_RETRY_CONFIG):
    """재시도 데코레이터 생성"""
    
    def wait_with_jitter(retry_state):
        """지수 백오프 + jitter"""
        attempt = retry_state.attempt_number
        delay = config.base_delay * (config.exponential_multiplier ** (attempt - 1))
        delay = min(delay, config.max_delay)
        
        if config.jitter:
            # ±25% 랜덤 지연
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            
        return max(0, delay)
    
    return retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_with_jitter,
        retry=retry_if_exception_type(config.retryable_exceptions),
        before_sleep=before_sleep_log(logger, "WARNING"),
        after=after_log(logger, "INFO"),
    )


def retry_async(
    func: Callable,
    *args,
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    **kwargs
) -> Any:
    """비동기 함수 재시도 실행"""
    retry_decorator = create_retry_decorator(config)
    decorated_func = retry_decorator(func)
    return decorated_func(*args, **kwargs)


class DiscordAPIError(Exception):
    """Discord API 에러"""
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
        rate_limited: bool = False
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.rate_limited = rate_limited


class RateLimitError(DiscordAPIError):
    """Rate limit 에러"""
    def __init__(self, message: str, retry_after: float):
        super().__init__(message, status_code=429, retry_after=retry_after, rate_limited=True)


class TimeoutError(DiscordAPIError):
    """타임아웃 에러"""
    def __init__(self, message: str):
        super().__init__(message, status_code=408)


def is_retryable_error(error: Exception) -> bool:
    """에러가 재시도 가능한지 확인"""
    if isinstance(error, RateLimitError):
        return True
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, asyncio.TimeoutError):
        return True
    if isinstance(error, ConnectionError):
        return True
    return False


def get_retry_delay(error: Exception, attempt: int) -> float:
    """에러에 따른 재시도 지연 시간 계산"""
    if isinstance(error, RateLimitError) and error.retry_after:
        return error.retry_after
    
    # 지수 백오프
    base_delay = 1.0
    delay = base_delay * (2 ** (attempt - 1))
    return min(delay, 60.0)


async def retry_with_backoff(
    func: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
) -> Any:
    """백오프와 함께 재시도"""
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            if not is_retryable_error(e):
                raise e
                
            if attempt == max_attempts:
                break
                
            delay = get_retry_delay(e, attempt)
            logger.warning(
                f"Attempt {attempt} failed, retrying in {delay:.2f}s",
                error=str(e),
                attempt=attempt,
                delay=delay
            )
            
            await asyncio.sleep(delay)
    
    # 모든 재시도 실패
    if isinstance(last_error, RateLimitError):
        raise MCPError(
            code=ErrorCode.RATE_LIMITED,
            message="Discord API rate limit exceeded",
            retry_after_ms=int(last_error.retry_after * 1000) if last_error.retry_after else None,
            rate_limited=True
        )
    elif isinstance(last_error, TimeoutError):
        raise MCPError(
            code=ErrorCode.TIMEOUT_ERROR,
            message="Request timeout",
            retry_after_ms=5000
        )
    else:
        raise MCPError(
            code=ErrorCode.DISCORD_API_ERROR,
            message=f"Discord API error: {str(last_error)}"
        )
