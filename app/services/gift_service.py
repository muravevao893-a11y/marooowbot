from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from app.config import Settings
from app.db.models import DeliveryStatus, GiveawayWinner
from app.utils.time import utcnow
from app.utils.tg_html import h


async def send_gift_to_winner(bot: Bot, settings: Settings, winner: GiveawayWinner) -> None:
    if not winner.gift_id:
        winner.delivery_status = DeliveryStatus.MANUAL_REQUIRED
        winner.delivery_error = "gift_id is empty"
        winner.claimed_at = utcnow()
        return

    if not hasattr(bot, "send_gift"):
        winner.delivery_status = DeliveryStatus.MANUAL_REQUIRED
        winner.delivery_error = "aiogram Bot has no send_gift method; update aiogram"
        winner.claimed_at = utcnow()
        return

    try:
        await bot.send_gift(user_id=winner.telegram_id, gift_id=winner.gift_id, text=settings.gift_text)
    except TelegramForbiddenError as exc:
        winner.delivery_status = DeliveryStatus.FAILED
        winner.delivery_error = f"forbidden: {exc}"
        winner.claimed_at = utcnow()
    except TelegramAPIError as exc:
        winner.delivery_status = DeliveryStatus.MANUAL_REQUIRED
        winner.delivery_error = str(exc)
        winner.claimed_at = utcnow()
    except Exception as exc:
        winner.delivery_status = DeliveryStatus.MANUAL_REQUIRED
        winner.delivery_error = str(exc)
        winner.claimed_at = utcnow()
    else:
        winner.delivery_status = DeliveryStatus.SENT
        winner.delivery_error = None
        winner.claimed_at = utcnow()
        winner.sent_at = utcnow()


async def format_available_gifts(bot: Bot, limit: int = 50) -> str:
    if not hasattr(bot, "get_available_gifts"):
        return "⚠️ Метод get_available_gifts недоступен. Обнови aiogram."
    try:
        gifts = await bot.get_available_gifts()
    except TelegramAPIError as exc:
        return f"⚠️ <b>Не смог загрузить подарки.</b>\n\n<code>{h(exc)}</code>"

    rows = []
    for gift in gifts.gifts[:limit]:
        sticker = getattr(gift, "sticker", None)
        emoji = getattr(sticker, "emoji", None) or "🎁"
        star_count = getattr(gift, "star_count", "?")
        remaining = getattr(gift, "remaining_count", None)
        extra = f" · осталось: <b>{remaining}</b>" if remaining is not None else ""
        rows.append(f"{emoji} <code>{h(gift.id)}</code> — <b>⭐ {h(star_count)}</b>{extra}")

    if not rows:
        return "<b>Доступных подарков нет.</b>"

    return (
        "<b>&amp;marooow gifts</b>\n━━━━━━━━━━━━━━\n\n"
        "Скопируй нужный <code>gift_id</code> и вставь в Railway:\n"
        "<code>AUTO_DROP_GIFT_ID=...</code>\n\n" + "\n".join(rows)
    )
