FROM python:3.9

RUN mkdir -p /usr/src/wordle_boards
WORKDIR /usr/src/wordle_boards

COPY wordle_boards/requirements.txt /usr/src/wordle_boards
RUN pip install --no-cache-dir -r requirements.txt

COPY wordle_boards /usr/src/wordle_boards

ENTRYPOINT ["python", "main.py"]
