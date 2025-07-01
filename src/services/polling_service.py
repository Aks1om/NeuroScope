import asyncio
import logging
from typing import Optional, Dict

class PollingService:
    """
    Periodically collects and processes news in an endless async loop.
    Supports graceful shutdown.
    """
    def __init__(
        self,
        collector_service,
        processed_service,
        logger: logging.Logger,
        interval: int = 300,
    ):
        """
        :param collector_service: Service responsible for collecting news
        :param processed_service: Service responsible for processing news
        :param logger: Logger instance
        :param interval: Polling interval in seconds
        """
        self.collector_service = collector_service
        self.processed_service = processed_service
        self.logger = logger
        self.interval = interval
        self._running = False

    async def run(self):
        """
        Start polling loop. Can be stopped by calling .stop().
        """
        self._running = True
        self.logger.info(f"PollingService запущен с интервалом {self.interval} сек.")
        while self._running:
            await self.poll()
            await asyncio.sleep(self.interval)
        self.logger.info("PollingService остановлен.")

    async def poll(self) -> Dict[str, int]:
        """
        Perform one poll cycle: collect and process news.
        Returns stats: {'collected': int, 'processed': int}
        """
        stats = {'collected': 0, 'processed': 0}
        try:
            collected = self.collector_service.collect_and_save()
            self.logger.info(f"Собрано и сохранено {collected} новостей.")
            stats['collected'] = collected

            processed = self.processed_service.process_and_save()
            self.logger.info(f"Обработано и сохранено {processed} новостей.")
            stats['processed'] = processed
        except Exception as e:
            self.logger.error(f"PollingService error: {e}")
        return stats

    def stop(self):
        """
        Request to stop polling loop after current iteration.
        """
        self.logger.info("PollingService получен запрос на остановку.")
        self._running = False