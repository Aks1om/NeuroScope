# src/services/news_service.py
import logging

class NewsService:
    """
    Оркестратор бизнес-логики: сбор, фильтрация, анализ, сохранение и отправка.
    """
    def __init__(self,
                 repository,
                 collectors: list,
                 filter_engine,
                 analyzer,
                 notifier,
                 logger: logging.Logger):
        self.repo = repository
        self.collectors = collectors
        self.filter_engine = filter_engine
        self.analyzer = analyzer
        self.notifier = notifier
        self.logger = logger

    def run(self):
        self.logger.info("Запуск NewsService.run()")
        # Сбор сырых данных
        items = []
        for collector in self.collectors:
            try:
                collected = collector.collect()
                self.logger.debug(f"{collector.__class__.__name__} собрал {len(collected)} элементов")
                items.extend(collected)
            except Exception as e:
                self.logger.error(f"Ошибка при сборе данных: {e}")
        # Фильтрация
        try:
            filtered = self.filter_engine.filter(items)
            self.logger.debug(f"Отфильтровано {len(filtered)} элементов")
        except Exception as e:
            self.logger.error(f"Ошибка при фильтрации: {e}")
            return
        # Анализ
        try:
            analyzed = self.analyzer.analyze(filtered)
            self.logger.debug(f"Проанализировано {len(analyzed)} элементов")
        except Exception as e:
            self.logger.error(f"Ошибка при анализе: {e}")
            return
        # Сохранение
        try:
            self.repo.insert_news(analyzed)
            self.logger.info(f"Сохранено {len(analyzed)} новостей в БД")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении в БД: {e}")
        # Уведомления
        for item in analyzed:
            try:
                self.notifier.send(item)
                self.logger.info(f"Отправлено уведомление: {item.get('title')}")
            except Exception as e:
                self.logger.error(f"Ошибка при отправке уведомления: {e}")