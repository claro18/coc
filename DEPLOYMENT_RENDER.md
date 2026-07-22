
# Render Deployment & Environment Setup Guide

## 1. Environment Variables (`.env`)

Create a `.env` file (or set these inside Render Dashboard -> Environment):

```env
# Telegram Config
BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_FROM_BOTFATHER"
ADMIN_IDS="123456789,987654321"

# Clash of Clans Official API (Optional for public profile sync)
COC_API_KEY="YOUR_SUPERCELL_DEVELOPER_KEY"

# Web App / Admin Dashboard Config
WEBAPP_URL="[https://your-bot-app.onrender.com](https://your-bot-app.onrender.com)"
PORT=8000

# Database Config (Render PostgreSQL Connection String)
DATABASE_URL="postgresql://user:password@hostname:5432/dbname"