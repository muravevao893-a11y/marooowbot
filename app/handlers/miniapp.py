# app/handlers/miniapp.py
from __future__ import annotations

import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

router = Router(name="miniapp")


def get_mini_app_url() -> str | None:
    url = (
        os.getenv("MINI_APP_URL")
        or os.getenv("WEBAPP_URL")
        or os.getenv("WEB_APP_URL")
        or os.getenv("RAILWAY_PUBLIC_DOMAIN")
    )

    if not url:
        return None

    url = url.strip().strip('"').strip("'")

    if url.startswith("http://") or url.startswith("https://"):
        pass
    elif ".up.railway.app" in url:
        url = f"https://{url}"
    else:
        return None

    if "/app" not in url:
        url = url.rstrip("/") + "/app"

    return url


def miniapp_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Открыть Mini App",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


@router.message(Command("miniapp"))
async def cmd_miniapp(message: Message) -> None:
    url = get_mini_app_url()

    if not url:
        await message.answer(
            "⚠️ <b>MINI_APP_URL не настроен</b>\n\n"
            "Проверь Railway → marooowbot → Variables:\n"
            "<code>MINI_APP_URL=https://marooowbot-production.up.railway.app/app?v=12</code>",
            parse_mode="HTML",
        )
        return

    await message.answer(
        "🎮 <b>&amp;marooow Mini App</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Открывай приложение именно через кнопку ниже.\n"
        "Так Telegram передаст профиль, аватарку и username.\n\n"
        f"<code>{url}</code>",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML",
    )