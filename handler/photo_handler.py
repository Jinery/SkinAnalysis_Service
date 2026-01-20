from telegram import Update
from telegram.ext import CallbackContext

from data.enums import ProcessImageStatus
from files.file_manager import file_manager
from service.analysis_service import AnalysisService


async def handle_user_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.message.photo[-1] is not None:
        photo = await update.message.photo[-1].get_file()
        photo_bytes = await photo.download_as_bytearray()

        path = file_manager.save_temporary_photo(photo_bytes, user_id)
        check_message = await update.message.reply_text("🔍 Просматриваю фото...")

        result = await AnalysisService.analyze(user_id, path)
        if result.get_status() == ProcessImageStatus.SUCCESS:
            with open(result.get_image_path(), "rb") as file:
                try:
                    await update.message.reply_photo(
                        photo=file,
                        caption=result.get_message() if result.get_message() else "✅ Анализ завершен.",
                    )
                    await check_message.delete()
                except Exception as e:
                    print(f"Error on sending photo: {e}")
                    await check_message.edit_text(f"😔 Увы, отправить фото не удалось.")
        elif result.get_status() == ProcessImageStatus.CLEANED:
            await check_message.edit_text(f"✅ {result.get_message()}")
        else:
            await check_message.edit_text(f"❌ {result.get_message()}")