# src/utils/news.py
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class NewsItem:
    id: int
    source: str
    title: str
    content: Optional[str]
    summary: Optional[str]
    url: Optional[str]
    image_url: Optional[str]
    tags: List[str]
    published_at: datetime
