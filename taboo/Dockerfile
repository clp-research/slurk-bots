FROM python:3.9

RUN mkdir -p /usr/src/taboo
WORKDIR /usr/src

COPY taboo/requirements.txt /usr/src/taboo
RUN pip install --no-cache-dir -r taboo/requirements.txt

COPY taboo /usr/src/taboo
COPY templates.py /usr/src/




# RUN -v taboo:/usr/src/taboo
# COPY /usr/src/taboo/data/results /Users/olhasvezhentseva/slurk-bots/taboo/data/results

ENTRYPOINT ["python", "-m", "taboo"]
