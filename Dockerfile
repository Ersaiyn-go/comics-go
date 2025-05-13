FROM python:3.11-slim

WORKDIR /app

# Устанавливаем netcat-openbsd (реализация nc)
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY wait-for-it.sh .
RUN chmod +x wait-for-it.sh

CMD ["./wait-for-it.sh", "db", "5432", "--", "python", "app.py"]
