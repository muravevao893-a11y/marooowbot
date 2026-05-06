from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.config import Settings


async def is_user_subscribed(bot: Bot, settings: Settings, user_id: int) -> bool:
    if not settings.channel_id:
        return True
    try:
        member = await bot.get_chat_member(chat_id=settings.channel_id, user_id=user_id)
    except TelegramAPIError:
        # If Telegram check fails, do not break the drop system.
        return True
    return member.status not in {"left", "kicked"}
