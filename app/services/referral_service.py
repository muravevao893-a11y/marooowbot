from __future__ import annotations

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Referral, ReferralActivity, ReferralStatus, User
from app.utils.time import utcnow


def is_admin(settings: Settings, telegram_id: int | None) -> bool:
    return bool(telegram_id and telegram_id in settings.admin_ids)


async def set_referrer_if_possible(session: AsyncSession, settings: Settings, referred_user: User, referrer_telegram_id: int | None) -> bool:
    if not settings.referral_enabled or not referrer_telegram_id:
        return False
    if referred_user.telegram_id == referrer_telegram_id:
        return False
    if is_admin(settings, referred_user.telegram_id) or is_admin(settings, referrer_telegram_id):
        return False

    exists = await session.execute(select(Referral).where(Referral.referred_user_id == referred_user.id))
    if exists.scalar_one_or_none():
        return False

    result = await session.execute(select(User).where(User.telegram_id == referrer_telegram_id))
    referrer = result.scalar_one_or_none()
    if referrer is None or referrer.is_banned or referred_user.is_banned:
        return False

    referral = Referral(referrer_user_id=referrer.id, referred_user_id=referred_user.id)
    session.add(referral)
    await session.flush()
    return True


async def track_referral_activity(session: AsyncSession, settings: Settings, user: User, discussion_root_message_id: int | None, comment_message_id: int | None) -> None:
    if not settings.referral_enabled or not discussion_root_message_id or not comment_message_id:
        return
    if user.is_banned or is_admin(settings, user.telegram_id):
        return

    result = await session.execute(select(Referral).where(Referral.referred_user_id == user.id, Referral.status == ReferralStatus.PENDING))
    referral = result.scalar_one_or_none()
    if referral is None:
        return

    existing = await session.execute(select(ReferralActivity).where(ReferralActivity.comment_message_id == comment_message_id))
    if existing.scalar_one_or_none():
        return

    session.add(ReferralActivity(referral_id=referral.id, referred_user_id=user.id, discussion_root_message_id=discussion_root_message_id, comment_message_id=comment_message_id))
    await session.flush()

    comments = await session.scalar(select(func.count(ReferralActivity.id)).where(ReferralActivity.referral_id == referral.id)) or 0
    posts = await session.scalar(select(func.count(distinct(ReferralActivity.discussion_root_message_id))).where(ReferralActivity.referral_id == referral.id)) or 0

    referral.comments_count = int(comments)
    referral.unique_posts_count = int(posts)

    if comments >= settings.referral_required_comments and posts >= settings.referral_required_posts:
        referral.status = ReferralStatus.ACTIVE
        referral.bonus_percent = settings.referral_bonus_percent
        referral.activated_at = utcnow()


async def get_referral_stats(session: AsyncSession, settings: Settings, user: User) -> dict[str, float | int]:
    active = await session.scalar(select(func.count(Referral.id)).where(Referral.referrer_user_id == user.id, Referral.status == ReferralStatus.ACTIVE)) or 0
    pending = await session.scalar(select(func.count(Referral.id)).where(Referral.referrer_user_id == user.id, Referral.status == ReferralStatus.PENDING)) or 0
    raw_bonus = float(active) * settings.referral_bonus_percent
    bonus = min(raw_bonus, settings.referral_bonus_cap_percent)
    return {"active": int(active), "pending": int(pending), "bonus_percent": round(bonus, 3), "raw_bonus_percent": round(raw_bonus, 3)}


async def get_user_chance_bonus(session: AsyncSession, settings: Settings, user: User) -> float:
    stats = await get_referral_stats(session, settings, user)
    return float(stats["bonus_percent"])
