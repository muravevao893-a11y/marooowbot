from __future__ import annotations

from datetime import datetime
from typing import Iterable

from app.utils.tg_html import h, user_link
from app.utils.time import fmt_dt

BRAND = "&amp;marooow"
LINE = "━━━━━━━━━━━━━━"


def start_text(first_name: str | None, entries: int, wins: int, *, referral_active: int = 0, referral_pending: int = 0, referral_bonus: float = 0.0, bot_username: str = "marooowbot", telegram_id: int | None = None) -> str:
    name = h(first_name or "ты")
    ref_link = f"https://t.me/{bot_username.lstrip('@')}?start=ref_{telegram_id}" if telegram_id else "—"
    return (
        f"<b>{BRAND}</b>\n{LINE}\n\n"
        f"<b>{name}, профиль готов.</b>\n\n"
        "Пиши комментарии под постами — бот роллит шанс на подарок.\n"
        "Если выпадет мишка, бот ответит прямо на твой коммент.\n\n"
        "<b>Профиль</b>\n"
        f"• Участий: <b>{entries}</b>\n"
        f"• Побед: <b>{wins}</b>\n\n"
        "<b>Рефералка</b>\n"
        f"• Активных друзей: <b>{referral_active}</b>\n"
        f"• Ожидают активации: <b>{referral_pending}</b>\n"
        f"• Бонус к шансу: <b>+{referral_bonus:g}%</b>\n\n"
        "<b>Твоя ссылка</b>\n"
        f"<code>{h(ref_link)}</code>\n\n"
        "<i>Активный друг = +0.1% к шансу.</i>"
    )


def profile_text(telegram_id: int, username: str | None, first_name: str | None, entries: int, wins: int, banned: bool, *, referral_active: int = 0, referral_pending: int = 0, referral_bonus: float = 0.0, bot_username: str = "marooowbot") -> str:
    handle = f"@{h(username)}" if username else "—"
    ref_link = f"https://t.me/{bot_username.lstrip('@')}?start=ref_{telegram_id}"
    status = "забанен" if banned else "активен"
    return (
        f"<b>{BRAND}</b>\n{LINE}\n\n"
        "<b>Твой профиль</b>\n\n"
        f"• ID: <code>{telegram_id}</code>\n"
        f"• Ник: <b>{handle}</b>\n"
        f"• Имя: <b>{h(first_name or '—')}</b>\n"
        f"• Участий: <b>{entries}</b>\n"
        f"• Побед: <b>{wins}</b>\n"
        f"• Статус: <b>{status}</b>\n\n"
        "<b>Рефералка</b>\n"
        f"• Активных: <b>{referral_active}</b>\n"
        f"• Ожидают: <b>{referral_pending}</b>\n"
        f"• Бонус: <b>+{referral_bonus:g}%</b>\n\n"
        "<b>Ссылка</b>\n"
        f"<code>{h(ref_link)}</code>"
    )


def chance_text(base: float, bonus: float, final: float, active: int, pending: int, max_bonus: float, bot_username: str, telegram_id: int) -> str:
    ref_link = f"https://t.me/{bot_username.lstrip('@')}?start=ref_{telegram_id}"
    return (
        f"<b>{BRAND} chance</b>\n{LINE}\n\n"
        f"🎲 Твой шанс: <b>{final:g}%</b>\n\n"
        f"• База: <b>{base:g}%</b>\n"
        f"• Реф-бонус: <b>+{bonus:g}%</b>\n"
        f"• Максимум бонуса: <b>+{max_bonus:g}%</b>\n"
        f"• Активных друзей: <b>{active}</b>\n"
        f"• Ожидают активации: <b>{pending}</b>\n\n"
        "<b>Твоя ссылка</b>\n"
        f"<code>{h(ref_link)}</code>"
    )


def rules_text() -> str:
    return (
        f"<b>{BRAND} rules</b>\n{LINE}\n\n"
        "• Создай профиль через <b>/start</b>.\n"
        "• Подпишись на канал.\n"
        "• Пиши нормальные комментарии под постами.\n"
        "• За каждый валидный комментарий бот роллит шанс.\n"
        "• Если выпадет подарок — бот ответит на комментарий.\n"
        "• Админы и основатель не участвуют.\n\n"
        "<b>Антиабуз</b>\n"
        "• одинаковый спам не считается\n"
        "• слишком частые сообщения не считаются\n"
        "• мультиакки и накрутка = бан"
    )


