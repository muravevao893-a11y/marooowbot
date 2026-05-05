from __future__ import annotations

from datetime import datetime
from typing import Iterable

from app.utils.tg_html import h, user_link
from app.utils.time import fmt_dt


BRAND = '&amp;marooow'
LINE = '━━━━━━━━━━━━━━'
THIN = '————————————'


def pct(value: float | int) -> str:
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f'{value:.2f}'.rstrip('0').rstrip('.')


def start_text(
    first_name: str | None = None,
    entries: int = 0,
    wins: int = 0,
    referral_active: int = 0,
    referral_pending: int = 0,
    referral_bonus: float = 0.0,
    bot_username: str = 'marooowbot',
    telegram_id: int | None = None,
    *args,
    **kwargs,
) -> str:
    name = h(first_name or 'друг')
    ref_link = '—'
    if telegram_id:
        ref_link = f'https://t.me/{bot_username.lstrip("@")}?' f'start=ref_{telegram_id}'

    return (
        f'<b>{BRAND}</b> · <b>профиль</b>\n'
        f'{LINE}\n\n'
        f'Привет, <b>{name}</b>. Профиль готов.\n\n'
        '<b>Что дальше?</b>\n'
        '• пиши комментарии под постами\n'
        '• бот роллит шанс выпадения подарка\n'
        '• если повезло — бот ответит на твой коммент\n\n'
        '<b>Статистика</b>\n'
        f'• Участий: <b>{entries}</b>\n'
        f'• Побед: <b>{wins}</b>\n'
        f'• Реф-бонус: <b>+{pct(referral_bonus)}%</b>\n\n'
        '<b>Рефералка</b>\n'
        f'• Активных друзей: <b>{referral_active}</b>\n'
        f'• Ожидают активации: <b>{referral_pending}</b>\n\n'
        '<b>Твоя ссылка</b>\n'
        f'<code>{h(ref_link)}</code>\n\n'
        '<i>1 активный друг = +0.1% к шансу. Активация: 5 комментов под 2 постами.</i>'
    )


def profile_text(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    entries: int = 0,
    wins: int = 0,
    banned: bool = False,
    referral_active: int = 0,
    referral_pending: int = 0,
    referral_bonus: float = 0.0,
    bot_username: str = 'marooowbot',
    *args,
    **kwargs,
) -> str:
    status = 'забанен' if banned else 'активен'
    handle = f'@{h(username)}' if username else '—'
    name = h(first_name or '—')
    ref_link = f'https://t.me/{bot_username.lstrip("@")}?' f'start=ref_{telegram_id}'

    return (
        f'<b>{BRAND}</b> · <b>твой профиль</b>\n'
        f'{LINE}\n\n'
        f'ID: <code>{telegram_id}</code>\n'
        f'Ник: <b>{handle}</b>\n'
        f'Имя: <b>{name}</b>\n'
        f'Статус: <b>{status}</b>\n\n'
        '<b>Дропы</b>\n'
        f'• Участий: <b>{entries}</b>\n'
        f'• Побед: <b>{wins}</b>\n\n'
        '<b>Рефералка</b>\n'
        f'• Активных: <b>{referral_active}</b>\n'
        f'• Ожидают: <b>{referral_pending}</b>\n'
        f'• Бонус к шансу: <b>+{pct(referral_bonus)}%</b>\n\n'
        '<b>Ссылка для друзей</b>\n'
        f'<code>{h(ref_link)}</code>'
    )


def chance_text(details: dict, bot_username: str, telegram_id: int) -> str:
    ref_link = f'https://t.me/{bot_username.lstrip("@")}?' f'start=ref_{telegram_id}'
    next_line = 'Бонус уже на максимуме.' if details['bonus'] >= details['bonus_cap'] else 'Следующий активный друг даст ещё +0.1%.'
    return (
        f'<b>{BRAND}</b> · <b>твой шанс</b>\n'
        f'{LINE}\n\n'
        f'Итоговый шанс: <b>{pct(details["final"])}%</b>\n'
        f'База: <b>{pct(details["base"])}%</b>\n'
        f'Реф-бонус: <b>+{pct(details["bonus"])}%</b>\n'
        f'Максимум бонуса: <b>+{pct(details["bonus_cap"])}%</b>\n\n'
        '<b>Рефералы</b>\n'
        f'• Активных: <b>{details["active_referrals"]}</b>\n'
        f'• Ожидают: <b>{details["pending_referrals"]}</b>\n'
        f'• Активация: <b>{details["required_comments"]}</b> комментов под <b>{details["required_posts"]}</b> постами\n\n'
        f'<i>{next_line}</i>\n\n'
        '<b>Твоя ссылка</b>\n'
        f'<code>{h(ref_link)}</code>'
    )


