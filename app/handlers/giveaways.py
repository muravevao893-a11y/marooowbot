from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.config import get_settings
from app.db.models import DeliveryStatus, Giveaway, GiveawayStatus, GiveawayType, GiveawayWinner, User
from app.db.session import session_scope
from app.keyboards import auto_drop_kb, claim_gift_kb, manual_giveaway_kb
from app.services.gift_service import send_gift_to_winner
from app.services.giveaway_service import add_manual_entry, create_auto_giveaway, find_active_auto_by_comment, get_giveaway, get_winner, try_comment_chance
from app.services.referral_service import track_referral_activity
from app.services.user_service import get_user_by_tg, get_or_create_user
from app.texts import chance_win_reply_text, claim_manual_text, claim_sent_text, manual_post_text

router = Router(name="giveaways")
settings = get_settings()
log = logging.getLogger(__name__)


def same_id(a, b) -> bool:
    return str(a) == str(b)


def origin_channel_message_id(message: Message) -> int | None:
    origin = getattr(message, "forward_origin", None)
    if origin:
        message_id = getattr(origin, "message_id", None)
        if message_id:
            return int(message_id)
    old_id = getattr(message, "forward_from_message_id", None)
    if old_id:
        return int(old_id)
    return None


def is_auto_forward_from_channel(message: Message) -> bool:
    if getattr(message, "is_automatic_forward", False):
        return True
    origin = getattr(message, "forward_origin", None)
    if origin:
        origin_chat = getattr(origin, "chat", None)
        if same_id(getattr(origin_chat, "id", None), settings.channel_id):
            return True
    if same_id(getattr(getattr(message, "sender_chat", None), "id", None), settings.channel_id):
        return True
    return False


def comment_root_id(message: Message) -> int | None:
    return message.reply_to_message.message_id if message.reply_to_message else None


async def create_auto_drop(message: Message) -> None:
    if not settings.auto_drops_enabled:
        log.info("AUTO_DROP_SKIP disabled")
        return

    async with session_scope() as session:
        existing = await session.scalar(
            select(Giveaway.id).where(
                Giveaway.type == GiveawayType.AUTO,
                Giveaway.status == GiveawayStatus.ACTIVE,
                Giveaway.discussion_chat_id == str(message.chat.id),
                Giveaway.discussion_root_message_id == message.message_id,
            )
        )
        if existing:
            log.info("AUTO_DROP_SKIP already exists root=%s", message.message_id)
            return

        giveaway = await create_auto_giveaway(
            session,
            settings,
            channel_message_id=origin_channel_message_id(message),
            discussion_root_message_id=message.message_id,
            discussion_message_thread_id=message.message_thread_id or message.message_id,
        )

        sent = await message.reply(
            __import__("app.texts", fromlist=["auto_drop_text"]).auto_drop_text(
                giveaway.title,
                giveaway.prize_name,
                giveaway.ends_at,
                giveaway.min_participants,
                giveaway.chance_percent or settings.chance_drop_percent,
            ),
            reply_markup=auto_drop_kb(settings.bot_username, giveaway.id),
        )
        giveaway.announcement_message_id = sent.message_id
        await session.flush()
        log.info("AUTO_DROP_CREATED giveaway_id=%s root=%s announcement=%s", giveaway.id, message.message_id, sent.message_id)


@router.channel_post()
async def any_channel_post(message: Message) -> None:
    log.info("CHANNEL_POST chat_id=%s expected_channel_id=%s message_id=%s text=%r", message.chat.id, settings.channel_id, message.message_id, message.text or message.caption)
    if not same_id(message.chat.id, settings.channel_id):
        log.info("CHANNEL_POST_SKIP wrong channel")
        return
    log.info("CHANNEL_POST_OK waiting discussion forward")


