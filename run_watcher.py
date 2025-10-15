import asyncio
import os
import json
from telegram import Bot
import reddit_helper
from find_duplicate_helper import find_duplicates

SAVE_DIR = os.environ.get("SAVE_DIR", "/mnt/truenas-bot")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

async def main():
    # Invia il bot solo se esiste notify_user
    notify_user_file = os.path.join(SAVE_DIR, "reddit_notify_user.txt")
    bot = None
    if os.path.exists(notify_user_file):
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
        except Exception as e:
            print(f"Impossibile inizializzare Telegram Bot: {e}")
    # reddit_watcher_once richiede un duplicate_handler asincrono
    async def duplicate_handler():
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, find_duplicates, SAVE_DIR)

    result = await reddit_helper.reddit_watcher_once(SAVE_DIR, duplicate_handler, bot=bot)
    print(f"Watcher completed: {result}")

if __name__ == "__main__":
    asyncio.run(main())
