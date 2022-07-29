ARG PYTHON_VERSION=3.10

FROM python:${PYTHON_VERSION}

RUN mkdir /src
WORKDIR /src

COPY requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY test-requirements.txt /src/test-requirements.txt
RUN pip install --no-cache-dir -r test-requirements.txt

COPY . /src
RUN pip install --no-cache-dir .
