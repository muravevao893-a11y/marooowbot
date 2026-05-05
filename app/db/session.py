from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def create_db_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight safety migrations for old Railway databases from earlier builds.
        # PostgreSQL supports ADD COLUMN IF NOT EXISTS; if a column already exists, nothing happens.
        statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS entries_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS wins_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS description TEXT",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS image_file_id VARCHAR(512)",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS discussion_message_thread_id INTEGER",
            "ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS announcement_message_id INTEGER",
            "ALTER TABLE giveaway_winners ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS discussion_root_message_id INTEGER",
            "ALTER TABLE chance_attempts ADD COLUMN IF NOT EXISTS text_hash VARCHAR(64)",
        ]
        for sql in statements:
            try:
                await conn.execute(text(sql))
            except Exception:
                # On non-PostgreSQL/local experiments this may fail; create_all is still enough for fresh DBs.
                pass


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
