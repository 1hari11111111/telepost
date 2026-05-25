from telegram import Message
from config import OWNER_ID


def is_owner(user_id: int) -> bool:
    """Check if the user is the bot owner."""
    return user_id == OWNER_ID


def get_content_type(message: Message) -> str:
    """Detect the type of content in a message."""
    if message.text:
        return "text"
    elif message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.document:
        return "document"
    elif message.audio:
        return "audio"
    elif message.voice:
        return "voice"
    elif message.animation:
        return "animation"
    elif message.sticker:
        return "sticker"
    elif message.poll:
        return "poll"
    elif message.video_note:
        return "video_note"
    return "unknown"


def channel_display_name(channel: dict) -> str:
    """Return a display-friendly name for a channel."""
    if channel.get("username"):
        return f"@{channel['username']}"
    return channel.get("title", str(channel.get("chat_id", "Unknown")))


def build_session_from_message(message: Message) -> dict:
    """
    Extract all needed fields from the incoming message so we can
    replay/forward it later without holding the Message object in MongoDB.
    """
    content_type = get_content_type(message)

    session = {
        "content_type": content_type,
        "caption": message.caption or message.text or None,
        "caption_entities": (
            [e.to_dict() for e in message.caption_entities]
            if message.caption_entities else
            [e.to_dict() for e in message.entities] if message.entities else []
        ),
        "media_group_id": message.media_group_id,
        # Store the raw message_id so we can forward it
        "source_message_id": message.message_id,
        "source_chat_id": message.chat_id,
        # Post options (toggled by user)
        "options": {
            "silent": False,
            "pin": False,
            "no_preview": False,
        },
        "selected_channel": None,
        "step": "channel_select",
        "control_message_id": None,
        # Store file_ids for direct sending (avoids forward branding)
        "file_id": _extract_file_id(message, content_type),
    }
    return session


def _extract_file_id(message: Message, content_type: str):
    """Extract file_id from message based on type."""
    if content_type == "photo":
        return message.photo[-1].file_id  # largest size
    elif content_type == "video":
        return message.video.file_id
    elif content_type == "document":
        return message.document.file_id
    elif content_type == "audio":
        return message.audio.file_id
    elif content_type == "voice":
        return message.voice.file_id
    elif content_type == "animation":
        return message.animation.file_id
    elif content_type == "sticker":
        return message.sticker.file_id
    elif content_type == "video_note":
        return message.video_note.file_id
    return None
