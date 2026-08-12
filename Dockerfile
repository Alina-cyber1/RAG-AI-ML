FROM python:3.11-slim

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY app.py .
COPY bot.py .
COPY RAG_KNOWLEDGE_BASE.txt .
COPY images/ images/

# Запуск (по умолчанию веб-интерфейс)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
