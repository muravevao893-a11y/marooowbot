from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.config import Settings


async def is_subscribed(bot: Bot, settings: Settings, user_id: int) -> bool:
    if not settings.require_subscription:
        return True
    try:
        member = await bot.get_chat_member(settings.channel_id, user_id)
    except TelegramAPIError:
        return False
    return member.status in {'creator', 'administrator', 'member'}
