# app/services/stats_service.py
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.tg_html import user_link
from app.utils.time import fmt_dt


async def _table_columns(session: AsyncSession, table_name: str) -> set[str]:
    result = await session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return set(result.scalars().all())


async def get_bot_stats(session: AsyncSession) -> tuple[int, int, int, int]:
    users = await session.scalar(text("SELECT COUNT(*) FROM users")) or 0

    active_giveaways = await session.scalar(
        text("SELECT COUNT(*) FROM giveaways WHERE status = 'active'")
    ) or 0

    wins = await session.scalar(text("SELECT COUNT(*) FROM giveaway_winners")) or 0

    chance_columns = await _table_columns(session, "chance_attempts")

    if "created_at" in chance_columns:
        attempts_24h = await session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM chance_attempts
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                """
            )
        ) or 0
    else:
        attempts_24h = await session.scalar(text("SELECT COUNT(*) FROM chance_attempts")) or 0

    return int(users), int(active_giveaways), int(wins), int(attempts_24h)


async def latest_winners_rows(session: AsyncSession, limit: int = 10) -> list[tuple[str, str, str]]:
    winner_columns = await _table_columns(session, "giveaway_winners")
    giveaway_columns = await _table_columns(session, "giveaways")

    if "prize_name" in winner_columns:
        prize_expr = "gw.prize_name"
    elif "prize_name" in giveaway_columns:
        prize_expr = "g.prize_name"
    else:
        prize_expr = "'подарок'"

    if "created_at" in winner_columns:
        date_expr = "gw.created_at"
    elif "created_at" in giveaway_columns:
        date_expr = "g.created_at"
    else:
        date_expr = "NOW()"

    result = await session.execute(
        text(
            f"""
            SELECT
                u.telegram_id AS telegram_id,
                u.first_name AS first_name,
                u.username AS username,
                COALESCE({prize_expr}, 'подарок') AS prize_name,
                COALESCE({date_expr}, NOW()) AS created_at
            FROM giveaway_winners gw
            LEFT JOIN users u ON u.id = gw.user_id
            LEFT JOIN giveaways g ON g.id = gw.giveaway_id
            ORDER BY COALESCE({date_expr}, NOW()) DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )

    rows: list[tuple[str, str, str]] = []

    for row in result.mappings().all():
        telegram_id = row.get("telegram_id")
        first_name = row.get("first_name")
        username = row.get("username")
        prize_name = row.get("prize_name") or "подарок"
        created_at = row.get("created_at")

        if telegram_id:
            user = user_link(int(telegram_id), first_name, username)
        else:
            user = "пользователь"

        rows.append((user, str(prize_name), fmt_dt(created_at)))

    return rows


async def refs_top_rows(session: AsyncSession, limit: int = 10) -> list[tuple[str, int]]:
    referral_columns = await _table_columns(session, "referrals")

    status_filter = "WHERE r.status = 'active'" if "status" in referral_columns else ""

    result = await session.execute(
        text(
            f"""
            SELECT
                u.telegram_id AS telegram_id,
                u.first_name AS first_name,
                u.username AS username,
                COUNT(r.id) AS count
            FROM referrals r
            LEFT JOIN users u ON u.id = r.referrer_user_id
            {status_filter}
            GROUP BY u.telegram_id, u.first_name, u.username
            ORDER BY COUNT(r.id) DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )

    rows: list[tuple[str, int]] = []

    for row in result.mappings().all():
        telegram_id = row.get("telegram_id")
        first_name = row.get("first_name")
        username = row.get("username")
        count = int(row.get("count") or 0)

        if telegram_id:
            user = user_link(int(telegram_id), first_name, username)
        else:
            user = "пользователь"

        rows.append((user, count))

    return rows


async def activity_rows(session: AsyncSession, limit: int = 10) -> list[tuple[str, int]]:
    chance_columns = await _table_columns(session, "chance_attempts")

    date_filter = ""
    if "created_at" in chance_columns:
        date_filter = "WHERE ca.created_at >= NOW() - INTERVAL '7 days'"

    skipped_filter = ""
    if "skipped_reason" in chance_columns:
        if date_filter:
            skipped_filter = "AND ca.skipped_reason IS NULL"
        else:
            skipped_filter = "WHERE ca.skipped_reason IS NULL"

    result = await session.execute(
        text(
            f"""
            SELECT
                u.telegram_id AS telegram_id,
                u.first_name AS first_name,
                u.username AS username,
                COUNT(ca.id) AS count
            FROM chance_attempts ca
            LEFT JOIN users u ON u.id = ca.user_id
            {date_filter}
            {skipped_filter}
            GROUP BY u.telegram_id, u.first_name, u.username
            ORDER BY COUNT(ca.id) DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )

    rows: list[tuple[str, int]] = []

    for row in result.mappings().all():
        telegram_id = row.get("telegram_id")
        first_name = row.get("first_name")
        username = row.get("username")
        count = int(row.get("count") or 0)

        if telegram_id:
            user = user_link(int(telegram_id), first_name, username)
        else:
            user = "пользователь"

        rows.append((user, count))

    return rows