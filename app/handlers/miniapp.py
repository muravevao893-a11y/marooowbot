from __future__ import annotations

import os
import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

router = Router(name="miniapp")

MINI_APP_VERSION = "15"
DEFAULT_MINI_APP_URL = f"https://marooowbot-production.up.railway.app/app?v={MINI_APP_VERSION}"


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
        url = url.rstrip("/") + "/app"

    if re.search(r"([?&])v=\d+", url):
        return re.sub(r"([?&])v=\d+", rf"\1v={MINI_APP_VERSION}", url)

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={MINI_APP_VERSION}"


def miniapp_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Mini App",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


@router.message(Command("miniapp"))
async def cmd_miniapp(message: Message) -> None:
    url = get_mini_app_url()

    await message.answer(
        "<b>&amp;marooow Mini App</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "Открывай приложение через кнопку ниже, чтобы Telegram передал профиль, аватар и username.\n\n"
        f"<code>{url}</code>",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML",
    )
