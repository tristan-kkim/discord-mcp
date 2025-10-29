# 멀티스테이지 빌드
FROM python:3.12-slim as builder

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 프로덕션 이미지
FROM python:3.12-slim

# 비루트 사용자 생성
RUN groupadd -r discordmcp && useradd -r -g discordmcp discordmcp

# 작업 디렉토리 설정
WORKDIR /app

# 빌드된 패키지 복사
COPY --from=builder /root/.local /home/discordmcp/.local

# 애플리케이션 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p logs && chown -R discordmcp:discordmcp /app

# 사용자 변경
USER discordmcp

# PATH 설정
ENV PATH=/home/discordmcp/.local/bin:$PATH

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 실행 명령
CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
