# src/services/polling_service.py
import asyncio
import logging
from typing import Dict

class PollingService:
    """
    Periodically collects and processes news in an endless async loop.
    Supports graceful shutdown and a first-run mode that skips processing.
    """
    def __init__(
        self,
        collector_service,
        processed_service,
        logger: logging.Logger,
        interval: int = 300,
        first_run: bool = True,
    ):
        self.collector = collector_service
        self.processor = processed_service
        self.logger = logger
        self.interval = interval
        self.first_run = first_run
        self._running = False

    async def run(self):
        self._running = True
        self.logger.info(f"PollingService started: interval={self.interval}s, first_run={self.first_run}")
        while self._running:
            stats = await self.poll()
            self.logger.info(f"Cycle stats: collected={stats['collected']} processed={stats['processed']}")
            await asyncio.sleep(self.interval)
        self.logger.info("PollingService stopped.")

    async def poll(self) -> Dict[str, int]:
        stats = {"collected": 0, "processed": 0}
        try:
            # 1) collect raw news
            stats["collected"] = self.collector.collect_and_save()

            # 2) on first run, skip processing to avoid bulk GPT calls
            if self.first_run:
                self.logger.info("First-run mode: skipping processing step.")
                self.first_run = False
                return stats

            # 3) process and save only new items
            stats["processed"] = self.processor.process_and_save()

        except Exception as e:
            self.logger.error(f"PollingService error: {e}")
        return stats

    def stop(self):
        self.logger.info("Stopping PollingService...")
        self._running = False

    def reset(self):
        """
        Reset raw and processed databases and clear media cache.
        """
        from src.utils.paths import RAW_DB, PROCESSED_DB, MEDIA_DIR
        # Recreate databases
        import shutil
        for path in (RAW_DB, PROCESSED_DB):
            try:
                path.unlink()
                self.logger.info(f"Deleted database file: {path}")
            except FileNotFoundError:
                pass
        # Clear media folder
        for file in MEDIA_DIR.glob('*'):
            try:
                file.unlink()
            except Exception:
                self.logger.warning(f"Failed to delete media file {file}")
        self.logger.info("Databases and media directory have been reset.")
        # Next cycle is first-run again
        self.first_run = True