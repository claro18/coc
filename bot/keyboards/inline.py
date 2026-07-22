from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://localhost:8000")


def main_menu(user_id: int, admin_ids: list[int] | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Refresh Progress", callback_data="menu:refresh"),
    )
    builder.row(
        InlineKeyboardButton(text="🔨 Active Builders", callback_data="menu:builders"),
        InlineKeyboardButton(text="📊 Detailed Stats", callback_data="menu:stats"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 Upgrade History", callback_data="menu:history"),
        InlineKeyboardButton(text="⚙️ Help", callback_data="menu:help"),
    )
    if admin_ids and user_id in admin_ids:
        builder.row(
            InlineKeyboardButton(
                text="👑 Admin Dashboard",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        )
    return builder.as_markup()


def refresh_prompt() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 Upload New JSON", callback_data="menu:upload_prompt"),
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Back to Menu", callback_data="menu:main"),
    )
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Back to Menu", callback_data="menu:main"),
    )
    return builder.as_markup()


def admin_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Dashboard", callback_data="admin:dashboard"),
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Back to Menu", callback_data="menu:main"),
    )
    return builder.as_markup()


def help_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📤 Upload Your JSON",
            callback_data="menu:upload_prompt",
        )
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Back to Menu", callback_data="menu:main"),
    )
    return builder.as_markup()
