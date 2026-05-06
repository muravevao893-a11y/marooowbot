from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web
from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db.session import session_scope

STATIC_DIR = Path(__file__).parent / "static"


def _json(data: dict, status: int = 200) -> web.Response:
    return web.json_response(data, status=status, dumps=lambda x: json.dumps(x, ensure_ascii=False))


def _verify_init_data(init_data: str, bot_token: str) -> dict | None:
    if not init_data:
        return None
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    user_raw = pairs.get("user")
    if not user_raw:
        return None

    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        return None


async def _get_request_user(request: web.Request) -> tuple[dict | None, dict]:
    settings: Settings = request.app["settings"]
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    init_data = str(payload.get("initData") or request.query.get("initData") or "")
    user = _verify_init_data(init_data, settings.bot_token)

    # Local/dev fallback. Never use this in public ads, only for quick browser preview.
    if user is None and request.query.get("dev_tg_id"):
        try:
            user = {"id": int(request.query["dev_tg_id"]), "first_name": "dev", "username": "dev"}
        except ValueError:
            user = None

    return user, payload


def _ref_link(settings: Settings, telegram_id: int) -> str:
    return f"https://t.me/{settings.bot_username.lstrip('@')}?start=ref_{telegram_id}"


async def index(request: web.Request) -> web.Response:
    return web.FileResponse(STATIC_DIR / "index.html")


async def health(request: web.Request) -> web.Response:
    return _json({"ok": True, "service": "marooow-miniapp"})


async def me(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    user_data, _ = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)

    telegram_id = int(user_data["id"])
    username = user_data.get("username")
    first_name = user_data.get("first_name") or "marooow"

    async with session_scope() as session:
        row = (await session.execute(
            text("SELECT id, telegram_id, username, first_name, entries_count, wins_count, is_banned, app_stars, exp, level FROM users WHERE telegram_id=:tid"),
            {"tid": telegram_id},
        )).mappings().first()

        if row is None:
            await session.execute(
                text(
                    """
                    INSERT INTO users (telegram_id, username, first_name, entries_count, wins_count, is_banned, app_stars, exp, level)
                    VALUES (:tid, :username, :first_name, 0, 0, FALSE, 0, 0, 1)
                    """
                ),
                {"tid": telegram_id, "username": username, "first_name": first_name},
            )
            row = (await session.execute(
                text("SELECT id, telegram_id, username, first_name, entries_count, wins_count, is_banned, app_stars, exp, level FROM users WHERE telegram_id=:tid"),
                {"tid": telegram_id},
            )).mappings().first()
        else:
            await session.execute(
                text("UPDATE users SET username=:username, first_name=:first_name, last_seen_at=NOW() WHERE telegram_id=:tid"),
                {"tid": telegram_id, "username": username, "first_name": first_name},
            )

        active_refs = await session.scalar(
            text("SELECT COUNT(*) FROM referrals r JOIN users u ON u.id=r.referrer_user_id WHERE u.telegram_id=:tid AND r.status='active'"),
            {"tid": telegram_id},
        ) or 0
        pending_refs = await session.scalar(
            text("SELECT COUNT(*) FROM referrals r JOIN users u ON u.id=r.referrer_user_id WHERE u.telegram_id=:tid AND r.status='pending'"),
            {"tid": telegram_id},
        ) or 0
        attempts_7d = await session.scalar(
            text("SELECT COUNT(*) FROM chance_attempts ca JOIN users u ON u.id=ca.user_id WHERE u.telegram_id=:tid AND ca.created_at >= NOW() - INTERVAL '7 days'"),
            {"tid": telegram_id},
        ) or 0
        wins_total = await session.scalar(
            text("SELECT COUNT(*) FROM giveaway_winners gw JOIN users u ON u.id=gw.user_id WHERE u.telegram_id=:tid"),
            {"tid": telegram_id},
        ) or 0

    bonus = min(float(active_refs) * settings.referral_bonus_percent, settings.referral_bonus_cap_percent)
    base = settings.chance_drop_percent
    final_chance = base + bonus
    exp = int(row.get("exp") or 0)
    level = int(row.get("level") or 1)

    return _json({
        "ok": True,
        "telegram": {
            "id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": user_data.get("last_name"),
            "photo_url": user_data.get("photo_url"),
            "language_code": user_data.get("language_code"),
        },
        "user": {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "stars": int(row.get("app_stars") or 0),
            "exp": exp,
            "level": level,
            "next_level_exp": max(level * 10000, 10000),
            "entries_count": int(row.get("entries_count") or 0),
            "wins_count": int(wins_total),
            "is_banned": bool(row.get("is_banned")),
            "ref_link": _ref_link(settings, telegram_id),
        },
        "chance": {
            "base": base,
            "bonus": round(bonus, 2),
            "final": round(final_chance, 2),
            "cap": settings.referral_bonus_cap_percent,
            "active_refs": int(active_refs),
            "pending_refs": int(pending_refs),
            "attempts_7d": int(attempts_7d),
        },
        "drops": {
            "active_title": settings.auto_drop_title,
            "prize": settings.auto_drop_prize,
            "chance_percent": base,
            "gift_id_set": bool(settings.auto_drop_gift_id),
        }
    })


