from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.config import get_settings
from app.db.models import DeliveryStatus, EntrySource, Giveaway, GiveawayStatus, GiveawayType
from app.db.session import session_scope
from app.keyboards import auto_drop_kb, claim_gift_kb
from app.services.giveaway_service import (
    add_entry,
    claim_winner_gift,
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

router = Router(name="giveaways")
settings = get_settings()
log = logging.getLogger(__name__)


def _same_chat_id(a: int | str | None, b: int | str | None) -> bool:
    if a is None or b is None:
        return False
    return str(a) == str(b)


def _origin_channel_message_id(message: Message) -> int | None:
    origin = getattr(message, "forward_origin", None)

    if origin:
        message_id = getattr(origin, "message_id", None)
        if message_id:
            return int(message_id)

    old_id = getattr(message, "forward_from_message_id", None)
    if old_id:
        return int(old_id)

    return None


def _is_auto_forwarded_channel_post(message: Message) -> bool:
    if getattr(message, "is_automatic_forward", False):
        return True

    origin = getattr(message, "forward_origin", None)
    if origin:
        origin_chat = getattr(origin, "chat", None)
        origin_chat_id = getattr(origin_chat, "id", None)
        if _same_chat_id(origin_chat_id, settings.channel_id):
            return True

    sender_chat = getattr(message, "sender_chat", None)
    sender_chat_id = getattr(sender_chat, "id", None)
    if _same_chat_id(sender_chat_id, settings.channel_id):
        return True

    return False


def _root_id_from_comment(message: Message) -> int | None:
    if message.reply_to_message:
        return message.reply_to_message.message_id
    return None


async def _create_auto_drop_for_discussion_post(message: Message) -> None:
    if not auto_drops_enabled():
        log.info("Auto drops disabled")
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
            log.info("Auto drop already exists for discussion message_id=%s", message.message_id)
            return

        giveaway = await create_auto_giveaway(
            session,
            settings,
            channel_message_id=_origin_channel_message_id(message),
            discussion_root_message_id=message.message_id,
            discussion_message_thread_id=message.message_thread_id or message.message_id,
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
        await session.flush()

        log.info(
            "Auto drop created: giveaway_id=%s root_message_id=%s thread_id=%s announcement_id=%s",
            giveaway.id,
            message.message_id,
            message.message_thread_id,
            sent.message_id,
        )


@router.channel_post(F.chat.id == settings.channel_id)
async def handle_channel_post(message: Message) -> None:
    log.info(
        "Channel post received: chat_id=%s message_id=%s. Waiting for discussion auto-forward.",
        message.chat.id,
        message.message_id,
    )


@router.message(F.chat.id == settings.discussion_chat_id)
async def handle_discussion_message(message: Message) -> None:
    log.info(
        "Discussion message: chat_id=%s message_id=%s thread_id=%s auto=%s from_user=%s sender_chat=%s reply_to=%s",
        message.chat.id,
        message.message_id,
        message.message_thread_id,
        getattr(message, "is_automatic_forward", None),
        getattr(message.from_user, "id", None) if message.from_user else None,
        getattr(message.sender_chat, "id", None) if getattr(message, "sender_chat", None) else None,
        message.reply_to_message.message_id if message.reply_to_message else None,
    )

    if _is_auto_forwarded_channel_post(message):
        await _create_auto_drop_for_discussion_post(message)
        return

    if message.from_user is None or message.from_user.is_bot:
        return

    root_id = _root_id_from_comment(message)
    thread_id = message.message_thread_id

    async with session_scope() as session:
        giveaway = await find_active_auto_by_comment(session, message.chat.id, root_id, thread_id)

        if giveaway is None:
            log.info(
                "No active auto giveaway found for comment: message_id=%s root_id=%s thread_id=%s",
                message.message_id,
                root_id,
                thread_id,
            )
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

        if not result.ok:
            log.info("Chance attempt rejected: user_id=%s reason=%s", message.from_user.id, result.reason)
            return

        if not result.won or result.winner is None:
            log.info("Chance attempt lost: user_id=%s giveaway_id=%s", message.from_user.id, giveaway.id)
            return

        await message.reply(
            chance_win_reply_text(giveaway.prize_name),
            reply_markup=claim_gift_kb(result.winner.id),
            parse_mode="HTML",
        )

        log.info(
            "Chance winner: user_id=%s giveaway_id=%s winner_id=%s",
            message.from_user.id,
            giveaway.id,
            result.winner.id,
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
            await callback.message.answer(
                chance_claim_sent_text(winner.giveaway.prize_name),
                parse_mode="HTML",
            )
            await callback.answer("Подарок отправлен")
            return

        if winner.delivery_status == DeliveryStatus.MANUAL_REQUIRED.value:
            await callback.message.answer(
                chance_claim_manual_text(winner.giveaway.prize_name),
                parse_mode="HTML",
            )
            await callback.answer("Нужна ручная выдача", show_alert=True)
            return

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