"""
채널 툴 단위 테스트
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from tools.discord.channels import (
    list_guilds, list_channels, get_channel, 
    create_channel, update_channel, delete_channel
)


@pytest.fixture
def mock_discord_client():
    """Mock Discord 클라이언트"""
    client = AsyncMock()
    return client


@pytest.fixture
def sample_guild():
    """샘플 길드 데이터"""
    return {
        "id": "123456789",
        "name": "Test Guild",
        "icon": None,
        "description": "Test Description"
    }


@pytest.fixture
def sample_channel():
    """샘플 채널 데이터"""
    return {
        "id": "987654321",
        "name": "test-channel",
        "type": 0,
        "guild_id": "123456789",
        "topic": "Test Topic"
    }


@pytest.mark.asyncio
async def test_list_guilds(mock_discord_client, sample_guild):
    """길드 목록 조회 테스트"""
    # Mock 설정
    mock_guild = MagicMock()
    mock_guild.model_dump.return_value = sample_guild
    mock_discord_client.get_guilds.return_value = [mock_guild]
    
    # 툴 클라이언트 설정
    from tools.discord.channels import set_discord_client
    set_discord_client(mock_discord_client)
    
    # 테스트 실행
    result = await list_guilds()
    
    # 검증
    assert result["count"] == 1
    assert result["guilds"][0] == sample_guild
    mock_discord_client.get_guilds.assert_called_once()


@pytest.mark.asyncio
async def test_list_channels(mock_discord_client, sample_channel):
    """채널 목록 조회 테스트"""
    # Mock 설정
    mock_channel = MagicMock()
    mock_channel.model_dump.return_value = sample_channel
    mock_discord_client.get_channels.return_value = [mock_channel]
    
    # 툴 클라이언트 설정
    from tools.discord.channels import set_discord_client
    set_discord_client(mock_discord_client)
    
    # 테스트 실행
    result = await list_channels("123456789")
    
    # 검증
    assert result["guild_id"] == "123456789"
    assert result["count"] == 1
    assert result["channels"][0] == sample_channel
    mock_discord_client.get_channels.assert_called_once_with("123456789")


@pytest.mark.asyncio
async def test_get_channel(mock_discord_client, sample_channel):
    """채널 정보 조회 테스트"""
    # Mock 설정
    mock_channel = MagicMock()
    mock_channel.model_dump.return_value = sample_channel
    mock_discord_client.get_channel.return_value = mock_channel
    
    # 툴 클라이언트 설정
    from tools.discord.channels import set_discord_client
    set_discord_client(mock_discord_client)
    
    # 테스트 실행
    result = await get_channel("987654321")
    
    # 검증
    assert result["channel"] == sample_channel
    mock_discord_client.get_channel.assert_called_once_with("987654321")


@pytest.mark.asyncio
async def test_create_channel(mock_discord_client, sample_channel):
    """채널 생성 테스트"""
    # Mock 설정
    mock_channel = MagicMock()
    mock_channel.model_dump.return_value = sample_channel
    mock_discord_client.create_channel.return_value = mock_channel
    
    # 툴 클라이언트 설정
    from tools.discord.channels import set_discord_client
    set_discord_client(mock_discord_client)
    
    # 테스트 실행
    result = await create_channel(
        guild_id="123456789",
        name="test-channel",
        type=0,
        topic="Test Topic"
    )
    
    # 검증
    assert result["channel"] == sample_channel
    mock_discord_client.create_channel.assert_called_once_with(
        guild_id="123456789",
        name="test-channel",
        type=0,
        topic="Test Topic",
        parent_id=None
    )


@pytest.mark.asyncio
async def test_update_channel(mock_discord_client, sample_channel):
    """채널 수정 테스트"""
    # Mock 설정
    mock_channel = MagicMock()
    mock_channel.model_dump.return_value = sample_channel
    mock_discord_client.update_channel.return_value = mock_channel
    
    # 툴 클라이언트 설정
    from tools.discord.channels import set_discord_client
    set_discord_client(mock_discord_client)
    
    # 테스트 실행
    result = await update_channel(
        channel_id="987654321",
        name="updated-channel",
        topic="Updated Topic"
    )
    
    # 검증
    assert result["channel"] == sample_channel
    mock_discord_client.update_channel.assert_called_once_with(
        channel_id="987654321",
        name="updated-channel",
        topic="Updated Topic",
        position=None
    )


@pytest.mark.asyncio
async def test_delete_channel(mock_discord_client):
    """채널 삭제 테스트"""
    # Mock 설정
    mock_discord_client.delete_channel.return_value = None
    
    # 툴 클라이언트 설정
    from tools.discord.channels import set_discord_client
    set_discord_client(mock_discord_client)
    
    # 테스트 실행
    result = await delete_channel("987654321")
    
    # 검증
    assert "deleted successfully" in result["message"]
    mock_discord_client.delete_channel.assert_called_once_with("987654321")


@pytest.mark.asyncio
async def test_list_guilds_no_client():
    """클라이언트 미설정 시 에러 테스트"""
    # 툴 클라이언트 설정 해제
    from tools.discord.channels import set_discord_client
    set_discord_client(None)
    
    # 테스트 실행 및 검증
    with pytest.raises(ValueError, match="Discord client not initialized"):
        await list_guilds()
