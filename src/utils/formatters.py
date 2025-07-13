from dataclasses import dataclass
from html import escape
from typing import List, Optional


# ──────────────────────────── модель ──────────────────────────── #

@dataclass(slots=True)
class NewsItem:
    id: int
    title: str
    url: str
    text: str
    # ↓ обязательные закончились — дальше всё опционально
    media_ids: Optional[List[str]] = None
    date: Optional[str] = None
    language: Optional[str] = None
    topic: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    image_url: Optional[str] = None


# ──────────────────────────── utils ──────────────────────────── #

def _e(s: str | None) -> str:
    """HTML-escape без ковычек, None → ''. """
    return escape(s or "", quote=False)


def build_caption(news: NewsItem) -> str:
    parts = [f"<b>{_e(news.title)}</b>"]
    if news.text:
        parts.append(_e(news.text))
    return "\n\n".join(parts)


def build_meta(news: NewsItem) -> str:
    return (
        f"<b>Источник:</b> <a href='{news.url}'>ссылка</a>\n"
        f"<b>ID:</b> {news.id}"
    )
