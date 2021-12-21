FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY concierge /usr/src/concierge

RUN pip install --no-cache-dir -r concierge/requirements.txt

ENTRYPOINT ["python", "-m", "concierge"]
