from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup

class WebScraperBase(ABC):
    def __init__(self, url):
        self.url = url

    @abstractmethod
    def parse(self, html):
        pass

    def fetch(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(self.url, headers=headers)
        response.raise_for_status()
        return response.text

    def run(self):
        html = self.fetch()
        return self.parse(html)
