from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile, InputMediaPhoto
from pathlib import Path

from src.utils.paths import MEDIA_DIR
from src.bot.keyboards import main_keyboard, edit_keyboard, media_keyboard
from src.bot.filter import LockManager, EditingSessionFilter, ProgOrAdminFilter

class EditState(StatesGroup):
    menu      = State()
    text      = State()
    title     = State()
    media_add = State()
    media_del = State()

def build_post_admin_router(sent_repo, prog_admin_filter, cfg) -> Router:
    router = Router()

    # --- Удалить ---
    @router.callback_query(F.data.startswith("delete:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        post = sent_repo.fetch_by_id(pid)
        # удалить все сообщения поста
        ids_to_delete = [post.main_message_id] + (post.others_message_ids or [])
        for mid in ids_to_delete:
            try:
                await cb.bot.delete_message(cb.message.chat.id, mid)
            except Exception:
                pass
        sent_repo.update_fields(pid, confirmed=False)  # Или удалить вообще, если надо
        await cb.answer("Удалено ✔️")
        await cb.message.delete()

    # --- Подтвердить ---
    @router.callback_query(F.data.startswith("confirm:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        sent_repo.set_flag("confirmed", [pid])
        await cb.answer("Отправлено ✔️")
        await cb.message.edit_reply_markup(reply_markup=None)

    # --- Вход в режим редактирования ---
    @router.callback_query(F.data.startswith("edit:"), prog_admin_filter)
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(":")[1])
        if LockManager.is_locked_by_other(pid, cb.from_user.id):
            await cb.answer("Пост сейчас редактируется другим пользователем.", show_alert=True)
            return
        LockManager.lock(pid, cb.from_user.id)
        await state.update_data(pid=pid)
        await state.set_state(EditState.menu)
        await cb.message.answer("Что изменить?", reply_markup=edit_keyboard(pid))
        await cb.answer()

    # --- Меню редактирования ---
    @router.callback_query(EditState.menu, prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        pid = data["pid"]
        await cb.message.answer("Что изменить?", reply_markup=edit_keyboard(pid))
        await cb.answer()

    # --- Редактирование текста ---
    @router.callback_query(F.data.startswith("t:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.text)
        await cb.message.answer("Отправьте новый текст:")
        await cb.answer()

    @router.message(EditState.text, prog_admin_filter, EditingSessionFilter())
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data["pid"]
        post = sent_repo.fetch_by_id(pid)
        sent_repo.update_fields(pid, text=msg.text)
        await state.set_state(EditState.menu)
        await msg.answer("Текст обновлён.", reply_markup=edit_keyboard(pid))

    # --- Редактирование заголовка ---
    @router.callback_query(F.data.startswith("h:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.title)
        await cb.message.answer("Отправьте новый заголовок:")
        await cb.answer()

    @router.message(EditState.title, prog_admin_filter, EditingSessionFilter())
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data["pid"]
        post = sent_repo.fetch_by_id(pid)
        sent_repo.update_fields(pid, title=msg.text)
        await state.set_state(EditState.menu)
        await msg.answer("Заголовок обновлён.", reply_markup=edit_keyboard(pid))

    # --- Работа с медиа ---
    @router.callback_query(F.data.startswith("m:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        pid = data["pid"]
        await cb.message.answer("Действие с медиа:", reply_markup=media_keyboard(pid))

    @router.callback_query(F.data.startswith("media_add:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.media_add)
        await cb.message.answer("Отправьте фото для добавления:")

    @router.message(EditState.media_add, prog_admin_filter, EditingSessionFilter())
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data["pid"]
        post = sent_repo.fetch_by_id(pid)
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_ids = (post.media_ids or []) + [file_id]
            sent_repo.update_fields(pid, media_ids=media_ids[:10])
            await msg.answer("Медиа добавлено.", reply_markup=edit_keyboard(pid))
        else:
            await msg.answer("Пришлите именно фото.")
        await state.set_state(EditState.menu)

    @router.callback_query(F.data.startswith("media_del:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        await state.set_state(EditState.media_del)
        await cb.message.answer("Введите номер медиа для удаления (1-based):")

    @router.message(EditState.media_del, prog_admin_filter, EditingSessionFilter())
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data["pid"]
        try:
            idx = int(msg.text.strip()) - 1
            post = sent_repo.fetch_by_id(pid)
            media_ids = post.media_ids or []
            if 0 <= idx < len(media_ids):
                del media_ids[idx]
                sent_repo.update_fields(pid, media_ids=media_ids)
                await msg.answer("Медиа удалено.", reply_markup=edit_keyboard(pid))
            else:
                await msg.answer("Неверный индекс.")
        except Exception:
            await msg.answer("Ошибка! Введите корректный индекс.")
        await state.set_state(EditState.menu)

    # --- Готово: снимаем лок ---
    @router.callback_query(F.data.startswith("done:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        pid = data["pid"]
        LockManager.unlock(pid)
        await state.clear()
        post = sent_repo.fetch_by_id(pid)
        # Присылаем итоговый пост с кнопками
        await cb.message.answer(
            f"<b>{post.title}</b>\n{post.text}",
            reply_markup=main_keyboard(pid),
            parse_mode="HTML"
        )
        await cb.answer(f"Пост {pid} обновлён")

    return router
