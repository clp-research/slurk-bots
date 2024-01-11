FROM python:3.9

RUN mkdir -p /usr/src/reference
WORKDIR /usr/src

COPY reference/requirements.txt /usr/src/reference
RUN pip install --no-cache-dir -r reference/requirements.txt

COPY reference /usr/src/reference
COPY templates.py /usr/src/



ENTRYPOINT ["python", "-m", "reference"]
