from __future__ import annotations

from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery
from aiogram.exceptions import TelegramAPIError

from app.config import get_settings
from sqlalchemy import text

from app.db.session import session_scope
from app.services.gift_service import format_available_gifts
from app.utils.tg_html import h

router = Router(name="payments")
settings = get_settings()


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


def format_balance(balance) -> str:
    amount = getattr(balance, "amount", 0)
    nano = getattr(balance, "nanostar_amount", 0) or 0
    return f"{amount}.{str(nano).rjust(9, '0')}" if nano else str(amount)


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    if not hasattr(message.bot, "get_my_star_balance"):
        await message.answer("⚠️ Обнови aiogram: нет get_my_star_balance.")
        return
    try:
        balance = await message.bot.get_my_star_balance()
        await message.answer(f"<b>&amp;marooow balance</b>\n━━━━━━━━━━━━━━\n\nБаланс: <b>⭐ {format_balance(balance)}</b>")
    except TelegramAPIError as exc:
        await message.answer(f"⚠️ Ошибка баланса:\n<code>{h(exc)}</code>")


@router.message(Command("gifts"))
async def cmd_gifts(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    await message.answer(await format_available_gifts(message.bot))


@router.message(Command("topup"))
async def cmd_topup(message: Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    if not command.args:
        await message.answer("Формат: <code>/topup 100</code>")
        return
    try:
        amount = int(command.args.strip())
    except ValueError:
        await message.answer("Нужно число. Например: <code>/topup 100</code>")
        return
    if amount < 1 or amount > 10000:
        await message.answer("Укажи от 1 до 10000 Stars.")
        return
    payload = f"topup:{message.from_user.id}:{amount}:{uuid4().hex[:10]}"
    try:
        await message.bot.send_invoice(
            chat_id=message.chat.id,
            title="Пополнение marooow bot",
            description=f"Пополнение бота на {amount} Telegram Stars",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{amount} Telegram Stars", amount=amount)],
        )
    except TelegramAPIError as exc:
        await message.answer(f"⚠️ Не смог создать счёт:\n<code>{h(exc)}</code>")


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    payload = query.invoice_payload or ""
    if not (payload.startswith("topup:") or payload.startswith("miniapp_topup:")):
        await query.answer(ok=False, error_message="Неверный платёж.")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payment = message.successful_payment
    if not payment:
        return

    payload = payment.invoice_payload or ""
    amount = int(payment.total_amount or 0)

    if payload.startswith("miniapp_topup:"):
        parts = payload.split(":")
        try:
            telegram_id = int(parts[1])
        except Exception:
            telegram_id = message.from_user.id if message.from_user else None

        if telegram_id:
            async with session_scope() as session:
                await session.execute(
                    text("UPDATE users SET app_stars = COALESCE(app_stars, 0) + :amount, last_seen_at = NOW() WHERE telegram_id = :tid"),
                    {"amount": amount, "tid": telegram_id},
                )
                await session.execute(
                    text("INSERT INTO miniapp_transactions (telegram_id, kind, amount, payload) VALUES (:tid, 'topup', :amount, :payload)"),
                    {"tid": telegram_id, "amount": amount, "payload": payload},
                )

        await message.answer(f"✅ <b>Баланс Mini App пополнен.</b>\n\nЗачислено: <b>★ {amount}</b>")
        return

    await message.answer(f"✅ <b>Пополнение прошло.</b>\n\nЗачислено: <b>⭐ {amount}</b>")
