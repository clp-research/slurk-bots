FROM python:3.9

RUN mkdir -p /usr/src/clickbot
WORKDIR /usr/src/clickbot

COPY clickbot/requirements.txt /usr/src/clickbot
RUN pip install --no-cache-dir -r requirements.txt

COPY clickbot /usr/src/clickbot

ENTRYPOINT ["python", "clickbot.py"]
