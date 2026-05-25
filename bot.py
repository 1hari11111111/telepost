import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import BOT_TOKEN
from handlers.channels import cmd_start, cmd_channels, cmd_cancel
from handlers.content import handle_incoming
from handlers.posting import handle_callback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ── Commands ───────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("channels", cmd_channels))
    app.add_handler(CommandHandler("cancel",   cmd_cancel))

    # ── Inline button callbacks ────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ── All incoming message types ─────────────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        handle_incoming,
    ))

    # ── Webhook (Heroku) vs Polling (local) ───────────────────────────────────
    port = int(os.environ.get("PORT", 8443))
    webhook_url = os.environ.get("WEBHOOK_URL", "")  # e.g. https://yourapp.herokuapp.com

    if webhook_url:
        logger.info(f"Starting webhook on port {port} → {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/{BOT_TOKEN}",
            url_path=BOT_TOKEN,
        )
    else:
        logger.info("No WEBHOOK_URL set — starting polling (local dev mode)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
