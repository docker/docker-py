# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}

WORKDIR /src
COPY . .

ARG VERSION
RUN --mount=type=cache,target=/cache/pip \
    PIP_CACHE_DIR=/cache/pip \
    SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION} \
    pip install .[ssh]
