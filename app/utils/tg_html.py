from __future__ import annotations

from html import escape
from typing import Any


def h(value: Any) -> str:
    return escape(str(value), quote=True)


def user_link(telegram_id: int, first_name: str | None = None, username: str | None = None) -> str:
    if username:
        return f'@{h(username)}'
    return f'<a href="tg://user?id={int(telegram_id)}">{h(first_name or telegram_id)}</a>'
