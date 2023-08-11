FROM python:3.9

RUN mkdir -p /usr/src/chatbot
WORKDIR /usr/src/chatbot

COPY chatbot/requirements.txt /usr/src/chatbot
RUN pip install --no-cache-dir -r requirements.txt

COPY templates.py /usr/src/chatbot
COPY chatbot /usr/src/chatbot

ENTRYPOINT ["python", "main.py"]