def rules_text(*args, **kwargs) -> str:
    return (
        f'<b>{BRAND}</b> · <b>правила</b>\n'
        f'{LINE}\n\n'
        '<b>Как участвовать</b>\n'
        '1. Нажми <b>/start</b> в боте.\n'
        '2. Подпишись на канал.\n'
        '3. Пиши нормальные комментарии под постами.\n'
        '4. Если подарок выпал — бот ответит на твой комментарий.\n\n'
        '<b>Рефералка</b>\n'
        '• друг должен зайти по твоей ссылке\n'
        '• написать 5 комментариев под 2 разными постами\n'
        '• за активного друга: <b>+0.1%</b> к шансу\n\n'
        '<b>Антиабуз</b>\n'
        '• короткий флуд не считается\n'
        '• одинаковые сообщения режутся\n'
        '• слишком частые комменты не роллят шанс\n'
        '• админы и основатель не участвуют\n\n'
        '<i>Пиши живые комменты — так шанс считается честно.</i>'
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
        f'<b>{BRAND} drop</b>\n'
        f'{LINE}\n\n'
        '<b>Здарова. Тут активен дроп.</b>\n\n'
        f'Пиши комментарии под этим постом — бот роллит шанс на <b>{h(prize)}</b>.\n\n'
        '<b>Как работает</b>\n'
        f'• базовый шанс: <b>{pct(chance_percent)}%</b> за комментарий\n'
        '• рефералы повышают шанс\n'
        '• если выпадет — бот ответит на твой коммент\n'
        '• подарок забирается кнопкой\n\n'
        '<b>Важно</b>\n'
        'Нужен профиль в боте и подписка на канал.\n\n'
        '⭐ Купить звёзды дешево с любым способом оплаты:\n'
        '<b>@lstarzbot</b>'
    )


def chance_win_reply_text(prize: str, *args, **kwargs) -> str:
    return (
        f'🎁 <b>{BRAND}</b>\n'
        f'{LINE}\n\n'
        f'<b>Поздравляю, тебе выпал {h(prize)}.</b>\n\n'
        'Жми кнопку ниже, чтобы забрать подарок.'
    )


def chance_claim_sent_text(prize: str, *args, **kwargs) -> str:
    return (
        '✅ <b>Подарок отправлен.</b>\n\n'
        f'<b>{h(prize)}</b> уже улетел тебе в Telegram.'
    )


def chance_claim_manual_text(prize: str, *args, **kwargs) -> str:
    return (
        '⚠️ <b>Победа засчитана.</b>\n\n'
        f'Авто-выдача сейчас недоступна. Админ выдаст <b>{h(prize)}</b> вручную.'
    )


def chance_claim_forbidden_text(*args, **kwargs) -> str:
    return '⛔ Это не твоя кнопка. Забрать подарок может только победитель.'


def proof_win_text(user, prize: str, final_chance: float | None = None) -> str:
    chance_line = f'\nШанс победителя: <b>{pct(final_chance)}%</b>' if final_chance is not None else ''
    return (
        f'🧸 <b>{BRAND} proof</b>\n'
        f'{LINE}\n\n'
        f'Подарок <b>{h(prize)}</b> улетел {user_link(user.telegram_id, user.first_name, user.username)}.{chance_line}\n\n'
        '<i>Следующий шанс — в комментариях под постами.</i>'
    )


def manual_giveaway_text(title: str, description: str | None, prize: str, winners: int, ends_at: datetime, count: int, *args, **kwargs) -> str:
    desc = f'\n{h(description)}\n' if description else ''
    return (
        f'<b>{BRAND}</b> · <b>розыгрыш</b>\n'
        f'{LINE}\n\n'
        f'🎁 <b>{h(title)}</b>\n{desc}\n'
        f'Приз: <b>{h(prize)}</b>\n'
        f'Победителей: <b>{winners}</b>\n'
        f'Участников: <b>{count}</b>\n'
        f'Финиш: <b>{fmt_dt(ends_at)}</b>\n\n'
        '<b>Условия</b>\n'
        '• профиль в боте\n'
        '• подписка на канал\n'
        '• участие через кнопку\n\n'
        '<i>Жми кнопку ниже и жди итоги.</i>'
    )


def joined_text(title: str, number: int, ends_at: datetime, *args, **kwargs) -> str:
    return (
        '✅ <b>Ты в розыгрыше.</b>\n\n'
        f'Розыгрыш: <b>{h(title)}</b>\n'
        f'Твой номер: <b>#{number}</b>\n'
        f'Итоги: <b>{fmt_dt(ends_at)}</b>'
    )


def already_joined_text(title: str, *args, **kwargs) -> str:
    return f'⚠️ <b>Ты уже участвуешь.</b>\n\nРозыгрыш: <b>{h(title)}</b>'


def finish_no_winners_text(title: str, participants: int, min_participants: int, *args, **kwargs) -> str:
    return (
        f'🏁 <b>{BRAND} итоги</b>\n'
        f'{LINE}\n\n'
        f'Розыгрыш: <b>{h(title)}</b>\n'
        f'Участников: <b>{participants}</b>\n\n'
        f'Победителей нет: нужно минимум <b>{min_participants}</b> участников.'
    )


