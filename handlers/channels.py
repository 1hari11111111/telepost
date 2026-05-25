import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.helpers import is_owner
from keyboards.inline import manage_channels_keyboard, main_menu_keyboard
from db.mongo import get_all_channels, clear_session

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    clear_session(user_id)
    await update.message.reply_text(
        "👋 <b>Welcome to your Telegram Post Bot!</b>\n\n"
        "Just send me any content — text, photo, video, document, audio, poll, or forward — "
        "and I'll ask you where to post it.\n\n"
        "Use /channels to manage your channels.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(),
    )


async def cmd_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    channels = get_all_channels()
    if not channels:
        text = (
            "📋 <b>No channels saved yet.</b>\n\n"
            "Forward a message from a channel or group to add it."
        )
    else:
        lines = []
        for ch in channels:
            handle = f"@{ch['username']}" if ch.get("username") else "Private"
            default = " ⭐" if ch.get("is_default") else ""
            lines.append(f"• <b>{ch['title']}</b> ({handle}){default}")
        text = "📋 <b>Your Channels:</b>\n\n" + "\n".join(lines)

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=manage_channels_keyboard(),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        return
    clear_session(user_id)
    await update.message.reply_text("✅ Action cancelled. Send me content to post!")
