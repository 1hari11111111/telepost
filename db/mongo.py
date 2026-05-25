from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["telegram_post_bot"]

channels_col = db["channels"]
sessions_col = db["sessions"]


# ─── Channel Operations ────────────────────────────────────────────────────────

def get_all_channels():
    return list(channels_col.find({}, {"_id": 0}))


def get_channel(chat_id: int):
    return channels_col.find_one({"chat_id": chat_id}, {"_id": 0})


def add_channel(chat_id: int, title: str, username: str = None, is_default: bool = False):
    if is_default:
        channels_col.update_many({}, {"$set": {"is_default": False}})
    channels_col.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "chat_id": chat_id,
            "title": title,
            "username": username,
            "is_default": is_default,
        }},
        upsert=True,
    )


def remove_channel(chat_id: int):
    channels_col.delete_one({"chat_id": chat_id})


def set_default_channel(chat_id: int):
    channels_col.update_many({}, {"$set": {"is_default": False}})
    channels_col.update_one({"chat_id": chat_id}, {"$set": {"is_default": True}})


def get_default_channel():
    return channels_col.find_one({"is_default": True}, {"_id": 0})


# ─── Session Operations ────────────────────────────────────────────────────────

def get_session(user_id: int):
    return sessions_col.find_one({"user_id": user_id}, {"_id": 0})


def save_session(user_id: int, data: dict):
    sessions_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, **data}},
        upsert=True,
    )


def clear_session(user_id: int):
    sessions_col.delete_one({"user_id": user_id})
