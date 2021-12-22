FROM python:3.9

RUN mkdir -p /usr/src/intervention
WORKDIR /usr/src/intervention

COPY intervention/requirements.txt /usr/src/intervention
RUN pip install --no-cache-dir -r requirements.txt

COPY intervention /usr/src/intervention

ENTRYPOINT ["python", "intervention.py"]
