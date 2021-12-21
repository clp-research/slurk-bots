FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY boxbot /usr/src/boxbot

RUN pip install --no-cache-dir -r boxbot/requirements.txt

ENTRYPOINT ["python", "-m", "boxbot"]
