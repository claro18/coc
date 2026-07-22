import json
import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ParseResult:
    def __init__(self) -> None:
        self.town_hall: int = 0
        self.total_builders: int = 5
        self.free_builders: int = 5
        self.buildings: list[dict[str, Any]] = []
        self.upgrades: list[dict[str, Any]] = []


def validate_json_structure(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    return True


def normalize_key(key: str) -> str:
    replacements = {
        "townhalllevel": "town_hall_level",
        "townhall_level": "town_hall_level",
        "townhall": "town_hall_level",
        "freebuildercount": "free_builder_count",
        "freebuilder": "free_builder_count",
        "activebuildercount": "active_builder_count",
        "totalbuildercount": "total_builder_count",
        "totalbuilders": "total_builder_count",
        "buildingitems": "buildings",
        "buildingitem": "buildings",
        "upgradesinprogress": "upgrades",
        "upgradeinprogress": "upgrades",
    }
    return replacements.get(key.lower(), key)


def parse_export(file_bytes: bytes) -> ParseResult:
    result = ParseResult()
    try:
        data = json.loads(file_bytes)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise ValueError("Invalid JSON file")

    if not validate_json_structure(data):
        raise ValueError("Invalid export file structure")

    normalized = {normalize_key(k): v for k, v in data.items()}

    result.town_hall = int(normalized.get("town_hall_level", 0))
    result.total_builders = int(normalized.get("total_builder_count", 5))
    result.free_builders = int(normalized.get("free_builder_count", result.total_builders))

    buildings_raw = normalized.get("buildings", [])
    if buildings_raw and isinstance(buildings_raw, list):
        result.buildings = buildings_raw

    upgrades_raw = normalized.get("upgrades", [])
    parsed_upgrades: list[dict[str, Any]] = []

    for b in buildings_raw:
        if not isinstance(b, dict):
            continue
        is_upgrading = b.get("isUpgrading") or b.get("is_upgrading") or False
        if not is_upgrading:
            continue
        upgrade_info = b.get("upgrade") or {}
        target_level = (upgrade_info.get("targetLevel") or upgrade_info.get("target_level") or
                        b.get("targetLevel") or b.get("target_level") or b.get("level", 0) + 1)
        duration_remaining = (upgrade_info.get("durationSecondsRemaining") or
                              upgrade_info.get("duration_seconds_remaining") or
                              upgrade_info.get("remainingTime") or
                              upgrade_info.get("remaining_time") or 0)
        building_name = (b.get("name") or b.get("building_name") or f"Building #{b.get('id', '?')}")
        building_level = int(b.get("level") or b.get("building_level", 0))

        parsed_upgrades.append({
            "building_name": str(building_name),
            "building_level": building_level,
            "target_level": int(target_level),
            "duration_seconds_remaining": int(duration_remaining),
        })

    if upgrades_raw and isinstance(upgrades_raw, list):
        for u in upgrades_raw:
            if isinstance(u, dict):
                parsed_upgrades.append({
                    "building_name": str(u.get("building_name", u.get("name", "Unknown"))),
                    "building_level": int(u.get("building_level", u.get("level", 0))),
                    "target_level": int(u.get("target_level", u.get("targetLevel", 0))),
                    "duration_seconds_remaining": int(
                        u.get("duration_seconds_remaining", u.get("durationSecondsRemaining", 0))
                    ),
                })

    result.upgrades = parsed_upgrades
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
