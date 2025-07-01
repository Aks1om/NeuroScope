# main.py
import sys
import asyncio
import signal

from src.utils.config import load_config
from src.bot.logger import setup_logger
from src.utils.paths import RAW_DB, PROCESSED_DB
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.data_collector.web_scraper_collector import WebScraperCollector
from src.services.collector_service import CollectorService
from src.services.translate_service import TranslateService
from src.services.processed_service import ProcessedService
from src.services.polling_service import PollingService

async def main():
    # 1) Load config
    cfg = load_config('config.yml')
    logger, bot = setup_logger(cfg, __name__)
    logger.debug("Config and logger initialized")

    # 2) Initialize DB clients
    raw_client = DuckDBClient(RAW_DB)
    processed_client = DuckDBClient(PROCESSED_DB)
    raw_repo = DuckDBNewsRepository(raw_client)
    processed_repo = DuckDBNewsRepository(processed_client)
    logger.debug("Databases connected")

    # 3) Create services
    collector = CollectorService(raw_repo=raw_repo, collectors=[WebScraperCollector()], logger=logger)
    translator = TranslateService()
    processor = ProcessedService(raw_repo=raw_repo, processed_repo=processed_repo, translate_service=translator, logger=logger)

    # 4) Start polling
    polling_service = PollingService(
        collector_service=collector,
        processed_service=processor,
        logger=logger,
        interval=cfg.get("poll_interval", 300),
    )

    # Graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Signal received: stopping polling_service...")
        polling_service.stop()
        stop_event.set()

    for sig in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(getattr(signal, sig), _signal_handler)
        except NotImplementedError:
            pass

    logger.info("Starting polling service...")
    polling_task = asyncio.create_task(polling_service.run())
    await stop_event.wait()
    await polling_task

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