def finish_winners_text(title: str, prize: str, participants: int, winner_rows: list[tuple[int, str | None, str | None]], *args, **kwargs) -> str:
    winners = '\n'.join(f'{i}. {user_link(tg_id, first_name, username)}' for i, (tg_id, username, first_name) in enumerate(winner_rows, start=1)) or '—'
    return (
        f'🏁 <b>{BRAND} итоги</b>\n'
        f'{LINE}\n\n'
        f'Розыгрыш: <b>{h(title)}</b>\n'
        f'Приз: <b>{h(prize)}</b>\n'
        f'Участников: <b>{participants}</b>\n\n'
        '<b>Победители</b>\n'
        f'{winners}\n\n'
        '<i>Подарки отправляются автоматически или проверяются админом.</i>'
    )


def winners_text(winners: Iterable, limit: int = 10) -> str:
    winners = list(winners)
    if not winners:
        return f'<b>{BRAND}</b> · <b>победители</b>\n{LINE}\n\nПока победителей нет.'

    lines = []
    for i, winner in enumerate(winners[:limit], start=1):
        prize = getattr(winner.giveaway, 'prize_name', 'подарок') if winner.giveaway else 'подарок'
        user = winner.user
        if user:
            name = user_link(user.telegram_id, user.first_name, user.username)
        else:
            name = 'user'
        status = 'выдан' if winner.delivery_status == 'sent' else 'ожидает'
        lines.append(f'{i}. {name} — <b>{h(prize)}</b> · <i>{status}</i>')

    return (
        f'<b>{BRAND}</b> · <b>последние победы</b>\n'
        f'{LINE}\n\n'
        + '\n'.join(lines)
    )


def ref_leaderboard_text(rows: list[tuple], title: str = 'топ рефералов') -> str:
    if not rows:
        return f'<b>{BRAND}</b> · <b>{h(title)}</b>\n{LINE}\n\nПока топ пустой.'
    lines = []
    for i, (user, count) in enumerate(rows, start=1):
        lines.append(f'{i}. {user_link(user.telegram_id, user.first_name, user.username)} — <b>{count}</b> активных')
    return f'<b>{BRAND}</b> · <b>{h(title)}</b>\n{LINE}\n\n' + '\n'.join(lines)


def activity_leaderboard_text(rows: list[tuple], days: int = 7) -> str:
    if not rows:
        return f'<b>{BRAND}</b> · <b>активность</b>\n{LINE}\n\nПока активности мало.'
    lines = []
    for i, (user, count) in enumerate(rows, start=1):
        lines.append(f'{i}. {user_link(user.telegram_id, user.first_name, user.username)} — <b>{count}</b> попыток')
    return f'<b>{BRAND}</b> · <b>топ активности за {days} дней</b>\n{LINE}\n\n' + '\n'.join(lines)


def active_giveaways_text(count: int = 0, *args, **kwargs) -> str:
    if count <= 0:
        return f'<b>{BRAND}</b> · <b>активные</b>\n{LINE}\n\nАктивных ручных розыгрышей сейчас нет.\n\n<i>Но авто-дропы появляются под новыми постами.</i>'
    return f'<b>{BRAND}</b> · <b>активные</b>\n{LINE}\n\nАктивные розыгрыши: <b>{count}</b>'


def admin_home_text(*args, **kwargs) -> str:
    return (
        f'<b>{BRAND}</b> · <b>admin</b>\n'
        f'{LINE}\n\n'
        'Выбери действие ниже.\n\n'
        '<i>Подсказка: /balance, /gifts, /topup 100, /stats</i>'
    )


def create_preview_text(title: str, prize: str, winners: int, duration_min: int, description: str | None, gift_id: str | None, *args, **kwargs) -> str:
    return (
        '<b>Предпросмотр розыгрыша</b>\n'
        f'{LINE}\n\n'
        f'Название: <b>{h(title)}</b>\n'
        f'Приз: <b>{h(prize)}</b>\n'
        f'Победителей: <b>{winners}</b>\n'
        f'Время: <b>{duration_min} мин.</b>\n'
        f'Gift ID: <code>{h(gift_id or "ручная выдача")}</code>\n\n'
        '<b>Описание</b>\n'
        f'{h(description or "—")}'
    )


def admin_stats_text(users: int, active_giveaways: int, winners: int, active_refs: int, attempts_24h: int) -> str:
    return (
        f'<b>{BRAND}</b> · <b>stats</b>\n'
        f'{LINE}\n\n'
        f'Пользователей: <b>{users}</b>\n'
        f'Активных розыгрышей: <b>{active_giveaways}</b>\n'
        f'Побед всего: <b>{winners}</b>\n'
        f'Активных рефералов: <b>{active_refs}</b>\n'
        f'Попыток за 24ч: <b>{attempts_24h}</b>'
    )
