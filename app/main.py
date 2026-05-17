from __future__ import annotations

import asyncio
import logging
import re

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import get_settings
from app.db.session import create_db_schema
from app.handlers import admin, giveaways, payments, user, miniapp
from app.jobs.scheduler import init_scheduler, restore_active_giveaways
from app.webapp.server import setup_webapp_routes


async def _make_storage(redis_url: str):
    try:
        return RedisStorage.from_url(redis_url)
    except Exception:
        return MemoryStorage()


def _validate_bot_token(token: str) -> None:
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{30,}", token):
        raise RuntimeError(
            "BOT_TOKEN has invalid format. Put the real token from @BotFather, "
            "for example 1234567890:AA..."
        )


async def run_webhook(dp: Dispatcher, bot: Bot) -> None:
    settings = get_settings()
    assert settings.webhook_full_url is not None
    await bot.set_webhook(settings.webhook_full_url, drop_pending_updates=False)

    app = web.Application()
    setup_webapp_routes(app, bot, settings)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webapp_host, settings.webapp_port)
    await site.start()
    logging.info("Webhook started: %s", settings.webhook_full_url)
    await asyncio.Event().wait()


async def start_webapp_server(bot: Bot) -> web.AppRunner | None:
    settings = get_settings()
    if not settings.webapp_enabled:
        return None

    app = web.Application()
    setup_webapp_routes(app, bot, settings)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webapp_host, settings.webapp_port)
    await site.start()
    logging.info("Mini App server started on %s:%s", settings.webapp_host, settings.webapp_port)
    return runner


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty")
    _validate_bot_token(settings.bot_token)

    await create_db_schema()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = await _make_storage(settings.redis_url)
    dp = Dispatcher(storage=storage)
    scheduler = None
    webapp_runner = None

    try:
        me = await bot.get_me()
        logging.info("Telegram bot authorized as @%s", me.username)

        dp.include_router(user.router)
        dp.include_router(admin.router)
        dp.include_router(payments.router)
        dp.include_router(giveaways.router)
        dp.include_router(miniapp.router)

        if settings.webhook_full_url:
            scheduler = init_scheduler(bot, settings)
            scheduler.start()
            logging.info("Scheduler started")
            await restore_active_giveaways()
            await run_webhook(dp, bot)
        else:
            await bot.delete_webhook(drop_pending_updates=False)
            webapp_runner = await start_webapp_server(bot)
            scheduler = init_scheduler(bot, settings)
            scheduler.start()
            logging.info("Scheduler started")
            await restore_active_giveaways()
            logging.info("Polling started")
            await dp.start_polling(
                bot,
                allowed_updates=[
                    "message",
                    "channel_post",
                    "callback_query",
                    "pre_checkout_query",
                    "my_chat_member",
                    "chat_member",
                ],
            )
    except TelegramUnauthorizedError as exc:
        raise RuntimeError("Telegram rejected BOT_TOKEN. Check BOT_TOKEN in Railway/.env and paste the real @BotFather token.") from exc
    finally:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        if webapp_runner:
            await webapp_runner.cleanup()
        await bot.session.close()
        close_storage = getattr(storage, "close", None)
        if close_storage:
            await close_storage()


if __name__ == "__main__":
    asyncio.run(main())
