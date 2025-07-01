# main.py
import sys
import asyncio
import signal

from src.utils.config import load_config
from src.logger.logger import setup_logger
from src.utils.paths import RAW_DB, PROCESSED_DB
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.data_collector.web_scraper_collector import WebScraperCollector
from src.services.collector_service import CollectorService
from src.services.translate_service import TranslateService
from src.services.processed_service import ProcessedService
from src.services.polling_service import PollingService

async def main():
    # 1) Загрузка конфига, логгера и прокси
    cfg = load_config('config.yml')
    logger, bot = setup_logger(cfg, __name__)
    logger.debug("Конфигурация и логгер инициализированы")

    # 2) Инициализация клиентов DuckDB и репозиториев
    raw_client = DuckDBClient(RAW_DB)
    processed_client = DuckDBClient(PROCESSED_DB)
    raw_repo = DuckDBNewsRepository(raw_client)
    processed_repo = DuckDBNewsRepository(processed_client)
    logger.debug("Подключены raw и processed базы")

    # 3) Сбор в raw
    collector = CollectorService(
        raw_repo=raw_repo,
        collectors=[WebScraperCollector()],
        logger=logger,
    )

    # 4) Обработка и перевод → processed
    translator = TranslateService()
    processor = ProcessedService(
        raw_repo=raw_repo,
        processed_repo=processed_repo,
        translate_service=translator,
        logger=logger,
    )

    # 5) Polling Service
    polling_service = PollingService(
        collector_service=collector,
        processed_service=processor,
        logger=logger,
        interval=300,  # каждые 5 минут
    )

    # Graceful shutdown через signal
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Получен сигнал на остановку. Завершаем polling_service...")
        polling_service.stop()
        stop_event.set()

    # На Ctrl+C и SIGTERM вызываем graceful shutdown
    for sig in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(getattr(signal, sig), _signal_handler)
        except NotImplementedError:
            pass

    logger.info("Polling service стартует...")
    polling_task = asyncio.create_task(polling_service.run())
    await stop_event.wait()
    await polling_task  # Дождёмся завершения polling

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())