import datetime
import json as json_lib
import os
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from database.connection import async_session
from database.models import User, ActiveUpgrade
from bot.keyboards.inline import main_menu, help_keyboard, back_to_menu
from bot.services.calculator import (
    calculate_th_progress,
    make_progress_bar,
    format_duration,
    get_upgrade_time,
)
from bot.services.parser import get_next_builder_free

logger = logging.getLogger(__name__)

start_router = Router()

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]


async def build_status_text(user: User) -> tuple[str, bool]:
    async with async_session() as session:
        result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user.id,
                ActiveUpgrade.is_completed == False,
            )
        )
        active_upgrades = result.scalars().all()

    has_data = user.town_hall > 0

    if not has_data:
        text = (
            "🏰 <b>Welcome to Clash Tracker!</b>\n\n"
            "No village data imported yet.\n\n"
            "To get started:\n"
            "1. Open Clash of Clans\n"
            "2. Go to <b>Settings → More Settings → Data Export</b>\n"
            "3. Tap <b>Export Data</b> to download your village .json file\n"
            "4. Upload the .json file here\n\n"
            "The bot will parse your village and start tracking upgrades automatically!"
        )
        return text, has_data

    buildings = json_lib.loads(user.buildings_snapshot) if user.buildings_snapshot else []
    progress = calculate_th_progress(user.town_hall, buildings)
    bar = make_progress_bar(progress)

    busy_builders = len(active_upgrades)
    free_builders = max(0, user.total_builders - busy_builders)

    now = datetime.datetime.utcnow()

    home_active = [u for u in active_upgrades if u.village == "home"]
    bb_active = [u for u in active_upgrades if u.village == "builder_base"]

    next_free = ""
    if active_upgrades:
        earliest = min(active_upgrades, key=lambda u: u.end_time)
        remaining = int((earliest.end_time.replace(tzinfo=None) - now).total_seconds())
        if remaining > 0:
            village_icon = "🏰" if earliest.village == "home" else "🏗️"
            next_free = (
                f"⏳ Next Builder Free in: <b>{format_duration(remaining)}</b> "
                f"({village_icon} {earliest.building_name} Lvl {earliest.target_level})"
            )
        else:
            next_free = "⏳ Some upgrades completing shortly..."

    lines = [f"🏰 <b>Town Hall Level: {user.town_hall}</b>"]
    if home_active or bb_active:
        lines.append(f"📊 TH Progress: <b>{bar} {progress:.1f}%</b>")
        lines.append(f"🔨 Active Builders: <b>{free_builders}/{user.total_builders}</b> Free")
        if home_active:
            lines.append(f"── 🏰 Town Hall: {len(home_active)} upgrade(s)")
        if bb_active:
            lines.append(f"── 🏗️ Builder Base: {len(bb_active)} upgrade(s)")
    else:
        lines.append(f"📊 TH Progress: <b>{bar} {progress:.1f}%</b>")
        lines.append(f"🔨 Active Builders: <b>{free_builders}/{user.total_builders}</b> Free")
    lines.append("")
    lines.append(next_free)
    lines.append("")
    lines.append("Use the buttons below to manage your village tracking.")
    text = "\n".join(lines).strip()
    return text, has_data


@start_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                id=user_id,
                username=username,
                created_at=datetime.datetime.utcnow(),
            )
            session.add(user)
            await session.commit()

    text, has_data = await build_status_text(user)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(user_id, ADMIN_IDS),
    )


@start_router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    user_id = message.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            await cmd_start(message)
            return

    text, has_data = await build_status_text(user)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(user_id, ADMIN_IDS),
    )


@start_router.callback_query(F.data == "menu:main")
async def callback_main_menu(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            await callback.message.edit_text("Please use /start first.")
            await callback.answer()
            return

    text, has_data = await build_status_text(user)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(user_id, ADMIN_IDS),
    )
    await callback.answer()


@start_router.callback_query(F.data == "menu:help")
async def callback_help(callback: CallbackQuery) -> None:
    text = (
        "⚙️ <b>How to Export Your Village Data</b>\n\n"
        "1. Open <b>Clash of Clans</b>\n"
        "2. Go to <b>Settings</b> (gear icon)\n"
        "3. Tap <b>More Settings</b>\n"
        "4. Scroll down to <b>Data Export</b>\n"
        "5. Tap <b>Export Data</b>\n"
        "6. Save the generated .json file\n"
        "7. Upload it here as a document\n\n"
        "The bot will automatically parse your village state and begin tracking all ongoing upgrades!\n\n"
        "🔄 <b>Refresh:</b> Upload a new .json file anytime to sync latest progress.\n"
        "🔔 <b>Notifications:</b> You'll be alerted when an upgrade completes."
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=help_keyboard(),
    )
    await callback.answer()


@start_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "⚙️ <b>How to Export Your Village Data</b>\n\n"
        "1. Open <b>Clash of Clans</b>\n"
        "2. Go to <b>Settings</b> (gear icon)\n"
        "3. Tap <b>More Settings</b>\n"
        "4. Scroll down to <b>Data Export</b>\n"
        "5. Tap <b>Export Data</b>\n"
        "6. Save the generated .json file\n"
        "7. Upload it here as a document\n\n"
        "The bot will automatically parse your village state and begin tracking all ongoing upgrades!\n\n"
        "🔄 <b>Refresh:</b> Upload a new .json file anytime to sync latest progress.\n"
        "🔔 <b>Notifications:</b> You'll be alerted when an upgrade completes."
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=help_keyboard(),
    )


@start_router.message(Command("import"))
async def cmd_import(message: Message) -> None:
    await message.answer(
        "📤 <b>Upload Your Village JSON</b>\n\n"
        "Please send your <b>.json</b> data export file as a document.\n\n"
        "How to get it:\n"
        "1. Open Clash of Clans\n"
        "2. <b>Settings → More Settings → Data Export</b>\n"
        "3. Tap <b>Export Data</b>\n"
        "4. Send the file here",
        parse_mode="HTML",
        reply_markup=back_to_menu(),
    )
