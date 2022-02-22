FROM apache/airflow:1.10.12-python3.6

USER root

RUN pip install wheel

RUN pip install google-play-scraper

COPY ./lib/crate-0.1.3.tar.gz .
RUN pip install ./crate-0.1.3.tar.gz

RUN apt update -y
COPY ./lib/google-chrome-stable_current_amd64.deb .
RUN apt install -y ./google-chrome-stable_current_amd64.deb

COPY ./lib/chromedriver .

USER airflow
