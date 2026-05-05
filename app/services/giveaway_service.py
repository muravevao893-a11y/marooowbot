from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass
from datetime import timedelta

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import (
    ChanceAttempt,
    DeliveryStatus,
    EntrySource,
    Giveaway,
    GiveawayEntry,
    GiveawayStatus,
    GiveawayType,
    GiveawayWinner,
    User,
)
from app.services.gift_service import send_gift_to_user
from app.services.referral_service import get_user_chance_bonus, is_admin
from app.services.subscription_service import is_subscribed
from app.utils.time import utcnow

log = logging.getLogger(__name__)


@dataclass
class EntryResult:
    ok: bool
    reason: str = ''
    count: int = 0
    entry_number: int | None = None


@dataclass
class ChanceResult:
    ok: bool
    reason: str = ''
    won: bool = False
    winner: GiveawayWinner | None = None
    final_chance: float = 0.0


def normalize_comment(text: str | None) -> str:
    return ' '.join((text or '').strip().lower().split())


def comment_hash(text: str | None) -> str | None:
    normalized = normalize_comment(text)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


async def create_auto_giveaway(
    session: AsyncSession,
    settings: Settings,
    channel_message_id: int | None,
    discussion_root_message_id: int,
    discussion_message_thread_id: int | None,
) -> Giveaway:
    now = utcnow()
    giveaway = Giveaway(
        type=GiveawayType.AUTO.value,
        status=GiveawayStatus.ACTIVE.value,
        title=settings.auto_drop_title,
        prize_name=settings.auto_drop_prize,
        gift_id=settings.auto_drop_gift_id,
        winners_count=settings.auto_drop_winners,
        min_participants=0,
        channel_id=str(settings.channel_id),
        channel_message_id=channel_message_id,
        discussion_chat_id=str(settings.discussion_chat_id),
        discussion_root_message_id=discussion_root_message_id,
        discussion_message_thread_id=discussion_message_thread_id,
        starts_at=now,
        ends_at=now + timedelta(seconds=settings.auto_drop_duration_seconds),
    )
    session.add(giveaway)
    await session.flush()
    return giveaway


async def find_active_auto_by_comment(
    session: AsyncSession,
    chat_id: int,
    root_id: int | None,
    thread_id: int | None,
) -> Giveaway | None:
    if root_id is None and thread_id is None:
        return None
    conditions = [
        Giveaway.type == GiveawayType.AUTO.value,
        Giveaway.status == GiveawayStatus.ACTIVE.value,
        Giveaway.discussion_chat_id == str(chat_id),
        Giveaway.ends_at > utcnow(),
    ]
    if root_id is not None:
        conditions.append(Giveaway.discussion_root_message_id == root_id)
    elif thread_id is not None:
        conditions.append(Giveaway.discussion_message_thread_id == thread_id)
    result = await session.execute(select(Giveaway).where(*conditions).order_by(Giveaway.id.desc()))
    return result.scalar_one_or_none()


async def count_entries(session: AsyncSession, giveaway_id: int) -> int:
    return (await session.execute(select(func.count(GiveawayEntry.id)).where(GiveawayEntry.giveaway_id == giveaway_id))).scalar_one() or 0


async def count_winners(session: AsyncSession, giveaway_id: int) -> int:
    return (await session.execute(select(func.count(GiveawayWinner.id)).where(GiveawayWinner.giveaway_id == giveaway_id))).scalar_one() or 0


async def add_entry(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    giveaway: Giveaway,
    user: User | None,
    telegram_id: int,
    comment_message_id: int | None,
    source: EntrySource,
) -> EntryResult:
    if user is None:
        return EntryResult(ok=False, reason='Сначала создай профиль через /start.')
    if user.is_banned:
        return EntryResult(ok=False, reason='Ты забанен.')
    if is_admin(settings, user.telegram_id):
        return EntryResult(ok=False, reason='Админы не участвуют в розыгрышах.')
    if not await is_subscribed(bot, settings, user.telegram_id):
        return EntryResult(ok=False, reason='Нужно быть подписанным на канал.')

    existing = await session.execute(select(GiveawayEntry).where(GiveawayEntry.giveaway_id == giveaway.id, GiveawayEntry.user_id == user.id))
    if existing.scalar_one_or_none() is not None:
        return EntryResult(ok=False, reason='Ты уже участвуешь.', count=await count_entries(session, giveaway.id))

    entry = GiveawayEntry(
        giveaway_id=giveaway.id,
        user_id=user.id,
        telegram_id=telegram_id,
        comment_message_id=comment_message_id,
        source=source.value if isinstance(source, EntrySource) else str(source),
    )
    session.add(entry)
    user.entries_count += 1
    await session.flush()
    count = await count_entries(session, giveaway.id)
    return EntryResult(ok=True, count=count, entry_number=count)


