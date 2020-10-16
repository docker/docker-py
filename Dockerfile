ARG PYTHON_VERSION=2.7

FROM python:${PYTHON_VERSION}

# Add SSH keys and set permissions
COPY tests/ssh-keys /root/.ssh
RUN chmod -R 600 /root/.ssh

RUN mkdir /src
WORKDIR /src

COPY requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

COPY test-requirements.txt /src/test-requirements.txt
RUN pip install -r test-requirements.txt

COPY . /src
RUN pip install .
