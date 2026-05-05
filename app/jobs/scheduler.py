from __future__ import annotations

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.services.manual_finish import finish_due_giveaways


def init_scheduler(bot: Bot, settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone='UTC')
    scheduler.add_job(
        finish_due_giveaways,
        'interval',
        seconds=10,
        kwargs={'bot': bot, 'settings': settings},
        max_instances=1,
        coalesce=True,
    )
    return scheduler
