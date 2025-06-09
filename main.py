import logging
#from src.data_collector.rss_collector import RSSCollector
#from src.database.duckdb import DuckDB
#from src.filtering_engine.topic_filter import TopicFilter
#from src.ai_analyzer.model import NewsAnalyzer
from src.telegram_bot.bot import TelegramBot
#from src.scheduler.tasks import run_scheduler

def main():
    logging.basicConfig(level=logging.INFO)

    # Инициализация хранилища
    db = DuckDB()

    # Инициализация модулей сбора
    rss_collector = RSSCollector(db)
    # scraper и api_collector аналогично

    # Модуль фильтрации новостей
    topic_filter = TopicFilter(db)

    # AI-анализатор
    analyzer = NewsAnalyzer(db)

    # Telegram-бот
    telegram_bot = TelegramBot(db)

    # Запуск периодических задач (сбор, фильтрация, анализ и отправка)
    run_scheduler(
        collectors=[rss_collector],  # остальные по необходимости
        filter_engine=topic_filter,
        analyzer=analyzer,
        telegram_bot=telegram_bot
    )

if __name__ == "__main__":
    main()
