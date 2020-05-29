FROM python:3.7.2

RUN mkdir -p /usr/src/math
WORKDIR /usr/src/math

COPY requirements.txt /usr/src/math
RUN pip install --no-cache-dir -r requirements.txt

COPY ./ /usr/src/math

ENTRYPOINT ["python", "math_bot.py"]
# CMD ["/bin/bash"]
