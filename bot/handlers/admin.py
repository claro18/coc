import datetime
import json as json_lib
import os
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
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


async def _upgrades_content(user_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.town_hall == 0:
            return None

        result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            ).order_by(ActiveUpgrade.end_time.asc())
        )
        active = result.scalars().all()

    from bot.services.calculator import format_duration
    from bot.services.parser import (
        HOME_TROOP_NAMES, HOME_SPELL_NAMES, HOME_SIEGE_MACHINE_NAMES,
        HOME_HERO_NAMES, HOME_PET_NAMES,
        BB_TROOP_NAMES, BB_HERO_NAMES,
    )

    HOME_LAB_NAMES = (
        set(HOME_TROOP_NAMES.values())
        | set(HOME_SPELL_NAMES.values())
        | set(HOME_SIEGE_MACHINE_NAMES.values())
    )
    HOME_HERO_NAMES_SET = set(HOME_HERO_NAMES.values())
    HOME_PET_NAMES_SET = set(HOME_PET_NAMES.values())
    BB_LAB_NAMES = set(BB_TROOP_NAMES.values())
    BB_HERO_NAMES_SET = set(BB_HERO_NAMES.values())

    now = datetime.datetime.utcnow()
    buildings = json_lib.loads(user.buildings_snapshot) if user.buildings_snapshot else []

    def find_building(name: str, village: str = "home") -> int | None:
        for b in buildings:
            if b["name"] == name and b.get("village", "home") == village:
                return b["level"]
        return None

    def cat(name: str, village: str) -> str:
        if village == "home":
            if name in HOME_LAB_NAMES: return "lab"
            if name in HOME_HERO_NAMES_SET: return "heroes"
            if name in HOME_PET_NAMES_SET: return "pets"
            return "buildings"
        if name in BB_LAB_NAMES: return "lab"
        if name in BB_HERO_NAMES_SET: return "heroes"
        return "buildings"

    def fmt(upg, num=None):
        remaining = int((upg.end_time.replace(tzinfo=None) - now).total_seconds())
        ts = format_duration(remaining) if remaining > 0 else "Completing..."
        if num is not None:
            return f"  👷 Builder #{num}: <b>{upg.building_name}</b> \u2192 Lvl {upg.target_level} ({ts})"
        return f"  🔬 <b>{upg.building_name}</b> \u2192 Lvl {upg.target_level} ({ts})"

    if not active:
        return "📋 <b>Upgrades</b>\n\nNo upgrades in progress.\nAll builders are free!", back_to_menu()

    lines = ["📋 <b>Upgrades</b>\n"]
    builder_counter = 0

    home_upgs = [u for u in active if u.village == "home"]
    if home_upgs:
        lines.append("── 🏰 Town Hall ──\n")
        h_build = [u for u in home_upgs if cat(u.building_name, "home") == "buildings"]
        h_lab   = [u for u in home_upgs if cat(u.building_name, "home") == "lab"]
        h_hero  = [u for u in home_upgs if cat(u.building_name, "home") == "heroes"]
        h_pet   = [u for u in home_upgs if cat(u.building_name, "home") == "pets"]

        if h_build:
            lines.append("🏛️ <b>Buildings:</b>")
            for u in h_build:
                builder_counter += 1
                lines.append(fmt(u, builder_counter))
            lines.append("")

        lab_level = find_building("Laboratory")
        if lab_level is not None:
            lines.append("🧪 <b>Laboratory</b>")
            if h_lab:
                for u in h_lab:
                    lines.append(fmt(u))
                lines.append("")
            else:
                lines.append(f"  🔬 Laboratory (Lvl {lab_level}) is free, you can start a research now.\n")

        if user.town_hall >= 7 and h_hero:
            lines.append("🦸 <b>Heroes:</b>")
            for u in h_hero:
                builder_counter += 1
                lines.append(fmt(u, builder_counter))
            lines.append("")

        if user.town_hall >= 14 and h_pet:
            lines.append("🐾 <b>Pets:</b>")
            for u in h_pet:
                builder_counter += 1
                lines.append(fmt(u, builder_counter))
            lines.append("")

    bb_upgs = [u for u in active if u.village == "builder_base"]
    if bb_upgs:
        lines.append("── 🏗️ Builder Base ──\n")
        bb_build = [u for u in bb_upgs if cat(u.building_name, "builder_base") == "buildings"]
        bb_lab   = [u for u in bb_upgs if cat(u.building_name, "builder_base") == "lab"]
        bb_hero  = [u for u in bb_upgs if cat(u.building_name, "builder_base") == "heroes"]

        if bb_build:
            lines.append("🏛️ <b>Buildings:</b>")
            for u in bb_build:
                builder_counter += 1
                lines.append(fmt(u, builder_counter))
            lines.append("")

        star_lab_level = find_building("Star Laboratory", "builder_base")
        if star_lab_level is not None:
            lines.append("🧪 <b>Star Laboratory</b>")
            if bb_lab:
                for u in bb_lab:
                    lines.append(fmt(u))
                lines.append("")
            else:
                lines.append(f"  🔬 Star Laboratory (Lvl {star_lab_level}) is free, you can start a research now.\n")

        if bb_hero:
            lines.append("🦸 <b>Heroes:</b>")
            for u in bb_hero:
                builder_counter += 1
                lines.append(fmt(u, builder_counter))
            lines.append("")

    text = "\n".join(lines).rstrip("\n")
    return text, back_to_menu()


