FROM python:3.9

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY math_ /usr/src/math_

RUN pip install --no-cache-dir -r math_/requirements.txt

ENTRYPOINT ["python", "-m", "math_"]
