import json
import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)

BUILDING_NAMES: dict[int, str] = {
    1000000: "Army Camp",
    1000001: "Town Hall",
    1000002: "Elixir Collector",
    1000003: "Elixir Storage",
    1000004: "Gold Mine",
    1000005: "Gold Storage",
    1000006: "Barracks",
    1000007: "Laboratory",
    1000008: "Cannon",
    1000009: "Archer Tower",
    1000010: "Walls",
    1000011: "Wizard Tower",
    1000012: "Air Defense",
    1000013: "Mortar",
    1000014: "Clan Castle",
    1000015: "Builder's Hut",
    1000019: "Hidden Tesla",
    1000020: "Spell Factory",
    1000021: "X-Bow",
    1000023: "Dark Elixir Drill",
    1000024: "Dark Elixir Storage",
    1000026: "Dark Barracks",
    1000027: "Inferno Tower",
    1000028: "Air Sweeper",
    1000029: "Dark Spell Factory",
    1000031: "Eagle Artillery",
    1000032: "Bomb Tower",
    1000059: "Workshop",
    1000067: "Scattershot",
    1000068: "Pet House",
    1000070: "Blacksmith",
    1000071: "Hero Hall",
    1000072: "Spell Tower",
    1000077: "Monolith",
    1000079: "Multi-Gear Tower",
    1000084: "Multi-Archer Tower",
    1000085: "Ricochet Cannon",
    1000089: "Firespitter",
    1000093: "Helper Hut",
    1000097: "Crafted Defense",
}

HERO_NAMES: dict[int, str] = {
    28000000: "Barbarian King",
    28000001: "Archer Queen",
    28000002: "Grand Warden",
    28000004: "Royal Champion",
    28000006: "Minion Prince",
}

TOWN_HALL_DATA_ID = 1000001


class ParseResult:
    def __init__(self) -> None:
        self.tag: str = ""
        self.town_hall: int = 0
        self.total_builders: int = 5
        self.free_builders: int = 5
        self.buildings: list[dict[str, Any]] = []
        self.upgrades: list[dict[str, Any]] = []


def _resolve_building_name(data_id: int) -> str:
    return BUILDING_NAMES.get(data_id, HERO_NAMES.get(data_id, f"Building #{data_id}"))


def _parse_building_list(
    entries: list[dict],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    buildings: list[dict[str, Any]] = []
    upgrades: list[dict[str, Any]] = []
    town_hall_lvl = 0

    for b in entries:
        if not isinstance(b, dict):
            continue
        data_id = b.get("data", 0)
        lvl = b.get("lvl", 0)
        cnt = b.get("cnt", 1)
        timer = b.get("timer")

        name = _resolve_building_name(data_id)

        if data_id == TOWN_HALL_DATA_ID:
            town_hall_lvl = max(town_hall_lvl, lvl)

        if timer is not None:
            upgrades.append({
                "building_name": name,
                "building_level": lvl,
                "target_level": lvl + 1,
                "duration_seconds_remaining": int(timer),
                "data_id": data_id,
            })

        for _ in range(cnt):
            buildings.append({
                "name": name,
                "level": lvl,
                "data_id": data_id,
            })

    return buildings, upgrades, town_hall_lvl


def parse_export(file_bytes: bytes) -> ParseResult:
    result = ParseResult()

    try:
        text = file_bytes.decode("utf-8-sig")
        data = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Invalid JSON: {e}")
        raise ValueError("Invalid JSON file")

    if not isinstance(data, dict):
        raise ValueError("Invalid export file structure")

    logger.info(f"Top-level keys in export: {list(data.keys())}")

    result.tag = data.get("tag", "")

    home_buildings: list[dict] = data.get("buildings") or []
    if not isinstance(home_buildings, list):
        home_buildings = []

    bb_buildings: list[dict] = data.get("buildings2") or []
    if not isinstance(bb_buildings, list):
        bb_buildings = []

    main_buildings, main_upgrades, th_lvl = _parse_building_list(home_buildings)
    bb_buildings_list, bb_upgrades, _ = _parse_building_list(bb_buildings)

    for upg in bb_upgrades:
        upg["building_name"] = f"{upg['building_name']} (BB)"
    for b in bb_buildings_list:
        b["name"] = f"{b['name']} (BB)"

    result.town_hall = th_lvl
    result.buildings = main_buildings + bb_buildings_list
    result.upgrades = main_upgrades + bb_upgrades

    total_builders = data.get("totalBuilderCount") or data.get("total_builder_count")
    if total_builders is not None:
        result.total_builders = int(total_builders)

    free_builders = data.get("freeBuilderCount") or data.get("free_builder_count")
    if free_builders is not None:
        result.free_builders = int(free_builders)
    else:
        result.free_builders = result.total_builders - len(result.upgrades)

    logger.info(
        f"Parsed: TH={result.town_hall}, builders={result.free_builders}/{result.total_builders}, "
        f"buildings={len(result.buildings)}, upgrades={len(result.upgrades)}"
    )
    return result


def get_next_builder_free(upgrades: list[dict[str, Any]], imported_at: datetime.datetime) -> dict | None:
    if not upgrades:
        return None
    earliest = min(upgrades, key=lambda u: u["duration_seconds_remaining"])
    completion_time = imported_at + datetime.timedelta(
        seconds=earliest["duration_seconds_remaining"]
    )
    return {
        "building_name": earliest["building_name"],
        "target_level": earliest["target_level"],
        "completion_time": completion_time,
        "remaining_seconds": earliest["duration_seconds_remaining"],
    }
