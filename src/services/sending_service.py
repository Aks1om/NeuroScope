# src/services/sending_service.py
import asyncio
import logging
from pathlib import Path
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import (
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

from src.utils.paths import MEDIA_DIR
from src.utils.formatters import NewsItem, build_caption, build_meta


class SendingService:
    MAX_PHOTOS = 10

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        processed_repo,
        logger: logging.Logger,
    ):
        self.bot = bot
        self.chat_id = chat_id
        self.repo = processed_repo
        self.logger = logger

    # ────────────────────────────── helpers ───────────────────────────── #

    async def _send_media_group(self, media: List[InputMediaPhoto]):
        try:
            return await self.bot.send_media_group(self.chat_id, media)
        except TelegramRetryAfter as e:
            self.logger.warning("Flood control (album): %s s", e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await self.bot.send_media_group(self.chat_id, media)

    async def _send_text(self, text: str, kb: InlineKeyboardMarkup | None = None):
        try:
            return await self.bot.send_message(
                self.chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb,
            )
        except TelegramRetryAfter as e:
            self.logger.warning("Flood control: %s s", e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await self.bot.send_message(
                self.chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb,
            )

    @ staticmethod
    def _edit_keyboard(post_id: int) -> InlineKeyboardMarkup:
        """Инлайн-клавиатура для модерации поста (aiogram v3)."""
        kb = [
            [
                InlineKeyboardButton(text = "✏️ Редактировать", callback_data = f"edit:{post_id}"),
                InlineKeyboardButton(text = "🗑 Удалить", callback_data = f"delete:{post_id}"),
                InlineKeyboardButton(text = "✅ Подтвердить", callback_data = f"confirm:{post_id}"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=kb)

    # ─────────────────────────────── core ─────────────────────────────── #

    async def send(self, limit: int, first_run: bool):
        """
        Шлёт новости в канал/предложку.
        Итог: два сообщения на новость:
          1) пост (заголовок + текст + ≤10 фото)
          2) meta-пост «Источник / ID» + inline-кнопки
        """
        items = self.repo.fetch_unsuggested(limit)
        if first_run:
            self.repo.mark_suggested([it["id"] for it in items])
            self.logger.debug("First run → just mark %d posts sent", len(items))
            return

        for raw in items:
            news = NewsItem(**raw)

            # ---------- 1) главный пост ----------
            caption = build_caption(news)

            if news.media_ids:                        # есть фото → альбом
                mids = news.media_ids[: self.MAX_PHOTOS]
                if len(news.media_ids) > self.MAX_PHOTOS:
                    self.logger.warning("Photos > %d, берём первые.", self.MAX_PHOTOS)

                album: List[InputMediaPhoto] = []
                for i, mid in enumerate(mids):
                    file = FSInputFile(Path(MEDIA_DIR) / mid)
                    if i == 0:
                        album.append(InputMediaPhoto(media=file, caption=caption, parse_mode="HTML"))
                    else:
                        album.append(InputMediaPhoto(media=file))
                await self._send_media_group(album)

            else:                                     # без фото → просто текст
                await self._send_text(caption)

            # ---------- 2) meta-пост ----------
            meta_text = build_meta(news)
            kb = self._edit_keyboard(news.id)
            await self._send_text(meta_text, kb)

            # ---------- отметка "отправлено" ----------
            self.repo.mark_suggested([news.id])
            await asyncio.sleep(1.0)                  # чуть притормозим
