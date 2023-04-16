FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY recolageval /usr/src/recolageval

RUN pip install --no-cache-dir -r recolageval/requirements.txt

ENTRYPOINT ["python", "-m", "recolageval"]
