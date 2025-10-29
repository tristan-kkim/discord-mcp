"""
JSON-RPC 핸들러
"""
import time
from typing import Any, Dict, Optional
from fastapi import HTTPException
from loguru import logger

from ..core.tool_registry import tool_registry
from ..core.schema import (
    MCPResponse, MCPError, ErrorCode, 
    ListToolsRequest, ListToolsResponse,
    CallToolRequest, CallToolResponse
)
from ..core.logging import log_tool_call, set_request_context, clear_request_context


class MCPHandler:
    """MCP 요청 핸들러"""
    
    async def handle_list_tools(self, request: ListToolsRequest) -> ListToolsResponse:
        """툴 목록 조회"""
        try:
            tools = tool_registry.list_tools()
            return ListToolsResponse(tools=tools)
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise HTTPException(status_code=500, detail="Failed to list tools")
    
    async def handle_call_tool(self, request: CallToolRequest) -> CallToolResponse:
        """툴 호출"""
        request_id = f"req_{int(time.time() * 1000)}"
        set_request_context(request_id=request_id, tool_name=request.tool)
        
        try:
            # 툴 실행
            result = await tool_registry.call_tool(
                name=request.tool,
                params=request.params
            )
            
            log_tool_call(request.tool, success=True)
            return CallToolResponse(result=result)
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", tool=request.tool, params=request.params)
            log_tool_call(request.tool, success=False, error_message=str(e))
            
            # MCP 에러로 변환
            if isinstance(e, MCPError):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": e.code,
                        "message": e.message,
                        "retry_after_ms": e.retry_after_ms,
                        "rate_limited": e.rate_limited
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": ErrorCode.INTERNAL_ERROR,
                        "message": f"Internal server error: {str(e)}"
                    }
                )
        finally:
            clear_request_context()
    
    async def handle_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """일반적인 MCP 요청 처리"""
        try:
            if method == "list_tools":
                request = ListToolsRequest()
                response = await self.handle_list_tools(request)
                return MCPResponse(
                    success=True,
                    data=response.model_dump()
                ).model_dump()
            
            elif method == "call_tool":
                if not params:
                    raise HTTPException(status_code=400, detail="Missing parameters for call_tool")
                
                request = CallToolRequest(**params)
                response = await self.handle_call_tool(request)
                return MCPResponse(
                    success=True,
                    data=response.model_dump()
                ).model_dump()
            
            else:
                raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Request handling failed: {e}", method=method, params=params)
            return MCPResponse(
                success=False,
                error=MCPError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Request handling failed: {str(e)}"
                )
            ).model_dump()


# 전역 핸들러 인스턴스
mcp_handler = MCPHandler()
