# app/db/session.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _safe_execute(conn, sql: str) -> None:
    await conn.execute(text(sql))


async def create_db_schema() -> None:
    async with engine.begin() as conn:
        # Create missing tables from current models.
        await conn.run_sync(Base.metadata.create_all)

        # ------------------------------------------------------------
        # giveaways fixes
        # ------------------------------------------------------------

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ADD COLUMN IF NOT EXISTS require_subscription BOOLEAN NOT NULL DEFAULT TRUE;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ALTER COLUMN require_subscription SET DEFAULT TRUE;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaways
            SET require_subscription = TRUE
            WHERE require_subscription IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ADD COLUMN IF NOT EXISTS chance_percent DOUBLE PRECISION DEFAULT 3;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ALTER COLUMN chance_percent SET DEFAULT 3;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaways
            SET chance_percent = 3
            WHERE chance_percent IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ADD COLUMN IF NOT EXISTS referral_bonus_enabled BOOLEAN NOT NULL DEFAULT TRUE;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ALTER COLUMN referral_bonus_enabled SET DEFAULT TRUE;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaways
            SET referral_bonus_enabled = TRUE
            WHERE referral_bonus_enabled IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ALTER COLUMN created_at SET DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaways
            SET created_at = NOW()
            WHERE created_at IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ADD COLUMN IF NOT EXISTS announcement_message_id INTEGER;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaways
            ADD COLUMN IF NOT EXISTS image_file_id VARCHAR(255);
            """,
        )

        # ------------------------------------------------------------
        # giveaway_entries fixes
        # ------------------------------------------------------------

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ADD COLUMN IF NOT EXISTS telegram_id BIGINT;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ADD COLUMN IF NOT EXISTS username VARCHAR(255);
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ADD COLUMN IF NOT EXISTS source VARCHAR(64) DEFAULT 'comment';
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ALTER COLUMN source SET DEFAULT 'comment';
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_entries
            SET source = 'comment'
            WHERE source IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ADD COLUMN IF NOT EXISTS is_valid BOOLEAN NOT NULL DEFAULT TRUE;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ALTER COLUMN is_valid SET DEFAULT TRUE;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_entries
            SET is_valid = TRUE
            WHERE is_valid IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_entries
            ALTER COLUMN created_at SET DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_entries
            SET created_at = NOW()
            WHERE created_at IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_entries ge
            SET telegram_id = u.telegram_id
            FROM users u
            WHERE ge.user_id = u.id
              AND ge.telegram_id IS NULL;
            """,
        )

        # ------------------------------------------------------------
        # giveaway_winners fixes
        # ------------------------------------------------------------

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS telegram_id BIGINT;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS username VARCHAR(255);
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS prize_name VARCHAR(255);
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS gift_id VARCHAR(255);
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(64) DEFAULT 'pending';
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ALTER COLUMN delivery_status SET DEFAULT 'pending';
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_winners
            SET delivery_status = 'pending'
            WHERE delivery_status IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS delivery_error TEXT;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ALTER COLUMN created_at SET DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_winners
            SET created_at = NOW()
            WHERE created_at IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE giveaway_winners
            ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_winners gw
            SET telegram_id = u.telegram_id
            FROM users u
            WHERE gw.user_id = u.id
              AND gw.telegram_id IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_winners gw
            SET username = u.username
            FROM users u
            WHERE gw.user_id = u.id
              AND gw.username IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_winners gw
            SET prize_name = g.prize_name
            FROM giveaways g
            WHERE gw.giveaway_id = g.id
              AND gw.prize_name IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE giveaway_winners gw
            SET gift_id = g.gift_id
            FROM giveaways g
            WHERE gw.giveaway_id = g.id
              AND gw.gift_id IS NULL;
            """,
        )

        # ------------------------------------------------------------
        # chance_attempts fixes
        # ------------------------------------------------------------

        await _safe_execute(
            conn,
            """
            ALTER TABLE chance_attempts
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE chance_attempts
            ALTER COLUMN created_at SET DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE chance_attempts
            SET created_at = NOW()
            WHERE created_at IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE chance_attempts
            ADD COLUMN IF NOT EXISTS won BOOLEAN NOT NULL DEFAULT FALSE;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE chance_attempts
            ALTER COLUMN won SET DEFAULT FALSE;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE chance_attempts
            SET won = FALSE
            WHERE won IS NULL;
            """,
        )

        # ------------------------------------------------------------
        # referrals fixes
        # ------------------------------------------------------------

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ADD COLUMN IF NOT EXISTS status VARCHAR(64) DEFAULT 'pending';
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ALTER COLUMN status SET DEFAULT 'pending';
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE referrals
            SET status = 'pending'
            WHERE status IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ADD COLUMN IF NOT EXISTS comments_count INTEGER DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ALTER COLUMN comments_count SET DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE referrals
            SET comments_count = 0
            WHERE comments_count IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ADD COLUMN IF NOT EXISTS unique_posts_count INTEGER DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ALTER COLUMN unique_posts_count SET DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE referrals
            SET unique_posts_count = 0
            WHERE unique_posts_count IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ADD COLUMN IF NOT EXISTS bonus_percent DOUBLE PRECISION DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ALTER COLUMN bonus_percent SET DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE referrals
            SET bonus_percent = 0
            WHERE bonus_percent IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ALTER COLUMN created_at SET DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE referrals
            SET created_at = NOW()
            WHERE created_at IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referrals
            ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ;
            """,
        )

        # ------------------------------------------------------------
        # referral_activity fixes
        # ------------------------------------------------------------

        await _safe_execute(
            conn,
            """
            ALTER TABLE referral_activity
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE referral_activity
            ALTER COLUMN created_at SET DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE referral_activity
            SET created_at = NOW()
            WHERE created_at IS NULL;
            """,
        )

        # ------------------------------------------------------------
        # users fixes
        # ------------------------------------------------------------

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS entries_count INTEGER DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ALTER COLUMN entries_count SET DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE users
            SET entries_count = 0
            WHERE entries_count IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS wins_count INTEGER DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ALTER COLUMN wins_count SET DEFAULT 0;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE users
            SET wins_count = 0
            WHERE wins_count IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT FALSE;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ALTER COLUMN is_banned SET DEFAULT FALSE;
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE users
            SET is_banned = FALSE
            WHERE is_banned IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ALTER COLUMN created_at SET DEFAULT NOW();
            """,
        )

        await _safe_execute(
            conn,
            """
            UPDATE users
            SET created_at = NOW()
            WHERE created_at IS NULL;
            """,
        )

        await _safe_execute(
            conn,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
            """,
        )


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise