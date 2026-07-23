import datetime
import json
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from aiogram import Bot
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ActiveUpgrade, User, BroadcastMessage
from database.connection import async_session

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})


def _category_line(building_name: str) -> str:
    from bot.services.parser import (
        HOME_TROOP_NAMES, HOME_SPELL_NAMES, HOME_SIEGE_MACHINE_NAMES,
        HOME_HERO_NAMES, HOME_PET_NAMES,
        BB_HERO_NAMES,
    )
    all_lab = (
        set(HOME_TROOP_NAMES.values())
        | set(HOME_SPELL_NAMES.values())
        | set(HOME_SIEGE_MACHINE_NAMES.values())
    )
    all_heroes = set(HOME_HERO_NAMES.values()) | set(BB_HERO_NAMES.values())
    all_pets = set(HOME_PET_NAMES.values())
    if building_name in all_lab:
        return "🧪 Laboratory is now available for research!"
    if building_name in all_heroes:
        return "🦸 Hero is ready for the next upgrade!"
    if building_name in all_pets:
        return "🐾 Pet is ready for the next upgrade!"
    return "🔨 A builder is now free."


async def send_5min_warning(
    bot: Bot, user_id: int, building_name: str, target_level: int, village: str = "home"
) -> None:
    icon = "🏰" if village == "home" else "🏗️"
    text = (
        f"📋 <b>Upgrades</b>\n"
        f"⏰ <b>5 Minutes Remaining!</b>\n\n"
        f"{icon} <b>{building_name}</b> \u2192 Lvl {target_level}\n"
        f"Will be ready in about 5 minutes!"
    )
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send 5-min warning to user {user_id}: {e}")


async def send_upgrade_notification(
    bot: Bot, user_id: int, building_name: str, target_level: int,
    builder_index: int, village: str = "home"
) -> None:
    icon = "🏰" if village == "home" else "🏗️"
    cat = _category_line(building_name)
    text = (
        f"🔔 <b>Upgrade Complete!</b>\n\n"
        f"{icon} <b>{building_name}</b> reached Level <b>{target_level}</b>!\n"
        f"{cat}"
    )
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

    async with async_session() as session:
        result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.building_name == building_name,
                ActiveUpgrade.target_level == target_level,
                ActiveUpgrade.is_completed == False,
            ).order_by(ActiveUpgrade.end_time.desc())
        )
        upgrade = result.scalar_one_or_none()
        if upgrade:
            upgrade.is_completed = True
            await session.commit()


async def schedule_upgrade(
    bot: Bot, user_id: int, upgrade_id: int, building_name: str,
    target_level: int, builder_index: int, end_time: datetime.datetime,
    village: str = "home"
) -> None:
    now = datetime.datetime.utcnow()
    run_time = end_time.replace(tzinfo=None)
    if run_time <= now:
        logger.info(f"Upgrade {upgrade_id} already due, marking completed")
        async with async_session() as session:
            result = await session.execute(
                select(ActiveUpgrade).where(ActiveUpgrade.id == upgrade_id)
            )
            upgrade = result.scalar_one_or_none()
            if upgrade:
                upgrade.is_completed = True
                await session.commit()
        return

    job_id = f"upgrade_{user_id}_{upgrade_id}"
    scheduler.add_job(
        send_upgrade_notification,
        trigger="date",
        run_date=run_time,
        args=[bot, user_id, building_name, target_level, builder_index, village],
        id=job_id,
        replace_existing=True,
        name=f"{building_name} Lvl {target_level} for user {user_id}",
    )

    warning_time = run_time - datetime.timedelta(minutes=5)
    if warning_time > now:
        warning_job_id = f"warning_{user_id}_{upgrade_id}"
        scheduler.add_job(
            send_5min_warning,
            trigger="date",
            run_date=warning_time,
            args=[bot, user_id, building_name, target_level, village],
            id=warning_job_id,
            replace_existing=True,
            name=f"5min-warning {building_name} Lvl {target_level} for user {user_id}",
        )

    logger.info(
        f"Scheduled notification for {building_name} Lvl {target_level} "
        f"(user {user_id}) at {run_time}"
    )


async def remove_upgrade_job(user_id: int, upgrade_id: int) -> None:
    for prefix in ("upgrade_", "warning_"):
        job_id = f"{prefix}{user_id}_{upgrade_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)


async def load_pending_upgrades(bot: Bot) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(ActiveUpgrade).where(ActiveUpgrade.is_completed == False)
        )
        upgrades = result.scalars().all()

    now = datetime.datetime.utcnow()
    count = 0
    for upgrade in upgrades:
        end = upgrade.end_time.replace(tzinfo=None) if upgrade.end_time.tzinfo else upgrade.end_time
        if end <= now:
            async with async_session() as session:
                upg = await session.get(ActiveUpgrade, upgrade.id)
                if upg:
                    upg.is_completed = True
                    await session.commit()
            continue
        await schedule_upgrade(
            bot, upgrade.user_id, upgrade.id, upgrade.building_name,
            upgrade.target_level, upgrade.builder_index, upgrade.end_time,
            village=upgrade.village,
        )
        count += 1

    logger.info(f"Loaded {count} pending upgrade jobs")


def get_active_job_count() -> int:
    return len(scheduler.get_jobs())


async def process_pending_broadcasts(bot: Bot) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(BroadcastMessage).where(BroadcastMessage.status == "pending")
            .order_by(BroadcastMessage.created_at.asc())
            .limit(1)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return

        msg.status = "sending"
        await session.commit()

        user_result = await session.execute(
            select(User).where(User.is_banned == False)
        )
        users = user_result.scalars().all()

    sent = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(chat_id=user.id, text=msg.text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    async with async_session() as session:
        bm = await session.get(BroadcastMessage, msg.id)
        if bm:
            bm.status = "completed"
            bm.sent_count = sent
            bm.failed_count = failed
            bm.completed_at = datetime.datetime.utcnow()
            await session.commit()

    try:
        await bot.send_message(
            chat_id=msg.admin_id,
            text=f"\U0001f4e8 <b>Broadcast Complete</b>\n\n"
                 f"\u2705 Sent: <b>{sent}</b>\n"
                 f"\u274c Failed: <b>{failed}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    logger.info(f"Broadcast {msg.id}: sent={sent}, failed={failed}")


def start_scheduler():
    scheduler.add_job(
        process_pending_broadcasts,
        trigger="interval",
        seconds=10,
        id="process_broadcasts",
        replace_existing=True,
        name="Process pending broadcasts",
    )
    scheduler.start()
    logger.info("APScheduler started")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")
