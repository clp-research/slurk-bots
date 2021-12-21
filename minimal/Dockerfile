FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY minimal /usr/src/minimal

RUN pip install --no-cache-dir -r minimal/requirements.txt

ENTRYPOINT ["python", "-m", "minimal"]
