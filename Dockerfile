FROM python:3.11-slim

WORKDIR /app

# Копируем файлы
COPY requirements.txt .
COPY RAG_WEBSITE_GIGACHAT_FINAL.py .
COPY RAG_KNOWLEDGE_BASE.txt .
COPY images/ images/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем приложение
CMD ["streamlit", "run", "RAG_WEBSITE_GIGACHAT_FINAL.py", "--server.port=8501", "--server.address=0.0.0.0"]