def auto_drop_text(title: str, prize: str, ends_at: datetime, min_participants: int, chance_percent: float) -> str:
    return (
        "<b>#marooow подарки</b>\n"
        "<b>Здарова! ✨</b>\n\n"
        "Тут ты можешь общаться в комментариях и получать шанс на подарок.\n\n"
        f"Просто пиши комментарии — и с шансом <b>{chance_percent:g}%</b> можешь залутать <b>{h(prize)}</b> 🧸\n\n"
        "<b>Как забрать, если выпало</b>\n"
        "• бот ответит на твой коммент\n"
        "• нажмёшь кнопку <b>«Забрать мишку»</b>\n"
        "• подарок улетит автоматически\n\n"
        "<i>Рефералы повышают личный шанс.</i>"
    )


def chance_win_reply_text(prize: str) -> str:
    return (
        f"🎁 <b>{BRAND}</b>\n{LINE}\n\n"
        f"<b>Поздравляю, тебе выпал {h(prize)}.</b>\n\n"
        "Нажми кнопку ниже, чтобы забрать подарок."
    )


def claim_sent_text(prize: str) -> str:
    return f"✅ <b>Готово.</b>\n\n<b>{h(prize)}</b> отправлен тебе в Telegram."


def claim_manual_text(prize: str, error: str | None = None) -> str:
    extra = f"\n\n<code>{h(error)}</code>" if error else ""
    return f"⚠️ <b>Победа засчитана.</b>\n\nАвто-выдача не сработала. Админ выдаст <b>{h(prize)}</b> вручную.{extra}"


def winners_text(rows: Iterable[tuple[str, str, str]]) -> str:
    rows = list(rows)
    if not rows:
        body = "Победителей пока нет."
    else:
        body = "\n".join(f"{i}. {user} — <b>{h(prize)}</b> · {h(dt)}" for i, (user, prize, dt) in enumerate(rows, 1))
    return f"🏆 <b>{BRAND} winners</b>\n{LINE}\n\n{body}"


def refs_top_text(rows: Iterable[tuple[str, int]]) -> str:
    rows = list(rows)
    body = "Пока пусто." if not rows else "\n".join(f"{i}. {user} — <b>{count}</b> активных" for i, (user, count) in enumerate(rows, 1))
    return f"🏆 <b>Топ рефералов</b>\n{LINE}\n\n{body}"


def activity_text(rows: Iterable[tuple[str, int]]) -> str:
    rows = list(rows)
    body = "Активности пока нет." if not rows else "\n".join(f"{i}. {user} — <b>{count}</b> комм." for i, (user, count) in enumerate(rows, 1))
    return f"🔥 <b>Активность за 7 дней</b>\n{LINE}\n\n{body}"


def admin_text() -> str:
    return f"<b>{BRAND} admin</b>\n{LINE}\n\nВыбери действие или используй команды."


def stats_text(users: int, active_giveaways: int, wins: int, attempts_24h: int) -> str:
    return (
        f"📊 <b>{BRAND} stats</b>\n{LINE}\n\n"
        f"• Пользователей: <b>{users}</b>\n"
        f"• Активных дропов: <b>{active_giveaways}</b>\n"
        f"• Побед всего: <b>{wins}</b>\n"
        f"• Попыток за 24ч: <b>{attempts_24h}</b>"
    )


def manual_post_text(title: str, prize: str, winners: int, ends_at: datetime, count: int) -> str:
    return (
        f"<b>{BRAND}</b>\n{LINE}\n\n"
        f"🎁 <b>{h(title)}</b>\n\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Победителей: <b>{winners}</b>\n"
        f"Участников: <b>{count}</b>\n"
        f"Итоги: <b>{fmt_dt(ends_at)}</b>\n\n"
        "Жми кнопку ниже и жди итоги."
    )


def manual_finished_text(title: str, prize: str, count: int, winner_links: list[str]) -> str:
    winners = "\n".join(f"{i}. {link}" for i, link in enumerate(winner_links, 1)) if winner_links else "Победителей нет."
    return (
        f"🏁 <b>{BRAND} итоги</b>\n{LINE}\n\n"
        f"Розыгрыш: <b>{h(title)}</b>\n"
        f"Приз: <b>{h(prize)}</b>\n"
        f"Участников: <b>{count}</b>\n\n"
        f"<b>Победители</b>\n{winners}"
    )
