# src/services/sending_service.py
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import (
    FSInputFile,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from src.data_manager.NewsItem import ProcessedNewsItem
from src.utils.formatters import build_caption, build_meta
from src.utils.paths import MEDIA_DIR


class SendingService:
    MAX_MEDIA   = 10
    FILE_ID_MIN = 40   # строка короче — точно не Telegram file_id

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        processed_repo,
        logger: logging.Logger,
    ):
        self.bot   = bot
        self.chat  = chat_id
        self.repo  = processed_repo
        self.log   = logger

    # ────────── helpers ────────── #
    async def _safe_send_album(self, album: List[InputMediaPhoto]):
        try:
            return await self.bot.send_media_group(self.chat, album)
        except TelegramRetryAfter as e:
            self.log.warning("Flood-control album: %.1f s", e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await self.bot.send_media_group(self.chat, album)
        except TelegramBadRequest as e:
            self.log.error("Album failed: %s", e)

    async def _safe_send_text(
        self,
        text: str,
        kb: InlineKeyboardMarkup | None = None,
    ):
        try:
            return await self.bot.send_message(
                self.chat,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb,
            )
        except TelegramRetryAfter as e:
            self.log.warning("Flood-control text: %.1f s", e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await self.bot.send_message(
                self.chat,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb,
            )

    @staticmethod
    def _edit_kb(post_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[[                       # 👇 добавили text=
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
                InlineKeyboardButton(text="🗑 Удалить",        callback_data=f"delete:{post_id}"),
                InlineKeyboardButton(text="✅ Подтвердить",    callback_data=f"confirm:{post_id}"),
            ]]
        )

    # ────────── core ────────── #
    async def send(self, limit: int, first_run: bool):
        """Отправляет новости в предложку: альбом ≤10 медиа + meta-пост."""
        items: List[ProcessedNewsItem] = self.repo.fetch_unsuggested(limit)

        # На самом первом прогоне просто отмечаем, ничего не отправляем.
        if first_run:
            self.repo.set_flag("suggested", [it.id for it in items])
            self.log.debug("First run: %d записей помечены suggested", len(items))
            return

        for news in items:
            caption = build_caption(news)

            # ---------- альбом ----------
            sent_main = False
            if news.media_ids:
                mids = news.media_ids[: self.MAX_MEDIA]
                album: List[InputMediaPhoto] = []

                for i, mid in enumerate(mids):
                    path = Path(MEDIA_DIR) / mid
                    if path.exists():
                        media_src = FSInputFile(path)
                    elif len(mid) >= self.FILE_ID_MIN and "." not in mid:
                        media_src = mid  # Telegram file_id
                    else:
                        self.log.warning(
                            "Skip media «%s»: файла нет и это не file_id", mid
                        )
                        continue

                    if i == 0:
                        album.append(
                            InputMediaPhoto(media=media_src,
                                            caption=caption,
                                            parse_mode="HTML")
                        )
                    else:
                        album.append(InputMediaPhoto(media=media_src))

                if album:
                    await self._safe_send_album(album)
                    sent_main = True

            # ---------- текстовый пост, если альбома нет ----------
            if not sent_main:
                await self._safe_send_text(caption)

            # ---------- meta ----------
            await self._safe_send_text(build_meta(news), kb=self._edit_kb(news.id))

            # ---------- mark ----------
            self.repo.set_flag("suggested", [news.id])
            await asyncio.sleep(1.0)  # пауза между новостями
