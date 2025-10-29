"""
구조화 로깅 설정 (JSON 포맷)
"""
import json
import sys
import uuid
from typing import Any, Dict, Optional
from loguru import logger
from contextvars import ContextVar

# 요청 컨텍스트 변수
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
tool_name_var: ContextVar[Optional[str]] = ContextVar('tool_name', default=None)
channel_id_var: ContextVar[Optional[str]] = ContextVar('channel_id', default=None)


def get_request_id() -> str:
    """현재 요청 ID를 가져오거나 새로 생성"""
    request_id = request_id_var.get()
    if not request_id:
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
    return request_id


def set_request_context(
    request_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    channel_id: Optional[str] = None
) -> None:
    """요청 컨텍스트 설정"""
    if request_id:
        request_id_var.set(request_id)
    if tool_name:
        tool_name_var.set(tool_name)
    if channel_id:
        channel_id_var.set(channel_id)


def clear_request_context() -> None:
    """요청 컨텍스트 초기화"""
    request_id_var.set(None)
    tool_name_var.set(None)
    channel_id_var.set(None)


class JSONFormatter:
    """JSON 포맷터"""
    
    def format(self, record: Dict[str, Any]) -> str:
        """레코드를 JSON으로 포맷"""
        # 기본 필드
        log_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
        }
        
        # 요청 컨텍스트 추가
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
            
        tool_name = tool_name_var.get()
        if tool_name:
            log_data["tool"] = tool_name
            
        channel_id = channel_id_var.get()
        if channel_id:
            log_data["channel_id"] = channel_id
        
        # 추가 필드들
        extra = record.get("extra", {})
        for key, value in extra.items():
            log_data[key] = value
            
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(log_level: str = "INFO") -> None:
    """로깅 설정"""
    # 기존 핸들러 제거
    logger.remove()
    
    # JSON 포맷터로 콘솔 출력
    logger.add(
        sys.stdout,
        format=JSONFormatter().format,
        level=log_level,
        serialize=False,
    )
    
    # 파일 출력 (선택사항)
    logger.add(
        "logs/discord-mcp.log",
        format=JSONFormatter().format,
        level=log_level,
        rotation="1 day",
        retention="30 days",
        serialize=False,
    )


def log_tool_call(
    tool_name: str,
    channel_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
    hit_rate_limit: bool = False,
    retry_count: int = 0,
    success: bool = True,
    error_message: Optional[str] = None,
    **kwargs
) -> None:
    """툴 호출 로그"""
    log_data = {
        "tool": tool_name,
        "success": success,
    }
    
    if channel_id:
        log_data["channel_id"] = channel_id
        
    if latency_ms is not None:
        log_data["latency_ms"] = latency_ms
        
    if hit_rate_limit:
        log_data["hit_rate_limit"] = hit_rate_limit
        
    if retry_count > 0:
        log_data["retry_count"] = retry_count
        
    if error_message:
        log_data["error_message"] = error_message
        
    # 추가 필드들
    log_data.update(kwargs)
    
    if success:
        logger.info("Tool call completed", **log_data)
    else:
        logger.error("Tool call failed", **log_data)


def log_discord_api_call(
    method: str,
    endpoint: str,
    status_code: int,
    latency_ms: float,
    rate_limit_remaining: Optional[int] = None,
    **kwargs
) -> None:
    """Discord API 호출 로그"""
    log_data = {
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "latency_ms": latency_ms,
    }
    
    if rate_limit_remaining is not None:
        log_data["rate_limit_remaining"] = rate_limit_remaining
        
    log_data.update(kwargs)
    
    if 200 <= status_code < 300:
        logger.info("Discord API call successful", **log_data)
    elif status_code == 429:
        logger.warning("Discord API rate limited", **log_data)
    else:
        logger.error("Discord API call failed", **log_data)


# 로깅 초기화
setup_logging()
