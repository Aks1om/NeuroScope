# src/services/processed_service.py

class ProcessedService:
    """
    1. Берёт всё из raw_repo.
    2. Переводит EN→RU (TranslateService).
    3. При необходимости обрабатывает GPT.
    4. Сохраняет уникальные записи в processed_repo.
    """

    def __init__(
        self,
        *,
        raw_repo,
        processed_repo,
        translate_service,
        chat_gpt_service,
        duplicate_filter,
        logger,
        use_chatgpt,
    ):
        self.raw_repo = raw_repo
        self.proc_repo = processed_repo
        self.translate = translate_service
        self.chat_gpt = chat_gpt_service
        self.dup_filter = duplicate_filter
        self.logger = logger
        self.use_chatgpt = use_chatgpt

    # ───────────────────────── helpers ───────────────────────── #
    def _already_done_ids(self):
        return self.proc_repo.all_field("id")

    # ───────────────────────── core ──────────────────────────── #
    def process_and_save(self, first_run):
        done_ids = self._already_done_ids()
        raw_items = self.raw_repo.fetch_all()
        recent_texts = self.dup_filter.get_recent_texts(raw_items, done_ids)
        batch = []

        for item in raw_items:
            if item.id in done_ids:
                continue

            text = item.text

            # 1) проверка на похожие новости (за последние dub_hours_threshold)
            if self.dup_filter.is_similar_recent(text, recent_texts):
                self.logger.debug("Похожая новость уже есть, пропускаем id=%s", item.id)
                continue

            # 2) GPT-обработка
            if not first_run and self.use_chatgpt:
                try:
                    text = self.chat_gpt.process(text)
                except Exception as e:
                    self.logger.error("GPT не справился для %s: %s", item.id, e)
                    continue

            processed = self.proc_repo.model(
                id=item.id,
                title=item.title,
                url=item.url,
                date=item.date,
                text=text,
                media_ids=item.media_ids,
                language=item.language,
                topic=item.topic,
            )
            batch.append(processed)

        if not batch:
            self.logger.debug("Нет новых элементов для обработки.")
            return 0

        unique = self.dup_filter.filter(batch)
        if not unique:
            self.logger.debug("Все элементы оказались дубликатами.")
            return 0

        saved = self.proc_repo.insert_news(unique)
        self.logger.debug("Сохранили в processed: %d", saved)
        return saved
