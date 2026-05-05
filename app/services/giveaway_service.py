from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass
from datetime import timedelta

from aiogram import Bot
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.services.channel_service import is_user_subscribed
from app.services.referral_service import get_user_chance_bonus
from app.utils.time import utcnow

log = logging.getLogger(__name__)


@dataclass
class ChanceResult:
    ok: bool
    reason: str | None = None
    won: bool = False
    winner: GiveawayWinner | None = None
    chance_percent: float = 0.0


@dataclass
class EntryResult:
    ok: bool
    reason: str = ""
    count: int = 0
    entry_number: int | None = None


def _hash_text(text: str | None) -> str | None:
    normalized = (text or "").strip().lower()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def create_auto_giveaway(session: AsyncSession, settings: Settings, *, channel_message_id: int | None, discussion_root_message_id: int, discussion_message_thread_id: int | None) -> Giveaway:
    now = utcnow()
    giveaway = Giveaway(
        type=GiveawayType.AUTO,
        status=GiveawayStatus.ACTIVE,
        title=settings.auto_drop_title,
        description=None,
        prize_name=settings.auto_drop_prize,
        gift_id=settings.auto_drop_gift_id,
        winners_count=settings.auto_drop_winners,
        min_participants=0,
        require_subscription=settings.require_subscription,
        chance_percent=settings.chance_drop_percent,
        referral_bonus_enabled=True,
        channel_id=str(settings.channel_id),
        channel_message_id=channel_message_id,
        discussion_chat_id=str(settings.discussion_chat_id),
        discussion_root_message_id=discussion_root_message_id,
        discussion_message_thread_id=discussion_message_thread_id,
        starts_at=now,
        ends_at=now + timedelta(seconds=settings.auto_drop_duration_seconds),
        created_by=None,
    )
    session.add(giveaway)
    await session.flush()
    return giveaway


async def find_active_auto_by_comment(session: AsyncSession, chat_id: int | str, root_id: int | None, thread_id: int | None) -> Giveaway | None:
    now = utcnow()
    conditions = [
        Giveaway.type == GiveawayType.AUTO,
        Giveaway.status == GiveawayStatus.ACTIVE,
        Giveaway.discussion_chat_id == str(chat_id),
        Giveaway.ends_at > now,
    ]
    if root_id is not None:
        conditions.append(Giveaway.discussion_root_message_id == root_id)
    elif thread_id is not None:
        conditions.append(Giveaway.discussion_message_thread_id == thread_id)
    else:
        return None

    result = await session.execute(select(Giveaway).where(*conditions).order_by(desc(Giveaway.id)).limit(1))
    return result.scalar_one_or_none()


async def _record_attempt(session: AsyncSession, giveaway: Giveaway, user: User, telegram_id: int, comment_message_id: int, root_id: int | None, text_hash: str | None, won: bool, chance: float, reason: str | None = None) -> ChanceAttempt:
    attempt = ChanceAttempt(
        giveaway_id=giveaway.id,
        user_id=user.id,
        telegram_id=telegram_id,
        comment_message_id=comment_message_id,
        discussion_root_message_id=root_id,
        text_hash=text_hash,
        won=won,
        skipped_reason=reason,
        chance_percent=chance,
    )
    session.add(attempt)
    await session.flush()
    return attempt


