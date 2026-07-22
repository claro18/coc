import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ActiveUpgrade, User
from database.connection import async_session

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})


async def send_upgrade_notification(
    bot: Bot, user_id: int, building_name: str, target_level: int, builder_index: int
) -> None:
    text = (
        f"🔔 <b>Upgrade Completed!</b>\n\n"
        f"Your <b>{building_name} (Level {target_level})</b> upgrade is finished!\n"
        f"Builder #{builder_index} is now free."
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
    target_level: int, builder_index: int, end_time: datetime.datetime
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
        args=[bot, user_id, building_name, target_level, builder_index],
        id=job_id,
        replace_existing=True,
        name=f"{building_name} Lvl {target_level} for user {user_id}",
    )
    logger.info(
        f"Scheduled notification for {building_name} Lvl {target_level} "
        f"(user {user_id}) at {run_time}"
    )


async def remove_upgrade_job(user_id: int, upgrade_id: int) -> None:
    job_id = f"upgrade_{user_id}_{upgrade_id}"
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
            upgrade.target_level, upgrade.builder_index, upgrade.end_time
        )
        count += 1

    logger.info(f"Loaded {count} pending upgrade jobs")


def get_active_job_count() -> int:
    return len(scheduler.get_jobs())


def start_scheduler():
    scheduler.start()
    logger.info("APScheduler started")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")
