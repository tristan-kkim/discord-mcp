"""
환경변수 설정.
"""
import os
from dataclasses import dataclass
from typing import Optional


DISCORD_API = "https://discord.com/api/v10"


@dataclass(frozen=True)
class Settings:
    bot_token: str
    default_guild_id: Optional[str]
    redis_url: Optional[str]
    log_level: str
    api_base_url: str = DISCORD_API

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
        if not token:
            raise RuntimeError(
                "DISCORD_BOT_TOKEN environment variable is required. "
                "Create a bot at https://discord.com/developers/applications "
                "and set DISCORD_BOT_TOKEN to its token."
            )
        return cls(
            bot_token=token,
            # SaseQ/discord-mcp 관례: 서버가 하나로 고정된 배포에서는
            # guild_id를 매 툴 호출마다 넘기지 않아도 되게 한다.
            default_guild_id=os.getenv("DISCORD_GUILD_ID") or None,
            redis_url=os.getenv("REDIS_URL") or None,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            # 엔드투엔드 테스트와 사내 프록시 경유를 위한 탈출구.
            api_base_url=(os.getenv("DISCORD_API_BASE_URL") or DISCORD_API).rstrip("/"),
        )
