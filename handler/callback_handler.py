from telegram import Update
from telegram.ext import CallbackContext

from handler.auth_handler import handle_disconnect_device, handle_confirm_disconnect, handle_cancel_disconnect
from storage.callback_storage import callback_storage


async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith(callback_storage.get_prefix()):
        stored_data = await callback_storage.get(data)
        if not stored_data:
            await query.edit_message_text("Ссылка устарела")
            return
        data = stored_data
        print(data)

    patrs = data.split(":")
    action = patrs[0]

    try:
        if action == "disconnect_device":
            await handle_disconnect_device(query, patrs[1:])
        elif action == "confirm_disconnect":
            await handle_confirm_disconnect(query, patrs[1:])
        elif action == "cancel_disconnect":
            await handle_cancel_disconnect(query)
    except Exception as e:
        print(e)