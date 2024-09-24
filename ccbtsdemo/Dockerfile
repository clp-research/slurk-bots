FROM python:3.9
#FROM node:16

RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY templates.py /usr/src/
COPY ccbtsdemo /usr/src/ccbtsdemo

# Install any dependencies
#RUN npm install

RUN pip install --no-cache-dir -r ccbtsdemo/requirements.txt

# Expose the port your app runs on
#EXPOSE 5000

COPY ccbtsdemo/data/models/20240924-080439-random-cello.tar.gz /usr/src/rasamodels/

# Expose the port RASA runs on
EXPOSE 5006

#ENTRYPOINT ["python", "-m", "ccbtsdemo"]
ENTRYPOINT ["sh", "-c", "python -m ccbtsdemo & rasa run --enable-api --cors '*' --port 5006 --log-file rasa.log --model /usr/src/rasamodels/20240924-080439-random-cello.tar.gz"]
