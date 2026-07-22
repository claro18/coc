import json
import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)

# --- Home Village ---

HOME_DEFENSE_NAMES: dict[int, str] = {
    1000008: "Cannon",
    1000009: "Archer Tower",
    1000011: "Wizard Tower",
    1000012: "Air Defense",
    1000013: "Mortar",
    1000015: "Builder's Hut",
    1000019: "Hidden Tesla",
    1000021: "X-Bow",
    1000027: "Inferno Tower",
    1000028: "Air Sweeper",
    1000031: "Eagle Artillery",
    1000032: "Bomb Tower",
    1000067: "Scattershot",
    1000072: "Spell Tower",
    1000077: "Monolith",
    1000079: "Multi-Gear Tower",
    1000084: "Multi-Archer Tower",
    1000085: "Ricochet Cannon",
    1000086: "Revenge Tower",
    1000089: "Firespitter",
    1000097: "Crafting Station",
    1000102: "Super Wizard Tower",
}

HOME_ARMY_BUILDING_NAMES: dict[int, str] = {
    1000000: "Army Camp",
    1000006: "Barracks",
    1000007: "Laboratory",
    1000020: "Spell Factory",
    1000026: "Dark Barracks",
    1000029: "Dark Spell Factory",
    1000059: "Workshop",
    1000068: "Pet House",
    1000070: "Blacksmith",
    1000071: "Hero Hall",
}

HOME_RESOURCE_BUILDING_NAMES: dict[int, str] = {
    1000002: "Elixir Collector",
    1000003: "Elixir Storage",
    1000004: "Gold Mine",
    1000005: "Gold Storage",
    1000014: "Clan Castle",
    1000023: "Dark Elixir Drill",
    1000024: "Dark Elixir Storage",
}

HOME_TRAP_NAMES: dict[int, str] = {
    12000000: "Bomb",
    12000001: "Spring Trap",
    12000002: "Giant Bomb",
    12000005: "Air Bomb",
    12000006: "Seeking Air Mine",
    12000008: "Skeleton Trap",
    12000016: "Tornado Trap",
    12000020: "Giga Bomb",
}

HOME_WALL_NAMES: dict[int, str] = {
    1000010: "Walls",
}

HOME_HERO_NAMES: dict[int, str] = {
    28000000: "Barbarian King",
    28000001: "Archer Queen",
    28000002: "Grand Warden",
    28000004: "Royal Champion",
    28000006: "Minion Prince",
    28000007: "Dragon Duke",
}

HOME_TROOP_NAMES: dict[int, str] = {
    4000000: "Barbarian",
    4000001: "Archer",
    4000002: "Goblin",
    4000003: "Giant",
    4000004: "Wall Breaker",
    4000005: "Balloon",
    4000006: "Wizard",
    4000007: "Healer",
    4000008: "Dragon",
    4000009: "P.E.K.K.A",
    4000010: "Minion",
    4000011: "Hog Rider",
    4000012: "Valkyrie",
    4000013: "Golem",
    4000015: "Witch",
    4000017: "Lava Hound",
    4000022: "Bowler",
    4000023: "Baby Dragon",
    4000024: "Miner",
    4000053: "Yeti",
    4000058: "Ice Golem",
    4000059: "Electro Dragon",
    4000065: "Dragon Rider",
    4000082: "Headhunter",
    4000095: "Electro Titan",
    4000097: "Apprentice Warden",
    4000110: "Root Rider",
    4000123: "Druid",
    4000132: "Thrower",
    4000150: "Furnace",
    4000177: "Meteor Golem",
}

HOME_SPELL_NAMES: dict[int, str] = {
    26000000: "Lightning Spell",
    26000001: "Healing Spell",
    26000002: "Rage Spell",
    26000003: "Jump Spell",
    26000005: "Freeze Spell",
    26000009: "Poison Spell",
    26000010: "Earthquake Spell",
    26000011: "Haste Spell",
    26000016: "Clone Spell",
    26000017: "Skeleton Spell",
    26000028: "Bat Spell",
    26000035: "Invisibility Spell",
    26000053: "Recall Spell",
    26000070: "Overgrowth Spell",
    26000098: "Revive Spell",
    26000109: "Ice Block Spell",
    26000120: "Totem Spell",
}

HOME_SIEGE_MACHINE_NAMES: dict[int, str] = {
    4000051: "Wall Wrecker",
    4000052: "Battle Blimp",
    4000062: "Stone Slammer",
    4000075: "Siege Barracks",
    4000087: "Log Launcher",
    4000091: "Flame Flinger",
    4000092: "Battle Drill",
    4000135: "Troop Launcher",
}

HOME_PET_NAMES: dict[int, str] = {
    73000000: "L.A.S.S.I",
    73000001: "Mighty Yak",
    73000002: "Electro Owl",
    73000003: "Unicorn",
    73000004: "Phoenix",
    73000007: "Poison Lizard",
    73000008: "Diggy",
    73000009: "Frosty",
    73000010: "Spirit Fox",
    73000011: "Angry Jelly",
    73000016: "Sneezy",
    73000017: "Greedy Raven",
}

