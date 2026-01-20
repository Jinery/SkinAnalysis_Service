import asyncio
import os

from dotenv import load_dotenv

from bot_core import build_bot_application, start_polling_bot

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_bot():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found.")
    application = build_bot_application(TOKEN)
    await start_polling_bot(application)

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except Exception as e:
        print(e)