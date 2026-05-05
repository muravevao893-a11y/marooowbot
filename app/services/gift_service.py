from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from app.config import Settings
from app.db.models import DeliveryStatus, GiveawayWinner
from app.utils.tg_html import h


async def send_gift_to_user(bot: Bot, settings: Settings, winner: GiveawayWinner, user_id: int, gift_id: str | None) -> None:
    if not gift_id:
        winner.delivery_status = DeliveryStatus.MANUAL_REQUIRED.value
        winner.delivery_error = 'gift_id is empty; manual delivery required'
        return
    try:
        await bot.send_gift(user_id=user_id, gift_id=gift_id, text=settings.gift_text)
    except TelegramForbiddenError as exc:
        winner.delivery_status = DeliveryStatus.FAILED.value
        winner.delivery_error = f'user blocked bot or forbidden: {exc}'
    except TelegramAPIError as exc:
        winner.delivery_status = DeliveryStatus.FAILED.value
        winner.delivery_error = str(exc)
    else:
        winner.delivery_status = DeliveryStatus.SENT.value
        winner.delivery_error = None


async def format_available_gifts(bot: Bot, limit: int = 50) -> str:
    try:
        gifts = await bot.get_available_gifts()
    except TelegramAPIError as exc:
        return '⚠️ <b>Не смог загрузить gifts.</b>\n\n' f'<code>{h(exc)}</code>'

    rows: list[str] = []
    for gift in gifts.gifts[:limit]:
        sticker = getattr(gift, 'sticker', None)
        emoji = getattr(sticker, 'emoji', None) or '🎁'
        star_count = getattr(gift, 'star_count', '?')
        remaining = getattr(gift, 'remaining_count', None)
        extra = f' · осталось: <b>{remaining}</b>' if remaining is not None else ''
        rows.append(f'{emoji} <code>{h(gift.id)}</code> — <b>⭐ {h(star_count)}</b>{extra}')
    if not rows:
        return '<b>Доступных подарков нет.</b>'
    return (
        '<b>&amp;marooow gifts</b>\n'
        '━━━━━━━━━━━━━━\n\n'
        'Скопируй <code>gift_id</code> нужного подарка и вставь в Railway:\n'
        '<code>AUTO_DROP_GIFT_ID=...</code>\n\n'
        + '\n'.join(rows)
    )
