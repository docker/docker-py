ARG PYTHON_VERSION=3.10

FROM python:${PYTHON_VERSION}

WORKDIR /src

COPY requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

COPY test-requirements.txt /src/test-requirements.txt
RUN pip install -r test-requirements.txt

COPY . .
ARG SETUPTOOLS_SCM_PRETEND_VERSION_DOCKER
RUN pip install .
