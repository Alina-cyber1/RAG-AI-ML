import os
import re
import time
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from gigachat import GigaChat

# ==========================================
# 1. НАСТРОЙКИ И ПЕРЕМЕННЫЕ
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ОТ_BOTFATHER")
GIGACHAT_SECRET = os.getenv("GIGACHAT_SECRET", "ВАШ_СЕКРЕТНЫЙ_КЛЮЧ_GIGACHAT")

# GigaChat
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
# 2. БАЗА ЗНАНИЙ
# ==========================================
def load_topics():
    topics = []
    file_path = "RAG_KNOWLEDGE_BASE.txt"
    
    if not os.path.exists(file_path):
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
# 3. ЛОГИКА ОТВЕТА
# ==========================================
def find_topic(question, topics):
    q_lower = question.lower()
    
    # 1. Сначала попробуем найти по точным ключевым словам (ваш старый список)
    topic_mapping = {
        'spark': 25, 'hadoop': 25, 'pyspark': 25,
        'kafka': 30, 'потоковая обработка': 30,
        'nlp': 17, 'обработка естественного языка': 17,
        'bert': 18, 't5': 18, 'transformer': 18, 'gpt': 18,
        'docker': 6, 'контейнер': 6, 'dockerfile': 22,
        'airflow': 27, 'mlflow': 27, 'mlops': 27,
        'git': 28, 'github': 28, 'gitlab': 28, 'ci/cd': 29,
        'нейронная сеть': 2, 'keras': 2,
        'градиентный спуск': 3,
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
    
    for keyword, topic_num in topic_mapping.items():
        if keyword in q_lower:
            for t in topics:
                if t['number'] == topic_num:
                    return t
    
    # 2. Если не нашли по ключевым словам, ищем по вхождению в любой текст темы
    for t in topics:
        # Разбиваем вопрос на отдельные слова
        words = q_lower.split()
        for word in words:
            # Если слово длиннее 3 букв и встречается в тексте темы
            if len(word) > 3 and word in t['content'].lower():
                return t
    
    # 3. Если ничего не нашли, ищем по заголовку
    for t in topics:
        if any(word.lower() in t['title'].lower() for word in q_lower.split() if len(word) > 3):
            return t
    
    # 4. Если ничего не найдено
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
# 4. ОБРАБОТЧИКИ TELEGRAM (НОВАЯ БИБЛИОТЕКА)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я RAG-ассистент. Задай вопрос по AI/ML!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_question = update.message.text
    topic = find_topic(user_question, topics_data)
    
    if not topic:
        answer = "Извините, я не нашёл информацию на этот вопрос в базе знаний."
    else:
        answer = ask_gigachat(user_question, topic['content'][:3500], topic['title'])
        answer += f"\n\n---\nИсточник: {topic['title']}"
    
    await update.message.reply_text(answer)

# ==========================================
# 5. ВЕБ-СЕРВЕР FLASK (ДЛЯ RENDER)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram RAG Bot is Running!"

# ==========================================
# 6. ТОЧКА ВХОДА (БЕЗ ПОТОКОВ И ASYNCIO)
# ==========================================
if __name__ == "__main__":
    import asyncio
    
    # Настраиваем приложение Telegram
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Запуск Telegram бота...")
    
    # Запускаем веб-сервер в отдельном потоке (чтобы не блокировать бота)
    def run_flask():
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
        
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем бота в основном потоке с правильной asyncio логикой
    print("Бот запущен и слушает сообщения...")
    application.run_polling()
