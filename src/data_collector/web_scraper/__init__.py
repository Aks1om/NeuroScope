# src/data_collector/web_scraper/web_scraper_base.py

from abc import ABC, abstractmethod
import requests


class WebScraperBase(ABC):
    """
    Абстрактный базовый класс для всех web-скраper-ов.

    Каждый наследник должен реализовать метод parse(html),
    возвращающий список словарей с ключами:
      title, url, date, content, media_ids.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url

    def fetch(self) -> str:
        """Скачивает HTML-страницу по base_url и возвращает текст."""
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(self.base_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text

    @abstractmethod
    def parse(self, html: str) -> list[dict]:
        """
        Парсит HTML и возвращает список новостей.
        Каждая новость — dict с ключами:
        title, url, date, content, media_ids.
        """
        ...

    def run(self) -> list[dict]:
        """Скачивает страницу и запускает парсинг."""
        html = self.fetch()
        return self.parse(html)
