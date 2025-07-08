from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.bot.filter import ProgFilter, AdminFilter
from src.utils.file_utils import load_config, dict_to_namespace
from src.utils.paths import MEDIA_DIR
from src.bot.filter import ProgOrAdminFilter
import logging

# FSM для редактирования поста
class EditPostState(StatesGroup):
    choosing_field = State()
    editing_text = State()
    editing_media = State()
    editing_url = State()


def get_post_admin_router(processed_repo, prog_admin_filter, cfg):
    router = Router()

    @router.callback_query(F.data.startswith("edit:"), prog_admin_filter)
    async def edit_callback(callback: CallbackQuery, state: FSMContext):
        post_id = int(callback.data.split(":", 1)[1])
        await edit_post_start(callback.message, state, post_id=post_id)
        await callback.answer()

    @router.message(Command("edit"), prog_admin_filter)
    async def edit_post_start(message: Message, state: FSMContext, post_id=None):
        try:
            if post_id is None:
                post_id = int(message.text.split(maxsplit=1)[1])
        except (IndexError, ValueError):
            await message.reply("Укажи ID поста: /edit 123")
            return

        post = processed_repo.fetch_by_id(post_id)
        if not post:
            await message.reply("Пост с таким ID не найден.")
            return

        text = post.get('text') or post.get('content') or ''
        await message.reply(
            f"Редактируем пост {post_id}.\n\n"
            f"<b>Текущий текст:</b>\n{text}\n\n"
            "Что менять?\n"
            "1. text — текст\n"
            "2. media — медиа\n"
            "3. url — ссылка\n\n"
            "<i>Напиши: text / media / url</i>",
            parse_mode="HTML"
        )
        await state.update_data(post_id=post_id)
        await state.set_state(EditPostState.choosing_field)

    @router.message(EditPostState.choosing_field, prog_admin_filter)
    async def choose_field(message: Message, state: FSMContext):
        choice = message.text.strip().lower()
        if choice == "text":
            await message.reply("Пришли новый текст поста.")
            await state.set_state(EditPostState.editing_text)
        elif choice == "media":
            await message.reply("Пришли новое фото/видео или альбом (несколько медиа)." )
            await state.set_state(EditPostState.editing_media)
        elif choice == "url":
            await message.reply("Пришли новый URL поста.")
            await state.set_state(EditPostState.editing_url)
        else:
            await message.reply("Варианты: text / media / url.")

    @router.message(EditPostState.editing_text, prog_admin_filter)
    async def edit_text(message: Message, state: FSMContext):
        data = await state.get_data()
        post_id = data["post_id"]
        processed_repo.update_text(post_id, message.text)
        await message.reply("Текст поста обновлён!")
        await state.clear()

    @router.message(EditPostState.editing_url, prog_admin_filter)
    async def edit_url(message: Message, state: FSMContext):
        data = await state.get_data()
        post_id = data["post_id"]
        processed_repo.update_url(post_id, message.text)
        await message.reply("URL поста обновлён!")
        await state.clear()

    @router.message(EditPostState.editing_media, prog_admin_filter)
    async def edit_media(message: Message, state: FSMContext):
        data = await state.get_data()
        post_id = data["post_id"]
        media_ids = []
        if message.photo:
            media_ids = [message.photo[-1].file_id]
        elif message.video:
            media_ids = [message.video.file_id]
        elif message.media_group_id and hasattr(message, 'media_group'):
            media_ids = [m.photo[-1].file_id if m.photo else m.video.file_id for m in message.media_group]
        else:
            await message.reply("Пришли фото, видео или альбом.")
            return

        processed_repo.update_media(post_id, media_ids)
        await message.reply("Медиа поста обновлены!")
        await state.clear()

    @router.callback_query(F.data.startswith("delete:"), prog_admin_filter)
    async def delete_callback(callback: CallbackQuery):
        post_id = int(callback.data.split(":", 1)[1])
        try:
            await callback.message.bot.delete_message(callback.message.chat.id, callback.message.reply_to_message.message_id)
            await callback.message.delete()
        except Exception:
            pass
        processed_repo.mark_rejected([post_id])
        await callback.answer("Пост удалён и отмечен как отклонённый.")

    @router.callback_query(F.data.startswith("confirm:"), prog_admin_filter)
    async def confirm_callback(callback: CallbackQuery):
        logger = logging.getLogger("bot")
        logger.debug("▶️ Confirm callback received: %s from user %s", callback.data, callback.from_user.id)
        await callback.answer()

        post_id = int(callback.data.split(":", 1)[1])
        post = processed_repo.fetch_by_id(post_id)
        if not post:
            logger.warning("❗ Tried to confirm missing post %s", post_id)
            await callback.answer("Новость не найдена в базе.", show_alert=True)
            return

        topic = post.topic
        if not topic:
            logger.error("❗ В новости нет topic!")
            await callback.answer("В новости нет темы (topic) — не могу отправить!", show_alert=True)
            return

        target_chat = getattr(cfg.telegram_channels.topics, topic, None)
        if not target_chat:
            logger.error("❗ No channel configured for topic %s", topic)
            await callback.answer(f"Канал для темы «{topic}» не настроен.", show_alert=True)
            return

        text = (
            f"<b>{post.title}</b>\n"
            f"{post.text}\n"
            f"<a href='{post.url}'>Читать далее</a>"
        )

        try:
            await callback.bot.send_message(
                chat_id=target_chat,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            if post.media_ids:
                media = [InputMediaPhoto(FSInputFile(str(MEDIA_DIR / m))) for m in post.media_ids]
                await callback.bot.send_media_group(chat_id=target_chat, media=media)
        except Exception as e:
            logger.error("🔥 Error sending to channel %s: %s", target_chat, e, exc_info=True)
            await callback.answer("Ошибка при отправке в канал. Смотри логи.", show_alert=True)
            return

        processed_repo.mark_confirmed([post_id])
        logger.info("✅ Post %s confirmed and sent to %s", post_id, target_chat)

        try:
            await callback.message.bot.delete_message(callback.message.chat.id,
                                                      callback.message.reply_to_message.message_id)
            await callback.message.delete()
        except Exception:
            pass

        await callback.answer("Новость подтверждена и отправлена в канал.")

    @router.message(Command("edit_help"), prog_admin_filter)
    async def edit_help(message: Message):
        await message.reply(
            "/edit <id> — начать редактирование поста\n"
            "Кнопки под сообщением: Редактировать, Удалить, Подтвердить.\n"
            "Редактирование доступно программистам и админам.",
            parse_mode="HTML"
        )

    return router