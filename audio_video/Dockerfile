FROM python:3.7.2

RUN mkdir -p /usr/src/slurk-audio-pilot/openvidu
WORKDIR /usr/src/slurk-audio-pilot

COPY audio-bot.py requirements.txt /usr/src/slurk-audio-pilot/
COPY openvidu/__init__.py /usr/src/slurk-audio-pilot/openvidu/
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "audio-bot.py"]
