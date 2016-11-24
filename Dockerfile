FROM python:2.7

RUN mkdir /home/docker-py
WORKDIR /home/docker-py

COPY requirements.txt /home/docker-py/requirements.txt
RUN pip install -r requirements.txt

COPY test-requirements.txt /home/docker-py/test-requirements.txt
RUN pip install -r test-requirements.txt

COPY . /home/docker-py
RUN pip install .
