import datetime
import io
import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Document
from sqlalchemy import select

from database.connection import async_session
from database.models import User, ActiveUpgrade
from bot.keyboards.inline import main_menu, refresh_prompt, back_to_menu
from bot.services.parser import parse_export, get_next_builder_free, ParseResult, TOWN_HALL_DATA_ID
from bot.services.calculator import (
    calculate_th_progress,
    make_progress_bar,
    format_duration,
)
from bot.services.scheduler import schedule_upgrade, remove_upgrade_job

logger = logging.getLogger(__name__)

json_router = Router()

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]


@json_router.message(F.document)
async def handle_document(message: Message) -> None:
    document: Document = message.document
    if not document.file_name or not document.file_name.lower().endswith(".json"):
        await message.reply(
            "❌ Please upload a valid <b>.json</b> file exported from Clash of Clans.\n\n"
            "Use <b>Settings → More Settings → Data Export</b> in the game.",
            parse_mode="HTML",
        )
        return

    processing_msg = await message.reply("⏳ Processing your village data...")

    try:
        file_bytes = await message.bot.download(document)
        if hasattr(file_bytes, "read"):
            file_bytes = file_bytes.read()
        elif isinstance(file_bytes, io.IOBase):
            file_bytes = file_bytes.read()
    except Exception as e:
        logger.error(f"Download error: {e}")
        await processing_msg.edit_text("❌ Failed to download file. Please try again.")
        return

    try:
        parsed: ParseResult = parse_export(file_bytes)
    except ValueError as e:
        await processing_msg.edit_text(f"❌ {e}\n\nPlease ensure you're uploading a valid CoC Data Export file.")
        return

    if parsed.town_hall == 0 and parsed.builder_hall == 0:
        logger.warning(
            f"Failed to parse town hall or builder hall from file. "
            f"User {message.from_user.id}, file {document.file_name}"
        )
        await processing_msg.edit_text(
            "❌ Could not detect Town Hall or Builder Hall in this file.\n\n"
            "Make sure you are uploading the correct JSON data export:\n"
            "Game Settings → More Settings → Data Export → Export Data\n\n"
            f"The file must contain a 'buildings' array with a Town Hall entry (data ID {TOWN_HALL_DATA_ID}).",
            reply_markup=back_to_menu(),
        )
        return

    user_id = message.from_user.id
    username = message.from_user.username
    now = datetime.datetime.utcnow()

    upgrade_count = len(parsed.upgrades)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                id=user_id,
                username=username,
                town_hall=parsed.town_hall,
                total_builders=parsed.total_builders,
                created_at=now,
                last_json_sync=now,
            )
            session.add(user)
        else:
            user.town_hall = parsed.town_hall
            user.total_builders = parsed.total_builders
            user.last_json_sync = now
            if username:
                user.username = username
        await session.commit()

        old_upg_result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            )
        )
        old_upgrades = old_upg_result.scalars().all()

        new_building_names = {
            (u["building_name"], u["target_level"]) for u in parsed.upgrades
        }

        for old_upg in old_upgrades:
            key = (old_upg.building_name, old_upg.target_level)
            if key not in new_building_names:
                old_upg.is_completed = True
                await remove_upgrade_job(user_id, old_upg.id)

        builder_index = 0
        new_upgrade_ids: list[int] = []
        for upg_data in parsed.upgrades:
            end_time = now + datetime.timedelta(
                seconds=upg_data["duration_seconds_remaining"]
            )
            new_upg = ActiveUpgrade(
                user_id=user_id,
                building_name=upg_data["building_name"],
                building_level=upg_data["building_level"],
                target_level=upg_data["target_level"],
                start_time=now,
                end_time=end_time,
                builder_index=builder_index,
            )
            session.add(new_upg)
            await session.flush()
            new_upgrade_ids.append(new_upg.id)
            builder_index += 1

        await session.commit()

    for idx, upg_data in enumerate(parsed.upgrades):
        if idx < len(new_upgrade_ids):
            end_time = now + datetime.timedelta(
                seconds=upg_data["duration_seconds_remaining"]
            )
            await schedule_upgrade(
                bot=message.bot,
                user_id=user_id,
                upgrade_id=new_upgrade_ids[idx],
                building_name=upg_data["building_name"],
                target_level=upg_data["target_level"],
                builder_index=idx,
                end_time=end_time,
            )

    progress = calculate_th_progress(parsed.town_hall, parsed.buildings)
    bar = make_progress_bar(progress)
    busy = len(parsed.upgrades)
    free = max(0, parsed.total_builders - busy)

    next_builder = get_next_builder_free(parsed.upgrades, now)
    next_free_text = ""
    if next_builder:
        next_free_text = (
            f"⏳ Next Builder Free: <b>{format_duration(next_builder['remaining_seconds'])}</b> "
            f"({next_builder['building_name']} Lvl {next_builder['target_level']})\n"
        )

    th_line = f"🏰 Town Hall Level: <b>{parsed.town_hall}</b>"
    if parsed.builder_hall:
        th_line += f"  |  🏗️ Builder Hall: <b>{parsed.builder_hall}</b>"

    summary = (
        f"✅ <b>Village Imported Successfully!</b>\n\n"
        f"{th_line}\n"
        f"📊 Progress: {bar} <b>{progress:.1f}%</b>\n"
        f"🔨 Builders: <b>{free}/{parsed.total_builders}</b> Free\n"
        f"📦 Upgrades Tracked: <b>{upgrade_count}</b>\n"
        f"{next_free_text}\n"
        f"You'll be notified as upgrades complete!"
    )

    await processing_msg.edit_text(
        summary,
        parse_mode="HTML",
        reply_markup=main_menu(user_id, ADMIN_IDS),
    )


@json_router.callback_query(F.data == "menu:refresh")
async def callback_refresh(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    now = datetime.datetime.utcnow()

    async with async_session() as session:
        result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            )
        )
        active = result.scalars().all()

        for upg in active:
            if upg.end_time.replace(tzinfo=None) <= now:
                upg.is_completed = True
                await remove_upgrade_job(user_id, upg.id)

        await session.commit()

    async with async_session() as session:
        result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            )
        )
        still_active = result.scalars().all()

    if not still_active:
        text = (
            "🔄 <b>Progress Refreshed</b>\n\n"
            "No active upgrades remaining.\n"
            "Upload a new .json file to track new upgrades!"
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=refresh_prompt(),
        )
    else:
        now = datetime.datetime.utcnow()
        earliest = min(still_active, key=lambda u: u.end_time)
        remaining = int(
            (earliest.end_time.replace(tzinfo=None) - now).total_seconds()
        )
        text = (
            "🔄 <b>Progress Refreshed</b>\n\n"
            f"⏳ <b>{len(still_active)}</b> upgrade(s) still in progress.\n"
            f"Next completion: <b>{format_duration(max(0, remaining))}</b>\n"
            f"({earliest.building_name} Lvl {earliest.target_level})\n\n"
            "Upload a new .json file to sync any newly started upgrades."
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=refresh_prompt(),
        )

    await callback.answer()


@json_router.callback_query(F.data == "menu:upload_prompt")
async def callback_upload_prompt(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
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
    await callback.answer()
