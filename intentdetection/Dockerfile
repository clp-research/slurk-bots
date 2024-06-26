FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY intentdetection /usr/src/intentdetection

RUN pip install --no-cache-dir -r intentdetection/requirements.txt

ENTRYPOINT ["python", "-m", "intentdetection"]
