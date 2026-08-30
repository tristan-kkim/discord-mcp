"""
내부 에러 타입.

MCP 프로토콜 메시지 모델은 여기에 두지 않는다. 그건 `mcp` SDK가 소유한다
(`mcp.types`). 이 모듈은 어댑터/코어 계층이 던지는 도메인 에러만 정의한다.
"""
from typing import Optional
from enum import Enum


class ErrorCode(int, Enum):
    """에러 코드 정의"""
    SUCCESS = 0
    INVALID_PARAMS = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMITED = 429
    INTERNAL_ERROR = 500
    DISCORD_API_ERROR = 1000
    VALIDATION_ERROR = 1001
    TIMEOUT_ERROR = 1002


class MCPError(Exception):
    """
    도메인 에러.

    반드시 Exception을 상속해야 한다 — 이전 버전은 pydantic BaseModel이라
    `raise MCPError(...)`가 TypeError로 죽었다 (rate limit / timeout 경로 전부).
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        retry_after_ms: Optional[int] = None,
        rate_limited: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retry_after_ms = retry_after_ms
        self.rate_limited = rate_limited

    def __str__(self) -> str:
        suffix = f" (retry after {self.retry_after_ms}ms)" if self.retry_after_ms else ""
        return f"[{self.code.name}] {self.message}{suffix}"
