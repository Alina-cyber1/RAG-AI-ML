import os
import re
import streamlit as st
from gigachat import GigaChat

# -------------------- НАСТРОЙКИ СТРАНИЦЫ --------------------
st.set_page_config(
    page_title="RAG-Ассистент AI/ML",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- КАСТОМНЫЙ CSS ДЛЯ ФИОЛЕТОВОГО ИНТЕРФЕЙСА --------------------
st.markdown("""
<style>
    /* Главный фиолетовый цвет */
    :root {
        --primary-purple: #6C35DE;
        --dark-purple: #4A1A9E;
        --light-purple: #E8DCF8;
    }

    /* Стили заголовка */
    h1 {
        color: var(--primary-purple) !important;
        font-weight: 600 !important;
        padding-bottom: 10px;
        border-bottom: 3px solid var(--light-purple);
    }

    /* Стили сообщений в чате */
    .stChatMessage {
        background-color: #F8F9FA;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    
    /* Сообщения ассистента (фиолетовый оттенок) */
    .stChatMessage[data-testid="chatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
        background-color: #F3EEFF;
        border-left: 4px solid var(--primary-purple);
    }

    /* Кнопка отправки (фиолетовая) */
    .stChatInput button {
        background-color: var(--primary-purple) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
    }
    .stChatInput button:hover {
        background-color: var(--dark-purple) !important;
    }

    /* Стили сайдбара */
    section[data-testid="stSidebar"] {
        background-color: #F8F5FF;
        border-right: 1px solid #E0D4F5;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: var(--primary-purple) !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- ПОДКЛЮЧЕНИЕ GIGACHAT --------------------
@st.cache_resource
def init_gigachat():
    credentials = os.getenv("GIGACHAT_SECRET")
    if not credentials:
        st.error("Не найден GIGACHAT_SECRET!")
        return None
    
    try:
        client = GigaChat(
            credentials=credentials,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            timeout=60.0,
            temperature=0.3
        )
        return client
    except Exception as e:
        st.error(f"Ошибка подключения: {e}")
        return None

# -------------------- ЗАГРУЗКА БАЗЫ ЗНАНИЙ --------------------
@st.cache_data
def load_topics():
    topics = []
    file_path = "RAG_KNOWLEDGE_BASE.txt"
    
    if not os.path.exists(file_path):
        st.error(f"Файл {file_path} не найден!")
        return [
            {'title': 'DOCKER', 'content': 'Docker — контейнеризация.', 'number': 1},
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

# -------------------- ГЕНЕРАЦИЯ ОТВЕТА --------------------
def ask_gigachat(client, question, context, topic_title):
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

# -------------------- ИНТЕРФЕЙС --------------------
def main():
    # Заголовок с фиолетовым акцентом (без эмодзи)
    st.title("RAG-Ассистент AI/ML")
    st.caption("Ответы по курсу AI/ML на основе 30 тем")
    
    client = init_gigachat()
    topics = load_topics()
    
    if not client:
        st.stop()
    
    with st.sidebar:
        st.subheader("Доступные темы")
        for t in topics[:10]:
            st.write(f"• {t['title']}")
        if len(topics) > 10:
            st.write(f"... и ещё {len(topics)-10} тем")
    
    # Инициализация истории чата
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Привет! Задайте вопрос по AI/ML!"}
        ]
    
    # Отображение переписки
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Поле ввода вопроса
    if prompt := st.chat_input("Напишите ваш вопрос..."):
        # Добавляем вопрос пользователя в историю и на экран
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Генерация ответа
        with st.chat_message("assistant"):
            with st.spinner("Ищу в базе..."):
                topic = find_topic(prompt, topics)
            
            if not topic:
                answer = "Извините, я не нашёл информацию на этот вопрос."
                source = "Не найдено"
            else:
                with st.spinner("Генерирую ответ..."):
                    answer = ask_gigachat(client, prompt, topic['content'][:3500], topic['title'])
                    source = topic['title']
                
                answer += f"\n\n---\nИсточник: {source}"
            
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
