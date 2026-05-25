import logging
from telegram import Update, MessageEntity
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

from db.mongo import get_session, save_session, clear_session, get_channel
from keyboards.inline import post_options_keyboard, channel_picker_keyboard, done_keyboard, add_channel_cancel_keyboard
from utils.helpers import channel_display_name

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Master callback query handler — routes all inline button presses."""
    query = update.callback_query
    await query.answer()

    user_id  = query.from_user.id
    data     = query.data
    chat_id  = query.message.chat_id
    msg_id   = query.message.message_id

    session = get_session(user_id)

    # ── Channel picked ─────────────────────────────────────────────────────────
    if data.startswith("pick_channel:"):
        channel_chat_id = int(data.split(":")[1])
        channel = get_channel(channel_chat_id)
        if not channel:
            await query.edit_message_text("⚠️ Channel not found. Please try again.")
            return

        opts = session.get("options", {"silent": False, "pin": False, "no_preview": False})
        save_session(user_id, {
            **session,
            "selected_channel": channel_chat_id,
            "step": "options_select",
        })

        display = channel_display_name(channel)
        await query.edit_message_text(
            text=f"📢 Posting to: <b>{display}</b>\n\nChoose post options:",
            parse_mode=ParseMode.HTML,
            reply_markup=post_options_keyboard(
                silent=opts.get("silent", False),
                pin=opts.get("pin", False),
                no_preview=opts.get("no_preview", False),
            ),
        )

    # ── Toggle options ─────────────────────────────────────────────────────────
    elif data.startswith("toggle:"):
        if not session:
            await query.edit_message_text("⚠️ Session expired. Please send your content again.")
            return

        key = data.split(":")[1]
        opts = session.get("options", {"silent": False, "pin": False, "no_preview": False})
        opts[key] = not opts.get(key, False)
        save_session(user_id, {**session, "options": opts})

        channel = get_channel(session.get("selected_channel"))
        display = channel_display_name(channel) if channel else "Unknown"

        await query.edit_message_reply_markup(
            reply_markup=post_options_keyboard(
                silent=opts.get("silent", False),
                pin=opts.get("pin", False),
                no_preview=opts.get("no_preview", False),
            )
        )

    # ── Post now ───────────────────────────────────────────────────────────────
    elif data == "post_now":
        await _do_post(update, context, session, chat_id, msg_id, user_id)

    # ── Back to channel picker ─────────────────────────────────────────────────
    elif data == "back_to_channels":
        save_session(user_id, {**session, "step": "channel_select", "selected_channel": None})
        await query.edit_message_text(
            "📦 <b>Content ready!</b>\n\nWhere do you want to post this?",
            parse_mode=ParseMode.HTML,
            reply_markup=channel_picker_keyboard(),
        )

    # ── Add channel (from posting flow) ───────────────────────────────────────
    elif data in ("add_channel", "add_channel_manage"):
        save_session(user_id, {
            **(session or {}),
            "step": "adding_channel",
            "control_message_id": msg_id,
        })
        await query.edit_message_text(
            "📨 <b>Add Channel / Group</b>\n\n"
            "Forward any message from the channel or group you want to add.\n\n"
            "Make sure I'm already an <b>admin</b> there first!",
            parse_mode=ParseMode.HTML,
            reply_markup=add_channel_cancel_keyboard(),
        )

    # ── Manage channels ────────────────────────────────────────────────────────
    elif data == "manage_channels":
        from keyboards.inline import manage_channels_keyboard
        channels = _get_all_channels_for_manage()
        if not channels:
            text = "📋 <b>No channels saved yet.</b>\n\nForward a message from a channel to add it."
        else:
            text = "📋 <b>Your Channels</b>\n\nTap 🗑 to remove · ⭐ to set as default:"
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=manage_channels_keyboard(),
        )

    # ── Delete channel ─────────────────────────────────────────────────────────
    elif data.startswith("del_channel:"):
        from db.mongo import remove_channel
        from keyboards.inline import manage_channels_keyboard
        ch_id = int(data.split(":")[1])
        channel = get_channel(ch_id)
        remove_channel(ch_id)
        display = channel_display_name(channel) if channel else str(ch_id)
        await query.edit_message_text(
            f"🗑 <b>{display}</b> removed.\n\n📋 <b>Your Channels:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=manage_channels_keyboard(),
        )

    # ── Set default channel ────────────────────────────────────────────────────
    elif data.startswith("default_channel:"):
        from db.mongo import set_default_channel
        from keyboards.inline import manage_channels_keyboard
        ch_id = int(data.split(":")[1])
        channel = get_channel(ch_id)
        set_default_channel(ch_id)
        display = channel_display_name(channel) if channel else str(ch_id)
        await query.edit_message_text(
            f"⭐ <b>{display}</b> set as default.\n\n📋 <b>Your Channels:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=manage_channels_keyboard(),
        )

    # ── Post to another channel ────────────────────────────────────────────────
    elif data == "post_another":
        save_session(user_id, {
            **(session or {}),
            "step": "channel_select",
            "selected_channel": None,
        })
        await query.edit_message_text(
            "📦 <b>Post to another channel?</b>\n\nWhere do you want to post?",
            parse_mode=ParseMode.HTML,
            reply_markup=channel_picker_keyboard(),
        )

    # ── Cancel ─────────────────────────────────────────────────────────────────
    elif data == "cancel":
        clear_session(user_id)
        await query.edit_message_text("✅ Done! Send me new content anytime.")

    # ── Back to main ───────────────────────────────────────────────────────────
    elif data == "back_to_main":
        from keyboards.inline import main_menu_keyboard
        await query.edit_message_text(
            "🤖 <b>Bot Menu</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(),
        )


def _get_all_channels_for_manage():
    from db.mongo import get_all_channels
    return get_all_channels()


async def _do_post(update, context, session, chat_id, msg_id, user_id):
    """Actually send the content to the selected channel."""
    query = update.callback_query

    if not session:
        await query.edit_message_text("⚠️ Session expired. Please send your content again.")
        return

    target_channel_id = session.get("selected_channel")
    if not target_channel_id:
        await query.edit_message_text("⚠️ No channel selected.")
        return

    channel = get_channel(target_channel_id)
    if not channel:
        await query.edit_message_text("⚠️ Channel not found.")
        return

    opts          = session.get("options", {})
    silent        = opts.get("silent", False)
    pin           = opts.get("pin", False)
    no_preview    = opts.get("no_preview", False)
    content_type  = session.get("content_type")
    file_id       = session.get("file_id")
    caption       = session.get("caption")
    source_msg_id = session.get("source_message_id")
    source_chat   = session.get("source_chat_id")
    media_group   = session.get("media_group_id")

    display = channel_display_name(channel)

    try:
        sent_message = None

        # ── Media group (album) — forward as-is ──────────────────────────────
        if media_group:
            # For media groups we forward the original message
            sent_message = await context.bot.forward_message(
                chat_id=target_channel_id,
                from_chat_id=source_chat,
                message_id=source_msg_id,
                disable_notification=silent,
            )

        # ── Text ──────────────────────────────────────────────────────────────
        elif content_type == "text":
            sent_message = await context.bot.send_message(
                chat_id=target_channel_id,
                text=caption or "",
                disable_notification=silent,
                disable_web_page_preview=no_preview,
            )

        # ── Photo ─────────────────────────────────────────────────────────────
        elif content_type == "photo":
            sent_message = await context.bot.send_photo(
                chat_id=target_channel_id,
                photo=file_id,
                caption=caption,
                disable_notification=silent,
            )

        # ── Video ─────────────────────────────────────────────────────────────
        elif content_type == "video":
            sent_message = await context.bot.send_video(
                chat_id=target_channel_id,
                video=file_id,
                caption=caption,
                disable_notification=silent,
            )

        # ── Document ──────────────────────────────────────────────────────────
        elif content_type == "document":
            sent_message = await context.bot.send_document(
                chat_id=target_channel_id,
                document=file_id,
                caption=caption,
                disable_notification=silent,
            )

        # ── Audio ─────────────────────────────────────────────────────────────
        elif content_type == "audio":
            sent_message = await context.bot.send_audio(
                chat_id=target_channel_id,
                audio=file_id,
                caption=caption,
                disable_notification=silent,
            )

        # ── Voice ─────────────────────────────────────────────────────────────
        elif content_type == "voice":
            sent_message = await context.bot.send_voice(
                chat_id=target_channel_id,
                voice=file_id,
                caption=caption,
                disable_notification=silent,
            )

        # ── Animation (GIF) ───────────────────────────────────────────────────
        elif content_type == "animation":
            sent_message = await context.bot.send_animation(
                chat_id=target_channel_id,
                animation=file_id,
                caption=caption,
                disable_notification=silent,
            )

        # ── Sticker ───────────────────────────────────────────────────────────
        elif content_type == "sticker":
            sent_message = await context.bot.send_sticker(
                chat_id=target_channel_id,
                sticker=file_id,
                disable_notification=silent,
            )

        # ── Video Note ────────────────────────────────────────────────────────
        elif content_type == "video_note":
            sent_message = await context.bot.send_video_note(
                chat_id=target_channel_id,
                video_note=file_id,
                disable_notification=silent,
            )

        # ── Poll — must forward (polls can't be re-created via API easily) ────
        elif content_type == "poll":
            sent_message = await context.bot.forward_message(
                chat_id=target_channel_id,
                from_chat_id=source_chat,
                message_id=source_msg_id,
                disable_notification=silent,
            )

        else:
            await query.edit_message_text("⚠️ Unsupported content type.")
            return

        # ── Pin if requested ──────────────────────────────────────────────────
        if pin and sent_message:
            try:
                await context.bot.pin_chat_message(
                    chat_id=target_channel_id,
                    message_id=sent_message.message_id,
                    disable_notification=silent,
                )
            except TelegramError as e:
                logger.warning(f"Could not pin message: {e}")

        # ── Success ───────────────────────────────────────────────────────────
        post_link = ""
        if channel.get("username") and sent_message:
            post_link = f"\n🔗 <a href='https://t.me/{channel['username']}/{sent_message.message_id}'>View Post</a>"

        await query.edit_message_text(
            f"✅ <b>Posted to {display}!</b>{post_link}",
            parse_mode=ParseMode.HTML,
            reply_markup=done_keyboard(),
            disable_web_page_preview=True,
        )

        # Keep session alive for "post another" use case
        save_session(user_id, {
            **session,
            "step": "done",
            "control_message_id": msg_id,
        })

    except TelegramError as e:
        logger.error(f"Failed to post: {e}")
        await query.edit_message_text(
            f"❌ <b>Failed to post!</b>\n\n<code>{str(e)}</code>\n\nMake sure I'm an admin in {display}.",
            parse_mode=ParseMode.HTML,
            reply_markup=channel_picker_keyboard(),
        )
