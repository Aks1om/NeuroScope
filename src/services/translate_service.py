# src/services/translate_service.py

import os
from pathlib import Path
import re
from langdetect import detect as langdetect_detect
import argostranslate.package
import argostranslate.translate

from src.utils.paths import EN_RU_ARGOS

class TranslateService:
    """
    Сервис для перевода текста с одного языка на другой, используя Argos Translate.
    """

    def __init__(
            self,
            model_path: Path = None,
            from_code: str = 'en',
            to_code: str = 'ru'
    ):
        self.from_code = from_code
        self.to_code = to_code

        model_path = Path(model_path or EN_RU_ARGOS)
        argostranslate.package.install_from_path(str(model_path))

        installed = argostranslate.translate.get_installed_languages()
        self.from_lang = next((lang for lang in installed if lang.code == self.from_code), None)
        self.to_lang = next((lang for lang in installed if lang.code == self.to_code), None)
        if not self.from_lang or not self.to_lang:
            raise ValueError(
                f"Модель перевода {self.from_code}->{self.to_code} не найдена или некорректный путь к модели.")

    def translate(self, text: str) -> str:
        """
        Переводит входной текст с self.from_code на self.to_code.
        """
        translation = self.from_lang.get_translation(self.to_lang)
        return translation.translate(text)

    def detect_language(self, text: str) -> str:
        """
        Определяет язык текста: 'ru' если есть кириллица,
        иначе пытается через langdetect, или 'unknown'.
        """
        if re.search(r'[А-Яа-я]', text):
            return 'ru'
        try:
            return langdetect_detect(text)
        except Exception:
            return 'unknown'
