from src.data_collector.web_scraper.drom_scraper import DromNewsScraper

class WebScraperCollector:
    def __init__(self, db):
        self.db = db
        self.scrapers = [
            DromNewsScraper("https://news.drom.ru/")
        ]

    def collect(self):
        all_news = []
        for scraper in self.scrapers:
            try:
                news = scraper.run()
                all_news.extend(news)
            except Exception as e:
                print(f"[!] Ошибка в {scraper.__class__.__name__}: {e}")
        return all_news
