FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY discord_mcp ./discord_mcp

RUN pip install --no-cache-dir --user ".[redis]"

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim

RUN groupadd -r discordmcp && useradd -r -g discordmcp discordmcp

WORKDIR /app

COPY --from=builder /root/.local /home/discordmcp/.local
ENV PATH=/home/discordmcp/.local/bin:$PATH

USER discordmcp

EXPOSE 8000

# /health는 streamable-http 모드에서만 뜬다.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status == 200 else 1)"

# 컨테이너는 네트워크로 서비스하므로 streamable-http가 기본이다.
# stdio로 쓰려면: docker run -i ... discord-mcp discord-mcp --transport stdio
ENTRYPOINT ["discord-mcp"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
