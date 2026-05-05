from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    bot_token: str = Field(..., alias='BOT_TOKEN')
    bot_username: str = Field('marooowbot', alias='BOT_USERNAME')

    channel_id: int = Field(..., alias='CHANNEL_ID')
    discussion_chat_id: int = Field(..., alias='DISCUSSION_CHAT_ID')
    admin_ids: list[int] = Field(default_factory=list, alias='ADMIN_IDS')

    database_url: str = Field('postgresql+asyncpg://postgres:postgres@localhost:5432/maroow', alias='DATABASE_URL')
    redis_url: str = Field('redis://localhost:6379/0', alias='REDIS_URL')

    # Auto chance drops under every channel post
    auto_drops_enabled: bool = Field(True, alias='AUTO_DROPS_ENABLED')
    auto_drop_title: str = Field('Ежедневный дроп', alias='AUTO_DROP_TITLE')
    auto_drop_prize: str = Field('мишка', alias='AUTO_DROP_PRIZE')
    auto_drop_gift_id: str | None = Field(None, alias='AUTO_DROP_GIFT_ID')
    auto_drop_winners: int = Field(1, alias='AUTO_DROP_WINNERS')
    auto_drop_duration_seconds: int = Field(7 * 24 * 60 * 60, alias='AUTO_DROP_DURATION_SECONDS')
    chance_drop_percent: float = Field(3.0, alias='CHANCE_DROP_PERCENT')
    require_subscription: bool = Field(True, alias='REQUIRE_SUBSCRIPTION')
    gift_text: str = Field('Подарок от &marooow 🧸', alias='GIFT_TEXT')

    # Anti-spam / fairness
    comment_cooldown_seconds: int = Field(30, alias='COMMENT_COOLDOWN_SECONDS')
    max_chance_attempts_per_hour: int = Field(30, alias='MAX_CHANCE_ATTEMPTS_PER_HOUR')
    min_comment_length: int = Field(2, alias='MIN_COMMENT_LENGTH')
    same_comment_cooldown_minutes: int = Field(60, alias='SAME_COMMENT_COOLDOWN_MINUTES')
    proof_channel_enabled: bool = Field(True, alias='PROOF_CHANNEL_ENABLED')

    # Referrals
    referral_enabled: bool = Field(True, alias='REFERRAL_ENABLED')
    referral_bonus_percent: float = Field(0.1, alias='REFERRAL_BONUS_PERCENT')
    referral_bonus_cap_percent: float = Field(3.0, alias='REFERRAL_BONUS_CAP_PERCENT')
    referral_required_comments: int = Field(5, alias='REFERRAL_REQUIRED_COMMENTS')
    referral_required_posts: int = Field(2, alias='REFERRAL_REQUIRED_POSTS')

    # Webhook optional. Empty = polling.
    webhook_full_url: str | None = Field(None, alias='WEBHOOK_FULL_URL')
    webhook_path: str = Field('/webhook', alias='WEBHOOK_PATH')
    webapp_host: str = Field('0.0.0.0', alias='WEBAPP_HOST')
    webapp_port: int = Field(8080, alias='PORT')

    @field_validator('admin_ids', mode='before')
    @classmethod
    def parse_admin_ids(cls, value: Any) -> list[int]:
        if value is None or value == '':
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        if isinstance(value, int):
            return [value]
        return [int(part.strip()) for part in str(value).replace(';', ',').split(',') if part.strip()]

    @field_validator('bot_username', mode='before')
    @classmethod
    def clean_username(cls, value: Any) -> str:
        return str(value or '').strip().lstrip('@')

    @field_validator('database_url', mode='before')
    @classmethod
    def normalize_db_url(cls, value: Any) -> str:
        url = str(value)
        # Railway Postgres often exposes postgresql://; SQLAlchemy async needs postgresql+asyncpg://
        if url.startswith('postgresql://'):
            url = 'postgresql+asyncpg://' + url.removeprefix('postgresql://')
        if url.startswith('postgres://'):
            url = 'postgresql+asyncpg://' + url.removeprefix('postgres://')
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
