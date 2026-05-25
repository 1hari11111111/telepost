import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import OWNER_ID
from db.mongo import get_session, save_session, get_channel, add_channel
from keyboards.inline import channel_picker_keyboard, add_channel_cancel_keyboard
from utils.helpers import is_owner, get_content_type, build_session_from_message, channel_display_name

logger = logging.getLogger(__name__)

# Tracks media group message ids to avoid duplicate control messages
_media_group_seen: set = set()


async def handle_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entry point for all incoming messages.
    Handles: text, photo, video, document, audio, voice, animation,
             sticker, poll, video_note, forwarded messages, media groups.
    """
    message = update.message
    user_id = message.from_user.id

    if not is_owner(user_id):
        await message.reply_text("⛔ You are not authorised to use this bot.")
        return

    # ── Check if user is in "adding channel" flow ──────────────────────────────
    session = get_session(user_id)
    if session and session.get("step") == "adding_channel":
        await _handle_add_channel_forward(update, context, session)
        return

    # ── Ignore duplicate media group triggers ──────────────────────────────────
    if message.media_group_id:
        if message.media_group_id in _media_group_seen:
            return  # already handled the first item of this album
        _media_group_seen.add(message.media_group_id)

    # ── Build session from this message ───────────────────────────────────────
    content_type = get_content_type(message)
    if content_type == "unknown":
        await message.reply_text("⚠️ Unsupported content type.")
        return

    session_data = build_session_from_message(message)

    # ── Send the channel picker control message ────────────────────────────────
    type_emoji = {
        "text": "📝", "photo": "🖼", "video": "🎬", "document": "📄",
        "audio": "🎵", "voice": "🎤", "animation": "🎞", "sticker": "🎭",
        "poll": "📊", "video_note": "📹",
    }
    emoji = type_emoji.get(content_type, "📦")

    caption_preview = ""
    if session_data.get("caption"):
        preview = session_data["caption"][:80]
        caption_preview = f"\n📝 <i>{preview}{'...' if len(session_data['caption']) > 80 else ''}</i>"

    text = (
        f"{emoji} <b>Content received!</b>{caption_preview}\n\n"
        f"Where do you want to post this?"
    )

    ctrl_msg = await message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=channel_picker_keyboard(),
    )

    session_data["control_message_id"] = ctrl_msg.message_id
    save_session(user_id, session_data)


async def _handle_add_channel_forward(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """Handle a forwarded message during the 'add channel' step."""
    message = update.message
    user_id = message.from_user.id
    control_message_id = session.get("control_message_id")

    async def show_error(text: str):
        try:
            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=control_message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=add_channel_cancel_keyboard(),
            )
        except Exception:
            await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=add_channel_cancel_keyboard())

    # Support both PTB v20+ (forward_origin) and fallback to legacy attributes
    forward_origin = getattr(message, "forward_origin", None)

    chat_id = None
    title = None
    username = None

    if forward_origin:
        # PTB 20.x with Bot API 7.0+ — use forward_origin
        origin_type = forward_origin.type

        if origin_type == "channel":
            chat_id  = forward_origin.chat.id
            title    = forward_origin.chat.title
            username = forward_origin.chat.username

        elif origin_type == "chat":
            sender = getattr(forward_origin, "sender_chat", None) or getattr(forward_origin, "chat", None)
            if sender:
                chat_id  = sender.id
                title    = getattr(sender, "title", None) or "Unknown Group"
                username = getattr(sender, "username", None)

        elif origin_type in ("user", "hidden_user"):
            # Last resort: message.sender_chat (set when forwarded on behalf of a channel)
            sender_chat = getattr(message, "sender_chat", None)
            if sender_chat:
                chat_id  = sender_chat.id
                title    = getattr(sender_chat, "title", None) or "Unknown"
                username = getattr(sender_chat, "username", None)

    else:
        # Fallback: legacy forward_* attributes (older Bot API / PTB versions)
        forward_chat = getattr(message, "forward_from_chat", None)
        if forward_chat:
            chat_id  = forward_chat.id
            title    = getattr(forward_chat, "title", None) or "Unknown"
            username = getattr(forward_chat, "username", None)

    if not chat_id:
        # Not a channel/group forward at all
        is_forwarded = (
            forward_origin is not None or
            getattr(message, "forward_from_chat", None) is not None or
            getattr(message, "forward_from", None) is not None
        )
        if is_forwarded:
            await show_error(
                "❌ <b>That's not a channel or group forward.</b>\n\n"
                "You forwarded from a <b>personal user</b>, not a channel or group.\n\n"
                "Go to your channel/group → tap any message → <b>Forward</b> → send it here."
            )
        else:
            await show_error(
                "📨 <b>Add Channel / Group</b>\n\n"
                "Please <b>forward a message</b> from the channel or group you want to add.\n\n"
                "Make sure I'm already an <b>admin</b> there first!"
            )
        try:
            await message.delete()
        except Exception:
            pass
        return

    # Check if already saved
    existing = get_channel(chat_id)
    if existing:
        display = channel_display_name(existing)
        await show_error(f"⚠️ <b>{display}</b> is already in your channels list!")
        try:
            await message.delete()
        except Exception:
            pass
        return

    # Verify bot can actually post to the channel by sending a test
    # get_chat_member is unreliable for private channels (returns "member" even for admins)
    try:
        test_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Bot connected successfully! (This message will be deleted)",
        )
        await context.bot.delete_message(chat_id=chat_id, message_id=test_msg.message_id)
    except Exception as e:
        logger.warning(f"Bot cannot post to {chat_id}: {e}")
        await show_error(
            "❌ <b>I can't post to that channel/group!</b>\n\n"
            "Please make sure I'm added as an <b>admin</b> with <b>Post Messages</b> permission, then forward again."
        )
        try:
            await message.delete()
        except Exception:
            pass
        return

    # Save to DB
    from db.mongo import get_all_channels
    is_first = len(get_all_channels()) == 0
    add_channel(chat_id, title, username, is_default=is_first)

    display = f"@{username}" if username else title

    await context.bot.edit_message_text(
        chat_id=user_id,
        message_id=control_message_id,
        text=(
            f"✅ <b>Channel Added!</b>\n\n"
            f"📢 <b>Name:</b> {title}\n"
            f"🔗 <b>Handle:</b> {'@' + username if username else 'Private (no @username)'}\n"
            f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
            f"{'⭐ Set as default (first channel)' if is_first else ''}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=channel_picker_keyboard(),
    )

    # Update session step back
    from db.mongo import save_session
    save_session(user_id, {**session, "step": "channel_select", "control_message_id": control_message_id})

    try:
        await message.delete()
    except Exception:
        pass
