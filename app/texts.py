from __future__ import annotations

from datetime import datetime

from app.utils.tg_html import h, user_link
from app.utils.time import fmt_dt


BRAND = "&amp;marooow"
LINE = "━━━━━━━━━━━━━━"


def start_text(first_name: str | None = None, entries: int = 0, wins: int = 0, *args, **kwargs) -> str:
    name = h(first_name or "ты")

    return (
        f"<b>{BRAND}</b>\n"
        f"{LINE}\n\n"
        f"<b>{name}, профиль создан.</b>\n\n"
        "Теперь твои комментарии под постами участвуют в дропах.\n"
        "Если выпадет подарок — бот ответит прямо на твой коммент.\n\n"
        "<b>Профиль</b>\n"
        f"• Участий: <b>{entries}</b>\n"
        f"• Побед: <b>{wins}</b>\n\n"
        "<i>Условие: профиль в боте + подписка на канал.</i>"
    )


def profile_text(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    entries: int = 0,
    wins: int = 0,
    banned: bool = False,
    *args,
    **kwargs,
) -> str:
    status = "забанен" if banned else "активен"
    handle = f"@{h(username)}" if username else "—"
    name = h(first_name or "—")

    return (
        f"<b>{BRAND}</b>\n"
        f"{LINE}\n\n"
        "<b>Твой профиль</b>\n\n"
        f"• ID: <code>{telegram_id}</code>\n"
        f"• Ник: <b>{handle}</b>\n"
        f"• Имя: <b>{name}</b>\n"
        f"• Участий: <b>{entries}</b>\n"
        f"• Побед: <b>{wins}</b>\n"
        f"• Статус: <b>{status}</b>"
    )


def rules_text(*args, **kwargs) -> str:
    return (
        f"<b>{BRAND}</b>\n"
        f"{LINE}\n\n"
        "<b>Правила дропов</b>\n\n"
        "• Нажми <b>/start</b>, чтобы создать профиль.\n"
        "• Подпишись на канал.\n"
        "• Пиши комментарии под постами.\n"
        "• Каждый комментарий может выбить подарок.\n"
        "• Если подарок выпал — бот ответит на твой комментарий.\n"
        "• Забрать подарок может только победитель.\n\n"
        "<b>Запрещено</b>\n"
        "• спамить одинаковыми комментами\n"
        "• использовать мультиаккаунты\n"
        "• накручивать активность\n\n"
        "<i>За абуз — бан без выдачи подарка.</i>"
    )


def auto_drop_text(
    title: str,
    prize: str,
    ends_at: datetime,
    min_participants: int = 0,
    chance_percent: float = 3.0,
    *args,
    **kwargs,
) -> str:
    return (
        f"<b>{BRAND} drop</b>\n"
        f"{LINE}\n\n"
        f"🧸 <b>{h(title)}</b>\n\n"
        "Пиши комментарий под этим постом.\n"
        f"Шанс выбить <b>{h(prize)}</b>: <b>{chance_percent:g}%</b> за комментарий.\n\n"
        "<b>Как это работает</b>\n"
        "• написал коммент\n"
        "• бот проверил шанс\n"
        "• если выпало — бот ответит тебе\n"
        "• жмёшь кнопку <b>«Забрать»</b>\n\n"
        "<b>Условия</b>\n"
        "• профиль в боте\n"
        "• подписка на канал\n\n"
        f"Активно до: <b>{fmt_dt(ends_at)}</b>"
    )


def manual_giveaway_text(
    title: str,
    description: str | None,
    prize: str,
    winners: int,
    ends_at: datetime,
    count: int,
    *args,
    **kwargs,
) -> str:
    desc = f"\n{h(description)}\n" if description else ""

    return (
        f"<b>{BRAND}</b>\n"
        f"{LINE}\n\n"
        f"🎁 <b>{h(title)}</b>\n"
        f"{desc}\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Победителей: <b>{winners}</b>\n"
        f"Участников: <b>{count}</b>\n"
        f"Финиш: <b>{fmt_dt(ends_at)}</b>\n\n"
        "<b>Условия</b>\n"
        "• профиль в боте\n"
        "• подписка на канал\n"
        "• участие через кнопку\n\n"
        "<i>Жми кнопку ниже и жди итоги.</i>"
    )


def already_joined_text(title: str, *args, **kwargs) -> str:
    return (
        "⚠️ <b>Ты уже участвуешь.</b>\n\n"
        f"Розыгрыш: <b>{h(title)}</b>"
    )


def joined_text(title: str, number: int, ends_at: datetime, *args, **kwargs) -> str:
    return (
        "✅ <b>Ты в розыгрыше.</b>\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Твой номер: <b>#{number}</b>\n"
        f"Итоги: <b>{fmt_dt(ends_at)}</b>"
    )


def finish_no_winners_text(
    title: str,
    participants: int,
    min_participants: int,
    *args,
    **kwargs,
) -> str:
    return (
        f"🏁 <b>{BRAND} итоги</b>\n"
        f"{LINE}\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Участников: <b>{participants}</b>\n\n"
        f"Победителей нет: нужно минимум <b>{min_participants}</b> участников."
    )


def finish_winners_text(
    title: str,
    prize: str,
    participants: int,
    winner_rows: list[tuple[int, str | None, str | None]],
    *args,
    **kwargs,
) -> str:
    lines = []

    for i, (telegram_id, username, first_name) in enumerate(winner_rows, start=1):
        lines.append(f"{i}. {user_link(telegram_id, first_name, username)}")

    winners = "\n".join(lines) if lines else "—"

    return (
        f"🏁 <b>{BRAND} итоги</b>\n"
        f"{LINE}\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Участников: <b>{participants}</b>\n\n"
        "<b>Победители</b>\n"
        f"{winners}\n\n"
        "<i>Подарки отправляются автоматически или проверяются админом.</i>"
    )


def admin_home_text(*args, **kwargs) -> str:
    return (
        f"<b>{BRAND} admin</b>\n"
        f"{LINE}\n\n"
        "Выбери действие."
    )


def create_preview_text(
    title: str,
    prize: str,
    winners: int,
    duration_min: int,
    description: str | None,
    gift_id: str | None,
    *args,
    **kwargs,
) -> str:
    return (
        "<b>Предпросмотр розыгрыша</b>\n"
        f"{LINE}\n\n"
        f"Название: <b>{h(title)}</b>\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Победителей: <b>{winners}</b>\n"
        f"Время: <b>{duration_min} мин.</b>\n"
        f"Gift ID: <code>{h(gift_id or 'ручная выдача')}</code>\n\n"
        "<b>Описание</b>\n"
        f"{h(description or '—')}"
    )


def chance_win_reply_text(prize: str, *args, **kwargs) -> str:
    return (
        f"🎁 <b>{BRAND}</b>\n"
        f"{LINE}\n\n"
        f"<b>Поздравляю, ты выиграл {h(prize)}.</b>\n\n"
        "Нажми кнопку ниже, чтобы забрать подарок."
    )


def chance_claim_sent_text(prize: str, *args, **kwargs) -> str:
    return (
        "✅ <b>Готово.</b>\n\n"
        f"<b>{h(prize)}</b> отправлен тебе в Telegram."
    )


def chance_claim_manual_text(prize: str, *args, **kwargs) -> str:
    return (
        "⚠️ <b>Победа засчитана.</b>\n\n"
        "Авто-выдача сейчас недоступна.\n"
        f"Админ выдаст <b>{h(prize)}</b> вручную."
    )


def chance_claim_forbidden_text(*args, **kwargs) -> str:
    return "⛔ Это не твоя кнопка. Забрать подарок может только победитель."