from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    File,
)

from src.utils.paths import MEDIA_DIR
from src.utils.app_config import AppConfig

# ────────────────────────── FSM ────────────────────────── #
class EditState(StatesGroup):
    text  = State()
    media = State()
    title = State()

class EditMedia(StatesGroup):
    waiting_add_photo = State()   # ждём фото/альбом
    waiting_add_index = State()   # ждём позицию (цифру)
    waiting_del_nums  = State()   # ждём «1,3…» для удаления


# ─────────────── helpers ─────────────── #
def _target_chat(cfg: AppConfig) -> int | str:
    return (
        cfg.telegram_channels.topics.get("auto")
        or cfg.telegram_channels.suggested_chat_id
    )


def _main_kb(pid: int) -> InlineKeyboardMarkup:
    """Кнопки управления постом (основное сообщение)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[  # в callback-data передаём id поста
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{pid}"),
            InlineKeyboardButton(text="🗑 Удалить",        callback_data=f"delete:{pid}"),
            InlineKeyboardButton(text="✅ Подтвердить",    callback_data=f"confirm:{pid}"),
        ]]
    )


def _edit_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[  # выбор поля для редактирования
            InlineKeyboardButton(text="Текст", callback_data=f"ef:text:{pid}"),
            InlineKeyboardButton(text="Медиа", callback_data=f"ef:media:{pid}"),
            InlineKeyboardButton(text="Заголовок", callback_data=f"ef:title:{pid}"),
        ]]
    )


def _media_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[  # режимы для медиа
            InlineKeyboardButton(text="➕ Добавить", callback_data=f"m:add:{pid}"),
            InlineKeyboardButton(text="➖ Убрать",   callback_data=f"m:del:{pid}"),
        ]]
    )


# ───────────────────── отправка поста / пересборка ───────────────────── #
async def _send_suggestion(
    bot: Bot,
    chat_id: int | str,
    post,
    *,
    with_kb: bool = True,
):
    """
    Отправляет пост-предложку.
    Возвращает (album_ids, meta_mid) — нужны, чтобы обновить БД.
    """
    caption = f"<b>{post.title}</b>\n{post.text}"
    album_ids: List[int] = []
    meta_mid: int | None = None

    # ---------- ALBUM ----------
    if post.media_ids:
        def _media_src(m: str):
            p = Path(MEDIA_DIR) / m
            return FSInputFile(p) if p.exists() else m  # локальный файл или file_id

        album = [
            InputMediaPhoto(
                media=_media_src(mid),
                **({"caption": caption, "parse_mode": "HTML"} if i == 0 else {}),
            )
            for i, mid in enumerate(post.media_ids[:10])
        ]
        msgs = await bot.send_media_group(chat_id, album)
        album_ids = [m.message_id for m in msgs]

        if with_kb:
            meta = await bot.send_message(
                chat_id,
                f"Источник: <a href='{post.url}'>ссылка</a>\nID: <code>{post.id}</code>",
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=_main_kb(post.id),
            )
            meta_mid = meta.message_id

    # ---------- SINGLE ----------
    else:
        msg = await bot.send_message(chat_id, caption, parse_mode="HTML")
        album_ids = [msg.message_id]
        if with_kb:
            await bot.edit_message_reply_markup(
                chat_id, msg.message_id, reply_markup=_main_kb(post.id)
            )

    return album_ids, meta_mid


async def _purge_old(bot: Bot, chat_id: int, *message_ids):
    """Удаляет старый альбом + meta-сообщение."""
    ids = [mid for mid in message_ids if mid]
    if not ids:
        return
    try:
        await bot.delete_messages(chat_id, ids)  # Bot API 7.1+
    except Exception:
        for mid in ids:
            try:
                await bot.delete_message(chat_id, mid)
            except Exception:
                pass


# ──────────────── ROUTER BUILD ──────────────── #
def build_post_admin_router(repo, prog_admin_filter, cfg: AppConfig) -> Router:
    router = Router()
    publish_chat = _target_chat(cfg)

    # ---------- DELETE ----------
    @router.callback_query(F.data.startswith("delete:"), prog_admin_filter)
    async def delete_cb(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        post = repo.fetch_by_id(pid)
        await _purge_old(cb.bot, cb.message.chat.id, *post.album_mids, post.meta_mid)
        await cb.answer("Удалено.")

    # ---------- CONFIRM ----------
    @router.callback_query(F.data.startswith("confirm:"), prog_admin_filter)
    async def confirm_cb(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        post = repo.fetch_by_id(pid)
        if not post:
            return await cb.answer("Не найдено", show_alert=True)

        await _send_suggestion(cb.bot, publish_chat, post, with_kb=False)
        repo.set_flag("confirmed", [pid])
        await cb.answer("Отправлено!")

    # ---------- EDIT MENU ----------
    @router.callback_query(F.data.startswith("edit:"), prog_admin_filter)
    async def edit_menu(cb: CallbackQuery, state: FSMContext):
        pid = int(cb.data.split(":")[1])
        await state.update_data(pid=pid)
        await cb.message.answer(f"Редактирование {pid}", reply_markup=_edit_kb(pid))
        await cb.answer()

    # выбор поля
    @router.callback_query(F.data.startswith("ef:"), prog_admin_filter)
    async def pick_field(cb: CallbackQuery, state: FSMContext):
        _, field, pid = cb.data.split(":")
        pid = int(pid)
        await state.update_data(pid=pid)

        if field == "text":
            await state.set_state(EditState.text)
            await cb.message.answer("Новый текст:")
        elif field == "title":
            await state.set_state(EditState.title)
            await cb.message.answer("Новый заголовок:")
        else:  # media
            await cb.message.answer("Медиа: выбери действие", reply_markup=_media_kb(pid))
            await state.set_state(EditState.media)
        await cb.answer()

    # переключение режима add/del для медиа
    @router.callback_query(F.data.startswith("m:"), prog_admin_filter)
    async def media_mode(cb: CallbackQuery, state: FSMContext):
        _, mode, pid = cb.data.split(":")
        await state.update_data(pid=int(pid), action=mode)
        if mode == "add":
            await cb.message.answer("Пришли фото/альбом — одним сообщением.")
            await state.set_state(EditMedia.waiting_add_photo)
        else:  # del
            await cb.message.answer("Укажи номера через запятую.")
            await state.set_state(EditMedia.waiting_del_nums)
        await cb.answer()

    # ───────────────────── TEXT / TITLE ───────────────────── #
    @router.message(EditState.text, prog_admin_filter)
    async def edit_text(msg: Message, state: FSMContext):
        pid = (await state.get_data())["pid"]
        repo.update_fields(pid, text=msg.text)
        post = repo.fetch_by_id(pid)

        await _purge_old(msg.bot, msg.chat.id, *post.album_mids, post.meta_mid)
        album_ids, meta_mid = await _send_suggestion(msg.bot, msg.chat.id, post)
        repo.update_fields(
            pid,
            main_mid=(album_ids[0] if album_ids else None),
            meta_mid=meta_mid,
        )
        await state.clear()

    @router.message(EditState.title, prog_admin_filter)
    async def edit_title(msg: Message, state: FSMContext):
        pid = (await state.get_data())["pid"]
        repo.update_fields(pid, title=msg.text)
        post = repo.fetch_by_id(pid)

        await _purge_old(msg.bot, msg.chat.id, *post.album_mids, post.meta_mid)
        album_ids, meta_mid = await _send_suggestion(msg.bot, msg.chat.id, post)
        repo.update_fields(
            pid,
            main_mid=(album_ids[0] if album_ids else None),
            meta_mid=meta_mid,
        )
        await state.clear()

    # ───────────────────── MEDIA: ADD (step 1) ───────────────────── #
    @router.message(EditMedia.waiting_add_photo, prog_admin_filter)
    async def media_add_photo(msg: Message, state: FSMContext):
        # собираем file_id-ы
        file_ids: List[str] = []
        if msg.photo:
            file_ids.append(msg.photo[-1].file_id)
        elif msg.video:
            file_ids.append(msg.video.file_id)
        elif getattr(msg, "media_group", None):
            for m in msg.media_group:
                file_ids.append(m.photo[-1].file_id if m.photo else m.video.file_id)

        if not file_ids:
            return await msg.reply("Не увидел медиа.")

        data = await state.get_data()
        pid = data["pid"]
        cur_mids: List[str] = repo.fetch_by_id(pid).media_ids

        if len(cur_mids) + len(file_ids) > 10:
            return await msg.reply("Максимум 10 фото. Удалите лишние и попробуйте снова.")

        await state.update_data(pending=file_ids, cur_mids=cur_mids)
        await msg.reply(f"Теперь пришли позицию 1…{len(cur_mids)+1} (0 — в конец).")
        await state.set_state(EditMedia.waiting_add_index)

    # ───────────────────── MEDIA: ADD (step 2) ───────────────────── #
    @router.message(EditMedia.waiting_add_index, prog_admin_filter)
    async def media_add_index(msg: Message, state: FSMContext):
        if not msg.text or not msg.text.isdigit():
            return await msg.reply("Нужна одна цифра позиции.")
        pos = int(msg.text)

        data = await state.get_data()
        pid       = data["pid"]
        file_ids  = data["pending"]
        mids      = list(data["cur_mids"])  # копия

        # скачиваем и сохраняем
        new_local: List[str] = []
        for fid in file_ids:
            tg_file: File = await msg.bot.get_file(fid)
            ext   = Path(tg_file.file_path).suffix or ".jpg"
            name  = f"{uuid.uuid4().hex[:16]}{ext}"
            await msg.bot.download_file(tg_file.file_path, MEDIA_DIR / name)
            new_local.append(name)

        idx = max(0, min(pos - 1, len(mids))) if pos else len(mids)
        mids[idx:idx] = new_local

        repo.update_fields(pid, media_ids=mids)
        post = repo.fetch_by_id(pid)

        await _purge_old(msg.bot, msg.chat.id, *post.album_mids, post.meta_mid)
        album_ids, meta_mid = await _send_suggestion(msg.bot, msg.chat.id, post)
        repo.update_fields(
            pid,
            main_mid=(album_ids[0] if album_ids else None),
            meta_mid=meta_mid,
        )
        await state.clear()
        await msg.answer("Фото добавлены.")

    # ───────────────────── MEDIA: DEL ───────────────────── #
    @router.message(EditMedia.waiting_del_nums, prog_admin_filter)
    async def media_del_nums(msg: Message, state: FSMContext):
        try:
            idxs = [int(i) - 1 for i in msg.text.split(",")]
        except Exception:
            return await msg.reply("Укажи номера через запятую.")

        pid  = (await state.get_data())["pid"]
        mids = list(repo.fetch_by_id(pid).media_ids)
        mids = [m for i, m in enumerate(mids) if i not in idxs]

        repo.update_fields(pid, media_ids=mids)
        post = repo.fetch_by_id(pid)

        await _purge_old(msg.bot, msg.chat.id, *post.album_mids, post.meta_mid)
        album_ids, meta_mid = await _send_suggestion(msg.bot, msg.chat.id, post)
        repo.update_fields(
            pid,
            main_mid=(album_ids[0] if album_ids else None),
            meta_mid=meta_mid,
        )
        await state.clear()

    return router
