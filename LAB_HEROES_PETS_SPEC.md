# Feature Spec: Laboratory + Heroes + Pets
### Automatically gated by Town Hall level

Goal: a new bot section showing Laboratory research status, Hero upgrades, and Pet upgrades — where every section/button automatically shows or hides based on the user's Town Hall, unlike regular buildings which are always shown to everyone.

---

## 1. Core principle: don't scatter `if town_hall >= X` checks everywhere

Instead of hardcoding conditions like `if user.town_hall >= 14` across multiple handlers, follow the same pattern already used in `calculator.py` (`get_max_level_at_th`) — centralized data with an `unlock_th` (or `th`) field per item, and the code reads from it to decide what to show. That way, whenever a new Town Hall or hero ships, you update a JSON file, not the bot's logic.

### Proposed data layout (extending `static_data/`)

```
static_data/
  coc_buildings.json      # already exists
  coc_heroes.json         # new
  coc_pets.json           # new
  coc_lab_troops.json     # new (troops/spells upgraded in the Laboratory)
```

Example `coc_heroes.json`:
```json
{
  "heroes": {
    "Barbarian King":  { "unlock_th": 7,  "levels": { "1": {"upgrade_time_seconds": 3600}, "2": {...} } },
    "Archer Queen":    { "unlock_th": 8,  "levels": {...} },
    "Minion Prince":   { "unlock_th": 9,  "levels": {...} },
    "Grand Warden":    { "unlock_th": 11, "levels": {...} },
    "Royal Champion":  { "unlock_th": 13, "levels": {...} },
    "Dragon Duke":     { "unlock_th": 15, "levels": {...} }
  }
}
```

Example `coc_pets.json`:
```json
{
  "pet_house_unlock_th": 14,
  "pets": {
    "L.A.S.S.I":        { "unlock_pet_house_level": 1 },
    "Mighty Yak":       { "unlock_pet_house_level": 1 },
    "Electro Owl":      { "unlock_pet_house_level": 2 },
    "Unicorn":          { "unlock_pet_house_level": 2 },
    "Phoenix":          { "unlock_pet_house_level": 3 },
    "Poison Lizard":    { "unlock_pet_house_level": 3 },
    "Diggy":            { "unlock_pet_house_level": 4 },
    "Frosty":           { "unlock_pet_house_level": 4 },
    "Spirit Fox":       { "unlock_pet_house_level": 5 },
    "Angry Jelly":      { "unlock_pet_house_level": 5 },
    "Sneezy":           { "unlock_pet_house_level": 6 },
    "Greedy Raven":     { "unlock_pet_house_level": 6 }
  }
}
```

> ⚠️ **Important caveat:** the exact `unlock_pet_house_level` for each pet (which one unlocks before which) is not 100% agreed upon across community sources, and Clash of Clans updates constantly (the most recent addition was "Greedy Raven" in the February 2026 update). **Don't treat the numbers above as final** — verify them from the game itself (the in-game Pet House screen shows exactly which pet unlocks at which level) or from Supercell's official changelog before shipping this to production. What is confirmed and consistent across multiple sources (including the official Fandom Wiki):
> - **Pet House unlocks exactly at Town Hall 14.**
> - Heroes: Barbarian King (TH7), Archer Queen (TH8), Minion Prince (TH9), Grand Warden (TH11), Royal Champion (TH13), Dragon Duke (TH15) — all gated through the Hero Hall building (itself unlocked at TH7).

---

## 2. Display logic (which button shows for which Town Hall)

```python
def get_visible_sections(town_hall: int) -> list[str]:
    sections = ["laboratory"]  # Laboratory exists from TH3+ always
    if town_hall >= 7:
        sections.append("heroes")       # Hero Hall
    if town_hall >= 14:
        sections.append("pets")         # Pet House
    return sections
```

And when building the keyboard (`bot/keyboards/inline.py`), build the buttons dynamically:

```python
def progression_menu(town_hall: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🧪 Laboratory", callback_data="prog:lab"))

    if town_hall >= 7:
        builder.row(InlineKeyboardButton(text="🦸 Heroes", callback_data="prog:heroes"))
    if town_hall >= 14:
        builder.row(InlineKeyboardButton(text="🐾 Pets", callback_data="prog:pets"))

    builder.row(InlineKeyboardButton(text="↩️ Back", callback_data="menu:main"))
    return builder.as_markup()
```

