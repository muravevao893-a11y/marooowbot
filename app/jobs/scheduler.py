from __future__ import annotations

import random
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update

from app.config import Settings
from app.db.models import DeliveryStatus, Giveaway, GiveawayEntry, GiveawayStatus, GiveawayType, GiveawayWinner, User
from app.db.session import session_scope
from app.services.gift_service import send_gift_to_winner
from app.texts import manual_finished_text
from app.utils.tg_html import user_link
from app.utils.time import utcnow

log = logging.getLogger(__name__)


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
            claimed = await session.scalar(
                update(Giveaway)
                .where(Giveaway.id == giveaway.id, Giveaway.status == GiveawayStatus.ACTIVE)
                .values(status=GiveawayStatus.FINISHED)
                .returning(Giveaway.id)
            )
            if not claimed:
                continue

            entries = (await session.execute(select(GiveawayEntry).where(GiveawayEntry.giveaway_id == giveaway.id))).scalars().all()
            count = len(entries)
            existing_winner = await session.scalar(
                select(GiveawayWinner).where(GiveawayWinner.giveaway_id == giveaway.id).order_by(GiveawayWinner.id).limit(1)
            )
            links: list[str] = []

            if existing_winner:
                user = await session.get(User, existing_winner.user_id)
                if user:
                    if existing_winner.delivery_status != DeliveryStatus.SENT:
                        existing_winner.gift_id = existing_winner.gift_id or giveaway.gift_id or settings.auto_drop_gift_id
                        await send_gift_to_winner(bot, settings, existing_winner)
                    links.append(user_link(user.telegram_id, user.first_name, user.username))
            elif entries:
                entry = random.choice(entries)
                user = await session.get(User, entry.user_id)
                if user:
                    gift_id = giveaway.gift_id or settings.auto_drop_gift_id
                    giveaway.gift_id = gift_id
                    giveaway.winners_count = 1

                    user.wins_count += 1
                    winner = GiveawayWinner(
                        giveaway_id=giveaway.id,
                        user_id=user.id,
                        telegram_id=user.telegram_id,
                        prize_name=giveaway.prize_name,
                        gift_id=gift_id,
                        delivery_status=DeliveryStatus.PENDING,
                    )
                    session.add(winner)
                    await session.flush()

                    await send_gift_to_winner(bot, settings, winner)
                    links.append(user_link(user.telegram_id, user.first_name, user.username))
                    log.info(
                        "MANUAL_GIVEAWAY_FINISHED giveaway_id=%s winner_id=%s delivery_status=%s",
                        giveaway.id,
                        winner.id,
                        winner.delivery_status,
                    )
                else:
                    log.warning("MANUAL_GIVEAWAY_WINNER_USER_MISSING giveaway_id=%s entry_id=%s", giveaway.id, entry.id)
            else:
                log.info("MANUAL_GIVEAWAY_FINISHED_NO_ENTRIES giveaway_id=%s", giveaway.id)

            text = manual_finished_text(giveaway.title, giveaway.prize_name, count, links)
            if giveaway.channel_id and giveaway.channel_message_id:
                try:
                    await bot.send_message(chat_id=giveaway.channel_id, text=text)
                except Exception as exc:
                    log.warning("MANUAL_GIVEAWAY_RESULT_SEND_FAILED giveaway_id=%s error=%r", giveaway.id, exc)

            duplicate_winners = (
                await session.execute(
                    select(GiveawayWinner).where(GiveawayWinner.giveaway_id == giveaway.id).order_by(GiveawayWinner.id).offset(1)
                )
            ).scalars().all()
            for duplicate in duplicate_winners:
                duplicate.delivery_status = DeliveryStatus.MANUAL_REQUIRED
                duplicate.delivery_error = "duplicate manual giveaway winner ignored"


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
