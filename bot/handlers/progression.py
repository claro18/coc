import datetime
import json as json_lib
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from database.connection import async_session
from database.models import User, ActiveUpgrade
from bot.keyboards.inline import progression_menu, back_to_menu
from bot.services.progression import (
    get_visible_sections,
    get_available_heroes,
    get_available_pets,
    get_hero_max_level_for_th,
)
from bot.services.calculator import format_duration

logger = logging.getLogger(__name__)

prog_router = Router()


def _find_level(buildings: list[dict], name: str) -> int:
    for b in buildings:
        if b.get("name") == name:
            return int(b.get("level", 0))
    return 0


@prog_router.callback_query(F.data == "prog:menu")
async def callback_prog_menu(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if not user or user.town_hall == 0:
        await callback.message.edit_text(
            "Please upload your village data first.",
            reply_markup=back_to_menu(),
        )
        await callback.answer()
        return

    sections = get_visible_sections(user.town_hall)
    lines = [f"📈 <b>Progression — Town Hall {user.town_hall}</b>\n"]
    for s in sections:
        if s == "laboratory":
            lines.append("🧪 <b>Laboratory</b> — Upgrade troops & spells")
        elif s == "heroes":
            lines.append("🦸 <b>Heroes</b> — Level up your heroes")
        elif s == "pets":
            lines.append("🐾 <b>Pets</b> — Train your loyal companions")
    lines.append("\nChoose a section below:")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=progression_menu(user.town_hall),
    )
    await callback.answer()


@prog_router.callback_query(F.data == "prog:lab")
async def callback_lab(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if not user or user.town_hall == 0:
        await callback.message.edit_text(
            "Please upload your village data first.",
            reply_markup=back_to_menu(),
        )
        await callback.answer()
        return

    buildings = json_lib.loads(user.buildings_snapshot) if user.buildings_snapshot else []
    lab_level = _find_level(buildings, "Laboratory")

    from bot.services.progression import get_lab_troops_data
    troops, spells = get_lab_troops_data()

    lines = [f"🧪 <b>Laboratory — Town Hall {user.town_hall}</b>"]
    if lab_level:
        lines.append(f"🔬 Lab Level: <b>{lab_level}</b>")
    lines.append("")

    troop_lines: list[str] = []
    spell_lines: list[str] = []
    now = datetime.datetime.utcnow()

    async with async_session() as session:
        upg_result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            )
        )
        active_upgs = upg_result.scalars().all()
    active_names = {u.building_name for u in active_upgs}

    for name, info in troops.items():
        max_lvl = info.get("max_level_by_th", {}).get(str(user.town_hall), 0)
        if max_lvl == 0:
            continue
        current = _find_level(buildings, name)
        if current >= max_lvl:
            troop_lines.append(f"  ✅ <b>{name}</b> — maxed (Lvl {max_lvl})")
        elif current > 0:
            remaining = ""
            if f"Lab: {name}" in active_names:
                for u in active_upgs:
                    if u.building_name == f"Lab: {name}":
                        secs = int((u.end_time.replace(tzinfo=None) - now).total_seconds())
                        remaining = f" ({format_duration(max(0, secs))} left)"
                        break
            troop_lines.append(f"  ⚔️ <b>{name}</b> — Lvl {current} → {max_lvl}{remaining}")
        else:
            troop_lines.append(f"  ⚔️ <b>{name}</b> — Lvl 0 → {max_lvl} (not started)")

    for name, info in spells.items():
        max_lvl = info.get("max_level_by_th", {}).get(str(user.town_hall), 0)
        if max_lvl == 0:
            continue
        current = _find_level(buildings, name)
        if current >= max_lvl:
            spell_lines.append(f"  ✅ <b>{name}</b> — maxed (Lvl {max_lvl})")
        elif current > 0:
            remaining = ""
            if f"Lab: {name}" in active_names:
                for u in active_upgs:
                    if u.building_name == f"Lab: {name}":
                        secs = int((u.end_time.replace(tzinfo=None) - now).total_seconds())
                        remaining = f" ({format_duration(max(0, secs))} left)"
                        break
            spell_lines.append(f"  ✨ <b>{name}</b> — Lvl {current} → {max_lvl}{remaining}")
        else:
            spell_lines.append(f"  ✨ <b>{name}</b> — Lvl 0 → {max_lvl} (not started)")

    if troop_lines:
        lines.append("─ <b>Troops</b> ─")
        lines.extend(troop_lines)
        lines.append("")
    if spell_lines:
        lines.append("─ <b>Spells</b> ─")
        lines.extend(spell_lines)
        lines.append("")

    if not troop_lines and not spell_lines:
        lines.append("No Laboratory upgrades available at your Town Hall.")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=progression_menu(user.town_hall),
    )
    await callback.answer()


