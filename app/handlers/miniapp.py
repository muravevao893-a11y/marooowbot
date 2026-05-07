# app/handlers/miniapp.py
from __future__ import annotations

import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

router = Router(name="miniapp")


DEFAULT_MINI_APP_URL = "https://marooowbot-production.up.railway.app/app?v=13"


def get_mini_app_url() -> str:
    url = (
        os.getenv("MINI_APP_URL")
        or os.getenv("WEBAPP_URL")
        or os.getenv("WEB_APP_URL")
        or DEFAULT_MINI_APP_URL
    )

    url = url.strip().strip('"').strip("'")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    if "/app" not in url:
        url = url.rstrip("/") + "/app?v=13"

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

    await message.answer(
        "🎮 <b>&amp;marooow Mini App</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Открывай приложение именно через кнопку ниже.\n"
        "Так Telegram передаст профиль, аватарку и username.\n\n"
        f"<code>{url}</code>",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML",
    )