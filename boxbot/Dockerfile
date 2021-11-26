FROM python:3.9

RUN mkdir -p /usr/src/boxbot
WORKDIR /usr/src/boxbot

COPY boxbot/requirements.txt /usr/src/boxbot
RUN pip install --no-cache-dir -r requirements.txt

COPY boxbot /usr/src/boxbot

ENTRYPOINT ["python", "boxbot.py"]
