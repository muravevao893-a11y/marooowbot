from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.config import get_settings
from app.db.models import DeliveryStatus, Giveaway, GiveawayStatus, GiveawayType
from app.db.session import session_scope
from app.keyboards import auto_drop_kb, claim_gift_kb
from app.services.giveaway_service import (
    add_entry,
    claim_winner_gift,
    count_entries,
    create_auto_giveaway,
    find_active_auto_by_comment,
    get_giveaway,
    get_winner_for_claim,
    try_comment_chance,
    update_manual_markup,
)
from app.services.runtime import auto_drops_enabled
from app.services.user_service import get_user_by_tg
from app.texts import (
    auto_drop_text,
    chance_claim_forbidden_text,
    chance_claim_manual_text,
    chance_claim_sent_text,
    chance_win_reply_text,
    joined_text,
)
from app.db.models import EntrySource

router = Router(name="giveaways")
settings = get_settings()


def _origin_channel_message_id(message: Message) -> int | None:
    origin = getattr(message, "forward_origin", None)
    if origin and getattr(origin, "type", None) == "channel":
        return getattr(origin, "message_id", None)
    return None


def _root_id_from_comment(message: Message) -> int | None:
    if message.reply_to_message:
        return message.reply_to_message.message_id
    return None


@router.message(F.chat.id == settings.discussion_chat_id, F.is_automatic_forward == True)  # noqa: E712
async def auto_forwarded_channel_post(message: Message) -> None:
    if not auto_drops_enabled():
        return
    async with session_scope() as session:
        existing = await session.execute(
            select(Giveaway).where(
                Giveaway.type == GiveawayType.AUTO.value,
                Giveaway.status == GiveawayStatus.ACTIVE.value,
                Giveaway.discussion_chat_id == str(message.chat.id),
                Giveaway.discussion_root_message_id == message.message_id,
            )
        )
        if existing.scalar_one_or_none():
            return
        giveaway = await create_auto_giveaway(
            session,
            settings,
            channel_message_id=_origin_channel_message_id(message),
            discussion_root_message_id=message.message_id,
            discussion_message_thread_id=message.message_thread_id,
        )
        sent = await message.reply(
            auto_drop_text(
                giveaway.title,
                giveaway.prize_name,
                giveaway.ends_at,
                giveaway.min_participants,
                settings.chance_drop_percent,
            ),
            reply_markup=auto_drop_kb(settings.bot_username, giveaway.id),
            parse_mode="HTML",
        )
        giveaway.announcement_message_id = sent.message_id


@router.message(F.chat.id == settings.discussion_chat_id)
async def collect_comment_chance(message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    if getattr(message, "is_automatic_forward", False):
        return

    root_id = _root_id_from_comment(message)
    thread_id = message.message_thread_id

    async with session_scope() as session:
        giveaway = await find_active_auto_by_comment(session, message.chat.id, root_id, thread_id)
        if giveaway is None:
            return
        user = await get_user_by_tg(session, message.from_user.id)
        result = await try_comment_chance(
            session,
            message.bot,
            settings,
            giveaway=giveaway,
            user=user,
            telegram_id=message.from_user.id,
            comment_message_id=message.message_id,
        )
        if not result.ok or not result.won or result.winner is None:
            return
        await message.reply(
            chance_win_reply_text(giveaway.prize_name),
            reply_markup=claim_gift_kb(result.winner.id),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("claim:"))
async def claim_chance_gift(callback: CallbackQuery) -> None:
    try:
        winner_id = int(callback.data.split(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Кнопка сломана.", show_alert=True)
        return

    async with session_scope() as session:
        winner = await get_winner_for_claim(session, winner_id)
        if winner is None or winner.giveaway is None or winner.user is None:
            await callback.answer("Победа не найдена.", show_alert=True)
            return
        if winner.user.telegram_id != callback.from_user.id:
            await callback.answer(chance_claim_forbidden_text(), show_alert=True)
            return
        if winner.delivery_status == DeliveryStatus.SENT.value:
            await callback.answer("Ты уже забрал подарок.", show_alert=True)
            return

        await claim_winner_gift(session, callback.bot, settings, winner)
        if winner.delivery_status == DeliveryStatus.SENT.value:
            await callback.message.answer(chance_claim_sent_text(winner.giveaway.prize_name), parse_mode="HTML")
            await callback.answer("Подарок отправлен")
        elif winner.delivery_status == DeliveryStatus.MANUAL_REQUIRED.value:
            await callback.message.answer(chance_claim_manual_text(winner.giveaway.prize_name), parse_mode="HTML")
            await callback.answer("Нужна ручная выдача", show_alert=True)
        else:
            await callback.answer("Не получилось отправить. Попробуй позже или напиши админу.", show_alert=True)


@router.callback_query(F.data.startswith("join:"))
async def join_manual_giveaway(callback: CallbackQuery) -> None:
    giveaway_id = int(callback.data.split(":", 1)[1])
    async with session_scope() as session:
        giveaway = await get_giveaway(session, giveaway_id)
        if giveaway is None:
            await callback.answer("Розыгрыш не найден.", show_alert=True)
            return
        user = await get_user_by_tg(session, callback.from_user.id)
        result = await add_entry(
            session,
            callback.bot,
            settings,
            giveaway=giveaway,
            user=user,
            telegram_id=callback.from_user.id,
            comment_message_id=None,
            source=EntrySource.BUTTON,
        )
        if not result.ok:
            await callback.answer(result.reason, show_alert=True)
            return
        await update_manual_markup(callback.bot, settings, giveaway, result.count)
        await callback.answer("Ты участвуешь.", show_alert=False)
        try:
            await callback.from_user.send_message(
                joined_text(giveaway.title, result.entry_number or result.count, giveaway.ends_at),
                parse_mode="HTML",
            )
        except Exception:
            pass
