import os
import re
import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from gigachat import GigaChat

# -------------------- ЛОГГИРОВАНИЕ --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- ПОЛУЧЕНИЕ ТОКЕНОВ --------------------
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GIGACHAT_CREDENTIALS = os.getenv('GIGACHAT_SECRET')

if not BOT_TOKEN:
    raise ValueError("Нет токена Telegram! Добавьте TELEGRAM_BOT_TOKEN в секреты.")
if not GIGACHAT_CREDENTIALS:
    raise ValueError("Нет секрета GigaChat! Добавьте GIGACHAT_SECRET в секреты.")

logger.info("Токены получены")

# -------------------- ИНИЦИАЛИЗАЦИЯ GIGACHAT --------------------
TEMPERATURE = 0.3

gigachat_client = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False,
    timeout=60.0,
    temperature=TEMPERATURE
)
logger.info(f"GigaChat клиент подключен (температура = {TEMPERATURE})")

# -------------------- ЗАГРУЗКА БАЗЫ ЗНАНИЙ --------------------
def load_topics_from_file(file_path="RAG_KNOWLEDGE_BASE.txt"):
    topics = []
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не найден!")
        return topics
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = re.split(r'(=== ТЕМА \d+: [^=]+ ===)', content)
    
    for i in range(1, len(sections), 2):
        title = sections[i].strip()
        text = sections[i+1].strip() if i+1 < len(sections) else ""
        if title and text:
            clean_title = title.replace('===', '').strip()
            topics.append({
                'title': clean_title,
                'content': text,
                'number': i // 2 + 1
            })
    
    logger.info(f"Загружено тем: {len(topics)}")
    return topics

topics = load_topics_from_file("RAG_KNOWLEDGE_BASE.txt")

if not topics:
    logger.warning("Файл RAG_KNOWLEDGE_BASE.txt не найден! Использую темы по умолчанию.")
    topics = [
        {'title': 'DOCKER', 'content': 'Docker — контейнеризация приложений.', 'number': 1},
        {'title': 'SPARK', 'content': 'Spark — распределённая обработка данных.', 'number': 2},
    ]

# -------------------- ПОИСК ТЕМЫ --------------------
def find_topic(question):
    q_lower = question.lower()
    
    topic_mapping = {
        'spark': 25, 'hadoop': 25, 'pyspark': 25,
        'kafka': 30, 'потоковая': 30,
        'nlp': 17, 'обработка естественного языка': 17,
        'bert': 18, 't5': 18, 'transformer': 18, 'gpt': 18,
        'docker': 6, 'контейнер': 6, 'dockerfile': 22,
        'airflow': 27, 'mlflow': 27, 'mlops': 27,
        'git': 28, 'github': 28, 'gitlab': 28, 'ci/cd': 29,
        'нейронная': 2, 'keras': 2,
        'градиентный': 3,
        'cnn': 4, 'сверточная': 4,
        'lstm': 5, 'rnn': 5,
        'rag': 7, 'langchain': 7,
        'pytorch': 8, 'tensorflow': 9,
        'automl': 10,
        'opencv': 11, 'компьютерное зрение': 11, 'yolo': 11,
        'whisper': 13, 'распознавание речи': 13,
        'sql': 14, 'база данных': 14,
        'fastapi': 15,
        'gigachat': 21, 'гигачат': 21,
        'scikit-learn': 26, 'sklearn': 26,
    }

    logger.info(f"Новый запрос: {question}")

    for keyword, topic_num in topic_mapping.items():
        if keyword in q_lower:
            for t in topics:
                if t['number'] == topic_num:
                    logger.info(f"Найдена тема {topic_num}: {t['title']} (по ключу '{keyword}')")
                    return t

    for t in topics:
        title_lower = t['title'].lower()
        if any(word in title_lower for word in q_lower.split() if len(word) > 3):
            logger.info(f"Найдена тема {t['number']}: {t['title']} (по заголовку)")
            return t

    for t in topics:
        content_lower = t['content'].lower()
        words = [w for w in q_lower.split() if len(w) > 4]
        matches = sum(1 for w in words if w in content_lower)
        if matches >= 2:
            logger.info(f"Найдена тема {t['number']}: {t['title']} (по содержимому)")
            return t

    logger.info(f"Тема не найдена для запроса: {question}")
    return None

