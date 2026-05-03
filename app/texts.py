# app/texts.py
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any, Iterable


BRAND = "<b>&amp;marooow</b>"
BOT_NAME = "marooow"


def h(value: Any) -> str:
    return escape(str(value), quote=True)


def mention_user(user: Any) -> str:
    telegram_id = getattr(user, "telegram_id", None) or getattr(user, "id", None)
    username = getattr(user, "username", None)

    if username:
        return f"@{h(username)}"

    first_name = getattr(user, "first_name", None) or "user"
    if telegram_id:
        return f'<a href="tg://user?id={int(telegram_id)}">{h(first_name)}</a>'

    return h(first_name)


def fmt_dt(value: Any) -> str:
    if not value:
        return "—"

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.strftime("%d.%m.%Y · %H:%M")

    return h(value)


def start_text(user: Any | None = None) -> str:
    name = h(getattr(user, "first_name", None) or BOT_NAME)

    return (
        f"{BRAND}\n\n"
        f"<b>{name}, профиль создан.</b>\n\n"
        "Теперь твои комментарии под постами участвуют в дропах, "
        "если ты подписан на канал.\n\n"
        "<b>Профиль</b>\n"
        "• Участий: <b>0</b>\n"
        "• Побед: <b>0</b>"
    )


def profile_text(user: Any) -> str:
    username = getattr(user, "username", None)
    first_name = getattr(user, "first_name", None)
    telegram_id = getattr(user, "telegram_id", None)
    entries_count = getattr(user, "entries_count", 0) or 0
    wins_count = getattr(user, "wins_count", 0) or 0
    is_banned = getattr(user, "is_banned", False)

    status = "забанен" if is_banned else "активен"
    visible_name = username and f"@{h(username)}" or h(first_name or telegram_id or "user")

    return (
        f"{BRAND}\n\n"
        "<b>Твой профиль</b>\n\n"
        f"• Ник: <b>{visible_name}</b>\n"
        f"• ID: <code>{h(telegram_id or '—')}</code>\n"
        f"• Участий: <b>{entries_count}</b>\n"
        f"• Побед: <b>{wins_count}</b>\n"
        f"• Статус: <b>{h(status)}</b>"
    )


def rules_text() -> str:
    return (
        f"{BRAND}\n\n"
        "<b>Правила дропов</b>\n\n"
        "• Чтобы участвовать, нажми <b>/start</b> в боте.\n"
        "• Подпишись на канал.\n"
        "• Пиши комментарии под постами.\n"
        "• Каждый комментарий может дать шанс на подарок.\n"
        "• Если подарок выпал — бот ответит на твой комментарий.\n\n"
        "<b>Важно</b>\n"
        "Накрутка, спам и мультиаккаунты могут привести к бану."
    )


def active_giveaways_text(count: int = 0) -> str:
    if count <= 0:
        return (
            f"{BRAND}\n\n"
            "<b>Активных розыгрышей сейчас нет.</b>\n\n"
            "Но под новыми постами могут появляться дропы."
        )

    return (
        f"{BRAND}\n\n"
        f"<b>Активные розыгрыши:</b> {count}\n\n"
        "Выбирай розыгрыш и жми кнопку участия."
    )


def auto_drop_announcement_text(
    prize: str = "мишка",
    chance_percent: float | int = 3,
    winners_limit: int | None = None,
    **_: Any,
) -> str:
    limit_line = ""
    if winners_limit:
        limit_line = f"\n• Лимит: <b>{winners_limit}</b> победитель(ей) под постом"

    return (
        f"{BRAND} <b>drop</b>\n\n"
        f"Кто хочет <b>{h(prize)}</b>?\n\n"
        f"Пиши комментарий под этим постом — шанс выпадения <b>{h(chance_percent)}%</b>."
        f"{limit_line}\n\n"
        "<b>Условия</b>\n"
        "• быть подписанным на канал\n"
        "• иметь профиль в боте\n\n"
        "Если подарок выпадет, бот ответит прямо на твой комментарий."
    )


def chance_win_reply_text(prize: str = "мишка", **_: Any) -> str:
    return (
        "🎁 <b>Поздравляю.</b>\n\n"
        f"Тебе выпал <b>{h(prize)}</b>.\n"
        "Нажми кнопку ниже, чтобы забрать подарок."
    )


def chance_not_registered_text() -> str:
    return (
        f"{BRAND}\n\n"
        "<b>Профиль не найден.</b>\n\n"
        "Нажми <b>Старт</b> в боте, чтобы твои комментарии участвовали в дропах."
    )


def not_subscribed_text() -> str:
    return (
        f"{BRAND}\n\n"
        "<b>Ты пока не участвуешь.</b>\n\n"
        "Для участия нужно быть подписанным на канал."
    )


def gift_claim_success_text(prize: str = "подарок") -> str:
    return (
        "✅ <b>Готово.</b>\n\n"
        f"<b>{h(prize)}</b> отправлен тебе в Telegram."
    )


def gift_claim_failed_text(reason: str | None = None) -> str:
    extra = f"\n\nПричина: <code>{h(reason)}</code>" if reason else ""

    return (
        "⚠️ <b>Не получилось отправить подарок автоматически.</b>"
        f"{extra}\n\n"
        "Админ проверит выдачу вручную."
    )


def already_claimed_text() -> str:
    return (
        "⚠️ <b>Подарок уже забрали.</b>\n\n"
        "Эта кнопка больше не активна."
    )


def only_winner_can_claim_text() -> str:
    return (
        "⛔ <b>Это не твой подарок.</b>\n\n"
        "Кнопка работает только для победителя."
    )


