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

ENTRYPOINT ["python", "-m", "ccbtsdemo"]
