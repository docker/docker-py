ARG PYTHON_VERSION=3.6
FROM python:$PYTHON_VERSION-jessie AS base

FROM base AS credhelpers
ARG CREDSTORE_VERSION=v0.6.2
ADD https://github.com/docker/docker-credential-helpers/releases/download/${CREDSTORE_VERSION}/docker-credential-pass-${CREDSTORE_VERSION}-amd64.tar.gz /tmp/

RUN tar -xf /tmp/docker-credential-pass-${CREDSTORE_VERSION}-amd64.tar.gz -C /usr/local/bin/
RUN docker-credential-pass version || echo "failed to run credentials helper"

FROM base AS final
RUN apt-get update && apt-get -y install \
    gnupg2 \
    pass

COPY --from=credhelpers /usr/local/bin/docker-credential-pass /usr/local/bin/

COPY ./tests/gpg-keys /gpg-keys
RUN gpg2 --import gpg-keys/secret
RUN gpg2 --import-ownertrust gpg-keys/ownertrust
RUN yes | pass init $(gpg2 --no-auto-check-trustdb --list-secret-keys | grep ^sec | cut -d/ -f2 | cut -d" " -f1)
RUN gpg2 --check-trustdb

WORKDIR /src
COPY requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

COPY test-requirements.txt /src/test-requirements.txt
RUN pip install -r test-requirements.txt

COPY . .
RUN pip install .
