FROM python:2.7
MAINTAINER Joffrey F <joffrey@docker.com>

RUN mkdir /home/docker-py
WORKDIR /home/docker-py

ADD requirements.txt /home/docker-py/requirements.txt
RUN pip install -r requirements.txt

ADD test-requirements.txt /home/docker-py/test-requirements.txt
RUN pip install -r test-requirements.txt

ADD . /home/docker-py
RUN pip install .
