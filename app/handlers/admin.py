from __future__ import annotations

from datetime import timedelta

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Giveaway, GiveawayStatus, GiveawayType
from app.db.session import session_scope
from app.keyboards import admin_kb, manual_giveaway_kb
from app.services.stats_service import get_bot_stats
from app.texts import admin_text, manual_post_text, stats_text
from app.utils.time import utcnow

router = Router(name="admin")
settings = get_settings()


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    await message.answer(admin_text(), reply_markup=admin_kb())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    async with session_scope() as session:
        await message.answer(stats_text(*(await get_bot_stats(session))))


@router.message(Command("drop"))
async def cmd_drop(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    if not command.args:
        await message.answer(
            "<b>Создать ручной розыгрыш</b>\n━━━━━━━━━━━━━━\n\n"
            "Формат:\n<code>/drop 60 1 мишка</code>\n\n"
            "Где 60 — минуты, 1 — количество победителей."
        )
        return
    parts = command.args.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Формат: <code>/drop 60 1 мишка</code>")
        return
    try:
        minutes = max(1, int(parts[0]))
        winners = max(1, int(parts[1]))
    except ValueError:
        await message.answer("Минуты и победители должны быть числами.")
        return
    prize = parts[2].strip()
    now = utcnow()
    ends_at = now + timedelta(minutes=minutes)
    title = f"РОЗЫГРЫШ {winners} {prize.upper()}"
    async with session_scope() as session:
        giveaway = Giveaway(
            type=GiveawayType.MANUAL,
            status=GiveawayStatus.ACTIVE,
            title=title,
            description=None,
            prize_name=prize,
            gift_id=settings.auto_drop_gift_id,
            winners_count=winners,
            min_participants=0,
            require_subscription=settings.require_subscription,
            chance_percent=None,
            referral_bonus_enabled=False,
            channel_id=str(settings.channel_id),
            starts_at=now,
            ends_at=ends_at,
            created_by=message.from_user.id,
        )
        session.add(giveaway)
        await session.flush()
        sent = await message.bot.send_message(
            settings.channel_id,
            manual_post_text(title, prize, winners, ends_at, 0),
            reply_markup=manual_giveaway_kb(giveaway.id, 0),
        )
        giveaway.channel_message_id = sent.message_id
        await session.flush()
    await message.answer("✅ Ручной розыгрыш опубликован.")
