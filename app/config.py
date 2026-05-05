from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(value: str | None, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return default


def _ids(value: str | None) -> set[int]:
    if not value:
        return set()
    result: set[int] = set()
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.add(int(part))
        except ValueError:
            pass
    return result


def _normalize_db_url(url: str) -> str:
    url = (url or "").strip().strip('"').strip("'")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+asyncpg" not in url.split("://", 1)[0]:
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


@dataclass(frozen=True)
class Settings:
    bot_token: str
    bot_username: str
    admin_ids: set[int]

    channel_id: str
    discussion_chat_id: str

    database_url: str
    redis_url: str

    webhook_full_url: str | None
    webhook_path: str
    webapp_host: str
    webapp_port: int

    auto_drops_enabled: bool
    auto_drop_title: str
    auto_drop_prize: str
    auto_drop_gift_id: str | None
    auto_drop_winners: int
    auto_drop_duration_seconds: int
    chance_drop_percent: float
    require_subscription: bool

    referral_enabled: bool
    referral_bonus_percent: float
    referral_bonus_cap_percent: float
    referral_required_comments: int
    referral_required_posts: int

    comment_cooldown_seconds: int
    max_chance_attempts_per_hour: int
    min_comment_length: int
    same_comment_cooldown_minutes: int
    proof_channel_enabled: bool

    gift_text: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    bot_username = os.getenv("BOT_USERNAME", "marooowbot").strip().lstrip("@")
    database_url = _normalize_db_url(os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"))

    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        bot_username=bot_username,
        admin_ids=_ids(os.getenv("ADMIN_IDS")),
        channel_id=os.getenv("CHANNEL_ID", "").strip(),
        discussion_chat_id=os.getenv("DISCUSSION_CHAT_ID", "").strip(),
        database_url=database_url,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0").strip(),
        webhook_full_url=(os.getenv("WEBHOOK_FULL_URL") or "").strip() or None,
        webhook_path=os.getenv("WEBHOOK_PATH", "/webhook").strip(),
        webapp_host=os.getenv("WEBAPP_HOST", "0.0.0.0").strip(),
        webapp_port=_int(os.getenv("PORT") or os.getenv("WEBAPP_PORT"), 8080),
        auto_drops_enabled=_bool(os.getenv("AUTO_DROPS_ENABLED"), True),
        auto_drop_title=os.getenv("AUTO_DROP_TITLE", "Кто хочет мишку?").strip(),
        auto_drop_prize=os.getenv("AUTO_DROP_PRIZE", "мишка").strip(),
        auto_drop_gift_id=(os.getenv("AUTO_DROP_GIFT_ID") or "").strip() or None,
        auto_drop_winners=max(1, _int(os.getenv("AUTO_DROP_WINNERS"), 1)),
        auto_drop_duration_seconds=max(60, _int(os.getenv("AUTO_DROP_DURATION_SECONDS"), 7200)),
        chance_drop_percent=max(0.0, _float(os.getenv("CHANCE_DROP_PERCENT"), 3.0)),
        require_subscription=_bool(os.getenv("REQUIRE_SUBSCRIPTION"), True),
        referral_enabled=_bool(os.getenv("REFERRAL_ENABLED"), True),
        referral_bonus_percent=max(0.0, _float(os.getenv("REFERRAL_BONUS_PERCENT"), 0.1)),
        referral_bonus_cap_percent=max(0.0, _float(os.getenv("REFERRAL_BONUS_CAP_PERCENT"), 3.0)),
        referral_required_comments=max(1, _int(os.getenv("REFERRAL_REQUIRED_COMMENTS"), 5)),
        referral_required_posts=max(1, _int(os.getenv("REFERRAL_REQUIRED_POSTS"), 2)),
        comment_cooldown_seconds=max(0, _int(os.getenv("COMMENT_COOLDOWN_SECONDS"), 30)),
        max_chance_attempts_per_hour=max(1, _int(os.getenv("MAX_CHANCE_ATTEMPTS_PER_HOUR"), 30)),
        min_comment_length=max(0, _int(os.getenv("MIN_COMMENT_LENGTH"), 2)),
        same_comment_cooldown_minutes=max(0, _int(os.getenv("SAME_COMMENT_COOLDOWN_MINUTES"), 60)),
        proof_channel_enabled=_bool(os.getenv("PROOF_CHANNEL_ENABLED"), True),
        gift_text=os.getenv("GIFT_TEXT", "Подарок от &marooow 🎁").strip(),
    )
