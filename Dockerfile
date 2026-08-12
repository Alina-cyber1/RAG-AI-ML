FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY RAG_WEBSITE_GIGACHAT_FINAL.py .
COPY RAG_KNOWLEDGE_BASE.txt .
COPY images/ images/

# Запускаем
CMD ["streamlit", "run", "RAG_WEBSITE_GIGACHAT_FINAL.py", "--server.port=7860", "--server.address=0.0.0.0"]
