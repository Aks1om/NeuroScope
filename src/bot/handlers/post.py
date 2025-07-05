# src/bot/handlers/post_admin.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.data_manager.duckdb_repository import DuckDBNewsRepository

router = Router()

class EditPostState(StatesGroup):
    choosing_field = State()
    editing_text = State()
    editing_media = State()
    editing_url = State()

# Получить репозиторий — через DI или импорт из src/di.py!
from src.di import processed_repo

# Только для админов — использовать фильтр, например ManagerFilter или AdminFilter
@router.message(Command("edit"))
async def edit_post_start(message: Message, state: FSMContext):
    try:
        post_id = int(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        await message.reply("Укажи ID поста: /edit 123")
        return

    post = processed_repo.fetch_by_id(post_id)  # метод надо реализовать
    if not post:
        await message.reply("Пост с таким ID не найден.")
        return

    await message.reply(
        f"Редактируем пост {post_id}.\n"
        f"Текущий текст: {post['text']}\n"
        "Что будем менять?\n1. Текст\n2. Медиа\n3. URL\n\n"
        "Напиши: text / media / url"
    )
    await state.update_data(post_id=post_id)
    await state.set_state(EditPostState.choosing_field)

@router.message(EditPostState.choosing_field)
async def choose_field(message: Message, state: FSMContext):
    choice = message.text.strip().lower()
    if choice == "text":
        await message.reply("Пришли новый текст поста.")
        await state.set_state(EditPostState.editing_text)
    elif choice == "media":
        await message.reply("Пришли новое фото/видео для поста.")
        await state.set_state(EditPostState.editing_media)
    elif choice == "url":
        await message.reply("Пришли новый URL.")
        await state.set_state(EditPostState.editing_url)
    else:
        await message.reply("Варианты: text / media / url.")

@router.message(EditPostState.editing_text)
async def edit_text(message: Message, state: FSMContext):
    data = await state.get_data()
    post_id = data["post_id"]
    # обновляем текст в базе
    processed_repo.update_text(post_id, message.text)
    await message.reply("Текст поста обновлён!")
    await state.clear()

# Аналогично — для media и url:
# реализовать processed_repo.update_media и update_url

# ... остальной код (edit_media, edit_url) по аналогии

