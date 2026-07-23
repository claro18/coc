import datetime
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from sqlalchemy import select

from database.connection import async_session
from database.models import User, BotSetting

logger = logging.getLogger(__name__)

ADMIN_IDS_RAW = __import__("os").getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]


async def _get_maintenance() -> dict | None:
    async with async_session() as session:
        result = await session.execute(
            select(BotSetting).where(BotSetting.key == "maintenance_mode")
        )
        setting = result.scalar_one_or_none()
    if setting and setting.value:
        import json
        return json.loads(setting.value)
    return None


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user:
                user.last_seen = datetime.datetime.utcnow()

                if user.is_banned:
                    await session.commit()
                    msg = user.ban_reason or "You have been banned from using this bot."
                    if isinstance(event, Message):
                        await event.answer(f"\u26d4 {msg}")
                    elif isinstance(event, CallbackQuery):
                        await event.answer(msg, show_alert=True)
                    return

                await session.commit()

        maintenance = await _get_maintenance()
        if maintenance and maintenance.get("enabled") and user_id not in ADMIN_IDS:
            msg = maintenance.get("message", "Bot is under maintenance. Please try again later.")
            if isinstance(event, Message):
                await event.answer(f"\U0001f6a7 {msg}")
            elif isinstance(event, CallbackQuery):
                await event.answer(f"\U0001f6a7 {msg}", show_alert=True)
            return

        return await handler(event, data)