@prog_router.callback_query(F.data == "prog:heroes")
async def callback_heroes(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if not user or user.town_hall == 0:
        await callback.message.edit_text(
            "Please upload your village data first.",
            reply_markup=back_to_menu(),
        )
        await callback.answer()
        return

    buildings = json_lib.loads(user.buildings_snapshot) if user.buildings_snapshot else []
    hero_hall_level = _find_level(buildings, "Hero Hall")
    available = get_available_heroes(user.town_hall)

    now = datetime.datetime.utcnow()

    async with async_session() as session:
        upg_result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            )
        )
        active_upgs = upg_result.scalars().all()
    active_names = {u.building_name for u in active_upgs}

    lines = [f"🦸 <b>Heroes — Town Hall {user.town_hall}</b>"]
    if hero_hall_level:
        lines.append(f"🏛️ Hero Hall Level: <b>{hero_hall_level}</b>")
    lines.append("")

    if not available:
        lines.append("No heroes available at your Town Hall yet.")
    else:
        for name, info in available:
            max_lvl = get_hero_max_level_for_th(name, user.town_hall)
            current = _find_level(buildings, name)
            remaining = ""
            if name in active_names:
                for u in active_upgs:
                    if u.building_name == name:
                        secs = int((u.end_time.replace(tzinfo=None) - now).total_seconds())
                        remaining = f" ({format_duration(max(0, secs))} left)"
                        break
            if current >= max_lvl:
                lines.append(f"  ✅ <b>{name}</b> — maxed (Lvl {max_lvl})")
            elif current > 0:
                lines.append(f"  ⬆️ <b>{name}</b> — Lvl {current} → {max_lvl}{remaining}")
            else:
                lines.append(f"  ⬆️ <b>{name}</b> — Lvl 0 → {max_lvl} (not started)")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=progression_menu(user.town_hall),
    )
    await callback.answer()


@prog_router.callback_query(F.data == "prog:pets")
async def callback_pets(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if not user or user.town_hall == 0:
        await callback.message.edit_text(
            "Please upload your village data first.",
            reply_markup=back_to_menu(),
        )
        await callback.answer()
        return

    buildings = json_lib.loads(user.buildings_snapshot) if user.buildings_snapshot else []
    pet_house_level = _find_level(buildings, "Pet House")
    available = get_available_pets(pet_house_level) if pet_house_level > 0 else []

    now = datetime.datetime.utcnow()

    async with async_session() as session:
        upg_result = await session.execute(
            select(ActiveUpgrade).where(
                ActiveUpgrade.user_id == user_id,
                ActiveUpgrade.is_completed == False,
            )
        )
        active_upgs = upg_result.scalars().all()
    active_names = {u.building_name for u in active_upgs}

    lines = [f"🐾 <b>Pets — Town Hall {user.town_hall}</b>"]
    if pet_house_level:
        lines.append(f"🏠 Pet House Level: <b>{pet_house_level}</b>")
    lines.append("")

    if not pet_house_level:
        lines.append("Pet House not found in your village (requires TH14+).")
    elif not available:
        lines.append("No pets available at your Pet House level.")
    else:
        for name, info in available:
            max_lvl = info.get("max_level", 0)
            current = _find_level(buildings, name)
            remaining = ""
            if name in active_names:
                for u in active_upgs:
                    if u.building_name == name:
                        secs = int((u.end_time.replace(tzinfo=None) - now).total_seconds())
                        remaining = f" ({format_duration(max(0, secs))} left)"
                        break
            if current >= max_lvl:
                lines.append(f"  ✅ <b>{name}</b> — maxed (Lvl {max_lvl})")
            elif current > 0:
                lines.append(f"  🐕 <b>{name}</b> — Lvl {current} → {max_lvl}{remaining}")
            else:
                unlock_lvl = info.get("unlock_pet_house_level", 0)
                status = "(not started)"
                if pet_house_level < unlock_lvl:
                    status = f"(unlocks at Pet House Lvl {unlock_lvl})"
                lines.append(f"  🐕 <b>{name}</b> — Lvl 0 → {max_lvl} {status}")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=progression_menu(user.town_hall),
    )
    await callback.answer()
