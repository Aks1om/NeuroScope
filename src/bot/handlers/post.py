# src/bot/handlers/post.py
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, FSInputFile
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


def build_post_admin_router(
    sent_repo,
    processed_repo,
    prog_admin_filter,
    cfg,
    *,
    build_caption,
    build_meta,
) -> Router:
    """
    sent_repo      -> DuckDBRepository(SentNewsItem)
    processed_repo -> DuckDBRepository(ProcessedNewsItem)
    build_caption(item) -> str
    build_meta(item)    -> str
    """
    router = Router()

    # ---------------- utils ---------------- #

    async def _remember(state, mid):
        data = await state.get_data()
        msgs = data.get("edit_msgs", [])
        msgs.append(mid)
        await state.update_data(edit_msgs=msgs)

    def _clip(text, limit):
        if len(text) <= limit:
            return text, False
        return text[: limit - 1] + "…", True

    async def _delete_ids(bot, chat_id, ids):
        for mid in ids:
            try:
                await bot.delete_message(chat_id, mid)
            except Exception:
                pass

    async def _send_post(bot, chat_id, item):
        """
        Отправить пост (как делает SendingService): альбом (если медиа) + meta с клавой.
        Возвращает (main_mid, others_ids_list).
        """
        main_mid = None
        others = []

        caption_full = build_caption(item)
        # альбом
        if item.media_ids:
            album = []
            trimmed_any = False
            for i, mid in enumerate(item.media_ids[:10]):
                path = Path(MEDIA_DIR) / mid
                if path.exists():
                    media_src = FSInputFile(path)
                elif len(mid) >= 40 and "." not in mid:
                    media_src = mid
                else:
                    continue

                if i == 0:
                    cap, _trim = _clip(caption_full, 1024)  # Telegram caption limit
                    trimmed_any = trimmed_any or _trim
                    album.append(InputMediaPhoto(media=media_src, caption=cap, parse_mode="HTML"))
                else:
                    album.append(InputMediaPhoto(media=media_src))
            if album:
                msgs = await bot.send_media_group(chat_id, album)
                if msgs:
                    main_mid = msgs[0].message_id
                    others.extend(m.message_id for m in msgs)
            # если текст был обрезан и хочется предупредить — можно дослать предупреждение (опционально)
        # только текст
        if main_mid is None:
            msg = await bot.send_message(
                chat_id,
                caption_full,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            main_mid = msg.message_id
            others.append(main_mid)

        # meta
        meta_msg = await bot.send_message(
            chat_id,
            build_meta(item),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_keyboard(item.id),
        )
        others.append(meta_msg.message_id)

        return main_mid, others

    # ---------------- handlers ---------------- #

    # Удалить (убрать из предложки)
    @router.callback_query(F.data.startswith("delete:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        sent_item = sent_repo.fetch_by_id(pid)
        if sent_item:
            await _delete_ids(cb.bot, cb.message.chat.id, [sent_item.main_message_id, *sent_item.others_message_ids])
        # вернуть в работу? -> снимаем suggested в processed
        processed_repo.update_fields(pid, suggested=False)
        await cb.answer("Удалено ✔️")
        # удаляем саму кнопку, с которой кликнули
        try:
            await cb.message.delete()
        except Exception:
            pass

    # Подтвердить
    @router.callback_query(F.data.startswith("confirm:"), prog_admin_filter)
    async def _(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        sent_repo.set_flag("confirmed", [pid])
        await cb.answer("Отправлено ✔️")
        await cb.message.edit_reply_markup(reply_markup=None)

    # Вход в редактирование
    @router.callback_query(F.data.startswith("edit:"), prog_admin_filter)
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(":")[1])
        if LockManager.is_locked_by_other(pid, cb.from_user.id):
            await cb.answer("Пост сейчас редактируется другим пользователем.", show_alert=True)
            return

        LockManager.lock(pid, cb.from_user.id)

        # сохраним id всех исходных сообщений поста, чтобы при done их снести
        sent_item = sent_repo.fetch_by_id(pid)
        orig_ids = []
        if sent_item:
            if sent_item.main_message_id:
                orig_ids.append(sent_item.main_message_id)
            orig_ids.extend(sent_item.others_message_ids)

        await state.update_data(pid=pid, edit_msgs=[cb.message.message_id], orig_msgs=orig_ids)

        msg = await cb.message.answer("Что изменить?", reply_markup=edit_keyboard(pid))
        await _remember(state, msg.message_id)

        await state.set_state(EditState.menu)
        await cb.answer()

    # Редактировать текст
    @router.callback_query(F.data.startswith("t:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        msg = await cb.message.answer("Отправьте новый текст:")
        await _remember(state, msg.message_id)
        await state.set_state(EditState.text)
        await cb.answer()

    @router.message(EditState.text, prog_admin_filter)
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data.get("pid")
        if pid is None:
            await msg.answer("Сессия не найдена. Нажмите «Редактировать» ещё раз.")
            return
        if LockManager.is_locked_by_other(pid, msg.from_user.id):
            await msg.answer("Пост редактируется другим пользователем.")
            return

        sent_repo.update_fields(pid, text=msg.text)

        ans = await msg.answer("Текст обновлён.", reply_markup=edit_keyboard(pid))
        await _remember(state, msg.message_id)
        await _remember(state, ans.message_id)
        await state.set_state(EditState.menu)

    # Редактировать заголовок
    @router.callback_query(F.data.startswith("h:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        msg = await cb.message.answer("Отправьте новый заголовок:")
        await _remember(state, msg.message_id)
        await state.set_state(EditState.title)
        await cb.answer()

    @router.message(EditState.title, prog_admin_filter)
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data.get("pid")
        if pid is None:
            await msg.answer("Сессия не найдена. Нажмите «Редактировать» ещё раз.")
            return
        if LockManager.is_locked_by_other(pid, msg.from_user.id):
            await msg.answer("Пост редактируется другим пользователем.")
            return

        sent_repo.update_fields(pid, title=msg.text)

        ans = await msg.answer("Заголовок обновлён.", reply_markup=edit_keyboard(pid))
        await _remember(state, msg.message_id)
        await _remember(state, ans.message_id)
        await state.set_state(EditState.menu)

    # Меню медиа
    @router.callback_query(F.data.startswith("m:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = (await state.get_data())["pid"]
        msg = await cb.message.answer("Действие с медиа:", reply_markup=media_keyboard(pid))
        await _remember(state, msg.message_id)
        await cb.answer()

    # Добавить медиа
    @router.callback_query(F.data.startswith("media_add:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        msg = await cb.message.answer("Отправьте фото для добавления:")
        await _remember(state, msg.message_id)
        await state.set_state(EditState.media_add)
        await cb.answer()

    @router.message(EditState.media_add, prog_admin_filter)
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data.get("pid")
        post = sent_repo.fetch_by_id(pid)

        if msg.photo:
            file_id = msg.photo[-1].file_id
            if len(post.media_ids) < 10:
                post.media_ids.append(file_id)
                sent_repo.update_fields(pid, media_ids=post.media_ids)
                ans = await msg.answer("Медиа добавлено.", reply_markup=edit_keyboard(pid))
            else:
                ans = await msg.answer("Можно не более 10 медиа!")
        else:
            ans = await msg.answer("Пришлите именно фото.")

        await _remember(state, msg.message_id)
        await _remember(state, ans.message_id)
        await state.set_state(EditState.menu)

    # Удалить медиа
    @router.callback_query(F.data.startswith("media_del:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        msg = await cb.message.answer("Введите номер медиа для удаления (1-based):")
        await _remember(state, msg.message_id)
        await state.set_state(EditState.media_del)
        await cb.answer()

    @router.message(EditState.media_del, prog_admin_filter)
    async def _(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid = data.get("pid")
        post = sent_repo.fetch_by_id(pid)
        try:
            idx = int(msg.text.strip()) - 1
            if 0 <= idx < len(post.media_ids):
                del post.media_ids[idx]
                sent_repo.update_fields(pid, media_ids=post.media_ids)
                ans = await msg.answer("Медиа удалено.", reply_markup=edit_keyboard(pid))
            else:
                ans = await msg.answer("Неверный индекс.")
        except Exception:
            ans = await msg.answer("Ошибка! Введите корректный индекс.")

        await _remember(state, msg.message_id)
        await _remember(state, ans.message_id)
        await state.set_state(EditState.menu)

    # Откатить к оригиналу из processed
    @router.callback_query(F.data.startswith("rollback:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(":")[1])
        orig = processed_repo.fetch_by_id(pid)
        if not orig:
            await cb.answer("Оригинал не найден.", show_alert=True)
            return
        # Обновляем sent запись оригинальными данными
        sent_repo.update_fields(
            pid,
            title=orig.title,
            text=orig.text,
            media_ids=orig.media_ids,
            language=orig.language,
            topic=orig.topic,
        )
        await cb.answer("Откат выполнен.")
        # Перерисуем редакт меню
        msg = await cb.message.answer("Данные возвращены. Что дальше?", reply_markup=edit_keyboard(pid))
        await _remember(state, msg.message_id)

    # Готово: финализируем, пересобираем пост, удаляем лишнее
    @router.callback_query(F.data.startswith("done:"), prog_admin_filter, EditingSessionFilter())
    async def _(cb: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        pid = data.get("pid")

        # снять лок
        LockManager.unlock(pid)

        # удалить служебные сообщения
        await _delete_ids(cb.bot, cb.message.chat.id, data.get("edit_msgs", []))

        # удалить старый пост (который был в предложке до редактирования)
        orig_ids = data.get("orig_msgs", [])
        await _delete_ids(cb.bot, cb.message.chat.id, orig_ids)

        post = sent_repo.fetch_by_id(pid)
        main_mid, others = await _send_post(cb.bot, cb.message.chat.id, post)

        # обновить message_ids в sent_repo
        sent_repo.update_fields(
            pid,
            main_message_id=main_mid,
            others_message_ids=others,
        )

        await state.clear()
        await cb.answer(f"Пост {pid} обновлён")

    return router
