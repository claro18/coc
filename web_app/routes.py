import hmac
import hashlib
import json
import os
import datetime
import logging

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from database.connection import sync_session
from database.models import User, ActiveUpgrade
from bot.services.scheduler import get_active_job_count

logger = logging.getLogger(__name__)

admin_router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

BOT_START_TIME = datetime.datetime.utcnow()


def validate_init_data(init_data: str) -> int | None:
    if not BOT_TOKEN:
        return None

    parsed = {}
    for part in init_data.split("&"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        from urllib.parse import unquote
        parsed[k] = unquote(v)

    hash_value = parsed.pop("hash", None)
    if not hash_value:
        return None

    sorted_keys = sorted(parsed.keys())
    data_check_string = "\n".join(f"{k}={parsed[k]}" for k in sorted_keys)

    secret_key = hmac.new(
        b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if computed_hash != hash_value:
        return None

    try:
        user_raw = parsed.get("user", "{}")
        user_data = json.loads(user_raw)
        return int(user_data.get("id", 0))
    except (ValueError, KeyError, TypeError):
        return None


@admin_router.get("/", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "webapp_url": os.getenv("WEBAPP_URL", "")},
    )


@admin_router.post("/api/verify")
async def verify_init_data(request: Request):
    body = await request.json()
    init_data = body.get("initData", "")
    user_id = validate_init_data(init_data)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if user_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"ok": True, "user_id": user_id}


@admin_router.get("/api/metrics")
async def get_metrics():
    try:
        with sync_session() as session:
            total_users = session.scalar(select(func.count(User.id))) or 0
            active_upgrades = session.scalar(
                select(func.count(ActiveUpgrade.id)).where(
                    ActiveUpgrade.is_completed == False
                )
            ) or 0
            total_upgrades = session.scalar(select(func.count(ActiveUpgrade.id))) or 0

        return {
            "total_users": total_users,
            "active_trackers": total_users,
            "active_upgrades": active_upgrades,
            "total_upgrades": total_upgrades,
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return {"total_users": 0, "active_trackers": 0, "active_upgrades": 0, "total_upgrades": 0}


@admin_router.get("/api/users")
async def get_users():
    try:
        with sync_session() as session:
            users = session.execute(
                select(User).order_by(User.created_at.desc()).limit(100)
            ).scalars().all()

        return {
            "users": [
                {
                    "id": u.id,
                    "username": u.username or "",
                    "tag": u.tag or "",
                    "town_hall": u.town_hall,
                    "created_at": u.created_at.strftime("%Y-%m-%d %H:%M UTC") if u.created_at else "",
                    "last_sync": u.last_json_sync.strftime("%Y-%m-%d %H:%M UTC") if u.last_json_sync else "Never",
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"Users error: {e}")
        return {"users": []}


@admin_router.get("/api/health")
async def health():
    uptime = datetime.datetime.utcnow() - BOT_START_TIME
    try:
        with sync_session() as session:
            session.execute(select(1))
            db_status = "Connected"
    except Exception:
        db_status = "Disconnected"

    try:
        active_jobs = get_active_job_count()
    except Exception:
        active_jobs = 0

    return {
        "status": "ok",
        "uptime": str(uptime).split(".")[0],
        "db": db_status,
        "scheduler_jobs": active_jobs,
    }
