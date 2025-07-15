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
    CAPTION_MAX = 1024  # лимит Telegram для caption в альбоме
    TEXT_MAX = 4096  # лимит для обычного сообщения

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
    @classmethod
    def _clip(cls, text: str, limit: int) -> tuple[str, bool]:
        """
        Возвращает (text ≤ limit, was_trimmed?).
        Добавляет «…» при обрезке.
        """

        if len(text) <= limit:
            return text, False
        return text[: limit - 1] + "…", True

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

    # ───────── helpers ───────── #
    @staticmethod
    def _edit_kb(post_id: int) -> InlineKeyboardMarkup:
        """Клавиатура: в callback-data только ID поста."""
        return InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{post_id}"),
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{post_id}"),
            ]]
        )

    # ────────── core ────────── #
    async def send(self, limit: int, first_run: bool):
        """
        Отправляет новости в «предложку».

        • Если у новости < 10 медиа — шлём альбом, иначе один текстовый пост.
        • Сохраняем ВСЕ message_id альбома, чтобы потом удалить без «хвостов».
        • На самом первом запуске (first_run=True) только проставляем флаг
          suggested — ничего не отправляем, чтобы не завалить чат.
        """
        items: List[ProcessedNewsItem] = self.repo.fetch_unsuggested(limit)

        # ── первый прогон: просто отметили и вышли ─────────────────────────
        if first_run:
            self.repo.set_flag("suggested", [it.id for it in items])
            self.log.debug("First run: %d записей помечены suggested", len(items))
            return

        # ── обычный режим ──────────────────────────────────────────────────
        for news in items:
            caption, trimmed = self._clip(build_caption(news), self.TEXT_MAX)
            album_ids: list[int] = []  # все id альбома или [main_mid] для текста
            main_mid: int | None = None

            # ---------- альбом ----------
            if news.media_ids:
                album: list[InputMediaPhoto] = []
                for i, mid in enumerate(news.media_ids[: self.MAX_MEDIA]):
                    path = Path(MEDIA_DIR) / mid
                    if path.exists():  # файл на диске
                        media_src = FSInputFile(path)
                    elif len(mid) >= self.FILE_ID_MIN and "." not in mid:
                        media_src = mid  # Telegram file_id
                    else:
                        self.log.warning("Skip media «%s»: файла нет", mid)
                        continue

                    kwargs = {"caption": caption, "parse_mode": "HTML"} if i == 0 else {}
                    if i == 0:  # только к первой фотке
                        cap, cap_trim = self._clip(caption, self.CAPTION_MAX)
                        trimmed = trimmed or cap_trim
                        kwargs = {"caption": cap, "parse_mode": "HTML"}
                    else:
                        kwargs = {}
                    album.append(InputMediaPhoto(media=media_src, **kwargs))

                if album:
                    msgs = await self._safe_send_album(album)
                    album_ids = [m.message_id for m in msgs]
                    if album_ids:
                        main_mid = album_ids[0]

            # ---------- одиночный текст ----------
            if main_mid is None:  # альбом не отправлен
                msg = await self._safe_send_text(caption)
                main_mid = msg.message_id
                album_ids = [main_mid]

            # ---------- meta ----------
            meta_msg = await self.bot.send_message(
                self.chat,
                f"Источник: <a href='{news.url}'>ссылка</a>\nID: <code>{news.id}</code>",
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=self._edit_kb(news.id),
            )
            meta_mid = meta_msg.message_id

            # ---------- warning для админов ---------- #
            if trimmed:
                warn = (f"⚠️ Текст новости ID={news.id} был обрезан "
                        f"до {self.CAPTION_MAX if news.media_ids else self.TEXT_MAX} символов.")
                await self._safe_send_text(warn)

            # ---------- запись в БД ----------
            self.repo.update_fields(
                news.id,
                main_mid=main_mid,
                meta_mid=meta_mid,
                album_mids=album_ids,  # сохраняем полный список id
                suggested=True,
            )

            await asyncio.sleep(1.0)  # пауза, чтобы не ловить flood-контроль

