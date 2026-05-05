from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎲 Мой шанс', callback_data='chance')],
        [InlineKeyboardButton(text='👤 Профиль', callback_data='profile'), InlineKeyboardButton(text='🏆 Победители', callback_data='winners')],
        [InlineKeyboardButton(text='🎁 Активные розыгрыши', callback_data='active'), InlineKeyboardButton(text='📜 Правила', callback_data='rules')],
    ])


def profile_kb(bot_username: str, telegram_id: int) -> InlineKeyboardMarkup:
    username = bot_username.lstrip('@')
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔗 Пригласить друга', url=f'https://t.me/{username}?start=ref_{telegram_id}')],
        [InlineKeyboardButton(text='🎲 Мой шанс', callback_data='chance'), InlineKeyboardButton(text='🏆 Топ рефов', callback_data='toprefs')],
        [InlineKeyboardButton(text='📜 Правила', callback_data='rules')],
    ])


def chance_kb(bot_username: str, telegram_id: int) -> InlineKeyboardMarkup:
    username = bot_username.lstrip('@')
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔗 Пригласить друга', url=f'https://t.me/{username}?start=ref_{telegram_id}')],
        [InlineKeyboardButton(text='👤 Профиль', callback_data='profile'), InlineKeyboardButton(text='🏆 Победители', callback_data='winners')],
    ])


def auto_drop_kb(bot_username: str, giveaway_id: int) -> InlineKeyboardMarkup:
    username = bot_username.lstrip('@')
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🤖 Создать профиль', url=f'https://t.me/{username}?start=drop_{giveaway_id}')],
        [InlineKeyboardButton(text='🎲 Проверить шанс', url=f'https://t.me/{username}?start=chance'), InlineKeyboardButton(text='📜 Правила', callback_data='rules')],
    ])


def claim_gift_kb(winner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎁 Забрать подарок', callback_data=f'claim:{winner_id}')]
    ])


def manual_giveaway_kb(giveaway_id: int, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'🎁 Участвовать · {count}', callback_data=f'join:{giveaway_id}')],
        [InlineKeyboardButton(text='🎲 Мой шанс', callback_data='chance'), InlineKeyboardButton(text='📜 Правила', callback_data='rules')],
    ])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎁 Создать розыгрыш', callback_data='admin:create')],
        [InlineKeyboardButton(text='⭐ Баланс', callback_data='admin:balance'), InlineKeyboardButton(text='🎁 Gifts', callback_data='admin:gifts')],
        [InlineKeyboardButton(text='📊 Статистика', callback_data='admin:stats')],
    ])


def admin_preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Опубликовать', callback_data='admin:publish')],
        [InlineKeyboardButton(text='❌ Отменить', callback_data='admin:cancel')],
    ])
