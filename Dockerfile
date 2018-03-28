FROM gcr.io/google-appengine/python

RUN apt-get update \
 && apt-get install -y chromedriver xvfb unzip\
 && ln -s /usr/lib/chromium/chromedriver /usr/local/bin/chromedriver

RUN virtualenv -p python3.6 /env

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

ADD . /app

CMD gunicorn -b :$PORT cronscrape.main:app
