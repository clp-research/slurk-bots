FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY ccbts /usr/src/ccbts

RUN pip install --no-cache-dir -r ccbts/requirements.txt

ENTRYPOINT ["python", "-m", "ccbts"]
