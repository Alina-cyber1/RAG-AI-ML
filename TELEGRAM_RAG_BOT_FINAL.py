import os
import re
import threading
import time
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from gigachat import GigaChat

# ==========================================
# 1. НАСТРОЙКИ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ==========================================
# Вставьте сюда ваши ключи (или они будут взяты из переменных окружения Render)
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ОТ_BOTFATHER")
GIGACHAT_SECRET = os.getenv("GIGACHAT_SECRET", "ВАШ_СЕКРЕТНЫЙ_КЛЮЧ_GIGACHAT")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация GigaChat (с кешированием, чтобы не создавать каждый раз)
def init_gigachat():
    try:
        client = GigaChat(
            credentials=GIGACHAT_SECRET,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            timeout=60.0,
            temperature=0.3
        )
        return client
    except Exception as e:
        print(f"Ошибка подключения к GigaChat: {e}")
        return None

client = init_gigachat()

# ==========================================
# 2. ЗАГРУЗКА БАЗЫ ЗНАНИЙ (RAG_KNOWLEDGE_BASE.txt)
# ==========================================
def load_topics():
    topics = []
    file_path = "RAG_KNOWLEDGE_BASE.txt"
    
    if not os.path.exists(file_path):
        # Если файла нет, возвращаем заглушку
        return [{'title': 'DOCKER', 'content': 'Docker — контейнеризация.', 'number': 1}]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = re.split(r'(=== ТЕМА \d+: [^=]+ ===)', content)
    
    for i in range(1, len(sections), 2):
        title = sections[i].strip().replace('===', '').strip()
        text = sections[i+1].strip() if i+1 < len(sections) else ""
        if title and text:
            topics.append({
                'title': title,
                'content': text,
                'number': i // 2 + 1
            })
    
    return topics

topics_data = load_topics()

# ==========================================
# 3. ЛОГИКА ПОИСКА И ОТВЕТА
# ==========================================
def find_topic(question, topics):
    q_lower = question.lower()
    
    topic_mapping = {
        'spark': 25, 'docker': 6, 'kafka': 30,
        'nlp': 17, 'rag': 7, 'pytorch': 8,
        'tensorflow': 9, 'git': 28, 'fastapi': 15,
        'gigachat': 21, 'cnn': 4, 'lstm': 5,
    }
    
    for keyword, topic_num in topic_mapping.items():
        if keyword in q_lower:
            for t in topics:
                if t['number'] == topic_num:
                    return t
    
    for t in topics:
        if any(word.lower() in t['title'].lower() for word in q_lower.split() if len(word) > 3):
            return t
    
    return None

def ask_gigachat(question, context, topic_title):
    if not client:
        return "Ошибка: GigaChat не подключен."
        
    prompt = f"""Ты эксперт по AI/ML. Используй ТОЛЬКО контекст.

Тема: {topic_title}

Если ответ ЕСТЬ в контексте - дай развёрнутый ответ.
Если ответа НЕТ - напиши: "В базе знаний нет информации."

КОНТЕКСТ:
{context[:3500]}

ВОПРОС: {question}

ОТВЕТ:"""
    
    try:
        response = client.chat(prompt)
        if response and response.choices:
            return response.choices[0].message.content
        return "Ошибка получения ответа"
    except Exception as e:
        return f"Ошибка: {str(e)[:100]}"

# ==========================================
# 4. ОБРАБОТЧИКИ СООБЩЕНИЙ TELEGRAM
# ==========================================
@dp.message()
async def handle_message(message: Message):
    user_question = message.text
    
    # Поиск темы в базе знаний
    topic = find_topic(user_question, topics_data)
    
    if not topic:
        answer = "Извините, я не нашёл информацию на этот вопрос в базе знаний."
        source = "Не найдено"
    else:
        answer = ask_gigachat(user_question, topic['content'][:3500], topic['title'])
        source = topic['title']
        answer += f"\n\n---\nИсточник: {source}"
    
    # Отправляем ответ пользователю
    await message.answer(answer)

# ==========================================
# 5. ФУНКЦИЯ ЗАПУСКА БОТА
# ==========================================
def run_bot():
    print("Telegram бот запущен и слушает сообщения...")
    # Запускаем поллинг (проверку новых сообщений)
    dp.run_polling(bot)

# ==========================================
# 6. ВЕБ-СЕРВЕР (ДЛЯ ОБМАНА RENDER)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram RAG Bot is Running!"

# ==========================================
# 7. ТОЧКА ВХОДА (ЗАПУСК ВСЕГО)
# ==========================================
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке (чтобы не блокировал веб-сервер)
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True  # Если упадет веб-сервер, поток закроется
    bot_thread.start()
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 10000))
    print(f"Веб-сервер запущен на порту {port}...")
    app.run(host='0.0.0.0', port=port)
