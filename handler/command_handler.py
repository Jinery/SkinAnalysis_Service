from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from data.enums import APIStatus, Platform
from database.database_worker import DatabaseWorker
from transflate.translator import translator

async def start_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    telegram_lang = user.language_code if user.language_code else "en"
    lang = "ru" if telegram_lang == "ru" else "en"
    await DatabaseWorker.get_or_update_user(update.effective_user.id, lang)

    last_name = f" {user.last_name}" if user.last_name else ""

    await update.message.reply_text(translator.translate(
        "commands.start", Platform.TELEGRAM, lang,
        first_name=user.first_name, last_name=last_name
    ), parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    lang = user.language_code if user.language_code == "ru" else "en"

    await update.message.reply_text(
        translator.translate("commands.help", Platform.TELEGRAM, lang),
        parse_mode=ParseMode.HTML,
    )


async def create_new_connection_id_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    lang = user.language_code if user.language_code == "ru" else "en"

    await DatabaseWorker.get_or_update_user(user_id, update.message.from_user.language_code)

    try:
        args = update.message.text.split()

        if len(args) < 2:
            await update.message.reply_text(
                translator.translate("commands.new_connection", Platform.TELEGRAM, lang),
                parse_mode=ParseMode.HTML
            )
            return

        connection_name = args[1].strip()

        max_devices = 3
        if len(args) >= 3:
            try:
                max_devices = int(args[2])
                if max_devices <= 0:
                    await update.message.reply_text(
                        translator.translate("errors.connections.not_positive", Platform.TELEGRAM, lang),
                        parse_mode=ParseMode.HTML
                    )
                    return
                if max_devices > 10:
                    await update.message.reply_text(
                        translator.translate("attentions.connections.max_limit", Platform.TELEGRAM, lang),
                        parse_mode=ParseMode.HTML
                    )
                    max_devices = 10
            except ValueError:
                await update.message.reply_text(
                    translator.translate("errors.connections.not_number", Platform.TELEGRAM, lang),
                    parse_mode=ParseMode.HTML
                )
                return

        connection, status = await DatabaseWorker.create_connection(user_id, connection_name, max_devices)

        if status is APIStatus.CONFLICT:
            await update.message.reply_text(
                translator.translate("errors.connections.already_exists", Platform.TELEGRAM, lang),
                parse_mode=ParseMode.HTML
            )

        if status is APIStatus.SUCCESS and connection is not None:
            await update.message.reply_text(
                translator.translate(
                    "success.connections.created",
                    Platform.TELEGRAM,
                    lang,
                    connection_name=connection.name,
                    connection_id=connection.connection_id,
                    max_devices=max_devices
                ),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        else: await update.message.reply_text(translator.translate("errors.connections.general", Platform.TELEGRAM, lang),)

    except IndexError:
        await update.message.reply_text(
            translator.translate("errors.connections.no_name", Platform.TELEGRAM, lang),
            parse_mode=ParseMode.HTML
        )
    except ValueError as ve:
        await update.message.reply_text(
            translator.translate("errors.connections.input", Platform.TELEGRAM, lang, error=str(ve)),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            translator.translate("errors.connections.try_later", Platform.TELEGRAM, lang),
            parse_mode=ParseMode.HTML
        )

async def remove_connection_by_name_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    lang = user.language_code if user.language_code == "ru" else "en"
    await DatabaseWorker.get_or_update_user(user_id, update.message.from_user.language_code)

    try:
        args = update.message.text.split()
        if len(args) < 2:
            await update.message.reply_text(
                translator.translate("commands.remove_connection", Platform.TELEGRAM, lang),
                parse_mode=ParseMode.HTML
            )
            return

        connection_name = args[1].strip()
        status = await DatabaseWorker.remove_connection(user_id, connection_name)
        match status:
            case APIStatus.SUCCESS:
                await update.message.reply_text(
                    translator.translate("success.connections.removed", Platform.TELEGRAM, lang,
                                         connection_name=connection_name),
                    ParseMode.HTML
                )
            case APIStatus.NOT_FOUND:
                await update.message.reply_text(
                    translator.translate("errors.connections.not_found", Platform.TELEGRAM, lang),
                )
    except Exception as e:
        print(e)
        await update.message.reply_text(
            translator.translate("errors.connections.remove_error", Platform.TELEGRAM, lang),
        )

async def get_user_connections_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id
    lang = user.language_code if user.language_code == "ru" else "en"
    await DatabaseWorker.get_or_update_user(user_id, update.message.from_user.language_code)

    try:
        connections = await DatabaseWorker.get_user_connections(user_id)
        if not connections:
            await update.message.reply_text(
                translator.translate("attentions.connections.no_connections", Platform.TELEGRAM, lang),
                parse_mode=ParseMode.HTML
            )
            return
        connections_list = []
        for index, connection in enumerate(connections):
            active_devices_count = sum(1 for device in connection.devices if device.is_active)

            if lang == "ru":
                created_at = connection.created_at.strftime('%d.%m.%Y %H:%M')
            else:
                created_at = connection.created_at.strftime('%m/%d/%Y %H:%M')

            item_text = translator.translate(
                "commands.my_connections.item",
                Platform.TELEGRAM,
                lang,
                index=index + 1,
                name=connection.name,
                connection_id=connection.connection_id,
                active=active_devices_count,
                max=connection.max_devices,
                created_at=created_at
            )
            connections_list.append(item_text)

        response = translator.translate("commands.my_connections.header", Platform.TELEGRAM, lang) + "\n\n".join(connections_list)
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(e)
        await update.message.reply_text(translator.translate("errors.connections.error_getting", Platform.TELEGRAM, lang),)