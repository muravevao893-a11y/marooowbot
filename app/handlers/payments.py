from __future__ import annotations

import logging
from uuid import uuid4

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from app.config import get_settings
from app.services.gift_service import format_available_gifts
from app.utils.tg_html import h

router = Router(name='payments')
settings = get_settings()
log = logging.getLogger(__name__)


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


async def deny(message: Message) -> None:
    await message.answer('⛔ <b>Не админ.</b>')


def format_stars_balance(balance) -> str:
    amount = getattr(balance, 'amount', 0)
    nano = getattr(balance, 'nanostar_amount', 0) or 0
    if nano:
        return f'{amount}.{str(nano).rjust(9, "0")}'
    return str(amount)


@router.message(Command('balance'))
async def cmd_balance(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    try:
        balance = await message.bot.get_my_star_balance()
        text = format_stars_balance(balance)
    except TelegramAPIError as exc:
        await message.answer('⚠️ <b>Не смог получить баланс Stars.</b>\n\n' f'<code>{h(exc)}</code>')
        return
    await message.answer(
        '<b>&amp;marooow balance</b>\n━━━━━━━━━━━━━━\n\n'
        f'Баланс бота: <b>⭐ {h(text)}</b>\n\n'
        'Пополнить:\n<code>/topup 100</code>'
    )


@router.message(Command('gifts'))
async def cmd_gifts(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    await message.answer(await format_available_gifts(message.bot))


@router.message(Command('topup'))
async def cmd_topup(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await deny(message)
        return
    if not command.args:
        await message.answer('<b>Пополнение Stars</b>\n━━━━━━━━━━━━━━\n\nФормат:\n<code>/topup 100</code>')
        return
    try:
        amount = int(command.args.strip().replace(' ', ''))
    except ValueError:
        await message.answer('Нужно число. Например: <code>/topup 100</code>')
        return
    if amount < 1 or amount > 10000:
        await message.answer('Сумма должна быть от <b>1</b> до <b>10000</b> Stars.')
        return

    payload = f'topup:{message.from_user.id}:{amount}:{uuid4().hex[:12]}'
    try:
        await message.bot.send_invoice(
            chat_id=message.chat.id,
            title='Пополнение marooow bot',
            description=f'Пополнение баланса бота на {amount} Telegram Stars',
            payload=payload,
            provider_token='',
            currency='XTR',
            prices=[LabeledPrice(label=f'{amount} Telegram Stars', amount=amount)],
        )
    except TelegramAPIError as exc:
        await message.answer('⚠️ <b>Не смог создать счёт.</b>\n\n' f'<code>{h(exc)}</code>')
        return


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery) -> None:
    if not (query.invoice_payload or '').startswith('topup:'):
        await query.answer(ok=False, error_message='Неверный платёж.')
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    payment = message.successful_payment
    if payment is None:
        return
    log.info('SUCCESSFUL_PAYMENT user=%s amount=%s currency=%s payload=%s', message.from_user.id if message.from_user else None, payment.total_amount, payment.currency, payment.invoice_payload)
    balance_text = 'не удалось получить'
    try:
        balance_text = f'⭐ {format_stars_balance(await message.bot.get_my_star_balance())}'
    except TelegramAPIError:
        pass
    await message.answer(
        '<b>✅ Пополнение прошло.</b>\n━━━━━━━━━━━━━━\n\n'
        f'Зачислено: <b>⭐ {payment.total_amount}</b>\n'
        f'Баланс бота: <b>{balance_text}</b>'
    )


@router.callback_query(F.data == 'admin:balance')
async def cb_admin_balance(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer('Не админ', show_alert=True)
        return
    try:
        balance = await callback.bot.get_my_star_balance()
        await callback.message.answer(f'<b>Баланс:</b> ⭐ {format_stars_balance(balance)}')
    except TelegramAPIError as exc:
        await callback.message.answer(f'Ошибка: <code>{h(exc)}</code>')
    await callback.answer()


@router.callback_query(F.data == 'admin:gifts')
async def cb_admin_gifts(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer('Не админ', show_alert=True)
        return
    await callback.message.answer(await format_available_gifts(callback.bot))
    await callback.answer()
