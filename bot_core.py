import asyncio

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from database.database import init_db
from handler.command_handler import start_command
from handler.photo_handler import handle_user_photo


def build_bot_application(token: str) -> Application:
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_user_photo))

    return application

async def start_polling_bot(application):
    try:
        await init_db()
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

    except asyncio.CancelledError:
        print("Bot polling cancelled")
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()