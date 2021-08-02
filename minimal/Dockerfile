FROM python:3.9

RUN mkdir -p /usr/src/minimal
WORKDIR /usr/src/minimal

COPY minimal/requirements.txt /usr/src/minimal
RUN pip install --no-cache-dir -r requirements.txt

COPY minimal /usr/src/minimal

ENTRYPOINT ["python", "minimal.py"]
