FROM python:3.9

RUN mkdir -p /usr/src/drawing_game
WORKDIR /usr/src/drawing_game

COPY drawing_game/requirements.txt /usr/src/drawing_game
RUN pip install --no-cache-dir -r requirements.txt

COPY drawing_game /usr/src/drawing_game

ENTRYPOINT ["python", "__main__.py"]