def giveaway_post_text(
    title: str,
    prize: str,
    winners_count: int = 1,
    ends_at: Any = None,
    conditions: str | None = None,
    entries_count: int = 0,
    **_: Any,
) -> str:
    conditions_block = h(conditions).replace("\n", "\n") if conditions else (
        "• подписка на канал\n"
        "• профиль в боте\n"
        "• участие через кнопку"
    )

    return (
        f"{BRAND}\n\n"
        f"🎁 <b>{h(title)}</b>\n\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Победителей: <b>{h(winners_count)}</b>\n"
        f"Участников: <b>{h(entries_count)}</b>\n"
        f"Финиш: <b>{fmt_dt(ends_at)}</b>\n\n"
        "<b>Условия</b>\n"
        f"{conditions_block}\n\n"
        "Жми кнопку ниже и жди итоги."
    )


def giveaway_joined_text(title: str, entry_number: int | None = None, ends_at: Any = None, **_: Any) -> str:
    number_line = f"\nТвой номер: <b>#{h(entry_number)}</b>" if entry_number else ""

    return (
        "✅ <b>Ты участвуешь.</b>\n\n"
        f"Розыгрыш: <b>{h(title)}</b>"
        f"{number_line}\n"
        f"Итоги: <b>{fmt_dt(ends_at)}</b>"
    )


def giveaway_already_joined_text(title: str | None = None, **_: Any) -> str:
    title_line = f"\n\nРозыгрыш: <b>{h(title)}</b>" if title else ""

    return (
        "⚠️ <b>Ты уже участвуешь.</b>"
        f"{title_line}"
    )


def giveaway_finished_text(
    title: str,
    prize: str,
    entries_count: int,
    winners: Iterable[Any] | None = None,
    **_: Any,
) -> str:
    winners = list(winners or [])

    if winners:
        winners_block = "\n".join(
            f"{idx}. {mention_user(user)}"
            for idx, user in enumerate(winners, start=1)
        )
    else:
        winners_block = "Победителей нет."

    return (
        f"🏁 {BRAND} <b>итоги</b>\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Участников: <b>{h(entries_count)}</b>\n\n"
        "<b>Победители</b>\n"
        f"{winners_block}"
    )


def admin_menu_text() -> str:
    return (
        f"{BRAND} <b>admin</b>\n\n"
        "Выбери действие."
    )


def admin_create_giveaway_text() -> str:
    return (
        "<b>Создание розыгрыша</b>\n\n"
        "Отправь название розыгрыша."
    )


def admin_preview_text(
    title: str,
    prize: str,
    winners_count: int,
    duration: str | int,
    conditions: str | None = None,
    **_: Any,
) -> str:
    conditions = conditions or "стандартные условия"

    return (
        "<b>Предпросмотр розыгрыша</b>\n\n"
        f"Название: <b>{h(title)}</b>\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Победителей: <b>{h(winners_count)}</b>\n"
        f"Длительность: <b>{h(duration)}</b>\n\n"
        "<b>Условия</b>\n"
        f"{h(conditions)}"
    )


def admin_success_text() -> str:
    return "✅ <b>Готово.</b>"


def admin_cancelled_text() -> str:
    return "❌ <b>Отменено.</b>"


def error_text() -> str:
    return (
        "⚠️ <b>Что-то пошло не так.</b>\n\n"
        "Попробуй ещё раз чуть позже."
    )


def banned_text() -> str:
    return (
        "⛔ <b>Ты забанен.</b>\n\n"
        "Участие в розыгрышах недоступно."
    )


def unknown_command_text() -> str:
    return (
        f"{BRAND}\n\n"
        "Не понял команду. Используй кнопки ниже."
    )


def button_active_giveaways() -> str:
    return "🎁 Активные розыгрыши"


def button_profile() -> str:
    return "👤 Профиль"


def button_rules() -> str:
    return "📜 Правила"


def button_join(count: int | None = None) -> str:
    if count is None:
        return "🎁 Участвовать"
    return f"🎁 Участвовать · {count}"


def button_claim_gift(prize: str = "подарок") -> str:
    return f"🎁 Забрать {prize}"


def button_open_bot() -> str:
    return "🤖 Открыть бота"


def button_back() -> str:
    return "← Назад"


# Compatibility aliases for older imports.
START_TEXT = start_text
PROFILE_TEXT = profile_text
RULES_TEXT = rules_text
ACTIVE_GIVEAWAYS_TEXT = active_giveaways_text
AUTO_DROP_ANNOUNCEMENT_TEXT = auto_drop_announcement_text
CHANCE_WIN_REPLY_TEXT = chance_win_reply_text
NOT_SUBSCRIBED_TEXT = not_subscribed_text
GIFT_CLAIM_SUCCESS_TEXT = gift_claim_success_text
GIFT_CLAIM_FAILED_TEXT = gift_claim_failed_text
ALREADY_CLAIMED_TEXT = already_claimed_text
ONLY_WINNER_CAN_CLAIM_TEXT = only_winner_can_claim_text
GIVEAWAY_POST_TEXT = giveaway_post_text
GIVEAWAY_JOINED_TEXT = giveaway_joined_text
GIVEAWAY_ALREADY_JOINED_TEXT = giveaway_already_joined_text
GIVEAWAY_FINISHED_TEXT = giveaway_finished_text
ADMIN_MENU_TEXT = admin_menu_text
ERROR_TEXT = error_text


def __getattr__(name: str):
    if name.endswith("_text") or name.endswith("_TEXT"):
        def fallback(*args: Any, **kwargs: Any) -> str:
            return error_text()
        return fallback

    raise AttributeError(name)