# src/services/polling_service.py
import asyncio
import logging
from aiogram import Bot
from src.services.collector_service import CollectorService
from src.services.processed_service import ProcessedService

class PollingService:
    def __init__(
        self,
        *,
        collector_service: CollectorService,
        processed_service: ProcessedService,
        bot: Bot,
        suggest_group_id: int,
        interval: int = 300,
        first_run: bool = True,
    ):
        self.collector = collector_service
        self.processor = processed_service
        self.bot = bot
        self.suggest_group_id = suggest_group_id
        self.interval = interval
        self.first_run = first_run
        self._running = False
        self.logger = logging.getLogger(__name__)

    async def run(self):
        self._running = True
        while self._running:
            try:
                # 1) Собираем «сырые» новости
                new_items = self.collector.collect_and_save()

                # 2) Если не первый запуск — шлём в группу «предложка»
                if not self.first_run and new_items:
                    for item in new_items:
                        text = (
                            f"🆕 <b>{item['title']}</b>\n"
                            f"{item['url']}\n\n"
                            f"ID: <code>{item['id']}</code>\n"
                            f"Используйте команды в лс для обработки."
                        )
                        await self.bot.send_message(
                            chat_id=self.suggest_group_id,
                            text=text,
                        )
                    self.logger.info(f"Отправили {len(new_items)} новых новостей в предложку.")

                # 3) Первый запуск — пропускаем обработку через GPT
                if self.first_run:
                    self.first_run = False
                    self.logger.info("Первый прогон: пропускаем GPT-обработку.")
                else:
                    # 4) Обрабатываем через TranslateService + ChatGPTService
                    count = self.processor.process_and_save()
                    self.logger.info(f"Обработано {count} новостей через GPT.")

            except Exception as e:
                self.logger.error(f"Ошибка в PollingService: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False