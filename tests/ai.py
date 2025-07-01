from transformers import AutoTokenizer, AutoModelForCausalLM, GPT2TokenizerFast, EncoderDecoderModel
import torch
import os

model_name = "IlyaGusev/rubert_telegram_headlines"
tokenizer = AutoTokenizer.from_pretrained(model_name, do_lower_case=False, do_basic_tokenize=False, strip_accents=False)
model = EncoderDecoderModel.from_pretrained(model_name)

article_text = (
    """
    Электромобиль Атом разработан под «поколенческое изменение отношения к автомобилю» — молодежь в крупных городах теперь предпочитает каршеринг и такси, но не спешит приобретать машину в личное пользование, об этом в интервью изданию РБК заявил гендиректор КАМАЗа Сергей Когогин. Напомним, КАМАЗ — ключевой инвестор проекта первого российского массового электромобиля.
    Атом ориентирован под потребности каршеринга и такси по той причине, что в традиционных потребительских нишах «бороться с китайским автопромом невозможно», подчеркнул Когогин.
    Ранее сообщалось о том, что на автозаводе «Москвич» завершается создание линий по серийному производству Атома. Выпуск новинки стартует в конце июля. Габаритная длина электромобиля — четыре метра, особенность конструкции — отсутствие центральных стоек кузова.
    """
)


input_ids = tokenizer(
    [article_text],
    add_special_tokens=True,
    max_length=256,
    padding="max_length",
    truncation=True,
    return_tensors="pt",
)["input_ids"]

output_ids = model.generate(
    input_ids=input_ids,
    max_length=64,
    no_repeat_ngram_size=3,
    num_beams=10,
    top_p=0.95
)[0]

headline = tokenizer.decode(output_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
print(headline)