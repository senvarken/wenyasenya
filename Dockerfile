FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# yt-dlp her zaman en güncel versiyon
RUN pip install --no-cache-dir --upgrade yt-dlp

COPY app.py .
COPY cookies.txt .

EXPOSE 10000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:10000", "--timeout", "120", "app:app"]
