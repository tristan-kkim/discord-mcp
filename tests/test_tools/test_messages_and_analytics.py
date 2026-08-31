"""
메시지 읽기/검색/분석 계열의 회귀 테스트.

여기 묶인 것들은 전부 "에러 없이 조용히 틀린 답을 주던" 경로다.
크래시는 눈에 띄지만 이런 것은 안 띈다.
"""
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock

from discord_mcp.adapters.discord.models import DiscordMessage
from discord_mcp.core.render import CONTENT_INTENT_HINT
from discord_mcp.tools.discord import advanced, messages


def make_message(
    id="1", content="hello", author_name="alice", author_id="a1",
    minutes_ago=0, reactions=None, embeds=None, attachments=None,
):
    stamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return DiscordMessage(
        id=id,
        channel_id="c1",
        author={"id": author_id, "username": author_name},
        content=content,
        timestamp=stamp.isoformat(),
        reactions=reactions or [],
        embeds=embeds or [],
        attachments=attachments or [],
    )


@pytest.fixture
def client():
    c = AsyncMock()
    messages.set_discord_client(c)
    advanced.set_discord_client(c)
    yield c
    messages.set_discord_client(None)
    advanced.set_discord_client(None)


# ------------------------------------------------------------------ 응답 크기
async def test_list_messages_returns_only_fields_the_model_uses(client):
    """
    실측: 메시지 2건이 1.4k 토큰이었고 nonce/sticker_items/components 같은
    필드가 전부 null인 채로 실려 있었다.
    """
    client.iter_messages.return_value = [make_message()]

    message = (await messages.list_messages("c1"))["messages"][0]

    assert message["content"] == "hello"
    assert message["author"] == {"id": "a1", "name": "alice"}
    for junk in ("nonce", "sticker_items", "components", "mention_channels",
                 "application_id", "tts", "type", "flags", "webhook_id"):
        assert junk not in message


async def test_list_messages_returns_paging_cursors(client):
    """커서를 안 주면 모델이 다음 페이지를 요청할 방법을 스스로 조립해야 한다."""
    client.iter_messages.return_value = [make_message(id="9"), make_message(id="5")]

    result = await messages.list_messages("c1")

    assert result["newest_message_id"] == "9"
    assert result["oldest_message_id"] == "5"


async def test_list_messages_pages_past_the_100_cap(client):
    """limit>100은 어댑터의 페이지네이터로 가야 한다. 이전엔 조용히 잘렸다."""
    client.iter_messages.return_value = []

    await messages.list_messages("c1", limit=300)

    assert client.iter_messages.await_args.kwargs["limit"] == 300


# ------------------------------------------- Message Content Intent 조용한 실패
async def test_all_empty_content_is_reported_not_swallowed(client):
    """
    Intent가 꺼지면 Discord는 에러 없이 본문을 비운다. 실측한 이 계정이
    바로 그 상태였고, 빈 채널과 구분할 방법이 없었다.
    """
    client.iter_messages.return_value = [make_message(content=""), make_message(content="")]

    result = await messages.list_messages("c1")

    assert result["warning"] == CONTENT_INTENT_HINT


async def test_one_real_message_means_no_false_alarm(client):
    client.iter_messages.return_value = [make_message(content=""), make_message(content="hi")]

    assert "warning" not in await messages.list_messages("c1")


# ---------------------------------------------------------------------- 검색
async def test_search_reports_how_far_it_looked(client):
    """
    봇에게는 서버사이드 검색이 없다. 못 찾은 것이 "없음"인지 "더 뒤"인지
    구분되지 않으면 모델이 잘못된 결론을 낸다.
    """
    client.search_messages.return_value = []

    result = await messages.search_messages("c1", "deploy", scan_limit=500)

    assert result["scanned"] == 500
    assert "scan_limit" in result["note"]


# ------------------------------------------------------------------- 임베드
async def test_embeds_argument_works(client):
    """
    `DiscordEmbed`가 import되어 있지 않아, embeds를 넘긴 send_message는
    전부 NameError로 죽었다.
    """
    client.send_message.return_value = make_message()

    await messages.send_message("c1", "hi", embeds=[{"title": "T", "description": "D"}])

    sent = client.send_message.await_args.kwargs["embeds"]
    assert sent[0].title == "T"


async def test_malformed_embed_explains_the_shape(client):
    with pytest.raises(ValueError, match="title, description"):
        await messages.send_message("c1", "hi", embeds=["not an object"])


