import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in environment variables")
if not OWNER_ID:
    raise ValueError("OWNER_ID is not set in environment variables")
