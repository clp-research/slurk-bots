FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY ccbtsreconstruction /usr/src/ccbtsreconstruction

RUN pip install --no-cache-dir -r ccbtsreconstruction/requirements.txt

ENTRYPOINT ["python", "-m", "ccbtsreconstruction"]
