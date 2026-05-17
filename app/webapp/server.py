from __future__ import annotations

import hashlib
import hmac
import json
import math
import mimetypes
import secrets
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import ClientSession, web
from aiogram import Bot
from aiogram.types import LabeledPrice
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db.session import session_scope

STATIC_DIR = Path(__file__).parent / "static"


def _json(data: dict, status: int = 200) -> web.Response:
    return web.json_response(data, status=status, dumps=lambda x: json.dumps(x, ensure_ascii=False, default=str))


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

    # Only for quick browser preview.
    if user is None and request.query.get("dev_tg_id"):
        try:
            user = {"id": int(request.query["dev_tg_id"]), "first_name": "dev", "username": "dev"}
        except ValueError:
            user = None

    return user, payload


def _ref_link(settings: Settings, telegram_id: int) -> str:
    return f"https://t.me/{settings.bot_username.lstrip('@')}?start=ref_{telegram_id}"


def _miniapp_url(settings: Settings, request: web.Request) -> str:
    if settings.mini_app_url:
        return settings.mini_app_url.rstrip("/")
    return str(request.url.with_path("/app").with_query({})).rstrip("/")


def _ton_to_nano(amount_ton: float) -> int:
    return int(math.ceil(amount_ton * 1_000_000_000))


def _nano_to_ton(amount_nano: int) -> float:
    return round(amount_nano / 1_000_000_000, 6)


async def index(request: web.Request) -> web.Response:
    # HARD FIX: serve the Mini App shell as text/html with inline CSS/JS.
    # This avoids Telegram WebView / Railway static CSS cache problems.
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return web.Response(
        text=html,
        content_type="text/html",
        charset="utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Maroow-UI": "v17-miniapp-instant-ui",
        },
    )


async def health(request: web.Request) -> web.Response:
    return _json({"ok": True, "service": "marooow-miniapp", "version": "miniapp-ui-v17"})