async def _check_spam_limits(
    session: AsyncSession,
    settings: Settings,
    user: User,
    text: str | None,
    root_id: int | None,
) -> str | None:
    normalized = normalize_comment(text)
    if len(normalized) < settings.min_comment_length:
        return 'too_short'

    now = utcnow()

    cooldown_since = now - timedelta(seconds=settings.comment_cooldown_seconds)
    recent = await session.execute(
        select(ChanceAttempt.id)
        .where(ChanceAttempt.user_id == user.id, ChanceAttempt.created_at >= cooldown_since)
        .limit(1)
    )
    if recent.scalar_one_or_none() is not None:
        return 'cooldown'

    hour_since = now - timedelta(hours=1)
    hour_count = (await session.execute(
        select(func.count(ChanceAttempt.id)).where(ChanceAttempt.user_id == user.id, ChanceAttempt.created_at >= hour_since)
    )).scalar_one() or 0
    if hour_count >= settings.max_chance_attempts_per_hour:
        return 'hour_limit'

    h = comment_hash(text)
    if h:
        same_since = now - timedelta(minutes=settings.same_comment_cooldown_minutes)
        same = await session.execute(
            select(ChanceAttempt.id)
            .where(
                ChanceAttempt.user_id == user.id,
                ChanceAttempt.text_hash == h,
                ChanceAttempt.created_at >= same_since,
            )
            .limit(1)
        )
        if same.scalar_one_or_none() is not None:
            return 'same_comment'

    return None


async def try_comment_chance(
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    giveaway: Giveaway,
    user: User | None,
    telegram_id: int,
    comment_message_id: int,
    comment_text: str | None = None,
    discussion_root_message_id: int | None = None,
) -> ChanceResult:
    if user is None:
        return ChanceResult(ok=False, reason='not_registered')
    if user.is_banned:
        return ChanceResult(ok=False, reason='banned')
    if is_admin(settings, user.telegram_id):
        return ChanceResult(ok=False, reason='admin')
    if not await is_subscribed(bot, settings, user.telegram_id):
        return ChanceResult(ok=False, reason='not_subscribed')

    duplicate = await session.execute(select(ChanceAttempt).where(ChanceAttempt.comment_message_id == comment_message_id))
    if duplicate.scalar_one_or_none() is not None:
        return ChanceResult(ok=False, reason='duplicate_comment')

    spam_reason = await _check_spam_limits(session, settings, user, comment_text, discussion_root_message_id)
    if spam_reason:
        return ChanceResult(ok=False, reason=spam_reason)

    if await count_winners(session, giveaway.id) >= giveaway.winners_count:
        return ChanceResult(ok=False, reason='winners_limit_reached')

    bonus = await get_user_chance_bonus(session, settings, user)
    final_chance = min(100.0, settings.chance_drop_percent + bonus)
    won = random.random() * 100 < final_chance

    attempt = ChanceAttempt(
        giveaway_id=giveaway.id,
        user_id=user.id,
        comment_message_id=comment_message_id,
        discussion_root_message_id=discussion_root_message_id,
        text_hash=comment_hash(comment_text),
        chance_percent=final_chance,
        won=won,
    )
    session.add(attempt)

    if not won:
        await session.flush()
        return ChanceResult(ok=True, won=False, final_chance=final_chance)

    winner = GiveawayWinner(
        giveaway_id=giveaway.id,
        user_id=user.id,
        gift_id=giveaway.gift_id,
        delivery_status=DeliveryStatus.PENDING.value,
    )
    session.add(winner)
    user.wins_count += 1
    await session.flush()
    return ChanceResult(ok=True, won=True, winner=winner, final_chance=final_chance)


async def get_giveaway(session: AsyncSession, giveaway_id: int) -> Giveaway | None:
    return (await session.execute(select(Giveaway).where(Giveaway.id == giveaway_id))).scalar_one_or_none()


async def get_winner_for_claim(session: AsyncSession, winner_id: int) -> GiveawayWinner | None:
    result = await session.execute(
        select(GiveawayWinner)
        .options(selectinload(GiveawayWinner.giveaway), selectinload(GiveawayWinner.user))
        .where(GiveawayWinner.id == winner_id)
    )
    return result.scalar_one_or_none()


async def claim_winner_gift(session: AsyncSession, bot: Bot, settings: Settings, winner: GiveawayWinner) -> None:
    if winner.delivery_status == DeliveryStatus.SENT.value:
        return
    await send_gift_to_user(bot, settings, winner, winner.user.telegram_id, winner.gift_id)
    if winner.delivery_status == DeliveryStatus.SENT.value:
        winner.claimed_at = utcnow()
    await session.flush()
