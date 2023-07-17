FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY placement /usr/src/placement

RUN pip install --no-cache-dir -r placement/requirements.txt

ENTRYPOINT ["python", "-m", "placement"]
