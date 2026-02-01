import os
from functools import lru_cache

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.constants import ParseMode
from telegram.ext import Application

from data.enums import APIStatus, Platform
from database.database_worker import DatabaseWorker
from storage.callback_storage import callback_storage
from transflate.translator import translator

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@lru_cache
def get_application() -> Application:
    return Application.builder().token(TOKEN).build()

async def notify_device_connection(
    user_id: int,
    device_platform: str,
    device_uid: str,
    device_name: str,
    device_model: str,
    device_os_version: str,
    connection_id: str,
):
    app = get_application()

    try:
        if not app.running:
            await app.initialize()
            await app.start()

        lang = await DatabaseWorker.get_language_by_user_id(user_id)

        not_specified = translator.translate("success.auth.not_specified", Platform.API, lang)
        params = {
            "device_name": device_name or translator.translate("success.auth.no_name", Platform.TELEGRAM, lang),
            "device_platform": device_platform or not_specified,
            "device_model": device_model or not_specified,
            "device_os_version": device_os_version or not_specified,
            "device_uid": device_uid
        }

        message_text = translator.translate(
            "success.auth.device_registered",
            Platform.TELEGRAM,
            lang=lang,
            **params
        )

        callback_data = await callback_storage.store(f"disconnect_device:{device_uid}:{connection_id}")
        print(callback_data)

        keyboard = [[
            InlineKeyboardButton(
                translator.translate("callbacks.auth.disconnect_device", Platform.TELEGRAM, lang),
                callback_data=callback_data,
            )
        ]]

        await app.bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(e)
    finally:
        if app.running:
            await app.stop()
            await app.shutdown()

async def handle_disconnect_device(query: CallbackQuery, parts: list[str]):
    if len(parts) < 2:
        print("Not enough arguments")
        return

    device_uid = parts[0]
    connection_id = parts[1]

    lang = await DatabaseWorker.get_language_by_connection_id(connection_id)

    first_callback_data = await callback_storage.store(f"confirm_disconnect:{device_uid}:{connection_id}")

    keyboard = [
        [
            InlineKeyboardButton("✅ " + translator.translate("callbacks.auth.confirm_disconnect_device", Platform.API, lang), callback_data=first_callback_data),
            InlineKeyboardButton("❌ " + translator.translate("callbacks.auth.reject_disconnect_device", Platform.API, lang), callback_data="cancel_disconnect")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = translator.translate(
        "callbacks.auth.reject_disconnect_device",
        Platform.TELEGRAM,
        lang,
        device_uid
    )

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def handle_confirm_disconnect(query, parts):
    if len(parts) < 2:
        print("Not enough arguments")
        return

    device_uid = parts[0]
    connection_id = parts[1]

    lang = await DatabaseWorker.get_language_by_connection_id(connection_id)
    status = await DatabaseWorker.disconnect_device(device_uid, connection_id)

    if status == APIStatus.SUCCESS:
        await query.edit_message_text(
            text=translator.translate("success.auth.device_disconnected", Platform.TELEGRAM, lang),
            parse_mode=ParseMode.HTML,
        )
    elif status == APIStatus.NOT_FOUND:
        await query.edit_message_text(
            translator.translate("errors.auth.device_not_found", Platform.TELEGRAM, lang),
            parse_mode=ParseMode.HTML
        )
    else:
        await query.edit_message_text(
            translator.translate("errors.auth.disconnect_error", Platform.TELEGRAM, lang),
            parse_mode=ParseMode.HTML,
        )

async def handle_cancel_disconnect(query, lang: str):
    await query.edit_message_text(
        translator.translate("success.auth.device_disconnect_canceled", Platform.TELEGRAM, lang),
        parse_mode=ParseMode.HTML
    )
