import asyncio
from pathlib import Path
from src.bot.keyboards import main_keyboard
from src.data_manager.models import SentNewsItem

class SendingService:
    MAX_MEDIA   = 10
    FILE_ID_MIN = 40
    CAPTION_MAX = 1024
    TEXT_MAX    = 4096

    def __init__(
        self,
        bot,
        chat_id,
        processed_repo,
        sent_repo,
        logger,
        build_caption,
        build_meta,
        media_dir,
    ):
        self.bot   = bot
        self.chat  = chat_id
        self.processed_repo  = processed_repo
        self.sent_repo = sent_repo
        self.logger   = logger
        self.build_caption = build_caption
        self.build_meta = build_meta
        self.media_dir = media_dir

    async def send(self, limit: int = 10, first_run: bool = False):
        items = self.processed_repo.fetch_unsuggested(limit)

        if first_run:
            self.processed_repo.set_flag("suggested", [it.id for it in items])
            self.logger.debug("Первый запуск: %d записей помечены как предложенные", len(items))
            return

        for news in items:
            try:
                caption, trimmed = self._clip(self.build_caption(news), self.TEXT_MAX)

                # --- Медиа ---
                main_mid, album_ids = await self._send_media(news, caption)

                # --- Если только текст ---
                if main_mid is None:
                    msg = await self._safe_send_text(caption)
                    main_mid = msg.message_id
                    album_ids = [main_mid]

                # --- Meta сообщение ---
                meta_msg = await self.bot.send_message(
                    self.chat,
                    self.build_meta(news),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=main_keyboard(news.id),
                )
                meta_mid = meta_msg.message_id
                album_ids.append(meta_mid)

                if trimmed:
                    warn = (
                        f"⚠️ Текст новости ID={news.id} был обрезан "
                        f"до {self.CAPTION_MAX if news.media_ids else self.TEXT_MAX} символов."
                    )
                    await self._safe_send_text(warn)

                self.processed_repo.set_flag("suggested", [news.id])
                self.sent_repo.insert_news([
                    SentNewsItem(
                        id=news.id,
                        title=news.title,
                        url=news.url,
                        date=news.date,
                        text=news.text,
                        media_ids=news.media_ids,
                        language=news.language,
                        topic=news.topic,
                        confirmed=False,
                        main_message_id=main_mid,
                        others_message_ids=album_ids
                    )
                ])

                await asyncio.sleep(1.0)

            except Exception as e:
                self.logger.error("Ошибка при отправке новости %s: %s", news.id, e)

    async def _send_media(self, news, caption):
        from aiogram.types import FSInputFile, InputMediaPhoto

        if not news.media_ids:
            return None, []

        album = []
        main_mid = None
        album_ids = []
        trimmed = False

        for i, mid in enumerate(news.media_ids[: self.MAX_MEDIA]):
            path = Path(self.media_dir) / mid
            if path.exists():
                media_src = FSInputFile(path)
            elif len(mid) >= self.FILE_ID_MIN and "." not in mid:
                media_src = mid
            else:
                self.logger.warning("Пропускаем медиа «%s»: файла нет", mid)
                continue

            # Только к первой фотке прикрепляем подпись
            if i == 0:
                cap, cap_trim = self._clip(caption, self.CAPTION_MAX)
                trimmed = trimmed or cap_trim
                kwargs = {"caption": cap, "parse_mode": "HTML"}
            else:
                kwargs = {}
            album.append(InputMediaPhoto(media=media_src, **kwargs))

        if not album:
            return None, []

        msgs = await self._safe_send_album(album)
        album_ids = [m.message_id for m in msgs]
        main_mid = album_ids[0] if album_ids else None

        return main_mid, album_ids

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
                self.logger.warning("Флуд-контроль альбома: %.1f сек", e.retry_after)
                await asyncio.sleep(e.retry_after)
                return await self.bot.send_media_group(self.chat, album)
            self.logger.error("Ошибка при отправке альбома: %s", e)
            return []

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
                self.logger.warning("Флуд-контроль текста: %.1f сек", e.retry_after)
                await asyncio.sleep(e.retry_after)
                return await self.bot.send_message(
                    self.chat,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=kb,
                )
            self.logger.error("Ошибка при отправке текста: %s", e)
