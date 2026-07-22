# Clash of Clans Automated Telegram Tracker Bot & Admin Mini App

## Project Overview
This is an automated Telegram Bot built with Python (`aiogram 3.x`) designed to track Clash of Clans village progression **solely via `.json` Data Export files** provided by players.

The system eliminates manual data entry completely. When a user uploads their village `.json` file, the bot parses active builders, current upgrades, remaining duration, and maxing percentage. Clicking a **"🔄 Refresh Progress"** button prompts the user to re-upload their latest export (or syncs from latest parsed state) to immediately update ongoing upgrades, percentage bars, and notification timers.

Additionally, it includes a secure **Telegram Mini App Admin Dashboard** restricted to specific Telegram User IDs defined in `.env`.

## Key Features
- **Zero Manual Input:** All village stats, upgrades, and builder assignments are imported strictly via the official Clash of Clans `.json` export file.
- **Dynamic Builder & Upgrade Tracking:** Automatic calculation of active upgrade end-times, percentage completion, and countdown timers.
- **Interactive Button UI:** Clean Inline Keyboards for stats, active builders, and refresh commands.
- **Push Notifications:** Background scheduler (`APScheduler`) sends automated Telegram alerts when a builder finishes an upgrade.
- **Admin Mini App (Web App):** A dashboard displaying user metrics, total registered players, join dates, and system logs—visible only to specified Admin IDs.
- **Render Ready:** Configured for seamless deployment on Render.com with persistent database support (PostgreSQL/SQLite) and Webhook mode.