from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.config import get_settings
from app.db.models import Giveaway, GiveawayStatus
from app.db.session import session_scope
from app.keyboards import chance_kb, main_menu_kb, profile_kb
from app.services.referral_service import get_referral_stats, set_referrer_if_possible
from app.services.stats_service import get_chance_details, get_last_winners, get_ref_leaderboard, get_activity_leaderboard
from app.services.user_service import get_or_create_user
from app.texts import (
    active_giveaways_text,
    activity_leaderboard_text,
    chance_text,
    profile_text,
    ref_leaderboard_text,
    rules_text,
    start_text,
    winners_text,
)

router = Router(name='user')
settings = get_settings()


def parse_ref_arg(args: str | None) -> int | None:
    if not args or not args.startswith('ref_'):
        return None
    try:
        return int(args.removeprefix('ref_'))
    except ValueError:
        return None


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    if message.from_user is None:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
        referrer_id = parse_ref_arg(command.args)
        if referrer_id:
            await set_referrer_if_possible(session, settings, user, referrer_id)
        stats = await get_referral_stats(session, settings, user)
        await message.answer(
            start_text(
                user.first_name,
                user.entries_count,
                user.wins_count,
                referral_active=stats['active'],
                referral_pending=stats['pending'],
                referral_bonus=stats['bonus_percent'],
                bot_username=settings.bot_username,
                telegram_id=user.telegram_id,
            ),
            reply_markup=main_menu_kb(),
        )


@router.message(Command('profile'))
async def cmd_profile(message: Message) -> None:
    if message.from_user is None:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
        stats = await get_referral_stats(session, settings, user)
        await message.answer(
            profile_text(
                user.telegram_id,
                user.username,
                user.first_name,
                user.entries_count,
                user.wins_count,
                user.is_banned,
                referral_active=stats['active'],
                referral_pending=stats['pending'],
                referral_bonus=stats['bonus_percent'],
                bot_username=settings.bot_username,
            ),
            reply_markup=profile_kb(settings.bot_username, user.telegram_id),
        )


@router.message(Command('chance'))
async def cmd_chance(message: Message) -> None:
    if message.from_user is None:
        return
    async with session_scope() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
        details = await get_chance_details(session, settings, user)
        await message.answer(chance_text(details, settings.bot_username, user.telegram_id), reply_markup=chance_kb(settings.bot_username, user.telegram_id))


@router.message(Command('winners'))
async def cmd_winners(message: Message) -> None:
    async with session_scope() as session:
        winners = await get_last_winners(session, 10)
    await message.answer(winners_text(winners), reply_markup=main_menu_kb())


@router.message(Command('refs'))
async def cmd_refs(message: Message) -> None:
    async with session_scope() as session:
        rows = await get_ref_leaderboard(session, 10)
    await message.answer(ref_leaderboard_text(rows), reply_markup=main_menu_kb())


@router.message(Command('activity'))
async def cmd_activity(message: Message) -> None:
    async with session_scope() as session:
        rows = await get_activity_leaderboard(session, 10, days=7)
    await message.answer(activity_leaderboard_text(rows, 7), reply_markup=main_menu_kb())


@router.message(Command('rules'))
async def cmd_rules(message: Message) -> None:
    await message.answer(rules_text(), reply_markup=main_menu_kb())


@router.callback_query(F.data == 'profile')
async def cb_profile(callback: CallbackQuery) -> None:
    async with session_scope() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        stats = await get_referral_stats(session, settings, user)
        await callback.message.answer(
            profile_text(
                user.telegram_id,
                user.username,
                user.first_name,
                user.entries_count,
                user.wins_count,
                user.is_banned,
                referral_active=stats['active'],
                referral_pending=stats['pending'],
                referral_bonus=stats['bonus_percent'],
                bot_username=settings.bot_username,
            ),
            reply_markup=profile_kb(settings.bot_username, user.telegram_id),
        )
    await callback.answer()


@router.callback_query(F.data == 'chance')
async def cb_chance(callback: CallbackQuery) -> None:
    async with session_scope() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        details = await get_chance_details(session, settings, user)
        await callback.message.answer(chance_text(details, settings.bot_username, user.telegram_id), reply_markup=chance_kb(settings.bot_username, user.telegram_id))
    await callback.answer()


@router.callback_query(F.data == 'winners')
async def cb_winners(callback: CallbackQuery) -> None:
    async with session_scope() as session:
        winners = await get_last_winners(session, 10)
    await callback.message.answer(winners_text(winners), reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == 'toprefs')
async def cb_toprefs(callback: CallbackQuery) -> None:
    async with session_scope() as session:
        rows = await get_ref_leaderboard(session, 10)
    await callback.message.answer(ref_leaderboard_text(rows), reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == 'rules')
async def cb_rules(callback: CallbackQuery) -> None:
    await callback.message.answer(rules_text(), reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == 'active')
async def cb_active(callback: CallbackQuery) -> None:
    async with session_scope() as session:
        count = (await session.execute(select(func.count(Giveaway.id)).where(Giveaway.status == GiveawayStatus.ACTIVE.value))).scalar_one() or 0
    await callback.message.answer(active_giveaways_text(int(count)), reply_markup=main_menu_kb())
    await callback.answer()
