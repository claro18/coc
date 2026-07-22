import json
import math
import os
from typing import Any


def load_buildings_data() -> dict[str, Any]:
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "static_data", "coc_buildings.json"
    )
    with open(path, "r") as f:
        return json.load(f)["buildings"]


BUILDINGS_DATA = load_buildings_data()


def get_max_level_at_th(building_name: str, town_hall: int) -> int:
    data = BUILDINGS_DATA.get(building_name)
    if not data:
        return 0
    levels = data.get("levels", {})
    max_lvl = 0
    for lvl_str, info in levels.items():
        lvl = int(lvl_str)
        th_req = int(info.get("th", 1))
        if th_req <= town_hall and lvl > max_lvl:
            max_lvl = lvl
    return max_lvl


def get_upgrade_time(building_name: str, level: int) -> int:
    data = BUILDINGS_DATA.get(building_name)
    if not data:
        return 0
    lvl_info = data.get("levels", {}).get(str(level))
    if not lvl_info:
        return 0
    return int(lvl_info.get("upgrade_time_seconds", 0))


def calculate_th_progress(town_hall: int, buildings: list[dict]) -> float:
    if not buildings or town_hall == 0:
        return 0.0

    total_completed_time = 0.0
    total_possible_time = 0.0

    for b in buildings:
        name = b.get("name", "")
        level = int(b.get("level", 0) or b.get("building_level", 0))
        if not name or level <= 0:
            continue

        max_lvl = get_max_level_at_th(name, town_hall)
        if max_lvl <= 1:
            continue

        for lvl in range(1, max_lvl + 1):
            time_for_level = get_upgrade_time(name, lvl)
            if lvl <= level:
                total_completed_time += time_for_level
            total_possible_time += time_for_level

    if total_possible_time == 0:
        return 0.0

    return min(100.0, (total_completed_time / total_possible_time) * 100.0)


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours:02d}h")
    parts.append(f"{minutes:02d}m")

    return " ".join(parts)


def make_progress_bar(percent: float, width: int = 10) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = round(percent / 100.0 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def format_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "Complete!"
    return format_duration(seconds)
