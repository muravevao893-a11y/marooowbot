from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _safe_execute(conn, sql: str) -> None:
    try:
        await conn.execute(text(sql))
    except Exception:
        # Startup should not die because an old Railway DB lacks/has a column in an unexpected shape.
        # The actual tables are still created by SQLAlchemy above.
        pass


async def create_db_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Safe migrations for old Railway DBs from previous project versions.
        # Important: old DBs may have NOT NULL columns without defaults.
        statements = [
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS require_subscription BOOLEAN NOT NULL DEFAULT TRUE",
            "UPDATE giveaways SET require_subscription = TRUE WHERE require_subscription IS NULL",
            "ALTER TABLE giveaways ALTER COLUMN require_subscription SET DEFAULT TRUE",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS chance_percent DOUBLE PRECISION DEFAULT 3",
            "UPDATE giveaways SET chance_percent = 3 WHERE chance_percent IS NULL",
            "ALTER TABLE giveaways ALTER COLUMN chance_percent SET DEFAULT 3",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS referral_bonus_enabled BOOLEAN NOT NULL DEFAULT TRUE",
            "UPDATE giveaways SET referral_bonus_enabled = TRUE WHERE referral_bonus_enabled IS NULL",
            "ALTER TABLE giveaways ALTER COLUMN referral_bonus_enabled SET DEFAULT TRUE",
            "ALTER TABLE giveaways ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE giveaways SET created_at = NOW() WHERE created_at IS NULL",

            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS entries_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS wins_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE",

            "ALTER TABLE users ADD COLUMN IF NOT EXISTS app_stars INTEGER NOT NULL DEFAULT 0",
            "UPDATE users SET app_stars = 0 WHERE app_stars IS NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS exp INTEGER NOT NULL DEFAULT 0",
            "UPDATE users SET exp = 0 WHERE exp IS NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1",
            "UPDATE users SET level = 1 WHERE level IS NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_daily_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_url TEXT",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS telegram_id BIGINT",
            "UPDATE giveaway_winners gw SET telegram_id = u.telegram_id FROM users u WHERE gw.user_id = u.id AND gw.telegram_id IS NULL",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS username VARCHAR(255)",
            "UPDATE giveaway_winners gw SET username = u.username FROM users u WHERE gw.user_id = u.id AND gw.username IS NULL",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(32) DEFAULT 'pending'",
            "UPDATE giveaway_winners SET delivery_status = 'pending' WHERE delivery_status IS NULL",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS delivery_error TEXT",
            "ALTER TABLE users ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE users SET created_at = NOW() WHERE created_at IS NULL",

            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS discussion_root_message_id INTEGER",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS text_hash VARCHAR(64)",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS skipped_reason VARCHAR(255)",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS chance_percent DOUBLE PRECISION NOT NULL DEFAULT 0",
            "UPDATE chance_attempts SET chance_percent = 0 WHERE chance_percent IS NULL",
            "ALTER TABLE chance_attempts ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE chance_attempts SET created_at = NOW() WHERE created_at IS NULL",

            "ALTER TABLE giveaway_entries ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE giveaway_entries SET created_at = NOW() WHERE created_at IS NULL",

            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS prize_name VARCHAR(255) NOT NULL DEFAULT 'подарок'",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS gift_id VARCHAR(255)",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS comment_message_id INTEGER",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE giveaway_winners ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE giveaway_winners SET created_at = NOW() WHERE created_at IS NULL",

            "ALTER TABLE referrals ADD COLUMN IF NOT EXISTS comments_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE referrals ADD COLUMN IF NOT EXISTS unique_posts_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE referrals ADD COLUMN IF NOT EXISTS bonus_percent DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE referrals ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE referrals ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE referrals SET created_at = NOW() WHERE created_at IS NULL",

            "ALTER TABLE referral_activity ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE referral_activity SET created_at = NOW() WHERE created_at IS NULL",


            "CREATE TABLE IF NOT EXISTS miniapp_transactions (id SERIAL PRIMARY KEY, telegram_id BIGINT NOT NULL, kind VARCHAR(64) NOT NULL, amount INTEGER NOT NULL DEFAULT 0, payload TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",

            "CREATE TABLE IF NOT EXISTS miniapp_deposits (id SERIAL PRIMARY KEY, telegram_id BIGINT NOT NULL, method VARCHAR(32) NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'pending', stars_amount INTEGER NOT NULL DEFAULT 0, ton_amount_nano BIGINT, comment VARCHAR(255), wallet_address TEXT, tx_hash TEXT, raw_payload TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), paid_at TIMESTAMPTZ)",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS method VARCHAR(32) NOT NULL DEFAULT 'ton'",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'pending'",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS stars_amount INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS ton_amount_nano BIGINT",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS comment VARCHAR(255)",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS wallet_address TEXT",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS tx_hash TEXT",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS raw_payload TEXT",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            "ALTER TABLE miniapp_deposits ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ",
            "CREATE INDEX IF NOT EXISTS idx_miniapp_deposits_user_status ON miniapp_deposits(telegram_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_miniapp_deposits_comment ON miniapp_deposits(comment)",
            "ALTER TABLE admin_logs ALTER COLUMN created_at SET DEFAULT NOW()",
            "UPDATE admin_logs SET created_at = NOW() WHERE created_at IS NULL",
        ]
        for sql in statements:
            await _safe_execute(conn, sql)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
