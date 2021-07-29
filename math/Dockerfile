FROM python:3.9

RUN mkdir -p /usr/src/math
WORKDIR /usr/src/math

COPY math/requirements.txt /usr/src/math
RUN pip install --no-cache-dir -r requirements.txt

COPY math /usr/src/math

ENTRYPOINT ["python", "math_bot.py"]
