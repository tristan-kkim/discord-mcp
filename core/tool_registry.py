"""
MCP 툴 등록 시스템
"""
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass
from loguru import logger

from .schema import ToolDefinition, MCPError, ErrorCode


@dataclass
class ToolHandler:
    """툴 핸들러"""
    name: str
    handler: Callable
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    description: str
    version: str = "v1"


class ToolRegistry:
    """MCP 툴 레지스트리"""
    
    def __init__(self):
        self._tools: Dict[str, ToolHandler] = {}
        self._tool_versions: Dict[str, List[str]] = {}
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        description: str,
        version: str = "v1"
    ) -> None:
        """툴 등록"""
        # 버전 관리
        if name not in self._tool_versions:
            self._tool_versions[name] = []
        
        if version not in self._tool_versions[name]:
            self._tool_versions[name].append(version)
        
        # 툴 핸들러 생성
        tool_handler = ToolHandler(
            name=name,
            handler=handler,
            input_schema=input_schema,
            output_schema=output_schema,
            description=description,
            version=version
        )
        
        # 툴 등록 (버전 포함 키 사용)
        tool_key = f"{name}@{version}"
        self._tools[tool_key] = tool_handler
        
        logger.info(f"Registered tool: {tool_key}")
    
    def get_tool(self, name: str, version: Optional[str] = None) -> Optional[ToolHandler]:
        """툴 가져오기"""
        if version:
            tool_key = f"{name}@{version}"
        else:
            # 최신 버전 사용
            if name in self._tool_versions:
                latest_version = max(self._tool_versions[name])
                tool_key = f"{name}@{latest_version}"
            else:
                return None
        
        return self._tools.get(tool_key)
    
    def list_tools(self, include_versions: bool = False) -> List[ToolDefinition]:
        """등록된 툴 목록 반환"""
        tools = []
        
        for tool_handler in self._tools.values():
            # 중복 제거 (같은 이름의 최신 버전만)
            if not include_versions:
                tool_name = tool_handler.name
                if tool_name in [t.name for t in tools]:
                    continue
                
                # 최신 버전인지 확인
                if tool_name in self._tool_versions:
                    latest_version = max(self._tool_versions[tool_name])
                    if tool_handler.version != latest_version:
                        continue
            
            tool_definition = ToolDefinition(
                name=tool_handler.name,
                description=tool_handler.description,
                input_schema=tool_handler.input_schema,
                output_schema=tool_handler.output_schema,
                version=tool_handler.version
            )
            tools.append(tool_definition)
        
        return sorted(tools, key=lambda t: t.name)
    
    def list_tool_versions(self, name: str) -> List[str]:
        """특정 툴의 버전 목록 반환"""
        return self._tool_versions.get(name, [])
    
    async def call_tool(
        self,
        name: str,
        params: Dict[str, Any],
        version: Optional[str] = None
    ) -> Any:
        """툴 호출"""
        tool_handler = self.get_tool(name, version)
        if not tool_handler:
            raise MCPError(
                code=ErrorCode.NOT_FOUND,
                message=f"Tool '{name}' not found"
            )
        
        try:
            # 입력 검증 (간단한 타입 체크)
            self._validate_input(tool_handler.input_schema, params)
            
            # 툴 실행
            if tool_handler.handler:
                result = await tool_handler.handler(**params)
            else:
                raise MCPError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Tool handler not available"
                )
            
            # 출력 검증
            self._validate_output(tool_handler.output_schema, result)
            
            return result
            
        except MCPError:
            raise
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", tool=name, params=params)
            raise MCPError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Tool execution failed: {str(e)}"
            )
    
    def _validate_input(self, schema: Dict[str, Any], params: Dict[str, Any]) -> None:
        """입력 파라미터 검증"""
        required_props = schema.get("properties", {})
        required_fields = schema.get("required", [])
        
        # 필수 필드 확인
        for field in required_fields:
            if field not in params:
                raise MCPError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Missing required parameter: {field}"
                )
        
        # 타입 검증 (간단한 버전)
        for field, value in params.items():
            if field in required_props:
                expected_type = required_props[field].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    raise MCPError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"Invalid type for parameter '{field}': expected {expected_type}"
                    )
    
    def _validate_output(self, schema: Dict[str, Any], result: Any) -> None:
        """출력 결과 검증"""
        # 간단한 검증만 수행
        if not isinstance(result, (dict, list, str, int, float, bool, type(None))):
            raise MCPError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid output type from tool"
            )
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """타입 체크"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        if expected_type in type_mapping:
            return isinstance(value, type_mapping[expected_type])
        
        return True  # 알 수 없는 타입은 통과
    
    def get_tool_info(self, name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """툴 정보 반환"""
        tool_handler = self.get_tool(name, version)
        if not tool_handler:
            return None
        
        return {
            "name": tool_handler.name,
            "description": tool_handler.description,
            "version": tool_handler.version,
            "input_schema": tool_handler.input_schema,
            "output_schema": tool_handler.output_schema,
            "available_versions": self.list_tool_versions(name)
        }
    
    def unregister_tool(self, name: str, version: Optional[str] = None) -> bool:
        """툴 등록 해제"""
        if version:
            tool_key = f"{name}@{version}"
            if tool_key in self._tools:
                del self._tools[tool_key]
                if name in self._tool_versions:
                    self._tool_versions[name].remove(version)
                    if not self._tool_versions[name]:
                        del self._tool_versions[name]
                return True
        else:
            # 모든 버전 제거
            if name in self._tool_versions:
                versions = self._tool_versions[name].copy()
                for v in versions:
                    tool_key = f"{name}@{v}"
                    if tool_key in self._tools:
                        del self._tools[tool_key]
                del self._tool_versions[name]
                return True
        
        return False


# 전역 툴 레지스트리 인스턴스
tool_registry = ToolRegistry()
