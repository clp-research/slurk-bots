FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY testbot /usr/src/testbot

RUN pip install --no-cache-dir -r testbot/requirements.txt

ENTRYPOINT ["python", "-m", "testbot"]
