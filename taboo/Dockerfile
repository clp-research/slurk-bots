FROM python:3.9

RUN mkdir -p /usr/src/taboo
WORKDIR /usr/src/taboo

COPY taboo/requirements.txt /usr/src/taboo
RUN pip install --no-cache-dir -r requirements.txt

COPY taboo /usr/src/taboo

ENTRYPOINT ["python", "taboo.py"]
