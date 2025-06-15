import time
import logging

def run_scheduler(collectors, filter_engine, analyzer, telegram_bot, interval=300):
    while True:
        logging.info("[Scheduler] Запуск цикла сбора и обработки")

        all_news = []
        for collector in collectors:
            try:
                news = collector.collect()
                all_news.extend(news)
                logging.info(f"[{collector.__class__.__name__}] Собрано {len(news)} новостей")
            except Exception as e:
                logging.error(f"[!] Ошибка в {collector.__class__.__name__}: {e}")

        if not all_news:
            logging.info("[Scheduler] Новостей нет. Спим...")
            time.sleep(interval)
            continue

        filtered_news = filter_engine.filter(all_news)
        logging.info(f"[Filter] Отфильтровано: {len(filtered_news)}")

        analyzed_news = analyzer.analyze(filtered_news)
        logging.info(f"[Analyzer] Проанализировано: {len(analyzed_news)}")

        for article in analyzed_news:
            try:
                telegram_bot.send(article)
            except Exception as e:
                logging.error(f"[TelegramBot] Ошибка при отправке новости: {e}")

        logging.info("[Scheduler] Цикл завершён. Спим...")
        time.sleep(interval)