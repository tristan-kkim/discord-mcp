"""
Discord 데이터 모델
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class DiscordUser(BaseModel):
    """Discord 사용자 모델"""
    id: str = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자명")
    discriminator: str = Field(..., description="구분자")
    avatar: Optional[str] = Field(None, description="아바타 해시")
    bot: bool = Field(False, description="봇 여부")
    system: bool = Field(False, description="시스템 사용자 여부")
    mfa_enabled: bool = Field(False, description="MFA 활성화 여부")
    banner: Optional[str] = Field(None, description="배너 해시")
    accent_color: Optional[int] = Field(None, description="강조 색상")
    locale: Optional[str] = Field(None, description="로케일")
    verified: bool = Field(False, description="인증 여부")
    email: Optional[str] = Field(None, description="이메일")
    flags: int = Field(0, description="사용자 플래그")
    premium_type: int = Field(0, description="프리미엄 타입")
    public_flags: int = Field(0, description="공개 플래그")


class DiscordGuild(BaseModel):
    """Discord 길드 모델"""
    id: str = Field(..., description="길드 ID")
    name: str = Field(..., description="길드 이름")
    icon: Optional[str] = Field(None, description="아이콘 해시")
    icon_hash: Optional[str] = Field(None, description="아이콘 해시 (압축)")
    splash: Optional[str] = Field(None, description="스플래시 해시")
    discovery_splash: Optional[str] = Field(None, description="디스커버리 스플래시 해시")
    owner_id: str = Field(..., description="소유자 ID")
    permissions: Optional[str] = Field(None, description="권한")
    region: Optional[str] = Field(None, description="지역")
    afk_channel_id: Optional[str] = Field(None, description="AFK 채널 ID")
    afk_timeout: int = Field(300, description="AFK 타임아웃 (초)")
    widget_enabled: bool = Field(False, description="위젯 활성화 여부")
    widget_channel_id: Optional[str] = Field(None, description="위젯 채널 ID")
    verification_level: int = Field(0, description="인증 레벨")
    default_message_notifications: int = Field(0, description="기본 메시지 알림")
    explicit_content_filter: int = Field(0, description="명시적 콘텐츠 필터")
    roles: List[Dict[str, Any]] = Field(default_factory=list, description="역할 목록")
    emojis: List[Dict[str, Any]] = Field(default_factory=list, description="이모지 목록")
    features: List[str] = Field(default_factory=list, description="기능 목록")
    mfa_level: int = Field(0, description="MFA 레벨")
    application_id: Optional[str] = Field(None, description="애플리케이션 ID")
    system_channel_id: Optional[str] = Field(None, description="시스템 채널 ID")
    system_channel_flags: int = Field(0, description="시스템 채널 플래그")
    rules_channel_id: Optional[str] = Field(None, description="규칙 채널 ID")
    max_presences: Optional[int] = Field(None, description="최대 프레즌스")
    max_members: Optional[int] = Field(None, description="최대 멤버 수")
    vanity_url_code: Optional[str] = Field(None, description="바니티 URL 코드")
    description: Optional[str] = Field(None, description="설명")
    banner: Optional[str] = Field(None, description="배너 해시")
    premium_tier: int = Field(0, description="프리미엄 티어")
    premium_subscription_count: int = Field(0, description="프리미엄 구독 수")
    preferred_locale: str = Field("en-US", description="선호 로케일")
    public_updates_channel_id: Optional[str] = Field(None, description="공개 업데이트 채널 ID")
    max_video_channel_users: Optional[int] = Field(None, description="최대 비디오 채널 사용자")
    approximate_member_count: Optional[int] = Field(None, description="대략적인 멤버 수")
    approximate_presence_count: Optional[int] = Field(None, description="대략적인 프레즌스 수")
    welcome_screen: Optional[Dict[str, Any]] = Field(None, description="환영 화면")
    nsfw_level: int = Field(0, description="NSFW 레벨")
    stickers: List[Dict[str, Any]] = Field(default_factory=list, description="스티커 목록")
    premium_progress_bar_enabled: bool = Field(False, description="프리미엄 진행률 바 활성화")


class DiscordChannel(BaseModel):
    """Discord 채널 모델"""
    id: str = Field(..., description="채널 ID")
    type: int = Field(..., description="채널 타입")
    guild_id: Optional[str] = Field(None, description="길드 ID")
    position: Optional[int] = Field(None, description="위치")
    permission_overwrites: List[Dict[str, Any]] = Field(default_factory=list, description="권한 덮어쓰기")
    name: Optional[str] = Field(None, description="채널 이름")
    topic: Optional[str] = Field(None, description="주제")
    nsfw: bool = Field(False, description="NSFW 여부")
    last_message_id: Optional[str] = Field(None, description="마지막 메시지 ID")
    bitrate: Optional[int] = Field(None, description="비트레이트")
    user_limit: Optional[int] = Field(None, description="사용자 제한")
    rate_limit_per_user: Optional[int] = Field(None, description="사용자당 속도 제한")
    recipients: List[DiscordUser] = Field(default_factory=list, description="수신자 목록")
    icon: Optional[str] = Field(None, description="아이콘 해시")
    owner_id: Optional[str] = Field(None, description="소유자 ID")
    application_id: Optional[str] = Field(None, description="애플리케이션 ID")
    parent_id: Optional[str] = Field(None, description="부모 채널 ID")
    last_pin_timestamp: Optional[str] = Field(None, description="마지막 핀 타임스탬프")
    rtc_region: Optional[str] = Field(None, description="RTC 지역")
    video_quality_mode: Optional[int] = Field(None, description="비디오 품질 모드")
    message_count: Optional[int] = Field(None, description="메시지 수")
    member_count: Optional[int] = Field(None, description="멤버 수")
    thread_metadata: Optional[Dict[str, Any]] = Field(None, description="스레드 메타데이터")
    member: Optional[Dict[str, Any]] = Field(None, description="멤버 정보")
    default_auto_archive_duration: Optional[int] = Field(None, description="기본 자동 아카이브 지속 시간")
    permissions: Optional[str] = Field(None, description="권한")
    flags: int = Field(0, description="채널 플래그")
    total_message_sent: Optional[int] = Field(None, description="전송된 총 메시지 수")
    available_tags: List[Dict[str, Any]] = Field(default_factory=list, description="사용 가능한 태그")
    applied_tags: List[str] = Field(default_factory=list, description="적용된 태그")
    default_reaction_emoji: Optional[Dict[str, Any]] = Field(None, description="기본 리액션 이모지")
    default_thread_rate_limit_per_user: Optional[int] = Field(None, description="기본 스레드 사용자당 속도 제한")
    default_sort_order: Optional[int] = Field(None, description="기본 정렬 순서")


class DiscordEmbed(BaseModel):
    """Discord 임베드 모델"""
    title: Optional[str] = Field(None, description="제목")
    type: str = Field("rich", description="임베드 타입")
    description: Optional[str] = Field(None, description="설명")
    url: Optional[str] = Field(None, description="URL")
    timestamp: Optional[str] = Field(None, description="타임스탬프")
    color: Optional[int] = Field(None, description="색상")
    footer: Optional[Dict[str, Any]] = Field(None, description="푸터")
    image: Optional[Dict[str, Any]] = Field(None, description="이미지")
    thumbnail: Optional[Dict[str, Any]] = Field(None, description="썸네일")
    video: Optional[Dict[str, Any]] = Field(None, description="비디오")
    provider: Optional[Dict[str, Any]] = Field(None, description="제공자")
    author: Optional[Dict[str, Any]] = Field(None, description="작성자")
    fields: List[Dict[str, Any]] = Field(default_factory=list, description="필드 목록")


class DiscordAttachment(BaseModel):
    """Discord 첨부파일 모델"""
    id: str = Field(..., description="첨부파일 ID")
    filename: str = Field(..., description="파일명")
    description: Optional[str] = Field(None, description="설명")
    content_type: Optional[str] = Field(None, description="콘텐츠 타입")
    size: int = Field(..., description="파일 크기")
    url: str = Field(..., description="URL")
    proxy_url: str = Field(..., description="프록시 URL")
    height: Optional[int] = Field(None, description="높이")
    width: Optional[int] = Field(None, description="너비")
    ephemeral: bool = Field(False, description="임시 여부")


class DiscordReaction(BaseModel):
    """Discord 리액션 모델"""
    count: int = Field(..., description="개수")
    me: bool = Field(False, description="내가 리액션했는지 여부")
    emoji: Dict[str, Any] = Field(..., description="이모지 정보")


class DiscordMessage(BaseModel):
    """Discord 메시지 모델"""
    id: str = Field(..., description="메시지 ID")
    channel_id: str = Field(..., description="채널 ID")
    author: DiscordUser = Field(..., description="작성자")
    content: str = Field(..., description="메시지 내용")
    timestamp: str = Field(..., description="작성 시간")
    edited_timestamp: Optional[str] = Field(None, description="수정 시간")
    tts: bool = Field(False, description="TTS 여부")
    mention_everyone: bool = Field(False, description="모든 사용자 멘션 여부")
    mentions: List[DiscordUser] = Field(default_factory=list, description="멘션된 사용자 목록")
    mention_roles: List[str] = Field(default_factory=list, description="멘션된 역할 목록")
    mention_channels: List[Dict[str, Any]] = Field(default_factory=list, description="멘션된 채널 목록")
    attachments: List[DiscordAttachment] = Field(default_factory=list, description="첨부파일 목록")
    embeds: List[DiscordEmbed] = Field(default_factory=list, description="임베드 목록")
    reactions: List[DiscordReaction] = Field(default_factory=list, description="리액션 목록")
    nonce: Optional[Union[str, int]] = Field(None, description="논스")
    pinned: bool = Field(False, description="고정 여부")
    webhook_id: Optional[str] = Field(None, description="웹훅 ID")
    type: int = Field(0, description="메시지 타입")
    activity: Optional[Dict[str, Any]] = Field(None, description="활동")
    application: Optional[Dict[str, Any]] = Field(None, description="애플리케이션")
    application_id: Optional[str] = Field(None, description="애플리케이션 ID")
    message_reference: Optional[Dict[str, Any]] = Field(None, description="메시지 참조")
    flags: int = Field(0, description="메시지 플래그")
    referenced_message: Optional[Dict[str, Any]] = Field(None, description="참조된 메시지")
    interaction: Optional[Dict[str, Any]] = Field(None, description="상호작용")
    thread: Optional[Dict[str, Any]] = Field(None, description="스레드")
    components: List[Dict[str, Any]] = Field(default_factory=list, description="컴포넌트 목록")
    sticker_items: List[Dict[str, Any]] = Field(default_factory=list, description="스티커 아이템 목록")
    stickers: List[Dict[str, Any]] = Field(default_factory=list, description="스티커 목록")
    position: Optional[int] = Field(None, description="위치")


class DiscordThread(BaseModel):
    """Discord 스레드 모델"""
    id: str = Field(..., description="스레드 ID")
    name: str = Field(..., description="스레드 이름")
    type: int = Field(..., description="스레드 타입")
    guild_id: str = Field(..., description="길드 ID")
    position: Optional[int] = Field(None, description="위치")
    permission_overwrites: List[Dict[str, Any]] = Field(default_factory=list, description="권한 덮어쓰기")
    rate_limit_per_user: Optional[int] = Field(None, description="사용자당 속도 제한")
    owner_id: Optional[str] = Field(None, description="소유자 ID")
    last_message_id: Optional[str] = Field(None, description="마지막 메시지 ID")
    parent_id: str = Field(..., description="부모 채널 ID")
    last_pin_timestamp: Optional[str] = Field(None, description="마지막 핀 타임스탬프")
    message_count: Optional[int] = Field(None, description="메시지 수")
    member_count: Optional[int] = Field(None, description="멤버 수")
    thread_metadata: Optional[Dict[str, Any]] = Field(None, description="스레드 메타데이터")
    member: Optional[Dict[str, Any]] = Field(None, description="멤버 정보")
    flags: int = Field(0, description="스레드 플래그")


class DiscordRole(BaseModel):
    """Discord 역할 모델"""
    id: str = Field(..., description="역할 ID")
    name: str = Field(..., description="역할 이름")
    color: int = Field(0, description="색상")
    hoist: bool = Field(False, description="표시 여부")
    icon: Optional[str] = Field(None, description="아이콘 해시")
    unicode_emoji: Optional[str] = Field(None, description="유니코드 이모지")
    position: int = Field(..., description="위치")
    permissions: str = Field(..., description="권한")
    managed: bool = Field(False, description="관리 여부")
    mentionable: bool = Field(False, description="멘션 가능 여부")
    tags: Optional[Dict[str, Any]] = Field(None, description="태그")
    flags: int = Field(0, description="역할 플래그")


class DiscordWebhook(BaseModel):
    """Discord 웹훅 모델"""
    id: str = Field(..., description="웹훅 ID")
    type: int = Field(..., description="웹훅 타입")
    guild_id: Optional[str] = Field(None, description="길드 ID")
    channel_id: str = Field(..., description="채널 ID")
    user: Optional[DiscordUser] = Field(None, description="사용자")
    name: Optional[str] = Field(None, description="이름")
    avatar: Optional[str] = Field(None, description="아바타 해시")
    token: Optional[str] = Field(None, description="토큰")
    application_id: Optional[str] = Field(None, description="애플리케이션 ID")
    source_guild: Optional[Dict[str, Any]] = Field(None, description="소스 길드")
    source_channel: Optional[Dict[str, Any]] = Field(None, description="소스 채널")
    url: Optional[str] = Field(None, description="URL")


# 채널 타입 상수
class ChannelType:
    GUILD_TEXT = 0
    DM = 1
    GUILD_VOICE = 2
    GROUP_DM = 3
    GUILD_CATEGORY = 4
    GUILD_ANNOUNCEMENT = 5
    ANNOUNCEMENT_THREAD = 10
    PUBLIC_THREAD = 11
    PRIVATE_THREAD = 12
    GUILD_STAGE_VOICE = 13
    GUILD_DIRECTORY = 14
    GUILD_FORUM = 15


# 메시지 타입 상수
class MessageType:
    DEFAULT = 0
    RECIPIENT_ADD = 1
    RECIPIENT_REMOVE = 2
    CALL = 3
    CHANNEL_NAME_CHANGE = 4
    CHANNEL_ICON_CHANGE = 5
    CHANNEL_PINNED_MESSAGE = 6
    GUILD_MEMBER_JOIN = 7
    USER_PREMIUM_GUILD_SUBSCRIPTION = 8
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_1 = 9
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_2 = 10
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_3 = 11
    CHANNEL_FOLLOW_ADD = 12
    GUILD_DISCOVERY_DISQUALIFIED = 14
    GUILD_DISCOVERY_REQUALIFIED = 15
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = 16
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = 17
    THREAD_CREATED = 18
    REPLY = 19
    CHAT_INPUT_COMMAND = 20
    THREAD_STARTER_MESSAGE = 21
    GUILD_INVITE_REMINDER = 22
    CONTEXT_MENU_COMMAND = 23
    AUTO_MODERATION_ACTION = 24
    ROLE_SUBSCRIPTION_PURCHASE = 25
    INTERACTION_PREMIUM_UPSELL = 26
    STAGE_START = 27
    STAGE_END = 28
    STAGE_SPEAKER = 29
    STAGE_TOPIC = 31
    GUILD_APPLICATION_PREMIUM_UPSELL = 32
