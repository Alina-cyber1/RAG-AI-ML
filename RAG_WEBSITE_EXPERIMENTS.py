import os
import re
import streamlit as st
from gigachat import GigaChat

# -------------------- НАСТРОЙКИ --------------------
st.set_page_config(
    page_title="RAG-Ассистент AI/ML",
    page_icon="🧠",
    layout="wide"
)

# -------------------- ПОДКЛЮЧЕНИЕ GIGACHAT --------------------
@st.cache_resource
def init_gigachat():
    """Инициализация клиента GigaChat (кэшируется)"""
    credentials = os.getenv("GIGACHAT_SECRET")
    if not credentials:
        st.error("❌ Не найден GIGACHAT_SECRET! Добавьте его в переменные окружения.")
        return None
    
    try:
        from gigachat import GigaChat
        client = GigaChat(
            credentials=credentials,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            timeout=60.0,
            temperature=0.3
        )
        return client
    except Exception as e:
        st.error(f"❌ Ошибка подключения GigaChat: {e}")
        return None

# -------------------- ЗАГРУЗКА БАЗЫ ЗНАНИЙ --------------------
@st.cache_data
def load_topics():
    """Загрузка тем из RAG_KNOWLEDGE_BASE.txt"""
    topics = []
    file_path = "RAG_KNOWLEDGE_BASE.txt"
    
    if not os.path.exists(file_path):
        st.error(f"❌ Файл {file_path} не найден!")
        # Запасные темы для демо
        return [
            {'title': 'DOCKER', 'content': 'Docker — контейнеризация приложений.', 'number': 1},
            {'title': 'SPARK', 'content': 'Spark — распределённая обработка данных.', 'number': 2},
        ]
    
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

# -------------------- ПОИСК ТЕМЫ --------------------
def find_topic(question, topics):
    """Поиск релевантной темы по вопросу"""
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
    
    # Поиск по ключевым словам
    for keyword, topic_num in topic_mapping.items():
        if keyword in q_lower:
            for t in topics:
                if t['number'] == topic_num:
                    return t
    
    # Поиск по заголовку
    for t in topics:
        title_lower = t['title'].lower()
        if any(word in title_lower for word in q_lower.split() if len(word) > 3):
            return t
    
    # Поиск по содержимому
    for t in topics:
        content_lower = t['content'].lower()
        words = [w for w in q_lower.split() if len(w) > 4]
        matches = sum(1 for w in words if w in content_lower)
        if matches >= 2:
            return t
    
    return None

# -------------------- ГЕНЕРАЦИЯ ОТВЕТА --------------------
def ask_gigachat(client, question, context, topic_title):
    """Запрос к GigaChat"""
    prompt = f"""Ты эксперт по курсу AI/ML. Используй ТОЛЬКО контекст ниже.

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
        return "Ошибка получения ответа от GigaChat"
    except Exception as e:
        return f"Ошибка: {str(e)[:100]}"

# -------------------- ИНТЕРФЕЙС STREAMLIT --------------------
def main():
    st.title("🧠 RAG-Ассистент AI/ML")
    st.markdown("Ответы на вопросы по курсу искусственного интеллекта на основе 30 тем")
    
    # Инициализация
    client = init_gigachat()
    topics = load_topics()
    
    if not client:
        st.stop()
    
    # Боковая панель с информацией
    with st.sidebar:
        st.header("📚 Доступные темы")
        for t in topics[:10]:  # Показываем первые 10
            st.write(f"• {t['title']}")
        st.write(f"... и ещё {len(topics)-10} тем")
        
        st.divider()
        st.caption("Система использует тематический поиск + GigaChat")
    
    # Основной чат
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Привет! Я RAG-ассистент. Использую GigaChat + базу знаний из 30 тем. Задайте вопрос!"}
        ]
    
    # Отображение истории чата
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Поле ввода вопроса
    if prompt := st.chat_input("Напишите ваш вопрос..."):
        # Добавляем вопрос пользователя
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Поиск темы
        with st.chat_message("assistant"):
            with st.spinner("🔍 Ищу в базе знаний..."):
                topic = find_topic(prompt, topics)
            
            if not topic:
                answer = """Извините, я не нашёл информацию на этот вопрос в базе знаний.

Доступные темы: Docker, Spark, Kafka, NLP, нейронные сети, градиентный спуск, CNN, LSTM, RAG, PyTorch, TensorFlow, AutoML, компьютерное зрение, Whisper, SQL, FastAPI, GigaChat, Git, CI/CD и другие."""
                source = "Не найдено"
            else:
                with st.spinner("🧠 Генерирую ответ через GigaChat..."):
                    answer = ask_gigachat(client, prompt, topic['content'][:3500], topic['title'])
                    source = topic['title']
                
                # Добавляем источник
                answer += f"\n\n---\n📌 **Источник:** {source}"
            
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
