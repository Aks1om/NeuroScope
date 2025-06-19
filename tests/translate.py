import argostranslate.package
import argostranslate.translate

# Функция для перевода текста
def translate_text(text, from_code="en", to_code="ru"):
    # Получаем установленные языки
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)
    if not from_lang or not to_lang:
        raise Exception(f"Языковой пакет {from_code}->{to_code} не установлен.")
    translation = from_lang.get_translation(to_lang)
    return translation.translate(text)

# Пример перевода
english_text = "This is a test article in English. Let's see how well it works!"
russian_text = translate_text(english_text)
print(russian_text)