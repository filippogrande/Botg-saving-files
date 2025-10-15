FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV SAVE_DIR=/mnt/truenas-bot
VOLUME ["/mnt/truenas-bot"]
CMD ["python", "bot.py"]
