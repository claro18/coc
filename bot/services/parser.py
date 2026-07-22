import json
import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)

BUILDING_NAMES: dict[int, str] = {
    1000000: "Town Hall",
    1000001: "Cannon",
    1000002: "Archer Tower",
    1000003: "Mortar",
    1000004: "Air Defense",
    1000005: "Wizard Tower",
    1000006: "Hidden Tesla",
    1000007: "Bomb Tower",
    1000008: "X-Bow",
    1000009: "Inferno Tower",
    1000010: "Walls",
    1000011: "Eagle Artillery",
    1000012: "Scattershot",
    1000013: "Spell Tower",
    1000014: "Monolith",
    1000015: "Builder's Hut",
    1000017: "Firespitter",
    1000018: "Ricochet Cannon",
    1000019: "Army Camp",
    1000020: "Laboratory",
    1000021: "Spell Factory",
    1000022: "Dark Spell Factory",
    1000023: "Dark Barracks",
    1000024: "Clan Castle",
    1000026: "Multi-Archer Tower",
    1000027: "Gold Mine",
    1000028: "Elixir Collector",
    1000029: "Dark Elixir Drill",
    1000030: "Barracks",
    1000031: "Gold Storage",
    1000032: "Elixir Storage",
    1000059: "Dark Elixir Storage",
    1000070: "Pet House",
    1000071: "Workshop",
}


class ParseResult:
    def __init__(self) -> None:
        self.town_hall: int = 0
        self.total_builders: int = 5
        self.free_builders: int = 5
        self.buildings: list[dict[str, Any]] = []
        self.upgrades: list[dict[str, Any]] = []


def _resolve_building_name(data_id: int) -> str:
    return BUILDING_NAMES.get(data_id, f"Building #{data_id}")


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

    town_hall_lvl = 0
    all_building_entries: list[dict[str, Any]] = []
    upgrades_found: list[dict[str, Any]] = []

    for b in home_buildings:
        if not isinstance(b, dict):
            continue
        data_id = b.get("data", 0)
        lvl = b.get("lvl", 0)
        cnt = b.get("cnt", 1)
        timer = b.get("timer")

        name = _resolve_building_name(data_id)

        if data_id == 1000000:
            town_hall_lvl = max(town_hall_lvl, lvl)

        if timer is not None:
            upgrades_found.append({
                "building_name": name,
                "building_level": lvl,
                "target_level": lvl + 1,
                "duration_seconds_remaining": int(timer),
                "data_id": data_id,
            })

        for _ in range(cnt):
            all_building_entries.append({
                "name": name,
                "level": lvl,
                "data_id": data_id,
            })

    bb_buildings: list[dict] = data.get("buildings2") or []
    if isinstance(bb_buildings, list):
        for b in bb_buildings:
            if not isinstance(b, dict):
                continue
            data_id = b.get("data", 0)
            lvl = b.get("lvl", 0)
            cnt = b.get("cnt", 1)
            timer = b.get("timer")
            name = _resolve_building_name(data_id)

            if timer is not None:
                upgrades_found.append({
                    "building_name": f"{name} (BB)",
                    "building_level": lvl,
                    "target_level": lvl + 1,
                    "duration_seconds_remaining": int(timer),
                    "data_id": data_id,
                })

            for _ in range(cnt):
                all_building_entries.append({
                    "name": f"{name} (BB)" if BUILDING_NAMES.get(data_id) else name,
                    "level": lvl,
                    "data_id": data_id,
                })

    result.town_hall = town_hall_lvl
    result.buildings = all_building_entries
    result.upgrades = upgrades_found

    total_builders = data.get("totalBuilderCount") or data.get("total_builder_count")
    if total_builders is not None:
        result.total_builders = int(total_builders)

    free_builders = data.get("freeBuilderCount") or data.get("free_builder_count")
    if free_builders is not None:
        result.free_builders = int(free_builders)
    else:
        result.free_builders = result.total_builders - len(upgrades_found)

    logger.info(
        f"Parsed: TH={result.town_hall}, builders={result.free_builders}/{result.total_builders}, "
        f"buildings={len(all_building_entries)}, upgrades={len(upgrades_found)}"
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
