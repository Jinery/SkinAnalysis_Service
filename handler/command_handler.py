from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext


async def start_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    last_name = f" {user.last_name}" if user.last_name else ""

    welcome_text = (
        f"Привет, <b>{user.first_name}{last_name}</b>👋\n\n"
        f"Пришли мне фото с подозрительной зоной. Я проанализирую его "
        f"и постараюсь определить наличие патологии."
    )

    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)
