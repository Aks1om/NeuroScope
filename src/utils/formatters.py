# src/utils/formatters.py
from src.utils.news import NewsItem

def format_news_for_telegram(news_item: NewsItem) -> dict:
    message_parts = []

    # Заголовок (обязательно)
    message_parts.append(f"*{news_item.title.strip()}*")

    # Текст новости (если есть summary)
    if news_item.summary:
        message_parts.append(f"\n_{news_item.summary.strip()}_")

    # Ссылка на источник (если есть)
    if news_item.url:
        message_parts.append(f"\n[Подробнее тут]({news_item.url.strip()})")

    # Теги (если есть)
    if news_item.tags:
        tags_str = ', '.join([f"#{tag.strip().replace(' ', '_')}" for tag in news_item.tags])
        message_parts.append(f"\n{tags_str}")

    full_message = "\n".join(message_parts)

    return {
        "text": full_message,
        "parse_mode": "Markdown",
        "image_url": news_item.image_url
    }
