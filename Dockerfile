FROM gcr.io/google-appengine/python

RUN apt-get update && apt-get dist-upgrade -y
RUN apt-get install -y firefox-esr xvfb unzip \
 && cd /tmp/ \
 && wget https://github.com/mozilla/geckodriver/releases/download/v0.20.0/geckodriver-v0.20.0-linux64.tar.gz -O driver.tar.gz \
 && tar -xvzf driver.tar.gz \
 && chmod +x geckodriver \
 && mv geckodriver /usr/local/bin/ \
 && rm driver.tar.gz

RUN virtualenv -p python3.6 /env

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

ADD . /app

CMD gunicorn -c gunicorn_config.py cronscrape.main:app
