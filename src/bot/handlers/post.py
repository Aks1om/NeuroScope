from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto,
    Message,
)
from pathlib import Path
from typing import List

from src.utils.paths import MEDIA_DIR
from src.bot.keyboards import main_keyboard, edit_keyboard, media_keyboard
from src.bot.filter import LockManager, EditingSessionFilter, ProgOrAdminFilter

# ---------- FSM ----------
class EditState(StatesGroup):
    menu         = State()
    text         = State()
    title        = State()
    media_add    = State()
    media_del    = State()

# ---------- Пересборка поста ----------
async def rebuild_post(bot: Bot, chat_id: int, post, repo):
    """Пересобрать пост: удалить старые сообщения, отправить новые, обновить message_id в БД."""
    try:
        ids_to_delete = []
        if post.main_message_id:
            ids_to_delete.append(post.main_message_id)
        if post.others_message_ids:
            ids_to_delete.extend(post.others_message_ids)
        if ids_to_delete:
            await bot.delete_messages(chat_id, ids_to_delete)
    except Exception:
        pass

    caption = f"<b>{post.title}</b>\n{post.text}"
    main_mid = None
    others_ids: List[int] = []

    # --- Отправляем медиа или текст ---
    if post.media_ids:
        album = [
            InputMediaPhoto(
                media=FSInputFile(Path(MEDIA_DIR) / m) if (Path(MEDIA_DIR) / m).exists() else m,
                **({"caption": caption, "parse_mode": "HTML"} if i == 0 else {})
            )
            for i, m in enumerate(post.media_ids[:10])
        ]
        msgs = await bot.send_media_group(chat_id, album)
        main_mid = msgs[0].message_id
        others_ids = [m.message_id for m in msgs[1:]]
    else:
        msg = await bot.send_message(chat_id, caption, parse_mode="HTML",
                                     reply_markup=main_keyboard(post.id))
        main_mid = msg.message_id

    # --- Meta сообщение ---
    meta = await bot.send_message(
        chat_id,
        f"Источник: <a href='{post.url}'>ссылка</a>\nID: <code>{post.id}</code>",
        parse_mode="HTML", disable_web_page_preview=True,
        reply_markup=main_keyboard(post.id)
    )
    others_ids.append(meta.message_id)

    # --- Обновляем в репозитории ---
    repo.update_fields(post.id, main_message_id=main_mid, others_message_ids=others_ids)

# ---------- Роутер ----------
def build_post_admin_router(repo, prog_admin_filter: ProgOrAdminFilter, cfg) -> Router:
    router = Router()

    # --- Удалить ---
    @router.callback_query(F.data.startswith("d:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data[2:])
        post = repo.fetch_by_id(pid)
        ids_to_delete = []
        if post.main_message_id:
            ids_to_delete.append(post.main_message_id)
        if post.others_message_ids:
            ids_to_delete.extend(post.others_message_ids)
        try:
            if ids_to_delete:
                await cb.bot.delete_messages(cb.message.chat.id, ids_to_delete)
        except Exception:
            pass
        await cb.answer("Удалено ✔️")

    # --- Подтвердить ---
    @router.callback_query(F.data.startswith("c:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data[2:])
        post = repo.fetch_by_id(pid)
        await rebuild_post(
            cb.bot,
            cfg.telegram_channels.topics.get("auto") or cfg.telegram_channels.suggested_chat_id,
            post,
            repo
        )
        repo.set_flag("confirmed", [pid])
        await cb.answer("Отправлено ✔️")

    # --- Вход в режим редактирования: даём лок ---
    @router.callback_query(F.data.startswith("e:"), prog_admin_filter)
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data[2:])
        LockManager.lock(pid, cb.from_user.id)
        repo.update_fields(pid, editing_by=cb.from_user.id)
        await state.update_data(pid=pid)
        await state.set_state(EditState.menu)
        await cb.message.answer("Выберите, что изменить:", reply_markup=edit_keyboard(pid))
        await cb.answer()

    # --- Назад ---
    @router.callback_query(F.data.startswith("back:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.menu)
        await cb.message.answer("Выберите, что изменить:", reply_markup=edit_keyboard(pid))
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
        await msg.answer("Выберите, что изменить:", reply_markup=edit_keyboard(pid))

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
        await msg.answer("Выберите, что изменить:", reply_markup=edit_keyboard(pid))

    # --- Работа с медиа ---
    @router.callback_query(F.data.startswith("m:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(':')[1])
        await state.set_state(EditState.menu)
        await cb.message.answer("Действие с медиа:", reply_markup=media_keyboard(pid))

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
        await rebuild_post(cb.bot, cb.message.chat.id, post, repo)
        await cb.message.answer(f"@{cb.from_user.username or cb.from_user.id} изменил пост {pid}")

    return router