async def winners(request: web.Request) -> web.Response:
    async with session_scope() as session:
        rows = (await session.execute(
            text(
                """
                SELECT u.telegram_id, u.username, u.first_name, COALESCE(gw.prize_name, g.prize_name, 'подарок') AS prize_name, COALESCE(gw.created_at, NOW()) AS created_at
                FROM giveaway_winners gw
                LEFT JOIN users u ON u.id=gw.user_id
                LEFT JOIN giveaways g ON g.id=gw.giveaway_id
                ORDER BY COALESCE(gw.created_at, NOW()) DESC
                LIMIT 20
                """
            )
        )).mappings().all()
    return _json({"ok": True, "items": [dict(r) | {"created_at": str(r["created_at"])} for r in rows]})


async def leaderboard(request: web.Request) -> web.Response:
    async with session_scope() as session:
        refs = (await session.execute(
            text(
                """
                SELECT u.telegram_id, u.username, u.first_name, COUNT(r.id) AS score
                FROM referrals r
                JOIN users u ON u.id=r.referrer_user_id
                WHERE r.status='active'
                GROUP BY u.telegram_id, u.username, u.first_name
                ORDER BY COUNT(r.id) DESC
                LIMIT 10
                """
            )
        )).mappings().all()
        activity = (await session.execute(
            text(
                """
                SELECT u.telegram_id, u.username, u.first_name, COUNT(ca.id) AS score
                FROM chance_attempts ca
                JOIN users u ON u.id=ca.user_id
                WHERE ca.created_at >= NOW() - INTERVAL '7 days' AND ca.skipped_reason IS NULL
                GROUP BY u.telegram_id, u.username, u.first_name
                ORDER BY COUNT(ca.id) DESC
                LIMIT 10
                """
            )
        )).mappings().all()
    return _json({"ok": True, "refs": [dict(r) for r in refs], "activity": [dict(r) for r in activity]})


async def daily(request: web.Request) -> web.Response:
    user_data, _ = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    telegram_id = int(user_data["id"])

    async with session_scope() as session:
        row = (await session.execute(
            text("SELECT id, last_daily_at FROM users WHERE telegram_id=:tid"), {"tid": telegram_id}
        )).mappings().first()
        if row is None:
            return _json({"ok": False, "error": "profile_not_found"}, 404)

        can_claim = await session.scalar(
            text("SELECT CASE WHEN last_daily_at IS NULL OR last_daily_at < NOW() - INTERVAL '20 hours' THEN TRUE ELSE FALSE END FROM users WHERE telegram_id=:tid"),
            {"tid": telegram_id},
        )
        if not can_claim:
            return _json({"ok": False, "error": "cooldown", "message": "Бонус уже забран. Попробуй позже."}, 429)

        await session.execute(
            text("UPDATE users SET app_stars=COALESCE(app_stars,0)+5, exp=COALESCE(exp,0)+100, last_daily_at=NOW() WHERE telegram_id=:tid"),
            {"tid": telegram_id},
        )
        await session.execute(
            text("INSERT INTO miniapp_transactions (telegram_id, kind, amount, payload) VALUES (:tid, 'daily', 5, 'daily bonus')"),
            {"tid": telegram_id},
        )

    return _json({"ok": True, "stars_added": 5, "exp_added": 100})


