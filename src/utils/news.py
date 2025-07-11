# src/utils/news.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass(slots=True)
class NewsItem:
    id: int
    title: str
    url: str
    date: datetime | None
    text: str
    media_ids: List[str]
    language: str
    topic: str
    # Дополнительные поля для форматтера
    summary: Optional[str] = None
    tags: List[str] = None
    image_url: Optional[str] = None  # первая картинка, если нужна превью