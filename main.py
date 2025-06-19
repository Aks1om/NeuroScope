# main.py
import logging
from src.utils.config import load_config
from src.utils.paths import RAW_DB
from src.logger.logger import setup_logger
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.data_collector.web_scraper_collector import WebScraperCollector
from src.data_collector.drom_scraper import DromScraperCollector
from src.data_collector.wallpaper_scraper import WallpaperScraperCollector
from src.processing.db_filter import DbFilterEngine
from src.processing.simple_filter import PassThroughFilter
from src.processing.sentiment import SentimentAnalyzer
from src.notification.telegram import TelegramNotifier
from src.services.news_service import NewsService
from src.scheduler.tasks import run_scheduler
from src.data_manager.duckdb_client import DuckDBClient

def main():
    # Загрузка конфигурации и логгера
    cfg = load_config('config.yml')
    logger = setup_logger(__name__)
    logger.info("NeuroScope запустился")



    # Репозиторий (DuckDB)
    repo = DuckDBNewsRepository(cfg.raw_db_path or RAW_DB)

    # Коллекторы данных
    collectors = [
        WebScraperCollector(cfg.sources.web),
        DromScraperCollector(cfg.sources.drom),
        WallpaperScraperCollector(cfg.sources.wallpaper),
    ]

    # Выбор механизма фильтрации
    if getattr(cfg, 'use_db_filter', False):
        filter_engine = DbFilterEngine(repo.client)
        logger.info("Используется DB фильтр")
    else:
        filter_engine = PassThroughFilter()
        logger.info("Используется PassThrough фильтр")

    # Анализатор
    analyzer = SentimentAnalyzer(cfg.analyzer)

    # Нотификатор (Telegram)
    notifier = TelegramNotifier(token=cfg.telegram.token,
                                chat_id=cfg.telegram.chat_id)

    # Сервис-оркестратор
    service = NewsService(
        repository=repo,
        collectors=collectors,
        filter_engine=filter_engine,
        analyzer=analyzer,
        notifier=notifier,
        logger=logger
    )

    # Запуск по расписанию
    run_scheduler(service.run, interval=cfg.scheduler.interval)


if __name__ == "__main__":
    main()