async def test_oversized_content_is_caught_before_the_api_call(client):
    with pytest.raises(ValueError, match="2000"):
        await messages.send_message("c1", "x" * 2001)

    client.send_message.assert_not_awaited()


# ----------------------------------------------------------------- 활동 분석
async def test_analyze_honours_the_days_window(client):
    """
    `days`는 받아서 출력에 되풀이할 뿐 필터링에 쓰이지 않았다. 90일 전 글이
    "최근 7일" 통계에 그대로 섞여 들어갔다.
    """
    client.iter_messages.return_value = [
        make_message(id="1", minutes_ago=60),
        make_message(id="2", minutes_ago=60 * 24 * 30, author_name="bob"),
    ]

    result = await advanced.analyze_channel_activity("c1", days=7)

    assert result["total_messages"] == 1
    assert result["unique_authors"] == 1


async def test_analyze_reports_the_span_it_actually_saw(client):
    """요청한 창과 데이터가 있는 구간은 다르다. 둘을 섞으면 거짓 보고가 된다."""
    client.iter_messages.return_value = [make_message(minutes_ago=30)]

    result = await advanced.analyze_channel_activity("c1", days=30)

    assert result["requested_days"] == 30
    assert result["observed_from"] is not None


async def test_analyze_admits_when_the_scan_limit_truncated_it(client):
    """limit에 걸려 창을 다 못 봤는데 조용하면, 부분 통계가 전체로 읽힌다."""
    client.iter_messages.return_value = [make_message(id=str(i)) for i in range(5)]

    result = await advanced.analyze_channel_activity("c1", days=7, limit=5)

    assert "truncated" in result


async def test_rank_rejects_an_unknown_sort_key(client):
    """이전엔 모르는 sort_by를 그냥 무시하고 정렬 없이 돌려줬다."""
    client.iter_messages.return_value = [make_message()]

    with pytest.raises(ValueError, match="score, reactions, timestamp"):
        await advanced.rank_messages("c1", sort_by="popularity")


async def test_sync_since_returns_the_next_cursor(client):
    client.get_messages.return_value = [make_message(id="20"), make_message(id="15")]

    result = await advanced.sync_since("c1", last_message_id="10")

    assert result["latest_message_id"] == "20"
    assert result["new_messages"] == 2


async def test_sync_since_with_nothing_new_keeps_the_cursor(client):
    client.get_messages.return_value = []

    assert (await advanced.sync_since("c1", "10"))["latest_message_id"] == "10"


# ------------------------------------------------------------- 컨텍스트 예산
async def test_long_bodies_are_cut_and_say_so(client):
    """
    Message Content Intent를 켜자 크기 문제가 null 노이즈에서 본문으로
    옮겨갔다. 실측: list_messages(limit=150)이 32.5k 토큰.
    """
    client.iter_messages.return_value = [make_message(content="x" * 3000)]

    result = await messages.list_messages("c1")

    body = result["messages"][0]
    assert len(body["content"]) <= 501
    assert body["truncated"] is True
    assert result["truncated_messages"] == 1
    assert "get_message" in result["note"]


async def test_short_bodies_are_left_alone(client):
    client.iter_messages.return_value = [make_message(content="short")]

    result = await messages.list_messages("c1")

    assert result["messages"][0]["content"] == "short"
    assert "truncated" not in result["messages"][0]
    assert "truncated_messages" not in result


async def test_content_limit_zero_returns_full_text(client):
    """자르기는 기본값이지 감옥이 아니다. 필요하면 전문을 받을 수 있어야 한다."""
    client.iter_messages.return_value = [make_message(content="x" * 3000)]

    result = await messages.list_messages("c1", content_limit=0)

    assert len(result["messages"][0]["content"]) == 3000


async def test_get_message_is_never_truncated(client):
    """잘린 본문의 전문을 받으러 오는 곳이므로 여기서 자르면 탈출구가 없다."""
    client.get_message.return_value = make_message(content="x" * 3000)

    result = await messages.get_message("c1", "1")

    assert len(result["message"]["content"]) == 3000


async def test_embed_text_is_cut_too(client):
    """봇 공지는 본문이 아니라 임베드에 길게 들어간다."""
    client.iter_messages.return_value = [
        make_message(content="hi", embeds=[{"description": "z" * 3000}])
    ]

    embed = (await messages.list_messages("c1"))["messages"][0]["embeds"][0]

    assert len(embed["description"]) <= 501


