from __future__ import annotations
import uuid
from pathlib import Path
from typing import List

from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from src.utils.paths import MEDIA_DIR
from src.data_manager.models import AppConfig
from src.bot.filter import LockManager, EditingSessionFilter, ProgOrAdminFilter

# ---------- FSM ----------
class EditState(StatesGroup):
    menu         = State()
    text         = State()
    title        = State()
    media_add    = State()
    media_del    = State()

# ---------- клавиатуры ----------
def _kb_main(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"e:{pid}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"d:{pid}"),
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"c:{pid}"),
        ]
    ])

def _kb_edit(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Текст", callback_data=f"t:{pid}"),
            InlineKeyboardButton(text="Заголовок", callback_data=f"h:{pid}"),
            InlineKeyboardButton(text="Медиа", callback_data=f"m:{pid}"),
        ],
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{pid}")]
    ])

def _kb_media(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data=f"ma:{pid}"),
            InlineKeyboardButton(text="➖ Удалить", callback_data=f"md:{pid}"),
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back:{pid}")]
    ])

# ---------- rebuild ----------
async def _rebuild(bot: Bot, chat_id: int, post):
    """Пересобрать пост и обновить message_id-ы в БД."""
    try:
        await bot.delete_messages(chat_id, post.album_mids + [post.meta_mid])
    except Exception:
        pass

    caption = f"<b>{post.title}</b>\n{post.text}"
    album_ids: List[int] = []
    meta_mid: int | None = None

    if post.media_ids:
        album = [
            InputMediaPhoto(
                media=FSInputFile(Path(MEDIA_DIR)/m) if (Path(MEDIA_DIR)/m).exists() else m,
                **({"caption": caption, "parse_mode": "HTML"} if i == 0 else {})
            )
            for i, m in enumerate(post.media_ids[:10])
        ]
        msgs = await bot.send_media_group(chat_id, album)
        album_ids = [m.message_id for m in msgs]
        meta = await bot.send_message(
            chat_id,
            f"Источник: <a href='{post.url}'>ссылка</a>\nID: <code>{post.id}</code>",
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=_kb_main(post.id)
        )
        meta_mid = meta.message_id
    else:
        msg = await bot.send_message(chat_id, caption, parse_mode="HTML",
                                     reply_markup=_kb_main(post.id))
        album_ids = [msg.message_id]
        meta_mid = None

    post.repo.update_fields(post.id, album_mids=album_ids, meta_mid=meta_mid)

# ---------- router ----------
def build_post_admin_router(repo, prog_admin_filter: ProgOrAdminFilter, cfg: AppConfig) -> Router:
    router = Router()

    # --- Удалить ---
    @router.callback_query(F.data.startswith("d:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data[2:])
        post = repo.fetch_by_id(pid)
        try:
            await cb.bot.delete_messages(cb.message.chat.id, post.album_mids + [post.meta_mid])
        except Exception:
            pass
        await cb.answer("Удалено ✔️")

    # --- Подтвердить ---
    @router.callback_query(F.data.startswith("c:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data[2:])
        post = repo.fetch_by_id(pid)
        await _rebuild(cb.bot, cfg.telegram_channels.topics.get("auto") or cfg.telegram_channels.suggested_chat_id, post)
        repo.set_flag("confirmed", [pid])
        await cb.answer("Отправлено ✔️")

    # --- Вход в режим редактирования: даем лок ---
    @router.callback_query(F.data.startswith("e:"), prog_admin_filter)
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data[2:])
        LockManager.lock(pid, cb.from_user.id)
        repo.update_fields(pid, editing_by=cb.from_user.id)
        await state.update_data(pid=pid)
        await state.set_state(EditState.menu)
        await cb.message.answer("Выберите, что изменить:", reply_markup=_kb_edit(pid))
        await cb.answer()

    # --- Назад ---
    @router.callback_query(F.data.startswith("back:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.menu)
        await cb.message.answer("Выберите, что изменить:", reply_markup=_kb_edit(pid))
        await cb.answer()

    # --- Редактирование текста ---
    @router.callback_query(F.data.startswith("t:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.text)
        await cb.message.answer("Отправьте новый текст:")

    @router.message(EditState.text, prog_admin_filter)
    async def _(msg: Message, state: FSMContext):
        pid = (await state.get_data())["pid"]
        repo.update_fields(pid, text=msg.text)
        await state.set_state(EditState.menu)
        await msg.answer("Выберите, что изменить:", reply_markup=_kb_edit(pid))

    # --- Редактирование заголовка ---
    @router.callback_query(F.data.startswith("h:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.title)
        await cb.message.answer("Отправьте новый заголовок:")

    @router.message(EditState.title, prog_admin_filter)
    async def _(msg: Message, state: FSMContext):
        pid = (await state.get_data())["pid"]
        repo.update_fields(pid, title=msg.text)
        await state.set_state(EditState.menu)
        await msg.answer("Выберите, что изменить:", reply_markup=_kb_edit(pid))

    # --- Работа с медиа ---
    @router.callback_query(F.data.startswith("m:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.menu)
        await cb.message.answer("Действие с медиа:", reply_markup=_kb_media(pid))

    # --- Добавление медиа ---
    @router.callback_query(F.data.startswith("ma:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.media_add)
        await cb.message.answer("Отправьте фото/видео одним сообщением:")

    # --- Удаление медиа ---
    @router.callback_query(F.data.startswith("md:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.media_del)
        await cb.message.answer("Введите номера через запятую (1-based):")

    # --- Завершение редактирования: снимаем лок ---
    @router.callback_query(F.data.startswith("done:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        LockManager.unlock(pid)
        repo.update_fields(pid, editing_by=None)
        await state.clear()
        post = repo.fetch_by_id(pid)
        await _rebuild(cb.bot, cb.message.chat.id, post)
        await cb.message.answer(f"@{cb.from_user.username or cb.from_user.id} изменил пост {pid}")

    return router
