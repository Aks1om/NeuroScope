import argostranslate.package
import argostranslate.translate


# Функция для перевода текста
def translate_text(text, from_code="en", to_code="ru"):
    argostranslate.package.install_from_path("../src/utils/en_ru.argosmodel")
    # Получаем установленные языки
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)
    if not from_lang or not to_lang:
        raise Exception(f"Языковой пакет {from_code}->{to_code} не установлен.")
    translation = from_lang.get_translation(to_lang)
    return translation.translate(text)

# Пример перевода
english_text = """
Three employees of a firm that provided workers to pick grapes for champagne has gone on trial for human trafficking, in one of the biggest labour scandals to hit France’s exclusive sparkling wine industry.

The employees of the firm supplying grape pickers for the champagne harvest in 2023 were charged with human trafficking and exploiting seasonal workers, submitting vulnerable people to undignified housing conditions, and employing foreign nationals without authorisation. The firm itself was also on trial for moral responsibility in the case.

The case, being heard at the criminal court of Châlons-en-Champagne in north-east France, has become known in France as “the grape harvest of shame”.

A police investigation found that a total of 57 men and women, mostly from west African countries and many of them undocumented, were allegedly held in fetid housing. They were allegedly forced to work in conditions likened to slavery while hand-picking grapes in Champagne’s picturesque vineyards, in a region recognised as a Unesco world heritage site.

The case came to light when residents in the small village of Nesle-le-Repons called police to complain about noise and activity in a derelict house during the September 2023 grape harvest.

A labour inspectorate found what it said in a report were “disgusting” and “dilapidated” living conditions at the house.
"""
russian_text = translate_text(english_text)
print(russian_text)