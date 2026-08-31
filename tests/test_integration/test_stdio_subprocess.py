"""
엔드투엔드 검증: 설치된 `discord-mcp` 바이너리를 진짜 서브프로세스로 띄우고,
진짜 MCP 클라이언트를 stdio로 붙여 프로토콜 왕복을 확인한다.

in-process 테스트와 달리 이건 실제 배포 경로를 그대로 탄다 —
콘솔 스크립트, 프로세스 경계, stdout 프레이밍까지 전부 포함된다.
Claude Desktop이 이 서버를 띄우는 방식과 동일하다.
"""
import os
import shutil
import sys

import pytest
from mcp import Client, StdioServerParameters

from tests.stub_discord_api import serve


def _find_binary() -> str | None:
    """PATH를 먼저 보고, 없으면 현재 venv의 bin에서 찾는다."""
    found = shutil.which("discord-mcp")
    if found:
        return found
    local = os.path.join(sys.exec_prefix, "bin", "discord-mcp")
    return local if os.path.exists(local) else None


BINARY = _find_binary()

pytestmark = pytest.mark.skipif(
    BINARY is None,
    reason="discord-mcp is not on PATH; run `pip install -e .` first",
)


@pytest.fixture(scope="module")
def stub_api():
    server, base_url = serve()
    yield base_url
    server.shutdown()


@pytest.fixture
def stdio_server(stub_api):
    return StdioServerParameters(
        command=BINARY,
        args=["--transport", "stdio"],
        env={
            "DISCORD_BOT_TOKEN": "stub-token",
            "DISCORD_API_BASE_URL": stub_api,
            "DISCORD_GUILD_ID": "111",
            "LOG_LEVEL": "CRITICAL",
            "PATH": sys.exec_prefix + "/bin",
        },
    )


async def test_stdio_subprocess_full_round_trip(stdio_server):
    """initialize → tools/list → tools/call 이 실제 프로세스 경계를 넘어 동작한다."""
    async with Client(stdio_server) as session:
        assert session.server_info.name == "discord-mcp"

        tools = (await session.list_tools()).tools
        assert len(tools) == 33, f"expected 33 tools, got {len(tools)}"

        guilds = await session.call_tool("list_guilds", {})
        assert guilds.is_error is False
        assert guilds.structured_content["result"]["guilds"][0]["name"] == "Stub Guild"

        # DISCORD_GUILD_ID가 설정돼 있으니 guild_id 없이 호출된다.
        channels = await session.call_tool("list_channels", {})
        assert channels.is_error is False
        assert channels.structured_content["result"]["channels"][0]["name"] == "general"

        sent = await session.call_tool(
            "send_message", {"channel_id": "222", "content": "hello"}
        )
        assert sent.is_error is False
        assert sent.structured_content["result"]["message"]["id"] == "333"


async def test_unknown_tool_is_a_protocol_error(stdio_server):
    """존재하지 않는 툴은 프로토콜 에러로 처리된다."""
    async with Client(stdio_server) as session:
        result = await session.call_tool("no_such_tool", {})
    assert result.is_error is True


async def test_missing_access_reaches_the_model_over_stdio(stdio_server):
    """
    가장 중요한 왕복이다. 봇이 볼 수 없는 채널을 읽으면 Discord는
    `{"message": "Missing Access", "code": 50001}`을 준다. 이 이유가 프로세스
    경계를 넘어 모델에게 도달하지 않으면, 모델은 `Error executing tool
    list_messages` 한 줄만 보고 다음에 무엇을 할지 알 수 없다.
    """
    async with Client(stdio_server) as session:
        result = await session.call_tool("list_messages", {"channel_id": "444"})

    assert result.is_error is True
    text = " ".join(getattr(block, "text", "") for block in result.content)
    assert "Missing Access" in text
    assert "get_permissions" in text, "the error should point at the diagnostic tool"


async def test_get_permissions_names_the_blocked_tools(stdio_server):
    """403을 만난 모델이 다음에 부를 툴이 실제로 원인을 짚어줘야 한다."""
    async with Client(stdio_server) as session:
        result = await session.call_tool("get_permissions", {})

    assert result.is_error is False
    report = result.structured_content["result"]
    assert "VIEW_CHANNEL" in report["guild_permissions"]
    # 스텁 봇에는 MANAGE_CHANNELS가 없으므로 채널 관리 툴이 막혀 있어야 한다.
    assert "MANAGE_CHANNELS" in report["blocked_tools"]["create_channel"]


async def test_search_scans_history_instead_of_calling_discord_search(stdio_server):
    """
    스텁에는 `/guilds/*/messages/search` 라우트가 없다. 이전 구현이었다면
    404로 죽는다. 지금은 채널 기록을 읽어 여기서 거른다.
    """
    async with Client(stdio_server) as session:
        result = await session.call_tool(
            "search_messages", {"channel_id": "222", "query": "hello"}
        )

    assert result.is_error is False
    found = result.structured_content["result"]
    assert found["count"] == 1
    assert found["messages"][0]["id"] == "333"


async def test_search_miss_says_how_far_it_looked(stdio_server):
    async with Client(stdio_server) as session:
        result = await session.call_tool(
            "search_messages", {"channel_id": "222", "query": "nonexistent"}
        )

    found = result.structured_content["result"]
    assert found["count"] == 0
    assert found["scanned"] == 200
