from __future__ import annotations

from datetime import timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import ChanceAttempt, GiveawayWinner, Referral, ReferralStatus, User
from app.services.referral_service import get_referral_stats
from app.utils.time import utcnow


async def get_chance_details(session: AsyncSession, settings: Settings, user: User) -> dict:
    stats = await get_referral_stats(session, settings, user)
    base = float(settings.chance_drop_percent)
    bonus = float(stats['bonus_percent'])
    final = min(100.0, base + bonus)
    return {
        'base': round(base, 2),
        'bonus': round(bonus, 2),
        'final': round(final, 2),
        'active_referrals': stats['active'],
        'pending_referrals': stats['pending'],
        'bonus_cap': round(settings.referral_bonus_cap_percent, 2),
        'required_comments': settings.referral_required_comments,
        'required_posts': settings.referral_required_posts,
    }


async def get_last_winners(session: AsyncSession, limit: int = 10) -> list[GiveawayWinner]:
    result = await session.execute(
        select(GiveawayWinner)
        .options(selectinload(GiveawayWinner.user), selectinload(GiveawayWinner.giveaway))
        .order_by(desc(GiveawayWinner.selected_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_ref_leaderboard(session: AsyncSession, limit: int = 10) -> list[tuple[User, int]]:
    result = await session.execute(
        select(User, func.count(Referral.id).label('active_count'))
        .join(Referral, Referral.referrer_user_id == User.id)
        .where(Referral.status == ReferralStatus.ACTIVE.value)
        .group_by(User.id)
        .order_by(desc('active_count'))
        .limit(limit)
    )
    return [(row[0], int(row[1] or 0)) for row in result.all()]


async def get_activity_leaderboard(session: AsyncSession, limit: int = 10, days: int = 7) -> list[tuple[User, int]]:
    since = utcnow() - timedelta(days=days)
    result = await session.execute(
        select(User, func.count(ChanceAttempt.id).label('attempts_count'))
        .join(ChanceAttempt, ChanceAttempt.user_id == User.id)
        .where(ChanceAttempt.created_at >= since)
        .group_by(User.id)
        .order_by(desc('attempts_count'))
        .limit(limit)
    )
    return [(row[0], int(row[1] or 0)) for row in result.all()]
