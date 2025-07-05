# src/services/sending_service.py

import logging
from typing import List, Dict, Any
from aiogram import Bot
from aiogram.types import (
    InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton, Message
)
from src.data_manager.duckdb_repository import DuckDBNewsRepository

def edit_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для редактирования поста"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"editpost_{post_id}"
                )
            ]
        ]
    )

class SendingService:
    """
    send(count, first_run):
      - Если first_run: помечает все существующие processed_news как suggested и возвращает 0
      - Иначе: вытаскивает из processed_news до count записей с suggested=FALSE,
               отправляет их в Telegram, помечает как suggested и возвращает число отправленных.
    """

    def __init__(
        self,
        processed_repo: DuckDBNewsRepository,
        bot: Bot,
        suggest_group_id: int,
        logger: logging.Logger,
    ):
        self.repo = processed_repo
        self.bot = bot
        self.chat_id = suggest_group_id
        self.logger = logger

    async def send(self, count, first_run: bool) -> int:
        # Первый прогон — просто пометить всё, ничего не шлём
        if first_run:
            self.repo.mark_all_suggested()
            return 0

        if count <= 0:
            return 0

        # 1) Берём данные
        items = self.repo.fetch_unsuggested(count)
        sent_ids: List[int] = []

        for it in items:
            caption = (
                f"<b>{it['title']}</b>\n\n"
                f"{it['content']}\n\n"
                f"<a href=\"{it['url']}\">Читать полностью</a>\n"
                f"ID: <code>{it['id']}</code>"
            )

            media = it.get("media_ids", [])
            msg: Message = None

            if media:
                # Формируем media_group с первой подписью
                group = []
                for idx, url in enumerate(media):
                    media_item = InputMediaPhoto(media=url)
                    if idx == 0:
                        media_item.caption = caption
                        media_item.parse_mode = "HTML"
                    group.append(media_item)
                try:
                    msgs = await self.bot.send_media_group(chat_id=self.chat_id, media=group)
                    # Отправить кнопку редактирования отдельным сообщением-реплаем на первую часть media_group
                    if msgs:
                        await self.bot.send_message(
                            chat_id=self.chat_id,
                            text=f"Управление постом ID: <code>{it['id']}</code>",
                            reply_markup=edit_keyboard(it["id"]),
                            parse_mode="HTML",
                            reply_to_message_id=msgs[0].message_id
                        )
                except Exception as e:
                    # Если не удалось отправить media_group, падаем обратно на текст
                    self.logger.error(f"Failed to send media_group for {it['id']}: {e}")
                    msg = await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=caption,
                        parse_mode="HTML",
                        reply_markup=edit_keyboard(it["id"])
                    )
                else:
                    msg = await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=caption,
                        parse_mode="HTML",
                        reply_markup=edit_keyboard(it["id"])
                    )

                sent_ids.append(it["id"])

        # 2) Помечаем отправленные
        if sent_ids:
            self.repo.mark_suggested(sent_ids)
            self.logger.debug(f"Отмечено {len(sent_ids)} как отправленные")

        return len(sent_ids)


