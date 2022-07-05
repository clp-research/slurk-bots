FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY echo /usr/src/echo

RUN pip install --no-cache-dir -r echo/requirements.txt

ENTRYPOINT ["python", "-m", "echo"]
