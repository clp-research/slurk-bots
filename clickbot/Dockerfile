FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY clickbot /usr/src/clickbot

RUN pip install --no-cache-dir -r clickbot/requirements.txt

ENTRYPOINT ["python", "-m", "clickbot"]
