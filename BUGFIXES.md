# Bug Diagnosis & Fixes — claro18/coc

Full review of the repository (current commit: `887a291`). Four issues found, each with root cause + exact fix.

---

## 1. TH Progress % always returns 0.0% after the first upload

**Symptom:** The first message right after uploading the JSON file shows a correct percentage, but any later view (`/menu`, "Detailed Stats") shows 0.0%.

**Root cause:** The `User` model (`database/models.py`) only stores `town_hall` and `total_builders` — there is no column persisting the building state (`buildings`). `calculate_th_progress()` needs the building list to compute anything, but `start.py:53` and `admin.py:99` call it like this:

```python
progress = calculate_th_progress(user.town_hall, [])
```

An empty list always produces zero. The real data (`parsed.buildings`) only exists in memory at the moment the JSON is parsed inside `json_import.py`, and is discarded right after.

**Fix:**

1. Add a new column in `database/models.py`:
```python
class User(Base):
    ...
    buildings_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
```

2. In `json_import.py`, persist the snapshot right after parsing:
```python
import json as json_lib
user.buildings_snapshot = json_lib.dumps(parsed.buildings)
```

3. In `start.py` and `admin.py`, load it instead of passing an empty list:
```python
buildings = json_lib.loads(user.buildings_snapshot) if user.buildings_snapshot else []
progress = calculate_th_progress(user.town_hall, buildings)
```

> Note: you'll need a small migration (or just delete `bot.db` in development) for the new column to take effect.

---

## 2. Admin Mini App is completely broken

**Root cause:** In `bot/main.py`, the real router that holds every endpoint (`web_app/routes.py` → `/`, `/api/metrics`, `/api/users`, `/api/verify`, `/api/health`) is only mounted **inside this condition**:
```python
if WEBHOOK_URL:
    ...
    main_app.include_router(web_admin_router)
```
But neither `render.yaml`, `.env.example`, nor `DEPLOYMENT_RENDER.md` define `WEBHOOK_URL`. That means, per the current documentation, the bot runs in **polling mode**, and in polling mode a separate FastAPI app is started that only serves `/health` — none of `web_app/routes.py`'s routes or static files are mounted. The "👑 Admin Dashboard" button opens a WebApp pointing at a domain that only serves a health check, so it shows a blank page / 404.

**Fix (best option — makes the dashboard work in both polling and webhook mode):**

In `bot/main.py`, move the mounting of `web_admin_router` and the static files outside the `if WEBHOOK_URL` block, so it always runs on the same FastAPI app that also serves the health check:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from web_app.routes import admin_router as web_admin_router

main_app = FastAPI(title="Clash Tracker Bot")
main_app.include_router(web_admin_router)   # <-- always, not only with webhook

web_app_dir = os.path.join(os.path.dirname(__file__), "..", "web_app", "static")
if os.path.isdir(web_app_dir):
    main_app.mount("/static", StaticFiles(directory=web_app_dir), name="admin_static")

@main_app.get("/health")
async def health():
    return {"status": "ok"}

if WEBHOOK_URL:
    # add /webhook endpoint and call set_webhook
    ...
    config = uvicorn.Config(main_app, host="0.0.0.0", port=PORT)
    await uvicorn.Server(config).serve()
else:
    # run main_app (admin + health) in a separate thread, bot polling in the main task
    ...
```

**Quicker alternative (if you don't want to touch `main.py` right now):** add `WEBHOOK_URL` to `render.yaml` pointing at the Render domain itself, so it runs in webhook mode, which does mount the router:
```yaml
- key: WEBHOOK_URL
  value: https://clhs-bot.onrender.com
