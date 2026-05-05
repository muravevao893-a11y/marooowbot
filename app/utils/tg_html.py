from __future__ import annotations

from html import escape


def h(value: object) -> str:
    return escape(str(value), quote=True)


def user_link(telegram_id: int | str, first_name: str | None = None, username: str | None = None) -> str:
    if username:
        return f"@{h(username)}"
    label = h(first_name or "user")
    return f'<a href="tg://user?id={int(telegram_id)}">{label}</a>'
