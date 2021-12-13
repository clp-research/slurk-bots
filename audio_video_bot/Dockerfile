FROM python:3.9

RUN mkdir -p /usr/src/audio-video-bot
WORKDIR /usr/src/audio-video-bot

COPY audio_video_bot/requirements.txt /usr/src/audio-video-bot
RUN pip install --no-cache-dir -r requirements.txt

COPY audio_video_bot /usr/src/audio-video-bot

ENTRYPOINT ["python", "audio_video_bot.py"]