@router.message()
async def any_message(message: Message) -> None:
    log.info(
        "MESSAGE chat_id=%s expected_discussion_id=%s message_id=%s thread_id=%s auto=%s from=%s sender_chat=%s reply_to=%s text=%r",
        message.chat.id,
        settings.discussion_chat_id,
        message.message_id,
        message.message_thread_id,
        getattr(message, "is_automatic_forward", None),
        message.from_user.id if message.from_user else None,
        message.sender_chat.id if message.sender_chat else None,
        message.reply_to_message.message_id if message.reply_to_message else None,
        message.text or message.caption,
    )

    if not same_id(message.chat.id, settings.discussion_chat_id):
        log.info("MESSAGE_SKIP wrong chat")
        return

    if is_auto_forward_from_channel(message):
        log.info("MESSAGE_AUTO_FORWARD detected")
        await create_auto_drop(message)
        return

    if message.from_user is None or message.from_user.is_bot:
        log.info("MESSAGE_SKIP no user or bot")
        return

    if message.from_user.id in settings.admin_ids:
        log.info("MESSAGE_SKIP admin user=%s", message.from_user.id)
        return

    root_id = comment_root_id(message)
    thread_id = message.message_thread_id

    async with session_scope() as session:
        giveaway = await find_active_auto_by_comment(session, message.chat.id, root_id, thread_id)
        if giveaway is None:
            log.info("COMMENT_SKIP no active giveaway root_id=%s thread_id=%s", root_id, thread_id)
            return

        user = await get_user_by_tg(session, message.from_user.id)
        if user is None:
            log.info("CHANCE_SKIP not_registered user=%s", message.from_user.id)
            return

        result = await try_comment_chance(
            session,
            message.bot,
            settings,
            giveaway=giveaway,
            user=user,
            telegram_id=message.from_user.id,
            comment_message_id=message.message_id,
            comment_text=message.text or message.caption,
            discussion_root_message_id=root_id,
        )

        if result.ok:
            await track_referral_activity(session, settings, user, root_id, message.message_id)

        if not result.ok:
            log.info("CHANCE_SKIP user=%s reason=%s", message.from_user.id, result.reason)
            return

        if not result.won or result.winner is None:
            log.info("CHANCE_LOST user=%s giveaway=%s chance=%s", message.from_user.id, giveaway.id, result.chance_percent)
            return

        await message.reply(chance_win_reply_text(giveaway.prize_name), reply_markup=claim_gift_kb(result.winner.id))
        log.info("CHANCE_WIN user=%s giveaway=%s winner=%s", message.from_user.id, giveaway.id, result.winner.id)


@router.callback_query(lambda c: c.data and c.data.startswith("claim:"))
async def claim_chance_gift(callback: CallbackQuery) -> None:
    try:
        winner_id = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Кнопка сломана.", show_alert=True)
        return

    async with session_scope() as session:
        winner = await get_winner(session, winner_id)
        if winner is None:
            await callback.answer("Победа не найдена.", show_alert=True)
            return
        if winner.telegram_id != callback.from_user.id:
            await callback.answer("Это не твой подарок.", show_alert=True)
            return
        if winner.delivery_status == DeliveryStatus.SENT:
            await callback.answer("Подарок уже забран.", show_alert=True)
            return

        await send_gift_to_winner(callback.bot, settings, winner)
        prize = winner.prize_name
        status = winner.delivery_status
        error = winner.delivery_error

        if status == DeliveryStatus.SENT:
            await callback.message.answer(claim_sent_text(prize))
            if settings.proof_channel_enabled and settings.channel_id:
                try:
                    await callback.bot.send_message(settings.channel_id, f"🧸 <b>Мишка улетел победителю.</b>\n\nСледующий шанс — в комментариях под новыми постами.")
                except Exception:
                    pass
            await callback.answer("Подарок отправлен")
        else:
            await callback.message.answer(claim_manual_text(prize, error))
            await callback.answer("Нужна ручная выдача", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("join:"))
async def join_manual_giveaway(callback: CallbackQuery) -> None:
    if callback.from_user.id in settings.admin_ids:
        await callback.answer("Админы не участвуют.", show_alert=True)
        return
    giveaway_id = int(callback.data.split(":", 1)[1])
    async with session_scope() as session:
        giveaway = await get_giveaway(session, giveaway_id)
        if giveaway is None or giveaway.status != GiveawayStatus.ACTIVE:
            await callback.answer("Розыгрыш не найден или завершён.", show_alert=True)
            return
        user = await get_or_create_user(session, callback.from_user)
        result = await add_manual_entry(session, giveaway, user, callback.from_user.id)
        if not result.ok:
            await callback.answer(result.reason, show_alert=True)
            return
        if giveaway.channel_id and giveaway.channel_message_id:
            try:
                await callback.bot.edit_message_reply_markup(chat_id=giveaway.channel_id, message_id=giveaway.channel_message_id, reply_markup=manual_giveaway_kb(giveaway.id, result.count))
            except Exception:
                pass
        await callback.answer("Ты участвуешь.")
