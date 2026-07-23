import hmac
import hashlib
import json as json_lib
import os
import datetime
import logging
import asyncio

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, or_

from database.connection import sync_session
from database.models import User, ActiveUpgrade, BroadcastMessage, BotSetting
from bot.services.scheduler import get_active_job_count, scheduler
from bot.main import bot_instance

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
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if computed_hash != hash_value:
        return None
    try:
        user_raw = parsed.get("user", "{}")
        user_data = json_lib.loads(user_raw)
        return int(user_data.get("id", 0))
    except (ValueError, KeyError, TypeError):
        return None


def _verify(request: Request) -> int:
    user_id = validate_init_data(request.headers.get("x-init-data", ""))
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if user_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user_id


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
            banned = session.scalar(select(func.count(User.id)).where(User.is_banned == True)) or 0
            active_upgrades = session.scalar(
                select(func.count(ActiveUpgrade.id)).where(ActiveUpgrade.is_completed == False)
            ) or 0
            total_upgrades = session.scalar(select(func.count(ActiveUpgrade.id))) or 0
            pending_broadcasts = session.scalar(
                select(func.count(BroadcastMessage.id)).where(BroadcastMessage.status == "pending")
            ) or 0
        return {
            "total_users": total_users,
            "banned_users": banned,
            "active_trackers": total_users,
            "active_upgrades": active_upgrades,
            "total_upgrades": total_upgrades,
            "pending_broadcasts": pending_broadcasts,
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return {"total_users": 0, "banned_users": 0, "active_trackers": 0, "active_upgrades": 0, "total_upgrades": 0, "pending_broadcasts": 0}


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
                    "is_banned": u.is_banned,
                    "created_at": u.created_at.strftime("%Y-%m-%d %H:%M UTC") if u.created_at else "",
                    "last_seen": u.last_seen.strftime("%Y-%m-%d %H:%M UTC") if u.last_seen else "",
                    "last_sync": u.last_json_sync.strftime("%Y-%m-%d %H:%M UTC") if u.last_json_sync else "Never",
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"Users error: {e}")
        return {"users": []}


