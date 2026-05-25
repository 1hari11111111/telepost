from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db.mongo import get_all_channels


def channel_picker_keyboard():
    """Inline keyboard showing all saved channels + Add New."""
    channels = get_all_channels()
    buttons = []

    for ch in channels:
        label = f"{'⭐ ' if ch.get('is_default') else ''}{'@' + ch['username'] if ch.get('username') else ch['title']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"pick_channel:{ch['chat_id']}")])

    buttons.append([InlineKeyboardButton("➕ Add New Channel / Group", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def post_options_keyboard(silent=False, pin=False, no_preview=False):
    """Inline keyboard for post options."""
    silent_label  = f"{'✅' if silent else '🔇'} Silent"
    pin_label     = f"{'✅' if pin else '📌'} Pin"
    preview_label = f"{'✅' if no_preview else '🔗'} No Preview"

    buttons = [
        [
            InlineKeyboardButton(silent_label,  callback_data="toggle:silent"),
            InlineKeyboardButton(pin_label,     callback_data="toggle:pin"),
        ],
        [
            InlineKeyboardButton(preview_label, callback_data="toggle:no_preview"),
        ],
        [
            InlineKeyboardButton("✅ Post Now", callback_data="post_now"),
            InlineKeyboardButton("🔙 Back",    callback_data="back_to_channels"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def manage_channels_keyboard():
    """Keyboard for channel management."""
    channels = get_all_channels()
    buttons = []

    for ch in channels:
        label = f"{'@' + ch['username'] if ch.get('username') else ch['title']}"
        buttons.append([
            InlineKeyboardButton(f"🗑 {label}", callback_data=f"del_channel:{ch['chat_id']}"),
            InlineKeyboardButton(f"⭐ Default", callback_data=f"default_channel:{ch['chat_id']}"),
        ])

    buttons.append([InlineKeyboardButton("➕ Add New Channel / Group", callback_data="add_channel_manage")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)


def main_menu_keyboard():
    """Main menu keyboard."""
    buttons = [
        [InlineKeyboardButton("📋 Manage Channels", callback_data="manage_channels")],
        [InlineKeyboardButton("❌ Close", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def done_keyboard():
    """Post done keyboard."""
    buttons = [
        [InlineKeyboardButton("🔁 Post to Another Channel", callback_data="post_another")],
        [InlineKeyboardButton("✅ Done", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def add_channel_cancel_keyboard():
    """Simple cancel keyboard used during add channel flow."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_channels")]])
