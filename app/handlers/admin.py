from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import get_settings
from app.db.models import ChanceAttempt, Giveaway, GiveawayStatus, GiveawayType, GiveawayWinner, Referral, ReferralStatus, User
from app.db.session import session_scope
from app.keyboards import admin_kb, admin_preview_kb, manual_giveaway_kb
from app.texts import admin_home_text, admin_stats_text, create_preview_text, manual_giveaway_text
from app.utils.time import utcnow

router = Router(name='admin')
settings = get_settings()


class CreateGiveaway(StatesGroup):
    title = State()
    description = State()
    prize = State()
    winners = State()
    duration = State()
    gift_id = State()
    image = State()
    preview = State()


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


@router.message(Command('admin'))
async def admin_home(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer('⛔ <b>Не админ.</b>')
        return
    await message.answer(admin_home_text(), reply_markup=admin_kb())




@router.message(Command('stats'))
async def admin_stats_cmd(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer('⛔ <b>Не админ.</b>')
        return
    async with session_scope() as session:
        users = (await session.execute(select(func.count(User.id)))).scalar_one() or 0
        active = (await session.execute(select(func.count(Giveaway.id)).where(Giveaway.status == GiveawayStatus.ACTIVE.value))).scalar_one() or 0
        winners = (await session.execute(select(func.count(GiveawayWinner.id)))).scalar_one() or 0
        refs = (await session.execute(select(func.count(Referral.id)).where(Referral.status == ReferralStatus.ACTIVE.value))).scalar_one() or 0
        # Approximate last 24h by DB timestamp; enough for admin overview.
        from app.utils.time import utcnow
        from datetime import timedelta as _td
        attempts = (await session.execute(select(func.count(ChanceAttempt.id)).where(ChanceAttempt.created_at >= utcnow() - _td(hours=24)))).scalar_one() or 0
    await message.answer(admin_stats_text(int(users), int(active), int(winners), int(refs), int(attempts)))


@router.callback_query(F.data == 'admin:stats')
async def admin_stats_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer('Не админ', show_alert=True)
        return
    async with session_scope() as session:
        users = (await session.execute(select(func.count(User.id)))).scalar_one() or 0
        active = (await session.execute(select(func.count(Giveaway.id)).where(Giveaway.status == GiveawayStatus.ACTIVE.value))).scalar_one() or 0
        winners = (await session.execute(select(func.count(GiveawayWinner.id)))).scalar_one() or 0
        refs = (await session.execute(select(func.count(Referral.id)).where(Referral.status == ReferralStatus.ACTIVE.value))).scalar_one() or 0
        from app.utils.time import utcnow
        from datetime import timedelta as _td
        attempts = (await session.execute(select(func.count(ChanceAttempt.id)).where(ChanceAttempt.created_at >= utcnow() - _td(hours=24)))).scalar_one() or 0
    await callback.message.answer(admin_stats_text(int(users), int(active), int(winners), int(refs), int(attempts)))
    await callback.answer()


@router.callback_query(F.data == 'admin:create')
async def start_create(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer('Не админ', show_alert=True)
        return
    await state.clear()
    await state.set_state(CreateGiveaway.title)
    await callback.message.answer('<b>Создание розыгрыша</b>\n━━━━━━━━━━━━━━\n\nОтправь название.')
    await callback.answer()


@router.message(CreateGiveaway.title)
async def create_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text or 'Розыгрыш')
    await state.set_state(CreateGiveaway.description)
    await message.answer('Отправь описание. Если не нужно — напиши <code>-</code>.')


@router.message(CreateGiveaway.description)
async def create_description(message: Message, state: FSMContext) -> None:
    text = message.text or '-'
    await state.update_data(description=None if text.strip() == '-' else text)
    await state.set_state(CreateGiveaway.prize)
    await message.answer('Какой приз? Например: <code>мишка</code>.')


@router.message(CreateGiveaway.prize)
async def create_prize(message: Message, state: FSMContext) -> None:
    await state.update_data(prize=message.text or 'мишка')
    await state.set_state(CreateGiveaway.winners)
    await message.answer('Сколько победителей? Например: <code>1</code>.')


@router.message(CreateGiveaway.winners)
async def create_winners(message: Message, state: FSMContext) -> None:
    try:
        winners = max(1, min(100, int((message.text or '1').strip())))
    except ValueError:
        await message.answer('Нужно число. Например: <code>1</code>.')
        return
    await state.update_data(winners=winners)
    await state.set_state(CreateGiveaway.duration)
    await message.answer('Сколько минут длится розыгрыш? Например: <code>60</code>.')


@router.message(CreateGiveaway.duration)
async def create_duration(message: Message, state: FSMContext) -> None:
    try:
        duration = max(1, min(10080, int((message.text or '60').strip())))
    except ValueError:
        await message.answer('Нужно число минут. Например: <code>60</code>.')
        return
    await state.update_data(duration_min=duration)
    await state.set_state(CreateGiveaway.gift_id)
    await message.answer('Вставь <code>gift_id</code> подарка. Если ручная выдача — напиши <code>-</code>. Получить список: /gifts')


@router.message(CreateGiveaway.gift_id)
async def create_gift_id(message: Message, state: FSMContext) -> None:
    text = (message.text or '-').strip()
    await state.update_data(gift_id=None if text == '-' else text)
    await state.set_state(CreateGiveaway.image)
    await message.answer('Отправь картинку для розыгрыша или напиши <code>-</code>, если без картинки.')


@router.message(CreateGiveaway.image)
async def create_image(message: Message, state: FSMContext) -> None:
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.text and message.text.strip() == '-':
        file_id = None
    else:
        await message.answer('Отправь фото или <code>-</code>.')
        return
    await state.update_data(image_file_id=file_id)
    data = await state.get_data()
    await state.set_state(CreateGiveaway.preview)
    await message.answer(
        create_preview_text(
            data['title'], data['prize'], data['winners'], data['duration_min'], data.get('description'), data.get('gift_id')
        ),
        reply_markup=admin_preview_kb(),
    )


@router.callback_query(F.data == 'admin:cancel')
async def create_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer('❌ <b>Отменено.</b>')
    await callback.answer()


@router.callback_query(F.data == 'admin:publish')
async def create_publish(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer('Не админ', show_alert=True)
        return
    data = await state.get_data()
    if not data:
        await callback.answer('Нет данных', show_alert=True)
        return

    ends_at = utcnow() + timedelta(minutes=int(data['duration_min']))
    async with session_scope() as session:
        giveaway = Giveaway(
            type=GiveawayType.MANUAL.value,
            status=GiveawayStatus.ACTIVE.value,
            title=data['title'],
            description=data.get('description'),
            prize_name=data['prize'],
            gift_id=data.get('gift_id'),
            winners_count=int(data['winners']),
            min_participants=1,
            channel_id=str(settings.channel_id),
            starts_at=utcnow(),
            ends_at=ends_at,
            created_by=callback.from_user.id,
            image_file_id=data.get('image_file_id'),
        )
        session.add(giveaway)
        await session.flush()

        text = manual_giveaway_text(giveaway.title, giveaway.description, giveaway.prize_name, giveaway.winners_count, giveaway.ends_at, 0)
        if giveaway.image_file_id:
            sent = await callback.bot.send_photo(settings.channel_id, photo=giveaway.image_file_id, caption=text, reply_markup=manual_giveaway_kb(giveaway.id, 0))
        else:
            sent = await callback.bot.send_message(settings.channel_id, text, reply_markup=manual_giveaway_kb(giveaway.id, 0))
        giveaway.channel_message_id = sent.message_id
        await session.flush()

    await state.clear()
    await callback.message.answer('✅ <b>Розыгрыш опубликован.</b>')
    await callback.answer()
