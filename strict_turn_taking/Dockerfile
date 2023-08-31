FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY strict_turn_taking /usr/src/strict_turn_taking

RUN pip install --no-cache-dir -r strict_turn_taking/requirements.txt

ENTRYPOINT ["python", "-m", "strict_turn_taking"]
