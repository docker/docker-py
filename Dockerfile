FROM ubuntu:12.10
MAINTAINER Joffrey F <joffrey@dotcloud.com>
RUN apt-get update
RUN yes | apt-get install python-pip
ADD . /home/docker-py
RUN cd /home/docker-py && pip install .
