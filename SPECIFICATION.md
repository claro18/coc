# Technical Specification Document

## 1. System Architecture & Stack
- **Language:** Python 3.11+
- **Telegram Bot Framework:** `aiogram` (v3.x)
- **CoC API Integration:** `coc.py` (Official Supercell API client for fetching public player/clan stats)
- **Game Static Data:** Static mapping of structure upgrade durations and costs (sourced from community data repositories e.g., `coc-data` / `ClashNinja` public schemas).
- **Scheduler:** `APScheduler` (AsyncIOScheduler) for managing live upgrade completion timers and notification alerts.
- **Database:** `SQLAlchemy` (v2.x) ORM with `PostgreSQL` (Production on Render) or `SQLite` (Local Dev).
- **Admin Mini App:** Lightweight HTML5 + Tailwind CSS + FastAPI/Flask backend serving the Telegram Web App interface.

---

## 2. `.json` Data Export Processing Engine

### 2.1 File Parsing Logic
1. When a user sends a `.json` document (obtained via CoC `Settings -> More Settings -> Data Export`):
   - Validate file structure against standard Supercell Data Export schema.
   - Extract `TownHallLevel`, `Buildings` array, `UpgradesInProgress` array, and `FreeBuilders` count.
2. Store the timestamp of file submission (`imported_at`).
3. Map internal building IDs/levels to static CoC upgrade time tables.

### 2.2 Active Upgrades & Real-Time Calculation
For every item inside `UpgradesInProgress`:
- Read `target_level`, `building_id`, and `duration_seconds_remaining` at the moment of export.
- Calculate absolute completion time: 
  $$\text{Completion Time} = \text{imported\_at} + \text{duration\_seconds\_remaining}$$
- Register a background job in `APScheduler` scheduled for $\text{Completion Time}$.
- When triggered, send a Telegram notification:
  > 🔔 **Upgrade Completed!**  
  > Your **Cannons (Level 12)** upgrade is finished! Builder #2 is now free.

### 2.3 Progress Percentage Algorithm
$$\text{Town Hall Progress \%} = \left( \frac{\text{Current Completed Upgrade Costs/Times}}{\text{Total Max Costs/Times for Current Town Hall Level}} \right) \times 100$$

Display visually in Telegram using progress bar formatting:
`[████████░░] 80% Maxed`

---

## 3. Telegram UI & User Flow

### 3.1 Main Menu (Inline Keyboards Only)
When user issues `/start` or clicks main menu buttons:

```text
+-------------------------------------------------------+
| 🏰 Town Hall Level: 14                                |
| 📊 TH Progress: [████████░░] 82.5%                     |
| 🔨 Active Builders: 4/6 Free                         |
| ⏳ Next Builder Free in: 04h 12m (Archer Tower Lvl 18) |
+-------------------------------------------------------+
| [ 🔄 Refresh Progress ]                              |
| [ 🔨 View Active Builders ] | [ 📊 Detailed Stats ]    |
| [ 📜 Upgrade History ]      | [ ⚙️ Help / How to Export ]|
+-------------------------------------------------------+
3.2 Refresh Flow ("🔄 Refresh Progress")
Because Telegram bots cannot force the Supercell app to output a file automatically, clicking "🔄 Refresh Progress" will:

Recalculate all active timers based on elapsed system time.

Prompt the user with a quick inline button: "Upload your latest .json file to sync new upgrades started in-game."

Automatically parse the new file, update active jobs, overwrite ended upgrades, and update the percentage display.

4. Admin Telegram Mini App (Web App)
4.1 Access Control & Security
Admin IDs must be defined in .env as a comma-separated list: ADMIN_IDS="123456789,987654321".

In the Telegram Bot main menu, check event.from_user.id.

IF AND ONLY IF user_id is in ADMIN_IDS, attach an extra button to the menu:

[ 👑 Admin Dashboard (Mini App) ] pointing to the Web App URL.

Regular users must never see this button, and direct API endpoints for the web app must validate Telegram InitData signatures to prevent unauthorized web access.

4.2 Mini App Dashboard Features
Overview Metrics: Total Registered Users, Active Village Trackers, Total Ongoing Upgrades Tracked.

User Directory Table: Searchable table listing User ID, Telegram Username, TH Level, Joined Date, Last Sync Timestamp.

System Health: Bot Uptime, Active Scheduler Jobs count, DB Connection status.

5. Database Schema (SQLAlchemy)
5.1 users Table
id (BigInteger, Primary Key - Telegram User ID)

username (String, Nullable)

tag (String, CoC Player Tag)

town_hall (Integer)

created_at (DateTime, Default UTC)

last_json_sync (DateTime)

5.2 active_upgrades Table
id (Integer, Primary Key)

user_id (BigInteger, ForeignKey users.id)

building_name (String)

target_level (Integer)

start_time (DateTime)

end_time (DateTime)

builder_index (Integer)

is_completed (Boolean, Default False)

6. Project Structure
Plaintext
.
├── bot/
│   ├── __init__.py
│   ├── main.py                  # Entry point (Polling/Webhook setup)
│   ├── handlers/
│   │   ├── start.py             # /start & menu handlers
│   │   ├── json_import.py       # Processing .json uploads & sync
│   │   └── admin.py             # Admin menu & web app launcher
│   ├── services/
│   │   ├── parser.py            # Logic to parse CoC JSON export
│   │   ├── scheduler.py         # APScheduler notification manager
│   │   └── calculator.py        # Progress % & time calculations
│   └── keyboards/
│       └── inline.py            # Inline keyboards builder
├── web_app/
│   ├── app.py                   # FastAPI app serving Mini App & API
│   ├── templates/
│   │   └── admin.html           # Admin Dashboard (Tailwind CSS)
│   └── static/
│       └── js/admin.js          # Telegram Mini App WebApp JS integration
├── database/
│   ├── models.py                # SQLAlchemy DB Models
│   └── connection.py            # Database session manager
├── static_data/
│   └── coc_buildings.json       # Levels, upgrade times, costs mapping
├── .env.example
├── Dockerfile
├── render.yaml
└── requirements.txt