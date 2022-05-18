FROM python:3.9

RUN mkdir -p /usr/src/wordle
WORKDIR /usr/src/wordle

COPY wordle/requirements.txt /usr/src/wordle
RUN pip install --no-cache-dir -r requirements.txt

COPY wordle /usr/src/wordle

ENTRYPOINT ["python", "main.py"]
