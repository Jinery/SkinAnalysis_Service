import os
import secrets
from functools import lru_cache

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.constants import ParseMode
from telegram.ext import Application

from data.enums import APIStatus
from database.database import Device
from database.database_worker import DatabaseWorker
from storage.callback_storage import callback_storage

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
        message = (
            f"🔔 <b>Подключение нового устройства!</b>\n\n"
            f"📱 <b>Устройство:</b> {device_name or 'Без имени'}\n"
            f"🖥️ <b>Платформа:</b> {device_platform or 'Не указана'}\n"
            f"📱 <b>Модель:</b> {device_model or 'Не указана'}\n"
            f"🔢 <b>Версия ОС:</b> {device_os_version or 'Не указана'}\n"
            f"🆔 <b>UID:</b> <code>{device_uid}</code>\n"
            f"❗️ Если это не вы, отключите устройство!"
        )

        callback_data = await callback_storage.store(f"disconnect_device:{device_uid}:{connection_id}")
        print(callback_data)

        keyboard = [[
            InlineKeyboardButton(
                "Отключить устройство",
                callback_data=callback_data,
            )
        ]]

        await app.bot.send_message(
            chat_id=user_id,
            text=message,
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
        await query.edit_message_text("❌ Ошибка формата команды")
        return

    device_uid = parts[0]
    connection_id = parts[1]

    first_callback_data = await callback_storage.store(f"confirm_disconnect:{device_uid}:{connection_id}")

    keyboard = [
        [
            InlineKeyboardButton("✅ Да, отключить", callback_data=first_callback_data),
            InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_disconnect")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"⚠️ <b>Подтверждение отключения</b>\n\n"
        f"Ты уверен, что хочешь отключить устройство?\n"
        f"<code>{device_uid}</code>\n\n"
        f"После отключения устройство не сможет подключаться.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def handle_confirm_disconnect(query, parts):
    if len(parts) < 2:
        await query.edit_message_text("❌ Ошибка формата команды")
        return

    device_uid = parts[0]
    connection_id = parts[1]

    status = await DatabaseWorker.disconnect_device(device_uid, connection_id)

    if status == APIStatus.SUCCESS:
        await query.edit_message_text(
            f"✅ <b>Устройство отключено!</b>\n\n"
            f"Оно больше не может подключаться к этому аккаунту.",
            parse_mode=ParseMode.HTML,
        )
    elif status == APIStatus.NOT_FOUND:
        await query.edit_message_text(
            f"❌ <b>Устройство не найдено</b>\n\n"
            f"Возможно, оно уже было отключено.",
            parse_mode=ParseMode.HTML
        )
    else:
        await query.edit_message_text(
            f"Не удалось отключить устройство.",
            parse_mode=ParseMode.HTML,
        )

async def handle_cancel_disconnect(query):
    await query.edit_message_text(
        "🚫 <b>Отключение отменено</b>\n\n"
        "Устройство остаётся активным.",
        parse_mode=ParseMode.HTML
    )
