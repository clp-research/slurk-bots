FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY golmi /usr/src/golmi

RUN pip install --no-cache-dir -r golmi/requirements.txt

ENTRYPOINT ["python", "-m", "golmi"]
