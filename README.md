# 📬 Telegram Post Bot

A personal Telegram bot that lets you send any content to it and post it to your saved channels or groups — with inline controls, no clutter.

---

## ✨ Features

- Post **text, photos, videos, documents, audio, voice, GIFs, stickers, polls, video notes, albums**
- **Add channels by forwarding** a message from them (no manual ID needed)
- **Inline edit mode** — one control message that updates in place, no chat spam
- **Post options** — Silent, Pin, Disable Preview (toggleable per post)
- **Channel management** — add, remove, set default
- **Owner-only access** — only you can use the bot

---

## 🗂 Project Structure

```
telegram-post-bot/
├── bot.py                 # Entry point
├── config.py              # Environment variable loading
├── handlers/
│   ├── channels.py        # /start, /channels, /cancel commands
│   ├── content.py         # Incoming message handler + add-channel flow
│   └── posting.py         # Callback handler + actual posting logic
├── db/
│   └── mongo.py           # MongoDB operations
├── keyboards/
│   └── inline.py          # All inline keyboards
├── utils/
│   └── helpers.py         # Utility functions
├── requirements.txt
├── Procfile               # Heroku config
├── runtime.txt            # Python version for Heroku
└── .env.example
```

---

## 🚀 Setup Guide

### 1. Create your Bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the steps
3. Copy the **Bot Token**

### 2. Get your Telegram User ID

1. Open [@userinfobot](https://t.me/userinfobot)
2. Send `/start`
3. Copy your **Id** number

### 3. Set up MongoDB Atlas

1. Go to [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster
3. Create a database user with read/write access
4. Whitelist all IPs (`0.0.0.0/0`) for Heroku compatibility
5. Click **Connect → Drivers** and copy the URI
   - It looks like: `mongodb+srv://user:pass@cluster.mongodb.net/telegram_post_bot`

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in:

```
BOT_TOKEN=your_bot_token
MONGO_URI=your_mongodb_atlas_uri
OWNER_ID=your_telegram_user_id
```

---

## ☁️ Deploy to Heroku

### Option A — Heroku CLI

```bash
# Login
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set MONGO_URI=your_mongodb_uri
heroku config:set OWNER_ID=your_user_id
heroku config:set WEBHOOK_URL=https://your-app-name.herokuapp.com

# Push code
git init
git add .
git commit -m "Initial commit"
git push heroku main

# Scale the web dyno
heroku ps:scale web=1
```

### Option B — Heroku Dashboard (GitHub Deploy)

1. Push this repo to GitHub
2. Go to [heroku.com](https://heroku.com) → New App
3. Connect your GitHub repo
4. Go to **Settings → Config Vars** and add:
   - `BOT_TOKEN`
   - `MONGO_URI`
   - `OWNER_ID`
   - `WEBHOOK_URL` = `https://your-app-name.herokuapp.com`
5. Go to **Deploy → Manual Deploy → Deploy Branch**

---

## 💻 Run Locally (for testing)

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file from example
cp .env.example .env
# Fill in your values (leave WEBHOOK_URL empty for polling mode)

# Run
python bot.py
```

> When `WEBHOOK_URL` is not set, the bot runs in **polling mode** — perfect for local testing.

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message + main menu |
| `/channels` | View and manage saved channels |
| `/cancel` | Cancel current action |

---

## 📨 Adding a Channel

1. Add the bot as an **admin** in your channel/group (with Post Messages permission)
2. Send `/start` or any content to the bot
3. Tap **➕ Add New Channel / Group**
4. **Forward any message** from that channel/group to the bot
5. Done! ✅

---

## 📝 Notes

- **Private channels** are supported — they'll be saved by ID (no @username shown)
- **Albums (media groups)** are forwarded as-is to preserve the group
- **Polls** are forwarded as-is (Telegram API limitation)
- The bot uses **webhook mode** on Heroku and **polling mode** locally automatically
