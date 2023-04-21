FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY ccbts /usr/src/ccbts

COPY ccbts/90_cocobots_blockworld/ver4 /usr/src

RUN pip install --no-cache-dir -r ccbts/requirements.txt

ENTRYPOINT ["python", "-m", "ccbts"]
