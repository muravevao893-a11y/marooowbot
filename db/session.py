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


async def create_db_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Fix old Railway database schema from previous bot versions.
        await conn.execute(
            text(
                """
                ALTER TABLE giveaways
                ADD COLUMN IF NOT EXISTS require_subscription BOOLEAN NOT NULL DEFAULT TRUE;
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE giveaways
                ALTER COLUMN require_subscription SET DEFAULT TRUE;
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE giveaways
                SET require_subscription = TRUE
                WHERE require_subscription IS NULL;
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE giveaways
                ADD COLUMN IF NOT EXISTS chance_percent DOUBLE PRECISION DEFAULT 3;
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE giveaways
                ALTER COLUMN chance_percent SET DEFAULT 3;
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE giveaways
                SET chance_percent = 3
                WHERE chance_percent IS NULL;
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE giveaways
                ADD COLUMN IF NOT EXISTS referral_bonus_enabled BOOLEAN NOT NULL DEFAULT TRUE;
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE giveaways
                ALTER COLUMN referral_bonus_enabled SET DEFAULT TRUE;
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE giveaways
                SET referral_bonus_enabled = TRUE
                WHERE referral_bonus_enabled IS NULL;
                """
            )
        )

        # The important fix for your current error.
        await conn.execute(
            text(
                """
                ALTER TABLE giveaways
                ALTER COLUMN created_at SET DEFAULT NOW();
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE giveaways
                SET created_at = NOW()
                WHERE created_at IS NULL;
                """
            )
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