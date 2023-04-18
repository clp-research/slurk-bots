FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY recolage /usr/src/recolage

RUN pip install --no-cache-dir -r recolage/requirements.txt

ENTRYPOINT ["python", "-m", "recolage"]