async def try_comment_chance(session: AsyncSession, bot: Bot, settings: Settings, *, giveaway: Giveaway, user: User, telegram_id: int, comment_message_id: int, comment_text: str | None, discussion_root_message_id: int | None) -> ChanceResult:
    if telegram_id in settings.admin_ids:
        return ChanceResult(ok=False, reason="admin")
    if user.is_banned:
        return ChanceResult(ok=False, reason="banned")

    if giveaway.require_subscription:
        subscribed = await is_user_subscribed(bot, settings, telegram_id)
        if not subscribed:
            return ChanceResult(ok=False, reason="not_subscribed")

    text_clean = (comment_text or "").strip()
    if len(text_clean) < settings.min_comment_length:
        return ChanceResult(ok=False, reason="too_short")

    exists = await session.scalar(select(ChanceAttempt.id).where(ChanceAttempt.comment_message_id == comment_message_id))
    if exists:
        return ChanceResult(ok=False, reason="duplicate_comment")

    now = utcnow()
    since_cooldown = now - timedelta(seconds=settings.comment_cooldown_seconds)
    recent = await session.scalar(
        select(ChanceAttempt.id).where(
            ChanceAttempt.user_id == user.id,
            ChanceAttempt.created_at >= since_cooldown,
            ChanceAttempt.skipped_reason.is_(None),
        ).limit(1)
    )
    if recent:
        return ChanceResult(ok=False, reason="cooldown")

    since_hour = now - timedelta(hours=1)
    attempts_hour = await session.scalar(
        select(func.count(ChanceAttempt.id)).where(
            ChanceAttempt.user_id == user.id,
            ChanceAttempt.created_at >= since_hour,
            ChanceAttempt.skipped_reason.is_(None),
        )
    ) or 0
    if attempts_hour >= settings.max_chance_attempts_per_hour:
        return ChanceResult(ok=False, reason="hour_limit")

    text_hash = _hash_text(text_clean)
    if text_hash and settings.same_comment_cooldown_minutes > 0:
        since_same = now - timedelta(minutes=settings.same_comment_cooldown_minutes)
        same = await session.scalar(
            select(ChanceAttempt.id).where(
                ChanceAttempt.user_id == user.id,
                ChanceAttempt.text_hash == text_hash,
                ChanceAttempt.created_at >= since_same,
                ChanceAttempt.skipped_reason.is_(None),
            ).limit(1)
        )
        if same:
            return ChanceResult(ok=False, reason="same_comment")

    winners_count = await session.scalar(select(func.count(GiveawayWinner.id)).where(GiveawayWinner.giveaway_id == giveaway.id)) or 0
    if winners_count >= giveaway.winners_count:
        await _record_attempt(session, giveaway, user, telegram_id, comment_message_id, discussion_root_message_id, text_hash, False, 0, "winners_limit")
        return ChanceResult(ok=False, reason="winners_limit")

    base = giveaway.chance_percent if giveaway.chance_percent is not None else settings.chance_drop_percent
    bonus = await get_user_chance_bonus(session, settings, user) if giveaway.referral_bonus_enabled else 0.0
    final_chance = max(0.0, min(100.0, float(base) + float(bonus)))
    won = random.uniform(0, 100) < final_chance

    await _record_attempt(session, giveaway, user, telegram_id, comment_message_id, discussion_root_message_id, text_hash, won, final_chance)
    user.entries_count += 1

    if not won:
        return ChanceResult(ok=True, won=False, chance_percent=final_chance)

    winner = GiveawayWinner(
        giveaway_id=giveaway.id,
        user_id=user.id,
        telegram_id=telegram_id,
        prize_name=giveaway.prize_name,
        gift_id=giveaway.gift_id,
        comment_message_id=comment_message_id,
        delivery_status=DeliveryStatus.PENDING,
    )
    session.add(winner)
    user.wins_count += 1
    await session.flush()
    return ChanceResult(ok=True, won=True, winner=winner, chance_percent=final_chance)


async def get_winner(session: AsyncSession, winner_id: int) -> GiveawayWinner | None:
    return await session.get(GiveawayWinner, winner_id)


async def get_giveaway(session: AsyncSession, giveaway_id: int) -> Giveaway | None:
    return await session.get(Giveaway, giveaway_id)


async def add_manual_entry(session: AsyncSession, giveaway: Giveaway, user: User, telegram_id: int) -> EntryResult:
    if user.is_banned:
        return EntryResult(False, "Ты забанен.")
    existing = await session.scalar(select(GiveawayEntry.id).where(GiveawayEntry.giveaway_id == giveaway.id, GiveawayEntry.user_id == user.id))
    count = await session.scalar(select(func.count(GiveawayEntry.id)).where(GiveawayEntry.giveaway_id == giveaway.id)) or 0
    if existing:
        return EntryResult(False, "Ты уже участвуешь.", int(count))
    entry = GiveawayEntry(giveaway_id=giveaway.id, user_id=user.id, telegram_id=telegram_id, source=EntrySource.BUTTON)
    session.add(entry)
    await session.flush()
    count = int(count) + 1
    return EntryResult(True, count=count, entry_number=count)
