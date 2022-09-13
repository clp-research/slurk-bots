FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY slurk-telegram /usr/src/slurk-telegram

RUN pip install --no-cache-dir -r slurk-telegram/requirements.txt

ENTRYPOINT ["python", "-m", "slurk-telegram"]