async def ton_manifest(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    base = _miniapp_url(settings, request).replace("/app", "")
    return _json(
        {
            "url": _miniapp_url(settings, request),
            "name": "marooow",
            "iconUrl": f"{base}/app/static/logo.svg",
            "termsOfUseUrl": f"{base}/app",
            "privacyPolicyUrl": f"{base}/app",
        }
    )


async def me(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    user_data, _ = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)

    telegram_id = int(user_data["id"])
    username = user_data.get("username")
    first_name = user_data.get("first_name") or "marooow"
    photo_url = user_data.get("photo_url")

    async with session_scope() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT id, telegram_id, username, first_name, entries_count, wins_count, is_banned,
                           app_stars, exp, level, photo_url
                    FROM users
                    WHERE telegram_id=:tid
                    """
                ),
                {"tid": telegram_id},
            )
        ).mappings().first()

        if row is None:
            await session.execute(
                text(
                    """
                    INSERT INTO users (telegram_id, username, first_name, entries_count, wins_count, is_banned, app_stars, exp, level, photo_url, last_seen_at)
                    VALUES (:tid, :username, :first_name, 0, 0, FALSE, 0, 0, 1, :photo_url, NOW())
                    """
                ),
                {"tid": telegram_id, "username": username, "first_name": first_name, "photo_url": photo_url},
            )
            row = (
                await session.execute(
                    text(
                        """
                        SELECT id, telegram_id, username, first_name, entries_count, wins_count, is_banned,
                               app_stars, exp, level, photo_url
                        FROM users
                        WHERE telegram_id=:tid
                        """
                    ),
                    {"tid": telegram_id},
                )
            ).mappings().first()
        else:
            await session.execute(
                text(
                    """
                    UPDATE users
                    SET username=:username, first_name=:first_name, photo_url=COALESCE(:photo_url, photo_url), last_seen_at=NOW()
                    WHERE telegram_id=:tid
                    """
                ),
                {"tid": telegram_id, "username": username, "first_name": first_name, "photo_url": photo_url},
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
        pending_deposits = await session.scalar(
            text("SELECT COUNT(*) FROM miniapp_deposits WHERE telegram_id=:tid AND status='pending'"),
            {"tid": telegram_id},
        ) or 0

    bonus = min(float(active_refs) * settings.referral_bonus_percent, settings.referral_bonus_cap_percent)
    base = settings.chance_drop_percent
    final_chance = base + bonus
    exp = int(row.get("exp") or 0)
    level = int(row.get("level") or 1)

    return _json(
        {
            "ok": True,
            "telegram": {
                "id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": user_data.get("last_name"),
                "photo_url": photo_url or row.get("photo_url"),
                "language_code": user_data.get("language_code"),
            },
            "user": {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "photo_url": photo_url or row.get("photo_url"),
                "stars": int(row.get("app_stars") or 0),
                "exp": exp,
                "level": level,
                "next_level_exp": max(level * 10000, 10000),
                "entries_count": int(row.get("entries_count") or 0),
                "wins_count": int(wins_total),
                "is_banned": bool(row.get("is_banned")),
                "ref_link": _ref_link(settings, telegram_id),
                "pending_deposits": int(pending_deposits),
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
            "ton": {
                "enabled": bool(settings.ton_receiver_address),
                "receiver": settings.ton_receiver_address,
                "stars_per_ton": settings.ton_stars_per_ton,
                "verified_mode": bool(settings.tonapi_key),
            },
            "drops": {
                "active_title": settings.auto_drop_title,
                "prize": settings.auto_drop_prize,
                "chance_percent": base,
                "gift_id_set": bool(settings.auto_drop_gift_id),
            },
        }
    )


async def winners(request: web.Request) -> web.Response:
    async with session_scope() as session:
        rows = (
            await session.execute(
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
            )
        ).mappings().all()
    return _json({"ok": True, "items": [dict(r) | {"created_at": str(r["created_at"])} for r in rows]})


async def leaderboard(request: web.Request) -> web.Response:
    async with session_scope() as session:
        refs = (
            await session.execute(
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
            )
        ).mappings().all()
        activity = (
            await session.execute(
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
            )
        ).mappings().all()
    return _json({"ok": True, "refs": [dict(r) for r in refs], "activity": [dict(r) for r in activity]})


async def daily(request: web.Request) -> web.Response:
    user_data, _ = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    telegram_id = int(user_data["id"])

    async with session_scope() as session:
        row = (
            await session.execute(text("SELECT id, last_daily_at FROM users WHERE telegram_id=:tid"), {"tid": telegram_id})
        ).mappings().first()
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


async def ton_create_deposit(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    user_data, payload = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    if not settings.ton_receiver_address:
        return _json({"ok": False, "error": "ton_not_configured", "message": "TON кошелёк проекта не указан в TON_RECEIVER_ADDRESS."}, 400)

    telegram_id = int(user_data["id"])
    stars_amount = max(30, min(int(payload.get("stars_amount") or 100), 100000))
    ton_amount = stars_amount / float(settings.ton_stars_per_ton)
    base_nano = _ton_to_nano(ton_amount)
    # Unique tiny nanoton offset lets us verify a deposit by exact amount even if a wallet doesn't support text payloads.
    amount_nano = base_nano + secrets.randbelow(9000) + 1000
    comment = f"marooow-{telegram_id}-{secrets.token_hex(4)}"

    async with session_scope() as session:
        await session.execute(
            text(
                """
                INSERT INTO miniapp_deposits (telegram_id, method, status, stars_amount, ton_amount_nano, comment, wallet_address)
                VALUES (:tid, 'ton', 'pending', :stars, :nano, :comment, :wallet)
                """
            ),
            {"tid": telegram_id, "stars": stars_amount, "nano": amount_nano, "comment": comment, "wallet": settings.ton_receiver_address},
        )
        deposit_id = await session.scalar(text("SELECT id FROM miniapp_deposits WHERE comment=:comment"), {"comment": comment})

    return _json(
        {
            "ok": True,
            "deposit_id": int(deposit_id),
            "address": settings.ton_receiver_address,
            "amount_nano": str(amount_nano),
            "amount_ton": _nano_to_ton(amount_nano),
            "stars_amount": stars_amount,
            "comment": comment,
            "verified_mode": bool(settings.tonapi_key),
        }
    )


def _event_matches_deposit(event: dict, receiver: str, amount_nano: int, comment: str) -> tuple[bool, str | None]:
    """Best-effort parser for TonAPI account events.
    We keep it defensive because indexers may change field names.
    """
    event_id = str(event.get("event_id") or event.get("id") or event.get("trace_id") or "")
    actions = event.get("actions") or []
    for action in actions:
        status = str(action.get("status") or "").lower()
        if status and status not in {"ok", "success"}:
            continue
        transfer = action.get("TonTransfer") or action.get("ton_transfer") or action.get("simple_preview") or {}
        candidates = [transfer, action]
        for obj in candidates:
            raw_amount = obj.get("amount") or obj.get("value") or obj.get("nanoton") or obj.get("amount_nano")
            try:
                got_amount = int(raw_amount)
            except Exception:
                got_amount = 0
            text_comment = str(obj.get("comment") or obj.get("message") or obj.get("payload") or obj.get("description") or "")
            recipient = obj.get("recipient") or obj.get("to") or {}
            if isinstance(recipient, dict):
                recipient_addr = str(recipient.get("address") or recipient.get("raw_form") or "")
            else:
                recipient_addr = str(recipient or "")
            # Primary path: exact randomized amount. Secondary path: text comment if wallet supports payloads.
            amount_ok = got_amount == amount_nano or (got_amount >= amount_nano and comment and comment in text_comment)
            receiver_ok = (not recipient_addr or receiver in recipient_addr or recipient_addr in receiver)
            if amount_ok and receiver_ok:
                return True, event_id
    # fallback: stringify event for exact randomized amount or optional comment.
    raw = json.dumps(event, ensure_ascii=False)
    if str(amount_nano) in raw or (comment and comment in raw):
        return True, event_id
    return False, None


async def _verify_ton_deposit(settings: Settings, comment: str, amount_nano: int) -> str | None:
    if not settings.tonapi_key or not settings.ton_receiver_address:
        return None
    url = f"https://tonapi.io/v2/accounts/{settings.ton_receiver_address}/events?limit=50"
    headers = {"Authorization": f"Bearer {settings.tonapi_key}"}
    async with ClientSession(headers=headers) as client:
        async with client.get(url, timeout=12) as resp:
            if resp.status >= 400:
                return None
            data = await resp.json()
    events = data.get("events") or data.get("items") or []
    for event in events:
        ok, event_id = _event_matches_deposit(event, settings.ton_receiver_address, amount_nano, comment)
        if ok:
            return event_id or "tonapi_event"
    return None


async def ton_confirm_deposit(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    user_data, payload = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    telegram_id = int(user_data["id"])
    deposit_id = int(payload.get("deposit_id") or 0)
    boc = str(payload.get("boc") or "")[:5000]

    async with session_scope() as session:
        dep = (
            await session.execute(
                text(
                    """
                    SELECT id, telegram_id, status, stars_amount, ton_amount_nano, comment, wallet_address, created_at
                    FROM miniapp_deposits
                    WHERE id=:id AND telegram_id=:tid
                    """
                ),
                {"id": deposit_id, "tid": telegram_id},
            )
        ).mappings().first()
        if not dep:
            return _json({"ok": False, "error": "deposit_not_found"}, 404)
        if dep["status"] == "paid":
            return _json({"ok": True, "status": "paid", "stars_added": int(dep["stars_amount"] or 0)})
        await session.execute(
            text("UPDATE miniapp_deposits SET raw_payload=:boc WHERE id=:id"),
            {"id": deposit_id, "boc": boc},
        )

    tx_hash = await _verify_ton_deposit(settings, str(dep["comment"]), int(dep["ton_amount_nano"] or 0))
    if not tx_hash:
        return _json(
            {
                "ok": True,
                "status": "pending",
                "message": "Платёж отправлен. Если TONAPI_KEY указан, бот подтвердит его после индексации. Без TONAPI_KEY нужна ручная проверка.",
            }
        )

    async with session_scope() as session:
        await session.execute(
            text(
                """
                UPDATE miniapp_deposits
                SET status='paid', tx_hash=:tx, paid_at=NOW()
                WHERE id=:id AND status != 'paid'
                """
            ),
            {"id": deposit_id, "tx": tx_hash},
        )
        await session.execute(
            text("UPDATE users SET app_stars=COALESCE(app_stars,0)+:amount, last_seen_at=NOW() WHERE telegram_id=:tid"),
            {"amount": int(dep["stars_amount"] or 0), "tid": telegram_id},
        )
        await session.execute(
            text("INSERT INTO miniapp_transactions (telegram_id, kind, amount, payload) VALUES (:tid, 'ton_topup', :amount, :payload)"),
            {"tid": telegram_id, "amount": int(dep["stars_amount"] or 0), "payload": f"deposit:{deposit_id}:{tx_hash}"},
        )
    return _json({"ok": True, "status": "paid", "stars_added": int(dep["stars_amount"] or 0), "tx_hash": tx_hash})


async def gift_catalog(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    try:
        available = await bot.get_available_gifts()
    except Exception as exc:
        return _json({"ok": False, "error": "gifts_failed", "message": str(exc)}, 500)

    items = []
    for gift in getattr(available, "gifts", [])[:80]:
        sticker = getattr(gift, "sticker", None)
        file_id = getattr(sticker, "file_id", None) if sticker else None
        emoji = getattr(sticker, "emoji", None) if sticker else None
        items.append(
            {
                "id": str(getattr(gift, "id", "")),
                "star_count": int(getattr(gift, "star_count", 0) or 0),
                "total_count": getattr(gift, "total_count", None),
                "remaining_count": getattr(gift, "remaining_count", None),
                "emoji": emoji or "🎁",
                "is_animated": bool(getattr(sticker, "is_animated", False)) if sticker else False,
                "is_video": bool(getattr(sticker, "is_video", False)) if sticker else False,
                "sticker_file_id": file_id,
                "media_url": f"/api/gift-media/{file_id}" if file_id else None,
            }
        )
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
        if str(tg_file.file_path or "").endswith(".tgs"):
            ctype = "application/x-tgsticker"
        return web.Response(body=data, content_type=ctype, headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        return web.Response(status=404)


async def inventory(request: web.Request) -> web.Response:
    user_data, _ = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    telegram_id = int(user_data["id"])
    async with session_scope() as session:
        rows = (
            await session.execute(
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
            )
        ).mappings().all()
    return _json({"ok": True, "items": [dict(r) | {"created_at": str(r["created_at"])} for r in rows]})


async def play_demo(request: web.Request) -> web.Response:
    """Safe mini-game animation endpoint: no real wager, no cashout, no valuable random prize."""
    settings: Settings = request.app["settings"]
    user_data, payload = await _get_request_user(request)
    if not user_data:
        return _json({"ok": False, "error": "auth_failed"}, 401)
    telegram_id = int(user_data["id"])
    game = str(payload.get("game") or "plinko")[:32]
    seed = secrets.randbelow(10000)
    exp_added = 10 + seed % 25
    demo_points = seed % 100
    async with session_scope() as session:
        await session.execute(text("UPDATE users SET exp=COALESCE(exp,0)+:exp WHERE telegram_id=:tid"), {"tid": telegram_id, "exp": exp_added})
        await session.execute(
            text("INSERT INTO miniapp_transactions (telegram_id, kind, amount, payload) VALUES (:tid, 'demo_game', :amount, :payload)"),
            {"tid": telegram_id, "amount": exp_added, "payload": f"{game}:{demo_points}"},
        )
    return _json({"ok": True, "game": game, "demo_points": demo_points, "exp_added": exp_added, "note": "fan_demo_only"})


def setup_webapp_routes(app: web.Application, bot: Bot, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    app["bot"] = bot
    app["settings"] = settings

    app.router.add_get("/", index)
    app.router.add_get("/app", index)
    app.router.add_get("/app/", index)
    app.router.add_get("/tonconnect-manifest.json", ton_manifest)
    app.router.add_static("/app/static", STATIC_DIR, show_index=False)
    app.router.add_static("/static", STATIC_DIR, show_index=False)
    app.router.add_get("/api/health", health)
    app.router.add_post("/api/me", me)
    app.router.add_get("/api/winners", winners)
    app.router.add_get("/api/leaderboard", leaderboard)
    app.router.add_post("/api/daily", daily)
    app.router.add_post("/api/topup", topup_invoice)
    app.router.add_post("/api/ton/create", ton_create_deposit)
    app.router.add_post("/api/ton/confirm", ton_confirm_deposit)
    app.router.add_get("/api/gift-catalog", gift_catalog)
    app.router.add_get("/api/gift-media/{file_id}", gift_media)
    app.router.add_post("/api/inventory", inventory)
    app.router.add_post("/api/play/demo", play_demo)
