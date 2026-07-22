import datetime
import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from database.connection import async_session
from database.models import User, ActiveUpgrade
from bot.keyboards.inline import main_menu, admin_panel, back_to_menu
from bot.services.scheduler import get_active_job_count
from bot.services.calculator import calculate_th_progress, make_progress_bar

logger = logging.getLogger(__name__)

admin_router = Router()

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

BOT_START_TIME = datetime.datetime.utcnow()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@admin_router.callback_query(F.data == "menu:builders")
async def callback_builders(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Please upload your village data first.", show_alert=True)
            return

        result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            ).order_by(ActiveUpgrade.end_time.asc())
        )
        active = result.scalars().all()

    now = datetime.datetime.utcnow()
    busy = len(active)
    free = max(0, user.total_builders - busy)

    if not active:
        text = (
            f"🔨 <b>Builder Status</b>\n\n"
            f"All <b>{user.total_builders}</b> builders are free!\n"
            f"No upgrades in progress."
        )
    else:
        lines = [f"🔨 <b>Builder Status</b>\n"]
        lines.append(f"Free: <b>{free}/{user.total_builders}</b>\n")
        for upg in active:
            remaining = int((upg.end_time.replace(tzinfo=None) - now).total_seconds())
            if remaining > 0:
                from bot.services.calculator import format_duration
                time_str = format_duration(remaining)
            else:
                time_str = "Completing..."
            lines.append(
                f"👷 Builder #{upg.builder_index + 1}: <b>{upg.building_name}</b> "
                f"→ Lvl {upg.target_level} ({time_str})"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "menu:stats")
async def callback_stats(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.town_hall == 0:
            await callback.answer("No village data found. Upload a JSON file first.", show_alert=True)
            return

        result = await session.execute(
            select(ActiveUpgrade).where(ActiveUpgrade.user_id == user_id)
        )
        all_upgrades = result.scalars().all()

    total = len(all_upgrades)
    completed = sum(1 for u in all_upgrades if u.is_completed)
    active = total - completed

    progress = calculate_th_progress(user.town_hall, [])
    bar = make_progress_bar(progress)

    last_sync = "Never"
    if user.last_json_sync:
        last_sync = user.last_json_sync.strftime("%Y-%m-%d %H:%M UTC")

    text = (
        f"📊 <b>Detailed Statistics</b>\n\n"
        f"🏰 Town Hall: <b>{user.town_hall}</b>\n"
        f"📈 Progress: {bar} <b>{progress:.1f}%</b>\n"
        f"🔨 Total Builders: <b>{user.total_builders}</b>\n"
        f"📦 Total Upgrades Tracked: <b>{total}</b>\n"
        f"✅ Completed: <b>{completed}</b>\n"
        f"🔄 Active: <b>{active}</b>\n"
        f"📅 Last Sync: <b>{last_sync}</b>\n"
        f"🆔 User ID: <code>{user.id}</code>"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "menu:history")
async def callback_history(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == True,
            ).order_by(ActiveUpgrade.end_time.desc()).limit(20)
        )
        history = result.scalars().all()

    if not history:
        text = (
            "📜 <b>Upgrade History</b>\n\n"
            "No completed upgrades yet.\n"
            "Upload a JSON file to start tracking!"
        )
    else:
        lines = ["📜 <b>Upgrade History (Last 20)</b>\n"]
        for h in history:
            completed_at = h.end_time.strftime("%m/%d %H:%M")
            lines.append(
                f"✅ <b>{h.building_name}</b> → Lvl {h.target_level} "
                f"({completed_at})"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin:dashboard")
async def callback_admin_dashboard(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("Access denied.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        total_users = result.scalar() or 0

        result = await session.execute(
            select(func.count(ActiveUpgrade.id)).where(
                ActiveUpgrade.is_completed == False
            )
        )
        active_upgrades = result.scalar() or 0

        result = await session.execute(
            select(func.count(ActiveUpgrade.id))
        )
        total_upgrades = result.scalar() or 0

    uptime = datetime.datetime.utcnow() - BOT_START_TIME
    uptime_str = str(uptime).split(".")[0]
    active_jobs = get_active_job_count()

    text = (
        f"👑 <b>Admin Dashboard</b>\n\n"
        f"📊 <b>Metrics</b>\n"
        f"👤 Total Users: <b>{total_users}</b>\n"
        f"🔄 Active Trackers: <b>{total_users}</b>\n"
        f"📦 Ongoing Upgrades: <b>{active_upgrades}</b>\n"
        f"📋 Total Upgrades: <b>{total_upgrades}</b>\n\n"
        f"⚙️ <b>System Health</b>\n"
        f"⏱ Uptime: <b>{uptime_str}</b>\n"
        f"📅 Scheduler Jobs: <b>{active_jobs}</b>\n"
        f"💾 Database: <b>Connected</b>\n\n"
        f"Use the Web App (button below) for the full dashboard."
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_panel(),
    )
    await callback.answer()
