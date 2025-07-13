# src/bot/handlers/post.py
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace

from aiogram import Router, F
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
)

from src.utils.paths import MEDIA_DIR


# ────────────────────────── FSM ────────────────────────── #
class EditState(StatesGroup):
    text = State()
    media = State()
    title = State()


# ─────────────── helpers ─────────────── #
def _target_chat(cfg: SimpleNamespace) -> int:
    t = cfg.telegram_channels
    topics = t.topics if hasattr(t, "topics") else {}
    return getattr(topics, "auto", None) or t.suggested_chat_id


def _main_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{pid}"),
            InlineKeyboardButton(text="🗑 Удалить",       callback_data=f"delete:{pid}"),
            InlineKeyboardButton(text="✅ Подтвердить",   callback_data=f"confirm:{pid}"),
        ]]
    )


def _edit_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Текст",     callback_data=f"ef:text:{pid}"),
            InlineKeyboardButton(text="Медиа",     callback_data=f"ef:media:{pid}"),
            InlineKeyboardButton(text="Заголовок", callback_data=f"ef:title:{pid}"),
        ]]
    )


def _media_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="➕ Добавить", callback_data=f"m:add:{pid}"),
            InlineKeyboardButton(text="➖ Убрать",   callback_data=f"m:del:{pid}"),
        ]]
    )


async def _send_suggestion(bot, chat_id: int, post, kb):
    """Отправить пост-предложку с учётом медиа ≤10 шт."""
    caption = f"<b>{post.title}</b>\n{post.text}"
    if post.media_ids:
        album = [
            InputMediaPhoto(
                media=FSInputFile(Path(MEDIA_DIR) / mid),
                **({"caption": caption, "parse_mode": "HTML"} if i == 0 else {})
            )
            for i, mid in enumerate(post.media_ids[:10])
        ]
        await bot.send_media_group(chat_id, album)
        await bot.send_message(chat_id, "▼", reply_markup=kb)
    else:
        await bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=kb)


# ──────────────── factory ──────────────── #
def build_post_admin_router(repo, prog_admin_filter, cfg) -> Router:
    r = Router()
    chat_id = _target_chat(cfg)

    # ────────── delete ────────── #
    @r.callback_query(F.data.startswith("delete:"), prog_admin_filter)
    async def delete_cb(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        repo.mark_rejected([pid])
        try:
            await cb.message.bot.delete_message(cb.message.chat.id, cb.message.reply_to_message.message_id)
            await cb.message.delete()
        except Exception:
            pass
        await cb.answer("Удалено.")

    # ────────── confirm ───────── #
    @r.callback_query(F.data.startswith("confirm:"), prog_admin_filter)
    async def confirm_cb(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        post = repo.fetch_by_id(pid)
        if not post:
            return await cb.answer("Не найдено", show_alert=True)
        await _send_suggestion(cb.bot, chat_id, post, None)
        repo.mark_confirmed([pid])
        await cb.answer("Отправлено!")

    # ────────── edit menu ─────── #
    @r.callback_query(F.data.startswith("edit:"), prog_admin_filter)
    async def edit_menu(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        await cb.message.answer(f"Редактирование {pid}", reply_markup=_edit_kb(pid))
        await cb.answer()

    # ───── pick field (ef:...) ─── #
    @r.callback_query(F.data.startswith("ef:"), prog_admin_filter)
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
        else:
            await cb.message.answer("Медиа: выбери действие", reply_markup=_media_kb(pid))
        await cb.answer()

    # ───── media action (m:add / m:del) ──── #
    @r.callback_query(F.data.startswith("m:"), prog_admin_filter)
    async def media_mode(cb: CallbackQuery, state: FSMContext):
        _, mode, pid = cb.data.split(":")
        await state.update_data(action=mode, pid=int(pid))
        await state.set_state(EditState.media)
        await cb.message.answer("Пришли файлы (add) или номера «1,3…» (del).")
        await cb.answer()

    # ───── edit text ───── #
    @r.message(EditState.text, prog_admin_filter)
    async def edit_text(msg: Message, state: FSMContext):
        pid = (await state.get_data())["pid"]
        repo.update_text(pid, msg.text)
        post = repo.fetch_by_id(pid)
        await _send_suggestion(msg.bot, msg.chat.id, post, _main_kb(pid))
        await state.clear()

    # ───── edit title ───── #
    @r.message(EditState.title, prog_admin_filter)
    async def edit_title(msg: Message, state: FSMContext):
        pid = (await state.get_data())["pid"]
        repo.update_title(pid, msg.text)
        post = repo.fetch_by_id(pid)
        await _send_suggestion(msg.bot, msg.chat.id, post, _main_kb(pid))
        await state.clear()

    # ───── edit media ───── #
    @r.message(EditState.media, prog_admin_filter)
    async def edit_media(msg: Message, state: FSMContext):
        data = await state.get_data()
        pid, action = data["pid"], data["action"]
        post = repo.fetch_by_id(pid)
        if not post:
            return await msg.reply("Не найдено.")
        mids = post.media_ids.copy()

        if action == "add":
            new_mids = []
            if msg.photo:
                new_mids.append(msg.photo[-1].file_id)
            elif msg.video:
                new_mids.append(msg.video.file_id)
            elif getattr(msg, "media_group", None):
                for m in msg.media_group:
                    new_mids.append(m.photo[-1].file_id if m.photo else m.video.file_id)
            if not new_mids:
                return await msg.reply("Не увидел медиа.")
            mids.extend(new_mids)
        else:  # del
            try:
                idxs = [int(i) - 1 for i in msg.text.split(",")]
            except Exception:
                return await msg.reply("Укажи номера через запятую.")
            mids = [m for i, m in enumerate(mids) if i not in idxs]

        repo.update_media(pid, mids)
        post = repo.fetch_by_id(pid)
        await _send_suggestion(msg.bot, msg.chat.id, post, _main_kb(pid))
        await state.clear()

    return r
