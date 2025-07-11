# src/bot/handlers/post.py

from __future__ import annotations
from pathlib import Path
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from src.utils.paths import MEDIA_DIR

# ───────────────────────────── FSM ───────────────────────────── #

class EditPostState(StatesGroup):
    choosing_field = State()
    editing_text   = State()
    editing_media  = State()
    editing_url    = State()

# ───────────────────── админ-роутер ─────────────────────────── #

def get_post_admin_router(news_post_service, prog_admin_filter, cfg) -> Router:
    router = Router()

    topics = getattr(cfg.telegram_channels, "topics", None)
    if isinstance(topics, dict):
        target_chat = topics.get("auto")
    elif hasattr(topics, "auto"):
        target_chat = topics.auto
    else:
        target_chat = None

    target_chat = target_chat or getattr(cfg.telegram_channels, "suggested_chat_id", None)

    # ────────────── edit / delete / confirm ────────────── #

    @router.callback_query(F.data.startswith("edit:"), prog_admin_filter)
    async def edit_callback(cb: CallbackQuery, state: FSMContext):
        post_id = int(cb.data.split(":", 1)[1])
        await edit_post_start(cb.message, state, post_id=post_id)
        await cb.answer()

    @router.callback_query(F.data.startswith("delete:"), prog_admin_filter)
    async def delete_callback(cb: CallbackQuery):
        post_id = int(cb.data.split(":", 1)[1])
        # Удалить оба сообщения (клавиатура и пост)
        try:
            await cb.message.bot.delete_message(cb.message.chat.id, cb.message.reply_to_message.message_id)
            await cb.message.delete()
        except Exception:
            pass
        news_post_service.mark_rejected(post_id)
        await cb.answer("Пост удалён и отмечен как отклонённый.")

    @router.callback_query(F.data.startswith("confirm:"), prog_admin_filter)
    async def confirm_callback(cb: CallbackQuery):
        post_id = int(cb.data.split(":", 1)[1])
        post = news_post_service.get_post(post_id)
        if not post:
            await cb.answer("Новость не найдена в базе.", show_alert=True)
            return

        caption = (
            f"<b>{post.title}</b>\n"
            f"{post.text}"
        )

        try:
            if post.media_ids:
                mids = post.media_ids[:10]
                album = []
                for i, mid in enumerate(mids):
                    file = FSInputFile(Path(MEDIA_DIR) / mid)
                    if i == 0:
                        album.append(InputMediaPhoto(media=file, caption=caption, parse_mode="HTML"))
                    else:
                        album.append(InputMediaPhoto(media=file))
                await cb.bot.send_media_group(chat_id=target_chat, media=album)
            else:
                await cb.bot.send_message(
                    chat_id=target_chat,
                    text=caption,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
        except Exception as e:
            await cb.answer("Ошибка при отправке в канал.", show_alert=True)
            return

        news_post_service.mark_confirmed(post_id)

        try:  # удаляем предложку + клавиатуру
            await cb.message.bot.delete_message(cb.message.chat.id, cb.message.reply_to_message.message_id)
            await cb.message.delete()
        except Exception:
            pass
        await cb.answer("Новость отправлена в канал.")

    # ──────────────── редактирование FSM ──────────────── #

    @router.message(Command("edit"), prog_admin_filter)
    async def edit_post_start(msg: Message, state: FSMContext, post_id: int | None = None):
        try:
            post_id = post_id or int(msg.text.split(maxsplit=1)[1])
        except (IndexError, ValueError):
            await msg.reply("Укажи ID поста: /edit 123")
            return

        post = news_post_service.get_post(post_id)
        if not post:
            await msg.reply("Пост не найден.")
            return

        await state.update_data(post_id=post_id)
        await state.set_state(EditPostState.choosing_field)
        await msg.reply(
            f"Редактируем <b>{post_id}</b>\n\n"
            f"<b>Текущий текст:</b>\n{post.text or ''}\n\n"
            "Что меняем? text / media / url",
            parse_mode="HTML",
        )

    @router.message(EditPostState.choosing_field, prog_admin_filter)
    async def choose_field(msg: Message, state: FSMContext):
        choice = msg.text.strip().lower()
        if choice == "text":
            await msg.reply("Пришли новый текст.")
            await state.set_state(EditPostState.editing_text)
        elif choice == "media":
            await msg.reply("Пришли новое фото/видео или альбом.")
            await state.set_state(EditPostState.editing_media)
        elif choice == "url":
            await msg.reply("Пришли новый URL.")
            await state.set_state(EditPostState.editing_url)
        else:
            await msg.reply("Варианты: text / media / url")

    @router.message(EditPostState.editing_text, prog_admin_filter)
    async def edit_text(msg: Message, state: FSMContext):
        post_id = (await state.get_data())["post_id"]
        news_post_service.update_text(post_id, msg.text)
        await msg.reply("Текст обновлён.")
        await state.clear()

    @router.message(EditPostState.editing_url, prog_admin_filter)
    async def edit_url(msg: Message, state: FSMContext):
        post_id = (await state.get_data())["post_id"]
        news_post_service.update_url(post_id, msg.text)
        await msg.reply("URL обновлён.")
        await state.clear()

    @router.message(EditPostState.editing_media, prog_admin_filter)
    async def edit_media(msg: Message, state: FSMContext):
        post_id = (await state.get_data())["post_id"]
        media_ids = []
        if msg.photo:
            media_ids = [msg.photo[-1].file_id]
        elif msg.video:
            media_ids = [msg.video.file_id]
        elif getattr(msg, "media_group", None):
            for m in msg.media_group:
                fid = m.photo[-1].file_id if m.photo else m.video.file_id
                media_ids.append(fid)
        else:
            await msg.reply("Пришли фото/видео или альбом.")
            return

        news_post_service.update_media(post_id, media_ids)
        await msg.reply("Медиа обновлены.")
        await state.clear()

    # ────────────── справка ────────────── #

    @router.message(Command("edit_help"), prog_admin_filter)
    async def edit_help(msg: Message):
        await msg.reply(
            "/edit <id> — начать редактирование\n"
            "Кнопки: ✏️ / 🗑 / ✅ под сообщением.\n"
            "Доступно программистам и админам.",
            parse_mode="HTML",
        )

    return router
