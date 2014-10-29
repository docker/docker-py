FROM debian:wheezy

MAINTAINER Joffrey F <joffrey@dotcloud.com>

RUN apt-get update && \
    apt-get install -y python-pip && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /opt/src/

ADD . /opt/src

WORKDIR /opt/src/

RUN pip install \
    -r /opt/src/test-requirements.txt \
    -e /opt/src

CMD ["/bin/bash"]
