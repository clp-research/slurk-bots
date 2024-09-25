FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY drawing_game /usr/src/drawing_game

RUN pip install --no-cache-dir -r drawing_game/requirements.txt

ENTRYPOINT ["python", "-m", "drawing_game"]

