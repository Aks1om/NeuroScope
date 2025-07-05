from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.bot.filter import ProgFilter, AdminFilter

# FSM
class EditPostState(StatesGroup):
    choosing_field = State()
    editing_text = State()
    editing_media = State()
    editing_url = State()

def get_post_admin_router(processed_repo):
    router = Router()

    # =========== КНОПКА "Редактировать" ===========
    @router.callback_query(F.data.startswith("editpost_"), ProgFilter, AdminFilter)
    async def editpost_callback(callback: CallbackQuery, state: FSMContext):
        post_id = int(callback.data.split("_")[1])
        await edit_post_start(callback.message, state, post_id=post_id)
        await callback.answer()

    # =========== /edit <id> ===========
    @router.message(Command("edit"), ProgFilter, AdminFilter)
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

    # =========== Шаг выбора поля ===========
    @router.message(EditPostState.choosing_field, ProgFilter, AdminFilter)
    async def choose_field(message: Message, state: FSMContext):
        choice = message.text.strip().lower()
        if choice == "text":
            await message.reply("Пришли новый текст поста.")
            await state.set_state(EditPostState.editing_text)
        elif choice == "media":
            await message.reply("Пришли новое фото/видео или альбом (несколько медиа).")
            await state.set_state(EditPostState.editing_media)
        elif choice == "url":
            await message.reply("Пришли новый URL поста.")
            await state.set_state(EditPostState.editing_url)
        else:
            await message.reply("Варианты: text / media / url.")

    # =========== Сохранение нового текста ===========
    @router.message(EditPostState.editing_text, ProgFilter, AdminFilter)
    async def edit_text(message: Message, state: FSMContext):
        data = await state.get_data()
        post_id = data["post_id"]
        processed_repo.update_text(post_id, message.text)
        await message.reply("Текст поста обновлён!")
        await state.clear()

    # =========== Сохранение нового URL ===========
    @router.message(EditPostState.editing_url, ProgFilter, AdminFilter)
    async def edit_url(message: Message, state: FSMContext):
        data = await state.get_data()
        post_id = data["post_id"]
        processed_repo.update_url(post_id, message.text)
        await message.reply("URL поста обновлён!")
        await state.clear()

    # =========== Сохранение новых медиа ===========
    @router.message(EditPostState.editing_media, ProgFilter, AdminFilter)
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

    # =========== /edit_help ===========
    @router.message(Command("edit_help"), ProgFilter, AdminFilter)
    async def edit_help(message: Message):
        await message.reply(
            "/edit <id> — начать редактирование поста\n"
            "Доступные поля: text, media, url\n"
            "Редактирование только для программистов и админов.",
            parse_mode="HTML"
        )

    return router
