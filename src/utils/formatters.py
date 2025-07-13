from __future__ import annotations
from datetime import datetime
from typing import Protocol, runtime_checkable

# ────────── универсальный интерфейс ────────── #
@runtime_checkable
class NewsProto(Protocol):
    id:        int
    title:     str
    url:       str | None
    date:      datetime | None
    text:      str
    media_ids: list[str]
    language:  str
    topic:     str


# ────────── функции форматирования ────────── #
def build_caption(news: NewsProto) -> str:
    date_str = news.date.strftime("%d.%m.%Y") if news.date else ""
    return f"<b>{news.title}</b>\n\n{news.text}\n\n<i>{date_str}</i>"


def build_meta(news: NewsProto) -> str:
    return (
        f"Источник: <a href=\"{news.url}\">ссылка</a>\n"
        f"ID: <code>{news.id}</code>"
    )
