import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web_app.routes import admin_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Clash Tracker Admin (Standalone)")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(admin_router)
