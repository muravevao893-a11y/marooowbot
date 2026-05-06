from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.utils.time import utcnow


async def get_user_by_tg(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(session: AsyncSession, tg_user: TgUser) -> User:
    user = await get_user_by_tg(session, tg_user.id)
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_seen_at=utcnow(),
        )
        session.add(user)
        await session.flush()
        return user

    user.username = tg_user.username
    user.first_name = tg_user.first_name
    user.last_seen_at = utcnow()
    await session.flush()
    return user
