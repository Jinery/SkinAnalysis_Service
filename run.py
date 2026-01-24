import os
import uvicorn
import asyncio
from dotenv import load_dotenv

from bot_core import build_bot_application, start_polling_bot
from api.main import app as fastapi_app

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))


async def start_api_server_async():
    print(f"Starting FastAPI Server on http://{API_HOST}:{API_PORT}...")

    config = uvicorn.Config(
        fastapi_app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        reload=False
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_all():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not found.")
        return

    application = build_bot_application(TOKEN)

    bot_task = asyncio.create_task(start_polling_bot(application))
    api_task = asyncio.create_task(start_api_server_async())

    await asyncio.wait([bot_task, api_task], return_when=asyncio.FIRST_COMPLETED)


async def start_bot_only_async():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found.")

    application = build_bot_application(TOKEN)
    await start_polling_bot(application)


def main():
    try:
        asyncio.run(run_all())
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()