```
But this changes how updates are received entirely (webhook instead of polling), so make sure that's actually the mode you want.

---

## 3. Duplicate builder entries in the same message (the actual root cause of what you sent)

This is the most important functional bug in the project right now.

**Symptom you sent:**
```
👷 Builder #6: Building #1000056 (BB) → Lvl 4 (09h 46m)
👷 Builder #6: Building #1000056 (BB) → Lvl 4 (09h 52m)
```
Same building, same target level, two different countdowns — meaning there are two rows in the database for the same upgrade.

**Root cause:** In `bot/handlers/json_import.py`, `handle_document`:
```python
new_building_names = {(u["building_name"], u["target_level"]) for u in parsed.upgrades}

for old_upg in old_upgrades:
    key = (old_upg.building_name, old_upg.target_level)
    if key not in new_building_names:
        old_upg.is_completed = True   # only when the upgrade disappeared from the new file
        ...

for upg_data in parsed.upgrades:
    new_upg = ActiveUpgrade(...)      # always creates a new row, unconditionally
    session.add(new_upg)
```

The logic only marks old upgrades complete (`is_completed = True`) when they **disappeared** from the new file. But any upgrade that's still running (still present in the new file too) leaves its old row untouched with `is_completed=False`, **and at the same time** the second loop creates a brand-new row for that same upgrade without checking whether one already exists. Every time you upload while an upgrade is still in progress, the rows pile up — which is exactly why you saw "Builder #6" twice with two different times (each row was computed from a different upload timestamp).

**Fix:** before creating a new row, look up a matching old row (same `building_name` + `target_level`, not completed) and update it instead of creating a new one:

```python
old_by_key = {
    (u.building_name, u.target_level): u
    for u in old_upgrades
    if (u.building_name, u.target_level) in new_building_names
}

for old_upg in old_upgrades:
    key = (old_upg.building_name, old_upg.target_level)
    if key not in new_building_names:
        old_upg.is_completed = True
        await remove_upgrade_job(user_id, old_upg.id)

builder_index = 0
new_upgrade_ids: list[int] = []
for upg_data in parsed.upgrades:
    key = (upg_data["building_name"], upg_data["target_level"])
    end_time = now + datetime.timedelta(seconds=upg_data["duration_seconds_remaining"])

    existing = old_by_key.get(key)
    if existing:
        # update the existing row instead of duplicating it
        existing.end_time = end_time
        existing.builder_index = builder_index
        new_upgrade_ids.append(existing.id)
    else:
        new_upg = ActiveUpgrade(
            user_id=user_id,
            building_name=upg_data["building_name"],
            building_level=upg_data["building_level"],
            target_level=upg_data["target_level"],
            start_time=now,
            end_time=end_time,
            builder_index=builder_index,
        )
        session.add(new_upg)
        await session.flush()
        new_upgrade_ids.append(new_upg.id)

    builder_index += 1
```

**You also need to clean up the duplicate rows already sitting in the database** (damage done before the fix), with a one-off script that removes duplicate `ActiveUpgrade` rows for the same user/building/level and keeps only the most recent one.

---

## 4. Unrecognized building names ("Building #1000056 (BB)")

**Good news:** this was already fixed in the latest commit in the repo (`887a291` — "Complete data ID mappings... fix Building #1000046 = Star Laboratory"). The IDs you saw (`1000056` = Roaster, `1000046` = Star Laboratory) **are** present now in `bot/services/parser.py`.

**So this is not a bug in the current code — it means the instance running on Render is still on an older commit than this fix.** The fix: `git pull` / redeploy on Render, and restart the service so the change takes effect.

**Warning for the future:** these `data_id` numbers are not officially documented by Supercell — they're all compiled from community sources (same idea noted in `SPECIFICATION.md`). Any new building or new Builder Base object can show up with an ID you don't have yet. **Suggestion:** log any `data_id` that has no name in the map, so you catch it quickly in the logs instead of it showing up to the user as "Building #XXXXXXX":

```python
name = name_map.get(data_id)
if name is None:
    logger.warning(f"Unmapped data_id encountered: {data_id} (lvl={lvl})")
    name = f"Building #{data_id}"
```