async def test_search_caps_results_but_reports_the_real_total(client):
    """
    넓은 질의가 수백 건을 맞히면 전부 돌려주는 것이 곧 컨텍스트 폭발이다 —
    실측으로 has=embed 한 번이 26k 토큰이었다. 총계는 남겨야 모델이
    "좁은 적중"과 "홍수"를 구분한다.
    """
    client.search_messages.return_value = [make_message(id=str(i)) for i in range(150)]

    result = await messages.search_messages("c1", "x", max_results=10)

    assert result["count"] == 10
    assert result["matched"] == 150
    assert "150 messages matched" in result["note"]


async def test_search_within_the_cap_says_nothing_about_flooding(client):
    client.search_messages.return_value = [make_message(id="1")]

    result = await messages.search_messages("c1", "x", max_results=10)

    assert result["matched"] == 1
    assert "matched; showing" not in result["note"]


async def test_scoring_sees_the_full_text_not_the_preview(client):
    """
    본문을 먼저 자르면 미리보기 길이 뒤의 키워드와 링크가 점수에서 사라진다.
    자르기는 출력 직전에만 일어나야 한다.
    """
    buried = "a" * 1000 + " https://example.com deploy"
    client.iter_messages.return_value = [make_message(content=buried)]

    result = await advanced.rank_messages("c1", keywords=["deploy"])

    scored = result["ranked_messages"][0]
    assert scored["score"] >= 3.0, "link (+2) and keyword (+1) past the preview were missed"
    assert len(scored["content"]) <= 201, "the output should still be a preview"
    assert scored["truncated"] is True


async def test_triage_output_drops_embed_bodies(client):
    """순위는 무엇을 더 볼지 고르는 자리다. 임베드 전문까지 실을 이유가 없다."""
    client.iter_messages.return_value = [
        make_message(content="hi", embeds=[{"description": "z" * 2000}])
    ]

    ranked = (await advanced.rank_messages("c1"))["ranked_messages"][0]

    assert "embeds" not in ranked


async def test_activity_stats_use_full_text(client):
    """link_ratio를 미리보기로 계산하면 긴 글의 링크를 놓쳐 통계가 틀어진다."""
    client.iter_messages.return_value = [make_message(content="a" * 1000 + " http://x.io")]

    assert (await advanced.analyze_channel_activity("c1", days=7))["link_ratio"] == 1.0


# ------------------------------------------------------------- 시스템 메시지
def _system(id="1", kind=6):
    """Discord가 만든 시스템 메시지. content가 비어 있는 게 정상이다."""
    return DiscordMessage(
        id=id, channel_id="c1", author={"id": "b", "username": "bot"},
        content="", timestamp="2026-01-01T00:00:00+00:00", type=kind,
    )


async def test_system_messages_say_what_they_are(client):
    """
    pin_message는 채널에 type 6을 남기고 unpin으로는 안 지워진다. 라벨이
    없으면 모델에게는 본문 없는 정체불명 항목으로 보인다.
    """
    client.iter_messages.return_value = [_system(kind=6)]

    m = (await messages.list_messages("c1"))["messages"][0]

    assert m["system_event"] == "pinned_a_message"


async def test_normal_messages_carry_no_system_label(client):
    client.iter_messages.return_value = [make_message()]

    assert "system_event" not in (await messages.list_messages("c1"))["messages"][0]


async def test_replies_are_not_mistaken_for_system_messages(client):
    """type 19(REPLY)는 본문을 갖는 정상 메시지다."""
    m = make_message()
    m.type = 19
    client.iter_messages.return_value = [m]

    brief = (await messages.list_messages("c1"))["messages"][0]
    assert "system_event" not in brief
    assert brief["content"] == "hello"


async def test_system_messages_do_not_trigger_the_intent_warning(client):
    """
    핀·입장 알림만 있는 채널에서 Intent가 켜져 있는데도 꺼졌다고 오진하면,
    사용자를 없는 문제를 고치러 보내게 된다.
    """
    client.iter_messages.return_value = [_system(kind=6), _system(id="2", kind=7)]

    assert "warning" not in await messages.list_messages("c1")


async def test_a_real_blank_message_still_warns(client):
    """시스템 메시지를 걸러내되, 진짜 빈 본문은 여전히 잡아야 한다."""
    client.iter_messages.return_value = [_system(kind=6), make_message(content="")]

    assert "warning" in await messages.list_messages("c1")