The exact same idea applies inside the Heroes section itself: if the user is TH9, they should see Barbarian King + Archer Queen + Minion Prince only, and NOT see Grand Warden (TH11), Royal Champion (TH13), or Dragon Duke (TH15):

```python
def get_available_heroes(town_hall: int, heroes_data: dict) -> list[str]:
    return [
        name for name, info in heroes_data.items()
        if town_hall >= info["unlock_th"]
    ]
```

Same logic for each pet based on `unlock_pet_house_level` (this requires knowing the user's current Pet House level — it should be persisted from the JSON export just like any other building, since its data ID already comes through the existing `buildings2` parsing path if present in the file).

---

## 3. Where to source Laboratory / Heroes / Pets data for future updates

1. **The file the user uploads:** Supercell's Data Export already contains a `heroes` array (and pet data, when present) — the code already reads `heroes_raw = data.get("heroes")` (see `parser.py` line 409), so no extra extraction work is required there. You just need to make sure all hero and pet names are present in `HOME_HERO_NAMES` and `HOME_PET_NAMES` (already present in the code).
2. **Upgrade times and costs** (upgrade_time_seconds per hero/pet/troop level): not currently in `coc_buildings.json` (it only has 34 buildings — no heroes, pets, or troops). Sources to compile this from:
   - **Community:** `clashninja.com`, `coc.guide`, Fandom Wiki pages for each hero/pet (they have Level → Upgrade Time → Cost tables).
   - **The `coc.py` library** (already listed as a dependency in `SPECIFICATION.md`) can fetch a player's public profile data via the official API, but it does not provide hero/pet upgrade time/cost tables — those still need to be compiled manually from in-game sources.
3. **Future updates:** whenever a new Town Hall ships (e.g. TH18 in November 2025) or a new hero is added (e.g. Dragon Duke in March 2026), these files (`coc_heroes.json`, `coc_pets.json`) are the only thing that needs updating — no code logic changes required.

---

## 4. Suggested "Laboratory" section UI

```
🧪 Laboratory — Town Hall 14

Upgrades available to you right now:
  ⚔️ Barbarian — Lvl 9 → 10  (available)
  🔥 Dragon    — Lvl 6 → 7   (available)
  🧙 Wizard    — maxed for your Town Hall

[View all troops]  [View spells]  [↩️ Back]
```

- Any troop/spell that has already reached the maximum level available for the user's Town Hall (same logic as the existing `get_max_level_at_th`) is shown with a "maxed for your Town Hall" label instead of an upgrade button.
- Troops/spells whose training building (Barracks / Dark Barracks / Spell Factory) doesn't exist yet or isn't leveled enough should not be shown at all, rather than shown disabled.

---

## 5. Suggested implementation order

1. Add the three new files under `static_data/` (you can start with just the six heroes + Pet House — that's the most important part).
2. Add `get_visible_sections`, `get_available_heroes`, `get_available_pets` functions in `bot/services/calculator.py` (or a new file `bot/services/progression.py`).
3. Add a new `progression_menu` keyboard in `bot/keyboards/inline.py`, plus a "📈 Progression / Laboratory" button in the existing `main_menu`.
4. Add a new handler `bot/handlers/progression.py` with:
   - `prog:lab` → shows Laboratory status
   - `prog:heroes` → shows only the heroes available at the user's TH
   - `prog:pets` → only shown if TH ≥ 14
5. Any hero/pet/troop upgrade already present in `parsed.upgrades` (the code already captures these from `heroes`/`units`/`spells` in the file) should be wired into the existing scheduling and notification system (`scheduler.py`) — no new mechanism is needed here, it already supports this.

---

## Sources used for this spec
- Clash of Clans Wiki (Fandom) — Pet House, Hero Hall, and Dragon Duke pages (continuously updated alongside each game update, and the closest thing to an official source despite being community-maintained).
- Recent (2026) community articles about hero and pet updates — used to confirm dates and the general TH thresholds (Pet House TH, hero unlock TH per hero), but the fine-grained details (exact upgrade times, the precise order in which each pet unlocks) still need verification from inside the game itself or from a real Data Export file for an advanced (TH14+) village.
