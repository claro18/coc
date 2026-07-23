import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

bot_instance: "Bot | None" = None


async def main():
    global bot_instance
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment!")
        sys.exit(1)

    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    from database.connection import init_db
    from bot.handlers.start import start_router
    from bot.handlers.json_import import json_router
    from bot.handlers.admin import admin_router as bot_admin_router
    from bot.middleware import BanCheckMiddleware
    from bot.services.scheduler import (
        start_scheduler,
        load_pending_upgrades,
        stop_scheduler,
    )

    bot = bot_instance = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    dp.include_routers(start_router, json_router, bot_admin_router)

    await init_db()
    logger.info("Database initialized")

    start_scheduler()
    await load_pending_upgrades(bot)
    logger.info("Scheduler started with pending upgrades")

    await bot.delete_webhook()

    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    from web_app.routes import admin_router as web_admin_router

    main_app = FastAPI(title="Clash Tracker Bot")
    main_app.state.bot = bot
    main_app.include_router(web_admin_router)

    web_app_dir = os.path.join(os.path.dirname(__file__), "..", "web_app", "static")
    web_app_dir = os.path.normpath(web_app_dir)
    if os.path.isdir(web_app_dir):
        main_app.mount(
            "/static",
            StaticFiles(directory=web_app_dir),
            name="admin_static",
        )

    @main_app.get("/health")
    async def health():
        return {"status": "ok"}

    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")

    if WEBHOOK_URL:
        from fastapi import Request
        from fastapi.responses import JSONResponse

        webhook_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")

        @main_app.post(WEBHOOK_PATH)
        async def webhook(request: Request) -> JSONResponse:
            update_data = await request.json()
            await dp.feed_webhook_update(bot, update_data)
            return JSONResponse(content={"ok": True})

        PORT = int(os.getenv("PORT", 8000))
        config = uvicorn.Config(main_app, host="0.0.0.0", port=PORT, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        logger.info("Starting bot in polling mode")
        PORT = int(os.getenv("PORT", 8000))

        from threading import Thread

        def run_web():
            uvicorn.run(main_app, host="0.0.0.0", port=PORT, log_level="warning")

        t = Thread(target=run_web, daemon=True)
        t.start()

        try:
            await dp.start_polling(bot)
        finally:
            stop_scheduler()
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
