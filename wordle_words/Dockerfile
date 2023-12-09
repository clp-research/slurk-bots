FROM python:3.9

RUN mkdir -p /usr/src/wordle_words
WORKDIR /usr/src

COPY wordle_words/requirements.txt /usr/src/wordle_words
RUN pip install --no-cache-dir -r wordle_words/requirements.txt

COPY wordle_words /usr/src/wordle_words
COPY templates.py /usr/src/

ENTRYPOINT ["python", "-m", "wordle_words"]
