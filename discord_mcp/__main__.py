"""
discord-mcp 실행 진입점.

    discord-mcp                                  # stdio (Claude Desktop / Claude Code 기본)
    discord-mcp --transport streamable-http      # HTTP, 127.0.0.1:8000/mcp
"""
import argparse
import sys

from loguru import logger

from .config import Settings
from .core.logging import setup_logging
from .server import build_server


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="discord-mcp",
        description="Model Context Protocol server for Discord.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport. stdio for local clients (default); "
             "streamable-http to serve over the network.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="streamable-http bind host")
    parser.add_argument("--port", type=int, default=8000, help="streamable-http bind port")
    parser.add_argument("--path", default="/mcp", help="streamable-http endpoint path")
    parser.add_argument(
        "--stateless",
        action="store_true",
        help="streamable-http without session affinity (for load-balanced deployments)",
    )
    return parser.parse_args(argv)


def _root_cause(exc: BaseException) -> BaseException:
    """anyio가 씌운 ExceptionGroup을 벗겨 실제 원인을 꺼낸다."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        settings = Settings.from_env()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    setup_logging(settings.log_level)
    server = build_server(settings)

    try:
        if args.transport == "stdio":
            server.run("stdio")
        else:
            logger.info(
                "serving MCP over streamable-http at http://{}:{}{}",
                args.host, args.port, args.path,
            )
            server.run(
                "streamable-http",
                host=args.host,
                port=args.port,
                streamable_http_path=args.path,
                stateless_http=args.stateless,
            )
    except KeyboardInterrupt:  # pragma: no cover
        return 0
    except BaseException as exc:  # noqa: BLE001 - 마지막 진단 지점
        cause = _root_cause(exc)
        # 인증 실패는 설정 실수라 traceback 대신 고칠 방법을 알려준다.
        if "401" in str(cause) or "Unauthorized" in str(cause):
            print(
                "error: Discord rejected the bot token (401 Unauthorized).\n"
                "  Check DISCORD_BOT_TOKEN — it must be the bot's token from the "
                "Bot tab of your application, not the client secret or an OAuth token.",
                file=sys.stderr,
            )
            return 2
        logger.opt(exception=cause).error("discord-mcp exited: {}", cause)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
