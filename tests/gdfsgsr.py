import asyncio
import duckdb
import os
import json
from collections import defaultdict
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import (
    InputMediaPhoto, InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN", "7014592821:AAEqfe-sfKGt8QKnCNGpLrqWCVqDiwQT-9M")
CHANNEL_ID = '-1002556034541'

db = duckdb.connect("posts.db")
db.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER,
    text TEXT,
    media JSON,
    message_id BIGINT,
    chat_id BIGINT
);
""")

router = Router()

def get_next_post_id():
    result = db.execute("SELECT MAX(id) FROM posts").fetchone()[0]
    return (result or 0) + 1

def get_copy_id_keyboard(post_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Копировать ID",
                    callback_data=f"copyid_{post_id}"
                )
            ]
        ]
    )

media_groups = defaultdict(list)
album_locks = dict()

@router.message(Command("post"))
async def cmd_post(message: types.Message):
    await message.answer(
        "Пришли:\n- только текст\n- текст + 1 фото\n- текст + 1 видео\n- или альбом (2-10 фото/видео с подписью)\n\n"
        "⚠️ Альбом — только одной отправкой скрепкой!"
    )

@router.message()
async def handle_all(message: types.Message, bot: Bot):
    # ======== Альбом (коллаж: фото и/или видео) ========
    if message.media_group_id:
        group_id = message.media_group_id
        media_groups[group_id].append(message)

        if group_id not in album_locks:
            album_locks[group_id] = asyncio.Lock()
            async with album_locks[group_id]:
                await asyncio.sleep(1.4)
                msgs = sorted(media_groups[group_id], key=lambda m: m.message_id)
                if len(msgs) < 2:
                    await msgs[0].answer("Альбом должен содержать минимум 2 медиафайла.")
                    del media_groups[group_id]
                    del album_locks[group_id]
                    return None
                else:
                    media = []
                    caption = msgs[0].caption or ""
                    for idx, m in enumerate(msgs):
                        if m.photo:
                            media.append(InputMediaPhoto(media=m.photo[-1].file_id, caption=caption if idx == 0 else None))
                        elif m.video:
                            media.append(InputMediaVideo(media=m.video.file_id, caption=caption if idx == 0 else None))
                    try:
                        sent = await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
                        post_id = get_next_post_id()
                        # Для правильной структуры медиа в базе
                        media_list = []
                        for m in msgs:
                            if m.photo:
                                media_list.append({"type": "photo", "file_id": m.photo[-1].file_id})
                            elif m.video:
                                media_list.append({"type": "video", "file_id": m.video.file_id})
                        db.execute(
                            "INSERT INTO posts (id, text, media, message_id, chat_id) VALUES (?, ?, ?, ?, ?)",
                            (
                                post_id,
                                caption,
                                json.dumps(media_list),
                                sent[0].message_id,
                                CHANNEL_ID
                            )
                        )
                        await msgs[0].answer(
                            f"Пост-альбом опубликован!\nID: <code>{post_id}</code>",
                            reply_markup=get_copy_id_keyboard(post_id),
                            parse_mode=ParseMode.HTML
                        )
                        del media_groups[group_id]
                        del album_locks[group_id]
                        return post_id
                    except Exception as e:
                        await msgs[0].answer(f"Ошибка при отправке альбома: {e}")
                        del media_groups[group_id]
                        del album_locks[group_id]
                        return None
        else:
            return None

    # ======= Одиночное видео =======
    elif message.video:
        caption = message.caption or message.text or ""
        file_id = message.video.file_id
        sent = await bot.send_video(chat_id=CHANNEL_ID, video=file_id, caption=caption)
        post_id = get_next_post_id()
        db.execute(
            "INSERT INTO posts (id, text, media, message_id, chat_id) VALUES (?, ?, ?, ?, ?)",
            (post_id, caption, json.dumps([{"type": "video", "file_id": file_id}]), sent.message_id, CHANNEL_ID)
        )
        await message.answer(
            f"Пост с видео опубликован!\nID: <code>{post_id}</code>",
            reply_markup=get_copy_id_keyboard(post_id),
            parse_mode=ParseMode.HTML
        )
        return post_id

    # ======= Одиночное фото =======
    elif message.photo:
        caption = message.caption or message.text or ""
        file_id = message.photo[-1].file_id
        sent = await bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption)
        post_id = get_next_post_id()
        db.execute(
            "INSERT INTO posts (id, text, media, message_id, chat_id) VALUES (?, ?, ?, ?, ?)",
            (post_id, caption, json.dumps([{"type": "photo", "file_id": file_id}]), sent.message_id, CHANNEL_ID)
        )
        await message.answer(
            f"Пост с фото опубликован!\nID: <code>{post_id}</code>",
            reply_markup=get_copy_id_keyboard(post_id),
            parse_mode=ParseMode.HTML
        )
        return post_id

    # ======= Только текст =======
    elif message.text:
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=message.text)
        post_id = get_next_post_id()
        db.execute(
            "INSERT INTO posts (id, text, media, message_id, chat_id) VALUES (?, ?, ?, ?, ?)",
            (post_id, message.text, None, sent.message_id, CHANNEL_ID)
        )
        await message.answer(
            f"Текстовый пост опубликован!\nID: <code>{post_id}</code>",
            reply_markup=get_copy_id_keyboard(post_id),
            parse_mode=ParseMode.HTML
        )
        return post_id

    else:
        await message.answer("Пришли только текст, текст с одним фото/видео или альбом (2-10 медиа).")
        return None

@router.callback_query(F.data.startswith("copyid_"))
async def copy_id_callback(callback: types.CallbackQuery):
    post_id = callback.data.split("_", 1)[1]
    await callback.answer("ID скопирован в буфер обмена!", show_alert=True)
    await callback.message.edit_text(
        f"ID поста: <code>{post_id}</code>\n(Скопируй вручную)",
        parse_mode=ParseMode.HTML
    )

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
