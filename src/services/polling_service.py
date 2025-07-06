# src/services/polling_service.py
import asyncio

class PollingService:
    def __init__(
        self,
        *,
        collector_service,
        processed_service,
        sending_service,
        bot,
        suggest_group_id,
        interval,
        first_run,
        logger
    ):
        self.collector = collector_service
        self.processor = processed_service
        self.sender = sending_service
        self.bot = bot
        self.suggest_group_id = suggest_group_id
        self.interval = interval
        self.first_run = first_run
        self._running = False
        self.logger = logger

    async def run(self):
        self._running = True
        while self._running:
            try:
                # 1) Собираем и сохраняем raw
                await self.collector.collect_and_save()

                # 2) Обработка (при первом прогоне без GPT)
                processed_count = self.processor.process_and_save(self.first_run)

                # 3) Отправка в Telegram и пометка
                await self.sender.send(processed_count, self.first_run)

                # 4) Сбрасываем флаг первого прогона
                if self.first_run:
                    self.first_run = False

            except Exception as e:
                self.logger.error(f"Ошибка в PollingService: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False