# -------------------- ЗАПРОС К GIGACHAT --------------------
def ask_gigachat(question, context, topic_title):
    logger.info(f"Отправка запроса к GigaChat. Тема: {topic_title}")

    prompt = f"""Ты эксперт по курсу AI/ML. Используй ТОЛЬКО контекст ниже.

Тема: {topic_title}

Если ответ ЕСТЬ в контексте - дай развёрнутый ответ.
Если ответа НЕТ - напиши: "В базе знаний нет информации."

КОНТЕКСТ:
{context[:3500]}

ВОПРОС: {question}

ОТВЕТ:"""

    try:
        response = gigachat_client.chat(prompt)
        if response and response.choices:
            answer = response.choices[0].message.content
            logger.info(f"Ответ получен, длина: {len(answer)} символов")
            return answer
        return "Ошибка получения ответа от GigaChat"
    except Exception as e:
        logger.error(f"Ошибка GigaChat: {str(e)[:100]}")
        return f"Ошибка: {str(e)[:100]}"

# -------------------- СОЗДАНИЕ БОТА --------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "RAG-Помощник по курсу AI/ML\n\n"
        "Я отвечаю на вопросы, используя:\n"
        "Базу знаний из 30 тем\n"
        "GigaChat для генерации ответов\n\n"
        "Примеры вопросов:\n"
        "- Что такое нейронная сеть?\n"
        "- Что такое Docker?\n"
        "- Что такое Spark?\n"
        "- Что такое Kafka?\n"
        "- Что такое RAG?\n\n"
        "Просто напишите ваш вопрос!"
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        " Доступные темы:\n\n"
        "• Нейронные сети (Keras, TensorFlow, PyTorch)\n"
        "• Градиентный спуск\n"
        "• Свёрточные сети (CNN)\n"
        "• Рекуррентные сети (LSTM, RNN)\n"
        "• Docker, контейнеризация\n"
        "• RAG системы, LangChain\n"
        "• PyTorch, TensorFlow\n"
        "• AutoML\n"
        "• Компьютерное зрение, OpenCV, YOLO\n"
        "• NLP, BERT, T5, трансформеры\n"
        "• Распознавание речи (Whisper)\n"
        "• Базы данных SQL\n"
        "• FastAPI, деплой\n"
        "• GigaChat, локальные модели\n"
        "• Spark, Hadoop, Kafka\n"
        "• Airflow, MLOps\n"
        "• Git, CI/CD, Kubernetes\n\n"
        "Задайте вопрос по любой теме!"
    )

@dp.message()
async def handle_question(message: types.Message):
    question = message.text.strip()

    if not question or question.startswith('/'):
        return

    await bot.send_chat_action(message.chat.id, "typing")

    logger.info(f"Новый запрос от @{message.from_user.username}: {question}")

    topic = find_topic(question)

    if not topic:
        await message.answer(
            "Не нашёл информацию на этот вопрос.\n\n"
            "Попробуйте спросить о:\n"
            "• Нейронных сетях, градиентном спуске\n"
            "• Docker, RAG, PyTorch, TensorFlow\n"
            "• Spark, Kafka, NLP\n"
            "• GigaChat, FastAPI, Git, CI/CD\n\n"
            "Используйте /help для полного списка тем."
        )
        return

    status_msg = await message.answer(f" Найдена тема: {topic['title']}\n\n Формирую ответ через GigaChat...")

    answer = ask_gigachat(question, topic['content'][:3500], topic['title'])

    final_answer = f"{answer}\n\n Источник: {topic['title']}"

    if len(final_answer) > 4000:
        final_answer = final_answer[:3950] + "...\n\n(ответ обрезан)"

    await status_msg.edit_text(final_answer)

    logger.info(f"Ответ отправлен пользователю @{message.from_user.username}")

# -------------------- ЗАПУСК БОТА --------------------
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    info = await bot.get_me()
    
    print("\n" + "="*60)
    print(" TELEGRAM RAG БОТ ЗАПУЩЕН!")
    print("="*60)
    print(f"Бот: @{info.username}")
    print(f"Тем в базе: {len(topics)}")
    print(f"GigaChat: доступен (температура = {TEMPERATURE})")
    print("="*60)
    print("Бот готов отвечать на вопросы!")
    print("="*60)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
