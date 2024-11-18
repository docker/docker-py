# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}

RUN apt-get update && apt-get -y install --no-install-recommends \
    gnupg2 \
    pass

# Add SSH keys and set permissions
COPY tests/ssh/config/client /root/.ssh
COPY tests/ssh/config/server/known_ed25519.pub /root/.ssh/known_hosts
RUN sed -i '1s;^;dpy-dind-ssh ;' /root/.ssh/known_hosts
RUN chmod -R 600 /root/.ssh

COPY ./tests/gpg-keys /gpg-keys
RUN gpg2 --import gpg-keys/secret
RUN gpg2 --import-ownertrust gpg-keys/ownertrust
RUN yes | pass init $(gpg2 --no-auto-check-trustdb --list-secret-key | awk '/^sec/{getline; $1=$1; print}')
RUN gpg2 --check-trustdb
ARG CREDSTORE_VERSION=v0.6.3
RUN curl -sSL -o /opt/docker-credential-pass.tar.gz \
    https://github.com/docker/docker-credential-helpers/releases/download/$CREDSTORE_VERSION/docker-credential-pass-$CREDSTORE_VERSION-amd64.tar.gz && \
    tar -xf /opt/docker-credential-pass.tar.gz -O > /usr/local/bin/docker-credential-pass && \
    rm -rf /opt/docker-credential-pass.tar.gz && \
    chmod +x /usr/local/bin/docker-credential-pass

WORKDIR /src
COPY . .

ARG VERSION=0.0.0.dev0
RUN --mount=type=cache,target=/cache/pip \
    PIP_CACHE_DIR=/cache/pip \
    SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION} \
    pip install .[dev,ssh,websockets]
