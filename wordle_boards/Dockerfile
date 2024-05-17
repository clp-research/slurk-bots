FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY wordle_boards /usr/src/wordle_boards

RUN pip install --no-cache-dir -r wordle_boards/requirements.txt

ENTRYPOINT ["python", "-m", "wordle_boards"]
