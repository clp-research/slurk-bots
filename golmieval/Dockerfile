FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY golmieval /usr/src/golmieval

RUN pip install --no-cache-dir -r golmieval/requirements.txt

ENTRYPOINT ["python", "-m", "golmieval"]
