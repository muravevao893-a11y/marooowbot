from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import get_settings


def main_menu_kb() -> InlineKeyboardMarkup:
    settings = get_settings()
    rows = []
    if settings.mini_app_url:
        rows.append([InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=WebAppInfo(url=settings.mini_app_url))])
    rows.append([InlineKeyboardButton(text="🎁 Активные дропы", callback_data="active")])
    rows.extend([
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
                InlineKeyboardButton(text="🎲 Мой шанс", callback_data="chance"),
            ],
            [
                InlineKeyboardButton(text="🏆 Победители", callback_data="winners"),
                InlineKeyboardButton(text="📜 Правила", callback_data="rules"),
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_kb(bot_username: str, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Пригласить друга", url=f"https://t.me/{bot_username.lstrip('@')}?start=ref_{telegram_id}")],
            [InlineKeyboardButton(text="🎲 Мой шанс", callback_data="chance"), InlineKeyboardButton(text="🏠 Меню", callback_data="home")],
        ]
    )


def auto_drop_kb(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    username = bot_username.lstrip("@")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Создать профиль", url=f"https://t.me/{username}?start=drop_{giveaway_id}")],
            [InlineKeyboardButton(text="🎲 Мой шанс", url=f"https://t.me/{username}?start=chance")],
        ]
    )


def claim_gift_kb(winner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎁 Забрать мишку", callback_data=f"claim:{winner_id}")]]
    )


def manual_giveaway_kb(giveaway_id: int, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"🎁 Участвовать · {count}", callback_data=f"join:{giveaway_id}")]]
    )


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🎁 Дроп командой /drop", callback_data="admin_drop_help")],
            [InlineKeyboardButton(text="📦 Gifts /gifts", callback_data="admin_gifts_help")],
        ]
    )


def miniapp_kb() -> InlineKeyboardMarkup:
    settings = get_settings()
    if not settings.mini_app_url:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⚠️ MINI_APP_URL не настроен", callback_data="home")]]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🚀 Открыть Mini App",
                web_app=WebAppInfo(url=settings.mini_app_url),
            )
        ]]
    )
