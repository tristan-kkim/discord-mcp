"""
Pydantic 모델 및 JSON Schema 정의
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
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


class MCPError(BaseModel):
    """MCP 에러 응답 모델"""
    code: ErrorCode = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    retry_after_ms: Optional[int] = Field(None, description="재시도 대기 시간 (밀리초)")
    rate_limited: bool = Field(False, description="Rate limit 여부")


class MCPResponse(BaseModel):
    """MCP 응답 기본 모델"""
    success: bool = Field(..., description="성공 여부")
    data: Optional[Any] = Field(None, description="응답 데이터")
    error: Optional[MCPError] = Field(None, description="에러 정보")


class ToolDefinition(BaseModel):
    """MCP 툴 정의"""
    name: str = Field(..., description="툴 이름")
    description: str = Field(..., description="툴 설명")
    input_schema: Dict[str, Any] = Field(..., description="입력 JSON Schema")
    output_schema: Dict[str, Any] = Field(..., description="출력 JSON Schema")
    version: str = Field("v1", description="툴 버전")


class ListToolsRequest(BaseModel):
    """툴 목록 조회 요청"""
    pass


class ListToolsResponse(BaseModel):
    """툴 목록 조회 응답"""
    tools: List[ToolDefinition] = Field(..., description="사용 가능한 툴 목록")


class CallToolRequest(BaseModel):
    """툴 호출 요청"""
    tool: str = Field(..., description="호출할 툴 이름")
    params: Dict[str, Any] = Field(default_factory=dict, description="툴 파라미터")


class CallToolResponse(BaseModel):
    """툴 호출 응답"""
    result: Any = Field(..., description="툴 실행 결과")


# Discord 관련 모델들
class DiscordUser(BaseModel):
    """Discord 사용자 모델"""
    id: str = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자명")
    discriminator: str = Field(..., description="구분자")
    avatar: Optional[str] = Field(None, description="아바타 해시")
    bot: bool = Field(False, description="봇 여부")


class DiscordChannel(BaseModel):
    """Discord 채널 모델"""
    id: str = Field(..., description="채널 ID")
    name: str = Field(..., description="채널 이름")
    type: int = Field(..., description="채널 타입")
    guild_id: Optional[str] = Field(None, description="길드 ID")
    position: Optional[int] = Field(None, description="위치")
    topic: Optional[str] = Field(None, description="주제")
    nsfw: bool = Field(False, description="NSFW 여부")


class DiscordGuild(BaseModel):
    """Discord 길드 모델"""
    id: str = Field(..., description="길드 ID")
    name: str = Field(..., description="길드 이름")
    icon: Optional[str] = Field(None, description="아이콘 해시")
    description: Optional[str] = Field(None, description="설명")
    member_count: Optional[int] = Field(None, description="멤버 수")


class DiscordEmbed(BaseModel):
    """Discord 임베드 모델"""
    title: Optional[str] = Field(None, description="제목")
    description: Optional[str] = Field(None, description="설명")
    color: Optional[int] = Field(None, description="색상")
    fields: List[Dict[str, Any]] = Field(default_factory=list, description="필드 목록")


class DiscordMessage(BaseModel):
    """Discord 메시지 모델"""
    id: str = Field(..., description="메시지 ID")
    channel_id: str = Field(..., description="채널 ID")
    content: str = Field(..., description="메시지 내용")
    author: DiscordUser = Field(..., description="작성자")
    timestamp: str = Field(..., description="작성 시간")
    edited_timestamp: Optional[str] = Field(None, description="수정 시간")
    embeds: List[DiscordEmbed] = Field(default_factory=list, description="임베드 목록")
    reactions: List[Dict[str, Any]] = Field(default_factory=list, description="리액션 목록")
    pinned: bool = Field(False, description="고정 여부")


class DiscordReaction(BaseModel):
    """Discord 리액션 모델"""
    emoji: str = Field(..., description="이모지")
    count: int = Field(..., description="개수")
    me: bool = Field(False, description="내가 리액션했는지 여부")


class DiscordThread(BaseModel):
    """Discord 스레드 모델"""
    id: str = Field(..., description="스레드 ID")
    name: str = Field(..., description="스레드 이름")
    type: int = Field(..., description="스레드 타입")
    guild_id: str = Field(..., description="길드 ID")
    parent_id: str = Field(..., description="부모 채널 ID")
    archived: bool = Field(False, description="아카이브 여부")
    locked: bool = Field(False, description="잠금 여부")


class DiscordRole(BaseModel):
    """Discord 역할 모델"""
    id: str = Field(..., description="역할 ID")
    name: str = Field(..., description="역할 이름")
    color: int = Field(..., description="색상")
    position: int = Field(..., description="위치")
    permissions: str = Field(..., description="권한")
    mentionable: bool = Field(False, description="멘션 가능 여부")


# 툴별 입력/출력 스키마
def create_json_schema(model: type[BaseModel]) -> Dict[str, Any]:
    """Pydantic 모델을 JSON Schema로 변환"""
    return model.model_json_schema()


# 공통 스키마
COMMON_SCHEMAS = {
    "error": create_json_schema(MCPError),
    "response": create_json_schema(MCPResponse),
    "tool_definition": create_json_schema(ToolDefinition),
    "list_tools_request": create_json_schema(ListToolsRequest),
    "list_tools_response": create_json_schema(ListToolsResponse),
    "call_tool_request": create_json_schema(CallToolRequest),
    "call_tool_response": create_json_schema(CallToolResponse),
}
