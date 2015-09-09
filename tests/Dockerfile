FROM dockerswarm/dind:1.8.1
MAINTAINER Joffrey F <joffrey@docker.com>

RUN mkdir /home/docker-py
WORKDIR /home/docker-py

RUN apt-get update && apt-get install -y python python-setuptools && easy_install pip

ADD requirements.txt /home/docker-py/requirements.txt
RUN pip install -r requirements.txt

ADD test-requirements.txt /home/docker-py/test-requirements.txt
RUN pip install -r test-requirements.txt

ADD . /home/docker-py
RUN pip install -U .

CMD ["bash", "-c", "docker daemon 2>/dev/null & py.test -rxs tests/integration_test.py"]