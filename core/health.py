"""
헬스체크 및 메트릭
"""
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

from .cache import cache_manager
from .schema import ErrorCode, MCPError


@dataclass
class HealthStatus:
    """헬스 상태"""
    status: str
    timestamp: float
    uptime: float
    services: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceMetrics:
    """서비스 메트릭"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    average_latency: float = 0.0
    last_request_time: Optional[float] = None


class HealthChecker:
    """헬스체크 관리자"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = ServiceMetrics()
        self._discord_connected = False
        self._redis_connected = False
    
    def update_discord_status(self, connected: bool) -> None:
        """Discord 연결 상태 업데이트"""
        self._discord_connected = connected
    
    def update_redis_status(self, connected: bool) -> None:
        """Redis 연결 상태 업데이트"""
        self._redis_connected = connected
    
    def record_request(
        self,
        success: bool,
        latency: float,
        rate_limited: bool = False
    ) -> None:
        """요청 메트릭 기록"""
        self.metrics.total_requests += 1
        self.metrics.last_request_time = time.time()
        
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        if rate_limited:
            self.metrics.rate_limited_requests += 1
        
        # 평균 지연시간 업데이트 (이동 평균)
        if self.metrics.average_latency == 0:
            self.metrics.average_latency = latency
        else:
            alpha = 0.1  # 가중치
            self.metrics.average_latency = (
                alpha * latency + (1 - alpha) * self.metrics.average_latency
            )
    
    async def check_discord_health(self) -> Dict[str, Any]:
        """Discord API 헬스체크"""
        try:
            # 실제로는 Discord API ping을 보내야 하지만,
            # 여기서는 연결 상태만 확인
            return {
                "status": "healthy" if self._discord_connected else "unhealthy",
                "connected": self._discord_connected,
                "last_check": time.time()
            }
        except Exception as e:
            logger.error(f"Discord health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "last_check": time.time()
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Redis 헬스체크"""
        try:
            if cache_manager._connected and cache_manager._redis:
                await cache_manager._redis.ping()
                return {
                    "status": "healthy",
                    "connected": True,
                    "last_check": time.time()
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": "Not connected to Redis",
                    "last_check": time.time()
                }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "last_check": time.time()
            }
    
    async def get_health_status(self) -> HealthStatus:
        """전체 헬스 상태 반환"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # 서비스별 헬스체크
        discord_health = await self.check_discord_health()
        redis_health = await self.check_redis_health()
        
        services = {
            "discord": discord_health,
            "redis": redis_health,
        }
        
        # 전체 상태 결정
        all_healthy = all(
            service["status"] == "healthy"
            for service in services.values()
        )
        
        status = "healthy" if all_healthy else "unhealthy"
        
        # 메트릭 정보
        metrics = {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "rate_limited_requests": self.metrics.rate_limited_requests,
            "success_rate": (
                self.metrics.successful_requests / max(self.metrics.total_requests, 1)
            ),
            "average_latency_ms": self.metrics.average_latency * 1000,
            "uptime_seconds": uptime,
        }
        
        return HealthStatus(
            status=status,
            timestamp=current_time,
            uptime=uptime,
            services=services,
            metrics=metrics
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Prometheus 형식 메트릭 반환"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            "discord_mcp_requests_total": self.metrics.total_requests,
            "discord_mcp_requests_successful": self.metrics.successful_requests,
            "discord_mcp_requests_failed": self.metrics.failed_requests,
            "discord_mcp_requests_rate_limited": self.metrics.rate_limited_requests,
            "discord_mcp_request_duration_seconds": self.metrics.average_latency,
            "discord_mcp_uptime_seconds": uptime,
            "discord_mcp_discord_connected": 1 if self._discord_connected else 0,
            "discord_mcp_redis_connected": 1 if self._redis_connected else 0,
        }


# 전역 헬스체커 인스턴스
health_checker = HealthChecker()


async def get_health() -> Dict[str, Any]:
    """헬스체크 엔드포인트용"""
    health_status = await health_checker.get_health_status()
    return {
        "status": health_status.status,
        "timestamp": health_status.timestamp,
        "uptime": health_status.uptime,
        "services": health_status.services,
        "metrics": health_status.metrics
    }


async def get_metrics() -> Dict[str, Any]:
    """메트릭 엔드포인트용"""
    return health_checker.get_metrics()
