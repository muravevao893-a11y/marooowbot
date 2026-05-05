from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Referral, ReferralActivity, ReferralStatus, User
from app.services.subscription_service import is_subscribed


def is_admin(settings: Settings, telegram_id: int | None) -> bool:
    return bool(telegram_id and telegram_id in settings.admin_ids)


async def set_referrer_if_possible(
    session: AsyncSession,
    settings: Settings,
    referred_user: User,
    referrer_telegram_id: int | None,
) -> bool:
    if not settings.referral_enabled or not referrer_telegram_id:
        return False
    if referred_user.telegram_id == referrer_telegram_id:
        return False
    if is_admin(settings, referred_user.telegram_id) or is_admin(settings, referrer_telegram_id):
        return False

    existing = await session.execute(select(Referral).where(Referral.referred_user_id == referred_user.id))
    if existing.scalar_one_or_none() is not None:
        return False

    referrer_result = await session.execute(select(User).where(User.telegram_id == referrer_telegram_id))
    referrer = referrer_result.scalar_one_or_none()
    if referrer is None or referrer.is_banned or referred_user.is_banned:
        return False

    referral = Referral(referrer_user_id=referrer.id, referred_user_id=referred_user.id)
    session.add(referral)
    await session.flush()
    return True


async def track_referral_activity(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    user: User,
    discussion_root_message_id: int | None,
    comment_message_id: int | None,
) -> None:
    if not settings.referral_enabled or not discussion_root_message_id or not comment_message_id:
        return
    if user.is_banned or is_admin(settings, user.telegram_id):
        return

    referral_result = await session.execute(
        select(Referral).where(
            Referral.referred_user_id == user.id,
            Referral.status == ReferralStatus.PENDING.value,
        )
    )
    referral = referral_result.scalar_one_or_none()
    if referral is None:
        return

    # Anti-abuse: referred user must still be subscribed before activation progress counts.
    if not await is_subscribed(bot, settings, user.telegram_id):
        return

    duplicate = await session.execute(select(ReferralActivity).where(ReferralActivity.comment_message_id == comment_message_id))
    if duplicate.scalar_one_or_none() is not None:
        return

    session.add(ReferralActivity(
        referral_id=referral.id,
        referred_user_id=user.id,
        discussion_root_message_id=discussion_root_message_id,
        comment_message_id=comment_message_id,
    ))
    await session.flush()

    comments_count = (await session.execute(select(func.count(ReferralActivity.id)).where(ReferralActivity.referral_id == referral.id))).scalar_one() or 0
    unique_posts_count = (await session.execute(select(func.count(distinct(ReferralActivity.discussion_root_message_id))).where(ReferralActivity.referral_id == referral.id))).scalar_one() or 0

    referral.comments_count = comments_count
    referral.unique_posts_count = unique_posts_count

    if comments_count >= settings.referral_required_comments and unique_posts_count >= settings.referral_required_posts:
        await session.execute(
            update(Referral)
            .where(Referral.id == referral.id)
            .values(
                status=ReferralStatus.ACTIVE.value,
                bonus_percent=settings.referral_bonus_percent,
                activated_at=datetime.now(timezone.utc),
                comments_count=comments_count,
                unique_posts_count=unique_posts_count,
            )
        )


async def get_referral_stats(session: AsyncSession, settings: Settings, user: User) -> dict[str, float | int]:
    active = (await session.execute(select(func.count(Referral.id)).where(Referral.referrer_user_id == user.id, Referral.status == ReferralStatus.ACTIVE.value))).scalar_one() or 0
    pending = (await session.execute(select(func.count(Referral.id)).where(Referral.referrer_user_id == user.id, Referral.status == ReferralStatus.PENDING.value))).scalar_one() or 0
    raw_bonus = active * settings.referral_bonus_percent
    bonus = min(raw_bonus, settings.referral_bonus_cap_percent)
    return {'active': int(active), 'pending': int(pending), 'bonus_percent': round(float(bonus), 2), 'raw_bonus_percent': round(float(raw_bonus), 2)}


async def get_user_chance_bonus(session: AsyncSession, settings: Settings, user: User) -> float:
    return float((await get_referral_stats(session, settings, user))['bonus_percent'])
