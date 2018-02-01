FROM python:3.6

RUN mkdir /src
WORKDIR /src

COPY requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

COPY test-requirements.txt /src/test-requirements.txt
RUN pip install -r test-requirements.txt

COPY . /src
RUN pip install .
