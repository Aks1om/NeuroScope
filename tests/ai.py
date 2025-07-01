import accelerate
from transformers import AutoTokenizer, AutoModelForCausalLM
import os

os.environ["HF_HOME"] = r"E:\For coding"
os.environ["TRANSFORMERS_CACHE"] = r"E:\For coding"

MODEL = "Yandex/YandexGPT-5-Lite-8B-Instruct"

# Загрузка токенизатора и модели
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    torch_dtype="auto",      # Можно явно: torch.float16
    device_map="cuda"        # Или "auto"
)

def generate_telegram_post(news_text, prompt_template):
    # Формируем финальный промпт через .format(news=...)
    full_prompt = prompt_template.format(news=news_text)
    input_ids = tokenizer(full_prompt, return_tensors="pt").input_ids.to(model.device)
    output_ids = model.generate(
        input_ids,
        max_new_tokens=200,  # Длина вывода
        temperature=1.2,  # Креативность
        top_p=0.95,  # Разнообразие
        do_sample=True,  # Сэмплирование
        pad_token_id=tokenizer.eos_token_id,
    )
    post = tokenizer.decode(output_ids[0][input_ids.shape[-1]:], skip_special_tokens=True)
    return post.strip()

# === ТВОЙ ПРОМПТ ===
prompt_template = (
    "Ты — редактор автомобильного Telegram-канала.\n"
    "Оформи новость в стиле автожурнала:\n"
    "— Начни с броского, цепляющего утверждения или главного факта.\n"
    "— Раскрой детали короткими, ёмкими фразами с элементами “автожаргона” (допускаются слова вроде “лошадей”, “робот”, “база”, “бензинка”, “гибрид”).\n"
    "— Заверши коротким выводом или личным мнением, чтобы пост был не сухим.\n"
    "Пиши без лишней канцелярщины, максимально по-человечески и живо, как для автоканала в Telegram.\n\n"
    "Новость:\n"
    "{news}\n\n"
    "Пост:"
)

# === ТЕКСТ НОВОСТИ ===
news_text = (
    """
    Электромобиль Атом разработан под «поколенческое изменение отношения к автомобилю» — молодежь в крупных городах теперь предпочитает каршеринг и такси, но не спешит приобретать машину в личное пользование, об этом в интервью изданию РБК заявил гендиректор КАМАЗа Сергей Когогин. Напомним, КАМАЗ — ключевой инвестор проекта первого российского массового электромобиля.
    Атом ориентирован под потребности каршеринга и такси по той причине, что в традиционных потребительских нишах «бороться с китайским автопромом невозможно», подчеркнул Когогин.
    Ранее сообщалось о том, что на автозаводе «Москвич» завершается создание линий по серийному производству Атома. Выпуск новинки стартует в конце июля. Габаритная длина электромобиля — четыре метра, особенность конструкции — отсутствие центральных стоек кузова.
    """
)

# === Генерация поста ===
post = generate_telegram_post(news_text, prompt_template)
print(post)

