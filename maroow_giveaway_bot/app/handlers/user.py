from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import get_settings
from app.db.session import session_scope
from app.keyboards import main_menu_kb, profile_kb
from app.services.referral_service import get_referral_stats, set_referrer_if_possible
from app.services.stats_service import activity_rows, latest_winners_rows, refs_top_rows
from app.services.user_service import get_or_create_user
from app.texts import activity_text, chance_text, profile_text, refs_top_text, rules_text, start_text, winners_text

router = Router(name="user")
settings = get_settings()


def _parse_ref(args: str | None) -> int | None:
    if not args or not args.startswith("ref_"):
        return None
    try:
        return int(args.replace("ref_", "", 1))
    except ValueError:
        return None


async def _send_home(message: Message) -> None:
    async with session_scope() as session:
        user = await get_or_create_user(session, message.from_user)
        referrer_id = None
        stats = await get_referral_stats(session, settings, user)
        await message.answer(
            start_text(
                user.first_name,
                user.entries_count,
                user.wins_count,
                referral_active=int(stats["active"]),
                referral_pending=int(stats["pending"]),
                referral_bonus=float(stats["bonus_percent"]),
                bot_username=settings.bot_username,
                telegram_id=user.telegram_id,
            ),
            reply_markup=main_menu_kb(),
        )


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, message.from_user)
        referrer = _parse_ref(command.args)
        if referrer:
            await set_referrer_if_possible(session, settings, user, referrer)
        stats = await get_referral_stats(session, settings, user)
        await message.answer(
            start_text(
                user.first_name,
                user.entries_count,
                user.wins_count,
                referral_active=int(stats["active"]),
                referral_pending=int(stats["pending"]),
                referral_bonus=float(stats["bonus_percent"]),
                bot_username=settings.bot_username,
                telegram_id=user.telegram_id,
            ),
            reply_markup=main_menu_kb(),
        )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    if not message.from_user:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, message.from_user)
        stats = await get_referral_stats(session, settings, user)
        await message.answer(
            profile_text(
                user.telegram_id,
                user.username,
                user.first_name,
                user.entries_count,
                user.wins_count,
                user.is_banned,
                referral_active=int(stats["active"]),
                referral_pending=int(stats["pending"]),
                referral_bonus=float(stats["bonus_percent"]),
                bot_username=settings.bot_username,
            ),
            reply_markup=profile_kb(settings.bot_username, user.telegram_id),
        )


@router.message(Command("chance"))
async def cmd_chance(message: Message) -> None:
    if not message.from_user:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, message.from_user)
        stats = await get_referral_stats(session, settings, user)
        bonus = float(stats["bonus_percent"])
        await message.answer(
            chance_text(
                settings.chance_drop_percent,
                bonus,
                settings.chance_drop_percent + bonus,
                int(stats["active"]),
                int(stats["pending"]),
                settings.referral_bonus_cap_percent,
                settings.bot_username,
                user.telegram_id,
            ),
            reply_markup=profile_kb(settings.bot_username, user.telegram_id),
        )


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(rules_text(), reply_markup=main_menu_kb())


@router.message(Command("winners"))
async def cmd_winners(message: Message) -> None:
    async with session_scope() as session:
        await message.answer(winners_text(await latest_winners_rows(session)), reply_markup=main_menu_kb())


@router.message(Command("refs"))
async def cmd_refs(message: Message) -> None:
    async with session_scope() as session:
        await message.answer(refs_top_text(await refs_top_rows(session)), reply_markup=main_menu_kb())


@router.message(Command("activity"))
async def cmd_activity(message: Message) -> None:
    async with session_scope() as session:
        await message.answer(activity_text(await activity_rows(session)), reply_markup=main_menu_kb())


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer("<b>&amp;marooow</b>\n━━━━━━━━━━━━━━\n\nМеню ниже.", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.message:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, callback.from_user)
        stats = await get_referral_stats(session, settings, user)
        await callback.message.answer(
            profile_text(
                user.telegram_id,
                user.username,
                user.first_name,
                user.entries_count,
                user.wins_count,
                user.is_banned,
                referral_active=int(stats["active"]),
                referral_pending=int(stats["pending"]),
                referral_bonus=float(stats["bonus_percent"]),
                bot_username=settings.bot_username,
            ),
            reply_markup=profile_kb(settings.bot_username, user.telegram_id),
        )
    await callback.answer()


@router.callback_query(F.data == "chance")
async def cb_chance(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.message:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, callback.from_user)
        stats = await get_referral_stats(session, settings, user)
        bonus = float(stats["bonus_percent"])
        await callback.message.answer(
            chance_text(settings.chance_drop_percent, bonus, settings.chance_drop_percent + bonus, int(stats["active"]), int(stats["pending"]), settings.referral_bonus_cap_percent, settings.bot_username, user.telegram_id),
            reply_markup=profile_kb(settings.bot_username, user.telegram_id),
        )
    await callback.answer()


@router.callback_query(F.data == "rules")
async def cb_rules(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(rules_text(), reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "winners")
async def cb_winners(callback: CallbackQuery) -> None:
    if callback.message:
        async with session_scope() as session:
            await callback.message.answer(winners_text(await latest_winners_rows(session)), reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "active")
async def cb_active(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer("🎁 <b>Активные дропы идут под новыми постами канала.</b>\n\nПереходи в комментарии и пиши сообщения.", reply_markup=main_menu_kb())
    await callback.answer()
