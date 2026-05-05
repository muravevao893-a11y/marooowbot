from __future__ import annotations

import random
from typing import Sequence

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import DeliveryStatus, Giveaway, GiveawayEntry, GiveawayStatus, GiveawayType, GiveawayWinner, User
from app.db.session import session_scope
from app.services.gift_service import send_gift_to_user
from app.texts import finish_no_winners_text, finish_winners_text
from app.utils.time import utcnow


async def finish_due_giveaways(bot: Bot, settings: Settings) -> None:
    async with session_scope() as session:
        result = await session.execute(
            select(Giveaway)
            .where(
                Giveaway.type == GiveawayType.MANUAL.value,
                Giveaway.status == GiveawayStatus.ACTIVE.value,
                Giveaway.ends_at <= utcnow(),
            )
            .limit(10)
        )
        giveaways = list(result.scalars().all())

        for giveaway in giveaways:
            entries_result = await session.execute(
                select(GiveawayEntry)
                .options(selectinload(GiveawayEntry.user))
                .where(GiveawayEntry.giveaway_id == giveaway.id, GiveawayEntry.is_valid == True)  # noqa: E712
            )
            entries = [e for e in entries_result.scalars().all() if e.user and not e.user.is_banned and e.user.telegram_id not in settings.admin_ids]
            participants = len(entries)

            if participants < giveaway.min_participants or participants == 0:
                giveaway.status = GiveawayStatus.FINISHED.value
                if giveaway.channel_message_id:
                    await bot.send_message(settings.channel_id, finish_no_winners_text(giveaway.title, participants, giveaway.min_participants))
                continue

            selected = random.sample(entries, k=min(giveaway.winners_count, participants))
            winner_rows: list[tuple[int, str | None, str | None]] = []
            for entry in selected:
                winner = GiveawayWinner(
                    giveaway_id=giveaway.id,
                    user_id=entry.user_id,
                    gift_id=giveaway.gift_id,
                    delivery_status=DeliveryStatus.PENDING.value,
                )
                session.add(winner)
                entry.user.wins_count += 1
                await session.flush()
                await send_gift_to_user(bot, settings, winner, entry.user.telegram_id, giveaway.gift_id)
                winner_rows.append((entry.user.telegram_id, entry.user.username, entry.user.first_name))

            giveaway.status = GiveawayStatus.FINISHED.value
            if giveaway.channel_message_id:
                await bot.send_message(settings.channel_id, finish_winners_text(giveaway.title, giveaway.prize_name, participants, winner_rows))
