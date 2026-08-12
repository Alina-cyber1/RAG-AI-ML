WORKDIR /app

# Копируем зависимости (убедитесь, что файл называется requirements.txt, а не requirementstxt)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код и данные (ИСПРАВЛЕНО: используем точные имена с вашего скриншота)
COPY RAG_WEBSITE_EXPERIMENTS.py .
COPY RAG_KNOWLEDGE_BASE.txt .

# Копируем папку с картинками
COPY images ./images

# Запускаем приложение (ОБЯЗАТЕЛЬНО исправьте имя файла и здесь, в CMD!)
CMD ["streamlit", "run", "RAG_WEBSITE_EXPERIMENTS.py", "--server.port=7860", "--server.address=0.0.0.0"]