async def _stats_content(user_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.town_hall == 0:
            return None

        result = await session.execute(
            select(ActiveUpgrade).where(ActiveUpgrade.user_id == user_id)
        )
        all_upgrades = result.scalars().all()

    total = len(all_upgrades)
    completed = sum(1 for u in all_upgrades if u.is_completed)
    active = total - completed

    buildings = json_lib.loads(user.buildings_snapshot) if user.buildings_snapshot else []
    progress = calculate_th_progress(user.town_hall, buildings)
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
    return text, back_to_menu()


async def _history_content(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
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
                f"✅ <b>{h.building_name}</b> \u2192 Lvl {h.target_level} "
                f"({completed_at})"
            )
        text = "\n".join(lines)

    return text, back_to_menu()


async def _admin_content(user_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
    if not is_admin(user_id):
        return None

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
    return text, admin_panel()


@admin_router.callback_query(F.data.in_({"menu:upgrades", "menu:builders"}))
async def callback_upgrades(callback: CallbackQuery) -> None:
    result = await _upgrades_content(callback.from_user.id)
    if result is None:
        await callback.answer("Please upload your village data first.", show_alert=True)
        return
    text, markup = result
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


@admin_router.message(Command("upgrades"))
async def cmd_upgrades(message: Message) -> None:
    result = await _upgrades_content(message.from_user.id)
    if result is None:
        await message.answer(
            "No village data found. Use /import to upload your JSON file.",
            reply_markup=back_to_menu(),
        )
        return
    text, markup = result
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@admin_router.callback_query(F.data == "menu:stats")
async def callback_stats(callback: CallbackQuery) -> None:
    result = await _stats_content(callback.from_user.id)
    if result is None:
        await callback.answer("No village data found. Upload a JSON file first.", show_alert=True)
        return
    text, markup = result
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


@admin_router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    result = await _stats_content(message.from_user.id)
    if result is None:
        await message.answer(
            "No village data found. Use /import to upload your JSON file.",
            reply_markup=back_to_menu(),
        )
        return
    text, markup = result
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@admin_router.callback_query(F.data == "menu:history")
async def callback_history(callback: CallbackQuery) -> None:
    text, markup = await _history_content(callback.from_user.id)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


@admin_router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    text, markup = await _history_content(message.from_user.id)
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@admin_router.callback_query(F.data == "admin:dashboard")
async def callback_admin_dashboard(callback: CallbackQuery) -> None:
    result = await _admin_content(callback.from_user.id)
    if result is None:
        await callback.answer("Access denied.", show_alert=True)
        return
    text, markup = result
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    result = await _admin_content(message.from_user.id)
    if result is None:
        await message.answer(
            "👑 <b>Admin Panel</b>\n\nAccess denied. You are not authorized.",
            parse_mode="HTML",
        )
        return
    text, markup = result
    await message.answer(text, parse_mode="HTML", reply_markup=markup)
