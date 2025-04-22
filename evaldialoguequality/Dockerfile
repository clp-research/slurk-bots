FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY evaldialoguequality /usr/src/evaldialoguequality

RUN pip install --no-cache-dir -r evaldialoguequality/requirements.txt

ENTRYPOINT ["python", "-m", "evaldialoguequality"]
