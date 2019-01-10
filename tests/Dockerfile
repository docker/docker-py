ARG PYTHON_VERSION=3.6
FROM python:$PYTHON_VERSION-jessie
RUN apt-get update && apt-get -y install \
    gnupg2 \
    pass \
    curl

COPY ./tests/gpg-keys /gpg-keys
RUN gpg2 --import gpg-keys/secret
RUN gpg2 --import-ownertrust gpg-keys/ownertrust
RUN yes | pass init $(gpg2 --no-auto-check-trustdb --list-secret-keys | grep ^sec | cut -d/ -f2 | cut -d" " -f1)
RUN gpg2 --check-trustdb
ARG CREDSTORE_VERSION=v0.6.0
RUN curl -sSL -o /opt/docker-credential-pass.tar.gz \
    https://github.com/docker/docker-credential-helpers/releases/download/$CREDSTORE_VERSION/docker-credential-pass-$CREDSTORE_VERSION-amd64.tar.gz && \
    tar -xf /opt/docker-credential-pass.tar.gz -O > /usr/local/bin/docker-credential-pass && \
    rm -rf /opt/docker-credential-pass.tar.gz && \
    chmod +x /usr/local/bin/docker-credential-pass

WORKDIR /src
COPY requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

COPY test-requirements.txt /src/test-requirements.txt
RUN pip install -r test-requirements.txt

COPY . /src
RUN pip install .