HOME_CRAFTED_DEFENSE_NAMES: dict[int, str] = {
    103000008: "Roaster",
    103000009: "Air Bombs",
    103000010: "Lava Launcher",
}

HOME_GUARDIAN_NAMES: dict[int, str] = {
    107000000: "Longshot",
    107000001: "Smasher",
}

HOME_HERO_EQUIPMENT_NAMES: dict[int, str] = {
    90000000: "Barbarian Puppet",
    90000001: "Rage Vial",
    90000002: "Archer Puppet",
    90000003: "Invisibility Vial",
    90000004: "Eternal Tome",
    90000005: "Life Gem",
    90000006: "Seeking Shield",
    90000007: "Royal Gem",
    90000008: "Earthquake Boots",
    90000009: "Hog Rider Puppet",
    90000010: "Giant Gauntlet",
    90000011: "Vampstache",
    90000012: "Haste Vial",
    90000013: "Rocket Spear",
    90000014: "Spiky Ball",
    90000015: "Frozen Arrow",
    90000017: "Giant Arrow",
    90000019: "Heroic Torch",
    90000020: "Healer Puppet",
    90000022: "Fireball",
    90000024: "Rage Gem",
    90000032: "Snake Bracelet",
    90000034: "Healing Tome",
    90000035: "Dark Crown",
    90000039: "Magic Mirror",
    90000040: "Electro Boots",
    90000041: "Lavaloon Puppet",
    90000042: "Henchmen Puppet",
    90000043: "Dark Orb",
    90000044: "Metal Pants",
    90000047: "Noble Iron",
    90000048: "Action Figure",
    90000049: "Meteor Staff",
    90000050: "Frost Flake",
    90000051: "Stick Horse",
    90000052: "Fire Heart",
    90000053: "Rocket Backpack",
    90000056: "Stun Blaster",
    90000057: "Flame Blower",
}

HOME_OTHER_NAMES: dict[int, str] = {
    1000001: "Town Hall",
    1000064: "B.O.B's Hut",
    1000093: "Helper Hut",
    93000000: "Builder's Apprentice",
    93000001: "Lab Assistant",
    93000002: "Prospector",
}

# --- Builder Base ---

BB_DEFENSE_NAMES: dict[int, str] = {
    1000041: "Double Cannon",
    1000043: "Hidden Tesla",
    1000044: "Cannon",
    1000045: "Multi Mortar",
    1000048: "Archer Tower",
    1000050: "Firecrackers",
    1000051: "Guard Post",
    1000052: "Mega Tesla",
    1000054: "Air Bombs",
    1000055: "Crusher",
    1000056: "Roaster",
    1000057: "Giant Cannon",
    1000063: "Lava Launcher",
    1000078: "O.T.T.O's Outpost",
    1000081: "X-Bow",
}

BB_ARMY_BUILDING_NAMES: dict[int, str] = {
    1000040: "Builder Barracks",
    1000042: "Army Camp",
    1000046: "Star Laboratory",
    1000049: "Reinforcement Camp",
    1000053: "Battle Machine Altar",
    1000080: "Battle Copter Altar",
    1000082: "Healing Hut",
}

BB_RESOURCE_BUILDING_NAMES: dict[int, str] = {
    1000035: "Elixir Collector",
    1000036: "Elixir Storage",
    1000037: "Gold Mine",
    1000038: "Gold Storage",
    1000058: "Gem Mine",
    1000065: "B.O.B Control",
}

BB_TRAP_NAMES: dict[int, str] = {
    12000010: "Spring Trap",
    12000011: "Push Trap",
    12000013: "Mine",
    12000014: "Mega Mine",
}

BB_WALL_NAMES: dict[int, str] = {
    1000033: "Wall",
}

BB_HERO_NAMES: dict[int, str] = {
    28000003: "Battle Machine",
    28000005: "Battle Copter",
}

BB_TROOP_NAMES: dict[int, str] = {
    4000031: "Raged Barbarian",
    4000032: "Sneaky Archer",
    4000033: "Beta Minion",
    4000034: "Boxer Giant",
    4000035: "Bomber",
    4000036: "Power P.E.K.K.A",
    4000037: "Cannon Cart",
    4000038: "Drop Ship",
    4000041: "Baby Dragon",
    4000042: "Night Witch",
    4000070: "Hog Glider",
    4000106: "Electrofire Wizard",
}

BB_OTHER_NAMES: dict[int, str] = {
    1000034: "Builder Hall",
    1000039: "Clock Tower",
}

# --- Composite mappings ---

HOME_VILLAGE_NAMES: dict[int, str] = {}
for d in [HOME_DEFENSE_NAMES, HOME_ARMY_BUILDING_NAMES,
          HOME_RESOURCE_BUILDING_NAMES, HOME_TRAP_NAMES,
          HOME_WALL_NAMES, HOME_HERO_NAMES, HOME_TROOP_NAMES,
          HOME_SPELL_NAMES, HOME_SIEGE_MACHINE_NAMES, HOME_PET_NAMES,
          HOME_CRAFTED_DEFENSE_NAMES, HOME_GUARDIAN_NAMES,
          HOME_HERO_EQUIPMENT_NAMES, HOME_OTHER_NAMES]:
    HOME_VILLAGE_NAMES.update(d)

