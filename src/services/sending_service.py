# src/services/sending_service.py
import asyncio
from pathlib import Path
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

class SendingService:
    MAX_MEDIA   = 10
    FILE_ID_MIN = 40   # строка короче — точно не Telegram file_id
    CAPTION_MAX = 1024  # лимит Telegram для caption в альбоме
    TEXT_MAX = 4096  # лимит для обычного сообщения

    def __init__(
        self,
        bot,
        chat_id,
        processed_repo,
        logger,
        build_caption,
        build_meta,
        media_dir,
    ):
        self.bot   = bot
        self.chat  = chat_id
        self.repo  = processed_repo
        self.log   = logger
        self.build_caption = build_caption
        self.build_meta = build_meta
        self.media_dir = media_dir

    @classmethod
    def _clip(cls, text, limit):
        if len(text) <= limit:
            return text, False
        return text[: limit - 1] + "…", True

    async def _safe_send_album(self, album):
        try:
            return await self.bot.send_media_group(self.chat, album)
        except Exception as e:
            if hasattr(e, "retry_after"):
                self.log.warning("Flood-control album: %.1f s", e.retry_after)
                await asyncio.sleep(e.retry_after)
                return await self.bot.send_media_group(self.chat, album)
            self.log.error("Album failed: %s", e)

    async def _safe_send_text(self, text, kb=None):
        try:
            return await self.bot.send_message(
                self.chat,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=kb,
            )
        except Exception as e:
            if hasattr(e, "retry_after"):
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
        """Клавиатура: в callback-data только ID поста."""
        return InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{post_id}"),
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{post_id}"),
            ]]
        )

    @staticmethod
    def _edit_kb(post_id):
        return InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{post_id}"),
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{post_id}"),
            ]]
        )

    async def send(self, limit, first_run):
        items = self.repo.fetch_unsuggested(limit)

        if first_run:
            self.repo.set_flag("suggested", [it.id for it in items])
            self.log.debug("First run: %d записей помечены suggested", len(items))
            return

        for news in items:
            caption, trimmed = self._clip(self.build_caption(news), self.TEXT_MAX)
            album_ids = []
            main_mid = None

            if getattr(news, "media_ids", None):
                album = []
                for i, mid in enumerate(news.media_ids[: self.MAX_MEDIA]):
                    path = Path(self.media_dir) / mid
                    if path.exists():
                        from aiogram.types import FSInputFile, InputMediaPhoto
                        media_src = FSInputFile(path)
                    elif len(mid) >= self.FILE_ID_MIN and "." not in mid:
                        media_src = mid
                    else:
                        self.log.warning("Skip media «%s»: файла нет", mid)
                        continue

                    kwargs = {"caption": caption, "parse_mode": "HTML"} if i == 0 else {}
                    if i == 0:
                        cap, cap_trim = self._clip(caption, self.CAPTION_MAX)
                        trimmed = trimmed or cap_trim
                        kwargs = {"caption": cap, "parse_mode": "HTML"}
                    else:
                        kwargs = {}
                    from aiogram.types import InputMediaPhoto
                    album.append(InputMediaPhoto(media=media_src, **kwargs))

                if album:
                    msgs = await self._safe_send_album(album)
                    album_ids = [m.message_id for m in msgs]
                    if album_ids:
                        main_mid = album_ids[0]

            if main_mid is None:
                msg = await self._safe_send_text(caption)
                main_mid = msg.message_id
                album_ids = [main_mid]

            meta_msg = await self.bot.send_message(
                self.chat,
                self.build_meta(news),
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=self._edit_kb(news.id),
            )
            meta_mid = meta_msg.message_id

            if trimmed:
                warn = (f"⚠️ Текст новости ID={news.id} был обрезан "
                        f"до {self.CAPTION_MAX if getattr(news, 'media_ids', None) else self.TEXT_MAX} символов.")
                await self._safe_send_text(warn)

            self.repo.update_fields(
                news.id,
                main_mid=main_mid,
                meta_mid=meta_mid,
                album_mids=album_ids,
                suggested=True,
            )

            await asyncio.sleep(1.0)
