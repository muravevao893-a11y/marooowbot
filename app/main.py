# app/main.py
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db.session import create_db_schema
from app.handlers import admin, giveaways, start
from app.jobs.finish_giveaways import finish_due_giveaways


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


async def main() -> None:
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # ВАЖНО: сначала start/admin, потом giveaways.
    # Если giveaways не подключить, посты/комменты будут "not handled".
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(giveaways.router)

    await create_db_schema()

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        finish_due_giveaways,
        "interval",
        seconds=10,
        kwargs={"bot": bot, "settings": settings},
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    logging.info("Scheduler started")
    logging.info("Polling started")

    await bot.delete_webhook(drop_pending_updates=False)

    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "channel_post",
            "callback_query",
            "my_chat_member",
            "chat_member",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())