from __future__ import annotations

import random
from datetime import timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select

from app.config import Settings
from app.db.models import DeliveryStatus, Giveaway, GiveawayEntry, GiveawayStatus, GiveawayType, GiveawayWinner, User
from app.db.session import session_scope
from app.keyboards import manual_giveaway_kb
from app.texts import manual_finished_text, manual_post_text
from app.utils.tg_html import user_link
from app.utils.time import utcnow


async def finish_due_giveaways(bot: Bot, settings: Settings) -> None:
    now = utcnow()
    async with session_scope() as session:
        result = await session.execute(
            select(Giveaway).where(
                Giveaway.type == GiveawayType.MANUAL,
                Giveaway.status == GiveawayStatus.ACTIVE,
                Giveaway.ends_at <= now,
            )
        )
        giveaways = list(result.scalars().all())

        for giveaway in giveaways:
            entries = (await session.execute(select(GiveawayEntry).where(GiveawayEntry.giveaway_id == giveaway.id))).scalars().all()
            count = len(entries)
            winners = random.sample(entries, min(giveaway.winners_count, count)) if entries else []
            links: list[str] = []
            for entry in winners:
                user = await session.get(User, entry.user_id)
                if not user:
                    continue
                winner = GiveawayWinner(
                    giveaway_id=giveaway.id,
                    user_id=user.id,
                    telegram_id=user.telegram_id,
                    prize_name=giveaway.prize_name,
                    gift_id=giveaway.gift_id,
                    delivery_status=DeliveryStatus.PENDING,
                )
                session.add(winner)
                user.wins_count += 1
                links.append(user_link(user.telegram_id, user.first_name, user.username))

            giveaway.status = GiveawayStatus.FINISHED
            text = manual_finished_text(giveaway.title, giveaway.prize_name, count, links)
            try:
                if giveaway.channel_id and giveaway.channel_message_id:
                    await bot.send_message(chat_id=giveaway.channel_id, text=text)
            except Exception:
                pass


async def restore_active_giveaways() -> None:
    # Placeholder kept for compatibility; APScheduler polls due giveaways every 10 sec.
    return None


def init_scheduler(bot: Bot, settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        finish_due_giveaways,
        "interval",
        seconds=10,
        kwargs={"bot": bot, "settings": settings},
        max_instances=1,
        coalesce=True,
    )
    return scheduler
