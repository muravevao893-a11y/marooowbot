from __future__ import annotations

from datetime import timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import ChanceAttempt, Giveaway, GiveawayStatus, GiveawayWinner, Referral, ReferralStatus, User
from app.utils.tg_html import user_link
from app.utils.time import fmt_dt, utcnow


async def get_bot_stats(session: AsyncSession) -> tuple[int, int, int, int]:
    users = await session.scalar(select(func.count(User.id))) or 0
    active_giveaways = await session.scalar(select(func.count(Giveaway.id)).where(Giveaway.status == GiveawayStatus.ACTIVE)) or 0
    wins = await session.scalar(select(func.count(GiveawayWinner.id))) or 0
    since = utcnow() - timedelta(hours=24)
    attempts = await session.scalar(select(func.count(ChanceAttempt.id)).where(ChanceAttempt.created_at >= since)) or 0
    return int(users), int(active_giveaways), int(wins), int(attempts)


async def latest_winners_rows(session: AsyncSession, limit: int = 10) -> list[tuple[str, str, str]]:
    stmt = (
        select(GiveawayWinner, User)
        .join(User, User.id == GiveawayWinner.user_id)
        .order_by(desc(GiveawayWinner.created_at))
        .limit(limit)
    )
    rows = []
    for winner, user in (await session.execute(stmt)).all():
        rows.append((user_link(user.telegram_id, user.first_name, user.username), winner.prize_name, fmt_dt(winner.created_at)))
    return rows


async def refs_top_rows(session: AsyncSession, limit: int = 10) -> list[tuple[str, int]]:
    subq = (
        select(Referral.referrer_user_id, func.count(Referral.id).label("cnt"))
        .where(Referral.status == ReferralStatus.ACTIVE)
        .group_by(Referral.referrer_user_id)
        .subquery()
    )
    stmt = select(User, subq.c.cnt).join(subq, subq.c.referrer_user_id == User.id).order_by(desc(subq.c.cnt)).limit(limit)
    return [(user_link(user.telegram_id, user.first_name, user.username), int(cnt)) for user, cnt in (await session.execute(stmt)).all()]


async def activity_rows(session: AsyncSession, limit: int = 10) -> list[tuple[str, int]]:
    since = utcnow() - timedelta(days=7)
    subq = (
        select(ChanceAttempt.user_id, func.count(ChanceAttempt.id).label("cnt"))
        .where(ChanceAttempt.created_at >= since, ChanceAttempt.skipped_reason.is_(None))
        .group_by(ChanceAttempt.user_id)
        .subquery()
    )
    stmt = select(User, subq.c.cnt).join(subq, subq.c.user_id == User.id).order_by(desc(subq.c.cnt)).limit(limit)
    return [(user_link(user.telegram_id, user.first_name, user.username), int(cnt)) for user, cnt in (await session.execute(stmt)).all()]
