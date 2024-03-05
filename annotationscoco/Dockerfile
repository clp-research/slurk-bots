FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY annotationscoco /usr/src/annotationscoco

RUN pip install --no-cache-dir -r annotationscoco/requirements.txt

ENTRYPOINT ["python", "-m", "annotationscoco"]
