from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from data.enums import APIStatus
from database.database_worker import DatabaseWorker


async def start_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    last_name = f" {user.last_name}" if user.last_name else ""

    welcome_text = (
        f"Привет, <b>{user.first_name}{last_name}</b>👋\n\n"
        f"Пришли мне фото с подозрительной зоной. Я проанализирую его "
        f"и постараюсь определить наличие патологии."
    )

    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        ("❔ </b>Как работатьс ботом?</b> ❔\n"
         "Достаточно просто отправить фото с подозрительной для вас зоной, и я сама найду все родинки(если они достаточно хорошо видны) и постарюсь определить наличие паталогии\n\n"
         "❓ <b>Как сделать фото для точного анализа</b> ❓\n"
         "Свет: Используй мягкое дневное освещение. Избегай прямой вспышки (она создает белые блики) и резких теней.\n"
         "Расстояние: Фотографируй с 10-15 см. Родинка должна быть в центре кадра, но не занимать его целиком (мне нужно видеть немного здоровой кожи вокруг для сравнения).\n"
         "Чистота: Кожа должна быть чистой, без пластырей, маркеров или повязок рядом.")
    )


async def create_new_connection_id_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    try:
        args = update.message.text.split()

        if len(args) < 2:
            await update.message.reply_text(
                "⚠️ <b>Для создания нового подключения используй:</b>\n"
                "<code>/newconnection название_подключения [макс_устройства]</code>\n\n"
                "📝 <b>Пример:</b>\n"
                "<code>/newconnection Моё_Первое_Подключение 3</code>",
                parse_mode=ParseMode.HTML
            )
            return

        connection_name = args[1].strip()

        max_devices = 3
        if len(args) >= 3:
            try:
                max_devices = int(args[2])
                if max_devices <= 0:
                    await update.message.reply_text( "❌ Максимальное количество устройств должно быть положительным числом!",
                                                     parse_mode=ParseMode.HTML
                                                     )
                    return
                if max_devices > 10:
                    await update.message.reply_text("Установлено максимальное значение 10 устройств для безопасности.",
                                                    parse_mode=ParseMode.HTML
                                                    )
                    max_devices = 10
            except ValueError:
                await update.message.reply_text( "❌ <b>Ошибка:</b> Максимальное количество устройств должно быть числом!",
                                                 parse_mode=ParseMode.HTML
                                                 )
                return

        connection, status = await DatabaseWorker.create_connection(user_id, connection_name, max_devices)

        if status is APIStatus.CONFLICT:
            await update.message.reply_text(f"⚠️ Подключение с названием <b>{connection_name}</b> уже существует")

        if status is APIStatus.SUCCESS and connection is not None:
            response_message = (
                "✅ <b>НОВОЕ ПОДКЛЮЧЕНИЕ СОЗДАНО!</b>\n\n"
                f"📛 <b>Название:</b> <code>{connection.name}</code>\n"
                f"🔢 <b>ID подключения:</b> <code>{connection.connection_id}</code>\n"
                f"📱 <b>Макс. устройств:</b> {max_devices}\n"
                "ID чувствителен к регистру!\n"
                "Не передавай этот код третьим лицам\n\n"
                "Сохрани это сообщение для быстрого доступа к ID!"
            )

            await update.message.reply_text(
                response_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        else: await update.message.reply_text("❌ Не удалось создать подключение.")

    except IndexError:
        await update.message.reply_text(
            "❌ Не указано название подключения!",
            parse_mode=ParseMode.HTML
        )
    except ValueError as ve:
        await update.message.reply_text(
            f"❌ Ошибка ввода: {str(ve)}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Не удалось создать подключение. Попробуй позже.",
            parse_mode=ParseMode.HTML
        )

async def remove_connection_by_name_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    try:
        args = update.message.text.split()
        if len(args) < 2:
            await update.message.reply_text(
                "<b>Название подключения не указано.</b>\n\n"
                "<b>Для удаления подключения используй:</b>\n"
                "<code>/removeconnection название_подключения</code>\n"
                "📝 <b>Пример:</b>\n"
                "<code>/removeconnection Моё_Первое_Подключение</code>",
                parse_mode=ParseMode.HTML
            )
            return

        connection_name = args[1].strip()
        status = await DatabaseWorker.remove_connection(user_id, connection_name)
        match status:
            case APIStatus.SUCCESS:
                await update.message.reply_text(f"✅ Подключение с названием <b>{connection_name}</b> успешно удалено!",
                                                ParseMode.HTML
                                                )
            case APIStatus.NOT_FOUND:
                await update.message.reply_text("❗️ Подключение с таким наванием не найдено!")
    except Exception as e:
        print(e)
        await update.message.reply_text("❌ Ошибка при удалении подключения.")

async def get_user_connections_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    try:
        connections = await DatabaseWorker.get_user_connections(user_id)
        if not connections:
            await update.message.reply_text("📭 <b>У тебя пока нет подключений.</b>", parse_mode=ParseMode.HTML)
            return
        connections_list = []
        for index, connection in enumerate(connections):
            active_devices_count = sum(1 for device in connection.devices if device.is_active)
            connections_list.append(
                f"<b>{index + 1} {connection.name}</b>\n"
                f"🔑 ID: <code>{connection.connection_id}</code>\n"
                f"📱 Подключённых устройств: {active_devices_count}/{connection.max_devices}\n"
                f"🕐 Создано: {connection.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

        response = (
                "<b>Твои подключения:</b>\n\n"
                + "\n\n".join(connections_list)
        )
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(e)
        await update.message.reply_text("Ошибка при получении твоих подключений")