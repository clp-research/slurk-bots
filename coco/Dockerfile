FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY coco /usr/src/coco

RUN pip install --no-cache-dir -r coco/requirements.txt

ENTRYPOINT ["python", "-m", "coco"]
