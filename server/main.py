"""
Discord MCP Server - FastAPI 애플리케이션
"""
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from .rpc import mcp_handler
from ..core.tool_registry import tool_registry
from ..core.cache import cache_manager
from ..core.health import get_health, get_metrics
from ..adapters.discord.http import DiscordClient
from ..tools.discord.channels import register_channel_tools, set_discord_client as set_channel_client
from ..tools.discord.messages import register_message_tools, set_discord_client as set_message_client
from ..tools.discord.threads import register_thread_tools, set_discord_client as set_thread_client
from ..tools.discord.reactions import register_reaction_tools, set_discord_client as set_reaction_client
from ..tools.discord.roles import register_role_tools, set_discord_client as set_role_client
from ..tools.discord.advanced import register_advanced_tools, set_discord_client as set_advanced_client


# 전역 Discord 클라이언트
discord_client: DiscordClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작
    logger.info("Starting Discord MCP Server...")
    
    # 환경 변수 로드
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
    
    # Discord 클라이언트 초기화
    global discord_client
    discord_client = DiscordClient(bot_token)
    await discord_client.connect()
    
    # 툴 클라이언트 설정
    set_channel_client(discord_client)
    set_message_client(discord_client)
    set_thread_client(discord_client)
    set_reaction_client(discord_client)
    set_role_client(discord_client)
    set_advanced_client(discord_client)
    
    # 툴 등록
    register_channel_tools()
    register_message_tools()
    register_thread_tools()
    register_reaction_tools()
    register_role_tools()
    register_advanced_tools()
    
    # 캐시 연결
    await cache_manager.connect()
    
    logger.info("Discord MCP Server started successfully")
    
    yield
    
    # 종료
    logger.info("Shutting down Discord MCP Server...")
    
    if discord_client:
        await discord_client.disconnect()
    
    await cache_manager.disconnect()
    
    logger.info("Discord MCP Server stopped")


# FastAPI 앱 생성
app = FastAPI(
    title="Discord MCP Server",
    description="Model Context Protocol server for Discord integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 요청 모델
class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}


# 엔드포인트들
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "Discord MCP Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return await get_health()


@app.get("/metrics")
async def metrics():
    """메트릭 엔드포인트"""
    return await get_metrics()


@app.post("/mcp/list_tools")
async def list_tools():
    """MCP 툴 목록 조회"""
    try:
        tools = tool_registry.list_tools()
        return {
            "success": True,
            "data": {
                "tools": [tool.model_dump() for tool in tools]
            }
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/call_tool")
async def call_tool(request: MCPRequest):
    """MCP 툴 호출"""
    try:
        result = await mcp_handler.handle_request(request.method, request.params)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """일반적인 MCP 엔드포인트"""
    return await call_tool(request)


# 에러 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error"
            }
        }
    )


# 개발용 실행
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
