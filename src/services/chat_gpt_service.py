# src/services/chat_gpt_service.py
import os
from openai import OpenAI

class ChatGPTService:
    """
    Обёртка вокруг функции gpt_process_with_proxy.
    Устанавливает и снимает прокси в окружении,
    делает запрос в OpenAI и возвращает результат.
    """

    def __init__(self, api_key, proxy_url=None):
        self.api_key = api_key
        self.proxy_url = proxy_url

    def process(self, news_text):
        """
        Переписывает текст через GPT с прокси.
        """
        old_proxy = os.environ.get('HTTPS_PROXY')
        if self.proxy_url:
            os.environ['HTTPS_PROXY'] = self.proxy_url

        prompt = (
            "Перепиши этот текст для моего Telegram-канала про автомобили. "
            "Сделай его коротким, дерзким и интересным, как будто пишет живой автолюбитель — добавь немного сарказма и эмоций. "
            "Тон должен быть уверенным и разговорным, с лёгким юмором (и даже негодованием, если уместно), но без лишнего молодёжного сленга — текст должен понравиться и молодым, и тем, кто постарше. "
            "Включи важные детали по теме, будто пишешь с экспертным знанием. Если в исходном посте упоминается фото или видео, отрази это в тексте с подходящим комментарием. "
            "Ограничение: итоговый пост должен быть максимально компактным — не длиннее 2–3 коротких абзацев. "
        )

        try:
            client = OpenAI(api_key=self.api_key)
            completion = client.chat.completions.create(
                model="gpt-4.1",
                store=True,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": news_text}
                ]
            )
            return completion.choices[0].message.content.strip()
        finally:
            # Восстанавливаем старый прокси
            if old_proxy is not None:
                os.environ['HTTPS_PROXY'] = old_proxy
            else:
                os.environ.pop('HTTPS_PROXY', None)
