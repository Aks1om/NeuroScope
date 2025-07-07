# src/services/sending_service.py
import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import InputMediaPhoto, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from src.utils.paths import MEDIA_DIR

class SendingService:
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        processed_repo,
        logger: logging.Logger,
    ):
        self.bot = bot
        self.chat_id = chat_id
        self.processed_repo = processed_repo
        self.logger = logger
        # Время последней отправки медиа-группы
        self._last_media_group_time = 0.0

    async def _send_media_group_throttled(self, media: list[InputMediaPhoto]):
        """Отправляет медиа-группу, соблюдая ограничение в 1 секунду между вызовами."""
        loop = asyncio.get_event_loop()
        now = loop.time()
        elapsed = now - self._last_media_group_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        result = await self.bot.send_media_group(
            chat_id=self.chat_id,
            media=media
        )
        # Обновляем время последней отправки
        self._last_media_group_time = loop.time()
        return result

    async def send(self, limit: int, first_run: bool):
        """
        Отправляет неотправленные новости в Telegram.
        Ограничивает количество отправляемых элементов параметром limit.
        При первом прогоне помечает все новости как отправленные и ничего не отправляет.
        """
        # При первом запуске не шлём ничего, просто помечаем все новости
        if first_run:
            try:
                if hasattr(self.processed_repo, 'mark_all_suggested'):
                    self.processed_repo.mark_all_suggested()
                else:
                    ids = [item['id'] for item in self.processed_repo.fetch_unsuggested(limit)]
                    self.processed_repo.mark_suggested(ids)
                self.logger.debug("Первый прогон: все новости помечены как отправленные")
            except Exception as e:
                self.logger.error(f"Ошибка при пометке всех новостей: {e}")
            return

        items = self.processed_repo.fetch_unsuggested(limit=limit)
        if not items:
            self.logger.debug("Нет новостей для отправки.")
            return

        for it in items:
            title = it.get('title', '')
            text = it.get('text') or it.get('content', '')
            url = it.get('url', '')
            media_ids = it.get('media_ids', [])

            msg_text = f"<b>{title}</b>\n{text}\n<a href='{url}'>Читать далее</a>"

            # Отправка текстового сообщения
            try:
                text_msg = await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=msg_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except TelegramRetryAfter as e:
                self.logger.warning(f"Flood control: retry after {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
                text_msg = await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=msg_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            first_msg_id = text_msg.message_id

            # Если есть медиа, отправляем альбом (до 10 фото)
            if media_ids:
                if len(media_ids) > 10:
                    self.logger.warning(
                        f"Media count {len(media_ids)} > 10 for {it['id']}, sending only first 10"
                    )
                album_ids = media_ids[:10]
                album = []  # type: list[InputMediaPhoto]
                for media_id in album_ids:
                    path = MEDIA_DIR / media_id
                    album.append(InputMediaPhoto(media=FSInputFile(str(path))))

                try:
                    await self._send_media_group_throttled(album)
                except TelegramRetryAfter as e:
                    self.logger.warning(f"Flood control: retry after {e.retry_after}s")
                    await asyncio.sleep(e.retry_after)
                    await self._send_media_group_throttled(album)
                except TelegramBadRequest as e:
                    self.logger.error(f"Failed media_group for {it['id']}: {e}")

            # Отправка клавиатуры под текстовым сообщением
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"Управление постом ID: <code>{it['id']}</code>",
                    reply_markup=self._edit_keyboard(it['id']),
                    parse_mode='HTML',
                    reply_to_message_id=first_msg_id
                )
            except Exception as e:
                self.logger.error(f"Failed to send control keyboard for {it['id']}: {e}")

            # Помечаем как отправленное
            self.processed_repo.mark_suggested([it['id']])

            # Пауза между отправками элементов (чтобы не перегружать Telegram)
            await asyncio.sleep(1.0)

    def _edit_keyboard(self, post_id: int) -> InlineKeyboardMarkup:
        """
        Создаёт InlineKeyboardMarkup с кнопками редактирования и удаления.
        """
        btn_edit = InlineKeyboardButton(
            text='Редактировать', callback_data=f'edit:{post_id}'
        )
        btn_delete = InlineKeyboardButton(
            text='Удалить', callback_data=f'delete:{post_id}'
        )
        return InlineKeyboardMarkup(inline_keyboard=[[btn_edit, btn_delete]])
