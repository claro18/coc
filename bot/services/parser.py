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


def _deep_get(data: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    for key in keys:
        parts = key.split(".")
        val = data
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = None
                break
        if val is not None:
            return val
    return default


def _find_key_case_insensitive(data: dict, target_key: str) -> Any:
    target_lower = target_key.lower()
    for k, v in data.items():
        if k.lower() == target_lower:
            return v
    return None


def _search_nested(obj: Any, target_key: str, depth: int = 0) -> Any:
    if depth > 3:
        return None
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == target_key.lower():
                return v
            result = _search_nested(v, target_key, depth + 1)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _search_nested(item, target_key, depth + 1)
            if result is not None:
                return result
    return None


def parse_export(file_bytes: bytes) -> ParseResult:
    result = ParseResult()

    try:
        text = file_bytes.decode("utf-8-sig")
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise ValueError("Invalid JSON file")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error: {e}")
        raise ValueError("Unreadable file encoding")

    if not isinstance(data, dict):
        raise ValueError("Invalid export file structure")

    logger.info(f"Top-level JSON keys: {list(data.keys())}")

    town_hall = _deep_get(
        data, "townHallLevel", "town_hall_level", "townhalllevel",
        "townHall", "town_hall", "thLevel", "th_level",
        default=None,
    )
    if town_hall is None:
        town_hall = _find_key_case_insensitive(data, "townHallLevel")
    if town_hall is None:
        town_hall = _search_nested(data, "townHallLevel")
    if town_hall is None:
        town_hall = _search_nested(data, "town_hall_level")
    if town_hall is not None:
        result.town_hall = int(town_hall)

    total_builders = _deep_get(
        data, "totalBuilderCount", "total_builder_count", "totalbuildercount",
        "totalBuilders", "total_builders", "totalBuilder",
        default=None,
    )
    if total_builders is not None:
        result.total_builders = int(total_builders)

    free_builders = _deep_get(
        data, "freeBuilderCount", "free_builder_count", "freebuildercount",
        "freeBuilders", "free_builders", "freeBuilder",
        default=None,
    )
    if free_builders is not None:
        result.free_builders = int(free_builders)
    else:
        result.free_builders = result.total_builders

    buildings_raw = _deep_get(
        data, "buildingItems", "building_items", "buildings",
        "buildingItem", "building_item", "items",
        default=[],
    )
    if isinstance(buildings_raw, list):
        result.buildings = buildings_raw
        logger.info(f"Found {len(buildings_raw)} buildings")
    else:
        logger.warning(f"No building list found, buildings_raw type: {type(buildings_raw)}")

    parsed_upgrades: list[dict[str, Any]] = []

    for b in result.buildings:
        if not isinstance(b, dict):
            continue

        is_upgrading = (
            b.get("isUpgrading") or b.get("is_upgrading") or
            b.get("isActive") or b.get("upgrading") or False
        )
        if not is_upgrading:
            continue

        upgrade_info = b.get("upgrade") or b.get("upgradeInfo") or b.get("upgrade_info") or {}

        target_level = (
            upgrade_info.get("targetLevel") or
            upgrade_info.get("target_level") or
            upgrade_info.get("target") or
            b.get("targetLevel") or
            b.get("target_level") or
            b.get("level", 0) + 1
        )

        duration_remaining = (
            upgrade_info.get("durationSecondsRemaining") or
            upgrade_info.get("duration_seconds_remaining") or
            upgrade_info.get("remainingTime") or
            upgrade_info.get("remaining_time") or
            upgrade_info.get("remainingSeconds") or
            b.get("upgradeRemainingTime") or
            b.get("upgrade_remaining_time") or
            0
        )

        building_name = (
            b.get("name") or b.get("buildingName") or b.get("building_name") or
            b.get("building") or f"Building #{b.get('id') or b.get('buildingId') or '?'}"
        )

        building_level = int(b.get("level") or b.get("buildingLevel") or b.get("building_level", 0))

        parsed_upgrades.append({
            "building_name": str(building_name),
            "building_level": building_level,
            "target_level": int(target_level),
            "duration_seconds_remaining": int(duration_remaining),
        })

    upgrades_raw = _deep_get(
        data, "upgradesInProgress", "upgrades_in_progress", "upgrades",
        "upgradeInProgress", "activeUpgrades", "active_upgrades",
        default=[],
    )
    if isinstance(upgrades_raw, list):
        for u in upgrades_raw:
            if isinstance(u, dict):
                parsed_upgrades.append({
                    "building_name": str(
                        u.get("name") or u.get("buildingName") or u.get("building_name") or
                        u.get("building") or "Unknown"
                    ),
                    "building_level": int(u.get("level") or u.get("buildingLevel") or u.get("building_level", 0)),
                    "target_level": int(
                        u.get("targetLevel") or u.get("target_level") or u.get("target") or 0
                    ),
                    "duration_seconds_remaining": int(
                        u.get("durationSecondsRemaining") or
                        u.get("duration_seconds_remaining") or
                        u.get("remainingTime") or u.get("remaining_time") or 0
                    ),
                })

    result.upgrades = parsed_upgrades
    logger.info(
        f"Parsed: TH={result.town_hall}, builders={result.free_builders}/{result.total_builders}, "
        f"upgrades={len(parsed_upgrades)}"
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
