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


async def create_db_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Safe migrations for old Railway DBs from previous project versions.
        statements = [
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS require_subscription BOOLEAN NOT NULL DEFAULT TRUE",
            "UPDATE giveaways SET require_subscription = TRUE WHERE require_subscription IS NULL",
            "ALTER TABLE giveaways ALTER COLUMN require_subscription SET DEFAULT TRUE",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS chance_percent DOUBLE PRECISION",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS referral_bonus_enabled BOOLEAN NOT NULL DEFAULT TRUE",
            "UPDATE giveaways SET referral_bonus_enabled = TRUE WHERE referral_bonus_enabled IS NULL",
            "ALTER TABLE giveaways ALTER COLUMN referral_bonus_enabled SET DEFAULT TRUE",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS discussion_root_message_id INTEGER",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS text_hash VARCHAR(64)",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS skipped_reason VARCHAR(255)",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS chance_percent DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS prize_name VARCHAR(255) NOT NULL DEFAULT 'подарок'",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS gift_id VARCHAR(255)",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS comment_message_id INTEGER",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS entries_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS wins_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITH TIME ZONE",
        ]
        for sql in statements:
            await conn.execute(text(sql))


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
