# src/services/sending_service.py

import logging
from typing import List, Dict, Any
from aiogram import Bot
from aiogram.types import InputMediaPhoto
from src.data_manager.duckdb_repository import DuckDBNewsRepository

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
                f"🆕 <b>{it['title']}</b>\n\n"
                f"{it['content']}\n\n"
                f"<a href=\"{it['url']}\">Читать полностью</a>\n"
                f"ID: <code>{it['id']}</code>"
            )

            media = it.get("media_ids", [])
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
                    await self.bot.send_media_group(chat_id=self.chat_id, media=group)
                except Exception as e:
                    # Если не удалось отправить media_group, падаём обратно на текст
                    self.logger.error(f"Failed to send media_group for {it['id']}: {e}")
                    await self.bot.send_message(chat_id=self.chat_id, text=caption, parse_mode="HTML")
            else:
                await self.bot.send_message(chat_id=self.chat_id, text=caption, parse_mode="HTML")

            sent_ids.append(it["id"])

        # 2) Помечаем отправленные
        if sent_ids:
            self.repo.mark_suggested(sent_ids)
            self.logger.info(f"Sent & marked {len(sent_ids)} items as suggested.")

        return len(sent_ids)