BUILDER_BASE_NAMES: dict[int, str] = {}
for d in [BB_DEFENSE_NAMES, BB_ARMY_BUILDING_NAMES,
          BB_RESOURCE_BUILDING_NAMES, BB_TRAP_NAMES,
          BB_WALL_NAMES, BB_HERO_NAMES, BB_TROOP_NAMES,
          BB_OTHER_NAMES]:
    BUILDER_BASE_NAMES.update(d)

TOWN_HALL_DATA_ID = 1000001
BUILDER_HALL_DATA_ID = 1000034


class ParseResult:
    def __init__(self) -> None:
        self.tag: str = ""
        self.town_hall: int = 0
        self.builder_hall: int = 0
        self.total_builders: int = 5
        self.free_builders: int = 5
        self.buildings: list[dict[str, Any]] = []
        self.upgrades: list[dict[str, Any]] = []


def _parse_entries(
    entries: list[dict],
    name_map: dict[int, str],
    suffix: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    upgrades: list[dict[str, Any]] = []

    for b in entries:
        if not isinstance(b, dict):
            continue
        data_id = b.get("data", 0)
        lvl = b.get("lvl", 0)
        cnt = b.get("cnt", 1)
        timer = b.get("timer")

        name = name_map.get(data_id, f"Building #{data_id}")

        if timer is not None:
            upgrades.append({
                "building_name": f"{name}{suffix}",
                "building_level": lvl,
                "target_level": lvl + 1,
                "duration_seconds_remaining": int(timer),
                "data_id": data_id,
            })

        for _ in range(cnt):
            items.append({
                "name": f"{name}{suffix}",
                "level": lvl,
                "data_id": data_id,
            })

    return items, upgrades


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

    all_items: list[dict[str, Any]] = []
    all_upgrades: list[dict[str, Any]] = []
    town_hall_lvl = 0
    builder_hall_lvl = 0

    buildings_raw: list[dict] = data.get("buildings") or []
    if isinstance(buildings_raw, list):
        items, upgs = _parse_entries(buildings_raw, HOME_VILLAGE_NAMES)
        all_items.extend(items)
        all_upgrades.extend(upgs)
        for b in buildings_raw:
            if b.get("data") == TOWN_HALL_DATA_ID:
                town_hall_lvl = max(town_hall_lvl, b.get("lvl", 0))

    buildings2_raw: list[dict] = data.get("buildings2") or []
    if isinstance(buildings2_raw, list):
        items, upgs = _parse_entries(buildings2_raw, BUILDER_BASE_NAMES, " (BB)")
        all_items.extend(items)
        all_upgrades.extend(upgs)
        for b in buildings2_raw:
            if b.get("data") == BUILDER_HALL_DATA_ID:
                builder_hall_lvl = max(builder_hall_lvl, b.get("lvl", 0))

    heroes_raw: list[dict] = data.get("heroes") or []
    if isinstance(heroes_raw, list):
        items, upgs = _parse_entries(heroes_raw, HOME_VILLAGE_NAMES)
        all_items.extend(items)
        all_upgrades.extend(upgs)

    units_raw: list[dict] = data.get("units") or []
    if isinstance(units_raw, list):
        items, upgs = _parse_entries(units_raw, HOME_VILLAGE_NAMES)
        all_items.extend(items)
        all_upgrades.extend(upgs)

    spells_raw: list[dict] = data.get("spells") or []
    if isinstance(spells_raw, list):
        items, upgs = _parse_entries(spells_raw, HOME_VILLAGE_NAMES)
        all_items.extend(items)
        all_upgrades.extend(upgs)

    traps_raw: list[dict] = data.get("traps") or []
    if isinstance(traps_raw, list):
        items, upgs = _parse_entries(traps_raw, HOME_VILLAGE_NAMES)
        all_items.extend(items)
        all_upgrades.extend(upgs)

    # handle traps2 (BB traps)
    traps2_raw: list[dict] = data.get("traps2") or []
    if isinstance(traps2_raw, list):
        items, upgs = _parse_entries(traps2_raw, BUILDER_BASE_NAMES, " (BB)")
        all_items.extend(items)
        all_upgrades.extend(upgs)

    result.town_hall = town_hall_lvl
    result.builder_hall = builder_hall_lvl
    result.buildings = all_items
    result.upgrades = all_upgrades

    total_builders = data.get("totalBuilderCount") or data.get("total_builder_count")
    if total_builders is not None:
        result.total_builders = int(total_builders)

    free_builders = data.get("freeBuilderCount") or data.get("free_builder_count")
    if free_builders is not None:
        result.free_builders = int(free_builders)
    else:
        result.free_builders = result.total_builders - len(all_upgrades)

    logger.info(
        f"Parsed: TH={result.town_hall}, BH={result.builder_hall}, "
        f"builders={result.free_builders}/{result.total_builders}, "
        f"buildings={len(all_items)}, upgrades={len(all_upgrades)}"
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