@admin_router.get("/api/users/search")
async def search_users(q: str = ""):
    try:
        with sync_session() as session:
            query = select(User)
            if q:
                q_like = f"%{q}%"
                query = query.where(
                    or_(
                        User.id.cast(func.text).ilike(q_like),
                        User.username.ilike(q_like),
                        User.tag.ilike(q_like),
                    )
                )
            query = query.order_by(User.created_at.desc()).limit(50)
            users = session.execute(query).scalars().all()
        return {
            "users": [
                {
                    "id": u.id,
                    "username": u.username or "",
                    "tag": u.tag or "",
                    "town_hall": u.town_hall,
                    "is_banned": u.is_banned,
                    "created_at": u.created_at.strftime("%Y-%m-%d %H:%M UTC") if u.created_at else "",
                    "last_seen": u.last_seen.strftime("%Y-%m-%d %H:%M UTC") if u.last_seen else "",
                    "last_sync": u.last_json_sync.strftime("%Y-%m-%d %H:%M UTC") if u.last_json_sync else "Never",
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"users": []}


@admin_router.get("/api/users/{user_id}")
async def get_user_detail(user_id: int):
    try:
        with sync_session() as session:
            user = session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            total_upgrades = session.scalar(
                select(func.count(ActiveUpgrade.id)).where(ActiveUpgrade.user_id == user_id)
            ) or 0
            completed = session.scalar(
                select(func.count(ActiveUpgrade.id)).where(
                    ActiveUpgrade.user_id == user_id, ActiveUpgrade.is_completed == True
                )
            ) or 0
            active = session.scalar(
                select(func.count(ActiveUpgrade.id)).where(
                    ActiveUpgrade.user_id == user_id, ActiveUpgrade.is_completed == False
                )
            ) or 0
            buildings = []
            if user.buildings_snapshot:
                try:
                    buildings = json_lib.loads(user.buildings_snapshot)
                except Exception:
                    pass
        return {
            "id": user.id,
            "username": user.username or "",
            "tag": user.tag or "",
            "town_hall": user.town_hall,
            "total_builders": user.total_builders,
            "buildings_count": len(buildings),
            "total_upgrades": total_upgrades,
            "completed_upgrades": completed,
            "active_upgrades": active,
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M UTC") if user.created_at else "",
            "last_seen": user.last_seen.strftime("%Y-%m-%d %H:%M UTC") if user.last_seen else "",
            "last_sync": user.last_json_sync.strftime("%Y-%m-%d %H:%M UTC") if user.last_json_sync else "Never",
            "is_banned": user.is_banned,
            "ban_reason": user.ban_reason or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/api/users/{user_id}/ban")
async def ban_user(user_id: int, request: Request):
    _verify(request)
    try:
        body = await request.json()
        reason = body.get("reason", "")
    except Exception:
        reason = ""
    with sync_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_banned = True
        user.ban_reason = reason
        session.commit()
    return {"ok": True}


@admin_router.post("/api/users/{user_id}/unban")
async def unban_user(user_id: int, request: Request):
    _verify(request)
    with sync_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_banned = False
        user.ban_reason = None
        session.commit()
    return {"ok": True}


@admin_router.get("/api/maintenance")
async def get_maintenance():
    with sync_session() as session:
        result = session.execute(
            select(BotSetting).where(BotSetting.key == "maintenance_mode")
        )
        setting = result.scalar_one_or_none()
    if setting and setting.value:
        try:
            data = json_lib.loads(setting.value)
            return {"enabled": data.get("enabled", False), "message": data.get("message", "")}
        except Exception:
            pass
    return {"enabled": False, "message": ""}


@admin_router.post("/api/maintenance")
async def set_maintenance(request: Request):
    _verify(request)
    body = await request.json()
    enabled = body.get("enabled", False)
    message = body.get("message", "Bot is under maintenance. Please try again later.")
    value = json_lib.dumps({"enabled": enabled, "message": message})
    with sync_session() as session:
        setting = session.get(BotSetting, "maintenance_mode")
        if setting:
            setting.value = value
        else:
            session.add(BotSetting(key="maintenance_mode", value=value))
        session.commit()

    bot = bot_instance
    if bot and not enabled:
        try:
            await bot.send_message(
                chat_id=_verify(request),
                text="\u2705 <b>Maintenance mode disabled.</b>\nBot is back online!",
                parse_mode="HTML",
            )
        except Exception:
            pass

    return {"ok": True}


@admin_router.post("/api/broadcast")
async def create_broadcast(request: Request):
    admin_id = _verify(request)
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message text is required")
    with sync_session() as session:
        bm = BroadcastMessage(text=text, admin_id=admin_id, status="pending")
        session.add(bm)
        session.commit()
        bm_id = bm.id
    return {"ok": True, "id": bm_id}


@admin_router.get("/api/broadcast/{broadcast_id}")
async def get_broadcast(broadcast_id: int):
    with sync_session() as session:
        bm = session.get(BroadcastMessage, broadcast_id)
        if not bm:
            raise HTTPException(status_code=404, detail="Broadcast not found")
        return {
            "id": bm.id,
            "text": bm.text,
            "status": bm.status,
            "sent_count": bm.sent_count,
            "failed_count": bm.failed_count,
            "created_at": bm.created_at.strftime("%Y-%m-%d %H:%M UTC") if bm.created_at else "",
            "completed_at": bm.completed_at.strftime("%Y-%m-%d %H:%M UTC") if bm.completed_at else "",
        }


@admin_router.get("/api/broadcast/history")
async def broadcast_history():
    with sync_session() as session:
        items = session.execute(
            select(BroadcastMessage).order_by(BroadcastMessage.created_at.desc()).limit(50)
        ).scalars().all()
        return {
            "broadcasts": [
                {
                    "id": b.id,
                    "text": b.text[:100] + ("..." if len(b.text) > 100 else ""),
                    "status": b.status,
                    "sent_count": b.sent_count,
                    "failed_count": b.failed_count,
                    "created_at": b.created_at.strftime("%Y-%m-%d %H:%M UTC") if b.created_at else "",
                    "completed_at": b.completed_at.strftime("%Y-%m-%d %H:%M UTC") if b.completed_at else "",
                }
                for b in items
            ]
        }


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
