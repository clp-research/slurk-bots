FROM python:3.7.2

RUN mkdir -p /usr/src/image_click_bot
WORKDIR /usr/src/image_click_bot

COPY requirements.txt /usr/src/image_click_bot
RUN pip install --no-cache-dir -r requirements.txt

COPY ./ /usr/src/image_click_bot

ENTRYPOINT ["python", "image_click_bot.py"]
# CMD ["/bin/bash"]
