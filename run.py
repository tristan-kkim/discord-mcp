#!/usr/bin/env python3
"""
Discord MCP Server 실행 스크립트
"""
import os
import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from server.main import app
import uvicorn


def main():
    """메인 실행 함수"""
    # 환경 변수 확인
    if not os.getenv("DISCORD_BOT_TOKEN"):
        print("❌ DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        print("   .env 파일을 생성하거나 환경변수를 설정해주세요.")
        sys.exit(1)
    
    # 서버 설정
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    print(f"🚀 Discord MCP Server 시작 중...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Log Level: {log_level}")
    print(f"   Health Check: http://{host}:{port}/health")
    print(f"   API Docs: http://{host}:{port}/docs")
    
    # 서버 실행
    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=os.getenv("ENVIRONMENT") == "development"
    )


if __name__ == "__main__":
    main()
