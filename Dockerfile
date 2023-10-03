FROM gorialis/discord.py

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt
ENV IS_DOCKER true
COPY . .

CMD ["python", "bot.py"]