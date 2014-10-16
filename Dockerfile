FROM python:2.7
MAINTAINER Joffrey F <joffrey@dotcloud.com>
ADD . /home/docker-py
WORKDIR /home/docker-py
RUN pip install -r test-requirements.txt
RUN pip install .
