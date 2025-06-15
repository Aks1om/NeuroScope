import logging
from src.data_collector.web_scraper_collector import WebScraperCollector
from src.scheduler.tasks import run_scheduler

class DummyDB:
    def insert_news(self, *args, **kwargs):
        pass  # Притворяется полезным

class DummyFilter:
    def filter(self, news):
        return news  # Ничего не фильтрует, просто пропускает

class DummyAnalyzer:
    def analyze(self, news):
        return news  # Не анализирует, но делает вид

class DummyTelegramBot:
    def send(self, article):
        print(f"\n[TELEGRAM] {article['title']}")
        print(f"URL: {article['url']}")
        print(f"Дата: {article.get('date')}")
        print(f"Текст: {article.get('text')[:300]}...")  # первые 300 символов
        print("Картинки:")
        for img in article.get("images", []):
            print(f" - {img}")

def main():
    logging.basicConfig(level=logging.INFO)

    db = DummyDB()
    scraper_collector = WebScraperCollector(db)
    topic_filter = DummyFilter()
    analyzer = DummyAnalyzer()
    telegram_bot = DummyTelegramBot()

    run_scheduler(
        collectors=[scraper_collector],
        filter_engine=topic_filter,
        analyzer=analyzer,
        telegram_bot=telegram_bot,
        interval=30  # 30 секунд, чтоб не стареть пока тестим
    )

if __name__ == "__main__":
    main()
