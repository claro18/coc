import json
import os
from typing import Any

HEROES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "static_data", "coc_heroes.json"
)
PETS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "static_data", "coc_pets.json"
)
LAB_TROOPS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "static_data", "coc_lab_troops.json"
)

_heroes_data: dict[str, Any] | None = None
_pets_data: dict[str, Any] | None = None
_lab_troops_data: dict[str, Any] | None = None


def _load_json(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def get_heroes_data() -> dict[str, Any]:
    global _heroes_data
    if _heroes_data is None:
        _heroes_data = _load_json(HEROES_PATH).get("heroes", {})
    return _heroes_data


def get_pets_data() -> tuple[int, dict[str, Any]]:
    global _pets_data
    if _pets_data is None:
        raw = _load_json(PETS_PATH)
        _pets_data = raw
    return _pets_data.get("pet_house_unlock_th", 14), _pets_data.get("pets", {})


def get_lab_troops_data() -> tuple[dict[str, Any], dict[str, Any]]:
    global _lab_troops_data
    if _lab_troops_data is None:
        _lab_troops_data = _load_json(LAB_TROOPS_PATH)
    return _lab_troops_data.get("troops", {}), _lab_troops_data.get("spells", {})


def get_visible_sections(town_hall: int) -> list[str]:
    sections = ["laboratory"]
    if town_hall >= 7:
        sections.append("heroes")
    pet_house_unlock_th, _ = get_pets_data()
    if town_hall >= pet_house_unlock_th:
        sections.append("pets")
    return sections


def get_available_heroes(town_hall: int) -> list[tuple[str, dict[str, Any]]]:
    heroes = get_heroes_data()
    return [
        (name, info) for name, info in heroes.items()
        if town_hall >= info.get("unlock_th", 99)
    ]


def get_available_pets(pet_house_level: int) -> list[tuple[str, dict[str, Any]]]:
    _, pets = get_pets_data()
    return [
        (name, info) for name, info in pets.items()
        if pet_house_level >= info.get("unlock_pet_house_level", 99)
    ]


def get_max_level_for_th(town_hall: int) -> dict[str, int]:
    troops, spells = get_lab_troops_data()
    result: dict[str, int] = {}
    for name, info in troops.items():
        result[name] = info.get("max_level_by_th", {}).get(str(town_hall), 0)
    for name, info in spells.items():
        result[name] = info.get("max_level_by_th", {}).get(str(town_hall), 0)
    return result


def get_hero_max_level_for_th(hero_name: str, town_hall: int) -> int:
    heroes = get_heroes_data()
    info = heroes.get(hero_name)
    if not info:
        return 0
    max_lvl = info.get("max_level", 0)
    unlock_th = info.get("unlock_th", 99)
    if town_hall < unlock_th:
        return 0
    return max_lvl
