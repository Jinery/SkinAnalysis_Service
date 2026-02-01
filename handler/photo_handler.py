from telegram import Update
from telegram.ext import CallbackContext

from data.enums import ProcessImageStatus, Platform
from files.file_manager import file_manager
from service.analysis_service import AnalysisService
from transflate.translator import translator


async def handle_user_photo(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id
    lang = user.language_code if user.language_code == "ru" else "en"

    if update.message.photo[-1] is not None:
        photo = await update.message.photo[-1].get_file()
        photo_bytes = await photo.download_as_bytearray()

        path = file_manager.save_temporary_photo(photo_bytes, user_id)
        check_message = await update.message.reply_text(
            translator.translate("info.analysis.checking", Platform.TELEGRAM, lang)
        )

        result = await AnalysisService.analyze(user_id, path)
        if result.get_status() == ProcessImageStatus.SUCCESS:
            with open(result.get_image_path(), "rb") as file:
                try:
                    await update.message.reply_photo(
                        photo=file,
                        caption=translator.translate(
                            result.get_message_key() if result.get_message_key() else "success.analysis.completed",
                            Platform.TELEGRAM,
                            lang,
                        )
                    )
                    await check_message.delete()
                except Exception as e:
                    print(f"Error on sending photo: {e}")
                    await check_message.edit_text(translator.translate("errors.analysis.send_failed", Platform.TELEGRAM, lang))
                finally:
                    try:
                        file_manager.clear_user_temp(user_id)
                    except Exception as e:
                        print(f"Cleanup error (ignored): {e}")
        elif result.get_status() == ProcessImageStatus.CLEANED:
            await check_message.edit_text("✅ " + translator.translate(result.get_message_key(), Platform.TELEGRAM, lang))
        else:
            await check_message.edit_text("❌ " + + translator.translate(result.get_message_key(), Platform.TELEGRAM, lang))