async def topup_invoice(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    settings: Settings = request.app["settings"]
    user_data, payload = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    amount = int(payload.get("amount") or 100)
    amount = max(1, min(amount, 10000))
    try:
        link = await bot.create_invoice_link(
            title="Пополнение &marooow",
            description=f"Пополнение баланса на {amount} Telegram Stars",
            payload=f"miniapp_topup:{user_data['id']}:{amount}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)],
        )
    except Exception as exc:
        return _json({"ok": False, "error": "invoice_failed", "message": str(exc)}, 500)
    return _json({"ok": True, "invoice_url": link})


async def gift_catalog(request: web.Request) -> web.Response:
    """Catalog of gifts the bot can send, from Telegram Bot API.
    This is not the user's personal Telegram/Fragment inventory.
    """
    bot: Bot = request.app["bot"]
    try:
        available = await bot.get_available_gifts()
    except Exception as exc:
        return _json({"ok": False, "error": "gifts_failed", "message": str(exc)}, 500)

    items = []
    for gift in getattr(available, "gifts", [])[:60]:
        sticker = getattr(gift, "sticker", None)
        file_id = getattr(sticker, "file_id", None) if sticker else None
        emoji = getattr(sticker, "emoji", None) if sticker else None
        items.append({
            "id": str(getattr(gift, "id", "")),
            "star_count": int(getattr(gift, "star_count", 0) or 0),
            "total_count": getattr(gift, "total_count", None),
            "remaining_count": getattr(gift, "remaining_count", None),
            "emoji": emoji or "🎁",
            "sticker_file_id": file_id,
            "media_url": f"/api/gift-media/{file_id}" if file_id else None,
        })
    return _json({"ok": True, "items": items})


async def gift_media(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    file_id = request.match_info.get("file_id", "")
    if not file_id:
        return web.Response(status=404)
    try:
        tg_file = await bot.get_file(file_id)
        bio = BytesIO()
        await bot.download_file(tg_file.file_path, destination=bio)
        data = bio.getvalue()
        ctype = mimetypes.guess_type(tg_file.file_path or "")[0] or "application/octet-stream"
        return web.Response(body=data, content_type=ctype, headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        return web.Response(status=404)


async def inventory(request: web.Request) -> web.Response:
    user_data, _ = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    telegram_id = int(user_data["id"])
    async with session_scope() as session:
        rows = (await session.execute(
            text(
                """
                SELECT
                    COALESCE(gw.prize_name, g.prize_name, 'подарок') AS prize_name,
                    COALESCE(gw.gift_id, g.gift_id) AS gift_id,
                    COALESCE(gw.delivery_status, 'pending') AS status,
                    COALESCE(gw.created_at, NOW()) AS created_at
                FROM giveaway_winners gw
                LEFT JOIN giveaways g ON g.id = gw.giveaway_id
                LEFT JOIN users u ON u.id = gw.user_id
                WHERE u.telegram_id = :tid
                ORDER BY COALESCE(gw.created_at, NOW()) DESC
                LIMIT 50
                """
            ),
            {"tid": telegram_id},
        )).mappings().all()
    return _json({"ok": True, "items": [dict(r) | {"created_at": str(r["created_at"])} for r in rows]})


def setup_webapp_routes(app: web.Application, bot: Bot, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    app["bot"] = bot
    app["settings"] = settings

    app.router.add_get("/", index)
    app.router.add_get("/app", index)
    app.router.add_get("/app/", index)
    app.router.add_static("/app/static", STATIC_DIR, show_index=False)
    app.router.add_get("/api/health", health)
    app.router.add_post("/api/me", me)
    app.router.add_get("/api/winners", winners)
    app.router.add_get("/api/leaderboard", leaderboard)
    app.router.add_post("/api/daily", daily)
    app.router.add_post("/api/topup", topup_invoice)
    app.router.add_get("/api/gift-catalog", gift_catalog)
    app.router.add_get("/api/gift-media/{file_id}", gift_media)
    app.router.add_post("/api/inventory", inventory)
