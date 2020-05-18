FROM python:3.7.2

RUN mkdir -p /usr/src/cola
WORKDIR /usr/src/cola

COPY requirements.txt /usr/src/cola
RUN pip install --no-cache-dir -r requirements.txt

COPY ./ /usr/src/cola

ENTRYPOINT ["python", "cola_bot.py"]
