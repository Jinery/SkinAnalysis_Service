import asyncio

from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from database.database import init_db
from handler.callback_handler import handle_callback
from handler.command_handler import start_command, help_command, create_new_connection_id_command, \
    remove_connection_by_name_command, get_user_connections_command
from handler.photo_handler import handle_user_photo


def build_bot_application(token: str) -> Application:
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("newconnection", create_new_connection_id_command))
    application.add_handler(CommandHandler("removeconnection", remove_connection_by_name_command))
    application.add_handler(CommandHandler("myconnections", get_user_connections_command))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_user_photo))

    application.add_handler(CallbackQueryHandler(handle_callback))

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